"""Mix for the lift-rocket short: VO + SFX on picture frames + a synthesised lo-fi bed.
Frame numbers match build.py (24 fps, frame 1 = t 0).
Run: python build_mix.py  -> mix.wav, cues.json
"""
import json, os
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SFX = os.path.join(HERE, "..", "..", "sfx")          # shared synthesised SFX bank
SR, FPS, LAST = 48000, 24, 820
N = int(LAST / FPS * SR) + SR
F = lambda t: int(round(t * FPS)) + 1
T = lambda f: (f - 1) / FPS
S = dict(walk=1, press=75, slam=103, launch=145, seven=234, knees=312, grey=347, floor=440,
         stops=491, dont=542, open=571, rev=647, face=719, end=749)
SLAM, DIE, TURN, STOP = S["slam"] + 10, S["knees"] + 6, S["end"] + 4, S["stops"] + 20

sfx = np.zeros((N, 2))
cues = []


def load(name):
    a, sr = sf.read(os.path.join(SFX, name), dtype="float64", always_2d=True)
    assert sr == SR, name
    return a if a.shape[1] == 2 else np.repeat(a, 2, axis=1)


def at(name, frame, db, kind=None, peak=0.0, lp=None):
    """place a sound so its peak (seconds into the file) lands on the frame"""
    a = load(name) * 10 ** (db / 20)
    if lp:                                   # one-pole low-pass for distant / muffled
        k = np.exp(-2 * np.pi * lp / SR)
        for c in range(2):
            y, prev = np.empty_like(a[:, c]), 0.0
            for i, v in enumerate(a[:, c]):
                prev = (1 - k) * v + k * prev
                y[i] = prev
            a[:, c] = y
    s = int((T(frame) - peak) * SR)
    s0 = max(s, 0)
    a = a[s0 - s:]
    e = min(N, s0 + len(a))
    sfx[s0:e] += a[: e - s0]
    if kind:
        cues.append({"f": frame, "kind": kind})


# ---------------------------------------------------------------- sound effects
for i, f in enumerate((4, 24, 44, 64)):                       # suit walks in
    at(["stepA.wav", "stepB.wav"][i % 2], f, -9, "step" if i == 0 else None)
at("button.wav", 93, -4, "button")
at("ding.wav", 96, -14)
at("slide.wav", SLAM, -8, peak=0.45)
at("slam.wav", SLAM + 3, -3, "slam", peak=0.117)
at("punch.wav", SLAM + 3, -6, peak=0.058)
L = S["launch"] + 2                                           # 0 -> 200 km/h
at("jet.wav", L, -2, "launch", peak=0.25)
at("boom.wav", L, -3, peak=0.084)
at("squash.wav", L + 3, -6, peak=0.076)
at("pop.wav", S["launch"] + 1, -12)                           # callout
at("squash2.wav", S["seven"] + 20, -4, "squash", peak=0.181)
at("pop.wav", S["seven"] + 14, -12)
at("thump.wav", DIE + 22, -2, "fall")
at("punch.wav", DIE + 22, -8, peak=0.058)
# floor counter ticks (same schedule as the picture) + ding on 90
land = F(18.55)
prev = None
for i in range(1, 90):
    f = int(L + (land - L) * ((i / 89) ** 0.8))
    if f >= S["floor"] - 2 and f != prev:
        at("tick.wav", f, -10)
    prev = f
at("ding.wav", land, -9, "ninety")
at("slam.wav", STOP, -2, "stop", peak=0.117)                  # the lift stops dead
at("boom.wav", STOP, -8, peak=0.084)
D = S["dont"]
at("up.wav", D + 6, -4, peak=0.17)                            # he keeps going
at("punch.wav", D + 6, -2, "ceiling", peak=0.058)
at("clunk.wav", D + 6, -6, peak=0.024)
at("thump.wav", D + 18, -1, "floor")
at("punch.wav", D + 18, -6, peak=0.058)
at("thump.wav", D + 21, -10)
at("ding.wav", S["open"] + 2, -8, "ding90")
at("slide.wav", S["open"] + 14, -10, peak=0.45)
at("pop.wav", F(26.0), -12)
for i, f in enumerate(range(TURN + 7, LAST, 20)):            # worker takes the stairs
    at("stepC.wav", f, -11 - i)
at("slide.wav", S["end"] + 31, -10, peak=0.45)
at("clunk.wav", S["end"] + 40, -5, "close", peak=0.024)

# ---------------------------------------------------------------- beds
t = np.arange(N) / SR
rng = np.random.default_rng(3)


def brown(n, cutoff):
    w = rng.standard_normal(n)
    k = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty(n)
    p = 0.0
    for i in range(n):
        p = (1 - k) * w[i] + k * p
        y[i] = p
    return y / (np.abs(y).max() + 1e-9)


def env(points):
    """[(frame, gain_db or None for silence)] -> linear gain per sample (linear interpolation)"""
    xs = [T(f) for f, _ in points]
    ys = [0.0 if g is None else 10 ** (g / 20) for _, g in points]
    return np.interp(t, xs, ys)


