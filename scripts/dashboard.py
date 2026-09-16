#!/usr/bin/env python3
"""Humanize dashboard: a local web page to see and steer the humanized agent.

Usage: python3 scripts/dashboard.py [--identity ~/.humanize/identity.json] [--port 4242]
Stdlib only. Serves scripts/dashboard.html, reads and writes the identity file,
masks secrets before they reach the browser, and runs host.open_command for the Chat button.
"""
import argparse, json, os, re, subprocess, sys, time, webbrowser
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRET_KEYS = re.compile(r"(api_key|apikey|token|secret|password|private|mnemonic|recovery|^auth$|^pat$|_key$|^key$)", re.I)

def load(p):
    if not p.exists():
        return {"name": "", "persona": "", "rules": [], "log": [], "layers": {}, "dashboard_requests": [], "host": {}}
    return json.loads(p.read_text() or "{}")

def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(p)

def mask(v, k=""):
    if isinstance(v, dict):
        return {kk: mask(vv, kk) for kk, vv in v.items()}
    if isinstance(v, list):
        return [mask(x, k) for x in v]
    if isinstance(v, str) and SECRET_KEYS.search(k) and len(v) > 6 and not v.startswith("~") and "/" not in v:
        return v[:3] + "…" + v[-3:]
    return v

def set_path(d, path, value):
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value

ALLOWED = re.compile(r"^(name|persona|rules|host\.(app|open_command|session_id)|layers\.[0-9]+\.(enabled|note)|accounts\.[a-z0-9_]+\.enabled|social\.[a-z0-9_]+\.enabled|messaging\.[a-z0-9_]+\.enabled)$")

class H(BaseHTTPRequestHandler):
    identity = None
    def log_message(self, *a): pass
    def send(self, code, body, ctype="application/json"):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")
    def do_GET(self):
        self.path = urlsplit(self.path).path
        if self.path == "/":
            return self.send(200, (HERE / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/identity":
            d = load(self.identity)
            return self.send(200, {"identity": mask(d), "path": str(self.identity), "mtime": self.identity.stat().st_mtime if self.identity.exists() else 0})
        if self.path == "/avatar":
            d = load(self.identity)
            p = Path(os.path.expanduser((d.get("face") or {}).get("photo") or "~/.humanize/face.png"))
            if p.exists():
                return self.send(200, p.read_bytes(), "image/png")
            return self.send(404, {"error": "no avatar yet"})
        self.send(404, {"error": "not found"})
    def do_POST(self):
        self.path = urlsplit(self.path).path
        d = load(self.identity); b = self.body()
        if self.path == "/api/update":
            path, value = b.get("path", ""), b.get("value")
            if not ALLOWED.match(path):
                return self.send(400, {"error": f"field not editable from dashboard: {path}"})
            set_path(d, path, value)
            d.setdefault("log", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "did": f"dashboard set {path}", "by": "human"})
            save(self.identity, d); return self.send(200, {"ok": True})
        if self.path == "/api/request":
            text = (b.get("text") or "").strip()
            if not text: return self.send(400, {"error": "empty"})
            d.setdefault("dashboard_requests", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "text": text, "done": False})
            save(self.identity, d); return self.send(200, {"ok": True})
        if self.path == "/api/request/done":
            i = b.get("index")
            try: d["dashboard_requests"][i]["done"] = True
            except Exception: return self.send(400, {"error": "bad index"})
            save(self.identity, d); return self.send(200, {"ok": True})
        if self.path == "/api/chat":
            cmd = (d.get("host") or {}).get("open_command")
            if not cmd:
                return self.send(400, {"error": "host.open_command is not set. The agent sets it during setup (see SKILL.md, Layer 22)."})
            try:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self.send(200, {"ok": True, "ran": cmd})
            except Exception as e:
                return self.send(500, {"error": str(e)})
        self.send(404, {"error": "not found"})

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity", default="~/.humanize/identity.json")
    ap.add_argument("--port", type=int, default=4242)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    H.identity = Path(os.path.expanduser(a.identity))
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}"
    print(f"Humanize dashboard on {url}  (identity: {H.identity})", flush=True)
    if not a.no_open:
        try: webbrowser.open(url)
        except Exception: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
