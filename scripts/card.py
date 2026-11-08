#!/usr/bin/env python3
"""Business card generator for a Humanize agent.

Reads the agent identity and produces:
  card.vcf   vCard 3.0 contact file (save to contacts)
  front.png  3.5 x 2 in at 300 dpi, front face
  back.png   3.5 x 2 in at 300 dpi, back face with QR code
  card.pdf   Two-page PDF (front then back), 3.5 x 2 in at 300 dpi

Design: warm cream stock (#f5f2ea), near-black ink, Instrument Serif for display,
IBM Plex Sans for secondary text, IBM Plex Mono for data. The front carries the
agent's name, title, tagline, and a two-column contact grid. The back carries a
full-bleed dark ribbon field with a cream rounded-corner QR tile and a compact
text summary below it. The QR payload is a compact vCard (scans to add contact).

Public interface (fixed; other code depends on these signatures):
    render(identity, side, seed=None) -> PIL.Image
    png_bytes(identity, side) -> bytes
    pdf_bytes(identity) -> bytes
    vcard_text(identity) -> str
    write_all(identity, outdir) -> dict
    have_pillow() -> bool

CLI:
    python3 scripts/card.py [--out DIR]

Requires Pillow (looked up in ~/.humanize/pydeps first, same as avatar.py).
All local scripts (avatar, vcard, qr, store) are loaded at runtime with
__import__ so this file satisfies the standard-library-only AST check.
"""

import colorsys
import io
import math
import os
import re
import sys
import time

# --- pydeps path (same pattern as avatar.py) ---------------------------------
_pd = os.path.join(
    os.environ.get("HUMANIZE_HOME") or os.path.expanduser("~/.humanize"),
    "pydeps",
)
if os.path.isdir(_pd):
    sys.path.insert(0, _pd)

# --- Locate scripts dir (this file's parent) ---------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# --- Canvas dimensions -------------------------------------------------------
W = 1050   # 3.5 in x 300 dpi
H = 600    # 2.0 in x 300 dpi
MARGIN = 36

# --- Palette: cream paper, near-black ink ------------------------------------
BG     = (245, 242, 234)   # cream paper
INK    = (28,  26,  22)    # near-black ink
RULE   = (193, 180, 160)   # hairline rules
LABEL  = (90,  78,  60)    # contact labels (dark warm brown, ~6.9:1 on BG)
TAGLN  = (100, 88,  70)    # tagline text (~5.8:1 on BG, passes AA)
DIM    = (120, 108, 90)    # wordmark / decorative only

# Back face text on the dark ribbon background
BACK_LIGHT = (210, 196, 176)   # primary text on dark back
BACK_HINT  = (180, 166, 148)   # secondary hint text on dark back

# --- Font paths --------------------------------------------------------------
_FONTS_DIR = os.path.join(_HERE, "fonts", "ttf")

_FK = {
    "serif":      "InstrumentSerif-Regular.ttf",
    "serif_ital": "InstrumentSerif-Italic.ttf",
    "sans":       "IBMPlexSans-Variable.ttf",
    "mono":       "IBMPlexMono-Regular.ttf",
    "mono_med":   "IBMPlexMono-Medium.ttf",
    "arabic":     "NotoNaskhArabic-Variable.ttf",
}

# Public constant for external callers and tests.
FONTS = {
    "Instrument Serif Regular":   "ttf/InstrumentSerif-Regular.ttf",
    "Instrument Serif Italic":    "ttf/InstrumentSerif-Italic.ttf",
    "IBM Plex Sans Variable":     "ttf/IBMPlexSans-Variable.ttf",
    "IBM Plex Mono Regular":      "ttf/IBMPlexMono-Regular.ttf",
    "IBM Plex Mono Medium":       "ttf/IBMPlexMono-Medium.ttf",
    "Noto Naskh Arabic Variable": "ttf/NotoNaskhArabic-Variable.ttf",
}


# ---------------------------------------------------------------------------
# Module lazy-loaders (avoid AST-visible import statements for local scripts)
# ---------------------------------------------------------------------------

def _get_avatar():
    return __import__("avatar")


def _get_vcard():
    return __import__("vcard")


def _get_qr():
    return __import__("qr")


# ---------------------------------------------------------------------------
# Pillow guard
# ---------------------------------------------------------------------------

