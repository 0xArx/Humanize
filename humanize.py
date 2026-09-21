#!/usr/bin/env python3
"""Humanize: give an AI agent everything a person has, and a dashboard to see it.

  init [--name N] [--persona P] [--port 4242] [--no-open]
        Create the identity from the template, draw the avatar, detect the host for the Open chat
        button, start the dashboard in the background and open it. Safe to re-run; never overwrites.
  status                     what the agent is and whether the dashboard is up
  doctor [--fix]             check this machine and the install; --fix adds keys new versions need
  dashboard [--port N]       run the dashboard in the foreground
  open                       open the dashboard in your browser (starts it if needed)
  stop                       stop the background dashboard
  avatar [seed]              (re)draw the avatar PNG
  self <init|push|pull|load|unlock|status> ...   keep the agent in a private git repo, load it anywhere
  demo                       a filled sample agent in a scratch folder, to see the dashboard

  memory add TEXT [--kind K] [--tags T]     remember something (local SQLite, no account)
  memory search QUERY [--limit N]           find it again
  memory person NAME [--handle H] [--notes N]   add or update someone it has met
  memory people                             who it knows

  For the agent, so it never hand-edits the identity file:
  get PATH                   print one value, e.g. get email.agentmail.address
  set PATH VALUE [--log T]   write one value; text stays text, lists, objects and booleans are parsed where the key expects them (--json forces JSON)
  log TEXT [--cost C]        append to the activity log
  requests [--all]           pending requests the human typed into the dashboard, as JSON
  done INDEX                 mark a request finished
  chat                       press the dashboard's Open chat button

Data lives in $HUMANIZE_HOME (default ~/.humanize). macOS and Linux; on Windows use WSL.
Standard library only. Pillow (for the avatar PNG) is installed on demand into ~/.humanize/pydeps.
"""
import argparse
import json
import os
import platform
import random
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
TEMPLATE = ROOT / "identity.template.json"
sys.path.insert(0, str(SCRIPTS))
import store  # noqa: E402

__version__ = "0.1.0"
LAYERS = range(0, 24)

FIRST = ["Ari", "Mira", "Tomas", "Noor", "Iris", "Kai", "Lena", "Omar", "Sana", "Jude", "Nadia", "Rafi", "Elio", "Zara", "Idris", "Maya"]
LAST = ["Vale", "Chen", "Reyes", "Haddad", "Okafor", "Lindqvist", "Moreau", "Tanaka", "Farouk", "Novak", "Mensah", "Karimi", "Silva", "Bakr", "Quinn", "Adeyemi"]


def die(msg, code=1):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def home():
    return store.home()


def ident_path():
    return home() / "identity.json"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_identity():
    try:
        return store.load(ident_path())
    except store.StoreError as e:
        die(str(e))


# ---------------------------------------------------------------- host + ports
def detect_host():
    system = platform.system()
    if system == "Darwin":
        if Path("/Applications/Claude.app").exists():
            return {"app": "claude-code-desktop", "open_command": 'open -a "Claude"', "chat_url": "", "session_id": ""}
        if Path("/Applications/Cursor.app").exists():
            return {"app": "cursor", "open_command": "open -a Cursor", "chat_url": "cursor://", "session_id": ""}
        return {"app": "claude-code-terminal", "open_command": "osascript -e 'tell app \"Terminal\" to do script \"claude --continue\"'", "chat_url": "", "session_id": ""}
    if system == "Linux":
        return {"app": "claude-code-terminal", "open_command": "x-terminal-emulator -e claude --continue", "chat_url": "", "session_id": ""}
    return {"app": "other", "open_command": "", "chat_url": "", "session_id": ""}


def port_free(port):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_port(start):
    for p in range(start, start + 40):
        if port_free(p):
            return p
    die(f"no free port between {start} and {start + 39}")


