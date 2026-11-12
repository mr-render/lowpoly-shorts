"""Word timings for a VO file (faster-whisper, CPU). The whole short is cut to these times.
Usage: python words.py vo/takeA.mp3 [more files...] [--lang en] [--model small.en]
-> vo/takeA_words.json  [{"w": "What", "s": 0.0, "e": 0.18}, ...]
"""
import json, os, subprocess, sys, tempfile
import soundfile as sf
from faster_whisper import WhisperModel

args = sys.argv[1:]
opt = lambda k, d: args[args.index(k) + 1] if k in args else d
lang, model = opt("--lang", "en"), opt("--model", "small.en")
files = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
m = WhisperModel(model if lang == "en" else model.replace(".en", ""), device="cpu", compute_type="int8")
for path in files:
    with tempfile.TemporaryDirectory() as td:          # decode with ffmpeg: avoids PyAV version issues
        wav = os.path.join(td, "a.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", wav], check=True)
        audio, _ = sf.read(wav, dtype="float32")
    segs, _ = m.transcribe(audio, language=lang, word_timestamps=True)
    ws = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in s.words]
    bad = [w["w"] for w in ws if w["e"] - w["s"] < 0.03]
    out = os.path.splitext(path)[0] + "_words.json"
    json.dump(ws, open(out, "w"), indent=0)
    print(out, len(ws), "words", f"| zero-length: {bad} -> prefer another take" if bad else "")
    print(" ".join(f"{w['w']}@{w['s']}" for w in ws))
