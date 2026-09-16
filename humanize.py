#!/usr/bin/env python3
"""Humanize: one command from clone to a running, filled dashboard.

  python3 humanize.py init [--name "Ari Vale"] [--persona "..."] [--port 4242] [--no-open]
      Creates ~/.humanize/identity.json from the template, picks a name if none is given,
      draws the avatar, detects the host for the Open chat button, starts the dashboard
      in the background, and opens it. Safe to re-run: never overwrites an existing identity.

  python3 humanize.py dashboard [--port 4242] [--no-open]   run the dashboard in the foreground
  python3 humanize.py stop                                   stop the background dashboard
  python3 humanize.py status                                 what the agent is and whether the dashboard runs
  python3 humanize.py avatar [seed]                          (re)draw the avatar PNG
  python3 humanize.py self <init|push|pull|load|status> ...  store or load the agent in its private repo
  python3 humanize.py demo [--port 4242]                     a filled sample identity in a scratch home, to see it

Stdlib only. Pillow is optional (used for the avatar PNG; the dashboard draws the live one without it).
"""
import argparse, json, os, platform, random, shutil, signal, socket, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
TEMPLATE = ROOT / "identity.template.json"

def home(): return Path(os.path.expanduser("~/.humanize"))
def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

FIRST = ["Ari", "Mira", "Tomas", "Noor", "Iris", "Kai", "Lena", "Omar", "Sana", "Jude", "Nadia", "Rafi", "Elio", "Zara", "Idris", "Maya"]
LAST = ["Vale", "Chen", "Reyes", "Haddad", "Okafor", "Lindqvist", "Moreau", "Tanaka", "Farouk", "Novak", "Mensah", "Karimi", "Silva", "Bakr", "Quinn", "Adeyemi"]

def log(d, did, **kw): d.setdefault("log", []).append({"at": now(), "did": did, **kw})

def save(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(d, indent=2)); os.chmod(tmp, 0o600); tmp.replace(p)

def detect_host():
    sysname = platform.system()
    if sysname == "Darwin":
        if Path("/Applications/Claude.app").exists():
            return {"app": "claude-code-desktop", "open_command": 'open -a "Claude"', "chat_url": "", "session_id": ""}
        if Path("/Applications/Cursor.app").exists():
            return {"app": "cursor", "open_command": "open -a Cursor", "chat_url": "cursor://", "session_id": ""}
        return {"app": "claude-code-terminal", "open_command": "osascript -e 'tell app \"Terminal\" to do script \"claude --continue\"'", "chat_url": "", "session_id": ""}
    if sysname == "Linux":
        return {"app": "claude-code-terminal", "open_command": "x-terminal-emulator -e claude --continue", "chat_url": "", "session_id": ""}
    return {"app": "other", "open_command": "", "chat_url": "", "session_id": ""}

def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0

def draw_avatar(seed, out):
    try:
        import PIL  # noqa
    except ImportError:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "pillow"], capture_output=True, text=True)
        if r.returncode:
            return None
    r = subprocess.run([sys.executable, str(SCRIPTS / "avatar.py"), seed, str(out), "1024"], capture_output=True, text=True)
    return str(out) if r.returncode == 0 else None