# Calls to the dashboard on this machine must never go through a proxy. urllib would otherwise honour
# http_proxy, VPN and macOS system proxy settings and fail to reach 127.0.0.1.
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def ping(port):
    try:
        with _LOCAL.open(f"http://127.0.0.1:{port}/api/ping", timeout=1.0) as r:
            return json.loads(r.read()).get("app") == "humanize"
    except Exception:
        return False


def dash_info():
    try:
        return json.loads((home() / "dashboard.json").read_text())
    except Exception:
        return None


def dash_alive():
    info = dash_info()
    return info if info and ping(info["port"]) else None


def open_in_browser(url):
    """The dashboard only opens for its owner: the URL carries the access key from a 0600 file."""
    try:
        key = (home() / "dashboard.key").read_text().strip()
    except OSError:
        key = ""
    if os.environ.get("HUMANIZE_NO_BROWSER"):   # tests, CI and headless servers
        return
    target = f"{url}/?k={key}" if key else url
    t = threading.Thread(target=lambda: webbrowser.open(target), daemon=True)   # some platforms block until a GUI app starts
    t.start()
    t.join(4)


def start_dashboard(port, open_browser):
    info = dash_alive()
    if info:
        url = f"http://127.0.0.1:{info['port']}"
    else:
        if not port_free(port):
            newp = find_port(port + 1)
            sys.stderr.write(f"port {port} is busy; using {newp}\n")
            port = newp
        (home() / "dashboard.json").unlink(missing_ok=True)
        logf = open(home() / "dashboard.log", "w")
        proc = subprocess.Popen([sys.executable, str(SCRIPTS / "dashboard.py"), "--identity", str(ident_path()), "--port", str(port), "--no-open"],
                                stdout=logf, stderr=logf, start_new_session=True)
        for _ in range(150):   # up to 15 seconds: slow disks and CI runners can take a few
            if proc.poll() is not None:
                tail = (home() / "dashboard.log").read_text().strip().splitlines()[-5:]
                die("the dashboard exited on start:\n  " + "\n  ".join(tail or ["(no output)"]))
            i = dash_info()
            if i and i.get("pid") == proc.pid and ping(i["port"]):
                port = i["port"]
                break
            time.sleep(0.1)
        else:
            die("the dashboard did not come up within 15 seconds; see " + str(home() / "dashboard.log"))
        url = f"http://127.0.0.1:{port}"
    if open_browser:
        open_in_browser(url)
    return url


# ---------------------------------------------------------------- avatar
def make_avatar(seed, out):
    """Returns the PNG path, or None if Pillow is unavailable. Pillow goes to ~/.humanize/pydeps."""
    cmd = [sys.executable, str(SCRIPTS / "avatar.py"), seed, str(out), "1024"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 3:
        pd = home() / "pydeps"
        pip = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--target", str(pd), "pillow"],
                             capture_output=True, text=True)
        if pip.returncode:
            sys.stderr.write("could not install Pillow: " + (pip.stderr.strip().splitlines() or ["unknown error"])[-1] + "\n")
            return None
        r = subprocess.run(cmd, capture_output=True, text=True)
    return str(out) if r.returncode == 0 else None


# ---------------------------------------------------------------- identity
def merge_missing(d, tpl, prefix=""):
    """Add keys that exist in tpl but not in d. Returns the dotted paths added."""
    added = []
    for k, v in tpl.items():
        if k not in d:
            d[k] = json.loads(json.dumps(v))
            added.append(prefix + k)
        elif isinstance(v, dict) and isinstance(d[k], dict) and v:
            added += merge_missing(d[k], v, prefix + k + ".")
    return added