room = brown(N, 400) * env([(1, -40), (L, -40), (L + 1, -46), (LAST, -46)])
rumble_src = brown(N, 90) + 0.5 * np.sin(2 * np.pi * 42 * t)
rumble = rumble_src * env([(1, None), (L - 1, None), (L, -8), (L + 30, -16), (STOP - 1, -18),
                           (STOP, None), (LAST, None)])
hum = 0.5 * np.sin(2 * np.pi * 120 * t) * env([(1, None), (SLAM, None), (SLAM + 4, -40),
                                                (STOP, -40), (STOP + 1, None), (LAST, None)])
g0, g1 = F(15.1), F(17.2)                                     # grey-out ring
ring = np.sin(2 * np.pi * 3400 * t) * env([(1, None), (g0, None), (g1, -30), (D + 5, -30),
                                           (D + 6, None), (LAST, None)])
beds = (room + rumble + hum + ring)[:, None] * np.ones((1, 2))

# ---------------------------------------------------------------- lo-fi bed (synth)
BEAT = 60 / 82
CH = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]   # Fmaj7 Em7 Dm7 Cmaj7
mus = np.zeros(N)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def ep(m, start, dur, vel):
    s = int(start * SR)
    n = min(int(dur * SR), N - s)
    if n <= 0:
        return
    tt = np.arange(n) / SR
    f0 = hz(m)
    x = (np.sin(2 * np.pi * f0 * tt) + 0.25 * np.sin(2 * np.pi * 2 * f0 * tt) * np.exp(-tt * 6)
         + 0.08 * np.sin(2 * np.pi * 3 * f0 * tt) * np.exp(-tt * 9))
    x *= np.exp(-tt * 1.6) * np.minimum(1, tt / 0.004) * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * tt))
    mus[s:s + n] += vel * x


bar = 4 * BEAT
for b in range(int(t[-1] / bar) + 1):
    ch = CH[b % 4]
    for beat, vel in ((0, 0.22), (1.5, 0.14), (2.5, 0.12)):
        for k, m in enumerate(ch):
            ep(m, b * bar + beat * BEAT + 0.012 * k, 1.6, vel)
    ep(ch[0] - 12, b * bar, bar, 0.3)                          # bass
    for beat in (0.5, 1.5, 2.5, 3.5):                          # soft hats
        s = int((b * bar + beat * BEAT) * SR)
        n = min(int(0.05 * SR), N - s)
        if n > 0:
            mus[s:s + n] += 0.03 * rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 80)
# warm it up (low-pass) and wow/flutter-free gain envelope: cut dead when the lift stops,
# back when the doors open on floor 90, ducked under the grey-out
k = np.exp(-2 * np.pi * 2200 / SR)
y, p = np.empty(N), 0.0
for i in range(N):
    p = (1 - k) * mus[i] + k * p
    y[i] = p
mus = y / np.abs(y).max()
mus *= env([(1, -22), (g0, -22), (g1, -32), (STOP - 1, -32), (STOP, None), (S["open"] + 1, None),
            (S["open"] + 2, -24), (LAST - 24, -24), (LAST, None)])
music = mus[:, None] * np.ones((1, 2))

# ---------------------------------------------------------------- VO
VO_FILE = os.environ.get("VO", "takeT2_aligned.wav")          # v2: energetic take laid on take A's timings
vo, sr = sf.read(os.path.join(HERE, "vo", VO_FILE), dtype="float64", always_2d=True)
assert sr == SR
vo = np.repeat(vo, 2, axis=1) if vo.shape[1] == 1 else vo
vo = vo / np.abs(vo).max()                                    # VO peaks at 0 dBFS before the master
voice = np.zeros((N, 2))
voice[: min(N, len(vo))] = vo[:N]

# sidechain: where the voice talks, SFX dip 5 dB and music dips 9 dB (fast attack, 250 ms release)
lvl = np.abs(voice[:, 0])
hop = SR // 100
rms = np.sqrt(np.convolve(lvl ** 2, np.ones(hop) / hop, mode="same"))
talk = (rms > 10 ** (-38 / 20)).astype(float)
k = np.exp(-1 / (0.25 * SR))
for i in range(1, N):                                         # hold-and-release smoothing
    talk[i] = max(talk[i], talk[i - 1] * k)
duck = lambda db: (10 ** (-db * talk / 20))[:, None]

SFX_DB, MUSIC_DB = -11, -7                                    # v1 was -3 / 0 -> SFX buried the voice
mix = voice + sfx * 10 ** (SFX_DB / 20) * duck(5) + beds * duck(5) + music * 10 ** (MUSIC_DB / 20) * duck(9)
mix = mix[: int(LAST / FPS * SR)]
sf.write(os.path.join(HERE, "mix_raw.wav"), mix, SR, subtype="FLOAT")
json.dump({"fps": FPS, "events": cues}, open(os.path.join(HERE, "cues.json"), "w"), indent=1)
print("cues", len(cues), "peak", round(20 * np.log10(np.abs(mix).max()), 1), "dBFS")
