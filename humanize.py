#!/usr/bin/env python3
"""Humanize: give an AI agent everything a person has, and a dashboard to see it.

  init [--profile ID] [--name N] [--persona P] [--port 4242] [--no-open]
        Create the identity from the template, draw the avatar, detect the host for the Open chat
        button, start the dashboard in the background and open it. Safe to re-run; never overwrites.
        --profile starts from a ready-made profile (name, persona, card, layers, rules); see `profiles`.
  profiles                   list the ready-made profiles
  status                     what the agent is and whether the dashboard is up
  doctor [--fix]             check this machine and the install; --fix adds keys new versions need
  dashboard [--port N]       run the dashboard in the foreground
  open                       open the dashboard in your browser (starts it if needed)
  stop                       stop the background dashboard
  avatar [seed]              (re)draw the avatar PNG
  card [--out DIR] [--title T] [--tagline T] [--website URL] [--vcard] [--open]
        generate a print-ready business card (front.png, back.png, card.pdf, card.vcf)
  self <init|push|pull|load|unlock|status> ...   keep the agent in a private git repo, load it anywhere
  demo [--profile ID]        a filled sample agent in a scratch folder, to see the dashboard

  memory add TEXT [--kind K] [--tags T]     remember something (local SQLite, no account)
  memory search QUERY [--limit N]           find it again
  memory person NAME [--handle H] [--notes N]   add or update someone it has met
  memory people                             who it knows

  secret backend|list|get|set|delete|migrate   the operating system's secret store (Keychain on macOS)
  totp new [name] | code SECRET-OR-NAME | uri SECRET LABEL   local 2FA codes, RFC 6238, no vendor
  calendar add|list|delete ...       a local iCalendar file (~/.humanize/calendar.ics), no account

  For the agent, so it never hand-edits the identity file:
  get PATH [--pointer]       print one value, e.g. get email.agentmail.address; a stored secret is fetched for you
  set PATH VALUE [--log T]   write one value; keys that hold secrets (api_key, token, password ...) go to the
                             secret store and leave a pointer in the identity (--plain keeps them in the file); text stays text, lists, objects and booleans are parsed where the key expects them (--json forces JSON)
  log TEXT [--cost C]        append to the activity log
  requests [--all]           pending requests the human typed into the dashboard, as JSON
  done INDEX                 mark a request finished
  chat                       press the dashboard's Open chat button

Data lives in $HUMANIZE_HOME (default ~/.humanize). macOS and Linux; on Windows use WSL.
Standard library only. Pillow (for the avatar and card PNGs) is installed on demand into ~/.humanize/pydeps.
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
PROFILES = ROOT / "profiles"
sys.path.insert(0, str(SCRIPTS))
import keystore  # noqa: E402
import store  # noqa: E402

__version__ = "0.4.2"
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
            tail = (home() / "dashboard.log").read_text().strip().splitlines()[-3:]
            die("the dashboard did not answer within 15 seconds"
                + (" (its process is still running)" if proc.poll() is None else "")
                + ". Its log, " + str(home() / "dashboard.log") + ":\n  " + "\n  ".join(tail or ["(empty)"]))
        url = f"http://127.0.0.1:{port}"
    if open_browser:
        open_in_browser(url)
    return url


# ---------------------------------------------------------------- avatar
def _ensure_pillow():
    """Ensure Pillow is in ~/.humanize/pydeps. Returns True on success."""
    pd = home() / "pydeps"
    test = subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(pd)!r}); import PIL"],
        capture_output=True)
    if test.returncode == 0:
        return True
    sys.stderr.write("Pillow not found. Installing into ~/.humanize/pydeps...\n")
    pip = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
         "--target", str(pd), "pillow"],
        capture_output=True, text=True)
    if pip.returncode:
        sys.stderr.write("could not install Pillow: " +
                         (pip.stderr.strip().splitlines() or ["unknown error"])[-1] + "\n")
        return False
    return True


def make_avatar(seed, out):
    """Returns the PNG path, or None if Pillow is unavailable. Pillow goes to ~/.humanize/pydeps."""
    cmd = [sys.executable, str(SCRIPTS / "avatar.py"), seed, str(out), "1024"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 3:
        if not _ensure_pillow():
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


def list_profiles():
    return [json.loads(f.read_text()) for f in sorted(PROFILES.glob("*.json"))]


def load_profile(pid):
    for prof in list_profiles():
        if prof["id"] == pid:
            return prof
    die(f"no profile '{pid}'. Choose one of: " + ", ".join(x["id"] for x in list_profiles()))


def apply_profile(d, prof, name=None, persona=None):
    """Fill a new identity from a ready-made profile. Explicit --name and --persona win."""
    d["name"] = name or prof["name"]
    d["persona"] = persona or prof["persona"]
    d["profile"] = prof["id"]
    d["business_card"].update({k: v for k, v in prof.get("business_card", {}).items() if v})
    on = set(prof["layers"])
    d["layers"] = {str(n): {"enabled": n in on} for n in LAYERS}
    d["rules"] = list(prof.get("rules", []))


def cmd_profiles(a):
    for prof in list_profiles():
        print(f"{prof['id']:<12} {prof['label']}: {prof['summary']}")
    print("\nuse one: python3 humanize.py init --profile <id> [--name \"Your Agent\"]")


def cmd_init(a):
    home().mkdir(parents=True, exist_ok=True)
    os.chmod(home(), 0o700)
    p = ident_path()
    prof = load_profile(a.profile) if a.profile else None
    if p.exists():
        d = load_identity()
        print(f"identity exists: {p}  ({d.get('name') or 'unnamed'})")
        if prof:
            print("profile not applied: it only fills a new identity, and this one already exists")
    elif prof:
        d = json.loads(TEMPLATE.read_text())
        apply_profile(d, prof, a.name, a.persona)
        store.log_entry(d, f"identity created from the {prof['label']} profile", by="humanize.py")
        store.save(p, d)
        print(f"identity created: {p}  ({d['name']}, {prof['label']})")
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
    _name = d.get("name") or ""
    _email = store.get(d, "email.agentmail.address")
    _phone = store.get(d, "phone.agentphone.number")
    if _name and (_email or _phone):
        _card = "ready"
    elif not _name:
        _card = "missing name"
    else:
        _card = "missing email and phone"
    rows = [("version", __version__), ("data dir", str(home())), ("name", _name or None),
            ("email", _email),
            ("phone", _phone), ("github", store.get(d, "accounts.github.username")),
            ("wallet", store.get(d, "wallet.evm.address")), ("self repo", store.get(d, "self_repo.url")),
            ("host", store.get(d, "host.app")),
            ("business card", _card),
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
    for tool, needed_for, hard in (("git", "storing the agent in a repo", False), ("openssl", "encrypting the agent for storage", False), ("node", "the Dial command line tool", False)):
        path = shutil.which(tool)
        row("ok" if path else "warn", f"{tool} {'found' if path else 'not found, needed for ' + needed_for}")
    pil = subprocess.run([sys.executable, "-c", f"import sys;sys.path.insert(0,{str(home() / 'pydeps')!r});import PIL;print(PIL.__version__)"], capture_output=True, text=True)
    row("ok" if pil.returncode == 0 else "warn", f"Pillow {pil.stdout.strip()}" if pil.returncode == 0 else "Pillow not installed; `python3 humanize.py avatar` installs it into ~/.humanize/pydeps (also needed for `humanize.py card`)")
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
    b = keystore.backend()
    row("ok" if b != "file" else "warn", f"secrets are kept in {keystore.label()}")
    if ident_path().exists():
        try:
            d = store.load(ident_path())
            plain = keystore.find_plaintext(d)
            if plain:
                row("warn", f"{len(plain)} secret(s) sit in identity.json as plain text" + ("" if a.fix else " (run doctor --fix, or `humanize.py secret migrate`)"))
                if a.fix:
                    print("        moved:", ", ".join(keystore.migrate(ident_path())))
            missing = [n for n in sorted(keystore.collect_pointers(d)) if keystore.get(n) is None]
            if missing:
                row("warn", f"{len(missing)} pointer(s) refer to secrets this machine does not have: {', '.join(missing[:4])}. Load the backup with the self key to restore them.")
            elif keystore.collect_pointers(d):
                row("ok", f"{len(keystore.collect_pointers(d))} secret(s) present in the store")
        except (store.StoreError, keystore.KeystoreError) as e:
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


def cmd_card(a):
    if not ident_path().exists():
        die("no identity yet. Run: python3 humanize.py init")
    # Validate website scheme before storing (same rules as vcard._normalize_url).
    if a.website is not None:
        _ws = a.website.strip()
        _bad_scheme = re.compile(r"^(javascript|data|file|vbscript|about)\s*:", re.I)
        if _bad_scheme.match(_ws) or ("://" in _ws and not re.match(r"^https?://", _ws, re.I)):
            die(f"website scheme not allowed: {a.website!r}. Use https://, http://, or a bare domain.")
    # Persist any field overrides to identity first
    if any(x is not None for x in [a.title, a.tagline, a.website]):
        def _apply(d):
            bc = d.setdefault("business_card", {})
            if a.title is not None:
                bc["title"] = a.title
            if a.tagline is not None:
                bc["tagline"] = a.tagline
            if a.website is not None:
                bc["website"] = a.website
            store.log_entry(d, "business_card fields updated via card command", by="humanize.py")
        store.update(ident_path(), _apply)
    d = load_identity()
    card = __import__("card")
    # --vcard: just print the vCard text, no Pillow needed
    if a.vcard:
        print(card.vcard_text(d))
        return
    # Ensure Pillow is available before rendering
    if not card.have_pillow():
        if not _ensure_pillow():
            die("Pillow could not be installed. Run: python3 humanize.py avatar")
        import importlib
        importlib.reload(card)
    out_dir = Path(a.out) if a.out else home() / "card"
    try:
        files = card.write_all(d, out_dir)
    except RuntimeError as e:
        die(str(e))
    for k, v in sorted(files.items()):
        print(f"{k}: {v}")
    # Print missing-fields note so the agent knows what to provision next.
    _vc = __import__("vcard")
    _f = _vc.fields(d)
    if _f.get("missing"):
        print("To improve this card, provision: " + "; ".join(_f["missing"]))
    if getattr(a, "open", False) and not os.environ.get("HUMANIZE_NO_BROWSER"):
        front_png = str(files.get("front.png", out_dir / "front.png"))
        subprocess.run(["open", front_png])


def cmd_self(a):
    env = dict(os.environ, HUMANIZE_HOME=str(home()))
    sys.exit(subprocess.call([sys.executable, str(SCRIPTS / "self.py")] + a.args, env=env))


# ---------------------------------------------------------------- agent helpers
def cmd_get(a):
    v = store.get(load_identity(), a.path)
    if v is None:
        sys.exit(1)
    if not a.pointer:
        try:
            v = keystore.resolve(v)
        except keystore.KeystoreError as e:
            die(str(e))
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
    where = None
    wants_secret = a.secret or (not a.plain and store.is_vaultable_key(a.path.split(".")[-1]))
    if wants_secret and isinstance(value, str) and value and not keystore.is_pointer(value):
        try:
            keystore.namespace()                     # before the write below, never inside it
            keystore.put(a.path, value)
            value, where = keystore.pointer(a.path), keystore.label()
        except keystore.KeystoreError as e:
            die(str(e))

    def apply(d):
        store.set_path(d, a.path, value)
        if a.log:
            store.log_entry(d, a.log, by="agent")
    try:
        store.update(ident_path(), apply)
    except store.StoreError as e:
        die(str(e))
    if where:
        sys.stderr.write(f"{a.path} is stored in {where}; the identity file holds a pointer.\n")


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


def cmd_totp(a):
    import totp
    try:
        if a.tcmd == "new":
            secret = totp.new_secret()
            if a.name:
                keystore.namespace()
                keystore.put(a.name, secret)
                sys.stderr.write(f"stored as a secret named {a.name!r}\n")
            print(secret)
        elif a.tcmd == "code":
            secret = keystore.get(a.secret) or a.secret
            print(f"{totp.code_for(secret)}  (valid {totp.seconds_remaining()}s more)")
        else:
            print(totp.otpauth_uri(a.secret, a.label))
    except Exception as e:
        die(str(e))


def cmd_calendar(a):
    import ical
    try:
        if a.ccmd == "add":
            uid = ical.add(a.title, a.start, a.end, a.location, a.description)
            out = uid
        elif a.ccmd == "delete":
            ical.delete(a.uid)
            out = None
        else:
            out = json.dumps(ical.list_events(a.frm, a.to), indent=2)
    except ValueError as e:
        die(str(e))
    if ident_path().exists() and not store.get(load_identity(), "calendar.local"):
        store.update(ident_path(), lambda d: store.set_path(d, "calendar.local", str(ical.path())))
    if out is not None:
        print(out)


def cmd_secret(a):
    try:
        if a.scmd == "backend":
            print(f"{keystore.backend()}: {keystore.label()}")
        elif a.scmd == "list":
            names = sorted(keystore.collect_pointers(load_identity()))
            print(json.dumps([{"name": n, "present": keystore.get(n) is not None} for n in names], indent=2))
        elif a.scmd == "get":
            v = keystore.get(a.name)
            if v is None:
                sys.exit(1)
            print(v)
        elif a.scmd == "set":
            keystore.put(a.name, a.value)
            print(keystore.pointer(a.name))
        elif a.scmd == "delete":
            keystore.delete(a.name)
        else:
            moved = keystore.migrate(ident_path())
            print(json.dumps({"moved": moved, "store": keystore.label()}, indent=2))
    except keystore.KeystoreError as e:
        die(str(e))


def cmd_demo(a):
    demo = Path(os.path.expanduser("~/.humanize-demo"))
    demo.mkdir(parents=True, exist_ok=True)
    os.environ["HUMANIZE_HOME"] = str(demo)
    d = json.loads(TEMPLATE.read_text())
    d.update(name="Ari Vale", persona="Software engineer. Direct, writes short emails, ships small things fast.")
    d["email"] = {"agentmail": {"address": "ari.vale@agentmail.to", "api_key": "am_demo000000"}}
    d["phone"]["agentphone"] = {"number": "+14155550123", "number_id": "num_01", "agent_id": "agt_01", "api_key": "ap_demo0000"}
    d["messaging"] = {"telegram": {"token": "123456:demo"}}
    d["wallet"]["evm"] = {"address": "0x4b7C1a9E2f3D4c5B6a7F8e9D0c1B2a3F4e5D6c7B"}
    d["browser"] = {"provider": "claude-browser"}
    d["accounts"] = {"github": {"username": "arivale", "vault": "github"}, "vercel": {"token": "vcp_demo"}}
    d["voice"] = {"agentphone": "voice_rachel", "tts": "edge-tts"}
    d["eyes"] = {"search": "host web tools", "weather": "open-meteo"}
    d["computer"] = {"provider": "docker", "id": "ari-box"}
    d["memory"]["supabase"] = "abcdefghijklmnop"
    d["social"] = {"x": {"handle": "arivale", "token": "demo"}}
    d["calendar"]["local"] = str(demo / "calendar.ics")
    d["calendar"]["booking_url"] = "https://cal.com/ari-vale/15min"
    d["self_repo"] = {"url": "https://github.com/arivale/self.git", "last_push": now()}
    d["host"] = detect_host() or {"app": "other", "open_command": "", "chat_url": "", "session_id": ""}
    d["layers"] = {str(n): {"enabled": n != 14} for n in LAYERS}
    d["rules"] = ["Monthly spend cap 50 USD."]
    d["dashboard_requests"] = [{"at": now(), "text": "Get a UK number.", "done": False}]
    for what in ("agentmail inbox ari.vale verified", "agentphone number +14155550123"):
        store.log_entry(d, what, by="agent")
    if getattr(a, "profile", None):
        prof = load_profile(a.profile)
        apply_profile(d, prof)
        handle = ".".join(d["name"].lower().split())
        d["email"]["agentmail"]["address"] = f"{handle}@agentmail.to"
        d["social"] = {"x": {"handle": handle.replace(".", ""), "token": "demo"}}
        d["accounts"]["github"]["username"] = handle.replace(".", "")
        d["calendar"]["booking_url"] = f"https://cal.com/{handle.replace('.', '-')}/15min"
    d["face"] = {"photo": make_avatar(d["name"], demo / "face.png"), "seed": d["name"]}
    _card_mod = __import__("card")
    if _card_mod.have_pillow():
        try:
            _card_mod.write_all(d, demo / "card")
        except Exception:
            pass
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
    p = add("init", cmd_init); p.add_argument("--profile"); p.add_argument("--name"); p.add_argument("--persona"); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true")
    add("status", cmd_status)
    p = add("doctor", cmd_doctor); p.add_argument("--fix", action="store_true")
    p = add("dashboard", cmd_dashboard); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true")
    add("open", cmd_open)
    add("stop", cmd_stop)
    p = add("avatar", cmd_avatar); p.add_argument("seed", nargs="?")
    p = add("card", cmd_card); p.add_argument("--out"); p.add_argument("--title"); p.add_argument("--tagline"); p.add_argument("--website"); p.add_argument("--vcard", action="store_true"); p.add_argument("--open", dest="open", action="store_true")
    p = add("self", cmd_self); p.add_argument("args", nargs=argparse.REMAINDER)
    add("profiles", cmd_profiles)
    p = add("demo", cmd_demo); p.add_argument("--profile"); p.add_argument("--port", type=int, default=4242); p.add_argument("--no-open", action="store_true")
    p = add("get", cmd_get); p.add_argument("path"); p.add_argument("--pointer", action="store_true", help="print the pointer, not the secret")
    p = add("set", cmd_set); p.add_argument("path"); p.add_argument("value"); p.add_argument("--log"); p.add_argument("--json", action="store_true", help="parse VALUE as JSON whatever the key")
    p.add_argument("--secret", action="store_true", help="store VALUE in the secret store whatever the key")
    p.add_argument("--plain", action="store_true", help="keep VALUE in the identity file even if the key looks secret")
    p = add("log", cmd_log); p.add_argument("text"); p.add_argument("--cost")
    p = add("requests", cmd_requests); p.add_argument("--all", action="store_true")
    p = add("done", cmd_done); p.add_argument("index", type=int)
    add("chat", cmd_chat)
    p = add("secret", cmd_secret)
    ssub = p.add_subparsers(dest="scmd", required=True)
    for n in ("backend", "list", "migrate"):
        ssub.add_parser(n)
    m = ssub.add_parser("get"); m.add_argument("name")
    m = ssub.add_parser("set"); m.add_argument("name"); m.add_argument("value")
    m = ssub.add_parser("delete"); m.add_argument("name")
    p = add("totp", cmd_totp)
    tsub = p.add_subparsers(dest="tcmd", required=True)
    m = tsub.add_parser("new"); m.add_argument("name", nargs="?")
    m = tsub.add_parser("code"); m.add_argument("secret")
    m = tsub.add_parser("uri"); m.add_argument("secret"); m.add_argument("label")
    p = add("calendar", cmd_calendar)
    csub = p.add_subparsers(dest="ccmd", required=True)
    m = csub.add_parser("add"); m.add_argument("title"); m.add_argument("start")
    m.add_argument("--end"); m.add_argument("--location"); m.add_argument("--description")
    m = csub.add_parser("list"); m.add_argument("--from", dest="frm"); m.add_argument("--to")
    m = csub.add_parser("delete"); m.add_argument("uid")
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
