# Short 1 — "What if lifts were as fast as rockets?" (low-poly PS1, ~38 s)

Started: 2026-11-11 22:11 (for the cost card). Set reused from the lift tests.
Voice: ElevenLabs eleven_v4, "Anna Relaxed" (calm, monotone female = deadpan).

## Facts (checked)
- 0 → 200 km/h (55.6 m/s) in 1 s = 5.7 g of acceleration → you feel ~6.7× your weight ("almost seven times").
- Floor 90 ≈ 360 m (4 m/floor): 28 m during the 1 s launch + 332 m at 55.6 m/s ≈ 6 s → ~7 s total.
- Grey-out (vision goes grey, blood leaves the head) starts around 4–5 g for an untrained person.
- Fastest real lift: Guangzhou CTF Finance Centre (Hitachi), rated 21 m/s = 75.6 km/h, Guinness 2019; everyday speed set to ~20 m/s.
  Sources: hitachi.com press 2019-09-27, Hitachi case study "elevator_china".

## VO
What if lifts were as fast as rockets?
You press the button. The doors slam shut.
Zero to two hundred kilometres an hour. In one second.
Your body suddenly weighs almost seven times more.
Your knees give up first.
Then the blood drains out of your head, and the world goes grey.
Floor ninety. Seven seconds.
Then the lift stops.
You don't.
The fastest real lift tops out at seventy-five kilometres an hour, and it takes its time getting there.
Not for the lift. For you.

## Shots (retimed to the VO word times)
| # | Line | Shot |
|---|------|------|
| 1 | What if lifts were as fast as rockets? | Lobby wide, Suit walks to the lift. Title caption. |
| 2 | You press the button. | Side medium: Interact on the call button, ding, doors open. |
| 3 | The doors slam shut. | Inside the car, looking out: doors slam in 3 frames. Face: side-eye. |
| 4 | Zero to 200 km/h. In one second. | Car interior, hard shake, floor digits race, Suit squashed. Face: shock. |
| 5 | Almost seven times more. | Low angle: squash deeper, HitRecieve. Caption "×7". |
| 6 | Your knees give up first. | Death fall onto his back, inside the car. |
| 7 | Blood drains... world goes grey. | Top-down on him lying; picture drains to grey. Face: dazed. |
| 8 | Floor ninety. Seven seconds. | Close-up on the floor display: 88, 89, 90. |
| 9 | Then the lift stops. | Wide in the car: shake stops dead. Silence. |
| 10 | You don't. | He flies up into the ceiling, thump, drops back. |
| 11 | Fastest real lift... 75 km/h | Doors open on floor 90: the Worker waiting outside, squints at him. |
| 12 | Not for the lift. For you. | Close-up of his face, flat on the floor, blink. Worker walks to the EXIT (stairs). |

## Build log + cost (v1, 2026-11-11)
- Wall time: 22:11 → ~22:30 (script, VO, scene, 3 still rounds, render, mix, post, sync check).
- ElevenLabs VO: 2 takes × 515 credits = 1,030 credits ≈ $0.19 (9.4 ¢ per take). Take A used.
- Render: 820 frames in 92 s (EEVEE 360×640, RTX 3070 Ti laptop). Post (PS1 + grey + captions): 17 s. $0.
- SFX: earshot bank (synthesised) + footsteps from the two-man test. Music: synthesised lo-fi bed (numpy). $0.
- Claude tokens: not measured here (check the plan usage page before/after the next short).
- Sound sync (earshot timeline, 12 cues): 11/12 within 100 ms, 9/12 within one frame, median 18 ms.
- Mix: -16.2 LUFS, -1.1 dBTP.
- Bugs fixed on the way: doors closed with a 0.7 m gap (mesh already holds its offset; old two_man.py has the same bug),
  floor display hidden above a 2.3 m car ceiling (car raised to 2.75 m), Worker visible before floor 90,
  one-frame pose pop when the Death clip hands over to the hold.
- Files: build.py, post.py, build_mix.py → lift_rocket.mp4 (1080×1920, 34 s).

## v2 (2026-11-11, feedback: SFX too loud, VO boring)
- New VO: "Tyler – Clear US YouTube Creator Voice" (rPMkKgdwgIwqv4fXgR6N), eleven_v4, energetic tags. 2 takes × 628 credits ≈ $0.23. Take T2 used (T1 dropped "grey").
- vo/align.py lays each phrase of the new take on take A's phrase start (picture unchanged); only 1 phrase sped up 4%.
- Mix: SFX −8 dB vs v1, music −7 dB, sidechain duck under voice (SFX −5, music −9). VO over the rest: +4 to +27 dB per section.
- Final: −16.5 LUFS, −1.4 dBTP. Total VO spend so far ≈ $0.42.
