"""Swap a VO take without re-cutting the picture.
The picture is cut to the reference take's word times. Each phrase of the new take is placed
where the same phrase starts in the reference; a phrase too long for its slot is sped up with
ffmpeg atempo (max 1.35x).
Usage: python align.py vo/takeA_words.json vo/takeB.mp3 [--end 33.5]
  needs vo/takeB_words.json (run words.py on takeB first)
-> vo/takeB_aligned.wav (48 kHz mono) + vo/takeB_aligned_words.json (use it for the captions)
"""
import difflib, json, os, re, subprocess, sys, tempfile
import numpy as np, soundfile as sf

SR = 48000
args = sys.argv[1:]
ref_words, take = args[0], args[1]
stem = os.path.splitext(take)[0]
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
A = json.load(open(ref_words))
B = json.load(open(stem + "_words.json"))
END = float(args[args.index("--end") + 1]) if "--end" in args else A[-1]["e"] + 1.5

# phrases in the reference: break on a gap of 0.3 s or more
starts = [0] + [i for i in range(1, len(A)) if A[i]["s"] - A[i - 1]["e"] >= 0.3]
bounds = list(zip(starts, starts[1:] + [len(A)]))

sm = difflib.SequenceMatcher(None, [norm(w["w"]) for w in A], [norm(w["w"]) for w in B], autojunk=False)
amap = {blk.a + k: blk.b + k for blk in sm.get_matching_blocks() for k in range(blk.size)}

with tempfile.TemporaryDirectory() as td:
    w48 = os.path.join(td, "t.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", take, "-ac", "1", "-ar", str(SR), w48], check=True)
    src, _ = sf.read(w48, dtype="float64")
out = np.zeros(int((END + 2) * SR))
words_out = []
for n, (i0, i1) in enumerate(bounds):
    mi = [amap[i] for i in range(i0, i1) if i in amap]
    assert mi, f"phrase {n} ('{' '.join(w['w'] for w in A[i0:i1])}') is missing from the new take"
    b0, b1 = min(mi), max(mi)
    s, e = max(0.0, B[b0]["s"] - 0.04), B[b1]["e"] + 0.12   # max(): a phrase can start at -0.04 s
    seg = src[int(s * SR): int(e * SR)]
    t0 = A[i0]["s"]
    slot = (A[i1]["s"] if i1 < len(A) else END) - t0 - 0.06
    rate = 1.0
    if len(seg) / SR > slot:
        rate = min(1.35, (len(seg) / SR) / slot)
        with tempfile.TemporaryDirectory() as td:
            a, b = os.path.join(td, "a.wav"), os.path.join(td, "b.wav")
            sf.write(a, seg, SR)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a, "-af", f"atempo={rate:.4f}", b], check=True)
            seg, _ = sf.read(b, dtype="float64")
    fade = int(0.01 * SR)
    seg[:fade] *= np.linspace(0, 1, fade)
    seg[-fade:] *= np.linspace(1, 0, fade)
    p = int(t0 * SR)
    out[p:p + len(seg)] += seg[: len(out) - p]
    for j in range(b0, b1 + 1):
        words_out.append({"w": B[j]["w"], "s": round(t0 + (B[j]["s"] - s) / rate, 2),
                          "e": round(t0 + (B[j]["e"] - s) / rate, 2)})
    print(f"phrase {n:2d} @ {t0:5.2f}s  len {(e - s):4.2f}s slot {slot:4.2f}s  x{rate:.2f}  "
          + " ".join(B[j]["w"] for j in range(b0, b1 + 1)))
sf.write(stem + "_aligned.wav", out, SR)
json.dump(words_out, open(stem + "_aligned_words.json", "w"), indent=0)
print("->", stem + "_aligned.wav")
