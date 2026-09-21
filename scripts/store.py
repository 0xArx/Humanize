"""Safe, dependency-free access to the Humanize identity file.

Every writer (the dashboard, humanize.py, self.py) goes through this module so that two
processes changing the file at the same time cannot lose each other's edits.

  home()             the Humanize data directory (HUMANIZE_HOME, else ~/.humanize)
  load(path)         parse the identity file; {} if missing; raises StoreError if it is corrupt
  save(path, data)   atomic write, mode 0600, keeps one .bak copy of the previous version
  update(path, fn)   locked read, modify, write
  get / set_path     dotted-path helpers
  mask(obj)          copy of obj with secret values hidden, for showing in a browser
"""
import json
import os
import re
import shutil
import threading
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None

_thread_lock = threading.RLock()


class StoreError(Exception):
    pass


def home():
    return Path(os.environ.get("HUMANIZE_HOME") or os.path.expanduser("~/.humanize"))


class _Locked:
    def __init__(self, path):
        self.lockpath = str(path) + ".lock"

    def __enter__(self):
        _thread_lock.acquire()
        Path(self.lockpath).parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.lockpath, "a+")
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()
        _thread_lock.release()


locked = _Locked   # public name for code outside this module that needs the same lock


def load(path):
    path = Path(path)
    if not path.exists():
        return {}
    text = path.read_text()
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except ValueError as e:
        raise StoreError(f"{path} is not valid JSON ({e}). Your last good copy is {path}.bak") from e
    if not isinstance(data, dict):
        raise StoreError(f"{path} must contain a JSON object")
    return data


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            shutil.copyfile(path, str(path) + ".bak")
            os.chmod(str(path) + ".bak", 0o600)
        except OSError:
            pass
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def update(path, fn):
    """Locked read-modify-write. fn(data) mutates in place; its return value is passed back."""
    with _Locked(path):
        data = load(path)
        result = fn(data)
        save(path, data)
        return result


def get(data, dotted, default=None):
    cur = data
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur if cur is not None else default


def set_path(data, dotted, value):
    keys = dotted.split(".")
    cur = data
    for k in keys[:-1]:
        nxt = cur.get(k)
        if nxt is None:
            nxt = cur[k] = {}
        if not isinstance(nxt, dict):
            raise StoreError(f"cannot set {dotted}: {k} is not an object")
        cur = nxt
    cur[keys[-1]] = value


def log_entry(data, did, **extra):
    import time
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "did": did}
    entry.update({k: v for k, v in extra.items() if v is not None})
    logs = data.setdefault("log", [])
    logs.append(entry)
    if len(logs) > 1000:
        del logs[: len(logs) - 1000]


_SECRET = re.compile(r"(api_?key|token|secret|passw|private|mnemonic|recovery|credential|cookie|totp|seed_phrase|_key$|^key$|^pat$|^auth$)", re.I)


def is_secret_key(key):
    k = str(key).lower()
    if "public" in k:
        return False
    return bool(_SECRET.search(k))


def is_vaultable_key(key):
    """Keys whose values belong in the operating system's secret store rather than in a plain file."""
    k = str(key).lower()
    return is_secret_key(k) and k != "auth"     # `auth` holds a file path, not a secret


def _hide(v):
    if isinstance(v, str):
        return "••••" + v[-4:] if len(v) >= 12 else "••••"
    if isinstance(v, dict):
        return {k: _hide(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_hide(x) for x in v]
    return v


def mask(obj, key=""):
    """Copy of obj with every value under a secret-looking key hidden. Nothing is exempt."""
    if isinstance(obj, dict):
        return {k: (_hide(v) if is_secret_key(k) else mask(v, k)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask(x, key) for x in obj]
    return obj
