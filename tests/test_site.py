"""The website must stay true to the repo and must obey the same rules as the product."""
import html
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import ROOT

SITE = ROOT / "site"
PAGE = (SITE / "index.html").read_text()


def readme_rows():
    """{layer number: (name, who is needed)} from the README table."""
    rows = {}
    for m in re.finditer(r"^\| (\d+) \| \[([^\]]+)\]\([^)]*\) \| [^|]+ \| ([^|]+) \|$", (ROOT / "README.md").read_text(), re.M):
        rows[int(m.group(1))] = (m.group(2), m.group(3).strip())
    return rows


class FilesTests(unittest.TestCase):
    def test_everything_the_page_needs_is_there(self):
        for f in ("index.html", "styles.css", "app.js", "early.js", "orb.js", "vercel.json", "favicon.svg", "fonts/fonts.css",
                  "fonts/InstrumentSerif-400.woff2", "fonts/IBMPlexSans.woff2", "img/dashboard-light.webp", "img/dashboard-dark.webp"):
            self.assertTrue((SITE / f).is_file(), f)
        refs = set(re.findall(r'(?:src|href)="(/[^"#?]+)"', PAGE))
        for ref in refs:
            self.assertTrue((SITE / ref.lstrip("/")).exists(), f"index.html references missing {ref}")
        for css in re.findall(r"url\(/?([^)]+)\)", (SITE / "fonts" / "fonts.css").read_text()):
            self.assertTrue((SITE / css.lstrip("/")).exists(), css)

    def test_the_avatar_code_is_the_products_own(self):
        self.assertEqual((SITE / "orb.js").read_bytes(), (ROOT / "scripts" / "orb.js").read_bytes(),
                         "site/orb.js must be an exact copy of scripts/orb.js. Copy it again after changing the product.")

    def test_fonts_are_the_bundled_ones(self):
        for f in (ROOT / "scripts" / "fonts").glob("*.woff2"):
            self.assertEqual((SITE / "fonts" / f.name).read_bytes(), f.read_bytes(), f.name)


