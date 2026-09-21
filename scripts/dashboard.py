#!/usr/bin/env python3
"""Humanize dashboard: a local web page to see and steer the humanized agent.

  python3 scripts/dashboard.py [--identity PATH] [--port 4242] [--no-open]

Standard library only. Binds to 127.0.0.1. Reads and writes the identity file through store.py,
hides secrets before they reach the browser, and runs host.open_command for the Open chat button.

Because this server can run a command on your machine, it defends itself:
  * only answers requests whose Host is 127.0.0.1, localhost or [::1] on its own port (DNS rebinding)
  * rejects requests whose Origin or Sec-Fetch-Site says they came from another site (CSRF)
  * the page itself is only served to a browser that holds the owner's access key (a 0600 file), so
    another user on the same machine cannot fetch it and lift the token
  * every /api call needs a per-run random token that is only handed to the page it serves
  * POST bodies must be application/json and are size capped and type validated
  * strict Content-Security-Policy with a per-response nonce, no inline event handlers, no third parties
"""
import argparse
import atexit
import hashlib
import hmac
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import store  # noqa: E402

VERSION = "0.1.0"
MAX_BODY = 64 * 1024
IMG_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
IMG_MAGIC = {".png": b"\x89PNG", ".jpg": b"\xff\xd8", ".jpeg": b"\xff\xd8", ".webp": b"RIFF", ".gif": b"GIF8"}
BLOCKED_SCHEMES = {"javascript", "data", "vbscript", "file", "blob"}
LAYER = r"(?:[0-9]|1[0-9]|2[0-3])"


def _str(n):
    return lambda v: isinstance(v, str) and len(v) <= n


def _url(v):
    if not isinstance(v, str) or len(v) > 2000:
        return False
    if v == "":
        return True
    m = re.match(r"^([a-z][a-z0-9+.\-]*)://", v, re.I)
    return bool(m) and m.group(1).lower() not in BLOCKED_SCHEMES


def _rules(v):
    return isinstance(v, list) and len(v) <= 100 and all(isinstance(x, str) and len(x) <= 500 for x in v)


