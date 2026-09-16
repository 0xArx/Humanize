#!/usr/bin/env python3
"""Generate the agent's avatar: flowing luminous ribbons in a dark disc, unique to this agent.
Think of the Siri energy, not a glass ball. No face, no text.

Usage: python3 scripts/avatar.py <seed> [out.png] [size]
The seed is the agent's name. Same seed, same mark, every time.
The dashboard animates the same ribbons live from the same seed, so they match.
Needs Pillow: pip install pillow
"""
import sys, hashlib, math, colorsys
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageChops
except ImportError:
    sys.exit("pip install pillow")

def palette(seed):
    """Same mapping as dashboard.html: sha256(seed) -> base hue, spread, complement, 4 colours."""
    h = hashlib.sha256(seed.encode()).digest()
    base = h[0] / 255 * 360
    spread = 28 + h[1] / 255 * 60
    comp = 150 + h[2] / 255 * 60
    sat = 0.85 + h[3] / 255 * 0.15
    hues = [base, (base + spread) % 360, (base - spread) % 360, (base + comp) % 360]
    cols = []
    for i, hue in enumerate(hues):
        l = [0.58, 0.52, 0.66, 0.5][i]
        r, g, b = colorsys.hls_to_rgb(hue / 360, l, sat)
        cols.append((int(r * 255), int(g * 255), int(b * 255)))
    return cols, h

class Rng:
    """mulberry32, identical to the one in dashboard.html, so both draw the same ribbons."""
    def __init__(self, seed): self.a = seed & 0xFFFFFFFF
    def next(self):
        self.a = (self.a + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    def uniform(self, a, b): return a + (b - a) * self.next()
    def choice(self, xs): return xs[int(self.next() * len(xs))]

def ribbon(rng, S, phase):
    """A ribbon is a closed-ish flowing curve around the centre: radius varies with two sines."""
    a1, a2 = rng.uniform(0.10, 0.22), rng.uniform(0.04, 0.10)
    f1, f2 = rng.choice([1, 2, 3]), rng.choice([2, 3, 5])
    p1, p2 = rng.uniform(0, math.tau), rng.uniform(0, math.tau)
    base = rng.uniform(0.16, 0.30)
    tilt = rng.uniform(0.6, 1.0)
    pts = []
    for i in range(361):
        t = math.radians(i) + phase
        r = S * (base + a1 * math.sin(f1 * t + p1) + a2 * math.sin(f2 * t + p2))
        pts.append((S / 2 + math.cos(t) * r, S / 2 + math.sin(t) * r * tilt))
    return pts

seed = sys.argv[1] if len(sys.argv) > 1 else "agent"
out = sys.argv[2] if len(sys.argv) > 2 else "face.png"
size = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
cols, h = palette(seed)
rng = Rng(int.from_bytes(h[4:8], "big"))

S = size
bg = (8, 8, 12)
img = Image.new("RGB", (S, S), bg)
canvas = Image.new("RGB", (S, S), (0, 0, 0))

# ribbons: additive glow layers, wide blurred halo plus a sharper bright core
n = 4 + h[5] % 3
for i in range(n):
    c = cols[i % 4]
    pts = ribbon(rng, S, rng.uniform(0, math.tau))
    halo = Image.new("RGB", (S, S), (0, 0, 0))
    ImageDraw.Draw(halo).line(pts, fill=c, width=int(S * rng.uniform(0.035, 0.06)), joint="curve")
    halo = halo.filter(ImageFilter.GaussianBlur(S * 0.05))
    canvas = ImageChops.add(canvas, ImageChops.multiply(halo, Image.new("RGB", (S, S), (170, 170, 170))))
    core = Image.new("RGB", (S, S), (0, 0, 0))
    ImageDraw.Draw(core).line(pts, fill=c, width=int(S * rng.uniform(0.010, 0.018)), joint="curve")
    core = core.filter(ImageFilter.GaussianBlur(S * 0.006))
    canvas = ImageChops.add(canvas, core)

# soft white centre so it reads as light, not paint
cen = Image.new("RGB", (S, S), (0, 0, 0))
ImageDraw.Draw(cen).ellipse([S * 0.42, S * 0.42, S * 0.58, S * 0.58], fill=(255, 255, 255))
cen = cen.filter(ImageFilter.GaussianBlur(S * 0.06))
canvas = ImageChops.add(canvas, ImageChops.multiply(cen, Image.new("RGB", (S, S), (120, 120, 120))))

# clip to a disc with a faint edge so it sits in a round avatar slot cleanly
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).ellipse([S * 0.06, S * 0.06, S * 0.94, S * 0.94], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(S * 0.02))
img.paste(canvas, (0, 0), mask)

img.save(out)
print(out, " ".join("#%02x%02x%02x" % c for c in cols))