def cmd_init(a):
    home().mkdir(parents=True, exist_ok=True)
    os.chmod(home(), 0o700)
    p = ident_path()
    if p.exists():
        d = load_identity()
        print(f"identity exists: {p}  ({d.get('name') or 'unnamed'})")
    else:
        d = json.loads(TEMPLATE.read_text())
        d["name"] = a.name or f"{random.choice(FIRST)} {random.choice(LAST)}"
        d["persona"] = a.persona or "Direct. Writes short messages. Ships small things fast."
        d["layers"] = {str(n): {"enabled": True} for n in LAYERS}
        store.log_entry(d, "identity created from template", by="humanize.py")
        if not a.name:
            store.log_entry(d, f"placeholder name {d['name']}; rename any time from the dashboard", by="humanize.py")
        store.save(p, d)
        print(f"identity created: {p}  ({d['name']})")

    def prepare(d):
        added = merge_missing(d, json.loads(TEMPLATE.read_text()))
        if added:
            store.log_entry(d, "identity gained keys from a newer version: " + ", ".join(added[:8]), by="humanize.py")
        if not store.get(d, "host.app"):
            d["host"] = detect_host()
            store.log_entry(d, f"host detected: {d['host']['app']}", by="humanize.py")
        if not store.get(d, "face.photo"):
            seed = store.get(d, "face.seed") or d["name"]
            out = make_avatar(seed, home() / "face.png")
            d["face"] = {"photo": out, "seed": seed}
            store.log_entry(d, "avatar drawn" if out else "avatar PNG skipped (no Pillow); the dashboard still draws it live", by="humanize.py")
    store.update(p, prepare)
    url = start_dashboard(a.port, not a.no_open)
    print(f"dashboard: {url}")
    print("next: the agent follows SKILL.md, section 'One-shot bootstrap'.")


def cmd_status(a):
    if not ident_path().exists():
        die("no identity yet. Run: python3 humanize.py init")
    d = load_identity()
    info = dash_alive()
    rows = [("version", __version__), ("data dir", str(home())), ("name", d.get("name")),
            ("email", store.get(d, "email.agentmail.address") or store.get(d, "email.mailgent.address")),
            ("phone", store.get(d, "phone.agentphone.number")), ("github", store.get(d, "accounts.github.username")),
            ("wallet", store.get(d, "wallet.mailgent_base_usdc")), ("self repo", store.get(d, "self_repo.url")),
            ("host", store.get(d, "host.app")),
            ("dashboard", f"http://127.0.0.1:{info['port']}" if info else "not running"),
            ("pending requests", len([r for r in d.get("dashboard_requests", []) if not r.get("done")]))]
    for k, v in rows:
        print(f"{k:>17}: {v if v not in (None, '') else '-'}")


