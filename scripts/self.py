#!/usr/bin/env python3
"""Keep the agent's self in a private git repo so it can be loaded on any machine.

What gets stored: identity.json (encrypted), face.png, rules, and the dashboard scripts.
Encryption: AES-256 via openssl with a passphrase (the "self key"). The repo is private on top of that.
The self key is the one thing the human keeps. Without it the repo is just a blob.

Usage:
  python3 scripts/self.py init  <git remote url>          # first time: create ~/.humanize/self, set remote, push
  python3 scripts/self.py push                            # encrypt identity, commit, push
  python3 scripts/self.py pull                            # fetch, decrypt into ~/.humanize/identity.json
  python3 scripts/self.py load  <git remote url>          # new machine: clone, decrypt, done
  python3 scripts/self.py status                          # remote, last push, whether local is ahead

Env / prompts:
  HUMANIZE_SELF_KEY   the passphrase. If unset, self.py reads it from ~/.humanize/self.key (mode 600),
                      and on first init generates one and prints it once so the human can save it.
  GITHUB_TOKEN        optional; if the remote is https://github.com/... the token is used for auth.
"""
import json, os, secrets, subprocess, sys, time
from pathlib import Path

HOME = Path(os.path.expanduser("~/.humanize"))
IDENTITY = HOME / "identity.json"
FACE = HOME / "face.png"
KEYFILE = HOME / "self.key"
REPO = HOME / "self"
HERE = Path(__file__).resolve().parent

def sh(*a, cwd=None, check=True, quiet=False):
    r = subprocess.run(a, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode:
        sys.exit(f"$ {' '.join(a)}\n{r.stderr.strip() or r.stdout.strip()}")
    if not quiet and r.stdout.strip():
        print(r.stdout.strip())
    return r

def key():
    k = os.environ.get("HUMANIZE_SELF_KEY")
    if k: return k
    if KEYFILE.exists(): return KEYFILE.read_text().strip()
    k = secrets.token_urlsafe(32)
    HOME.mkdir(parents=True, exist_ok=True)
    KEYFILE.write_text(k); os.chmod(KEYFILE, 0o600)
    print("\nNEW SELF KEY (save this somewhere the human controls; it is the only way to load this agent elsewhere):\n\n  " + k + "\n")
    return k

def authed(url):
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok and IDENTITY.exists():
        try:
            tok = json.loads(IDENTITY.read_text()).get("accounts", {}).get("github", {}).get("token")
        except Exception: tok = None
    if tok and url.startswith("https://github.com/"):
        return url.replace("https://github.com/", f"https://x-access-token:{tok}@github.com/")
    return url

def encrypt(src, dst, k):
    sh("openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", str(src), "-out", str(dst), "-pass", "pass:" + k, quiet=True)

def decrypt(src, dst, k):
    r = sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-in", str(src), "-out", str(dst), "-pass", "pass:" + k, check=False, quiet=True)
    if r.returncode: sys.exit("Decrypt failed. Wrong self key?")
    os.chmod(dst, 0o600)

def stage(k):
    REPO.mkdir(parents=True, exist_ok=True)
    encrypt(IDENTITY, REPO / "identity.json.enc", k)
    if FACE.exists(): (REPO / "face.png").write_bytes(FACE.read_bytes())
    (REPO / "scripts").mkdir(exist_ok=True)
    for f in ("dashboard.py", "dashboard.html", "avatar.py", "self.py"):
        p = HERE / f
        if p.exists(): (REPO / "scripts" / f).write_bytes(p.read_bytes())
    (REPO / "README.md").write_text(
        "# self\n\nThis is a Humanize agent. identity.json is encrypted with the self key.\n\n"
        "Load on a new machine:\n\n```bash\nexport HUMANIZE_SELF_KEY=<self key>\n"
        "python3 -c \"$(curl -fsSL https://raw.githubusercontent.com/0xArx/Humanize/main/scripts/self.py)\" load <this repo url>\n"
        "python3 ~/.humanize/self/scripts/dashboard.py\n```\n")
    (REPO / ".gitignore").write_text("*.key\nidentity.json\n")

def note(**kw):
    if not IDENTITY.exists(): return
    d = json.loads(IDENTITY.read_text())
    d.setdefault("self_repo", {}).update(kw)
    IDENTITY.write_text(json.dumps(d, indent=2))

def cmd_init(url):
    if not IDENTITY.exists(): sys.exit(f"no identity at {IDENTITY}")
    k = key(); stage(k)
    if not (REPO / ".git").exists():
        sh("git", "init", "-q", "-b", "main", cwd=REPO)
    sh("git", "remote", "remove", "origin", cwd=REPO, check=False, quiet=True)
    sh("git", "remote", "add", "origin", authed(url), cwd=REPO)
    note(url=url, initialized=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    cmd_push()

def cmd_push():
    if not (REPO / ".git").exists(): sys.exit("run init <remote url> first")
    k = key(); stage(k)
    sh("git", "add", "-A", cwd=REPO)
    r = sh("git", "-c", "user.name=humanize", "-c", "user.email=self@humanize.local", "commit", "-q", "-m", "self " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), cwd=REPO, check=False, quiet=True)
    sh("git", "push", "-q", "-u", "origin", "main", cwd=REPO)
    sh("git", "symbolic-ref", "HEAD", "refs/heads/main", cwd=REPO, check=False, quiet=True)
    note(last_push=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print("pushed")

def cmd_pull():
    if not (REPO / ".git").exists(): sys.exit("run load <remote url> on a fresh machine")
    sh("git", "pull", "-q", "--ff-only", "origin", "main", cwd=REPO)
    decrypt(REPO / "identity.json.enc", IDENTITY, key())
    if (REPO / "face.png").exists(): FACE.write_bytes((REPO / "face.png").read_bytes())
    print("pulled and decrypted into", IDENTITY)

def cmd_load(url):
    HOME.mkdir(parents=True, exist_ok=True)
    if REPO.exists() and any(REPO.iterdir()): sys.exit(f"{REPO} already exists; use pull")
    sh("git", "clone", "-q", "-b", "main", authed(url), str(REPO))
    decrypt(REPO / "identity.json.enc", IDENTITY, key())
    if (REPO / "face.png").exists(): FACE.write_bytes((REPO / "face.png").read_bytes())
    print("loaded. identity at", IDENTITY, "\nstart the dashboard: python3", REPO / "scripts/dashboard.py")

def cmd_status():
    out = {"repo": str(REPO), "initialized": (REPO / ".git").exists()}
    if out["initialized"]:
        out["remote"] = sh("git", "remote", "get-url", "origin", cwd=REPO, check=False, quiet=True).stdout.strip().split("@")[-1]
        out["last_commit"] = sh("git", "log", "-1", "--format=%cI %s", cwd=REPO, check=False, quiet=True).stdout.strip()
        if IDENTITY.exists():
            out["identity_newer_than_push"] = IDENTITY.stat().st_mtime > (REPO / "identity.json.enc").stat().st_mtime if (REPO / "identity.json.enc").exists() else True
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    c = a[0]
    if c == "init" and len(a) > 1: cmd_init(a[1])
    elif c == "push": cmd_push()
    elif c == "pull": cmd_pull()
    elif c == "load" and len(a) > 1: cmd_load(a[1])
    elif c == "status": cmd_status()
    else: sys.exit(__doc__)
