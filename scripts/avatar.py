#!/usr/bin/env python3
"""Draw the agent's avatar: flowing luminous ribbons on a dark disc, unique to this agent.
No face, no text. Same seed, same mark, every time.

  python3 scripts/avatar.py <seed> [out.png] [size]     write a PNG (needs Pillow)
  python3 scripts/avatar.py --params <seed>             print the palette and ribbon shapes as JSON

The dashboard animates the same palette and ribbon shapes live (scripts/orb.js). The parameter
derivation below and orb.js must stay identical; tests/test_avatar_parity.py enforces it.
Pillow is looked up in ~/.humanize/pydeps first, where `humanize.py` installs it without touching
the system Python.
"""
import colorsys
import hashlib
import json
import math
import os
import sys

_pd = os.path.join(os.environ.get("HUMANIZE_HOME") or os.path.expanduser("~/.humanize"), "pydeps")
if os.path.isdir(_pd):
    sys.path.insert(0, _pd)


class Rng:
    """mulberry32, identical to the one in orb.js."""

    def __init__(self, seed):
        self.a = seed & 0xFFFFFFFF

    def next(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    def uniform(self, a, b):
        return a + (b - a) * self.next()

    def choice(self, xs):
        return xs[int(self.next() * len(xs))]


def params(seed):
    """Pure function of the seed. The order of random draws is part of the contract with orb.js."""
    h = hashlib.sha256(seed.encode()).digest()
    base = h[0] / 255 * 360
    spread = 28 + h[1] / 255 * 60
    comp = 150 + h[2] / 255 * 60
    sat = 0.85 + h[3] / 255 * 0.15
    hues = [base, (base + spread) % 360, (base - spread) % 360, (base + comp) % 360]
    lights = [0.58, 0.52, 0.66, 0.5]
    rng = Rng(int.from_bytes(h[4:8], "big"))
    ribbons = []
    for i in range(4 + h[5] % 3):
        phase = rng.uniform(0, math.tau)
        a1, a2 = rng.uniform(0.10, 0.22), rng.uniform(0.04, 0.10)
        f1, f2 = rng.choice([1, 2, 3]), rng.choice([2, 3, 5])
        p1, p2 = rng.uniform(0, math.tau), rng.uniform(0, math.tau)
        base_r, tilt = rng.uniform(0.16, 0.30), rng.uniform(0.6, 1.0)
        w_halo, w_core = rng.uniform(0.035, 0.06), rng.uniform(0.010, 0.018)
        drift = rng.uniform(0.05, 0.14) * (1 if i % 2 else -1)
        ribbons.append(dict(phase=phase, a1=a1, a2=a2, f1=f1, f2=f2, p1=p1, p2=p2, base=base_r,
                            tilt=tilt, w_halo=w_halo, w_core=w_core, drift=drift))
    return dict(hues=hues, sat=sat, lights=lights, ribbons=ribbons)


def rgb(p, i):
    r, g, b = colorsys.hls_to_rgb(p["hues"][i] / 360, p["lights"][i], p["sat"])
    return int(r * 255), int(g * 255), int(b * 255)


def render(seed, out, size):
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageFilter
    except ImportError:
        sys.stderr.write("Pillow is required to write a PNG. Run: python3 humanize.py avatar\n")
        sys.exit(3)
    p = params(seed)
    S = size
    img = Image.new("RGB", (S, S), (8, 8, 12))
    canvas = Image.new("RGB", (S, S), (0, 0, 0))
    for idx, r in enumerate(p["ribbons"]):
        c = rgb(p, idx % 4)
        pts = []
        for i in range(361):
            t = math.radians(i) + r["phase"]
            rad = S * (r["base"] + r["a1"] * math.sin(r["f1"] * t + r["p1"]) + r["a2"] * math.sin(r["f2"] * t + r["p2"]))
            pts.append((S / 2 + math.cos(t) * rad, S / 2 + math.sin(t) * rad * r["tilt"]))
        halo = Image.new("RGB", (S, S), (0, 0, 0))
        ImageDraw.Draw(halo).line(pts, fill=c, width=int(S * r["w_halo"]), joint="curve")
        halo = halo.filter(ImageFilter.GaussianBlur(S * 0.05))
        canvas = ImageChops.add(canvas, ImageChops.multiply(halo, Image.new("RGB", (S, S), (170, 170, 170))))
        core = Image.new("RGB", (S, S), (0, 0, 0))
        ImageDraw.Draw(core).line(pts, fill=c, width=max(1, int(S * r["w_core"])), joint="curve")
        core = core.filter(ImageFilter.GaussianBlur(S * 0.006))
        canvas = ImageChops.add(canvas, core)
    cen = Image.new("RGB", (S, S), (0, 0, 0))
    ImageDraw.Draw(cen).ellipse([S * 0.42, S * 0.42, S * 0.58, S * 0.58], fill=(255, 255, 255))
    cen = cen.filter(ImageFilter.GaussianBlur(S * 0.06))
    canvas = ImageChops.add(canvas, ImageChops.multiply(cen, Image.new("RGB", (S, S), (120, 120, 120))))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([S * 0.06, S * 0.06, S * 0.94, S * 0.94], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(S * 0.02))
    img.paste(canvas, (0, 0), mask)
    img.save(out)
    return " ".join("#%02x%02x%02x" % rgb(p, i) for i in range(4))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--params":
        print(json.dumps(params(a[1] if len(a) > 1 else "agent")))
        sys.exit(0)
    seed = a[0] if a else "agent"
    out = a[1] if len(a) > 1 else "face.png"
    size = int(a[2]) if len(a) > 2 else 1024
    print(out, render(seed, out, size))
