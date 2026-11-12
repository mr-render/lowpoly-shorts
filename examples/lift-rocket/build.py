"""Short 1: "What if lifts were as fast as rockets?" (~34 s, PS1 low-poly, Quaternius CC0).

Shot times come from the VO word timings (vo/takeA_words.json).
Run: blender -b -P build.py -- <frames_dir> [--still f1,f2,...]
"""
import bpy, sys, os, math, random

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "..", "scripts")
sys.path.insert(0, SCRIPTS)
import lowpoly_kit as K

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
outdir = os.path.abspath(args[0]) if args else os.path.join(HERE, "frames")   # abspath: Blender's own cwd differs
os.makedirs(outdir, exist_ok=True)
FPS = 24
LAST = 820
F = lambda t: int(round(t * FPS)) + 1          # VO seconds -> frame
random.seed(7)

# ---------------------------------------------------------------- shots (VO take A)
S = dict(
    walk=1,              # "What if lifts were as fast as rockets?"
    press=F(3.10),       # "You press the button"
    slam=F(4.25),        # "The doors slam shut"
    launch=F(6.00),      # "Zero to 200 km/h. In one second."
    seven=F(9.70),       # "...weighs almost seven times more"
    knees=F(12.95),      # "Your knees give up first"
    grey=F(14.40),       # "...blood drains... world goes grey"
    floor=F(18.30),      # "Floor ninety. Seven seconds."
    stops=F(20.40),      # "Then the lift stops."
    dont=F(22.55),       # "You don't."
    open=F(23.75),       # "The fastest real lift... 75 km/h"
    rev=F(26.90),        # "...and it takes its time getting there"
    face=F(29.90),       # "Not for the lift."
    end=F(31.15),        # "For you."
)

# ---------------------------------------------------------------- room
SET = os.path.join(SCRIPTS, "set_lift_lobby.py")
g = {"BUILD_ONLY": True, "__file__": SET}
try:
    exec(open(SET, encoding="utf-8-sig").read(), g)
except SystemExit:
    pass
box, uv_world, mat = g["box"], g["uv_world"], g["mat"]
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, LAST
OB, MAT = bpy.data.objects, bpy.data.materials
D = 8.0

for n in ("wall_back", "lift_frame", "lift_doors"):
    bpy.data.objects.remove(OB[n], do_unlink=True)
wall_m, frame_m, door_m = MAT["wall"], MAT["frame"], MAT["door"]
for name, loc, size in (("wall_back_L", (-1.86, D / 2, 1.6), (2.28, 0.1, 3.2)),
                        ("wall_back_R", (1.86, D / 2, 1.6), (2.28, 0.1, 3.2)),
                        ("wall_back_T", (0, D / 2, 2.7), (1.44, 0.1, 1.0))):
    uv_world(box(name, loc, size, wall_m), 3.2)
box("jamb_L", (-0.79, D / 2 - 0.08, 1.15), (0.14, 0.12, 2.3), frame_m)
box("jamb_R", (0.79, D / 2 - 0.08, 1.15), (0.14, 0.12, 2.3), frame_m)
box("lintel", (0, D / 2 - 0.08, 2.24), (1.72, 0.12, 0.14), frame_m)

# a deep car (2.4 m) so a man can fall flat inside it
CD, CW, CH = 2.4, 1.6, 2.75
CY0 = D / 2 + 0.05
CY = CY0 + CD / 2
box("car_floor", (0, CY, -0.02), (CW, CD, 0.04), MAT["floor"])
uv_world(OB["car_floor"], 2.0)
box("car_ceil", (0, CY, CH), (CW, CD, 0.04), MAT["ceil"])
for name, loc, size in (("car_back", (0, CY0 + CD, CH / 2), (CW, 0.05, CH)),
                        ("car_L", (-CW / 2, CY, CH / 2), (0.05, CD, CH)),
                        ("car_R", (CW / 2, CY, CH / 2), (0.05, CD, CH))):
    uv_world(box(name, loc, size, door_m), 2.2)