class SafetyTests(unittest.TestCase):
    def test_no_third_party_loads_anywhere(self):
        ext = r"(?:https?:)?//(?!127\.0\.0\.1|localhost)[a-z0-9.-]+\.[a-z]{2,}"
        for name in ("index.html", "styles.css", "app.js", "early.js"):
            text = (SITE / name).read_text().replace("http://www.w3.org/2000/svg", "")
            for how in (rf'\bsrc\s*=\s*["\']{ext}', rf'<link[^>]+href\s*=\s*["\']{ext}', rf'url\(\s*["\']?{ext}', rf"@import[^;]*{ext}",
                        rf"\bfetch\(", r"XMLHttpRequest|WebSocket\(|EventSource\(|sendBeacon"):
                self.assertIsNone(re.search(how, text, re.I), f"{name} loads from outside: {how}")

    def test_the_page_uses_nothing_a_strict_csp_would_block(self):
        self.assertIsNone(re.search(r"<style", PAGE, re.I), "no <style> block")
        self.assertIsNone(re.search(r"\sstyle\s*=", PAGE, re.I), "no inline style attribute")
        self.assertIsNone(re.search(r"\son[a-z]+\s*=", PAGE, re.I), "no inline event handler")
        for body in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", PAGE, re.S):
            self.assertEqual(body.strip(), "", "no inline script")
        self.assertNotIn("javascript:", PAGE)

    def test_vercel_config_sends_a_strict_csp_and_security_headers(self):
        cfg = json.loads((SITE / "vercel.json").read_text())
        headers = {h["key"]: h["value"] for r in cfg["headers"] if r["source"] == "/(.*)" for h in r["headers"]}
        csp = headers["Content-Security-Policy"]
        for want in ("default-src 'none'", "script-src 'self'", "style-src 'self'", "frame-ancestors 'none'", "base-uri 'none'", "form-action 'none'"):
            self.assertIn(want, csp)
        self.assertNotIn("unsafe", csp)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("Referrer-Policy", headers)

    @unittest.skipUnless(shutil.which("node"), "node is needed to check JavaScript syntax")
    def test_scripts_parse(self):
        for f in ("app.js", "early.js", "orb.js"):
            r = subprocess.run(["node", "--check", str(SITE / f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{f}: {r.stderr}")


class HtmlTests(unittest.TestCase):
    def test_basic_structure(self):
        self.assertRegex(PAGE, r'<html lang="en">')
        self.assertEqual(len(re.findall(r"<h1[ >]", PAGE)), 1)
        self.assertIn('<meta name="viewport"', PAGE)
        ids = re.findall(r'\bid="([^"]+)"', PAGE)
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids")
        for target in re.findall(r'(?:href|aria-controls)="#?([A-Za-z][\w-]*)"', PAGE):
            if target in ("top",):
                continue
            self.assertIn(target, ids + ["what", "how", "layers", "dashboard", "security", "use", "status", "faq"], f"dangling reference to #{target}")
        for img in re.findall(r"<img[^>]*>", PAGE):
            self.assertRegex(img, r'\balt="[^"]{10,}"')
            self.assertRegex(img, r'\bwidth="\d+"')
            self.assertRegex(img, r'\bheight="\d+"')

    def test_the_nav_links_point_at_real_sections(self):
        for sec in re.findall(r'data-sec="(\w+)"', PAGE):
            self.assertIn(f'id="{sec}"', PAGE)


class TruthTests(unittest.TestCase):
    """The page makes claims. Each one is checked against the repo."""

    def cards(self):
        out = {}
        for m in re.finditer(r'<article class="lcard[^"]*" data-n="(\d+)" data-group="(\w+)" data-need="(\w+)">(.*?)</article>', PAGE, re.S):
            body = m.group(4)
            out[int(m.group(1))] = dict(group=m.group(2), need=m.group(3),
                                        title=html.unescape(re.search(r"<h3>(.*?)</h3>", body).group(1)),
                                        note=html.unescape(re.search(r'need-note"><span>[^<]*</span> (.*?)</p>', body).group(1)) if "need-note" in body else "nothing")
        return out

    def test_the_layer_cards_match_the_repo(self):
        cards, rows = self.cards(), readme_rows()
        self.assertEqual(sorted(cards), list(range(24)))
        self.assertEqual(sorted(rows), list(range(24)), "the README table must list every layer")
        for n in range(24):
            self.assertEqual(cards[n]["title"], rows[n][0], f"layer {n} name")
            who = rows[n][1]
            self.assertEqual(cards[n]["need"], "nobody" if who.startswith("nothing") else "person", f"layer {n}: who is needed")
            if who != "nothing":
                self.assertEqual(cards[n]["note"], who, f"layer {n}: what a person is needed for")
        files = {int(f.name[:2]): f.read_text().splitlines()[0] for f in (ROOT / "layers").glob("*.md")}
        for n in range(24):
            self.assertTrue(files[n].startswith(f"# Layer {n}: "))

    def test_the_groups_match_the_dashboard(self):
        dash = (ROOT / "scripts" / "dashboard.html").read_text()
        groups = {}
        for name, nums in re.findall(r'\["(\w+)", \[([\d, ]+)\]\]', re.search(r"const GROUPS = (\[.*?\]);", dash).group(1)):
            for n in nums.split(","):
                groups[int(n)] = name
        for n, c in self.cards().items():
            self.assertEqual(c["group"], groups[n], f"layer {n} group")

    def test_the_numbers_are_not_bigger_than_the_truth(self):
        claimed = {b: int(a) for a, b in re.findall(r'<b>(\d+)</b><span>([^<]+)</span>', PAGE)}
        tests = unittest.TestLoader().discover(str(ROOT / "tests")).countTestCases()
        for label, n in claimed.items():
            if "automated tests" in label:
                self.assertLessEqual(n, tests, "the page claims more tests than exist")
            if "layer" in label and "guide" in label:
                self.assertEqual(n, 24)
        matrix = (ROOT / ".github" / "workflows" / "ci.yml").read_text().count("- { os:")
        self.assertIn(f"<b>{matrix}</b><span>CI jobs", PAGE)

    def test_the_version_matches(self):
        v = re.search(r'__version__ = "([^"]+)"', (ROOT / "humanize.py").read_text()).group(1)
        self.assertIn(f"Version {v}.", PAGE)

    def test_the_provider_table_lists_only_providers_the_ledger_knows(self):
        ledger = (ROOT / "docs" / "providers.md").read_text()
        alias = {"x402 Bazaar": "x402 and the Bazaar"}
        for name in re.findall(r'<span role="cell">([A-Za-z0-9 ]+)</span><span role="cell" class="y">', PAGE):
            self.assertIn(alias.get(name, name), ledger, f"{name} is on the page but not in docs/providers.md")

    def test_the_page_never_says_a_live_signup_was_run(self):
        self.assertIn("Nothing that creates an account has been run yet", PAGE)
        for row in re.findall(r'<span role="cell">(?:Mailgent|AgentMail|AgentPhone|Dial)</span>(.*?)</div>', PAGE):
            self.assertIn("not yet", row)


if __name__ == "__main__":
    unittest.main()
