"""PS1 post pass: 15-bit colour with ordered dither, then nearest-neighbour upscale.
Usage: python ps1_post.py in.png out.png [--scale 3]
"""
import os, sys
import numpy as np
from PIL import Image

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5
FONTS = [  # heavy sans for captions, first one found wins (override with CAPTION_FONT)
    r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/Library/Fonts/Arial Black.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def find_font():
    for p in [os.environ.get("CAPTION_FONT")] + FONTS:
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError("No caption font found: set CAPTION_FONT to a bold .ttf")


def ps1(img, scale=3, levels=32):
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    h, w, _ = a.shape
    th = np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w][..., None]
    a = np.clip(np.round(a * (levels - 1) + th) / (levels - 1), 0, 1)   # 5 bits per channel
    out = Image.fromarray((a * 255).astype(np.uint8))
    return out.resize((w * scale, h * scale), Image.NEAREST)


if __name__ == "__main__":
    scale = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 3
    ps1(Image.open(sys.argv[1]), scale).save(sys.argv[2])
    print("saved", sys.argv[2])
