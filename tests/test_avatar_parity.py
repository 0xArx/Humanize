import json
import shutil
import subprocess
import sys
import unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import avatar  # noqa: E402

SEEDS = ["Ari Vale", "Mira Chen", "Tomas Reyes", "", "x", "Noor ❤ Haddad", "a" * 300]


def close(a, b, path="$"):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        assert abs(a - b) < 1e-9, f"{path}: js={a} py={b}"
    elif isinstance(a, list):
        assert len(a) == len(b), f"{path}: length js={len(a)} py={len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, f"{path}[{i}]")
    elif isinstance(a, dict):
        assert sorted(a) == sorted(b), f"{path}: keys js={sorted(a)} py={sorted(b)}"
        for k in a:
            close(a[k], b[k], f"{path}.{k}")
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


class AvatarTests(unittest.TestCase):
    def test_same_seed_same_mark_different_seed_different_mark(self):
        self.assertEqual(avatar.params("Ari Vale"), avatar.params("Ari Vale"))
        marks = {json.dumps(avatar.params(s)) for s in SEEDS}
        self.assertEqual(len(marks), len(SEEDS))

    @unittest.skipUnless(shutil.which("node"), "node is needed to compare with the browser code")
    def test_python_and_browser_code_derive_identical_avatars(self):
        js = f"""
        const HZ = require({str(ROOT / 'scripts' / 'orb.js')!r});
        (async () => {{ const out = {{}};
          for (const s of {json.dumps(SEEDS)}) out[s] = await HZ.orbParams(s);
          console.log(JSON.stringify(out)); }})();"""
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        from_js = json.loads(r.stdout)
        for seed in SEEDS:
            close(from_js[seed], avatar.params(seed), seed[:12] or "<empty>")

    def test_params_cli_matches_the_function(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "avatar.py"), "--params", "Ari Vale"], capture_output=True, text=True)
        self.assertEqual(json.loads(r.stdout), json.loads(json.dumps(avatar.params("Ari Vale"))))

    def test_png_is_written_and_deterministic_when_pillow_exists(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        import tempfile, pathlib
        d = pathlib.Path(tempfile.mkdtemp())
        a, b = d / "a.png", d / "b.png"
        for out in (a, b):
            subprocess.run([sys.executable, str(ROOT / "scripts" / "avatar.py"), "Ari Vale", str(out), "256"], check=True, capture_output=True)
        self.assertTrue(a.read_bytes().startswith(b"\x89PNG"))
        self.assertEqual(a.read_bytes(), b.read_bytes())
        shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
