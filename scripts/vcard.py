#!/usr/bin/env python3
"""Build business-card contact data from an agent identity.

Public interface (fixed; other code depends on these signatures):
    fields(identity: dict) -> dict
    build(fields: dict) -> str
    qr_payload(fields: dict) -> str
    sanitize(text) -> str

vCard escaping: commas, semicolons, backslashes and embedded newlines in
property values are escaped with a backslash. Raw CR and LF are removed
during sanitize() so they can never appear in the output stream.

Line folding: long property lines are folded at 75 octets (bytes), with
each continuation line prefixed by a single space, as RFC 6350 requires.

Secret pointers (values beginning with "secret:") are never emitted.

Identity key "card" means the payment card (Layer 4). Business-card data
lives under "business_card" to avoid that collision.
"""
import datetime
import hashlib
import re

_MAX_SANITIZE = 500    # maximum length after sanitize()
_QR_BUDGET    = 329    # strictly < 330 UTF-8 bytes

# Profile URL patterns for common social networks.
_SOCIAL_URL = {
    "twitter":   "https://twitter.com/{h}",
    "x":         "https://x.com/{h}",
    "instagram": "https://instagram.com/{h}",
    "facebook":  "https://facebook.com/{h}",
    "github":    "https://github.com/{h}",
    "linkedin":  "https://linkedin.com/in/{h}",
    "tiktok":    "https://tiktok.com/@{h}",
    "youtube":   "https://youtube.com/@{h}",
    "reddit":    "https://reddit.com/u/{h}",
}

# Networks where X-SOCIALPROFILE is understood by major clients.
_KNOWN_NETS = frozenset(_SOCIAL_URL)


# ---------------------------------------------------------------------------
# Sanitize
# ---------------------------------------------------------------------------

def sanitize(text, maxlen=_MAX_SANITIZE):
    """Strip control characters, collapse whitespace, cap length.

    CR and LF are the dangerous ones: they could inject extra vCard property
    lines. They are replaced with a space before collapsing. All other C0
    and C1 control characters are also replaced with a space.
    """
    text = str(text)
    text = re.sub(r"[\r\n]", " ", text)                # CR/LF first
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text)  # remaining controls
    text = re.sub(r" {2,}", " ", text)                  # collapse runs
    text = text.strip()
    if len(text) > maxlen:
        text = text[:maxlen]
    return text


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _is_secret(v):
    return isinstance(v, str) and v.startswith("secret:")


def _g(identity, dotted, default=None):
    """Dotted-path get on a nested dict, mirrors store.get."""
    cur = identity
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur if cur is not None else default


def _safe(v):
    """Sanitize v and return the result, or None if missing or a secret pointer."""
    if v is None or _is_secret(v):
        return None
    s = sanitize(str(v))
    return s if s else None


def _normalize_e164(phone):
    """Return E.164 form (+digits) or None if no country code is present.

    A number with no leading '+' cannot be given a country code without
    inventing one, so it is left as a display-only value. After stripping
    recognised formatting characters (spaces, dashes, dots, parens,
    slashes), only digits may remain after the '+'; any other character
    makes the value non-normalizable.
    """
    if not phone:
        return None
    stripped = re.sub(r"[\s\-\.\(\)\/]", "", phone)
    if stripped.startswith("+"):
        digits_part = stripped[1:]
        if not re.match(r"^\d+$", digits_part):
            return None   # non-digit chars remain after stripping formatting
        if 7 <= len(digits_part) <= 15:
            return "+" + digits_part
        return None
    return None


# Schemes that are explicitly rejected regardless of "://" presence.
_REJECT_SCHEME = re.compile(r"^(javascript|data|file|vbscript|about)\s*:", re.I)


def _normalize_url(url):
    """Return url with an https:// scheme, or None for disallowed schemes.

    Allowed: https, http (kept as-is), bare domain (https:// prepended).
    Rejected: javascript:, data:, file:, vbscript:, about:, and any other
    explicit non-http(s) scheme containing '://'.
    """
    if not url:
        return None
    url = url.strip()
    if _REJECT_SCHEME.match(url):
        return None
    low = url.lower()
    if low.startswith("https://") or low.startswith("http://"):
        return url
    if "://" in url:
        return None   # explicit non-http(s) scheme
    return "https://" + url


def _social_url(network, handle):
    pat = _SOCIAL_URL.get(network.lower())
    if not pat:
        return None
    return pat.format(h=handle.lstrip("@"))


def _escape_value(text):
    """Escape a vCard 3.0 property value.

    Escapes backslash first to avoid double-escaping, then comma, semicolon
    and any embedded newline characters (which sanitize() should have already
    removed, but this is a defence-in-depth measure).
    """
    text = text.replace("\\", "\\\\")
    text = text.replace(",", "\\,")
    text = text.replace(";", "\\;")
    text = text.replace("\r\n", "\\n")
    text = text.replace("\r",   "\\n")
    text = text.replace("\n",   "\\n")
    return text


