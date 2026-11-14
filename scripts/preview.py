"""Preview tool for low-poly shorts: a fast low-res preview, notes on the timeline, re-render only what changed.

  python preview.py <short_dir> render              # render shots whose content changed (first run: all)
  python preview.py <short_dir> render --all        # render every shot
  python preview.py <short_dir> render --shots c_press,c_slam
  python preview.py <short_dir> serve [--port 8765] [--no-open]   # the notes page in the browser
  python preview.py <short_dir> notes [--all]       # notes for Claude, grouped by shot
  python preview.py <short_dir> done 3 5 --reply "Turned his head left"

Settings: <short_dir>/preview.json (all optional)
  {"build": "build.py", "audio": "mix_raw.wav", "scale": 50, "step": 2, "samples": 1,
   "final": ["blender -b -P build.py -- frames", "python build_mix.py", "python post.py", "ffmpeg ..."]}
Everything is written to <short_dir>/preview/.
"""
import argparse, glob, json, os, shutil, subprocess, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(build="build.py", audio=None, scale=50, step=2, samples=1, final=[])


# ---------------------------------------------------------------- helpers
def load_cfg(short):
    cfg = dict(DEFAULTS)
    p = os.path.join(short, "preview.json")
    if os.path.exists(p):
        cfg.update(json.load(open(p, encoding="utf-8")))
    return cfg


def find_blender():
    for c in [os.environ.get("BLENDER"), shutil.which("blender")]:
        if c and os.path.exists(c):
            return c
    pats = [r"C:\Program Files\Blender Foundation\Blender *\blender.exe",
            "/Applications/Blender.app/Contents/MacOS/Blender", "/usr/bin/blender", "/snap/bin/blender"]
    found = sorted((p for pat in pats for p in glob.glob(pat)),
                   key=lambda p: [int(x) if x.isdigit() else 0 for x in p.replace(".", " ").split()])
    if found:
        return found[-1]
    sys.exit("Blender not found: put it on PATH or set BLENDER=<path to blender>")


def find_audio(short, cfg):
    if cfg.get("audio"):
        p = os.path.join(short, cfg["audio"])
        return p if os.path.exists(p) else None
    for pat in ("mix_raw.wav", "mix.wav", "vo/*aligned.wav", "vo/*.wav", "vo/*.mp3"):
        hits = sorted(glob.glob(os.path.join(short, pat)))
        if hits:
            return hits[0]
    return None


def prev_dir(short):
    p = os.path.join(short, "preview")
    os.makedirs(p, exist_ok=True)
    return p


def read_json(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(p, data):
    tmp = p + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, p)


# ---------------------------------------------------------------- render
def render(short, mode="changed", shots=(), log=print):
    cfg = load_cfg(short)
    prev = prev_dir(short)
    build = os.path.join(short, cfg["build"])
    if not os.path.exists(build):
        sys.exit(f"build script not found: {build}")
    bcfg = dict(mode=mode, shots=list(shots), scale=cfg["scale"], step=cfg["step"], samples=cfg["samples"])
    t0 = time.time()
    cmd = [find_blender(), "-b", "--factory-startup", "-P", os.path.join(HERE, "preview_blender.py"), "--",
           short, build, prev, json.dumps(bcfg)]
    res_p = os.path.join(prev, "blender_result.json")
    if os.path.exists(res_p):
        os.remove(res_p)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", cwd=short)
    tail = []
    for line in proc.stdout:
        line = line.rstrip()
        tail = (tail + [line])[-60:]
        if line.startswith("PREVIEW") or "Error" in line or "Traceback" in line:
            log(line)
    proc.wait()
    if proc.returncode != 0 or not os.path.exists(res_p):
        log("\n".join(tail[-30:]))
        raise RuntimeError("Blender failed (see the lines above)")
    res = json.load(open(res_p))
    t_blender = time.time() - t0

    # assemble: grid frames -> numbered sequence -> mp4 with the audio
    t1 = time.time()
    seq = os.path.join(prev, "seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    grid = [f for f in res["grid"] if f <= res["frame_end"]]
    for i, f in enumerate(grid, 1):
        src = os.path.join(prev, "frames", f"f_{f:04d}.png")
        if not os.path.exists(src):
            raise RuntimeError(f"frame missing: {src}")
        dst = os.path.join(seq, f"s_{i:05d}.png")
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)
    rate = res["fps"] / res["step"]
    out = os.path.join(prev, "preview.mp4")
    tmp = os.path.join(prev, "preview_tmp.mp4")
    audio = find_audio(short, cfg)
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{rate}", "-i", os.path.join(seq, "s_%05d.png")]
    if audio:
        ff += ["-i", audio]
    ff += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-g", str(int(rate)),
           "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2"]
    if audio:
        ff += ["-c:a", "aac", "-b:a", "160k", "-t", f"{len(grid) / rate:.3f}"]
    ff += ["-movflags", "+faststart", tmp]
    subprocess.run(ff, check=True)
    os.replace(tmp, out)
    shutil.rmtree(seq, ignore_errors=True)
    t_mux = time.time() - t1

    meta = dict(res, audio=os.path.relpath(audio, short) if audio else None, duration=round(len(grid) / rate, 3),
                rendered_at=time.time(), version=int(time.time() * 1000),
                seconds=dict(res["seconds"], blender_total=round(t_blender, 1), mux=round(t_mux, 1),
                             total=round(time.time() - t0, 1)))
    write_json(os.path.join(prev, "shots.json"), meta)
    redo = res["rerendered"]
    log(f"PREVIEW ready: {out}")
    log(f"  shots re-rendered: {len(redo)}/{len(res['shots'])}" + (f" -> {', '.join(redo)}" if redo else " (nothing changed)"))
    log(f"  time: total {meta['seconds']['total']} s (build {res['seconds']['build']}, fingerprint "
        f"{res['seconds']['fingerprint']}, render {res['seconds']['render']}, video {meta['seconds']['mux']})")
    return meta


