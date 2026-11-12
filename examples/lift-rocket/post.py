"""Post pass for the lift short: PS1 look, grey-out, captions (word highlight), stat callouts.
Run: python post.py  (frames/ -> out/ at 1080x1920)
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
from ps1_post import ps1, find_font

FPS = 24
F = lambda t: int(round(t * FPS)) + 1
SRC, OUT = os.path.join(HERE, "frames"), os.path.join(HERE, "out")
FONT = find_font()
YEL, WHITE, BLACK = (255, 214, 10), (255, 255, 255), (0, 0, 0)

# grey-out: drains from "drains" (15.1 s) to "grey" (17.2 s), snaps back on the ceiling hit
G0, G1, G_OFF = F(15.1), F(17.2), 542 + 6

# captions: 1-3 words, break on punctuation or a pause
words = json.load(open(os.path.join(HERE, "vo", "takeT2_aligned_words.json")))
FIX = {"gray.": "grey.", "kilometers": "km", "200": "200", "75": "75"}
chunks, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    if (w["w"][-1] in ".,?!" or len(cur) == 3 or nxt is None or nxt["s"] - w["e"] > 0.25):
        chunks.append(cur)
        cur = []
CAPS = []
for c in chunks:
    CAPS.append((F(c[0]["s"]), F(c[-1]["e"]) + 2,
                 [(FIX.get(w["w"], w["w"]).strip(".,?!").upper(), F(w["s"])) for w in c]))
# stat callouts (top third)
CALLOUTS = [(146, 233, "0 TO 200 KM/H"), (254, 311, "×7 YOUR WEIGHT"), (F(26.0), 718, "REAL MAX: 75 KM/H")]


def text_w(d, s, f):
    return d.textbbox((0, 0), s, font=f)[2]


def draw_caption(img, f):
    d = ImageDraw.Draw(img)
    for a, b, ws in CAPS:
        if a <= f < b:
            font = ImageFont.truetype(FONT, 92)
            sp = 26
            total = sum(text_w(d, w, font) for w, _ in ws) + sp * (len(ws) - 1)
            x, y = (1080 - total) // 2, 1300
            if total > 940:                          # shrink when long
                font = ImageFont.truetype(FONT, 70)
                total = sum(text_w(d, w, font) for w, _ in ws) + sp * (len(ws) - 1)
                x = (1080 - total) // 2
            for w, ws_f in ws:
                col = YEL if ws_f <= f and (ws_f == max(s for _, s in ws if s <= f)) else WHITE
                d.text((x, y), w, font=font, fill=col, stroke_width=9, stroke_fill=BLACK)
                x += text_w(d, w, font) + sp
            break
    for a, b, s in CALLOUTS:
        if a <= f < b:
            k = min(1.0, (f - a) / 4)                # pop-in scale
            size = int(64 + 26 * k) if k < 1 else 90
            font = ImageFont.truetype(FONT, size)
            w = text_w(d, s, font)
            pad = 26
            x0, y0 = (1080 - w) // 2 - pad, 300
            d.rounded_rectangle((x0, y0, x0 + w + 2 * pad, y0 + size + 40), radius=22,
                                fill=(230, 40, 30), outline=BLACK, width=6)
            d.text((x0 + pad, y0 + 12), s, font=font, fill=WHITE, stroke_width=4, stroke_fill=BLACK)


def grey_amount(f):
    if f < G0 or f >= G_OFF:
        return 0.0
    return min(1.0, (f - G0) / (G1 - G0)) * 0.9


def one(f):
    img = Image.open(os.path.join(SRC, f"f_{f:04d}.png")).convert("RGB")
    g = grey_amount(f)
    if g:
        a = np.asarray(img).astype(np.float32)
        lum = (a @ np.array([0.299, 0.587, 0.114]))[..., None]
        a = a * (1 - g) + lum * g
        h, w = lum.shape[:2]                         # tunnel vision: dark edges
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        a *= (1 - g * 0.75 * np.clip(r - 0.45, 0, 1))[..., None]
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    img = ps1(img, 3)
    draw_caption(img, f)
    img.save(os.path.join(OUT, f"f_{f:04d}.png"))
    return f


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    n = len([x for x in os.listdir(SRC) if x.endswith(".png")])
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(one, range(1, n + 1), chunksize=16))
    print("post done", n)