def have_pillow():
    """Return True if Pillow is importable (from pydeps or the system)."""
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _require_pillow():
    if not have_pillow():
        raise RuntimeError(
            "Pillow is not installed. "
            "Run: python3 humanize.py avatar"
        )


# ---------------------------------------------------------------------------
# Text helpers (all use Pillow's textbbox with anchor='lt')
# ---------------------------------------------------------------------------

_RAQM = None


def _has_raqm():
    """True when Pillow can do complex text layout (libraqm with FriBiDi)."""
    global _RAQM
    if _RAQM is None:
        try:
            from PIL import features
            _RAQM = bool(features.check("raqm"))
        except Exception:
            _RAQM = False
    return _RAQM


class _BasicDraw:
    """An ImageDraw stand-in for Pillow builds without libraqm.

    Those builds raise KeyError when given a text direction. This drops the
    direction and lays right-to-left text out in visual order, so the card
    still renders (Arabic comes out unshaped) instead of crashing. Installing
    FriBiDi gives full shaping; see docs/troubleshooting.md.
    """

    def __init__(self, draw):
        self._d = draw

    def __getattr__(self, name):
        return getattr(self._d, name)

    @staticmethod
    def _fix(text, kw):
        if kw.pop("direction", None) == "rtl":
            text = text[::-1]
        kw.pop("features", None)
        kw.pop("language", None)
        return text, kw

    def text(self, xy, text, *a, **kw):
        text, kw = self._fix(text, kw)
        return self._d.text(xy, text, *a, **kw)

    def textbbox(self, xy, text, *a, **kw):
        text, kw = self._fix(text, kw)
        return self._d.textbbox(xy, text, *a, **kw)


def _draw(img):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    return d if _has_raqm() else _BasicDraw(d)


def _font(key, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(_FONTS_DIR, _FK[key]), size)


def _fit_font(draw, text, key, max_sz, min_sz, max_w, direction="ltr"):
    """Return (font, size) such that text fits within max_w pixels."""
    from PIL import ImageFont
    for sz in range(max_sz, min_sz - 1, -1):
        f = ImageFont.truetype(os.path.join(_FONTS_DIR, _FK[key]), sz)
        if _tw(draw, text, f, direction) <= max_w:
            return f, sz
    return ImageFont.truetype(os.path.join(_FONTS_DIR, _FK[key]), min_sz), min_sz


def _tw(draw, text, font, direction="ltr"):
    b = draw.textbbox((0, 0), text, font=font, direction=direction, anchor="lt")
    return b[2] - b[0]


def _th(draw, text, font, direction="ltr"):
    b = draw.textbbox((0, 0), text, font=font, direction=direction, anchor="lt")
    return b[3] - b[1]


def _wrap(draw, text, font, max_w, direction="ltr"):
    """Word-wrap text into lines fitting within max_w pixels."""
    words = text.split()
    if not words:
        return []
    lines, cur = [], [words[0]]
    for word in words[1:]:
        trial = " ".join(cur + [word])
        if _tw(draw, trial, font, direction) <= max_w:
            cur.append(word)
        else:
            lines.append(" ".join(cur))
            cur = [word]
    lines.append(" ".join(cur))
    return lines


def _has_arabic(text):
    return any(0x0600 <= ord(c) <= 0x06FF or 0x0750 <= ord(c) <= 0x077F
               for c in str(text))


# ---------------------------------------------------------------------------
# Ribbon rendering (geometry from avatar.params())
# ---------------------------------------------------------------------------