box("car_rail", (0, CY0 + CD - 0.06, 0.95), (CW - 0.1, 0.05, 0.05), MAT["steel"])
box("car_panel", (0, CY, CH - 0.03), (0.9, 0.9, 0.02), MAT["lightpanel"])
box("car_btn_plate", (-CW / 2 + 0.04, CY0 + 0.35, 1.15), (0.03, 0.16, 0.36), MAT["steel"])
for i in range(4):
    box(f"car_btn{i}", (-CW / 2 + 0.06, CY0 + 0.35, 1.03 + i * 0.08), (0.02, 0.05, 0.05),
        MAT["button"])
bpy.ops.object.light_add(type="POINT", location=(0.3, CY - 0.4, 2.45))
car_light = bpy.context.object
car_light.data.energy = 90
car_light.data.color = (1, 0.97, 0.9)
car_light.data.shadow_soft_size = 0.3
bpy.ops.object.light_add(type="POINT", location=(0.1, CY0 + 0.15, 1.9))   # fill on faces
bpy.context.object.data.energy = 35

# front wall (reverse shots) with the EXIT (= stairs) door
uv_world(box("wall_front", (0, -D / 2, 1.6), (6.0, 0.1, 3.2), wall_m), 3.2)
box("exit_frame", (0.6, -D / 2 + 0.06, 1.08), (1.04, 0.06, 2.2), frame_m)
box("exit_door", (0.6, -D / 2 + 0.09, 1.05), (0.9, 0.04, 2.1), MAT["bench"])
box("exit_sign", (0.6, -D / 2 + 0.08, 2.4), (0.42, 0.04, 0.16),
    mat("exit_green", color=(0.1, 0.9, 0.3), emit=4))
bpy.ops.object.light_add(type="AREA", location=(0, -3.0, 3.05))
bpy.context.object.data.energy = 220
bpy.context.object.data.size = 3
bpy.context.object.data.color = (1, 0.95, 0.85)
box("light_front", (0, -3.0, 3.19), (1.2, 0.6, 0.03), MAT["lightpanel"])
ceil_bsdf = next(n for n in MAT["ceil"].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
ceil_bsdf.inputs["Emission Color"].default_value = (0.85, 0.84, 0.8, 1)
ceil_bsdf.inputs["Emission Strength"].default_value = 0.22
OB["call_plate"].location.x = OB["call_button"].location.x = 1.5

doors = []
for side in (-1, 1):
    d = box(f"door_{side}", (0.35 * side, D / 2 - 0.15, 1.08), (0.7, 0.06, 2.15), door_m)
    uv_world(d, 2.2)
    doors.append((d, side))


def door_keys(frames_open):            # [(frame, openness 0..1)], constant between keys
    for d, side in doors:
        for f, k in frames_open:
            d.location.x = side * 0.68 * k        # mesh already sits at its closed spot
            d.keyframe_insert("location", index=0, frame=f)


SLAM = S["slam"] + 10                  # on "slam"
door_keys([(1, 1), (SLAM, 1), (SLAM + 3, 0),            # slam in 3 frames
           (S["open"] + 6, 0), (S["open"] + 22, 1),     # floor 90 opens
           (S["end"] + 18, 1), (S["end"] + 40, 0)])     # closes on him
# ---------------------------------------------------------------- floor digits (pixel font)
FONT = {"0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
        "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
        "6": "111100111101111", "7": "111001010010010", "8": "111101111101111",
        "9": "111101111001111"}
led_m = MAT["led"]


def digits(name, text, origin, px, facing):
    """Pixel number centred on origin. facing=-1: readable from -Y (lobby), +1: from +Y (car)."""
    verts, faces = [], []
    w = (len(text) * 4 - 1) * px
    for ci, ch in enumerate(text):
        bits = FONT[ch]
        for r in range(5):
            for c in range(3):
                if bits[r * 3 + c] == "1":
                    x, z = (ci * 4 + c) * px - w / 2, (2.5 - r) * px
                    n = len(verts)
                    verts += [(x, 0, z), (x + px, 0, z), (x + px, 0, z - px), (x, 0, z - px)]
                    faces.append((n, n + 1, n + 2, n + 3))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(led_m)
    o = bpy.data.objects.new(name, me)
    scn.collection.objects.link(o)
    o.location = origin
    if facing > 0:
        o.rotation_euler.z = math.pi
    return o


# inside display, above the doors on the car side of the wall
box("in_disp", (0, D / 2 + 0.06, 2.42), (0.36, 0.02, 0.2), frame_m)
COUNT = list(range(1, 91))
nums = {}
for n in COUNT:
    nums[n] = digits(f"num_{n}", str(n), (0, D / 2 + 0.075, 2.42), 0.022, +1)
# schedule: 1 before launch, races to 89 by the display shot, lands on 90 on "ninety"
launch_t, land = S["launch"] + 2, F(18.55)
sched = [(1, 1)]
for i, n in enumerate(COUNT[1:], start=1):
    p = i / (len(COUNT) - 1)
    sched.append((int(launch_t + (land - launch_t) * (p ** 0.8)), n))
for n, o in nums.items():
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=1)
prev = None
for f, n in sched:
    if prev is not None:
        nums[prev].hide_render = True
        nums[prev].keyframe_insert("hide_render", frame=f)
    nums[n].hide_render = False
    nums[n].keyframe_insert("hide_render", frame=f)
    prev = n
