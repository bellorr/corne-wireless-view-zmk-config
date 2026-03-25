#!/usr/bin/env python3
"""
Generate a skull-and-crossbones PNG for the nice!view peripheral display.
Output: assets/skull.png  (68×140px portrait — converter rotates to 140×68 landscape)
"""

from PIL import Image, ImageDraw
import os

W, H = 68, 140
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def ellipse(cx, cy, rx, ry, fill="black"):
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


def bone(x0, y0, x1, y1, shaft_w=4, knob_r=6):
    """Draw a bone from (x0,y0) to (x1,y1) with round knobs at each end."""
    import math

    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length  # unit vector along bone
    px, py = -uy, ux  # perpendicular unit vector

    # Shaft polygon
    hw = shaft_w / 2
    pts = [
        (x0 + px * hw, y0 + py * hw),
        (x0 - px * hw, y0 - py * hw),
        (x1 - px * hw, y1 - py * hw),
        (x1 + px * hw, y1 + py * hw),
    ]
    d.polygon(pts, fill="black")

    # Knobs — two circles at each end (offset slightly along the bone axis)
    for cx, cy in [(x0, y0), (x1, y1)]:
        ellipse(cx, cy, knob_r, knob_r)
        # two smaller side knobs
        ellipse(cx + px * (knob_r * 0.7), cy + py * (knob_r * 0.7), knob_r * 0.55, knob_r * 0.55)
        ellipse(cx - px * (knob_r * 0.7), cy - py * (knob_r * 0.7), knob_r * 0.55, knob_r * 0.55)


# ── Skull ────────────────────────────────────────────────────────────────────
cx, cy = 34, 42

# Cranium
ellipse(cx, cy - 4, 26, 24)

# Cheekbones / jaw — slightly wider oval lower
ellipse(cx, cy + 16, 22, 12)

# Clear the gap between cranium and jaw to make jaw look separate
d.rectangle([cx - 18, cy + 8, cx + 18, cy + 16], fill="white")
# Re-draw the jaw
d.rectangle([cx - 20, cy + 12, cx + 20, cy + 24], fill="black")
# Round the jaw corners
ellipse(cx - 18, cy + 18, 5, 6, fill="black")
ellipse(cx + 18, cy + 18, 5, 6, fill="black")

# Re-draw lower cranium over gap
ellipse(cx, cy + 4, 24, 18)

# Eyes (hollow — draw white circles)
ellipse(cx - 11, cy - 2, 8, 9, fill="white")
ellipse(cx + 11, cy - 2, 8, 9, fill="white")

# Nose (small inverted triangle / heart-shaped notch)
d.polygon([(cx, cy + 12), (cx - 4, cy + 7), (cx + 4, cy + 7)], fill="white")

# Teeth — 5 rectangles along jaw bottom
tooth_y0 = cy + 16
tooth_y1 = cy + 26
for i in range(5):
    tx = cx - 16 + i * 8
    d.rectangle([tx + 1, tooth_y0, tx + 6, tooth_y1], fill="white")

# ── Crossbones ───────────────────────────────────────────────────────────────
bone(10, 82, 58, 130, shaft_w=5, knob_r=6)
bone(58, 82, 10, 130, shaft_w=5, knob_r=6)

# ── Save ─────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "..", "assets", "skull.png")
out = os.path.normpath(out)
img.save(out)
print(f"Saved: {out}  ({W}×{H}px)")