def start_dashboard(identity, port, open_browser=True):
    if port_open(port):
        url = f"http://127.0.0.1:{port}"
    else:
        p = subprocess.Popen([sys.executable, str(SCRIPTS / "dashboard.py"), "--identity", str(identity), "--port", str(port), "--no-open"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        (home() / "dashboard.json").write_text(json.dumps({"pid": p.pid, "port": port}))
        for _ in range(40):
            if port_open(port): break
            time.sleep(0.1)
        url = f"http://127.0.0.1:{port}"
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    return url

def cmd_init(a):
    H = home(); H.mkdir(parents=True, exist_ok=True); os.chmod(H, 0o700)
    ident = H / "identity.json"
    if ident.exists():
        d = json.loads(ident.read_text())
        print(f"identity exists: {ident}  ({d.get('name') or 'unnamed'})")
    else:
        d = json.loads(TEMPLATE.read_text())
        d["name"] = a.name or f"{random.choice(FIRST)} {random.choice(LAST)}"
        d["persona"] = a.persona or "Direct. Writes short messages. Ships small things fast."
        d["layers"] = {str(n): {"enabled": True} for n in range(0, 24)}
        log(d, "identity created from template", by="humanize.py")
        if not a.name: log(d, f"placeholder name {d['name']}; rename any time from the dashboard", by="humanize.py")
        save(ident, d)
        print(f"identity created: {ident}  ({d['name']})")
    changed = False
    if not (d.get("host") or {}).get("app"):
        d["host"] = detect_host(); log(d, f"host detected: {d['host']['app']}", by="humanize.py"); changed = True
    if not (d.get("face") or {}).get("photo"):
        seed = (d.get("face") or {}).get("seed") or d["name"]
        out = draw_avatar(seed, H / "face.png")
        d["face"] = {"photo": out, "seed": seed}
        log(d, "avatar drawn" if out else "avatar skipped (no Pillow); dashboard draws it live", by="humanize.py"); changed = True
    if changed: save(ident, d)
    url = start_dashboard(ident, a.port, not a.no_open)
    print(f"dashboard: {url}")
    print("next for the agent: follow SKILL.md, One-shot bootstrap, from step 3 (Mailgent signup).")

def cmd_dashboard(a):
    os.execv(sys.executable, [sys.executable, str(SCRIPTS / "dashboard.py"), "--port", str(a.port)] + (["--no-open"] if a.no_open else []))

def cmd_stop(a):
    pf = home() / "dashboard.json"
    if not pf.exists(): print("no background dashboard recorded"); return
    try: os.kill(json.loads(pf.read_text())["pid"], signal.SIGTERM); print("stopped")
    except (ProcessLookupError, KeyError, ValueError): print("was not running")
    pf.unlink(missing_ok=True)

def cmd_status(a):
    ident = home() / "identity.json"
    if not ident.exists(): print("no identity yet. run: python3 humanize.py init"); return
    d = json.loads(ident.read_text())
    have = lambda *ps: any(_get(d, p) for p in ps)
    rows = [("name", d.get("name")), ("email", _get(d, "email.agentmail.address") or _get(d, "email.mailgent.address")), ("phone", _get(d, "phone.agentphone.number")),
            ("github", _get(d, "accounts.github.username")), ("wallet", _get(d, "wallet.mailgent_base_usdc")), ("self repo", _get(d, "self_repo.url")),
            ("host", _get(d, "host.app")), ("dashboard", _dash_status()), ("pending requests", len([r for r in d.get("dashboard_requests", []) if not r.get("done")]))]
    for k, v in rows: print(f"{k:>17}: {v if v not in (None, '') else '-'}")

def _dash_status():
    pf = home() / "dashboard.json"
    port = 4242
    try: port = json.loads(pf.read_text())["port"]
    except Exception: pass
    return f"running on http://127.0.0.1:{port}" if port_open(port) else "not running"

def _get(d, p):
    for k in p.split("."):
        d = d.get(k) if isinstance(d, dict) else None
        if d is None: return None
    return d

def cmd_avatar(a):
    ident = home() / "identity.json"
    d = json.loads(ident.read_text()) if ident.exists() else {}
    seed = a.seed or (d.get("face") or {}).get("seed") or d.get("name") or "agent"
    out = draw_avatar(seed, home() / "face.png")
    print(out or "Pillow missing and could not be installed")
    if out and ident.exists():
        d["face"] = {"photo": out, "seed": seed}; save(ident, d)

def cmd_self(a):
    os.execv(sys.executable, [sys.executable, str(SCRIPTS / "self.py")] + a.args)

def cmd_demo(a):
    scratch = Path(os.path.expanduser("~/.humanize-demo")); scratch.mkdir(exist_ok=True)
    d = json.loads(TEMPLATE.read_text())
    d.update({"name": "Ari Vale", "persona": "Software engineer. Direct, writes short emails, ships small things fast.", "did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"})
    d["email"] = {"mailgent": {"address": "bright-otter-k3f9@mailgent.dev", "api_key": "mgnt-demo0000000000"}, "agentmail": {"address": "ari.vale@agentmail.to", "api_key": "am_demo000000"}}
    d["phone"]["agentphone"] = {"number": "+14155550123", "number_id": "num_01", "agent_id": "agt_01", "api_key": "ap_demo0000"}
    d["messaging"] = {"telegram": {"token": "123456:demo"}}
    d["wallet"]["mailgent_base_usdc"] = "0x4b7C1a9E2f3D4c5B6a7F8e9D0c1B2a3F4e5D6c7B"
    d["browser"] = {"provider": "claude-browser"}
    d["accounts"] = {"github": {"username": "arivale", "vault": "github", "created": now()[:10]}, "vercel": {"token": "vcp_demo"}, "supabase": {"pat": "sbp_demo"}}
    d["voice"]["agentphone"] = "voice_rachel"; d["computer"] = {"provider": "smolmachines", "id": "m_7781"}; d["memory"]["supabase"] = "abcdefghijklmnop"
    d["social"] = {"x": {"handle": "arivale", "token": "demo"}}; d["calendar"]["booking_url"] = "https://cal.com/ari-vale/15min"
    d["self_repo"] = {"url": "https://github.com/arivale/self.git", "last_push": now()}
    d["host"] = {"app": "claude-code-desktop", "open_command": "echo demo", "chat_url": "", "session_id": "demo"}
    d["layers"] = {str(n): {"enabled": n != 14} for n in range(0, 24)}
    d["rules"] = ["Monthly spend cap 50 USD."]; d["dashboard_requests"] = [{"at": now(), "text": "Get a UK number.", "done": False}]
    for did in ["mailgent agent-signup", "agentmail inbox ari.vale verified", "agentphone number +14155550123"]: log(d, did)
    face = draw_avatar("Ari Vale", scratch / "face.png"); d["face"] = {"photo": face, "seed": "Ari Vale"}
    save(scratch / "identity.json", d)
    print(f"demo identity: {scratch / 'identity.json'}")
    os.execv(sys.executable, [sys.executable, str(SCRIPTS / "dashboard.py"), "--identity", str(scratch / "identity.json"), "--port", str(a.port)])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("init"); p.add_argument("--name"); p.add_argument("--persona"); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true"); p.set_defaults(f=cmd_init)
    p = sub.add_parser("dashboard"); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true"); p.set_defaults(f=cmd_dashboard)
    p = sub.add_parser("stop"); p.set_defaults(f=cmd_stop)
    p = sub.add_parser("status"); p.set_defaults(f=cmd_status)
    p = sub.add_parser("avatar"); p.add_argument("seed", nargs="?"); p.set_defaults(f=cmd_avatar)
    p = sub.add_parser("self"); p.add_argument("args", nargs=argparse.REMAINDER); p.set_defaults(f=cmd_self)
    p = sub.add_parser("demo"); p.add_argument("--port", type=int, default=4242); p.set_defaults(f=cmd_demo)
    a = ap.parse_args()
    if not a.cmd: ap.print_help(); sys.exit(0)
    a.f(a)