# ---------------------------------------------------------------- notes
def notes_path(short):
    return os.path.join(prev_dir(short), "notes.json")


_notes_lock = threading.Lock()


def load_notes(short):
    return read_json(notes_path(short), {"notes": [], "next_id": 1, "approved": False})


def shot_at(meta, t):
    for s in meta.get("shots", []):
        if s["t0"] <= t < s["t1"]:
            return s
    return meta["shots"][-1] if meta.get("shots") else None


def add_note(short, t, text):
    meta = read_json(os.path.join(prev_dir(short), "shots.json"), {})
    s = shot_at(meta, t)
    fps = meta.get("fps", 24)
    with _notes_lock:
        d = load_notes(short)
        n = dict(id=d["next_id"], t=round(t, 2), frame=int(round(t * fps)) + meta.get("frame_start", 1),
                 shot=s["name"] if s else None, text=text.strip(), status="open", reply="",
                 created=time.strftime("%Y-%m-%d %H:%M:%S"))
        d["notes"].append(n)
        d["next_id"] += 1
        d["approved"] = False
        write_json(notes_path(short), d)
    return n


def print_notes(short, show_all=False):
    d = load_notes(short)
    ns = [n for n in d["notes"] if show_all or n["status"] == "open"]
    if d.get("approved"):
        print("APPROVED: the user approved the preview. Render the final version.")
    if not ns:
        print("No open notes." if not show_all else "No notes.")
        return
    by = {}
    for n in ns:
        by.setdefault(n["shot"], []).append(n)
    meta = read_json(os.path.join(prev_dir(short), "shots.json"), {})
    order = [s["name"] for s in meta.get("shots", [])]
    for shot in sorted(by, key=lambda x: order.index(x) if x in order else 999):
        s = next((s for s in meta.get("shots", []) if s["name"] == shot), None)
        rng = f"frames {s['start']}-{s['end']}" if s else ""
        print(f"[{shot}] {rng}")
        for n in by[shot]:
            mark = "" if n["status"] == "open" else f"  ({n['status']}: {n['reply']})"
            print(f"  #{n['id']}  {n['t']:.2f}s  frame {n['frame']}: {n['text']}{mark}")


def mark_done(short, ids, reply):
    with _notes_lock:
        d = load_notes(short)
        for n in d["notes"]:
            if n["id"] in ids:
                n["status"], n["reply"] = "done", reply or n.get("reply", "")
        write_json(notes_path(short), d)
    print(f"marked done: {ids}")


# ---------------------------------------------------------------- server
JOB = dict(name=None, running=False, log=[], ok=None, started=None)


