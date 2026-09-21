import json
import socket
import unittest

from helpers import HomeCase, ROOT, store


class InitTests(HomeCase):
    def test_init_creates_a_complete_private_identity(self):
        r = self.init("Ari Vale")
        self.assertIn("identity created", r.stdout)
        d = self.load()
        self.assertEqual(d["name"], "Ari Vale")
        self.assertEqual(oct(self.identity.stat().st_mode & 0o777), "0o600")
        self.assertEqual(oct(self.home.stat().st_mode & 0o777), "0o700")
        self.assertEqual(len(d["layers"]), 24)
        tpl = json.loads((ROOT / "identity.template.json").read_text())
        self.assertEqual(sorted(set(tpl) - set(d)), [], "every template key must be present")
        self.assertTrue(d["host"]["app"], "host is detected")
        self.assertIsNotNone(d["face"]["seed"])

    def test_init_is_idempotent_and_never_overwrites(self):
        self.init("First Name")
        self.hz("set", "persona", "kept")
        r = self.hz("init", "--name", "Second Name", "--port", "0", "--no-open")
        self.assertIn("identity exists", r.stdout)
        d = self.load()
        self.assertEqual((d["name"], d["persona"]), ("First Name", "kept"))

    def test_a_newer_version_adds_missing_keys_without_touching_values(self):
        self.init()
        d = self.load()
        del d["eyes"], d["verify"]
        d["persona"] = "mine"
        self.identity.write_text(json.dumps(d))
        self.hz("init", "--port", "0", "--no-open")
        d = self.load()
        self.assertIn("eyes", d)
        self.assertIn("verify", d)
        self.assertEqual(d["persona"], "mine")

    def test_a_busy_default_port_is_skipped(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        busy = s.getsockname()[1]
        try:
            r = self.hz("init", "--name", "P", "--port", str(busy), "--no-open")
            info = json.loads((self.home / "dashboard.json").read_text())
            self.assertNotEqual(info["port"], busy)
            self.assertIn(f"http://127.0.0.1:{info['port']}", r.stdout)
        finally:
            s.close()

    def test_stop_stops_and_status_reports(self):
        self.init()
        self.assertIn("http://127.0.0.1:", self.hz("status").stdout)
        self.assertIn("stopped", self.hz("stop").stdout)
        self.assertIn("not running", self.hz("status").stdout)

    def test_a_corrupt_identity_is_a_clear_error_and_left_alone(self):
        self.init()
        self.identity.write_text("{oops")
        r = self.hz("status", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not valid JSON", r.stderr)
        self.assertEqual(self.identity.read_text(), "{oops")

    def test_version(self):
        self.assertRegex(self.hz("--version").stdout, r"humanize \d+\.\d+\.\d+")


class DoctorTests(HomeCase):
    def test_doctor_passes_on_a_healthy_install(self):
        self.init()
        r = self.hz("doctor")
        self.assertIn("0 problem(s)", r.stdout)
        self.assertIn("install files complete", r.stdout)

    def test_doctor_fix_repairs_permissions_and_missing_keys(self):
        self.init()
        d = self.load()
        del d["contacts"]
        self.identity.write_text(json.dumps(d))
        self.identity.chmod(0o644)
        self.assertIn("missing", self.hz("doctor").stdout)
        self.hz("doctor", "--fix")
        self.assertEqual(oct(self.identity.stat().st_mode & 0o777), "0o600")
        self.assertIn("contacts", self.load())

    def test_doctor_fails_on_a_corrupt_identity(self):
        self.init()
        self.identity.write_text("nope")
        r = self.hz("doctor", check=False)
        self.assertEqual(r.returncode, 1)


class AgentHelperTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.init()

    def test_get_set_and_types(self):
        self.hz("set", "email.agentmail.address", "ari@agentmail.to")
        self.hz("set", "rules", '["no spend over 50"]')
        self.hz("set", "layers.14.enabled", "false")
        self.assertEqual(self.hz("get", "email.agentmail.address").stdout.strip(), "ari@agentmail.to")
        self.assertEqual(self.hz("get", "layers.14.enabled").stdout.strip(), "false")
        self.assertEqual(json.loads(self.hz("get", "rules").stdout), ["no spend over 50"])
        self.assertNotEqual(self.hz("get", "nothing.here", check=False).returncode, 0)

    def test_set_with_log_and_log_with_cost(self):
        self.hz("set", "did", "did:key:z6Mk", "--log", "stored did")
        self.hz("log", "bought a number", "--cost", "$3/mo")
        log = self.load()["log"]
        self.assertEqual(log[-1]["did"], "bought a number")
        self.assertEqual(log[-1]["cost"], "$3/mo")
        self.assertTrue(any(e["did"] == "stored did" and e["by"] == "agent" for e in log))

    def test_set_through_a_scalar_is_an_error_not_a_crash(self):
        r = self.hz("set", "name.first", "x", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)

    def test_requests_and_done(self):
        store.update(self.identity, lambda d: d.__setitem__("dashboard_requests", [
            {"at": "t", "text": "one", "done": False}, {"at": "t", "text": "two", "done": False}]))
        pending = json.loads(self.hz("requests").stdout)
        self.assertEqual([r["text"] for r in pending], ["one", "two"])
        self.hz("done", "0")
        self.assertEqual([r["text"] for r in json.loads(self.hz("requests").stdout)], ["two"])
        self.assertEqual(len(json.loads(self.hz("requests", "--all").stdout)), 2)
        self.assertNotEqual(self.hz("done", "9", check=False).returncode, 0)

    def test_chat_reports_a_missing_command(self):
        self.hz("set", "host.open_command", "")
        r = self.hz("chat", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("open_command", r.stderr)


class MemoryTests(HomeCase):
    def test_remember_search_and_people(self):
        self.init()
        self.hz("memory", "add", "Met Sana Okafor at the KL conference", "--kind", "person", "--tags", "sana")
        self.hz("memory", "add", "Decided to use SQLite for memory", "--kind", "decision")
        hit = json.loads(self.hz("memory", "search", "conference sana").stdout)
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["kind"], "person")
        self.assertEqual(json.loads(self.hz("memory", "search", 'a "b" (c) * OR NEAR').stdout), [], "punctuation cannot break search")
        self.assertEqual(len(json.loads(self.hz("memory", "search").stdout)), 2, "empty query lists the latest")
        self.hz("memory", "person", "Sana Okafor", "--handle", "@sana")
        self.hz("memory", "person", "Sana Okafor", "--notes", "prefers WhatsApp")
        people = json.loads(self.hz("memory", "people").stdout)
        self.assertEqual((people[0]["handle"], people[0]["notes"]), ("@sana", "prefers WhatsApp"))
        self.assertEqual(oct((self.home / "memory.db").stat().st_mode & 0o777), "0o600")
        self.assertTrue(self.load()["memory"]["local"].endswith("memory.db"))

    def test_nothing_to_remember_is_an_error(self):
        self.init()
        self.assertNotEqual(self.hz("memory", "add", "   ", check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
