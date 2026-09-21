import json
import subprocess
import sys
import threading
import unittest

from helpers import HomeCase, ROOT, store


class MaskTests(unittest.TestCase):
    def test_hides_secrets_whatever_the_value_looks_like(self):
        d = {"email": {"mailgent": {"address": "a@b.dev", "api_key": "mgnt-8f2a9c1d7e6b5a4f"}},
             "wallet": {"evm": {"address": "0xabc", "privateKey": "0xdead" + "0" * 58}},
             "accounts": {"x": {"token": "has/slashes+and=signs=="}, "y": {"password": "pw"}},
             "phone": {"dial": {"auth": "~/.local/share/dial/auth.json"}},
             "ssh": {"public_key": "ssh-ed25519 AAAA"}}
        m = store.mask(d)
        self.assertEqual(m["email"]["mailgent"]["address"], "a@b.dev")
        self.assertTrue(m["email"]["mailgent"]["api_key"].startswith("•"))
        self.assertNotIn("mgnt-8f2a", json.dumps(m))
        self.assertTrue(m["wallet"]["evm"]["privateKey"].startswith("•"))
        self.assertEqual(m["wallet"]["evm"]["address"], "0xabc")
        self.assertTrue(m["accounts"]["x"]["token"].startswith("•"), "a secret containing / must still be hidden")
        self.assertEqual(m["accounts"]["y"]["password"], "••••")
        self.assertTrue(m["phone"]["dial"]["auth"].startswith("•"), "no value is exempt")
        self.assertEqual(m["ssh"]["public_key"], "ssh-ed25519 AAAA", "public keys are not secret")

    def test_a_secret_object_is_hidden_whole(self):
        self.assertNotIn("v1", json.dumps(store.mask({"credentials": {"a": "v1", "b": ["v1"]}})))

    def test_leaves_non_strings_alone(self):
        self.assertEqual(store.mask({"token": None, "n": 3, "ok": True}), {"token": None, "n": 3, "ok": True})


class FileTests(HomeCase):
    def test_save_is_private_atomic_and_keeps_a_backup(self):
        p = self.home / "identity.json"
        store.save(p, {"v": 1})
        store.save(p, {"v": 2})
        self.assertEqual(oct(p.stat().st_mode & 0o777), "0o600")
        self.assertEqual(json.loads(p.read_text()), {"v": 2})
        self.assertEqual(json.loads((self.home / "identity.json.bak").read_text()), {"v": 1})
        self.assertFalse((self.home / "identity.json.tmp").exists())

    def test_corrupt_file_is_reported_not_overwritten(self):
        p = self.home / "identity.json"
        self.home.mkdir(parents=True)
        p.write_text("{not json")
        with self.assertRaises(store.StoreError) as cm:
            store.update(p, lambda d: d.update(x=1))
        self.assertIn(".bak", str(cm.exception))
        self.assertEqual(p.read_text(), "{not json", "a corrupt file must be left for the human to inspect")

    def test_set_path_refuses_to_walk_through_a_scalar(self):
        with self.assertRaises(store.StoreError):
            store.set_path({"a": "text"}, "a.b", 1)

    def test_threads_never_lose_an_update(self):
        p = self.home / "identity.json"
        store.save(p, {"n": 0})

        def bump():
            for _ in range(40):
                store.update(p, lambda d: d.__setitem__("n", d["n"] + 1))
        ts = [threading.Thread(target=bump) for _ in range(5)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(store.load(p)["n"], 200)

    def test_processes_never_lose_an_update(self):
        p = self.home / "identity.json"
        store.save(p, {"n": 0})
        code = ("import sys; sys.path.insert(0, %r); import store\n"
                "for _ in range(25): store.update(%r, lambda d: d.__setitem__('n', d['n'] + 1))" % (str(ROOT / "scripts"), str(p)))
        procs = [subprocess.Popen([sys.executable, "-c", code]) for _ in range(4)]
        [pr.wait() for pr in procs]
        self.assertEqual(store.load(p)["n"], 100)

    def test_log_is_capped(self):
        d = {}
        for i in range(1100):
            store.log_entry(d, f"e{i}")
        self.assertEqual(len(d["log"]), 1000)
        self.assertEqual(d["log"][-1]["did"], "e1099")


if __name__ == "__main__":
    unittest.main()
