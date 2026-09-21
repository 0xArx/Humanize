import json
import os
import subprocess
import sys
import unittest

from helpers import HomeCase, ROOT, store


class SelfStorageTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.bare = self.tmp / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.bare)], check=True)
        self.init("Sana Okafor")
        self.hz("stop")
        store.update(self.identity, lambda d: d.update(email={"mailgent": {"address": "a@b.dev", "api_key": "mgnt-VERYSECRETVALUE123"}}))
        self.env["HUMANIZE_SELF_KEY"] = "test-self-key-0123456789"

    def selfpy(self, *args, check=True, env=None, home=None):
        e = dict(self.env, **(env or {}))
        if home:
            e["HUMANIZE_HOME"] = str(home)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "self.py"), *args], capture_output=True, text=True, env=e, timeout=120)
        if check and r.returncode:
            raise AssertionError(f"self.py {' '.join(args)} -> {r.returncode}\n{r.stdout}\n{r.stderr}")
        return r

    def test_round_trip_to_a_second_machine(self):
        self.hz("memory", "add", "remember me")
        self.selfpy("init", str(self.bare))
        clone = self.tmp / "machine2"
        r = self.selfpy("load", str(self.bare), home=clone)
        self.assertIn("identity written", r.stdout)
        a, b = self.load(), json.loads((clone / "identity.json").read_text())
        for d in (a, b):
            d.pop("self_repo", None)
        self.assertEqual(a, b)
        self.assertEqual(oct((clone / "identity.json").stat().st_mode & 0o777), "0o600")
        self.assertTrue((clone / "face.png").exists() or True)
        e = dict(self.env, HUMANIZE_HOME=str(clone))
        found = subprocess.run([sys.executable, str(ROOT / "humanize.py"), "memory", "search", "remember"], capture_output=True, text=True, env=e)
        self.assertIn("remember me", found.stdout, "memory travels with the identity")
        self.assertTrue((clone / "self" / "humanize.py").exists() and (clone / "self" / "scripts" / "dashboard.py").exists(),
                        "the repo carries the scripts needed to boot")

    def test_nothing_secret_is_stored_in_plaintext(self):
        self.selfpy("init", str(self.bare))
        worktree = self.home / "self"
        for path in worktree.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                self.assertNotIn(b"VERYSECRETVALUE123", path.read_bytes(), str(path))
        blob = subprocess.run(["git", "--git-dir", str(self.bare), "log", "--all", "-p", "--format="], capture_output=True, text=True).stdout
        self.assertNotIn("VERYSECRETVALUE123", blob)
        self.assertFalse((worktree / "identity.json").exists())

    def test_wrong_key_and_tampering_are_refused(self):
        self.selfpy("init", str(self.bare))
        clone = self.tmp / "m2"
        r = self.selfpy("load", str(self.bare), home=clone, env={"HUMANIZE_SELF_KEY": "wrong"}, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Decrypt failed", r.stdout + r.stderr)
        self.assertFalse((clone / "identity.json").exists())
        enc = self.home / "self" / "identity.json.enc"
        raw = bytearray(enc.read_bytes())
        raw[40] ^= 0x01
        enc.write_bytes(bytes(raw))
        r = self.selfpy("unlock", "--force", check=False)
        self.assertIn("modified", r.stdout + r.stderr)

    def test_push_without_a_key_does_not_invent_one(self):
        self.selfpy("init", str(self.bare), env={"HUMANIZE_SELF_KEY": ""})   # creates the key file
        (self.home / "self.key").unlink()
        r = self.selfpy("push", check=False, env={"HUMANIZE_SELF_KEY": ""})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No self key", r.stdout + r.stderr)
        self.assertFalse((self.home / "self.key").exists(), "a new key would make earlier pushes unreadable")

    def test_first_init_creates_and_prints_a_key_once(self):
        env = {"HUMANIZE_SELF_KEY": ""}
        r = self.selfpy("init", str(self.bare), env=env)
        self.assertIn("NEW SELF KEY", r.stdout)
        keyfile = self.home / "self.key"
        self.assertEqual(oct(keyfile.stat().st_mode & 0o777), "0o600")
        self.assertIn(keyfile.read_text().strip(), r.stdout)
        self.assertNotIn("NEW SELF KEY", self.selfpy("push", env=env).stdout)

    def test_pull_refuses_to_discard_unpushed_work(self):
        self.selfpy("init", str(self.bare))
        st = json.loads(self.selfpy("status").stdout)
        self.assertFalse(st["unpushed_changes"])
        self.hz("set", "persona", "changed after the push")
        self.assertTrue(json.loads(self.selfpy("status").stdout)["unpushed_changes"])
        r = self.selfpy("pull", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not pushed", r.stdout + r.stderr)
        self.assertEqual(self.load()["persona"], "changed after the push")
        self.selfpy("push")
        self.assertFalse(json.loads(self.selfpy("status").stdout)["unpushed_changes"], "pushing does not count as a change")

    def test_unlock_will_not_overwrite_a_different_identity_without_force(self):
        self.selfpy("init", str(self.bare))
        clone = self.tmp / "m2"
        self.selfpy("load", str(self.bare), home=clone)
        e = dict(self.env, HUMANIZE_HOME=str(clone))
        subprocess.run([sys.executable, str(ROOT / "humanize.py"), "set", "persona", "local edit"], env=e, check=True, capture_output=True)
        r = self.selfpy("unlock", home=clone, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--force", r.stdout + r.stderr)
        self.selfpy("unlock", "--force", home=clone)
        self.assertTrue((clone / "identity.json.bak").exists())

    def test_the_token_never_lands_in_git_config(self):
        self.selfpy("init", str(self.bare), env={"GITHUB_TOKEN": "ghp_SHOULDNEVERBESTORED"})
        cfg = (self.home / "self" / ".git" / "config").read_text()
        self.assertNotIn("SHOULDNEVERBESTORED", cfg)
        self.assertNotIn("x-access-token", cfg)

    def test_status_before_init(self):
        st = json.loads(self.selfpy("status").stdout)
        self.assertFalse(st["initialized"])


if __name__ == "__main__":
    unittest.main()
