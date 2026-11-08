"""Local two-factor codes. RFC 6238 (TOTP) over RFC 4226 (HOTP). No account, no vendor, no network call.

When a service's own 2FA setup shows a QR code, decode the `secret` parameter from its `otpauth://` URL
(or type in the plain secret it shows as an alternative to the QR code) and store it with the secret
store (Layer 13). From then on this module produces the same 6-digit codes an authenticator app would.

  totp.py new [name]              generate a fresh base32 secret; store it if a name is given
  totp.py code <secret-or-name>   the current 6-digit code and how many seconds it is valid for
  totp.py uri <secret> <label>    an otpauth:// URI, if something wants to show its own QR code

The core (`code_for`) is checked against the official RFC 4226 Appendix D test vectors in
tests/test_totp.py, so a change here that breaks correctness fails the test suite, not a login somewhere.
"""
import base64
import hmac
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keystore  # noqa: E402

STEP = 30
DIGITS = 6


def die(msg):
    sys.exit(msg.rstrip())


def new_secret(length=20):
    """A fresh random secret, base32-encoded (the conventional TOTP text form)."""
    import secrets as _random
    return base64.b32encode(_random.token_bytes(length)).decode().rstrip("=")


def _key_bytes(secret_b32):
    s = secret_b32.strip().upper().replace(" ", "")
    pad = (-len(s)) % 8
    return base64.b32decode(s + "=" * pad)


def code_for(secret_b32, when=None, step=STEP, digits=DIGITS):
    """The TOTP code for `secret_b32` at time `when` (default now). RFC 6238 over HMAC-SHA1."""
    counter = int((when if when is not None else time.time()) // step)
    key = _key_bytes(secret_b32)
    digest = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10 ** digits)).zfill(digits)


def seconds_remaining(when=None, step=STEP):
    now = when if when is not None else time.time()
    return step - int(now % step)


def otpauth_uri(secret_b32, label, issuer="Humanize"):
    from urllib.parse import quote
    return f"otpauth://totp/{quote(issuer)}:{quote(label)}?secret={secret_b32}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"


def _resolve(secret_or_name):
    """Accept a literal base32 secret, or a name previously stored with `totp.py new <name>`."""
    try:
        _key_bytes(secret_or_name)
        return secret_or_name
    except Exception:
        pass
    stored = keystore.get("totp." + secret_or_name)
    if stored:
        return stored
    die(f"{secret_or_name!r} is not a valid base32 secret and no stored TOTP secret has that name")


def main():
    a = sys.argv[1:]
    if not a:
        die(__doc__)
    if a[0] == "new":
        secret = new_secret()
        if len(a) > 1:
            keystore.namespace()
            keystore.put("totp." + a[1], secret)
            print(f"stored as totp.{a[1]}")
        print(secret)
    elif a[0] == "code" and len(a) > 1:
        secret = _resolve(a[1])
        print(f"{code_for(secret)}  (valid {seconds_remaining()}s more)")
    elif a[0] == "uri" and len(a) > 2:
        print(otpauth_uri(a[1], a[2]))
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
