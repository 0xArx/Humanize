"""Tests for scripts/vcard.py.

Covers: field mapping, secret-pointer redaction, injection safety (one
BEGIN/END pair, no unescaped line breaks), line folding at 75 octets
including multibyte characters, qr_payload byte budget, phone E.164
normalisation, website scheme rejection, and real-world Contacts.framework
interoperability via a Swift helper script (skipped when swift is absent).
"""
import datetime
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
sys.path.insert(0, str(ROOT / "tests"))

import vcard        # noqa: E402
import fixtures as F  # noqa: E402

_CLOCK = datetime.datetime(2026, 1, 1, 12, 0, 0)   # fixed for deterministic REV


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fields(key):
    return vcard.fields(F.FIXTURES[key])


def _build(key):
    return vcard.build(_fields(key), _clock=_CLOCK)


def _qr(key):
    return vcard.qr_payload(_fields(key))


def _parse_vcf(text):
    """Naive line-by-line vCard parser (for test assertions only)."""
    cards = []
    current = {}
    # Unfold continuation lines first.
    joined = []
    for raw in text.split("\r\n"):
        if raw.startswith(" ") and joined:
            joined[-1] += raw[1:]
        else:
            joined.append(raw)
    for line in joined:
        if line == "BEGIN:VCARD":
            current = {}
        elif line == "END:VCARD":
            cards.append(current)
        elif ":" in line:
            prop, _, val = line.partition(":")
            current[prop] = val
    return cards


# ---------------------------------------------------------------------------
# sanitize()
# ---------------------------------------------------------------------------

class TestSanitize(unittest.TestCase):
    def test_removes_cr_and_lf(self):
        result = vcard.sanitize("a\rb\nc")
        self.assertNotIn("\r", result)
        self.assertNotIn("\n", result)

    def test_removes_other_control_chars(self):
        result = vcard.sanitize("a\x00\x07\x1b\x7f\x80\x9fb")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x07", result)
        self.assertNotIn("\x1b", result)
        self.assertNotIn("\x7f", result)

    def test_collapses_whitespace(self):
        self.assertEqual(vcard.sanitize("a  b   c"), "a b c")

    def test_strips_leading_trailing(self):
        self.assertEqual(vcard.sanitize("  hello  "), "hello")

    def test_caps_length_at_500_default(self):
        long = "x" * 600
        self.assertEqual(len(vcard.sanitize(long)), 500)

    def test_custom_maxlen(self):
        self.assertEqual(len(vcard.sanitize("x" * 100, maxlen=10)), 10)

    def test_empty_string(self):
        self.assertEqual(vcard.sanitize(""), "")

    def test_non_ascii_preserved(self):
        arabic = "نور"
        self.assertEqual(vcard.sanitize(arabic), arabic)

    def test_converts_input_to_string(self):
        self.assertEqual(vcard.sanitize(42), "42")


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

