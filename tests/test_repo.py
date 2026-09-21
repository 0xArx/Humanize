"""The repo checks itself: docs match code, links resolve, layers are complete, nothing leaks."""
import json
import re
import subprocess
import unittest
from pathlib import Path

from helpers import ROOT

TEXT = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        and p.suffix in {".md", ".py", ".js", ".html", ".json", ".sh", ".yml", ".css", ".txt"} and "fonts" not in p.parts[-2:-1]]
DOCS = [p for p in TEXT if p.suffix == ".md"]


def frontmatter(path):
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.S)
    return dict(re.findall(r"^(\w+): (.*)$", m.group(1), re.M)) if m else {}


class SkillTests(unittest.TestCase):
    def test_frontmatter_is_valid_for_skill_loaders(self):
        fm = frontmatter(ROOT / "SKILL.md")
        self.assertEqual(fm["name"], "humanize")
        self.assertRegex(fm["name"], r"^[a-z0-9-]{1,64}$")
        self.assertTrue(0 < len(fm["description"]) <= 1024, f"description is {len(fm['description'])} chars, the limit is 1024")
        self.assertIn("Use when", fm["description"])

    def test_skill_md_stays_a_short_router(self):
        self.assertLessEqual((ROOT / "SKILL.md").read_text().count("\n"), 260, "move detail into layers/")

    def test_there_is_one_file_per_layer_and_skill_md_links_each(self):
        files = sorted((ROOT / "layers").glob("*.md"))
        self.assertEqual([f.name[:2] for f in files], [f"{i:02d}" for i in range(24)])
        skill = (ROOT / "SKILL.md").read_text()
        for i, f in enumerate(files):
            self.assertRegex(f.read_text().splitlines()[0], rf"^# Layer {i}: \S", f.name)
            self.assertIn(f"layers/{f.name}", skill, f"SKILL.md must link {f.name}")
            body = f.read_text()
            for field in ("**Gives", "**Human needed:**", "**Identity keys:**") if i not in () else ():
                self.assertIn(field, body, f"{f.name} is missing {field}")

    def test_dashboard_layer_docs_match_the_files(self):
        html = (ROOT / "scripts" / "dashboard.html").read_text()
        slug = json.loads(re.sub(r"(\d+):", r'"\1":', re.search(r"const SLUG = (\{.*?\});", html).group(1)))
        files = {f.name[:2]: f.name[3:-3] for f in (ROOT / "layers").glob("*.md")}
        self.assertEqual({f"{int(k):02d}": v for k, v in slug.items()}, files)

    def test_dashboard_only_reads_keys_the_template_has(self):
        html = (ROOT / "scripts" / "dashboard.html").read_text()
        tpl = json.loads((ROOT / "identity.template.json").read_text())
        skip = {"layers", "accounts", "social", "messaging", "brain", "email.mailgent.api_key"}
        for path in set(re.findall(r'\bg\(i,\s*"([a-z_.]+)"\)', html)):
            if path in skip or path.startswith(("layers.", "accounts.", "social.", "messaging.")):
                continue
            cur = tpl
            for k in path.split("."):
                self.assertIsInstance(cur, dict, path)
                self.assertIn(k, cur, f"dashboard reads {path} but identity.template.json has no {k}")
                cur = cur[k]

    def test_identity_template_is_valid_and_private_by_default(self):
        tpl = json.loads((ROOT / "identity.template.json").read_text())
        self.assertEqual((tpl["name"], tpl["rules"], tpl["log"], tpl["dashboard_requests"]), ("", [], [], []))
        self.assertNotIn("orthogonal", json.dumps(tpl).lower())


