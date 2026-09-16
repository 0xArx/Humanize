#!/usr/bin/env python3
"""Generate the agent's avatar: an abstract mark of layered squiggles, no face, no text.

Usage: python3 scripts/avatar.py <seed> [out.png] [size]
The seed is the agent's name. Same seed, same mark, every time.
Needs Pillow: pip install pillow
"""
import sys, random, hashlib, math
try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("pip install pillow")

seed = sys.argv[1] if len(sys.argv) > 1 else "agent"
out = sys.argv[2] if len(sys.argv) > 2 else "face.png"
size = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))

S = size * 4  # draw at 4x then downsample for smooth lines
img = Image.new("RGB", (S, S), (
    rng.choice([(246, 243, 236), (238, 240, 245), (250, 247, 240), (34, 34, 38), (28, 32, 44)])
))
d = ImageDraw.Draw(img)
dark_bg = sum(img.getpixel((0, 0))) < 300
palette = rng.sample([
    (220, 60, 50), (30, 90, 200), (240, 170, 30), (20, 150, 110), (150, 60, 190),
    (250, 110, 70), (40, 170, 220), (230, 80, 150), (90, 200, 90),
], 3)
if dark_bg:
    palette = [tuple(min(255, c + 40) for c in p) for p in palette]

def bezier(p0, p1, p2, p3, n=120):
    for i in range(n + 1):
        t = i / n
        x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
        y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
        yield (x, y)

def rp(margin=0.08):
    return (rng.uniform(S*margin, S*(1-margin)), rng.uniform(S*margin, S*(1-margin)))

# long tangled squiggles: chains of bezier segments
for _ in range(rng.randint(14, 22)):
    color = rng.choice(palette)
    width = rng.randint(S//140, S//55)
    p = rp()
    pts = []
    for _ in range(rng.randint(3, 7)):
        c1, c2, p3 = rp(), rp(), rp()
        pts.extend(bezier(p, c1, c2, p3))
        p = p3
    d.line(pts, fill=color, width=width, joint="curve")

# loops and arcs
for _ in range(rng.randint(6, 12)):
    color = rng.choice(palette)
    cx, cy = rp(0.15)
    r = rng.uniform(S*0.04, S*0.18)
    start = rng.uniform(0, 360)
    d.arc([cx-r, cy-r, cx+r, cy+r], start, start + rng.uniform(120, 400),
          fill=color, width=rng.randint(S//160, S//70))

# short scribbles
for _ in range(rng.randint(20, 40)):
    color = rng.choice(palette)
    x, y = rp(0.1)
    pts = [(x, y)]
    for _ in range(rng.randint(4, 12)):
        x += rng.uniform(-S*0.04, S*0.04); y += rng.uniform(-S*0.04, S*0.04)
        pts.append((x, y))
    d.line(pts, fill=color, width=rng.randint(S//220, S//110), joint="curve")

img = img.resize((size, size), Image.LANCZOS)
img.save(out)
print(out)