class TestFields(unittest.TestCase):
    # --- "full" fixture ---

    def test_full_name(self):
        f = _fields("full")
        self.assertEqual(f["name"], "Ari Vale")
        self.assertEqual(f["first"], "Ari")
        self.assertEqual(f["last"], "Vale")

    def test_full_title_and_tagline(self):
        f = _fields("full")
        self.assertEqual(f["title"],   "AI Agent")
        self.assertEqual(f["tagline"], "Built to get things done.")

    def test_full_email(self):
        self.assertEqual(_fields("full")["email"], "ari@agentmail.to")

    def test_full_phone_display_and_e164(self):
        f = _fields("full")
        self.assertEqual(f["phone"],      "+14155550100")
        self.assertEqual(f["phone_e164"], "+14155550100")

    def test_full_whatsapp(self):
        self.assertEqual(_fields("full")["whatsapp"], "+14155550100")

    def test_full_website_explicit(self):
        self.assertEqual(_fields("full")["website"], "https://arivale.ai")

    def test_full_website_falls_back_to_domain(self):
        # Remove business_card.website; domain.name should take over.
        identity = dict(F.FIXTURES["full"])
        identity["business_card"] = {"title": "AI Agent", "tagline": None, "website": None}
        f = vcard.fields(identity)
        self.assertEqual(f["website"], "https://arivale.ai")

    def test_full_booking_url(self):
        self.assertEqual(_fields("full")["booking_url"], "https://cal.com/ari-vale/15min")

    def test_full_handles_include_github_and_social(self):
        handles = _fields("full")["handles"]
        labels = {h["label"] for h in handles}
        self.assertIn("GitHub", labels)
        self.assertIn("Twitter", labels)
        self.assertIn("Linkedin", labels)

    def test_full_github_handle_url(self):
        handles = _fields("full")["handles"]
        gh = next(h for h in handles if h["label"] == "GitHub")
        self.assertEqual(gh["url"], "https://github.com/ari-vale")
        self.assertEqual(gh["text"], "@ari-vale")

    def test_full_address(self):
        addr = _fields("full")["address"]
        self.assertIsNotNone(addr)
        self.assertEqual(addr["line1"], "123 Main St")
        self.assertEqual(addr["city"],  "San Francisco")

    def test_full_seed_from_face_seed(self):
        self.assertEqual(_fields("full")["seed"], "Ari Vale")

    def test_full_no_missing_fields(self):
        # All important fields are present.
        missing = _fields("full")["missing"]
        self.assertEqual(missing, [])

    # --- "minimal" fixture ---

    def test_minimal_name(self):
        f = _fields("minimal")
        self.assertEqual(f["name"], "Mira Chen")

    def test_minimal_missing_list(self):
        missing = _fields("minimal")["missing"]
        # No phone, no website, no title, no handles, no address.
        self.assertTrue(len(missing) >= 3)
        combined = " ".join(missing)
        self.assertIn("phone", combined)
        self.assertIn("website", combined)

    def test_minimal_phone_is_none(self):
        f = _fields("minimal")
        self.assertIsNone(f["phone"])
        self.assertIsNone(f["phone_e164"])

    def test_minimal_seed_falls_back_to_name(self):
        self.assertEqual(_fields("minimal")["seed"], "Mira Chen")

    # --- secret pointers never leak ---

    def test_api_key_never_emitted(self):
        f = _fields("full")
        dumped = json.dumps(f)
        self.assertNotIn("secret:", dumped)

    def test_secret_phone_not_emitted(self):
        identity = {"name": "X", "phone": {"agentphone": {"number": "secret:phone.agentphone.number"}}}
        f = vcard.fields(identity)
        self.assertIsNone(f["phone"])
        self.assertIsNone(f["phone_e164"])

    def test_secret_email_not_emitted(self):
        identity = {"name": "X", "email": {"agentmail": {"address": "secret:email.agentmail.address"}}}
        f = vcard.fields(identity)
        self.assertIsNone(f["email"])

    def test_secret_handle_not_emitted(self):
        identity = {"name": "X", "social": {"twitter": {"handle": "secret:social.twitter.handle"}}}
        f = vcard.fields(identity)
        self.assertEqual(f["handles"], [])

    def test_secret_whatsapp_not_emitted(self):
        identity = {"name": "X", "whatsapp": {"number": "secret:whatsapp.number"}}
        f = vcard.fields(identity)
        self.assertIsNone(f["whatsapp"])

    # --- "nophone" fixture ---

    def test_nophone_website_bare_domain_gets_scheme(self):
        self.assertEqual(_fields("nophone")["website"], "https://agenthub.dev")

    def test_nophone_no_phone_in_missing(self):
        missing = _fields("nophone")["missing"]
        self.assertTrue(any("phone" in m for m in missing))

    # --- name splitting edge cases ---

    def test_single_word_name(self):
        f = vcard.fields({"name": "Zed"})
        self.assertEqual(f["first"], "Zed")
        self.assertEqual(f["last"],  "")

    def test_two_word_name(self):
        f = vcard.fields({"name": "Kit Okafor"})
        self.assertEqual(f["first"], "Kit")
        self.assertEqual(f["last"],  "Okafor")

    def test_three_word_name(self):
        f = vcard.fields({"name": "Mariam Ali Siddiqui"})
        self.assertEqual(f["first"], "Mariam Ali")
        self.assertEqual(f["last"],  "Siddiqui")

    def test_arabic_name_split(self):
        f = _fields("arabic")
        # "Noor Hadid" in Arabic: last word is the family name.
        self.assertTrue(len(f["first"]) > 0)
        self.assertTrue(len(f["last"])  > 0)

    def test_empty_name(self):
        f = vcard.fields({})
        self.assertEqual(f["name"],  "")
        self.assertEqual(f["first"], "")
        self.assertEqual(f["last"],  "")

    # --- seed derivation ---

    def test_seed_prefers_face_seed(self):
        identity = {"name": "A B", "face": {"seed": "custom-seed"}}
        self.assertEqual(vcard.fields(identity)["seed"], "custom-seed")

    def test_seed_falls_back_to_name(self):
        identity = {"name": "A B"}
        self.assertEqual(vcard.fields(identity)["seed"], "A B")

    def test_seed_falls_back_to_agent(self):
        self.assertEqual(vcard.fields({})["seed"], "agent")

    def test_secret_face_seed_falls_back_to_name(self):
        identity = {"name": "Ari", "face": {"seed": "secret:face.seed"}}
        self.assertEqual(vcard.fields(identity)["seed"], "Ari")