class LinkTests(unittest.TestCase):
    def test_every_relative_markdown_link_resolves(self):
        for doc in DOCS:
            for target in re.findall(r"\]\(([^)\s#]+)(?:#[^)]*)?\)", doc.read_text()):
                if re.match(r"^(https?:|mailto:)", target):
                    continue
                self.assertTrue((doc.parent / target).exists(), f"{doc.relative_to(ROOT)} links to missing {target}")

    def test_files_named_in_backticks_exist(self):
        wanted = {"humanize.py", "install.sh", "identity.template.json", "scripts/dashboard.py", "scripts/dashboard.html", "scripts/orb.js",
                  "scripts/store.py", "scripts/self.py", "scripts/avatar.py", "scripts/memory.py", "SECURITY.md", "CHANGELOG.md",
                  "docs/architecture.md", "docs/providers.md", "docs/troubleshooting.md", "AGENTS.md", "LICENSE", "CONTRIBUTING.md"}
        for w in sorted(wanted):
            self.assertTrue((ROOT / w).exists(), w)

    def test_layer_cross_references_point_at_real_layers(self):
        for doc in [ROOT / "SKILL.md", *sorted((ROOT / "layers").glob("*.md"))]:
            for n in re.findall(r"\bLayers? (\d+)\b", doc.read_text()):
                self.assertLess(int(n), 24, f"{doc.name} mentions Layer {n}")


class HygieneTests(unittest.TestCase):
    def test_no_em_dashes(self):
        for p in TEXT:
            self.assertNotIn(chr(0x2014), p.read_text(), f"{p.relative_to(ROOT)} has an em dash")

    def test_the_marketplace_is_not_mentioned(self):
        for p in TEXT:
            if p.parts[-2] == "tests":
                continue
            low = p.read_text().lower()
            self.assertNotIn("orthogonal", low, p.relative_to(ROOT))
            self.assertNotIn("orth run", low, p.relative_to(ROOT))

    def test_no_secret_shaped_strings_are_committed(self):
        pats = [r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}", r"re_[A-Za-z0-9_]{24,}",
                r"sbp_[a-f0-9]{30,}", r"AKIA[0-9A-Z]{16}", r"xox[bp]-[A-Za-z0-9-]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"]
        for p in TEXT:
            if p.parts[-2] == "tests":
                continue
            for pat in pats:
                self.assertIsNone(re.search(pat, p.read_text()), f"{p.relative_to(ROOT)} looks like it contains a secret ({pat})")

    def test_gitignore_keeps_private_files_out(self):
        gi = (ROOT / ".gitignore").read_text()
        for entry in ("identity.json", "*.key", ".humanize/"):
            self.assertIn(entry, gi)

    def test_git_history_has_a_single_author_and_no_attribution_trailers(self):
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        r = subprocess.run(["git", "log", "--format=%an|%B"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            self.skipTest("git log unavailable")
        self.assertNotRegex(r.stdout, r"(?i)co-authored-by|generated with")
        authors = set(subprocess.run(["git", "log", "--format=%an"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")) - {""}
        self.assertEqual(authors, {"0xArx"})

    def test_python_files_are_standard_library_only(self):
        import ast, sys
        std = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else None
        local = {"store", "memory", "avatar", "helpers", "dashboard", "self", "orb"}
        optional = {"PIL", "fcntl"}
        for p in list(ROOT.glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
            for node in ast.walk(ast.parse(p.read_text())):
                names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
                for n in names:
                    if std is not None and n not in std and n not in local and n not in optional:
                        self.fail(f"{p.name} imports {n}, which is not in the standard library")


class VersionTests(unittest.TestCase):
    def test_versions_agree(self):
        v = re.search(r'__version__ = "([^"]+)"', (ROOT / "humanize.py").read_text()).group(1)
        self.assertEqual(re.search(r'VERSION = "([^"]+)"', (ROOT / "scripts" / "dashboard.py").read_text()).group(1), v)
        self.assertRegex((ROOT / "CHANGELOG.md").read_text(), rf"## \[{re.escape(v)}\]")


class ScriptTests(unittest.TestCase):
    def test_install_script_parses_in_posix_sh(self):
        r = subprocess.run(["sh", "-n", str(ROOT / "install.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_dashboard_inline_script_is_valid_javascript(self):
        import shutil, tempfile
        if not shutil.which("node"):
            self.skipTest("node not installed")
        html = (ROOT / "scripts" / "dashboard.html").read_text()
        js = re.search(r'<script nonce="__HZ_NONCE__">(.*?)</script>', html, re.S).group(1)
        f = Path(tempfile.mkdtemp()) / "inline.js"
        f.write_text(js)
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run(["node", "--check", str(ROOT / "scripts" / "orb.js")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
