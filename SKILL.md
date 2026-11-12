---
name: lowpoly-shorts
description: Make a 30-60 s vertical low-poly PS1-style 3D short (blocky CC0 characters, flat pixel faces, crunchy dithered look, word-highlight captions, synced SFX, AI voice) fully in code with Blender, at $0 render cost. Use when the user asks for a "low-poly short", "PS1 style video", "what if..." 3D short, or names this skill.
---

# Low-poly PS1 shorts

Everything is code: Claude writes one Blender script per short, renders it on the user's machine,
looks at the frames, fixes them, then builds the sound and captions. No video generator.

Proven on `examples/lift-rocket/` ("What if lifts were as fast as rockets?", 34 s).
Read that example before writing a new short: it is the template.

## Requirements (check first, install what is missing)
- Blender 4.2+ (tested on 5.3). Find it: `blender` on PATH, else
  `C:\Program Files\Blender Foundation\<ver>\blender.exe` / `/Applications/Blender.app/Contents/MacOS/Blender`.
- Python 3.10+ with `numpy pillow soundfile faster-whisper`; `ffmpeg` on PATH.
- Characters: Quaternius "Ultimate Modular Men" (CC0, free, quaternius.com). Unzip into
  `assets/quaternius-modular-men/` or set `LOWPOLY_PACK` to its `Individual Characters/Blends` folder.
- A TTS voice (ElevenLabs or any tool the user has). Optional: the `earshot` MCP to check sound.

## The pipeline (one folder per short, copy `examples/lift-rocket/` as the start)

| # | Step | File / command | Done when |
|---|------|----------------|-----------|
| 1 | Script | `script.md` | Hook question + chain of consequences, each worse and funnier + real numbers + dry punchline. 60-110 words for 30-40 s. Every number checked with a source and written in the Facts list. |
| 2 | Voice | `vo/takeA.mp3` | 2 takes, pick the one with clean word timings. Energetic creator voice, not a calm one (calm = "boring" feedback). |
| 3 | Word timings | `python ../../scripts/words.py vo/takeA.mp3` | `takeA_words.json` has no zero-length words. |
| 4 | Shot list | table in `script.md` | One shot per VO phrase, a new picture every 1-3 s, each shot keyed to a word time. |
| 5 | Scene | `build.py` (Blender) | `blender -b -P build.py -- frames --still 30,120,...` renders stills; look at every still before the full render. |
| 6 | Render | `blender -b -P build.py -- frames` | 360x640 EEVEE PNGs, `f_0001.png`... |
| 7 | Sound | `python build_mix.py` | SFX placed on picture frames, VO on top, lo-fi bed under, ducking. Writes `mix_raw.wav` + `cues.json`. |
| 8 | Post | `python post.py` | PS1 dither, effects, word-highlight captions, stat callouts -> `out/` at 1080x1920. |
| 9 | Mux | see below | `short.mp4`, then measure and check sync. |

Frame rule everywhere: 24 fps, frame 1 = t 0, `F = lambda t: int(round(t * 24)) + 1`.

Mux:
```
ffmpeg -y -framerate 24 -i out/f_%04d.png -i mix_raw.wav -c:v libx264 -crf 16 -pix_fmt yuv420p \
  -af "loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000" -c:a aac -b:a 192k -shortest short.mp4
```

Swap the voice later without re-cutting the picture:
`python ../../scripts/words.py vo/takeB.mp3` then `python ../../scripts/align.py vo/takeA_words.json vo/takeB.mp3 --end 34` (`--end` = where the VO bed stops; output is end + 2 s long. Without it: last word + 1.5 s, which gives a shorter file than the picture)
-> `takeB_aligned.wav` + `takeB_aligned_words.json`. Point `build_mix.py` (VO env var) and `post.py` at them.

## Kit API (`scripts/lowpoly_kit.py`, import inside Blender)
- `load_character(scn, "Suit")` -> `(armature, meshes, actions)`. Characters: Adventurer, Beach,
  Casual_2, Casual_Hoodie, Farmer, King, Punk, Spacesuit, Suit, Swat, Worker.