def cmd_doctor(a):
    fails = warns = 0

    def row(level, text):
        nonlocal fails, warns
        fails += level == "fail"
        warns += level == "warn"
        print(f"  {level:<5} {text}")
    print(f"Humanize doctor v{__version__}")
    v = sys.version_info
    row("ok" if v >= (3, 9) else "fail", f"python {v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 9) else " (need 3.9 or newer)"))
    row("ok" if platform.system() in ("Darwin", "Linux") else "fail", f"platform {platform.system()}" + ("" if platform.system() in ("Darwin", "Linux") else " (use WSL)"))
    for tool, needed_for, hard in (("git", "storing the agent in a repo", False), ("openssl", "encrypting the agent for storage", False), ("node", "the Mailgent and Dial command line tools", False)):
        path = shutil.which(tool)
        row("ok" if path else "warn", f"{tool} {'found' if path else 'not found, needed for ' + needed_for}")
    pil = subprocess.run([sys.executable, "-c", f"import sys;sys.path.insert(0,{str(home() / 'pydeps')!r});import PIL;print(PIL.__version__)"], capture_output=True, text=True)
    row("ok" if pil.returncode == 0 else "warn", f"Pillow {pil.stdout.strip()}" if pil.returncode == 0 else "Pillow not installed; `python3 humanize.py avatar` installs it into ~/.humanize/pydeps")
    missing = [n for n in ("humanize.py", "identity.template.json", "SKILL.md", "scripts/dashboard.py", "scripts/dashboard.html", "scripts/orb.js", "scripts/store.py", "scripts/self.py", "scripts/avatar.py", "scripts/fonts/fonts.css")
               if not (ROOT / n).exists()]
    layer_docs = sorted((ROOT / "layers").glob("[0-9][0-9]-*.md"))
    row("ok" if not missing and len(layer_docs) == 24 else "fail", "install files complete" if not missing and len(layer_docs) == 24 else f"install incomplete: missing {missing or ''} layer docs {len(layer_docs)}/24")
    if home().exists():
        mode = home().stat().st_mode & 0o777
        row("ok" if mode == 0o700 else "warn", f"data dir {home()} mode {oct(mode)[2:]}" + ("" if mode == 0o700 else " (should be 700; init fixes it)"))
    p = ident_path()
    if not p.exists():
        row("warn", "no identity yet; run `python3 humanize.py init`")
    else:
        try:
            d = store.load(p)
            mode = p.stat().st_mode & 0o777
            row("ok" if mode == 0o600 else "warn", f"identity.json valid, mode {oct(mode)[2:]}" + ("" if mode == 0o600 else " (should be 600)"))
            if mode != 0o600 and a.fix:
                os.chmod(p, 0o600)
                print("        fixed mode")
            added = merge_missing(json.loads(json.dumps(d)), json.loads(TEMPLATE.read_text()))
            if added:
                row("warn", f"identity is missing {len(added)} keys added in newer versions" + ("" if a.fix else " (run doctor --fix)"))
                if a.fix:
                    store.update(p, lambda d: (merge_missing(d, json.loads(TEMPLATE.read_text())), store.log_entry(d, "doctor added missing keys", by="humanize.py")))
                    print("        added them")
            else:
                row("ok", "identity has every key this version knows")
        except store.StoreError as e:
            row("fail", str(e))
    info = dash_alive()
    row("ok" if info else "warn", f"dashboard running at http://127.0.0.1:{info['port']} (pid {info['pid']})" if info else "dashboard not running; `python3 humanize.py init` starts it")
    print(f"\n{fails} problem(s), {warns} warning(s)")
    sys.exit(1 if fails else 0)


def cmd_open(a):
    info = dash_alive()
    url = f"http://127.0.0.1:{info['port']}" if info else start_dashboard(4242, False)
    open_in_browser(url)
    print(url)


def cmd_stop(a):
    info = dash_info()
    if not info:
        print("no background dashboard recorded")
        return
    try:
        os.kill(info["pid"], signal.SIGTERM)
        for _ in range(30):
            if not ping(info["port"]):
                break
            time.sleep(0.1)
        print("stopped")
    except ProcessLookupError:
        print("was not running")
    (home() / "dashboard.json").unlink(missing_ok=True)


def cmd_dashboard(a):
    os.execv(sys.executable, [sys.executable, str(SCRIPTS / "dashboard.py"), "--identity", str(ident_path()), "--port", str(a.port)] + (["--no-open"] if a.no_open else []))


def cmd_avatar(a):
    d = store.load(ident_path()) if ident_path().exists() else {}
    seed = a.seed or store.get(d, "face.seed") or d.get("name") or "agent"
    home().mkdir(parents=True, exist_ok=True)
    out = make_avatar(seed, home() / "face.png")
    if not out:
        die("could not write the PNG (Pillow missing and could not be installed). The dashboard still draws the avatar live.")
    print(out)
    if ident_path().exists():
        store.update(ident_path(), lambda d: d.__setitem__("face", {"photo": out, "seed": store.get(d, "face.seed") or seed}))


def cmd_self(a):
    env = dict(os.environ, HUMANIZE_HOME=str(home()))
    sys.exit(subprocess.call([sys.executable, str(SCRIPTS / "self.py")] + a.args, env=env))


# ---------------------------------------------------------------- agent helpers
def cmd_get(a):
    v = store.get(load_identity(), a.path)
    if v is None:
        sys.exit(1)
    print(v if isinstance(v, str) else json.dumps(v))


def coerce(path, raw, force_json=False):
    """Turn the text from the command line into the right JSON type for that key.

    The identity template says what a key holds. Text stays text (so `set host.open_command true` stores the
    word, not a boolean). Booleans, lists and objects are parsed where the key expects them, and an
    impossible value is an error rather than something stored wrongly. A key the template does not know is
    text, unless it is a JSON list or object. --json parses whatever it is given."""
    try:
        parsed, valid = json.loads(raw), True
    except ValueError:
        parsed, valid = None, False
    if force_json:
        if not valid:
            raise store.StoreError(f"{raw!r} is not valid JSON")
        return parsed
    if re.fullmatch(r"layers\.\d+\.enabled|(accounts|social|messaging)\.[a-z0-9_]+\.enabled", path):
        expected = False
    else:
        expected = store.get(json.loads(TEMPLATE.read_text()), path)
    for kind, name in ((bool, "true or false"), (list, "a JSON list"), (dict, "a JSON object")):
        if isinstance(expected, kind):
            if not (valid and isinstance(parsed, kind)):
                raise store.StoreError(f"{path} expects {name}, got {raw!r}")
            return parsed
    if expected is None or isinstance(expected, str):
        return parsed if valid and isinstance(parsed, (dict, list)) and expected is None else raw
    return parsed if valid else raw


def cmd_set(a):
    try:
        value = coerce(a.path, a.value, a.json)
    except store.StoreError as e:
        die(str(e))

    def apply(d):
        store.set_path(d, a.path, value)
        if a.log:
            store.log_entry(d, a.log, by="agent")
    try:
        store.update(ident_path(), apply)
    except store.StoreError as e:
        die(str(e))


def cmd_log(a):
    store.update(ident_path(), lambda d: store.log_entry(d, a.text, cost=a.cost, by="agent"))


def cmd_requests(a):
    reqs = [dict(index=i, **r) for i, r in enumerate(load_identity().get("dashboard_requests", []))]
    print(json.dumps(reqs if a.all else [r for r in reqs if not r.get("done")], indent=2))


def cmd_done(a):
    def apply(d):
        reqs = d.get("dashboard_requests", [])
        if not 0 <= a.index < len(reqs):
            raise store.StoreError(f"no request {a.index}")
        reqs[a.index]["done"] = True
        store.log_entry(d, f"finished request: {reqs[a.index]['text'][:80]}", by="agent")
    try:
        store.update(ident_path(), apply)
    except store.StoreError as e:
        die(str(e))


def cmd_chat(a):
    info = dash_alive()
    if not info:
        die("the dashboard is not running. Run: python3 humanize.py init")
    req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/chat", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json", "X-Humanize-Token": info["token"]})
    try:
        with _LOCAL.open(req, timeout=10) as r:
            print(r.read().decode())
    except urllib.error.HTTPError as e:
        die(json.loads(e.read() or b"{}").get("error", str(e)))