# the lobby display (floor 90 for the ending)
OB["indicator_led"].hide_render = True
lobby90 = digits("lobby_90", "90", (0, D / 2 - 0.185, 2.5), 0.016, -1)
lobby1 = digits("lobby_1", "1", (0, D / 2 - 0.185, 2.5), 0.016, -1)
for o, on in ((lobby90, 0), (lobby1, 1)):
    for f, v in ((1, on), (S["open"], 1 - on)):
        o.hide_render = not v
        o.keyframe_insert("hide_render", frame=f)

# ---------------------------------------------------------------- characters
suit, suit_m, SA = K.load_character(scn, "Suit")
work, work_m, WA = K.load_character(scn, "Worker")
SUIT_SPEC = dict(eye_y=19, brows=True, mouth=True, regions=[(2, 30, 15, 27), (11, 21, 3, 12)])
WORK_SPEC = dict(eye_y=17, brows=False, mouth=False, regions=[(2, 30, 13, 19)])
suit_faces = K.add_faces(scn, suit, suit_m["Suit_Head"], "suit",
                         ("neutral", "blink", "side", "shock", "grimace", "dazed", "xeyes"),
                         SUIT_SPEC, drop=lambda m, c: m in ("Eye", "Eyebrows"))
work_faces = K.add_faces(scn, work, work_m["Worker_Head"], "work",
                         ("neutral", "blink", "side", "squint"), WORK_SPEC,
                         drop=lambda m, c: m == "Eye" or (m == "Eyebrows" and c.y < -0.14
                                                         and 1.69 < c.z < 1.74 and abs(c.x) < 0.1))
PI = math.pi
IN = (-0.25, CY0 + 0.6)                # where he stands in the car, facing the doors (-Y)

# ---- suit: root path
K.drive_root(suit, [(1, 0.2, 1.3, PI, False), (S["press"] - 4, -0.15, CY0 + 0.5, PI, True),
                    (S["press"] - 1, -0.15, CY0 + 0.5, PI, False),
                    (S["press"], *IN, 0.0, False), (LAST, *IN, 0.0, False)], LAST)
# squash under g-force (keyed scale on the armature object)
def key_scale(f, sz, sxy=None):
    sxy = sxy if sxy is not None else 1 + (1 - sz) * 0.6
    suit.scale = (sxy, sxy, sz)
    suit.keyframe_insert("scale", frame=f)
key_scale(1, 1.0)
key_scale(S["launch"] + 2, 1.0)
key_scale(S["launch"] + 5, 0.86)
key_scale(S["seven"] + 20, 0.86)
key_scale(S["seven"] + 26, 0.74)
key_scale(S["knees"] - 1, 0.74)
key_scale(S["knees"], 1.0, 1.0)
# "You don't": he keeps going up, hits the ceiling, drops back
for f, z in ((1, 0.0), (S["dont"] + 2, 0.0), (S["dont"] + 6, 2.2), (S["dont"] + 9, 2.2),
             (S["dont"] + 18, 0.0), (S["dont"] + 21, 0.06), (S["dont"] + 24, 0.0)):
    suit.location.z = z
    suit.keyframe_insert("location", index=2, frame=f)