# path pattern -> validator. Anything not listed here cannot be written from the browser.
WRITABLE = [
    (re.compile(r"^name$"), lambda v: isinstance(v, str) and 0 < len(v.strip()) <= 100),
    (re.compile(r"^persona$"), _str(2000)),
    (re.compile(r"^rules$"), _rules),
    (re.compile(r"^host\.(app|session_id)$"), _str(200)),
    (re.compile(r"^host\.open_command$"), _str(2000)),
    (re.compile(r"^host\.chat_url$"), _url),
    (re.compile(rf"^layers\.{LAYER}\.enabled$"), lambda v: isinstance(v, bool)),
    (re.compile(r"^(accounts|social|messaging)\.[a-z0-9_]+\.enabled$"), lambda v: isinstance(v, bool)),
]


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Handler(BaseHTTPRequestHandler):
    identity = None      # Path
    token = ""
    access_key = ""
    port = 0
    server_version = "Humanize"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    # ---- plumbing -------------------------------------------------------
    def _send(self, code, body, ctype="application/json", extra=None):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        if ctype.startswith("application/json"):
            self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, code, msg):
        self._send(code, {"error": msg})

    def _allowed_hosts(self):
        return {f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"[::1]:{self.port}"}

    def _guard(self, post=False, need_token=True):
        if self.headers.get("Host", "") not in self._allowed_hosts():
            self._fail(403, "bad host")
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {"http://" + h for h in self._allowed_hosts()}:
            self._fail(403, "bad origin")
            return False
        if post and self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
            self._fail(403, "cross-site request refused")
            return False
        if need_token:
            got = self.headers.get("X-Humanize-Token", "")
            if not secrets.compare_digest(got.encode(), self.token.encode()):
                self._fail(403, "bad token")
                return False
        return True

    def _json_body(self):
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._fail(415, "Content-Type must be application/json")
            return None
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._fail(400, "bad Content-Length")
            return None
        if n > MAX_BODY:
            self._fail(413, "request too large")
            return None
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            self._fail(400, "body is not valid JSON")
            return None
        if not isinstance(body, dict):
            self._fail(400, "body must be a JSON object")
            return None
        return body

    def _cookie_value(self):
        return hmac.new(self.access_key.encode(), b"hz-session-v1", hashlib.sha256).hexdigest()

    def _session_ok(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "hz" and secrets.compare_digest(v.encode(), self._cookie_value().encode()):
                return True
        return False

    def _locked(self):
        page = ("<!doctype html><meta charset=utf-8><title>Humanize</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:32rem;margin:15vh auto;padding:0 1rem}"
                "code{background:#0001;padding:2px 6px;border-radius:6px}</style><h1>Locked</h1>"
                "<p>This dashboard only opens for its owner. From a terminal on this machine run:</p><p><code>python3 humanize.py open</code></p>")
        self._send(401, page.encode(), "text/html; charset=utf-8", {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'", "Cache-Control": "no-store"})

    def _csp(self, nonce):
        return ("default-src 'none'; script-src 'self' 'nonce-%s'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; "
                "form-action 'none'; frame-ancestors 'none'" % nonce)

    # ---- GET ------------------------------------------------------------
    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == "/":
                if not self._guard(need_token=False):
                    return
                query = parse_qsl(urlsplit(self.path).query)
                given = dict(query).get("k")
                if given is not None:
                    if not secrets.compare_digest(given.encode(), self.access_key.encode()):
                        return self._locked()
                    rest = urlencode([(k, v) for k, v in query if k != "k"])
                    return self._send(302, b"", "text/plain", {
                        "Location": "/" + ("?" + rest if rest else ""), "Cache-Control": "no-store",
                        "Set-Cookie": f"hz={self._cookie_value()}; HttpOnly; SameSite=Strict; Path=/; Max-Age=7776000"})
                if not self._session_ok():
                    return self._locked()
                nonce = secrets.token_urlsafe(16)
                html = (HERE / "dashboard.html").read_text()
                html = html.replace("__HZ_TOKEN__", self.token).replace("__HZ_NONCE__", nonce)
                return self._send(200, html.encode(), "text/html; charset=utf-8",
                                  {"Content-Security-Policy": self._csp(nonce), "X-Frame-Options": "DENY", "Cache-Control": "no-store"})
            if path == "/orb.js":
                if not self._guard(need_token=False):
                    return
                return self._send(200, (HERE / "orb.js").read_bytes(), "text/javascript; charset=utf-8")
            m = re.match(r"^/fonts/([A-Za-z0-9_.\-]+\.(?:woff2|css))$", path)
            if m:
                if not self._guard(need_token=False):
                    return
                f = HERE / "fonts" / m.group(1)
                if not f.is_file():
                    return self._fail(404, "not found")
                ctype = "font/woff2" if f.suffix == ".woff2" else "text/css; charset=utf-8"
                return self._send(200, f.read_bytes(), ctype, {"Cache-Control": "public, max-age=604800"})
            if path == "/api/ping":
                if not self._guard(need_token=False):
                    return
                return self._send(200, {"app": "humanize", "version": VERSION})
            if path == "/avatar":
                if not self._guard(need_token=False):
                    return
                if not self._session_ok():
                    return self._fail(401, "open the dashboard with: python3 humanize.py open")
                return self._avatar()
            if path == "/api/identity":
                if not self._guard():
                    return
                d = store.load(self.identity)
                mtime = self.identity.stat().st_mtime_ns if self.identity.exists() else 0
                seed = store.get(d, "face.seed") or d.get("name") or "agent"
                return self._send(200, {"identity": store.mask(d), "mtime": mtime, "seed": seed, "version": VERSION, "app_dir": str(HERE.parent), "data_dir": str(self.identity.parent)})
            if path == "/api/self/status":
                if not self._guard():
                    return
                return self._self("status")
            return self._fail(404, "not found")
        except store.StoreError as e:
            return self._fail(500, str(e))
        except Exception as e:  # never leak a traceback to the browser
            sys.stderr.write(f"GET {path}: {e!r}\n")
            return self._fail(500, "internal error")

    def _avatar(self):
        d = store.load(self.identity)
        raw = store.get(d, "face.photo") or str(store.home() / "face.png")
        p = Path(os.path.expanduser(str(raw)))
        ext = p.suffix.lower()
        try:
            ok = ext in IMG_TYPES and p.is_file() and p.stat().st_size <= 5 * 1024 * 1024
            data = p.read_bytes() if ok else b""
        except OSError:
            ok, data = False, b""
        if not ok or not data.startswith(IMG_MAGIC[ext]):
            return self._fail(404, "no avatar")
        self._send(200, data, IMG_TYPES[ext], {"Cache-Control": "no-cache"})

    # ---- POST -----------------------------------------------------------
    def do_POST(self):
        path = urlsplit(self.path).path
        if not self._guard(post=True):
            return
        body = self._json_body()
        if body is None:
            return
        try:
            if path == "/api/update":
                return self._update(body)
            if path == "/api/request":
                return self._request(body)
            if path == "/api/request/done":
                return self._done(body)
            if path == "/api/chat":
                return self._chat()
            if path == "/api/self/push":
                return self._self("push")
            return self._fail(404, "not found")
        except store.StoreError as e:
            return self._fail(500, str(e))
        except Exception as e:
            sys.stderr.write(f"POST {path}: {e!r}\n")
            return self._fail(500, "internal error")

    def _update(self, body):
        path, value = body.get("path"), body.get("value")
        if not isinstance(path, str):
            return self._fail(400, "path must be a string")
        rule = next((r for pat, r in WRITABLE if pat.match(path)), None)
        if rule is None:
            return self._fail(400, f"field is not editable from the dashboard: {path}")
        if not rule(value):
            return self._fail(400, f"invalid value for {path}")
        if isinstance(value, str) and path != "host.open_command":
            value = value.strip()

        def apply(d):
            store.set_path(d, path, value)
            store.log_entry(d, f"dashboard set {path}", by="human")
        store.update(self.identity, apply)
        self._send(200, {"ok": True})

    def _request(self, body):
        text = body.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            return self._fail(400, "text must be 1 to 2000 characters")

        def apply(d):
            reqs = d.setdefault("dashboard_requests", [])
            reqs.append({"at": now(), "text": text.strip(), "done": False})
            if len(reqs) > 500:  # drop the oldest finished ones first
                keep = [r for r in reqs if not r.get("done")]
                done = [r for r in reqs if r.get("done")]
                d["dashboard_requests"] = (done[-(500 - len(keep)):] if len(keep) < 500 else []) + keep
        store.update(self.identity, apply)
        self._send(200, {"ok": True})

    def _done(self, body):
        i = body.get("index")
        if not isinstance(i, int) or isinstance(i, bool):
            return self._fail(400, "index must be an integer")
        err = []

        def apply(d):
            reqs = d.get("dashboard_requests", [])
            if not 0 <= i < len(reqs):
                err.append("no such request")
                return
            reqs[i]["done"] = True
        store.update(self.identity, apply)
        if err:
            return self._fail(400, err[0])
        self._send(200, {"ok": True})

    def _chat(self):
        d = store.load(self.identity)
        cmd = store.get(d, "host.open_command")
        if not cmd:
            return self._fail(400, "host.open_command is not set. Click Host and pick where your chat lives.")
        try:
            p = subprocess.Popen(cmd, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE, start_new_session=True, text=True)
        except OSError as e:
            return self._fail(500, f"could not run the command: {e}")
        try:
            _, err = p.communicate(timeout=2.5)
        except subprocess.TimeoutExpired:  # still running, e.g. a terminal window: that is success
            if p.stderr:
                p.stderr.close()
            return self._send(200, {"ok": True})
        if p.returncode != 0:
            detail = (err or "").strip().splitlines()[-1:] or [f"exit code {p.returncode}"]
            return self._fail(500, f"the command failed: {detail[0][:300]}")
        store.update(self.identity, lambda d: store.log_entry(d, "dashboard opened chat", by="human"))
        self._send(200, {"ok": True})

    def _self(self, action):
        env = dict(os.environ, HUMANIZE_HOME=str(self.identity.parent))
        try:
            r = subprocess.run([sys.executable, str(HERE / "self.py"), action], text=True, capture_output=True, env=env, timeout=180)
        except subprocess.TimeoutExpired:
            return self._fail(504, "timed out talking to the git remote")
        if action == "status":
            try:
                return self._send(200, json.loads(r.stdout))
            except ValueError:
                return self._send(200, {"initialized": False, "error": (r.stderr or r.stdout).strip()[:300]})
        if r.returncode:
            return self._fail(500, (r.stderr or r.stdout).strip()[:400] or "push failed")
        self._send(200, {"ok": True, "out": r.stdout.strip()[:400]})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identity", default=str(store.home() / "identity.json"))
    ap.add_argument("--port", type=int, default=4242, help="0 picks a free port")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    Handler.identity = Path(os.path.expanduser(a.identity)).resolve()
    Handler.token = secrets.token_urlsafe(32)
    keyfile = Handler.identity.parent / "dashboard.key"
    keyfile.parent.mkdir(parents=True, exist_ok=True)
    if keyfile.exists() and keyfile.read_text().strip():
        Handler.access_key = keyfile.read_text().strip()
    else:
        Handler.access_key = secrets.token_urlsafe(32)
        fd = os.open(str(keyfile), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(Handler.access_key)
    os.chmod(keyfile, 0o600)
    try:
        srv = Server(("127.0.0.1", a.port), Handler)
    except OSError as e:
        sys.exit(f"cannot listen on 127.0.0.1:{a.port}: {e}. Try --port 0 for a free port.")
    Handler.port = srv.server_address[1]

    info = Handler.identity.parent / "dashboard.json"
    info.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(info), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"pid": os.getpid(), "port": Handler.port, "token": Handler.token, "started": now(), "version": VERSION}, f)

    def cleanup(*_):
        try:
            info.unlink()
        except OSError:
            pass
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    url = f"http://127.0.0.1:{Handler.port}"
    print(f"Humanize dashboard on {url}  (identity: {Handler.identity})", flush=True)
    if not a.no_open:
        try:
            webbrowser.open(f"{url}/?k={Handler.access_key}")
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
