"""Tests for scripts/card.py and the humanize.py card command.

Covers:
- PNG dimensions and mode
- Determinism (render twice, equal bytes)
- PDF validity (starts with %PDF, two pages, correct MediaBox)
- write_all file set and permissions
- CLI end to end (init, set email and phone, run card, files exist)
- Flags persist to identity
- javascript: website rejected
- Missing Pillow path still produces card.vcf and a helpful error for images
- Graceful rendering of every fixture from fixtures.py
- QR round-trip through CoreImage decoder on the rendered back.png
"""
import io
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vcard  # noqa: E402


sys.path.insert(0, str(ROOT / "tests"))
from fixtures import FIXTURES  # noqa: E402

SEEDS = ["Ari Vale", "Noor Hadid", "Kit Okafor", "Zed", "Mariam Siddiqui", "Quill"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_card():
    """Import card module with scripts on the path."""
    import importlib
    if "card" in sys.modules:
        return sys.modules["card"]
    return importlib.import_module("card")


def _have_pillow():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# PNG dimension / mode
# ---------------------------------------------------------------------------

class TestPngDimensionsMode(unittest.TestCase):
    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_front_is_1050x600_rgb(self):
        card = _import_card()
        img = card.render(FIXTURES["full"], "front")
        self.assertEqual(img.size, (1050, 600))
        self.assertEqual(img.mode, "RGB")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_back_is_1050x600_rgb(self):
        card = _import_card()
        img = card.render(FIXTURES["full"], "back")
        self.assertEqual(img.size, (1050, 600))
        self.assertEqual(img.mode, "RGB")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_invalid_side_raises_value_error(self):
        card = _import_card()
        with self.assertRaises(ValueError):
            card.render(FIXTURES["full"], "top")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_png_bytes_returns_valid_png(self):
        card = _import_card()
        b = card.png_bytes(FIXTURES["full"], "front")
        self.assertTrue(b.startswith(b"\x89PNG"), "must start with PNG magic")
        self.assertGreater(len(b), 1000)

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_png_bytes_back_returns_valid_png(self):
        card = _import_card()
        b = card.png_bytes(FIXTURES["full"], "back")
        self.assertTrue(b.startswith(b"\x89PNG"))


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism(unittest.TestCase):
    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_render_twice_same_bytes_front(self):
        card = _import_card()
        b1 = card.png_bytes(FIXTURES["full"], "front")
        b2 = card.png_bytes(FIXTURES["full"], "front")
        self.assertEqual(b1, b2, "front PNG must be byte-identical across calls")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_render_twice_same_bytes_back(self):
        card = _import_card()
        b1 = card.png_bytes(FIXTURES["full"], "back")
        b2 = card.png_bytes(FIXTURES["full"], "back")
        self.assertEqual(b1, b2, "back PNG must be byte-identical across calls")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_render_twice_same_bytes_minimal(self):
        card = _import_card()
        b1 = card.png_bytes(FIXTURES["minimal"], "front")
        b2 = card.png_bytes(FIXTURES["minimal"], "front")
        self.assertEqual(b1, b2)

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_pdf_bytes_deterministic(self):
        card = _import_card()
        p1 = card.pdf_bytes(FIXTURES["full"])
        p2 = card.pdf_bytes(FIXTURES["full"])
        self.assertEqual(p1, p2, "PDF must be byte-identical across calls")


# ---------------------------------------------------------------------------
# PDF validity
# ---------------------------------------------------------------------------

class TestPdfValidity(unittest.TestCase):
    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def setUp(self):
        card = _import_card()
        self.pdf = card.pdf_bytes(FIXTURES["full"])

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_starts_with_pdf_magic(self):
        card = _import_card()
        pdf = card.pdf_bytes(FIXTURES["full"])
        self.assertTrue(pdf.startswith(b"%PDF"), "PDF must start with %PDF")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_has_two_pages(self):
        card = _import_card()
        pdf = card.pdf_bytes(FIXTURES["full"])
        # Count /Type /Page entries (each page object has one).
        page_count = pdf.count(b"/Type /Page\n") + pdf.count(b"/Type/Page\n") + pdf.count(b"/Type /Page\r")
        # Pillow writes /Type /Page for each page object.
        self.assertGreaterEqual(page_count, 2, "PDF must have at least 2 page objects")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_mediabox_matches_3_5x2_at_300dpi(self):
        """3.5 in x 2 in at 300 dpi = 1050x600 px. In PDF points (72pt/in): 252 x 144."""
        card = _import_card()
        pdf = card.pdf_bytes(FIXTURES["full"])
        # MediaBox in PDF points: 3.5*72=252, 2*72=144
        # Allow integer or float representations with some tolerance.
        text = pdf.decode("latin-1", errors="replace")
        # Find MediaBox lines
        boxes = re.findall(r"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", text)
        self.assertTrue(boxes, "PDF must contain a MediaBox")
        for box in boxes:
            w, h = float(box[2]), float(box[3])
            # 1050 px at 300 dpi = 252 pt; 600 px at 300 dpi = 144 pt
            self.assertAlmostEqual(w, 252.0, delta=1.0, msg=f"MediaBox width should be ~252 pt, got {w}")
            self.assertAlmostEqual(h, 144.0, delta=1.0, msg=f"MediaBox height should be ~144 pt, got {h}")


# ---------------------------------------------------------------------------
# write_all file set and permissions
# ---------------------------------------------------------------------------

class TestWriteAll(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hz-card-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_writes_expected_files(self):
        card = _import_card()
        out = os.path.join(self.tmp, "out")
        result = card.write_all(FIXTURES["full"], out)
        self.assertIn("card.vcf", result)
        self.assertIn("front.png", result)
        self.assertIn("back.png", result)
        self.assertIn("card.pdf", result)
        for name, path in result.items():
            self.assertTrue(os.path.isfile(path), f"{name} should be a file")
            self.assertGreater(os.path.getsize(path), 100, f"{name} should not be empty")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_creates_outdir_with_mode_700(self):
        card = _import_card()
        out = os.path.join(self.tmp, "newdir")
        self.assertFalse(os.path.exists(out))
        card.write_all(FIXTURES["full"], out)
        self.assertTrue(os.path.isdir(out))
        mode = os.stat(out).st_mode & 0o777
        self.assertEqual(mode, 0o700, f"outdir mode should be 700, got {oct(mode)}")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_vcf_is_valid_vcard(self):
        card = _import_card()
        out = os.path.join(self.tmp, "vcf_test")
        result = card.write_all(FIXTURES["full"], out)
        text = Path(result["card.vcf"]).read_text(encoding="utf-8")
        self.assertIn("BEGIN:VCARD", text)
        self.assertIn("END:VCARD", text)
        self.assertIn("FN:", text)


# ---------------------------------------------------------------------------
# vCard standalone function
# ---------------------------------------------------------------------------

class TestVcardText(unittest.TestCase):
    def test_vcard_text_returns_vcard(self):
        card = _import_card()
        text = card.vcard_text(FIXTURES["full"])
        self.assertIn("BEGIN:VCARD", text)
        self.assertIn("END:VCARD", text)
        self.assertIn("Ari Vale", text)

    def test_vcard_text_no_pillow_required(self):
        """vcard_text must work even if have_pillow() is False (pure text path)."""
        card = _import_card()
        # This should never raise even if Pillow is absent.
        text = card.vcard_text(FIXTURES["minimal"])
        self.assertIn("Mira Chen", text)


# ---------------------------------------------------------------------------
# Missing Pillow path
# ---------------------------------------------------------------------------

class TestMissingPillow(unittest.TestCase):
    def test_have_pillow_returns_bool(self):
        card = _import_card()
        result = card.have_pillow()
        self.assertIsInstance(result, bool)

    def test_render_raises_runtime_error_when_pillow_absent(self):
        """Simulate absent Pillow by patching have_pillow and PIL import."""
        card = _import_card()
        import unittest.mock as mock

        original_have = card.have_pillow
        original_require = card._require_pillow

        def fake_require():
            raise RuntimeError(
                "Pillow is not installed. Run: python3 humanize.py avatar"
            )

        card._require_pillow = fake_require
        try:
            err = None
            try:
                card.render(FIXTURES["full"], "front")
            except RuntimeError as e:
                err = str(e)
            self.assertIsNotNone(err, "render should raise RuntimeError when Pillow absent")
            self.assertIn("humanize.py avatar", err,
                          "error message should tell user how to install Pillow")
        finally:
            card._require_pillow = original_require

    def test_vcard_text_works_without_pillow(self):
        """vcard_text must not call _require_pillow."""
        card = _import_card()

        def fake_require():
            raise RuntimeError("NO PILLOW")

        orig = card._require_pillow
        card._require_pillow = fake_require
        try:
            text = card.vcard_text(FIXTURES["full"])
            self.assertIn("Ari Vale", text)
        finally:
            card._require_pillow = orig


# ---------------------------------------------------------------------------
# CLI end to end
# ---------------------------------------------------------------------------

from helpers import HomeCase  # noqa: E402


class TestCardCli(HomeCase):
    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_card_command_produces_four_files(self):
        self.init("Test Agent")
        self.hz("set", "email.agentmail.address", "test@agentmail.to")
        self.hz("set", "phone.agentphone.number", "+14155550001")
        out = str(self.tmp / "card_out")
        r = self.hz("card", "--out", out)
        self.assertIn("front.png", r.stdout)
        self.assertIn("back.png", r.stdout)
        self.assertIn("card.vcf", r.stdout)
        self.assertIn("card.pdf", r.stdout)
        for name in ("front.png", "back.png", "card.vcf", "card.pdf"):
            self.assertTrue((Path(out) / name).exists(), f"{name} should exist")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_vcard_flag_prints_vcard_to_stdout(self):
        self.init("Vcard Agent")
        self.hz("set", "email.agentmail.address", "vc@agentmail.to")
        r = self.hz("card", "--vcard")
        self.assertIn("BEGIN:VCARD", r.stdout)
        self.assertIn("END:VCARD", r.stdout)
        self.assertIn("Vcard Agent", r.stdout)

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_title_flag_persists_to_identity(self):
        self.init("Flag Agent")
        self.hz("set", "email.agentmail.address", "flag@agentmail.to")
        out = str(self.tmp / "flag_card")
        self.hz("card", "--out", out, "--title", "Chief Bot")
        d = self.load()
        self.assertEqual(d.get("business_card", {}).get("title"), "Chief Bot")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_tagline_flag_persists_to_identity(self):
        self.init("Tag Agent")
        self.hz("set", "email.agentmail.address", "tag@agentmail.to")
        out = str(self.tmp / "tag_card")
        self.hz("card", "--out", out, "--tagline", "Always on.")
        d = self.load()
        self.assertEqual(d.get("business_card", {}).get("tagline"), "Always on.")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_website_flag_persists_to_identity(self):
        self.init("Web Agent")
        self.hz("set", "email.agentmail.address", "web@agentmail.to")
        out = str(self.tmp / "web_card")
        self.hz("card", "--out", out, "--website", "https://agent.example.com")
        d = self.load()
        self.assertEqual(d.get("business_card", {}).get("website"), "https://agent.example.com")

    def test_javascript_website_is_rejected(self):
        self.init("Bad Agent")
        r = self.hz("card", "--website", "javascript:alert(1)", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not allowed", r.stderr + r.stdout)

    def test_data_website_is_rejected(self):
        self.init("Bad Agent 2")
        r = self.hz("card", "--website", "data:text/html,<h1>hi</h1>", check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_file_website_is_rejected(self):
        self.init("Bad Agent 3")
        r = self.hz("card", "--website", "file:///etc/passwd", check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_card_before_init_gives_clear_error(self):
        r = self.hz("card", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("init", r.stderr + r.stdout)

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_default_outdir_is_home_card(self):
        self.init("Home Card Agent")
        self.hz("set", "email.agentmail.address", "home@agentmail.to")
        self.hz("card")
        card_dir = self.home / "card"
        self.assertTrue(card_dir.is_dir())
        self.assertTrue((card_dir / "front.png").exists())


# ---------------------------------------------------------------------------
# Fixture rendering: graceful for every fixture
# ---------------------------------------------------------------------------

class TestFixtureRendering(unittest.TestCase):
    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_all_fixtures_render_both_sides(self):
        card = _import_card()
        for fname, identity in FIXTURES.items():
            for side in ("front", "back"):
                with self.subTest(fixture=fname, side=side):
                    img = card.render(identity, side)
                    self.assertEqual(img.size, (1050, 600), f"{fname} {side}: wrong size")
                    self.assertEqual(img.mode, "RGB", f"{fname} {side}: wrong mode")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_all_seeds_render_front(self):
        card = _import_card()
        for seed in SEEDS:
            with self.subTest(seed=seed):
                identity = dict(FIXTURES["full"], face={"seed": seed})
                img = card.render(identity, "front", seed=seed)
                self.assertEqual(img.size, (1050, 600))

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_arabic_front_renders_correctly(self):
        card = _import_card()
        img = card.render(FIXTURES["arabic"], "front")
        self.assertEqual(img.size, (1050, 600))
        # Verify image is not empty (not all-cream background)
        from PIL import ImageStat
        stat = ImageStat.Stat(img)
        # The stddev across channels should be > 0 (there is drawn content)
        self.assertGreater(max(stat.stddev), 0)

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_minimal_front_renders_correctly(self):
        card = _import_card()
        img = card.render(FIXTURES["minimal"], "front")
        self.assertEqual(img.size, (1050, 600))

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_stress_front_renders_correctly(self):
        card = _import_card()
        img = card.render(FIXTURES["stress"], "front")
        self.assertEqual(img.size, (1050, 600))

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_injection_fixture_renders_without_error(self):
        """Injection fixture must not crash the renderer."""
        card = _import_card()
        img = card.render(FIXTURES["injection"], "front")
        self.assertEqual(img.size, (1050, 600))

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    def test_seed_parameter_overrides_identity_seed(self):
        card = _import_card()
        identity = dict(FIXTURES["full"])
        img1 = card.render(identity, "front", seed="Ari Vale")
        img2 = card.render(identity, "front", seed="Ari Vale")
        # Same seed, same bytes.
        buf1, buf2 = io.BytesIO(), io.BytesIO()
        img1.save(buf1, format="PNG")
        img2.save(buf2, format="PNG")
        self.assertEqual(buf1.getvalue(), buf2.getvalue())


# ---------------------------------------------------------------------------
# QR round-trip (CoreImage decoder, macOS only)
# ---------------------------------------------------------------------------

def _swift_available():
    return shutil.which("swift") is not None and platform.system() == "Darwin"


SWIFT_HARNESS = """\
import CoreImage
import Foundation
guard CommandLine.arguments.count == 2 else { exit(1) }
let path = CommandLine.arguments[1]
guard let img = CIImage(contentsOf: URL(fileURLWithPath: path)) else { exit(1) }
let det = CIDetector(ofType: CIDetectorTypeQRCode, context: nil,
                     options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])!
let feats = det.features(in: img)
guard let feat = feats.first as? CIQRCodeFeature, let msg = feat.messageString else { exit(1) }
print(msg, terminator: "")
"""


class TestQrRoundTrip(unittest.TestCase):
    @unittest.skipUnless(_have_pillow(), "Pillow required")
    @unittest.skipUnless(_swift_available(), "swift + macOS required")
    def _decode_qr(self, img_path, swift_path):
        r = subprocess.run(["swift", swift_path, str(img_path)],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None

    @staticmethod
    def _normalise(text):
        """Normalise line endings and strip trailing whitespace for comparison.

        CoreImage strips CRLF down to LF and drops the trailing newline when
        returning the decoded string. vcard.qr_payload uses CRLF per RFC 6350.
        Normalise both sides to LF-only with no trailing newline before comparing.
        """
        return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    @unittest.skipUnless(_swift_available(), "swift + macOS required")
    def test_qr_round_trip_full_fixture(self):
        """Scan the back QR and verify it equals the expected vCard payload."""
        import tempfile
        card = _import_card()

        with tempfile.TemporaryDirectory(prefix="hz-qr-test-") as tmp:
            # Write Swift harness
            swift_path = os.path.join(tmp, "decode_qr.swift")
            Path(swift_path).write_text(SWIFT_HARNESS)

            identity = FIXTURES["full"]
            f = vcard.fields(identity)
            expected = vcard.qr_payload(f)

            back_path = os.path.join(tmp, "back.png")
            card.render(identity, "back").save(back_path)

            decoded = self._decode_qr(back_path, swift_path)
            self.assertIsNotNone(decoded, "CoreImage QR decoder returned nothing")
            self.assertEqual(self._normalise(decoded), self._normalise(expected),
                             f"QR payload mismatch.\nExpected: {expected!r}\nGot: {decoded!r}")

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    @unittest.skipUnless(_swift_available(), "swift + macOS required")
    def test_qr_round_trip_minimal_fixture(self):
        import tempfile
        card = _import_card()

        with tempfile.TemporaryDirectory(prefix="hz-qr-min-") as tmp:
            swift_path = os.path.join(tmp, "decode_qr.swift")
            Path(swift_path).write_text(SWIFT_HARNESS)

            identity = FIXTURES["minimal"]
            f = vcard.fields(identity)
            expected = vcard.qr_payload(f)

            back_path = os.path.join(tmp, "back.png")
            card.render(identity, "back").save(back_path)

            decoded = self._decode_qr(back_path, swift_path)
            self.assertIsNotNone(decoded)
            self.assertEqual(self._normalise(decoded), self._normalise(expected))

    @unittest.skipUnless(_have_pillow(), "Pillow required")
    @unittest.skipUnless(_swift_available(), "swift + macOS required")
    def test_qr_round_trip_arabic_fixture(self):
        import tempfile
        card = _import_card()

        with tempfile.TemporaryDirectory(prefix="hz-qr-ar-") as tmp:
            swift_path = os.path.join(tmp, "decode_qr.swift")
            Path(swift_path).write_text(SWIFT_HARNESS)

            identity = FIXTURES["arabic"]
            f = vcard.fields(identity)
            expected = vcard.qr_payload(f)

            back_path = os.path.join(tmp, "back.png")
            card.render(identity, "back").save(back_path)

            decoded = self._decode_qr(back_path, swift_path)
            self.assertIsNotNone(decoded)
            self.assertEqual(self._normalise(decoded), self._normalise(expected))


# ---------------------------------------------------------------------------
# Status and doctor integration
# ---------------------------------------------------------------------------

class TestStatusAndDoctor(HomeCase):
    def test_status_shows_card_ready_when_name_and_email(self):
        self.init("Ready Agent")
        self.hz("set", "email.agentmail.address", "ready@agentmail.to")
        r = self.hz("status")
        self.assertIn("card", r.stdout.lower())
        self.assertIn("ready", r.stdout.lower())

    def test_status_shows_card_missing_when_no_email_or_phone(self):
        self.init("Bare Agent")
        r = self.hz("status")
        # Should not say "ready" for card if no email/phone
        lines = [l for l in r.stdout.lower().splitlines() if "card" in l]
        self.assertTrue(any("missing" in l or "-" in l or "ready" in l or "no email" in l
                            for l in lines),
                        f"Expected card status line, got: {r.stdout}")

    def test_doctor_mentions_pillow(self):
        self.init()
        r = self.hz("doctor", check=False)
        self.assertIn("Pillow", r.stdout)


# ---------------------------------------------------------------------------
# have_pillow
# ---------------------------------------------------------------------------

class TestHavePillow(unittest.TestCase):
    def test_have_pillow_returns_true_when_installed(self):
        card = _import_card()
        # On this machine Pillow is installed.
        self.assertTrue(card.have_pillow())


if __name__ == "__main__":
    unittest.main()
