#!/usr/bin/env python3
"""Keep the agent's self in a private git repo so it can be loaded on any machine.

Stored in the repo: the identity file (encrypted), the avatar, and a copy of the Humanize scripts.
The repo should be private, and the identity is encrypted on top of that: AES-256-CBC with a key
derived by PBKDF2 (200,000 rounds) from the "self key", plus an HMAC-SHA256 over the ciphertext so a
wrong key or a tampered file is detected before anything is decrypted.
The self key is the one thing the human keeps. Without it the repo is just an unreadable blob.

  self.py init <remote url>     first time: make a key, encrypt, commit, push
  self.py push                  encrypt the current identity, commit, push
  self.py pull [--force]        fetch, then replace the local identity (refuses if you have unpushed changes)
  self.py load <remote url>     new machine: clone, decrypt, done
  self.py unlock [--force]      decrypt an already cloned self repo into place
  self.py status                JSON: remote, last commit, unpushed changes, key available

Environment
  HUMANIZE_HOME       data folder (default ~/.humanize)
  HUMANIZE_SELF_KEY   the self key; otherwise it is read from the secret store (the macOS Keychain, the system
                      keyring, or a private file), then from $HUMANIZE_HOME/self.key on older installs
  GITHUB_TOKEN        used to authenticate to github.com; otherwise accounts.github.token from the
                      identity file; otherwise whatever git already has (credential helper, SSH)
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import store
    import keystore
except ImportError:  # self.py copied on its own
    store = keystore = None
SELF_KEY_NAME = "_hz.self-key"

HOME = Path(os.environ.get("HUMANIZE_HOME") or os.path.expanduser("~/.humanize"))
IDENTITY = HOME / "identity.json"
FACE = HOME / "face.png"
KEYFILE = HOME / "self.key"
REPO = HOME / "self"
STATE = HOME / "self.state.json"
MAGIC = b"HZ1"
ITER = 200_000


def die(msg):
    sys.exit(msg.rstrip())


# ---------------------------------------------------------------- crypto
def _mac_key(k):
    return hashlib.pbkdf2_hmac("sha256", k.encode(), b"humanize-self-mac-v1", ITER, 32)


def _openssl(args, data, k):
    fd, pf = tempfile.mkstemp()  # mode 0600; keeps the key out of the process list
    try:
        with os.fdopen(fd, "w") as f:
            f.write(k)
        r = subprocess.run(["openssl", "enc", *args, "-aes-256-cbc", "-pbkdf2", "-iter", str(ITER), "-pass", "file:" + pf],
                           input=data, capture_output=True)
    except FileNotFoundError:
        die("openssl is required. Install it (macOS and most Linux have it) and retry.")
    finally:
        os.unlink(pf)
    if r.returncode:
        die("openssl failed: " + r.stderr.decode(errors="replace").strip()[:200])
    return r.stdout


def seal(data, k):
    body = MAGIC + _openssl(["-salt"], data, k)
    return body + hmac.new(_mac_key(k), body, hashlib.sha256).digest()


def unseal(blob, k):
    if blob[:3] != MAGIC or len(blob) < 3 + 16 + 32:
        die("this is not a Humanize self file")
    body, tag = blob[:-32], blob[-32:]
    if not hmac.compare_digest(tag, hmac.new(_mac_key(k), body, hashlib.sha256).digest()):
        die("Decrypt failed: wrong self key, or the file was modified.")
    return _openssl(["-d"], body[3:], k)


def key(create=False):
    k = os.environ.get("HUMANIZE_SELF_KEY")
    if k:
        return k
    if keystore and IDENTITY.exists():
        try:
            k = keystore.get(SELF_KEY_NAME)
        except keystore.KeystoreError:
            k = None
        if k:
            return k
    if KEYFILE.exists():
        return KEYFILE.read_text().strip()
    if not create:
        die("No self key. Set HUMANIZE_SELF_KEY, or restore it: it lives in the secret store (or " + str(KEYFILE) + " on older installs).")
    k = secrets.token_urlsafe(32)
    where = None
    if keystore and IDENTITY.exists():
        try:
            keystore.put(SELF_KEY_NAME, k)
            where = keystore.label()
        except keystore.KeystoreError:
            where = None
    if where is None:
        HOME.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(KEYFILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(k)
        where = str(KEYFILE)
    print("\nNEW SELF KEY. Give this to the human once and keep it somewhere safe.\n"
          "It is the only way to load this agent on another machine, and it cannot be recovered.\n"
          f"It is also saved in {where} so pushes can run unattended:\n\n  " + k + "\n")
    return k


# ---------------------------------------------------------------- state
def read_identity():
    if not IDENTITY.exists():
        die(f"no identity at {IDENTITY}")
    return IDENTITY.read_bytes()


def secret_bundle(identity):
    """The secrets the identity points at, as this machine has them."""
    if not keystore:
        return {}
    out = {}
    for name in sorted(keystore.collect_pointers(identity)):
        try:
            v = keystore.get(name)
        except keystore.KeystoreError:
            v = None
        if v is not None:
            out[name] = v
    return out


def fingerprint(raw=None, with_secrets=True):
    """Hash of the identity (without the self_repo bookkeeping) and of its secrets, so that pushing does not
    count as a change but rotating a key does."""
    try:
        d = json.loads(raw if raw is not None else read_identity())
    except ValueError:
        return None
    d.pop("self_repo", None)
    body = {"identity": d}
    if with_secrets:
        body["secrets"] = {n: hashlib.sha256(v.encode()).hexdigest() for n, v in secret_bundle(d).items()}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def read_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def write_state(**kw):
    s = read_state()
    s.update(kw)
    fd = os.open(str(STATE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(s, f)


def note(**kw):
    def apply(d):
        d.setdefault("self_repo", {}).update(kw)
    if not IDENTITY.exists():
        return
    if store:
        store.update(IDENTITY, apply)
    else:
        d = json.loads(IDENTITY.read_text())
        apply(d)
        IDENTITY.write_text(json.dumps(d, indent=2))


def unpushed():
    return fingerprint() != read_state().get("pushed_fp")


# ---------------------------------------------------------------- git
def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    try:
        t = json.loads(IDENTITY.read_text()).get("accounts", {}).get("github", {}).get("token")
        return keystore.resolve(t) if keystore and t else t
    except Exception:
        return None


def git(*args, cwd=None, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="humanize", GIT_AUTHOR_EMAIL="self@humanize.local",
               GIT_COMMITTER_NAME="humanize", GIT_COMMITTER_EMAIL="self@humanize.local")
    t = token()
    if t:  # via the environment, so the token never appears in the process list or in .git/config
        b64 = base64.b64encode(f"x-access-token:{t}".encode()).decode()
        env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader", GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {b64}")
    try:
        r = subprocess.run(["git", *args], cwd=cwd, env=env, text=True, capture_output=True)
    except FileNotFoundError:
        die("git is required.")
    if check and r.returncode:
        msg = (r.stderr.strip() or r.stdout.strip()).replace(t or "\0", "***")
        die(f"git {args[0]} failed: {msg}")
    return r


# ---------------------------------------------------------------- commands
def stage(k):
    REPO.mkdir(parents=True, exist_ok=True)
    raw = read_identity()
    (REPO / "identity.json.enc").write_bytes(seal(raw, k))
    bundle = secret_bundle(json.loads(raw))
    senc = REPO / "secrets.json.enc"
    if bundle:
        senc.write_bytes(seal(json.dumps(bundle, sort_keys=True).encode(), k))
    elif senc.exists():
        senc.unlink()
    if FACE.exists():
        shutil.copyfile(FACE, REPO / "face.png")
    mem = HOME / "memory.db"
    if mem.exists() and mem.stat().st_size <= 20 * 1024 * 1024:  # consistent snapshot, then encrypt
        import sqlite3
        fd, tmp = tempfile.mkstemp()
        os.close(fd)
        try:
            src, dst = sqlite3.connect(str(mem)), sqlite3.connect(tmp)
            src.backup(dst)
            src.close(); dst.close()
            (REPO / "memory.db.enc").write_bytes(seal(Path(tmp).read_bytes(), k))
        finally:
            os.unlink(tmp)
    shutil.copytree(HERE, REPO / "scripts", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.lock"))
    for f in ("humanize.py", "identity.template.json"):
        if (HERE.parent / f).exists():
            shutil.copyfile(HERE.parent / f, REPO / f)
    (REPO / "README.md").write_text(
        "# self\n\nA Humanize agent. `identity.json.enc`, `secrets.json.enc` and `memory.db.enc` are encrypted with the self key; nothing else here is secret.\n\n"
        "Load it on a new machine (needs git, Python 3 and the self key):\n\n"
        "```bash\ngit clone <this repo> ~/.humanize/self\n"
        "HUMANIZE_SELF_KEY=<self key> python3 ~/.humanize/self/scripts/self.py unlock\n"
        "python3 ~/.humanize/self/humanize.py init\n```\n")
    (REPO / ".gitignore").write_text("*.key\nidentity.json\n*.lock\n__pycache__/\n")
    return fingerprint(raw)


def cmd_init(url):
    k = key(create=True)
    fp = stage(k)
    if not (REPO / ".git").exists():
        git("init", "-q", "-b", "main", cwd=REPO)
    git("remote", "remove", "origin", cwd=REPO, check=False)
    git("remote", "add", "origin", url, cwd=REPO)
    note(url=url)
    push(k, fp)


def push(k=None, fp=None):
    if not (REPO / ".git").exists():
        die("Not set up yet. Run: self.py init <remote url>")
    k = k or key()
    fp = fp or stage(k)
    git("add", "-A", cwd=REPO)
    git("commit", "-q", "-m", "self " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), cwd=REPO, check=False)
    git("push", "-q", "-u", "origin", "main", cwd=REPO)
    write_state(pushed_fp=fp)
    note(last_push=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print("pushed")


def cmd_pull(force):
    if not (REPO / ".git").exists():
        die("Nothing to pull. On a new machine run: self.py load <remote url>")
    if unpushed() and not force:
        die("You have changes that are not pushed. Run `self.py push` first, or use --force to discard them.")
    git("pull", "-q", "--ff-only", "origin", "main", cwd=REPO)
    unlock(True)


def unlock(force):
    enc = REPO / "identity.json.enc"
    if not enc.exists():
        die(f"{enc} not found")
    raw = unseal(enc.read_bytes(), key())
    if IDENTITY.exists() and not force and fingerprint(with_secrets=False) != fingerprint(raw, with_secrets=False):
        die(f"{IDENTITY} already exists and differs. Use --force to replace it (the old one is kept as identity.json.bak).")
    HOME.mkdir(parents=True, exist_ok=True)
    os.chmod(HOME, 0o700)
    if store:
        store.save(IDENTITY, json.loads(raw))
    else:
        IDENTITY.write_bytes(raw)
        os.chmod(IDENTITY, 0o600)
    if (REPO / "face.png").exists():
        shutil.copyfile(REPO / "face.png", FACE)
    menc = REPO / "memory.db.enc"
    if menc.exists() and (force or not (HOME / "memory.db").exists()):
        (HOME / "memory.db").write_bytes(unseal(menc.read_bytes(), key()))
        os.chmod(HOME / "memory.db", 0o600)
    senc = REPO / "secrets.json.enc"
    if senc.exists():
        if not keystore:
            die("this backup holds secrets but keystore.py is missing")
        for name, value in json.loads(unseal(senc.read_bytes(), key())).items():
            keystore.put(name, value)
    write_state(pushed_fp=fingerprint())
    print("identity written to", IDENTITY)


def cmd_load(url):
    HOME.mkdir(parents=True, exist_ok=True)
    if REPO.exists() and any(REPO.iterdir()):
        die(f"{REPO} already exists. Use `self.py unlock` or `self.py pull`.")
    git("clone", "-q", "-b", "main", url, str(REPO))
    unlock(False)
    print("start the dashboard:  python3", REPO / "humanize.py", "init")


def cmd_status():
    out = {"repo": str(REPO), "initialized": (REPO / ".git").exists(), "key_available": bool(os.environ.get("HUMANIZE_SELF_KEY") or KEYFILE.exists())}
    if out["initialized"]:
        r = git("remote", "get-url", "origin", cwd=REPO, check=False)
        out["remote"] = r.stdout.strip().split("@")[-1] if r.returncode == 0 else None
        out["last_commit"] = git("log", "-1", "--format=%cI %s", cwd=REPO, check=False).stdout.strip() or None
        out["unpushed_changes"] = IDENTITY.exists() and unpushed()
    print(json.dumps(out, indent=2))


def main():
    a = sys.argv[1:]
    if not a:
        die(__doc__)
    c, rest = a[0], a[1:]
    force = "--force" in rest
    rest = [x for x in rest if x != "--force"]
    if c == "init" and rest:
        cmd_init(rest[0])
    elif c == "push":
        push()
    elif c == "pull":
        cmd_pull(force)
    elif c == "unlock":
        unlock(force)
    elif c == "load" and rest:
        cmd_load(rest[0])
    elif c == "status":
        cmd_status()
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