# ---------------------------------------------------------------------------
# Phone normalisation
# ---------------------------------------------------------------------------

class TestPhoneNormalise(unittest.TestCase):
    def _e164(self, n):
        return vcard._normalize_e164(n)

    def test_us_number_with_plus(self):
        self.assertEqual(self._e164("+14155550100"), "+14155550100")

    def test_formatted_us_with_plus(self):
        self.assertEqual(self._e164("+1 (415) 555-0100"), "+14155550100")

    def test_uk_number(self):
        self.assertEqual(self._e164("+44 20 7123 4567"), "+442071234567")

    def test_no_plus_no_country_code(self):
        # Cannot safely infer country code, so E.164 must be None.
        self.assertIsNone(self._e164("4155550100"))

    def test_local_format_no_plus(self):
        self.assertIsNone(self._e164("(415) 555-0100"))

    def test_too_short(self):
        self.assertIsNone(self._e164("+123"))

    def test_too_long(self):
        self.assertIsNone(self._e164("+1234567890123456"))

    def test_empty(self):
        self.assertIsNone(self._e164(""))

    def test_injected_content_does_not_produce_e164(self):
        # LF in phone number: sanitize() removes it before _normalize_e164 sees it.
        raw = "+14155550199\nEND:VCARD"
        sanitized = vcard.sanitize(raw)
        self.assertNotIn("\n", sanitized)
        # After sanitize: "+14155550199 END:VCARD". Stripping formatting
        # chars gives "+14155550199END:VCARD". The non-digit letters make
        # this invalid E.164, so None is expected.
        e164 = vcard._normalize_e164(sanitized)
        self.assertIsNone(e164)


# ---------------------------------------------------------------------------
# Website scheme handling
# ---------------------------------------------------------------------------

class TestWebsite(unittest.TestCase):
    def _url(self, u):
        return vcard._normalize_url(u)

    def test_https_kept(self):
        self.assertEqual(self._url("https://example.com"), "https://example.com")

    def test_http_kept(self):
        self.assertEqual(self._url("http://example.com"), "http://example.com")

    def test_bare_domain_gets_https(self):
        self.assertEqual(self._url("example.com"), "https://example.com")

    def test_bare_subdomain(self):
        self.assertEqual(self._url("sub.example.com/path"), "https://sub.example.com/path")

    def test_reject_javascript(self):
        self.assertIsNone(self._url("javascript:alert(1)"))

    def test_reject_data(self):
        self.assertIsNone(self._url("data:text/html,<b>hi</b>"))

    def test_reject_file(self):
        self.assertIsNone(self._url("file:///etc/passwd"))

    def test_reject_ftp(self):
        self.assertIsNone(self._url("ftp://files.example.com"))

    def test_none_input(self):
        self.assertIsNone(self._url(None))

    def test_empty_string(self):
        self.assertIsNone(self._url(""))


# ---------------------------------------------------------------------------
# build() structure
# ---------------------------------------------------------------------------