# ---- suit: animation
DIE = S["knees"] + 6                   # on "knees"
K.nla(suit, [(SA["Walk"], 1, S["press"] + 1, 0),
             (SA["Idle_Neutral"], S["press"], DIE + 2, 3),
             (SA["Interact"], S["press"] + 4, S["press"] + 30, 3),
             (SA["HitRecieve"], S["launch"] + 2, S["launch"] + 12, 2),
             (SA["HitRecieve"], S["seven"] + 20, S["seven"] + 30, 2),
             (SA["Death"], DIE, DIE + 32, 2)])
# hold the last Death frame (lying flat) to the end
suit.animation_data.nla_tracks[-1].strips[0].blend_out = 0   # no pop into the hold
tr = suit.animation_data.nla_tracks.new()
tr.name = "99_lying"
hold = tr.strips.new("lying", DIE + 32, SA["Death"])
hold.action_frame_start, hold.action_frame_end = 31.0, 32.0
hold.scale = (LAST - DIE - 31)
hold.extrapolation = "HOLD_FORWARD"

K.show_faces(suit_faces, [(1, "neutral"), (30, "blink"), (32, "neutral"),
                          (S["press"] + 18, "side"),
                          (S["launch"] + 3, "shock"), (S["knees"] + 2, "grimace"),
                          (S["grey"], "dazed"), (S["dont"] + 6, "xeyes"),
                          (S["face"] + 14, "dazed"), (S["face"] + 22, "blink"),
                          (S["face"] + 24, "dazed")])

# ---- worker: waits on floor 90, looks in, takes the stairs
WX, WY = 0.25, 2.55
EXIT = (0.6, -D / 2 + 0.5)
ex_yaw = K.yaw_to(EXIT[0] - WX, EXIT[1] - WY)
TURN = S["end"] + 4
K.drive_root(work, [(1, WX, WY, PI, False), (TURN, WX, WY, PI, False),
                    (TURN + 10, WX, WY, ex_yaw, True), (LAST, EXIT[0] + 0.0, -1.2, ex_yaw, False)],
             LAST)
for f in range(1, S["open"]):           # he is on floor 90: off-set until the doors open
    work.location.z = -50
    work.keyframe_insert("location", index=2, frame=f)
K.nla(work, [(WA["Idle_Neutral"], 1, TURN + 4, 0), (WA["Walk"], TURN, LAST + 1, 4)])
K.show_faces(work_faces, [(1, "neutral"), (S["open"] + 26, "squint"), (S["rev"] + 30, "side"),
                          (S["rev"] + 44, "squint"), (TURN, "neutral")])

# ---------------------------------------------------------------- cameras
cams = {}
def cam(name, loc, tgt, lens):
    cams[name] = K.new_cam(scn, name, loc, tgt, lens)
    return cams[name]

c1 = cam("c_walk", (-0.6, -0.9, 1.5), (0.0, 4.6, 1.15), 24)          # lobby wide toward the lift
for f, loc in ((1, (-0.6, -0.9, 1.5)), (S["press"], (-0.45, -0.3, 1.5))):
    c1.location = loc
    c1.keyframe_insert("location", frame=f)
