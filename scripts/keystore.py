"""Secrets, kept where the operating system protects them.

The identity file holds only pointers such as "secret:email.mailgent.api_key". The value itself lives in:

  keychain        the macOS Keychain, through the `security` tool
  secret-service  the Linux keyring, through `secret-tool` (needs a desktop session)
  file            $HUMANIZE_HOME/secrets.json, mode 600, plain text. The last resort, when neither exists.

HUMANIZE_KEYSTORE=auto|keychain|secret-service|file picks one. Tests and CI use `file`.

Values are stored base64 encoded, so newlines and odd characters survive every backend. Each agent has a
random namespace in its identity ("keystore.ns"), so two agents on one machine never share a secret and a
backup loaded on a new machine finds its secrets under the same name.
"""
import base64
import json
import os
import platform
import re
import secrets as _random
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

PREFIX = "secret:"
_NAME = re.compile(r"[A-Za-z0-9_.\-]{1,200}")
LABELS = {"keychain": "the macOS Keychain", "secret-service": "the system keyring",
          "file": "a private file (no system secret store found)"}


class KeystoreError(Exception):
    pass


# ---------------------------------------------------------------- pointers
def is_pointer(v):
    return isinstance(v, str) and v.startswith(PREFIX) and bool(_NAME.fullmatch(v[len(PREFIX):]))


def pointer(name):
    if not _NAME.fullmatch(name or ""):
        raise KeystoreError(f"{name!r} is not a valid secret name")
    return PREFIX + name


def collect_pointers(obj):
    """Every secret name the object points at."""
    found = set()
    if isinstance(obj, dict):
        for v in obj.values():
            found |= collect_pointers(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= collect_pointers(v)
    elif is_pointer(obj):
        found.add(obj[len(PREFIX):])
    return found


def find_plaintext(obj, prefix=""):
    """(path, value) for every secret that still sits in the data as plain text."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str) and v and not is_pointer(v) and store.is_vaultable_key(k):
                out.append((path, v))
            elif isinstance(v, (dict, list)):
                out += find_plaintext(v, path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += find_plaintext(v, f"{prefix}.{i}")
    return out


# ---------------------------------------------------------------- backend choice
_ss_ok = None


def _secret_service_available():
    global _ss_ok
    if _ss_ok is None:
        r = subprocess.run(["secret-tool", "lookup", "service", "humanize-probe", "account", "probe"], capture_output=True, text=True)
        _ss_ok = r.returncode == 1 and not r.stderr.strip()   # "not found" with no complaint: a keyring answered
    return _ss_ok


def backend():
    want = os.environ.get("HUMANIZE_KEYSTORE", "auto").strip().lower()
    if want in ("file", "keychain", "secret-service"):
        return want
    system = platform.system()
    if system == "Darwin" and shutil.which("security"):
        return "keychain"
    if system == "Linux" and shutil.which("secret-tool") and _secret_service_available():
        return "secret-service"
    return "file"


def label():
    return LABELS[backend()]


# ---------------------------------------------------------------- namespace
def namespace():
    """This agent's stable namespace, created on first use and kept in its identity."""
    path = store.home() / "identity.json"
    ns = store.get(store.load(path), "keystore.ns")
    if not ns:
        if not path.exists():
            raise KeystoreError("there is no identity yet; run `python3 humanize.py init` first")

        def make(d):
            if not store.get(d, "keystore.ns"):
                store.set_path(d, "keystore.ns", _random.token_hex(8))
            return store.get(d, "keystore.ns")
        ns = store.update(path, make)
    return "humanize-" + ns


# ---------------------------------------------------------------- backends
def _run(cmd, input=None):
    return subprocess.run(cmd, input=input, capture_output=True, text=True)


def _fail(r, what):
    raise KeystoreError(f"{what} failed: {(r.stderr or r.stdout).strip()[:200] or 'exit ' + str(r.returncode)}")


def _file_path():
    return store.home() / "secrets.json"


def _file_read():
    try:
        d = json.loads(_file_path().read_text())
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _file_write(d):
    p = _file_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(d, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def put(name, value):
    """Store a secret. The value never appears in an error message."""
    pointer(name)
    ns, b = namespace(), backend()
    enc = base64.b64encode(value.encode()).decode()
    if b == "keychain":
        r = _run(["security", "add-generic-password", "-a", name, "-s", ns, "-w", enc, "-U"])
        if r.returncode:
            _fail(r, "the Keychain")
    elif b == "secret-service":
        r = _run(["secret-tool", "store", "--label", f"Humanize {name}", "service", ns, "account", name], input=enc)
        if r.returncode:
            _fail(r, "the system keyring")
    else:
        with store.locked(_file_path()):
            d = _file_read()
            d[f"{ns}/{name}"] = enc
            _file_write(d)


def get(name):
    """The secret, or None if this machine does not have it."""
    pointer(name)
    ns, b = namespace(), backend()
    if b == "keychain":
        r = _run(["security", "find-generic-password", "-a", name, "-s", ns, "-w"])
        if r.returncode == 44:
            return None
        if r.returncode:
            _fail(r, "the Keychain")
        enc = r.stdout.strip()
    elif b == "secret-service":
        r = _run(["secret-tool", "lookup", "service", ns, "account", name])
        if r.returncode == 1 and not r.stderr.strip():
            return None
        if r.returncode:
            _fail(r, "the system keyring")
        enc = r.stdout.strip()
    else:
        enc = _file_read().get(f"{ns}/{name}")
    if not enc:
        return None
    try:
        return base64.b64decode(enc.encode()).decode()
    except (ValueError, UnicodeDecodeError):
        raise KeystoreError(f"the stored value for {name} is damaged")


def delete(name):
    pointer(name)
    ns, b = namespace(), backend()
    if b == "keychain":
        r = _run(["security", "delete-generic-password", "-a", name, "-s", ns])
        if r.returncode not in (0, 44):
            _fail(r, "the Keychain")
    elif b == "secret-service":
        r = _run(["secret-tool", "clear", "service", ns, "account", name])
        if r.returncode not in (0, 1):
            _fail(r, "the system keyring")
    else:
        with store.locked(_file_path()):
            d = _file_read()
            d.pop(f"{ns}/{name}", None)
            _file_write(d)


def resolve(value):
    """A pointer becomes its secret; anything else is returned as it is."""
    if not is_pointer(value):
        return value
    v = get(value[len(PREFIX):])
    if v is None:
        raise KeystoreError(f"{value} is not in this machine's secret store. Load the backup with the self key to restore it.")
    return v


def migrate(identity_path):
    """Move every plain-text secret in the identity into the store and leave a pointer. Returns the paths moved."""
    identity_path = Path(identity_path)
    namespace()
    moved = []
    for path, value in find_plaintext(store.load(identity_path)):
        name = path
        if not _NAME.fullmatch(name):
            continue
        put(name, value)
        moved.append((path, value))

    def apply(d):
        for path, value in moved:
            if store.get(d, path) == value:          # do not clobber a change made meanwhile
                store.set_path(d, path, pointer(path))
        store.log_entry(d, f"moved {len(moved)} secret(s) into {label()}", by="humanize.py")
    if moved:
        store.update(identity_path, apply)
        try:   # the previous version kept as .bak still holds the plain text
            shutil.copyfile(identity_path, str(identity_path) + ".bak")
            os.chmod(str(identity_path) + ".bak", 0o600)
        except OSError:
            pass
    return [p for p, _ in moved]