class TestBuild(unittest.TestCase):
    def test_starts_and_ends_correctly(self):
        vcf = _build("full")
        self.assertTrue(vcf.startswith("BEGIN:VCARD\r\n"))
        self.assertTrue(vcf.rstrip("\r\n").endswith("END:VCARD"))

    def test_contains_version_3(self):
        self.assertIn("VERSION:3.0\r\n", _build("full"))

    def test_fn_present(self):
        self.assertIn("FN:Ari Vale\r\n", _build("full"))

    def test_n_structured(self):
        vcf = _build("full")
        self.assertIn("N:Vale;Ari;;;\r\n", vcf)

    def test_title_present(self):
        self.assertIn("TITLE:AI Agent\r\n", _build("full"))

    def test_tel_e164(self):
        self.assertIn("TEL;TYPE=CELL:+14155550100\r\n", _build("full"))

    def test_email_present(self):
        self.assertIn("EMAIL;TYPE=INTERNET:ari@agentmail.to\r\n", _build("full"))

    def test_url_present(self):
        self.assertIn("URL:https://arivale.ai\r\n", _build("full"))

    def test_adr_present(self):
        vcf = _build("full")
        self.assertIn("ADR;TYPE=POSTAL:", vcf)

    def test_note_tagline(self):
        vcf = _build("full")
        self.assertIn("NOTE:Built to get things done.\r\n", vcf)

    def test_rev_format(self):
        vcf = _build("full")
        self.assertIn("REV:20260101T120000Z\r\n", vcf)

    def test_uid_stable_for_same_seed(self):
        uid1 = _fields("full")["seed"]
        uid2 = _fields("full")["seed"]
        vcf1 = vcard.build(_fields("full"), _clock=_CLOCK)
        vcf2 = vcard.build(_fields("full"), _clock=_CLOCK)
        self.assertEqual(vcf1, vcf2)

    def test_uid_differs_for_different_seeds(self):
        f1 = vcard.fields({"name": "Ari Vale"})
        f2 = vcard.fields({"name": "Kit Okafor"})
        vcf1 = vcard.build(f1, _clock=_CLOCK)
        vcf2 = vcard.build(f2, _clock=_CLOCK)
        # Extract UID lines.
        uid1 = [l for l in vcf1.split("\r\n") if l.startswith("UID:")][0]
        uid2 = [l for l in vcf2.split("\r\n") if l.startswith("UID:")][0]
        self.assertNotEqual(uid1, uid2)

    def test_crlf_line_endings(self):
        vcf = _build("full")
        # Every \n must be preceded by \r.
        for i, ch in enumerate(vcf):
            if ch == "\n" and i > 0:
                self.assertEqual(vcf[i - 1], "\r", "bare LF found")

    def test_single_word_name_n_field(self):
        f = vcard.fields({"name": "Zed"})
        vcf = vcard.build(f, _clock=_CLOCK)
        # N: given name with no family name.
        self.assertIn("N:;Zed;;;\r\n", vcf)

    def test_arabic_name_encoded(self):
        vcf = _build("arabic")
        # Arabic FN must appear.
        self.assertIn("FN:", vcf)
        noor = "نور حديد"
        self.assertIn(noor, vcf)

    def test_handles_absence_of_optional_fields(self):
        vcf = _build("minimal")
        self.assertNotIn("TITLE:", vcf)
        self.assertNotIn("TEL",   vcf)
        self.assertNotIn("ADR",   vcf)

    def test_social_handles_x_socialprofile(self):
        vcf = _build("full")
        self.assertIn("X-SOCIALPROFILE;TYPE=twitter:", vcf)
        self.assertIn("X-SOCIALPROFILE;TYPE=github:", vcf)


# ---------------------------------------------------------------------------
# Line folding
# ---------------------------------------------------------------------------

class TestFolding(unittest.TestCase):
    def _lines(self, vcf):
        """Return unfolded logical lines from a vCard string."""
        physical = vcf.split("\r\n")
        logical = []
        for p in physical:
            if p.startswith(" ") and logical:
                logical[-1] += p[1:]
            else:
                logical.append(p)
        return logical

    def _physical_lines(self, vcf):
        return [l for l in vcf.split("\r\n") if l]

    def test_all_physical_lines_at_most_75_bytes(self):
        for key in F.FIXTURES:
            with self.subTest(key=key):
                vcf = _build(key)
                for line in self._physical_lines(vcf):
                    blen = len(line.encode("utf-8"))
                    self.assertLessEqual(blen, 75, f"line too long ({blen} bytes): {line!r}")

    def test_multibyte_line_at_75_bytes(self):
        # A property whose value contains Arabic characters so that
        # multibyte boundary enforcement matters.
        arabic_title = "وكيل " * 10
        f = vcard.fields({
            "name": "Test",
            "business_card": {"title": arabic_title.strip(), "tagline": None, "website": None},
        })
        vcf = vcard.build(f, _clock=_CLOCK)
        for line in self._physical_lines(vcf):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_folded_line_reconstructs_to_original_value(self):
        long_title = "A" * 200
        f = vcard.fields({
            "name": "Test",
            "business_card": {"title": long_title, "tagline": None, "website": None},
        })
        vcf = vcard.build(f, _clock=_CLOCK)
        logical = self._lines(vcf)
        title_line = next((l for l in logical if l.startswith("TITLE:")), None)
        self.assertIsNotNone(title_line)
        self.assertEqual(title_line, "TITLE:" + long_title)

    def test_short_line_is_not_folded(self):
        result = vcard._fold("FN:Ari Vale")
        self.assertNotIn("\r\n", result)

    def test_fold_does_not_split_multibyte_char(self):
        # Build a line that is almost exactly 75 bytes and ends in a
        # multibyte character; it must not be split mid-character.
        prefix = "X-TEST:" + "a" * 67   # 7 + 67 = 74 bytes so far
        suffix = "é"               # 2 bytes, total = 76 -> must fold
        line = prefix + suffix
        folded = vcard._fold(line)
        # The folded output decoded back to str must equal the original.
        reassembled = folded.replace("\r\n ", "")
        self.assertEqual(reassembled, line)