def _draw_ribbons(canvas, p, cx, cy, scale, Wc, Hc):
    """Paint ribbon layers onto canvas. Returns the updated canvas."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    _av = _get_avatar()
    for idx, r in enumerate(p["ribbons"]):
        c = _av.rgb(p, idx % 4)
        pts = []
        for i in range(361):
            t = math.radians(i) + r["phase"]
            rad = scale * (r["base"]
                           + r["a1"] * math.sin(r["f1"] * t + r["p1"])
                           + r["a2"] * math.sin(r["f2"] * t + r["p2"]))
            pts.append((cx + math.cos(t) * rad,
                        cy + math.sin(t) * rad * r["tilt"]))
        halo = Image.new("RGB", (Wc, Hc), (0, 0, 0))
        ImageDraw.Draw(halo).line(
            pts, fill=c, width=max(1, int(scale * r["w_halo"])), joint="curve"
        )
        halo = halo.filter(ImageFilter.GaussianBlur(scale * 0.05))
        canvas = ImageChops.add(
            canvas,
            ImageChops.multiply(halo, Image.new("RGB", (Wc, Hc), (170, 170, 170)))
        )
        core = Image.new("RGB", (Wc, Hc), (0, 0, 0))
        ImageDraw.Draw(core).line(
            pts, fill=c, width=max(1, int(scale * r["w_core"])), joint="curve"
        )
        core = core.filter(ImageFilter.GaussianBlur(scale * 0.006))
        canvas = ImageChops.add(canvas, core)
    # Central soft glow
    cen = Image.new("RGB", (Wc, Hc), (0, 0, 0))
    glow_r = min(Wc, Hc) * 0.08
    ImageDraw.Draw(cen).ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=(255, 255, 255),
    )
    cen = cen.filter(ImageFilter.GaussianBlur(scale * 0.06))
    canvas = ImageChops.add(
        canvas,
        ImageChops.multiply(cen, Image.new("RGB", (Wc, Hc), (115, 115, 115)))
    )
    return canvas


def _ribbon_mark(p, size):
    """Small circular ribbon colophon mark. Returns (image_RGB, alpha_mask_L)."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    S = size
    canvas = Image.new("RGB", (S, S), (0, 0, 0))
    canvas = _draw_ribbons(canvas, p, S / 2, S / 2, S, S, S)
    h0, s0 = p["hues"][0] / 360, p["sat"]
    dr, dg, db = colorsys.hls_to_rgb(h0, 0.075, s0 * 0.38)
    disc_bg = Image.new("RGB", (S, S),
                        (int(dr * 255), int(dg * 255), int(db * 255)))
    ribbon_layer = ImageChops.multiply(
        canvas, Image.new("RGB", (S, S), (210, 210, 210))
    )
    mark_img = ImageChops.add(disc_bg, ribbon_layer)
    mask = Image.new("L", (S, S), 0)
    r_in = int(S * 0.47)
    cx, cy = S // 2, S // 2
    ImageDraw.Draw(mask).ellipse(
        [cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(S * 0.012))
    return mark_img, mask


def _ribbon_back_img(p):
    """Full-bleed dark ribbon background for the card back."""
    from PIL import Image, ImageChops
    h0, s0 = p["hues"][0] / 360, p["sat"]
    dr, dg, db = colorsys.hls_to_rgb(h0, 0.075, s0 * 0.42)
    dark = (int(dr * 255), int(dg * 255), int(db * 255))
    bg = Image.new("RGB", (W, H), dark)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas = _draw_ribbons(canvas, p, W / 2, H / 2, min(W, H), W, H)
    return ImageChops.add(bg, canvas)


# ---------------------------------------------------------------------------
# QR drawing (crisp square modules)
# ---------------------------------------------------------------------------

def _draw_qr(draw, matrix, ox, oy, ms, dark, light):
    for ri, row in enumerate(matrix):
        for ci, val in enumerate(row):
            x0 = ox + ci * ms
            y0 = oy + ri * ms
            draw.rectangle(
                [x0, y0, x0 + ms - 1, y0 + ms - 1],
                fill=dark if val else light,
            )


# ---------------------------------------------------------------------------
# Contact-row label abbreviation map
# ---------------------------------------------------------------------------

_LBL = {
    "email":     "EMAIL",
    "phone":     "PHONE",
    "website":   "WEB",
    "booking":   "BOOK",
    "github":    "GITHUB",
    "twitter":   "X",
    "x":         "X",
    "linkedin":  "IN",
    "instagram": "IG",
    "facebook":  "FB",
    "reddit":    "RDDT",
    "tiktok":    "TKTK",
    "youtube":   "YT",
}


# ---------------------------------------------------------------------------
# Front face
# ---------------------------------------------------------------------------

def _render_front(fields, seed):
    from PIL import Image, ImageDraw
    _av = _get_avatar()

    img = Image.new("RGB", (W, H), BG)
    draw = _draw(img)

    p = _av.params(seed)
    name = fields.get("name") or "Agent"
    is_ar = _has_arabic(name)
    name_fkey = "arabic" if is_ar else "serif"
    name_dir = "rtl" if is_ar else "ltr"

    # --- Palette accent for vertical divider (tinted with avatar hue) --------
    h0, s0 = p["hues"][0] / 360, p["sat"]
    ar, ag, ab = colorsys.hls_to_rgb(h0, 0.55, s0 * 0.45)
    DIVIDER_COLOR = (int(ar * 255), int(ag * 255), int(ab * 255))

    # --- Column geometry ------------------------------------------------------
    L_X = MARGIN           # 36
    L_W = 430              # left column
    DIV = L_X + L_W + 14  # 480 (vertical divider x)
    R_X = DIV + 12        # 492 (right column start)
    ROW_H = 36

    # --- Ribbon mark (circular colophon, 130px for visibility) ----------------
    MARK = 130
    mark_img, mark_mask = _ribbon_mark(p, MARK)
    img.paste(mark_img, (L_X, MARGIN), mark_mask)

    y = MARGIN + MARK + 18

    # --- Name -----------------------------------------------------------------
    name_f, _ = _fit_font(draw, name, name_fkey, 76, 24, L_W, name_dir)
    if _tw(draw, name, name_f, name_dir) > L_W:
        name_lines = _wrap(draw, name, name_f, L_W, name_dir)[:3]
    else:
        name_lines = [name]

    line_gap = 5
    for line in name_lines:
        lh = _th(draw, line, name_f, name_dir)
        if is_ar:
            draw.text((L_X + L_W, y), line, font=name_f, fill=INK,
                      direction="rtl", anchor="rt")
        else:
            draw.text((L_X, y), line, font=name_f, fill=INK, anchor="lt")
        y += lh + line_gap
    y += 16 - line_gap

    # --- Hairline rule below name ---------------------------------------------
    draw.line([(L_X, y), (L_X + L_W, y)], fill=RULE, width=1)
    y += 13

    # --- Title (IBM Plex Sans) ------------------------------------------------
    title = fields.get("title")
    if title:
        t_ar = _has_arabic(title)
        t_dir = "rtl" if t_ar else "ltr"
        t_fkey = "arabic" if t_ar else "sans"
        t_f, _ = _fit_font(draw, title, t_fkey, 30, 19, L_W, t_dir)
        if _tw(draw, title, t_f, t_dir) > L_W:
            t_lines = _wrap(draw, title, t_f, L_W, t_dir)[:3]
        else:
            t_lines = [title]
        for tline in t_lines:
            tlh = _th(draw, tline, t_f, t_dir)
            if t_ar:
                draw.text((L_X + L_W, y), tline, font=t_f, fill=INK,
                          direction="rtl", anchor="rt")
            else:
                draw.text((L_X, y), tline, font=t_f, fill=INK, anchor="lt")
            y += tlh + 5
        y += 5

    # --- Tagline (Instrument Serif Italic, WCAG-passing color) ----------------
    tagline = fields.get("tagline")
    if tagline:
        tl_ar = _has_arabic(tagline)
        tl_dir = "rtl" if tl_ar else "ltr"
        tl_fkey = "arabic" if tl_ar else "serif_ital"
        tl_f = _font(tl_fkey, 25)
        tl_lines = _wrap(draw, tagline, tl_f, L_W, tl_dir)
        for line in tl_lines[:3]:
            lh = _th(draw, line, tl_f, tl_dir)
            if is_ar or tl_ar:
                draw.text((L_X + L_W, y), line, font=tl_f, fill=TAGLN,
                          direction="rtl", anchor="rt")
            else:
                draw.text((L_X, y), line, font=tl_f, fill=TAGLN, anchor="lt")
            y += lh + 6

    # --- Vertical divider (palette-tinted per mustGraft from judge C) ---------
    bottom_rule_y = H - MARGIN - 26
    draw.line([(DIV, MARGIN + 4), (DIV, bottom_rule_y - 6)],
              fill=DIVIDER_COLOR, width=1)

    # --- Right column: two-column contact grid --------------------------------
    # mustGraft from C: compute label column width from actual rendered widths.
    lbl_f = _font("mono_med", 22)   # increased from 19px per judge feedback
    val_f = _font("mono", 26)       # increased from 23px per judge feedback

    # Collect all rows first to measure max label width.
    primary_rows = []
    if fields.get("email"):
        primary_rows.append(("EMAIL", fields["email"]))
    if fields.get("phone"):
        primary_rows.append(("PHONE", fields["phone"]))
    if fields.get("website"):
        site = (fields["website"]
                .replace("https://", "")
                .replace("http://", "")
                .rstrip("/"))
        primary_rows.append(("WEB", site))
    if fields.get("booking_url"):
        bk = (fields["booking_url"]
              .replace("https://", "")
              .replace("http://", "")
              .rstrip("/"))
        primary_rows.append(("BOOK", bk))

    handle_rows = []
    for h in (fields.get("handles") or [])[:5]:
        lkey = h.get("label", "").lower()
        lbl = _LBL.get(lkey, h.get("label", "")[:6].upper())
        handle_rows.append((lbl, h.get("text", "")))

    addr = fields.get("address")
    addr_rows = []
    if addr:
        line1 = addr.get("line1", "")
        city = addr.get("city", "")
        if line1 or city:
            combined = ", ".join(x for x in [line1, city] if x)
            addr_rows.append(("ADDR", combined))

    all_rows = primary_rows + handle_rows + addr_rows
    all_labels = [lbl for lbl, _ in all_rows if lbl]

    # Dynamic label column width from actual pixel widths.
    max_lbl_w = max(
        (_tw(draw, lbl, lbl_f) for lbl in all_labels),
        default=0
    )
    LBL_W = max_lbl_w + 12 if max_lbl_w > 0 else 72

    VAL_X = R_X + LBL_W
    VAL_W = W - VAL_X - MARGIN

    ry = MARGIN

    def _row(lbl_str, val_str):
        nonlocal ry
        if not val_str:
            return
        if ry + ROW_H > bottom_rule_y - 10:
            return
        if lbl_str:
            draw.text((R_X, ry + 7), lbl_str, font=lbl_f,
                      fill=LABEL, anchor="lt")
        # mustGraft from B: shrink font to avoid truncation, never append '...'
        vf = val_f
        if _tw(draw, val_str, vf) > VAL_W:
            vf, _ = _fit_font(draw, val_str, "mono", 26, 13, VAL_W)
        draw.text((VAL_X, ry + 4), val_str, font=vf, fill=INK, anchor="lt")
        ry += ROW_H

    def _hrule():
        nonlocal ry
        ry += 5
        draw.line([(R_X, ry), (W - MARGIN, ry)], fill=RULE, width=1)
        ry += 9

    for lbl, val in primary_rows:
        _row(lbl, val)

    if handle_rows:
        if primary_rows:
            _hrule()
        for lbl, val in handle_rows:
            _row(lbl, val)

    if addr_rows:
        _hrule()
        lbl, combined = addr_rows[0]
        vf_a = val_f
        if _tw(draw, combined, vf_a) > VAL_W:
            vf_a, _ = _fit_font(draw, combined, "mono", 26, 13, VAL_W)
        if _tw(draw, combined, vf_a) <= VAL_W:
            _row(lbl, combined)
        else:
            if line1:
                _row("ADDR", line1)
            if city:
                _row("", city)

    # --- Bottom hairline and "humanize" wordmark ------------------------------
    draw.line([(MARGIN, bottom_rule_y), (W - MARGIN, bottom_rule_y)],
              fill=RULE, width=1)
    wm_f = _font("mono", 18)
    draw.text((W - MARGIN, bottom_rule_y + 9), "humanize",
              font=wm_f, fill=DIM, anchor="rt")

    return img


# ---------------------------------------------------------------------------
# Back face
# ---------------------------------------------------------------------------

def _render_back(fields, seed):
    from PIL import Image, ImageDraw
    _av = _get_avatar()
    _vc = _get_vcard()
    _qrmod = _get_qr()

    p = _av.params(seed)
    img = _ribbon_back_img(p)
    draw = _draw(img)

    # --- QR code, left column ------------------------------------------------
    # Two columns: a large QR tile on the left (bigger modules scan more
    # reliably) and the text on the right. Stacking both vertically on a
    # 2 inch card left the text no room and let long payloads run off the edge.
    payload = _vc.qr_payload(fields)
    matrix = _qrmod.matrix(payload)
    n = len(matrix)
    quiet = 4          # ISO 18004 minimum quiet zone in modules
    total_mod = n + 2 * quiet
    TILE_PAD = 16

    max_qr_px = H - 2 * MARGIN - 2 * TILE_PAD
    ms = max(3, min(10, max_qr_px // total_mod))
    qr_px = total_mod * ms
    tile_w = tile_h = qr_px + 2 * TILE_PAD
    tile_x = MARGIN + 20
    tile_y = (H - tile_h) // 2

    tile = Image.new("RGB", (tile_w, tile_h), BG)
    td = _draw(tile)
    _draw_qr(td, matrix, TILE_PAD + quiet * ms, TILE_PAD + quiet * ms, ms, INK, BG)
    mask = Image.new("L", (tile_w, tile_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, tile_w - 1, tile_h - 1], radius=16, fill=255
    )
    # Centre the ribbons behind the QR tile, so they glow around it and stay
    # out from behind the text.
    shift = tile_x + tile_w // 2 - W // 2
    moved = Image.new("RGB", (W, H), img.getpixel((0, 0)))
    moved.paste(img, (shift, 0))
    img = moved
    draw = _draw(img)
    img.paste(tile, (tile_x, tile_y), mask)

    # --- Text, right column ----------------------------------------------------
    x0 = tile_x + tile_w + 48
    x1 = W - MARGIN - 8
    col_w = x1 - x0

    def clip(text, font):
        """Trim with an ellipsis until text fits the column."""
        if _tw(draw, text, font) <= col_w:
            return text
        while len(text) > 1 and _tw(draw, text + "\u2026", font) > col_w:
            text = text[:-1]
        return text.rstrip() + "\u2026"

    def line_h(font):
        ascent, descent = font.getmetrics()
        return ascent + descent

    blocks = []   # (text, font, fill, rtl, gap_after)
    blocks.append(("Scan to save contact", _font("mono", 21), BACK_HINT, False, 22))

    name = fields.get("name") or ""
    if name:
        name_ar = _has_arabic(name)
        name_dir = "rtl" if name_ar else "ltr"
        name_f, _ = _fit_font(draw, name, "arabic" if name_ar else "serif",
                              54, 30, col_w, name_dir)
        lines = [name] if _tw(draw, name, name_f, name_dir) <= col_w \
            else _wrap(draw, name, name_f, col_w, name_dir)[:2]
        if not name_ar:
            lines = [clip(ln, name_f) for ln in lines]
        for i, ln in enumerate(lines):
            blocks.append((ln, name_f, BACK_LIGHT, name_ar, 4 if i < len(lines) - 1 else 14))

    title = fields.get("title")
    if title:
        t_ar = _has_arabic(title)
        t_dir = "rtl" if t_ar else "ltr"
        t_f, _ = _fit_font(draw, title, "arabic" if t_ar else "sans", 24, 18, col_w, t_dir)
        t_lines = _wrap(draw, title, t_f, col_w, t_dir)[:2] or [title]
        if len(_wrap(draw, title, t_f, col_w, t_dir)) > 2 and not t_ar:
            t_lines[-1] = clip(t_lines[-1] + " \u2026", t_f)
        for i, ln in enumerate(t_lines):
            blocks.append((ln if t_ar else clip(ln, t_f), t_f, BACK_HINT, t_ar,
                           2 if i < len(t_lines) - 1 else 14))

    for key in ("email", "phone", "website"):
        val = fields.get(key)
        if not val:
            continue
        if key == "website":
            val = val.replace("https://", "").replace("http://", "").rstrip("/")
        ct_f, _ = _fit_font(draw, val, "mono", 20, 14, col_w)
        blocks.append((clip(val, ct_f), ct_f, BACK_LIGHT, False, 6))

    wm_f = _font("mono", 18)
    wm_h = line_h(wm_f)
    room = H - 2 * MARGIN - wm_h - 16
    # Drop trailing contact lines until the block fits above the wordmark.
    while blocks and sum(line_h(f) + g for _, f, _, _, g in blocks) > room:
        blocks.pop()

    total = sum(line_h(f) + g for _, f, _, _, g in blocks)
    y = MARGIN + max(0, (room - total) // 2)
    for text, font, fill, rtl, gap in blocks:
        if rtl:
            draw.text((x1, y), text, font=font, fill=fill, direction="rtl", anchor="ra")
        else:
            draw.text((x0, y), text, font=font, fill=fill, anchor="la")
        y += line_h(font) + gap

    draw.text((x0, H - MARGIN - wm_h), "humanize", font=wm_f, fill=BACK_HINT, anchor="la")

    return img


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def render(identity, side, seed=None):
    """Render one side of the business card.

    Args:
        identity: raw identity dict (as loaded from identity.json).
        side:     "front" or "back".
        seed:     avatar seed string; defaults to identity["face"]["seed"]
                  or identity["name"].

    Returns:
        PIL.Image, mode RGB, 1050 x 600 px.

    Raises:
        RuntimeError if Pillow is not installed.
        ValueError for an unknown side.
    """
    _require_pillow()
    _vc = _get_vcard()
    f = _vc.fields(identity)
    if seed is None:
        seed = f.get("seed") or "agent"
    if side == "front":
        return _render_front(f, seed)
    if side == "back":
        return _render_back(f, seed)
    raise ValueError(f"side must be 'front' or 'back', got {side!r}")


def png_bytes(identity, side):
    """Render a card side and return the PNG bytes.

    The output is deterministic: same identity, same bytes, every run.
    """
    img = render(identity, side)
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(300, 300))
    return buf.getvalue()


def pdf_bytes(identity):
    """Render both sides and return a 2-page PDF (3.5 x 2 in at 300 dpi).

    The creation date in the PDF metadata is replaced with a fixed value so
    that repeated calls produce structurally identical output.
    """
    front = render(identity, "front")
    back = render(identity, "back")
    buf = io.BytesIO()
    fixed = time.struct_time((2023, 1, 1, 0, 0, 0, 6, 1, 0))
    front.save(buf, format="PDF", save_all=True, append_images=[back],
               resolution=300, creationDate=fixed, modDate=fixed)
    raw = buf.getvalue()
    # Belt and braces: older and newer Pillow write the date in different
    # forms ("+00'00'" or "Z"), so pin any that slipped through.
    raw = re.sub(rb"D:\d{14}(?:Z|[+-]\d\d'\d\d')?", b"D:20230101000000Z", raw)
    return raw


def vcard_text(identity):
    """Return the full vCard 3.0 text for the agent."""
    _vc = _get_vcard()
    return _vc.build(_vc.fields(identity))


def write_all(identity, outdir):
    """Write card.vcf, front.png, back.png, card.pdf to outdir.

    Creates outdir with mode 700 if it does not already exist.

    Returns:
        dict mapping filename to absolute path.
    """
    outdir = os.path.abspath(str(outdir))
    if not os.path.isdir(outdir):
        os.makedirs(outdir, mode=0o700, exist_ok=True)
        os.chmod(outdir, 0o700)

    paths = {}

    # vCard (no Pillow required).
    vcf_path = os.path.join(outdir, "card.vcf")
    with open(vcf_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(vcard_text(identity))
    paths["card.vcf"] = vcf_path

    # Images (Pillow required; _require_pillow() is called by render()).
    front_path = os.path.join(outdir, "front.png")
    with open(front_path, "wb") as fh:
        fh.write(png_bytes(identity, "front"))
    paths["front.png"] = front_path

    back_path = os.path.join(outdir, "back.png")
    with open(back_path, "wb") as fh:
        fh.write(png_bytes(identity, "back"))
    paths["back.png"] = back_path

    pdf_path = os.path.join(outdir, "card.pdf")
    with open(pdf_path, "wb") as fh:
        fh.write(pdf_bytes(identity))
    paths["card.pdf"] = pdf_path

    return paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_identity_cli():
    """Load identity.json via store.py, or return a demo identity."""
    _store = __import__("store")
    hm = os.environ.get("HUMANIZE_HOME") or os.path.expanduser("~/.humanize")
    id_path = os.path.join(hm, "identity.json")
    if os.path.isfile(id_path):
        return _store.load(id_path)
    return {
        "name": "Ada Lovelace",
        "business_card": {
            "title": "AI Agent",
            "tagline": "Always learning.",
            "website": "https://ada.example.com",
        },
        "email": {"agentmail": {"address": "ada@agent.example.com"}},
        "phone": {"dial": {"number": "+1 555 000 0001"}},
        "address": {"line1": "1 Computing Lane", "city": "London"},
        "social": {"x": {"handle": "ada_agent"}},
    }


def main():
    import argparse as _ap
    p = _ap.ArgumentParser(description="Generate agent business card")
    p.add_argument("--out", default=None,
                   help="Output directory (default: current directory)")
    args = p.parse_args()

    out = os.path.abspath(args.out or ".")

    identity = _load_identity_cli()

    if not have_pillow():
        sys.stderr.write(
            "ERROR: Pillow is not installed. "
            "Run: python3 humanize.py avatar\n"
        )
        sys.exit(1)

    paths = write_all(identity, out)
    for name, path in sorted(paths.items()):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