def cmd_memory(a):
    import memory
    try:
        if a.mcmd == "add":
            out = {"id": memory.add(a.text, a.kind, a.tags)}
        elif a.mcmd == "search":
            out = memory.search(a.query, a.limit)
        elif a.mcmd == "person":
            out = {"id": memory.person(a.name, a.handle, a.notes)}
        else:
            out = memory.people()
    except ValueError as e:
        die(str(e))
    if ident_path().exists() and not store.get(load_identity(), "memory.local"):
        store.update(ident_path(), lambda d: store.set_path(d, "memory.local", str(memory.db_path())))
    print(json.dumps(out, indent=2))


def cmd_demo(a):
    demo = Path(os.path.expanduser("~/.humanize-demo"))
    demo.mkdir(parents=True, exist_ok=True)
    os.environ["HUMANIZE_HOME"] = str(demo)
    d = json.loads(TEMPLATE.read_text())
    d.update(name="Ari Vale", persona="Software engineer. Direct, writes short emails, ships small things fast.",
             did="did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK")
    d["email"] = {"mailgent": {"address": "bright-otter-k3f9@mailgent.dev", "api_key": "mgnt-demo0000000000"},
                  "agentmail": {"address": "ari.vale@agentmail.to", "api_key": "am_demo000000"}}
    d["phone"]["agentphone"] = {"number": "+14155550123", "number_id": "num_01", "agent_id": "agt_01", "api_key": "ap_demo0000"}
    d["messaging"] = {"telegram": {"token": "123456:demo"}}
    d["wallet"]["mailgent_base_usdc"] = "0x4b7C1a9E2f3D4c5B6a7F8e9D0c1B2a3F4e5D6c7B"
    d["browser"] = {"provider": "claude-browser"}
    d["accounts"] = {"github": {"username": "arivale", "vault": "github"}, "vercel": {"token": "vcp_demo"}}
    d["voice"] = {"agentphone": "voice_rachel", "tts": "edge-tts"}
    d["eyes"] = {"search": "host web tools", "weather": "open-meteo"}
    d["computer"] = {"provider": "docker", "id": "ari-box"}
    d["memory"]["supabase"] = "abcdefghijklmnop"
    d["social"] = {"x": {"handle": "arivale", "token": "demo"}}
    d["calendar"]["booking_url"] = "https://cal.com/ari-vale/15min"
    d["self_repo"] = {"url": "https://github.com/arivale/self.git", "last_push": now()}
    d["host"] = detect_host() or {"app": "other", "open_command": "", "chat_url": "", "session_id": ""}
    d["layers"] = {str(n): {"enabled": n != 14} for n in LAYERS}
    d["rules"] = ["Monthly spend cap 50 USD."]
    d["dashboard_requests"] = [{"at": now(), "text": "Get a UK number.", "done": False}]
    for did in ("mailgent agent-signup", "agentmail inbox ari.vale verified", "agentphone number +14155550123"):
        store.log_entry(d, did, by="agent")
    d["face"] = {"photo": make_avatar("Ari Vale", demo / "face.png"), "seed": "Ari Vale"}
    store.save(demo / "identity.json", d)
    port = a.port if port_free(a.port) else find_port(a.port + 1)
    print(f"demo identity in {demo}. Ctrl-C to stop.")
    os.execv(sys.executable, [sys.executable, str(SCRIPTS / "dashboard.py"), "--identity", str(demo / "identity.json"), "--port", str(port)] + (["--no-open"] if a.no_open else []))