- Actions (in place, 24): Death, HitRecieve, HitRecieve_2, Idle, Idle_Neutral, Interact, Kick_Left/Right,
  Punch_Left/Right, Roll, Run, Run_Back/Left/Right, Walk, Wave, Gun_Shoot, Idle_Gun*, Idle_Sword, Sword_Slash, Run_Shoot.
- `add_faces(scn, arm, head, tag, kinds, spec, drop)` before moving the armature. Kinds:
  neutral, blink, side, shock, grimace, squint, dazed, xeyes. `drop` deletes the pack's 3D eyes/brows.
- `show_faces(faces, [(frame, kind), ...])`: hard cuts, each face holds until the next.
- `nla(arm, [(action, start, end, blend[, influence]), ...])`: later entries on higher tracks.
- `drive_root(arm, [(frame, x, y, yaw, ease), ...], last)`: yaw 0 faces -Y (the default camera).
- `new_cam`, `aim`, `yaw_to`, `ps1_render_settings(scn, outdir)`.
- Sets: `scripts/set_lift_lobby.py` (exec with `BUILD_ONLY=True`, it returns `box`, `uv_world`, `mat`).
  New sets follow the same pattern: boxes with pixel textures (`interpolation = "Closest"`).

## Look rules
- Render 360x640, `filter_size 0`, AgX Punchy, flat shading; post: 15-bit colour + Bayer dither, x3 nearest.
- Faces are flat 32x28 pixel decals swapped with hard cuts; never animate a face smoothly.
- Squash under force by keying the armature scale (z down, xy up). Comedy beats: fast in (2-3 frames), hold.
- Captions: 1-3 words, heavy sans, white with black stroke, current word yellow, lower third (y 1300 of 1920).
- Stat callouts: red rounded box, top third, pop-in over 4 frames, one per real number.

## Sound rules
- Every SFX is placed so its peak lands on the picture frame (`at(name, frame, db, peak=...)`).
- The voice must win: VO normalised to 0 dBFS, SFX bus -11 dB, music -7 dB, plus sidechain duck
  while the voice talks (SFX -5 dB, music -9 dB). v1 of the lift short had SFX at -3 and music at 0:
  "I can't hear the voiceover".
- Cut the music dead on the big stop beat, bring it back after. Silence sells the gag.
- Master: loudnorm -15 LUFS, true peak -1.5 dBTP.
- Check: earshot `timeline` on the mp4 vs `cues.json` (target: every cue within 100 ms), `measure` for LUFS.

## Bugs already hit (do not repeat)
- Pack meshes ship render-hidden: `hide_render = False` (the kit does it).
- Door meshes already sit at their closed spot: animate the offset only, or they close with a 0.7 m gap.
- A ceiling lower than ~2.75 m hides wall displays from the camera inside a lift-sized car.
- A character who must not be seen yet: key `location.z = -50` until his shot.
- NLA one-shot handing over to a hold: set the clip's `blend_out = 0` or the pose pops for one frame.
- Reverse shots go black (unlit ceiling): add a front light and a little ceiling emission. Render the
  reverse angle early.
- faster-whisper on mp3 can break with a PyAV mismatch: `words.py` decodes with ffmpeg first.
- A phrase starting at -0.04 s gives an empty slice in alignment: clamp with `max(0.0, ...)` (done).

## Cost (lift short, RTX 3070 Ti laptop)
Render 820 frames in 92 s, post 17 s, $0. Characters, SFX, music: $0 (CC0 + synthesised in code).
Voice: ElevenLabs about $0.10 per take, 2 takes per short.

## Before you hand it over
- Look at a contact sheet of the final frames (every ~2 s), not only the stills.
- Measure loudness, check sync, check captions against the VO text (spelling fixes go in post.py `FIX`).
- Tell the user what was measured and what was not heard by a human.