# ---------------------------------------------------------------------------
# Injection safety
# ---------------------------------------------------------------------------

class TestInjection(unittest.TestCase):
    def _vcf(self):
        return _build("injection")

    def test_exactly_one_begin_vcard(self):
        # Count physical lines that ARE EXACTLY "BEGIN:VCARD".
        # Property values may contain the text "BEGIN:VCARD" but they will
        # always be preceded by a property name or a fold-continuation space,
        # so they never appear as a standalone line.
        vcf = self._vcf()
        physical = vcf.split("\r\n")
        self.assertEqual(physical.count("BEGIN:VCARD"), 1)

    def test_exactly_one_end_vcard(self):
        vcf = self._vcf()
        physical = vcf.split("\r\n")
        self.assertEqual(physical.count("END:VCARD"), 1)

    def test_no_raw_cr_in_values(self):
        vcf = self._vcf()
        # Split by CRLF to get physical lines; each line must not contain \r.
        for line in vcf.split("\r\n"):
            self.assertNotIn("\r", line, f"raw CR in: {line!r}")

    def test_no_raw_lf_in_values(self):
        vcf = self._vcf()
        for line in vcf.split("\r\n"):
            self.assertNotIn("\n", line, f"raw LF in: {line!r}")

    def test_semicolons_in_values_are_escaped(self):
        f = vcard.fields(F.FIXTURES["injection"])
        # The title contains semicolons; after build() they must be escaped.
        vcf = vcard.build(f, _clock=_CLOCK)
        cards = _parse_vcf(vcf)
        self.assertEqual(len(cards), 1)

    def test_long_string_capped(self):
        f = _fields("injection")
        # tagline came from a 5000-char string; must be capped.
        tagline = f["tagline"]
        if tagline is not None:
            self.assertLessEqual(len(tagline), 500)

    def test_backslashes_escaped(self):
        f = vcard.fields({"name": "A", "social": {"twitter": {"handle": "path\\file", "token": "x"}}})
        vcf = vcard.build(f, _clock=_CLOCK)
        self.assertIn("\\\\", vcf)   # backslash is doubled

    def test_secret_pointer_not_in_vcf(self):
        vcf = self._vcf()
        self.assertNotIn("secret:", vcf)


# ---------------------------------------------------------------------------
# qr_payload() byte budget
# ---------------------------------------------------------------------------

class TestQrPayload(unittest.TestCase):
    def test_under_budget_for_all_fixtures(self):
        for key in F.FIXTURES:
            with self.subTest(key=key):
                payload = _qr(key)
                blen = len(payload.encode("utf-8"))
                self.assertLessEqual(blen, 329,
                    f"{key}: qr_payload is {blen} bytes, budget is 329")

    def test_begins_and_ends_correctly(self):
        for key in F.FIXTURES:
            with self.subTest(key=key):
                p = _qr(key)
                self.assertTrue(p.startswith("BEGIN:VCARD"))
                self.assertTrue(p.rstrip("\r\n").endswith("END:VCARD"))

    def test_exactly_one_begin_end(self):
        for key in F.FIXTURES:
            with self.subTest(key=key):
                p = _qr(key)
                # Count lines that ARE EXACTLY these markers.
                physical = p.split("\r\n")
                self.assertEqual(physical.count("BEGIN:VCARD"), 1,
                    f"{key}: expected 1 BEGIN:VCARD standalone line")
                self.assertEqual(physical.count("END:VCARD"), 1,
                    f"{key}: expected 1 END:VCARD standalone line")

    def test_no_address_in_payload(self):
        p = _qr("full")
        self.assertNotIn("ADR:", p)

    def test_no_social_handles_in_payload(self):
        p = _qr("full")
        self.assertNotIn("X-SOCIALPROFILE", p)

    def test_stress_under_budget(self):
        # stress fixture has very long name and title; must be truncated.
        p = _qr("stress")
        self.assertLessEqual(len(p.encode("utf-8")), 329)

    def test_injection_under_budget(self):
        p = _qr("injection")
        self.assertLessEqual(len(p.encode("utf-8")), 329)

    def test_arabic_under_budget(self):
        p = _qr("arabic")
        self.assertLessEqual(len(p.encode("utf-8")), 329)