def main():
    if os.name == "nt":
        die("Humanize supports macOS and Linux. On Windows, run it inside WSL.")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"humanize {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    def add(name, fn, **kw):
        p = sub.add_parser(name, **kw)
        p.set_defaults(f=fn)
        return p
    p = add("init", cmd_init); p.add_argument("--name"); p.add_argument("--persona"); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true")
    add("status", cmd_status)
    p = add("doctor", cmd_doctor); p.add_argument("--fix", action="store_true")
    p = add("dashboard", cmd_dashboard); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true")
    add("open", cmd_open)
    add("stop", cmd_stop)
    p = add("avatar", cmd_avatar); p.add_argument("seed", nargs="?")
    p = add("self", cmd_self); p.add_argument("args", nargs=argparse.REMAINDER)
    p = add("demo", cmd_demo); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true")
    p = add("get", cmd_get); p.add_argument("path")
    p = add("set", cmd_set); p.add_argument("path"); p.add_argument("value"); p.add_argument("--log"); p.add_argument("--json", action="store_true", help="parse VALUE as JSON whatever the key")
    p = add("log", cmd_log); p.add_argument("text"); p.add_argument("--cost")
    p = add("requests", cmd_requests); p.add_argument("--all", action="store_true")
    p = add("done", cmd_done); p.add_argument("index", type=int)
    add("chat", cmd_chat)
    p = add("memory", cmd_memory)
    msub = p.add_subparsers(dest="mcmd", required=True)
    m = msub.add_parser("add"); m.add_argument("text"); m.add_argument("--kind", default="note"); m.add_argument("--tags", default="")
    m = msub.add_parser("search"); m.add_argument("query", nargs="?", default=""); m.add_argument("--limit", type=int, default=10)
    m = msub.add_parser("person"); m.add_argument("name"); m.add_argument("--handle"); m.add_argument("--notes")
    msub.add_parser("people")
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return
    a.f(a)


if __name__ == "__main__":
    main()