cam("c_press", (0.55, 2.4, 1.55), (-0.25, CY0 + 0.55, 1.2), 30)       # into the open car
cam("c_slam", (0.1, 2.0, 1.5), (-0.05, CY0 + 0.6, 1.45), 26)          # the doors slam on us
c4 = cam("c_launch", (0.12, CY0 + 0.1, 1.5), (-0.25, CY0 + 0.65, 1.3), 15)   # inside, from the back
c5 = cam("c_seven", (0.1, CY0 + 0.12, 0.35), (-0.25, CY0 + 0.6, 1.15), 14)       # low, looking up
c6 = cam("c_knees", (0.72, CY0 + 1.0, 1.0), (-0.3, CY0 + 1.0, 0.6), 17)        # side, he falls
c7 = cam("c_grey", (-0.2, CY0 + 1.4, 2.6), (-0.2, CY0 + 1.4, 0.0), 30)    # top-down
c7.rotation_euler = (0, 0, 0)                                          # head at the top of frame
c8 = cam("c_floor", (0.0, CY0 + 0.75, 2.2), (0.0, D / 2, 2.43), 50)    # the display
c9 = cam("c_stops", (0.7, CY0 + 2.25, 1.9), (-0.25, CY0 + 0.9, 0.4), 16)       # wide inside
c10 = cam("c_dont", (0.65, CY0 + 2.2, 0.3), (-0.25, CY0 + 1.0, 1.3), 15)       # low wide, sees ceiling
c11 = cam("c_open", (0.9, 1.5, 1.8), (-0.2, CY0 + 1.2, 0.25), 26)    # over the worker's shoulder
c12 = cam("c_rev", (0.45, CY0 + 0.3, 0.3), (WX, WY, 1.55), 20)        # from the floor, up at him
c13 = cam("c_face", (-0.25, CY0 + 1.93, 0.85), (-0.25, CY0 + 1.93, 0.0), 40)   # his face, top-down
c13.rotation_euler = (0, 0, 0)
c14 = cam("c_end", (-0.05, CY0 + 2.2, 1.6), (0.3, -2.0, 1.0), 20)       # from inside, worker leaves

# floor-display shot: counting is fast; slow push
for f, lens in ((S["floor"], 50), (S["stops"] - 1, 60)):
    c8.data.lens = lens
    c8.data.keyframe_insert("lens", frame=f)
for f, lens in ((S["face"], 40), (S["end"] - 1, 48)):
    c13.data.lens = lens
    c13.data.keyframe_insert("lens", frame=f)

order = [("c_walk", "walk"), ("c_press", "press"), ("c_slam", "slam"), ("c_launch", "launch"),
         ("c_seven", "seven"), ("c_knees", "knees"), ("c_grey", "grey"), ("c_floor", "floor"),
         ("c_stops", "stops"), ("c_dont", "dont"), ("c_open", "open"), ("c_rev", "rev"),
         ("c_face", "face"), ("c_end", "end")]
for cname, key in order:
    scn.timeline_markers.new(cname, frame=S[key]).camera = cams[cname]
scn.camera = c1

# camera shake while the car moves: launch -> stops (amplitude in metres / radians)
def shake_amp(f):
    if S["launch"] + 2 <= f < S["launch"] + 30:
        return 0.035
    if S["launch"] + 30 <= f < S["stops"] + 20:
        return 0.012
    if S["stops"] + 20 <= f < S["stops"] + 23:
        return 0.05                     # the stop jolt
    if S["dont"] + 6 <= f < S["dont"] + 10:
        return 0.04                     # ceiling hit
    if S["dont"] + 18 <= f < S["dont"] + 21:
        return 0.03                     # floor hit
    return 0.0

for cname in ("c_launch", "c_seven", "c_knees", "c_grey", "c_floor", "c_stops", "c_dont"):
    c = cams[cname]
    base_l, base_r = c.location.copy(), c.rotation_euler.copy()
    for f in range(1, LAST + 1, 1):
        a = shake_amp(f)
        if a == 0 and shake_amp(f - 1) == 0:
            continue
        c.location = (base_l.x + random.uniform(-a, a), base_l.y + random.uniform(-a, a),
                      base_l.z + random.uniform(-a, a))
        c.rotation_euler = (base_r.x + random.uniform(-a, a) * 0.6, base_r.y,
                            base_r.z + random.uniform(-a, a) * 0.6)
        c.keyframe_insert("location", frame=f)
        c.keyframe_insert("rotation_euler", frame=f)

# ---------------------------------------------------------------- render
K.ps1_render_settings(scn, outdir)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, "..", "lift_rocket.blend"))
if "--still" in args:
    fl = [int(x) for x in args[args.index("--still") + 1].split(",")]
    for f in fl:
        scn.frame_set(f)
        scn.camera = next(m.camera for m in sorted(scn.timeline_markers, key=lambda m: -m.frame)
                          if m.frame <= f)
        scn.render.filepath = os.path.join(outdir, f"still_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print("DONE", outdir, S)