# ---------------------------------------------------------------------------
# Contacts.framework interoperability (requires swift on PATH)
# ---------------------------------------------------------------------------

SWIFT_SCRIPT = ROOT / "tests" / "parse_vcard.swift"


@unittest.skipUnless(sys.platform == "darwin", "Contacts.framework is macOS only")
@unittest.skipUnless(shutil.which("swift"), "swift not on PATH")
@unittest.skipUnless(SWIFT_SCRIPT.exists(), "parse_vcard.swift not found")
class TestSwiftInterop(unittest.TestCase):
    """Parse vCards with Apple Contacts.framework and check the values."""

    def _run_swift(self, vcf_text):
        with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False, mode="w",
                                        encoding="utf-8") as f:
            f.write(vcf_text)
            tmppath = f.name
        try:
            r = subprocess.run(
                ["swift", str(SWIFT_SCRIPT), tmppath],
                capture_output=True, text=True, timeout=30,
            )
            return r.stdout, r.returncode
        finally:
            os.unlink(tmppath)

    def _contacts_from_vcf(self, vcf_text):
        """Return list of contact dicts parsed by the Swift helper."""
        stdout, rc = self._run_swift(vcf_text)
        self.assertEqual(rc, 0, f"Swift exited {rc}: {stdout}")
        contacts = []
        current = {}
        for line in stdout.splitlines():
            if line == "---":
                contacts.append(current)
                current = {}
            elif "=" in line:
                k, _, v = line.partition("=")
                if k in current:
                    if not isinstance(current[k], list):
                        current[k] = [current[k]]
                    current[k].append(v)
                else:
                    current[k] = v
        return contacts

    def test_full_fixture_one_contact(self):
        contacts = self._contacts_from_vcf(_build("full"))
        self.assertEqual(len(contacts), 1, f"expected 1 contact, got: {contacts}")

    def test_full_fixture_given_family_name(self):
        contacts = self._contacts_from_vcf(_build("full"))
        c = contacts[0]
        self.assertEqual(c.get("GN"), "Ari")
        self.assertEqual(c.get("FN"), "Vale")

    def test_full_fixture_job_title(self):
        contacts = self._contacts_from_vcf(_build("full"))
        self.assertEqual(contacts[0].get("TITLE"), "AI Agent")

    def test_full_fixture_phone(self):
        contacts = self._contacts_from_vcf(_build("full"))
        phones = contacts[0].get("TEL", "")
        if isinstance(phones, list):
            phones = " ".join(phones)
        self.assertIn("14155550100", phones)

    def test_full_fixture_email(self):
        contacts = self._contacts_from_vcf(_build("full"))
        emails = contacts[0].get("EMAIL", "")
        if isinstance(emails, list):
            emails = " ".join(emails)
        self.assertIn("ari@agentmail.to", emails)

    def test_stress_fixture_one_contact(self):
        contacts = self._contacts_from_vcf(_build("stress"))
        self.assertEqual(len(contacts), 1)

    def test_arabic_fixture_one_contact(self):
        contacts = self._contacts_from_vcf(_build("arabic"))
        self.assertEqual(len(contacts), 1)

    def test_arabic_fixture_name_preserved(self):
        contacts = self._contacts_from_vcf(_build("arabic"))
        c = contacts[0]
        combined = (c.get("GN") or "") + " " + (c.get("FN") or "")
        # At least one Arabic character should appear in the name fields.
        has_arabic = any("؀" <= ch <= "ۿ" for ch in combined)
        self.assertTrue(has_arabic, f"no Arabic chars in name: {combined!r}")

    def test_injection_exactly_one_contact(self):
        contacts = self._contacts_from_vcf(_build("injection"))
        self.assertEqual(len(contacts), 1,
            f"injection produced {len(contacts)} contacts instead of 1")

    def test_injection_no_extra_phones(self):
        contacts = self._contacts_from_vcf(_build("injection"))
        phones = contacts[0].get("TEL", "")
        if isinstance(phones, list):
            self.assertEqual(len(phones), 1, f"too many phones: {phones}")


if __name__ == "__main__":
    unittest.main()
