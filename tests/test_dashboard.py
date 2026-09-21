"""The dashboard can run a command on the machine, so most of these tests are attacks that must fail."""
import json
import re
import unittest

from helpers import HomeCase, http, store


def jpost(port, token, path, obj, **kw):
    h = {"Content-Type": "application/json", "X-Humanize-Token": token}
    h.update(kw.pop("headers", {}))
    return http(port, "POST", path, json.dumps(obj), h, **kw)


class SecurityTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.port, self.token = self.dashboard()
        self.marker = self.tmp / "PWNED"

    def test_the_original_csrf_attack_is_blocked(self):
        """A foreign page sets the chat command and presses the button using only a 'simple' request."""
        evil = {"Origin": "https://evil.example", "Content-Type": "text/plain"}
        s1, _, _ = http(self.port, "POST", "/api/update", json.dumps({"path": "host.open_command", "value": f"touch {self.marker}"}), evil)
        s2, _, _ = http(self.port, "POST", "/api/chat", "{}", evil)
        self.assertEqual((s1, s2), (403, 403))
        self.assertFalse(self.marker.exists())
        self.assertNotIn("touch", json.dumps(self.load()))

    def test_dns_rebinding_host_is_refused_everywhere(self):
        for path in ("/", "/api/ping", "/orb.js", "/avatar", "/fonts/fonts.css"):
            s, _, _ = http(self.port, "GET", path, host="attacker.example")
            self.assertEqual(s, 403, path)
        s, _, _ = http(self.port, "GET", "/", host=f"127.0.0.1:{self.port + 1}")
        self.assertEqual(s, 403, "right host, wrong port")

    def test_every_api_call_needs_the_token(self):
        for method, path in (("GET", "/api/identity"), ("GET", "/api/self/status"), ("POST", "/api/update"), ("POST", "/api/request"),
                             ("POST", "/api/request/done"), ("POST", "/api/chat"), ("POST", "/api/self/push")):
            h = {"Content-Type": "application/json"}
            self.assertEqual(http(self.port, method, path, "{}" if method == "POST" else None, h)[0], 403, path)
            h["X-Humanize-Token"] = "wrong"
            self.assertEqual(http(self.port, method, path, "{}" if method == "POST" else None, h)[0], 403, path)

    def test_cross_site_and_wrong_content_type_are_refused_even_with_the_token(self):
        self.assertEqual(jpost(self.port, self.token, "/api/request", {"text": "x"}, headers={"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(jpost(self.port, self.token, "/api/request", {"text": "x"}, headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(http(self.port, "POST", "/api/request", '{"text":"x"}', {"Content-Type": "text/plain", "X-Humanize-Token": self.token})[0], 415)
        self.assertEqual(self.load()["dashboard_requests"], [])

    def test_bad_bodies_are_400_or_413_never_500(self):
        h = {"Content-Type": "application/json", "X-Humanize-Token": self.token}
        self.assertEqual(http(self.port, "POST", "/api/update", "{not json", h)[0], 400)
        self.assertEqual(http(self.port, "POST", "/api/update", "[1,2]", h)[0], 400)
        self.assertEqual(http(self.port, "POST", "/api/request", json.dumps({"text": "a" * 70000}), h)[0], 413)
        self.assertEqual(jpost(self.port, self.token, "/api/request", {"text": "a" * 2001})[0], 400)
        self.assertEqual(jpost(self.port, self.token, "/api/request/done", {"index": "0"})[0], 400)
        self.assertEqual(jpost(self.port, self.token, "/api/request/done", {"index": 99})[0], 400)

    def test_only_listed_fields_with_the_right_type_can_be_written(self):
        ok = lambda p, v: jpost(self.port, self.token, "/api/update", {"path": p, "value": v})[0]
        self.assertEqual(ok("persona", "hello"), 200)
        self.assertEqual(ok("layers.3.enabled", False), 200)
        self.assertEqual(ok("layers.24.enabled", False), 400, "there is no layer 24")
        self.assertEqual(ok("layers.3.enabled", "yes"), 400)
        self.assertEqual(ok("name", ""), 400)
        self.assertEqual(ok("name", "x" * 101), 400)
        self.assertEqual(ok("rules", "not a list"), 400)
        self.assertEqual(ok("rules", ["ok", 5]), 400)
        for secret in ("wallet.evm.privateKey", "email.mailgent.api_key", "accounts.github.token", "log", "self_repo.url", "dashboard_requests"):
            self.assertEqual(ok(secret, "x"), 400, secret)
        for bad in ("javascript:alert(1)", "javascript://x%0Aalert(1)", "data://text/html,x", "file:///etc/passwd"):
            self.assertEqual(ok("host.chat_url", bad), 400, bad)
        self.assertEqual(ok("host.chat_url", "cursor://"), 200)
        self.assertEqual(ok("host.chat_url", "https://claude.ai/code"), 200)

    def test_the_page_and_api_never_reveal_secrets(self):
        store.update(self.identity, lambda d: d.update(wallet={"evm": {"address": "0xabc", "privateKey": "0xSECRETSECRETSECRETSECRET"}},
                                                       email={"mailgent": {"address": "a@b.dev", "api_key": "mgnt-SECRETSECRET"}}))
        s, _, body = http(self.port, "GET", "/api/identity", headers={"X-Humanize-Token": self.token})
        self.assertEqual(s, 200)
        self.assertNotIn(b"SECRETSECRET", body)
        self.assertIn(b"0xabc", body)
        _, _, page = http(self.port, "GET", "/", headers={"Cookie": self.cookie})
        self.assertNotIn(b"SECRETSECRET", page)

    def test_headers_csp_and_no_inline_handlers(self):
        s, h, page = http(self.port, "GET", "/", headers={"Cookie": self.cookie})
        self.assertEqual(s, 200)
        csp = h["content-security-policy"]
        self.assertIn("default-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertNotRegex(csp, r"script-src[^;]*unsafe-inline")
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        html = page.decode()
        self.assertIn(f'nonce="{nonce}"', html)
        self.assertNotIn("__HZ_", html, "placeholders must be replaced")
        self.assertIsNone(re.search(r"\son(click|change|input|error|load|mouseover)=", html))
        # the page may name a URL the user can choose to open (a host preset), but must never LOAD a third-party resource
        external = r"(?:https?:)?//(?!127\.0\.0\.1|localhost)[a-z0-9.-]+\.[a-z]{2,}"
        for how in (rf'\bsrc\s*=\s*["\']{external}', rf'<link[^>]+href\s*=\s*["\']{external}', rf'url\(\s*["\']?{external}', rf'@import[^;]*{external}', rf'\bfetch\(\s*[`"\']{external}', rf'\bXMLHttpRequest|\bWebSocket\(|\bEventSource\('):
            self.assertIsNone(re.search(how, html, re.I), f"the page loads something from a third party: {how}")
        self.assertEqual(h["x-content-type-options"], "nosniff")
        self.assertEqual(h["x-frame-options"], "DENY")
        self.assertEqual(h["cross-origin-resource-policy"], "same-origin")
        self.assertNotEqual(http(self.port, "GET", "/", headers={"Cookie": self.cookie})[1]["content-security-policy"], csp, "nonce is fresh per response")

    def test_static_routes_cannot_escape_their_folders(self):
        for path in ("/fonts/../store.py", "/fonts/..%2fstore.py", "/fonts/%2e%2e/dashboard.py", "/fonts/x.woff2", "/scripts/store.py", "/store.py", "/identity.json"):
            self.assertIn(http(self.port, "GET", path)[0], (403, 404), path)
        self.assertEqual(http(self.port, "GET", "/fonts/fonts.css")[0], 200)
        self.assertEqual(http(self.port, "GET", "/orb.js")[0], 200)

    def test_avatar_only_serves_real_small_images(self):
        secret = self.tmp / "notes.txt"
        secret.write_text("top secret")
        for photo in (str(secret), "/etc/hosts", str(self.tmp / "missing.png")):
            store.update(self.identity, lambda d: store.set_path(d, "face.photo", photo))
            self.assertEqual(http(self.port, "GET", "/avatar", headers={"Cookie": self.cookie})[0], 404, photo)
        fake = self.tmp / "fake.png"
        fake.write_text("not a png")
        store.update(self.identity, lambda d: store.set_path(d, "face.photo", str(fake)))
        self.assertEqual(http(self.port, "GET", "/avatar", headers={"Cookie": self.cookie})[0], 404, "extension alone is not enough")
        real = self.tmp / "real.png"
        real.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        store.update(self.identity, lambda d: store.set_path(d, "face.photo", str(real)))
        s, h, _ = http(self.port, "GET", "/avatar", headers={"Cookie": self.cookie})
        self.assertEqual((s, h["content-type"]), (200, "image/png"))


class StartupTests(unittest.TestCase):
    def test_starting_the_server_never_does_a_reverse_dns_lookup(self):
        """http.server resolves the machine's own name before it listens; on slow DNS the port stays closed for
        many seconds. On a CI runner this made every dashboard start take about 30 seconds."""
        import socket, sys, time
        from helpers import ROOT
        sys.path.insert(0, str(ROOT / "scripts"))
        import dashboard
        real = socket.getfqdn

        def slow(*a, **k):
            raise AssertionError("socket.getfqdn was called while starting the dashboard server")
        socket.getfqdn = slow
        try:
            t0 = time.time()
            srv = dashboard.Server(("127.0.0.1", 0), dashboard.Handler)
            self.assertLess(time.time() - t0, 2)
            self.assertEqual(srv.server_port, srv.server_address[1])
            srv.server_close()
        finally:
            socket.getfqdn = real


class AccessTests(HomeCase):
    """Another user on the same machine can reach 127.0.0.1 too. Only the owner may load the page."""

    def setUp(self):
        super().setUp()
        self.port, self.token = self.dashboard()

    def test_the_page_is_locked_without_the_key_and_reveals_no_token(self):
        s, h, body = http(self.port, "GET", "/")
        self.assertEqual(s, 401)
        self.assertIn(b"Locked", body)
        self.assertIn(b"humanize.py open", body)
        self.assertNotIn(self.token.encode(), body)
        self.assertNotIn(b"hz-token", body)

    def test_the_wrong_key_and_a_forged_cookie_are_refused(self):
        self.assertEqual(http(self.port, "GET", "/?k=wrong")[0], 401)
        self.assertEqual(http(self.port, "GET", "/?k=")[0], 401)
        self.assertEqual(http(self.port, "GET", "/", headers={"Cookie": "hz=" + "0" * 64})[0], 401)
        self.assertEqual(http(self.port, "GET", "/", headers={"Cookie": "other=" + self.cookie.split("=")[1]})[0], 401)

    def test_the_right_key_sets_a_strict_http_only_cookie_and_hides_the_key(self):
        s, h, _ = http(self.port, "GET", f"/?k={self.key}")
        self.assertEqual(s, 302)
        self.assertEqual(h["location"], "/", "the key must not stay in the address bar")
        cookie = h["set-cookie"]
        for flag in ("HttpOnly", "SameSite=Strict", "Path=/"):
            self.assertIn(flag, cookie)
        self.assertNotIn(self.key, cookie, "the cookie is derived, not the key itself")
        s, _, body = http(self.port, "GET", "/", headers={"Cookie": self.cookie})
        self.assertEqual(s, 200)
        self.assertIn(self.token.encode(), body)

    def test_other_query_parameters_survive_the_redirect(self):
        _, h, _ = http(self.port, "GET", f"/?k={self.key}&theme=dark")
        self.assertEqual(h["location"], "/?theme=dark")

    def test_the_avatar_is_owner_only_but_ping_is_open(self):
        self.assertEqual(http(self.port, "GET", "/avatar")[0], 401)
        self.assertEqual(http(self.port, "GET", "/api/ping")[0], 200)

    def test_the_key_file_is_private_and_survives_a_restart(self):
        keyfile = self.home / "dashboard.key"
        self.assertEqual(oct(keyfile.stat().st_mode & 0o777), "0o600")
        before = keyfile.read_text()
        self.hz("stop")
        self.hz("init", "--port", "0", "--no-open")
        self.assertEqual(keyfile.read_text(), before, "bookmarks and cookies keep working after a restart")
        info = json.loads((self.home / "dashboard.json").read_text())
        self.assertEqual(http(info["port"], "GET", "/", headers={"Cookie": self.cookie})[0], 200)
        self.assertEqual(oct((self.home / "dashboard.json").stat().st_mode & 0o777), "0o600")

    def test_the_open_command_gives_a_working_url(self):
        r = self.hz("open")
        self.assertRegex(r.stdout.strip(), r"^http://127\.0\.0\.1:\d+$")
        self.assertNotIn(self.key, r.stdout, "the key is never printed")


class BehaviourTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.port, self.token = self.dashboard()

    def test_ping_identifies_the_app(self):
        s, _, body = http(self.port, "GET", "/api/ping")
        self.assertEqual(json.loads(body)["app"], "humanize")

    def test_update_request_and_done_round_trip_and_are_logged(self):
        self.assertEqual(jpost(self.port, self.token, "/api/update", {"path": "persona", "value": "  padded  "})[0], 200)
        self.assertEqual(self.load()["persona"], "padded")
        self.assertEqual(jpost(self.port, self.token, "/api/request", {"text": "Get a UK number."})[0], 200)
        self.assertEqual(jpost(self.port, self.token, "/api/request/done", {"index": 0})[0], 200)
        d = self.load()
        self.assertTrue(d["dashboard_requests"][0]["done"])
        self.assertTrue(any(e["did"] == "dashboard set persona" and e["by"] == "human" for e in d["log"]))

    def test_the_agent_and_the_dashboard_can_write_at_the_same_time(self):
        import subprocess, sys, threading
        from helpers import ROOT
        errors = []

        def dash():
            for i in range(15):
                if jpost(self.port, self.token, "/api/request", {"text": f"r{i}"})[0] != 200:
                    errors.append(i)

        def agent():
            for i in range(15):
                subprocess.run([sys.executable, str(ROOT / "humanize.py"), "log", f"a{i}"], env=self.env, check=True, capture_output=True)
        ts = [threading.Thread(target=dash), threading.Thread(target=agent)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        d = self.load()
        self.assertEqual(errors, [])
        self.assertEqual(len(d["dashboard_requests"]), 15)
        self.assertEqual(len([e for e in d["log"] if re.fullmatch(r"a\d+", e["did"])]), 15)

    def test_chat_runs_the_command_and_reports_failures(self):
        marker = self.tmp / "opened"
        self.hz("set", "host.open_command", f"touch {marker}")
        self.assertEqual(jpost(self.port, self.token, "/api/chat", {})[0], 200)
        self.assertTrue(marker.exists())
        self.hz("set", "host.open_command", "echo boom >&2; exit 3")
        s, _, body = jpost(self.port, self.token, "/api/chat", {})
        self.assertEqual(s, 500)
        self.assertIn("boom", json.loads(body)["error"])
        self.hz("set", "host.open_command", "")
        s, _, body = jpost(self.port, self.token, "/api/chat", {})
        self.assertEqual(s, 400)
        self.assertIn("Host", json.loads(body)["error"])

    def test_a_wrongly_typed_command_is_a_400_not_a_crash(self):
        store.update(self.identity, lambda d: store.set_path(d, "host.open_command", True))
        s, _, body = jpost(self.port, self.token, "/api/chat", {})
        self.assertEqual(s, 400)
        self.assertIn("must be text", json.loads(body)["error"])

    def test_a_long_running_command_counts_as_started(self):
        self.hz("set", "host.open_command", "sleep 30")
        self.assertEqual(jpost(self.port, self.token, "/api/chat", {})[0], 200)

    def test_the_cli_chat_command_uses_the_token_itself(self):
        marker = self.tmp / "via-cli"
        self.hz("set", "host.open_command", f"touch {marker}")
        self.hz("chat")
        self.assertTrue(marker.exists())

    def test_a_corrupt_identity_is_a_500_with_a_reason_not_a_crash(self):
        self.identity.write_text("{broken")
        s, _, body = http(self.port, "GET", "/api/identity", headers={"X-Humanize-Token": self.token})
        self.assertEqual(s, 500)
        self.assertIn("not valid JSON", json.loads(body)["error"])
        self.assertEqual(http(self.port, "GET", "/api/ping")[0], 200, "server keeps running")

    def test_self_status_reports_uninitialised(self):
        s, _, body = http(self.port, "GET", "/api/self/status", headers={"X-Humanize-Token": self.token})
        self.assertEqual(s, 200)
        self.assertFalse(json.loads(body)["initialized"])


if __name__ == "__main__":
    unittest.main()
