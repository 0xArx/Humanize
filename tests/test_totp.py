"""Local 2FA codes: RFC 6238 (TOTP) over RFC 4226 (HOTP), checked against the official test vectors."""
import hmac
import struct
import sys
import unittest

from helpers import HomeCase, ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import totp  # noqa: E402
import keystore  # noqa: E402

# RFC 4226 Appendix D: HOTP(secret, counter) for counters 0..9, shared secret "12345678901234567890".
HOTP_SECRET = "12345678901234567890"
HOTP_VECTORS = ["755224", "287082", "359152", "969429", "338314",
                "254676", "287922", "162583", "399871", "520489"]

# RFC 6238 Appendix B: 8-digit TOTP for the same secret (SHA1 case) at these Unix times.
TOTP_SECRET_B32 = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32("12345678901234567890")
TOTP_VECTORS = {
    59: "94287082",
    1111111109: "07081804",
    1111111136: "14050471",
    1234567890: "89005924",
    2000000000: "69279037",
}


def _hotp(secret_ascii, counter, digits=6):
    key = secret_ascii.encode()
    digest = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10 ** digits)).zfill(digits)


class VectorTests(unittest.TestCase):
    def test_hotp_core_matches_all_ten_rfc_4226_vectors(self):
        for counter, expected in enumerate(HOTP_VECTORS):
            self.assertEqual(_hotp(HOTP_SECRET, counter), expected, f"counter {counter}")

    def test_totp_matches_all_five_rfc_6238_vectors_at_8_digits(self):
        for when, expected in TOTP_VECTORS.items():
            self.assertEqual(totp.code_for(TOTP_SECRET_B32, when=when, digits=8), expected, f"time {when}")

    def test_totp_matches_the_same_vectors_truncated_to_6_digits(self):
        for when, expected in TOTP_VECTORS.items():
            self.assertEqual(totp.code_for(TOTP_SECRET_B32, when=when), expected[-6:], f"time {when}")


class BehaviourTests(unittest.TestCase):
    def test_a_fresh_secret_is_valid_base32_and_different_each_time(self):
        a, b = totp.new_secret(), totp.new_secret()
        self.assertNotEqual(a, b)
        totp._key_bytes(a)  # raises if not valid base32
        totp._key_bytes(b)

    def test_code_for_accepts_lowercase_and_spaced_secrets(self):
        spaced = " ".join(TOTP_SECRET_B32[i:i + 4] for i in range(0, len(TOTP_SECRET_B32), 4))
        self.assertEqual(totp.code_for(spaced.lower(), when=59, digits=8), TOTP_VECTORS[59])

    def test_seconds_remaining_counts_down_within_the_30s_step(self):
        self.assertEqual(totp.seconds_remaining(when=1111111109), 30 - (1111111109 % 30))
        self.assertEqual(totp.seconds_remaining(when=1111111136), 30 - (1111111136 % 30))

    def test_otpauth_uri_carries_the_secret_label_and_issuer(self):
        uri = totp.otpauth_uri(TOTP_SECRET_B32, "ari@agentmail.to")
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn(f"secret={TOTP_SECRET_B32}", uri)
        self.assertIn("issuer=Humanize", uri)
        self.assertIn("digits=6", uri)
        self.assertIn("period=30", uri)


class CliTests(HomeCase):
    """Exercises humanize.py's `totp` subcommand (cmd_totp), which wraps scripts/totp.py directly
    rather than through its own resolve-by-name CLI: a stored name is looked up as-is, with no
    'totp.' prefix, and falls back to treating the argument as a literal secret."""

    def setUp(self):
        super().setUp()
        self.init()

    def hz_totp(self, *args, **kw):
        return self.hz("totp", *args, **kw)

    def test_new_without_a_name_only_prints_the_secret(self):
        r = self.hz_totp("new")
        secret = r.stdout.strip()
        totp._key_bytes(secret)  # valid base32
        self.assertEqual(r.stderr.strip(), "")
        self.assertIsNone(keystore.get(secret), "nothing should be stored without a name")

    def test_new_with_a_name_stores_it_under_that_exact_name(self):
        r = self.hz_totp("new", "github")
        self.assertIn("stored as a secret named 'github'", r.stderr)
        secret = r.stdout.strip()
        self.assertEqual(keystore.get("github"), secret)

    def test_code_looks_up_a_stored_name_first(self):
        secret = self.hz_totp("new", "github").stdout.strip()
        by_name = self.hz_totp("code", "github").stdout
        by_secret = self.hz_totp("code", secret).stdout
        self.assertEqual(by_name.split()[0], by_secret.split()[0])

    def test_code_reports_a_literal_secret_and_time_remaining(self):
        r = self.hz_totp("code", TOTP_SECRET_B32)
        self.assertRegex(r.stdout.strip(), r"^\d{6}  \(valid \d+s more\)$")

    def test_code_on_an_unstored_non_base32_name_is_a_clear_error(self):
        r = self.hz_totp("code", "no-such-name", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.strip(), "should explain why it failed")

    def test_uri_subcommand(self):
        r = self.hz_totp("uri", TOTP_SECRET_B32, "ari@agentmail.to")
        self.assertTrue(r.stdout.strip().startswith("otpauth://totp/"))


if __name__ == "__main__":
    unittest.main()