def _fold(line):
    """Fold a vCard line at 75 octets with CRLF + SPACE continuation.

    Multibyte UTF-8 characters are never split: the loop advances by
    Unicode code point, encoding to bytes only for the length check.
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    chunks = []
    current = b""
    limit = 75         # first chunk up to 75 bytes
    for ch in line:
        ch_b = ch.encode("utf-8")
        if len(current) + len(ch_b) > limit:
            chunks.append(current.decode("utf-8"))
            current = b" " + ch_b   # continuation line starts with SPACE
            limit = 74              # subsequent chunks: 74 bytes including leading space
        else:
            current += ch_b
    if current:
        chunks.append(current.decode("utf-8"))
    return "\r\n".join(chunks)


def _uid_from_seed(seed):
    """Stable UUID-formatted UID derived from the seed via SHA-256."""
    h = hashlib.sha256(("humanize:" + seed).encode("utf-8")).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _split_name(full_name):
    """Split a full name into (first, last).

    Single-word names: first = name, last = ''.
    Multi-word names:  last = final word, first = all preceding words.
    Particles and non-Latin scripts follow the same rule.
    """
    parts = full_name.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def fields(identity):
    """Extract business-card fields from a raw identity dict.

    Returns a dict with keys:
        name (str), first (str), last (str),
        title (str|None), tagline (str|None),
        email (str|None), phone (str|None), phone_e164 (str|None),
        whatsapp (str|None), website (str|None),
        handles (list of {label, text, url}),
        address (dict|None with line1, city),
        booking_url (str|None),
        missing (list of human-readable suggestions),
        seed (str).

    Secret pointers ("secret:...") are never emitted.
    """
    raw_name = _safe(_g(identity, "name")) or ""
    first, last = _split_name(raw_name)

    title   = _safe(_g(identity, "business_card.title"))
    tagline = _safe(_g(identity, "business_card.tagline"))
    bc_url  = _safe(_g(identity, "business_card.website"))

    email_val = _safe(_g(identity, "email.agentmail.address"))

    # Phone: prefer agentphone, fall back to dial.
    raw_phone = (_g(identity, "phone.agentphone.number")
                 or _g(identity, "phone.dial.number"))
    phone_display  = None
    phone_e164_val = None
    if raw_phone and not _is_secret(raw_phone):
        phone_display  = sanitize(str(raw_phone)) or None
        phone_e164_val = _normalize_e164(phone_display) if phone_display else None

    # WhatsApp.
    wa = _g(identity, "whatsapp.number")
    whatsapp_val = _safe(wa)

    # Website: explicit business_card.website, else domain.name.
    website = _normalize_url(bc_url) if bc_url else None
    if not website:
        domain = _safe(_g(identity, "domain.name"))
        if domain:
            website = _normalize_url(domain)

    # Booking URL.
    booking_url = None
    raw_booking = _g(identity, "calendar.booking_url")
    if raw_booking and not _is_secret(raw_booking):
        bu = sanitize(str(raw_booking))
        if bu:
            booking_url = _normalize_url(bu)

    # Social handles.
    handles = []

    gh = _safe(_g(identity, "accounts.github.username"))
    if gh:
        handles.append({
            "label": "GitHub",
            "text":  "@" + gh,
            "url":   "https://github.com/" + gh,
        })

    social = _g(identity, "social") or {}
    if isinstance(social, dict):
        for network, data in social.items():
            if not isinstance(data, dict):
                continue
            handle_v = data.get("handle")
            if handle_v is None or _is_secret(handle_v):
                continue
            h_text = sanitize(str(handle_v))
            if not h_text:
                continue
            url = _social_url(network, h_text)
            handles.append({
                "label": network.capitalize(),
                "text":  "@" + h_text.lstrip("@"),
                "url":   url,
            })

    # Address (line1 and city; template does not include state/postal/country).
    line1 = _safe(_g(identity, "address.line1"))
    city  = _safe(_g(identity, "address.city"))
    address = {"line1": line1 or "", "city": city or ""} if (line1 or city) else None

    # Avatar seed.
    face_seed = _g(identity, "face.seed")
    if face_seed and not _is_secret(face_seed):
        seed = sanitize(str(face_seed)) or raw_name or "agent"
    elif raw_name:
        seed = raw_name
    else:
        seed = "agent"

    # Suggestions for improving the card.
    missing = []
    if not email_val:
        missing.append("no email address yet (Layer 1)")
    if not phone_display:
        missing.append("no phone number yet (Layer 2)")
    if not website:
        missing.append("no website yet (Layer 17)")
    if not title:
        missing.append("no title set (business_card.title)")
    if not handles:
        missing.append("no social handles yet (Layers 6, 14)")
    if not address:
        missing.append("no address yet (Layer 16)")

    return {
        "name":        raw_name,
        "first":       first,
        "last":        last,
        "title":       title,
        "tagline":     tagline,
        "email":       email_val,
        "phone":       phone_display,
        "phone_e164":  phone_e164_val,
        "whatsapp":    whatsapp_val,
        "website":     website,
        "handles":     handles,
        "address":     address,
        "booking_url": booking_url,
        "missing":     missing,
        "seed":        seed,
    }


def build(fields, _clock=None):
    """Build a full vCard 3.0 string.

    Output is UTF-8, CRLF line endings, lines folded at 75 octets.
    _clock: datetime.datetime used for REV; defaults to utcnow(). Pass a
    fixed value in tests to get deterministic output.
    """
    now = _clock if _clock is not None else datetime.datetime.utcnow()
    rev = now.strftime("%Y%m%dT%H%M%SZ")
    uid = _uid_from_seed(fields.get("seed", "agent"))

    lines = []

    def emit(prop, value):
        """Append a folded property line, escaping the value."""
        if value is None:
            return
        lines.append(_fold(prop + ":" + _escape_value(value)))

    lines.append("BEGIN:VCARD")
    lines.append("VERSION:3.0")

    # FN: formatted (display) name.
    fn = fields.get("name") or " ".join(
        filter(None, [fields.get("first"), fields.get("last")])
    )
    emit("FN", fn or "")

    # N: structured name (family;given;additional;prefix;suffix).
    # Components are escaped individually; the separating semicolons are structural.
    last_esc  = _escape_value(fields.get("last")  or "")
    first_esc = _escape_value(fields.get("first") or "")
    lines.append(_fold(f"N:{last_esc};{first_esc};;;"))

    if fields.get("title"):
        emit("TITLE", fields["title"])

    phone_e164 = fields.get("phone_e164")
    phone      = fields.get("phone")
    if phone_e164:
        emit("TEL;TYPE=CELL", phone_e164)
    elif phone:
        emit("TEL;TYPE=CELL", phone)

    if fields.get("email"):
        emit("EMAIL;TYPE=INTERNET", fields["email"])

    if fields.get("website"):
        emit("URL", fields["website"])

    if fields.get("booking_url"):
        emit("URL;TYPE=BOOKING", fields["booking_url"])

    for h in fields.get("handles") or []:
        label = h.get("label", "")
        url   = h.get("url")
        text  = h.get("text", "")
        net   = label.lower()
        if url:
            if net in _KNOWN_NETS:
                emit(f"X-SOCIALPROFILE;TYPE={net}", url)
            else:
                emit(f"URL;TYPE={label}", url)
        elif text:
            emit(f"X-SOCIALPROFILE;TYPE={net}", text)

    addr = fields.get("address")
    if addr:
        # ADR: pobox;extended;street;locality;region;postal;country.
        # Each component is independently escaped; the semicolons are structural.
        parts = [
            "",
            "",
            _escape_value(addr.get("line1") or ""),
            _escape_value(addr.get("city")  or ""),
            "",
            "",
            "",
        ]
        lines.append(_fold("ADR;TYPE=POSTAL:" + ";".join(parts)))

    if fields.get("tagline"):
        emit("NOTE", fields["tagline"])

    lines.append(f"REV:{rev}")
    lines.append(f"UID:{uid}")
    lines.append("END:VCARD")

    return "\r\n".join(lines) + "\r\n"


def qr_payload(fields):
    """Compact vCard 3.0 for embedding in a QR code.

    Contains only name, title, one phone, one email, website. No social
    handles, no address, no NOTE. Lines are not folded (QR handles any
    content and folding wastes bytes).

    Drop order to stay under 330 UTF-8 bytes (most optional first):
        1. website
        2. title
        3. truncate name with '...' (last resort)
    """
    fn_full    = fields.get("name") or " ".join(
        filter(None, [fields.get("first"), fields.get("last")])
    )
    last_full  = fields.get("last")  or ""
    first_full = fields.get("first") or ""

    def _try(fn, last, first, inc_title, inc_website):
        parts = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            "FN:"    + _escape_value(fn),
            "N:"     + _escape_value(last) + ";" + _escape_value(first) + ";;;",
        ]
        if inc_title and fields.get("title"):
            parts.append("TITLE:" + _escape_value(fields["title"]))
        phone_e164 = fields.get("phone_e164")
        phone      = fields.get("phone")
        if phone_e164:
            parts.append("TEL;TYPE=CELL:" + phone_e164)
        elif phone:
            parts.append("TEL;TYPE=CELL:" + _escape_value(phone))
        if fields.get("email"):
            parts.append("EMAIL;TYPE=INTERNET:" + _escape_value(fields["email"]))
        if inc_website and fields.get("website"):
            parts.append("URL:" + _escape_value(fields["website"]))
        parts.append("END:VCARD")
        return "\r\n".join(parts) + "\r\n"

    # Try progressively simpler payloads.
    for inc_title, inc_website in [(True, True), (True, False), (False, False)]:
        result = _try(fn_full, last_full, first_full, inc_title, inc_website)
        if len(result.encode("utf-8")) <= _QR_BUDGET:
            return result

    # Last resort: truncate the name character by character.
    for cut in range(len(fn_full) - 1, 0, -1):
        fn_t = fn_full[:cut] + "..."
        first_t, last_t = _split_name(fn_t)
        result = _try(fn_t, last_t, first_t, False, False)
        if len(result.encode("utf-8")) <= _QR_BUDGET:
            return result

    # Absolute fallback (should be unreachable in practice).
    return "BEGIN:VCARD\r\nVERSION:3.0\r\nFN:.\r\nN:;;;;\r\nEND:VCARD\r\n"
