"""Shared helpers. Every test runs against a throwaway HUMANIZE_HOME, never the real one."""
import http.client as httpclient
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import keystore  # noqa: E402
import store  # noqa: E402


class HomeCase(unittest.TestCase):
    """Gives each test its own data directory and a helper to run humanize.py inside it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hz-test-"))
        self.home = self.tmp / "home"
        self.env = dict(os.environ, HUMANIZE_HOME=str(self.home), HOME=str(self.tmp), HUMANIZE_NO_BROWSER="1", HUMANIZE_KEYSTORE="file")
        os.environ["HUMANIZE_HOME"] = str(self.home)  # for in-process use of store
        os.environ["HUMANIZE_KEYSTORE"] = "file"      # tests never touch a real Keychain
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.hz("stop", check=False)
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("HUMANIZE_HOME", None)
        os.environ.pop("HUMANIZE_KEYSTORE", None)

    def hz(self, *args, check=True, input=None, env=None):
        r = subprocess.run([sys.executable, str(ROOT / "humanize.py"), *args], capture_output=True, text=True,
                           env=dict(self.env, **(env or {})), input=input, timeout=120)
        if check and r.returncode:
            raise AssertionError(f"humanize.py {' '.join(args)} exited {r.returncode}\n{r.stdout}\n{r.stderr}")
        return r

    @property
    def identity(self):
        return self.home / "identity.json"

    def load(self):
        return json.loads(self.identity.read_text())

    def init(self, name="Test Agent", port="0"):
        return self.hz("init", "--name", name, "--port", port, "--no-open")

    def dashboard(self):
        """Start a dashboard, sign this test in as its owner, and return (port, token)."""
        self.init()
        info = json.loads((self.home / "dashboard.json").read_text())
        self.key = (self.home / "dashboard.key").read_text().strip()
        _, headers, _ = http(info["port"], "GET", f"/?k={self.key}")
        self.cookie = headers["set-cookie"].split(";")[0]
        return info["port"], info["token"]


def http(port, method, path, body=None, headers=None, host=None):
    """Raw request with full control over headers, including a forged Host."""
    c = httpclient.HTTPConnection("127.0.0.1", port, timeout=15)
    h = {"Host": host or f"127.0.0.1:{port}"}
    h.update(headers or {})
    payload = body if isinstance(body, (bytes, type(None))) else body.encode()
    c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    for k, v in h.items():
        c.putheader(k, v)
    if payload is not None:
        c.putheader("Content-Length", str(len(payload)))
    c.endheaders(payload)
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, dict((k.lower(), v) for k, v in r.getheaders()), data
