# lowpoly-shorts

A free Claude Code skill that makes vertical low-poly PS1-style 3D shorts in Blender, fully in code.
Blocky CC0 characters, flat pixel faces, crunchy dithered look, word-highlight captions, synced sound effects.
Every render runs on your own machine and costs $0.

Example in `examples/lift-rocket/`: "What if lifts were as fast as rockets?" (34 s, 1080x1920).

## What you need
- [Claude Code](https://claude.com/claude-code)
- [Blender](https://www.blender.org/download/) 4.2 or newer (tested on 5.3)
- Python 3.10+ and ffmpeg
- The free character pack **Ultimate Modular Men** by Quaternius (CC0): https://quaternius.com
- A text-to-speech voice (ElevenLabs or any other)

## Install
```
git clone <this repo> ~/.claude/skills/lowpoly-shorts
pip install numpy pillow soundfile faster-whisper
```
Unzip the character pack into `~/.claude/skills/lowpoly-shorts/assets/quaternius-modular-men/`
(or set `LOWPOLY_PACK` to its `Individual Characters/Blends` folder).

## Use
Open Claude Code in an empty folder and type:
```
Use the lowpoly-shorts skill. Make a short: "What if humans could jump like fleas?"
```
Claude writes the script, cuts the scene to your voice-over, renders, mixes the sound and adds captions.

## Rebuild the example
```
cd examples/lift-rocket
blender -b -P build.py -- frames
python build_mix.py
python post.py
ffmpeg -y -framerate 24 -i out/f_%04d.png -i mix_raw.wav -c:v libx264 -crf 16 -pix_fmt yuv420p -af "loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000" -c:a aac -b:a 192k -shortest short.mp4
```
On a laptop RTX 3070 Ti: render about 2 min, post about 20 s.

## What is inside
| Path | What |
|------|------|
| `SKILL.md` | The instructions Claude follows: pipeline, look rules, sound rules, known bugs |
| `scripts/lowpoly_kit.py` | Characters, pixel faces, animation (NLA), root paths, cameras, render settings |
| `scripts/set_lift_lobby.py` | A ready set (lift lobby) to start from |
| `scripts/words.py` | Word timings from the voice-over (faster-whisper) |
| `scripts/align.py` | Swap the voice-over take without re-cutting the picture |
| `scripts/ps1_post.py` | PS1 colour + dither + upscale, caption font finder |
| `sfx/` | Sound effects, synthesised in code (free to use) |
| `examples/lift-rocket/` | The full example short: script, scene, mix, post |

## Licences
- Code and sounds in this repo: MIT.
- Characters: Quaternius, CC0 (not included, download them from quaternius.com).
- The example voice-over was generated with ElevenLabs.
