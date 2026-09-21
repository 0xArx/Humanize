"""Secrets belong in the operating system's store, with only a pointer in the identity file."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HomeCase, ROOT, keystore, store


class StoreTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_round_trip_and_mode(self):
        keystore.put("email.mailgent.api_key", "mgnt-abc\nwith newline and é")
        self.assertEqual(keystore.get("email.mailgent.api_key"), "mgnt-abc\nwith newline and é")
        self.assertEqual(oct((self.home / "secrets.json").stat().st_mode & 0o777), "0o600")
        keystore.delete("email.mailgent.api_key")
        self.assertIsNone(keystore.get("email.mailgent.api_key"))
        keystore.delete("email.mailgent.api_key")   # deleting nothing is fine

    def test_the_value_is_not_stored_readably(self):
        keystore.put("x.token", "plain-secret-value")
        self.assertNotIn("plain-secret-value", (self.home / "secrets.json").read_text())

    def test_two_agents_never_share_a_secret(self):
        keystore.put("x.token", "agent one")
        other = self.tmp / "other"
        env = dict(self.env, HUMANIZE_HOME=str(other))
        subprocess.run([sys.executable, str(ROOT / "humanize.py"), "init", "--name", "Other", "--port", "0", "--no-open"], env=env, check=True, capture_output=True)
        code = ("import sys; sys.path.insert(0, %r); import keystore; print(keystore.get('x.token'))" % str(ROOT / "scripts"))
        out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "None")
        subprocess.run([sys.executable, str(ROOT / "humanize.py"), "stop"], env=env, capture_output=True)

    def test_names_and_pointers_are_validated(self):
        for bad in ("", "has space", "a/b", "x" * 201):
            with self.assertRaises(keystore.KeystoreError):
                keystore.pointer(bad)
        self.assertTrue(keystore.is_pointer("secret:a.b-c_d"))
        self.assertFalse(keystore.is_pointer("secret:"))
        self.assertFalse(keystore.is_pointer("hunter2"))
        self.assertFalse(keystore.is_pointer(None))

    def test_a_pointer_to_a_missing_secret_is_a_clear_error(self):
        with self.assertRaises(keystore.KeystoreError) as cm:
            keystore.resolve("secret:not.here")
        self.assertIn("self key", str(cm.exception))

    def test_errors_never_contain_the_secret(self):
        os.environ["HUMANIZE_KEYSTORE"] = "keychain"
        os.environ["PATH"], old = "/nonexistent", os.environ["PATH"]
        try:
            with self.assertRaises(Exception) as cm:
                keystore.put("a.token", "TOPSECRETVALUE")
            self.assertNotIn("TOPSECRETVALUE", str(cm.exception))
        finally:
            os.environ["PATH"] = old
            os.environ["HUMANIZE_KEYSTORE"] = "file"

    def test_the_backend_can_be_chosen(self):
        for name in ("file", "keychain", "secret-service"):
            os.environ["HUMANIZE_KEYSTORE"] = name
            self.assertEqual(keystore.backend(), name)
        os.environ["HUMANIZE_KEYSTORE"] = "file"


class CliTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_a_secret_looking_key_goes_to_the_store_automatically(self):
        r = self.hz("set", "email.mailgent.api_key", "mgnt-TOPSECRET123")
        self.assertIn("stored in", r.stderr)
        raw = self.identity.read_text()
        self.assertNotIn("TOPSECRET123", raw)
        self.assertEqual(self.load()["email"]["mailgent"]["api_key"], "secret:email.mailgent.api_key")
        self.assertNotIn("TOPSECRET123", (self.home / "identity.json.bak").read_text())
        self.assertEqual(self.hz("get", "email.mailgent.api_key").stdout.strip(), "mgnt-TOPSECRET123", "get fetches it for the agent")
        self.assertEqual(self.hz("get", "email.mailgent.api_key", "--pointer").stdout.strip(), "secret:email.mailgent.api_key")

    def test_only_secret_looking_keys_are_moved(self):
        self.hz("set", "email.mailgent.address", "a@b.dev")
        self.hz("set", "ssh.public_key", "ssh-ed25519 AAAA")
        self.hz("set", "phone.dial.auth", "~/.local/share/dial/auth.json")
        d = self.load()
        self.assertEqual(d["email"]["mailgent"]["address"], "a@b.dev")
        self.assertEqual(d["ssh"]["public_key"], "ssh-ed25519 AAAA", "a public key is not a secret")
        self.assertEqual(d["phone"]["dial"]["auth"], "~/.local/share/dial/auth.json", "a file path is not a secret")

    def test_plain_and_secret_flags_override(self):
        self.hz("set", "email.mailgent.api_key", "keep-me-plain-1234", "--plain")
        self.assertEqual(self.load()["email"]["mailgent"]["api_key"], "keep-me-plain-1234")
        self.hz("set", "persona", "sensitive persona text", "--secret")
        self.assertEqual(self.load()["persona"], "secret:persona")
        self.assertEqual(self.hz("get", "persona").stdout.strip(), "sensitive persona text")

    def test_setting_a_pointer_or_a_non_string_is_left_alone(self):
        self.hz("set", "email.mailgent.api_key", "secret:already.there")
        self.assertEqual(self.load()["email"]["mailgent"]["api_key"], "secret:already.there")
        self.hz("set", "messaging.telegram.token", '{"a": 1}')
        self.assertEqual(self.load()["messaging"]["telegram"]["token"], {"a": 1})

    def test_the_dashboard_never_shows_the_value_and_the_page_still_loads(self):
        self.hz("set", "phone.agentphone.api_key", "ap_live_NEVERSHOWN99")
        port, token = self.dashboard()
        from helpers import http
        s, _, body = http(port, "GET", "/api/identity", headers={"X-Humanize-Token": token})
        self.assertEqual(s, 200)
        self.assertNotIn(b"NEVERSHOWN99", body)

    def test_secret_commands(self):
        self.assertIn("file", self.hz("secret", "backend").stdout)
        self.hz("set", "email.mailgent.api_key", "mgnt-LISTED-000000")
        listed = json.loads(self.hz("secret", "list").stdout)
        self.assertEqual(listed, [{"name": "email.mailgent.api_key", "present": True}])
        self.hz("secret", "set", "custom.thing", "value-1")
        self.assertEqual(self.hz("secret", "get", "custom.thing").stdout.strip(), "value-1")
        self.hz("secret", "delete", "custom.thing")
        self.assertNotEqual(self.hz("secret", "get", "custom.thing", check=False).returncode, 0)

    def test_migrate_moves_existing_plain_text_and_scrubs_the_backup_copy(self):
        d = self.load()
        d["email"]["mailgent"]["api_key"] = "mgnt-OLDPLAIN-5555"
        d["accounts"] = {"github": {"username": "arivale", "token": "ghp_OLDPLAINTOKEN0000"}}
        d["wallet"]["evm"]["privateKey"] = "0xPLAINPRIVATEKEY0000"
        self.identity.write_text(json.dumps(d))
        out = json.loads(self.hz("secret", "migrate").stdout)
        self.assertEqual(sorted(out["moved"]), ["accounts.github.token", "email.mailgent.api_key", "wallet.evm.privateKey"])
        for f in ("identity.json", "identity.json.bak"):
            text = (self.home / f).read_text()
            for secret in ("OLDPLAIN-5555", "OLDPLAINTOKEN", "PLAINPRIVATEKEY"):
                self.assertNotIn(secret, text, f"{secret} still in {f}")
        self.assertEqual(self.hz("get", "accounts.github.token").stdout.strip(), "ghp_OLDPLAINTOKEN0000")
        self.assertEqual(json.loads(self.hz("secret", "migrate").stdout)["moved"], [], "running it again moves nothing")
        self.assertEqual(self.load()["accounts"]["github"]["username"], "arivale")

    def test_doctor_reports_and_fixes_plain_secrets_and_missing_ones(self):
        d = self.load()
        d["email"]["mailgent"]["api_key"] = "mgnt-DOCTOR-7777"
        self.identity.write_text(json.dumps(d))
        self.assertIn("plain text", self.hz("doctor").stdout)
        r = self.hz("doctor", "--fix")
        self.assertNotIn("DOCTOR-7777", self.identity.read_text())
        self.assertIn("secret(s) present", self.hz("doctor").stdout)
        (self.home / "secrets.json").unlink()
        self.assertIn("refer to secrets this machine does not have", self.hz("doctor").stdout)
        self.assertNotEqual(self.hz("get", "email.mailgent.api_key", check=False).returncode, 0)


@unittest.skipUnless(os.environ.get("HUMANIZE_TEST_REAL_KEYCHAIN") and sys.platform == "darwin", "set HUMANIZE_TEST_REAL_KEYCHAIN=1 on a Mac to use the real Keychain")
class RealKeychainTests(HomeCase):
    def test_round_trip_through_the_real_macos_keychain(self):
        self.init()
        os.environ["HUMANIZE_KEYSTORE"] = "keychain"
        try:
            keystore.put("probe.token", "real keychain value ✓")
            self.assertEqual(keystore.get("probe.token"), "real keychain value ✓")
            keystore.put("probe.token", "updated")
            self.assertEqual(keystore.get("probe.token"), "updated")
            keystore.delete("probe.token")
            self.assertIsNone(keystore.get("probe.token"))
        finally:
            try:
                keystore.delete("probe.token")
            finally:
                os.environ["HUMANIZE_KEYSTORE"] = "file"


if __name__ == "__main__":
    unittest.main()