def run_job(short, name, fn):
    if JOB["running"]:
        return False

    def log(line):
        JOB["log"] = (JOB["log"] + [str(line)])[-200:]

    def target():
        JOB.update(name=name, running=True, log=[], ok=None, started=time.time())
        try:
            fn(log)
            JOB["ok"] = True
        except Exception as e:      # shown on the page
            log(f"FAILED: {e}")
            JOB["ok"] = False
        JOB["running"] = False

    threading.Thread(target=target, daemon=True).start()
    return True


def final_job(short, cfg):
    def fn(log):
        if not cfg["final"]:
            raise RuntimeError('no "final" commands in preview.json')
        blender = find_blender()
        for c in cfg["final"]:
            c = c.replace("blender ", f'"{blender}" ', 1) if c.startswith("blender ") else c
            log(f"$ {c}")
            p = subprocess.Popen(c, shell=True, cwd=short, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace")
            for line in p.stdout:
                line = line.rstrip()
                if line and not line.startswith(("Fra:", "Saved:", " Time:")):
                    log(line[:300])
            if p.wait() != 0:
                raise RuntimeError(f"command failed: {c}")
        log("FINAL done")
    return fn


def make_handler(short):
    prev = prev_dir(short)
    page = os.path.join(HERE, "preview_page.html")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def _file(self, path, ctype):
            if not os.path.exists(path):
                return self._json({"error": "not found"}, 404)
            size = os.path.getsize(path)
            rng = self.headers.get("Range")
            start, end = 0, size - 1
            if rng and rng.startswith("bytes="):
                a, _, b = rng[6:].partition("-")
                if a:
                    start = int(a)
                    end = int(b) if b else size - 1
                else:
                    start = size - int(b)
                end = min(end, size - 1)
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            else:
                self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                        return
                    left -= len(chunk)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self._file(page, "text/html; charset=utf-8")
            if path == "/preview.mp4":
                return self._file(os.path.join(prev, "preview.mp4"), "video/mp4")
            if path == "/api/state":
                meta = read_json(os.path.join(prev, "shots.json"), {})
                cfg = load_cfg(short)
                return self._json(dict(name=os.path.basename(os.path.abspath(short)), meta=meta,
                                       notes=load_notes(short), job={k: JOB[k] for k in ("name", "running", "ok", "started")},
                                       log=JOB["log"][-40:], has_final=bool(cfg["final"])))
            self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = self.path.split("?")[0]
            body = self._body()
            if path == "/api/notes":
                if not str(body.get("text", "")).strip():
                    return self._json({"error": "empty note"}, 400)
                return self._json(add_note(short, float(body.get("t", 0)), str(body["text"])))
            if path.startswith("/api/notes/"):
                nid = int(path.rsplit("/", 1)[1])
                with _notes_lock:
                    d = load_notes(short)
                    if body.get("delete"):
                        d["notes"] = [n for n in d["notes"] if n["id"] != nid]
                    else:
                        for n in d["notes"]:
                            if n["id"] == nid:
                                for k in ("text", "status"):
                                    if k in body:
                                        n[k] = body[k]
                    write_json(notes_path(short), d)
                return self._json(d)
            if path == "/api/approve":
                with _notes_lock:
                    d = load_notes(short)
                    d["approved"] = bool(body.get("approved", True))
                    write_json(notes_path(short), d)
                return self._json(d)
            if path == "/api/render":
                mode = "all" if body.get("all") else "changed"
                ok = run_job(short, "preview", lambda log: render(short, mode, log=log))
                return self._json({"started": ok})
            if path == "/api/final":
                ok = run_job(short, "final", final_job(short, load_cfg(short)))
                return self._json({"started": ok})
            self._json({"error": "not found"}, 404)

    return H


def serve(short, port, open_browser=True):
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(short))
    url = f"http://127.0.0.1:{port}/"
    print(f"PREVIEW page: {url}  (Ctrl+C to stop)", flush=True)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("short")
    ap.add_argument("cmd", choices=["render", "serve", "notes", "done"])
    ap.add_argument("ids", nargs="*", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--shots", default="")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--reply", default="")
    a = ap.parse_args()
    short = os.path.abspath(a.short)
    if a.cmd == "render":
        if a.shots:
            render(short, "shots", [s.strip() for s in a.shots.split(",") if s.strip()])
        else:
            render(short, "all" if a.all else "changed")
    elif a.cmd == "serve":
        serve(short, a.port, not a.no_open)
    elif a.cmd == "notes":
        print_notes(short, a.all)
    elif a.cmd == "done":
        mark_done(short, set(a.ids), a.reply)


if __name__ == "__main__":
    main()
