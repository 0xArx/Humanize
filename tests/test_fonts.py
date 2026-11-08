"""Font file tests: presence, loadability, size, and LICENSE coverage.

The FONTS table maps a human label to the file path relative to scripts/fonts/.
The card renderer (scripts/card.py) uses these exact paths.
"""
import unittest
from pathlib import Path

from helpers import ROOT

FONTS_DIR = ROOT / "scripts" / "fonts"

# FONTS table: label -> path relative to scripts/fonts/
# The card renderer imports this dict to locate each typeface.
FONTS = {
    "Instrument Serif Regular":      "ttf/InstrumentSerif-Regular.ttf",
    "Instrument Serif Italic":       "ttf/InstrumentSerif-Italic.ttf",
    "IBM Plex Sans Variable":        "ttf/IBMPlexSans-Variable.ttf",
    "IBM Plex Mono Regular":         "ttf/IBMPlexMono-Regular.ttf",
    "IBM Plex Mono Medium":          "ttf/IBMPlexMono-Medium.ttf",
    "Noto Naskh Arabic Variable":    "ttf/NotoNaskhArabic-Variable.ttf",
}

# Per-file size cap: variable fonts are larger than statics; 600 KB covers all.
SIZE_CAP = 600 * 1024

# Families whose names must appear in LICENSE.md (the ttf/ section).
LICENSE_FAMILIES = [
    "Instrument Serif",
    "IBM Plex Sans",
    "IBM Plex Mono",
    "Noto Naskh Arabic",
]


class FontFilesExistTest(unittest.TestCase):
    def test_every_font_file_exists(self):
        for label, rel in FONTS.items():
            path = FONTS_DIR / rel
            self.assertTrue(path.exists(), f"{label}: {rel} not found under scripts/fonts/")

    def test_every_font_file_is_a_regular_file(self):
        for label, rel in FONTS.items():
            path = FONTS_DIR / rel
            if path.exists():
                self.assertTrue(path.is_file(), f"{label}: {rel} is not a regular file")


class FontSizeTest(unittest.TestCase):
    def test_every_font_file_is_under_size_cap(self):
        for label, rel in FONTS.items():
            path = FONTS_DIR / rel
            if not path.exists():
                self.skipTest(f"{rel} missing, skipping size check")
            size = path.stat().st_size
            self.assertLessEqual(
                size, SIZE_CAP,
                f"{label} ({rel}) is {size} bytes, over the {SIZE_CAP}-byte cap"
            )


class FontLoadTest(unittest.TestCase):
    """Each font must load in Pillow at 12 px, 24 px, and 48 px and render Latin text."""

    def _load_and_render(self, path, size, text="Agent Ag"):
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype(str(path), size)
        img = Image.new("RGB", (400, size + 20), (245, 242, 234))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), text, font=font, fill=(24, 22, 20))

    def test_latin_fonts_load_and_render(self):
        latin_keys = [k for k in FONTS if "Arabic" not in k]
        for label in latin_keys:
            rel = FONTS[label]
            path = FONTS_DIR / rel
            if not path.exists():
                self.skipTest(f"{rel} missing")
            for size in (12, 24, 48):
                try:
                    self._load_and_render(path, size)
                except Exception as exc:
                    self.fail(f"{label} @{size}px: {exc}")

    def test_arabic_font_loads_and_renders(self):
        label = "Noto Naskh Arabic Variable"
        rel = FONTS[label]
        path = FONTS_DIR / rel
        if not path.exists():
            self.skipTest(f"{rel} missing")
        from PIL import Image, ImageDraw, ImageFont
        arabic_text = "مرحبا"  # مرحبا
        for size in (12, 24, 48):
            try:
                font = ImageFont.truetype(str(path), size)
                img = Image.new("RGB", (300, size + 20), (245, 242, 234))
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), arabic_text, font=font, fill=(24, 22, 20),
                          direction="rtl")
            except Exception as exc:
                self.fail(f"{label} @{size}px with Arabic text: {exc}")


class LicenseMdTest(unittest.TestCase):
    def test_license_md_exists(self):
        self.assertTrue((FONTS_DIR / "LICENSE.md").exists())

    def test_license_md_mentions_every_family(self):
        text = (FONTS_DIR / "LICENSE.md").read_text()
        for family in LICENSE_FAMILIES:
            self.assertIn(family, text,
                          f"LICENSE.md does not mention '{family}'")

    def test_license_md_mentions_sil_ofl(self):
        text = (FONTS_DIR / "LICENSE.md").read_text()
        self.assertIn("SIL Open Font License", text)


if __name__ == "__main__":
    unittest.main()
