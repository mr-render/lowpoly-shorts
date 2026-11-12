"""Low-poly PS1 test room: a lift lobby, vertical 9:16.
Run: blender -b -P room_test.py -- <out.png>
Renders at 360x640 (PS1-ish), the PS1 post pass (ps1_post.py) upscales it.
"""
import bpy, sys, math, random
import numpy as np

BUILD_ONLY = globals().get("BUILD_ONLY", False)   # set by scene scripts that exec this file
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "//room.png"
random.seed(4)

# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

# ---------- helpers ----------
def pixel_tex(name, w, h, fn):
    img = bpy.data.images.new(name, w, h)
    px = np.zeros((h, w, 4), dtype=np.float32)
    for y in range(h):
        for x in range(w):
            px[y, x] = (*fn(x, y), 1.0)
    img.pixels[:] = px.ravel()
    return img

def mat(name, color=None, img=None, rough=0.8, emit=0.0, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if img:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.interpolation = "Closest"          # crisp PS1 texels
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    elif color:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*(color or (1, 1, 1)), 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m

def box(name, loc, size, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    return o

def uv_world(o, scale=1.0):
    """Box-project UVs so tile textures repeat by metre."""
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=scale)
    bpy.ops.object.mode_set(mode="OBJECT")

# ---------- textures ----------
def floor_fn(x, y):
    c = ((x // 8) + (y // 8)) % 2
    base = (0.78, 0.74, 0.66) if c else (0.34, 0.30, 0.28)
    n = random.uniform(-0.03, 0.03)
    if x % 8 == 0 or y % 8 == 0:
        return (0.2, 0.18, 0.17)
    return tuple(max(0, v + n) for v in base)

def wall_fn(x, y):
    n = random.uniform(-0.025, 0.025)
    if y < 10:                                   # wainscot band
        return (0.30 + n, 0.42 + n, 0.40 + n)
    if y == 10:
        return (0.15, 0.2, 0.2)
    return (0.80 + n, 0.76 + n, 0.62 + n)

def metal_fn(x, y):
    n = random.uniform(-0.04, 0.04)
    v = 0.55 + 0.08 * math.sin(x * 0.9) + n
    if x in (15, 16):                            # door seam
        v = 0.15
    return (v, v * 1.02, v * 1.05)

floor_m = mat("floor", img=pixel_tex("floor", 32, 32, floor_fn), rough=0.6)
wall_m = mat("wall", img=pixel_tex("wall", 32, 32, wall_fn))
door_m = mat("door", img=pixel_tex("door", 32, 32, metal_fn), rough=0.3, metal=0.6)
frame_m = mat("frame", color=(0.12, 0.12, 0.13), rough=0.4, metal=0.5)
ceil_m = mat("ceil", color=(0.85, 0.84, 0.8))
light_m = mat("lightpanel", color=(1.0, 0.97, 0.88), emit=6)
led_m = mat("led", color=(0.9, 0.12, 0.08), emit=3)          # red floor digits
btn_m = mat("button", color=(0.95, 0.95, 0.9), emit=1.5)     # soft white call button
steel_m = mat("steel", color=(0.6, 0.6, 0.62), rough=0.35, metal=0.8)
pot_m = mat("pot", color=(0.55, 0.25, 0.14))
leaf_m = mat("leaf", color=(0.12, 0.38, 0.12))
bench_m = mat("bench", color=(0.42, 0.26, 0.14))
skin_m = mat("skin", color=(0.85, 0.62, 0.48))
suit_m = mat("suit", color=(0.13, 0.16, 0.26))

# ---------- room (6 wide, 8 deep, 3.2 high) ----------
W, D, H = 6.0, 8.0, 3.2
f = box("floor", (0, 0, -0.05), (W, D, 0.1), floor_m); uv_world(f, 2.0)
c = box("ceiling", (0, 0, H + 0.05), (W, D, 0.1), ceil_m)
bw = box("wall_back", (0, D / 2, H / 2), (W, 0.1, H), wall_m); uv_world(bw, 3.2)
lw = box("wall_left", (-W / 2, 0, H / 2), (0.1, D, H), wall_m); uv_world(lw, 3.2)
rw = box("wall_right", (W / 2, 0, H / 2), (0.1, D, H), wall_m); uv_world(rw, 3.2)

# lift: frame + two doors + floor indicator
box("lift_frame", (0, D / 2 - 0.08, 1.15), (1.7, 0.12, 2.3), frame_m)
d = box("lift_doors", (0, D / 2 - 0.15, 1.08), (1.4, 0.06, 2.15), door_m); uv_world(d, 2.2)
box("indicator", (0, D / 2 - 0.15, 2.5), (0.5, 0.05, 0.14), frame_m)
box("indicator_led", (0.0, D / 2 - 0.18, 2.5), (0.16, 0.02, 0.08), led_m)
box("call_plate", (1.05, D / 2 - 0.07, 1.1), (0.12, 0.03, 0.22), steel_m)
box("call_button", (1.05, D / 2 - 0.09, 1.1), (0.05, 0.02, 0.05), btn_m)

# ceiling light panels
for y in (-2.0, 1.0):
    box(f"light_{y}", (0, y, H - 0.01), (1.2, 0.6, 0.03), light_m)

# plant (low poly, 6 sides)
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.22, depth=0.45, location=(-2.3, 2.9, 0.225))
bpy.context.object.data.materials.append(pot_m)
for i in range(5):
    a = i / 5 * math.tau
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.12, depth=0.9,
                                    location=(-2.3 + 0.12 * math.cos(a), 2.9 + 0.12 * math.sin(a), 0.85),
                                    rotation=(0.35 * math.sin(a), 0.35 * math.cos(a), a))
    bpy.context.object.data.materials.append(leaf_m)

# bench on the right wall
box("bench_seat", (2.55, 2.0, 0.45), (0.5, 1.8, 0.08), bench_m)
for yy in (1.2, 2.8):
    box(f"bench_leg{yy}", (2.55, yy, 0.22), (0.45, 0.06, 0.44), frame_m)

# placeholder person (blocky) - skipped when a scene script imports the room
if not BUILD_ONLY:
  box("legs", (0.6, 1.6, 0.45), (0.34, 0.2, 0.9), suit_m)
  box("torso", (0.6, 1.6, 1.22), (0.46, 0.26, 0.66), suit_m)
  box("head", (0.6, 1.6, 1.72), (0.24, 0.26, 0.3), skin_m)

# ---------- lights ----------
bpy.ops.object.light_add(type="AREA", location=(0, -1, H - 0.15))
L = bpy.context.object; L.data.energy = 450; L.data.size = 4; L.data.color = (1, 0.95, 0.85)
bpy.ops.object.light_add(type="POINT", location=(0, D / 2 - 1, 2.6))
bpy.context.object.data.energy = 150
bpy.context.object.data.color = (1, 0.8, 0.55)

world = bpy.data.worlds.new("w"); scn.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.05, 0.06, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

# ---------- camera: eye level, slight down tilt, vertical ----------
bpy.ops.object.camera_add(location=(-0.9, -1.6, 1.5), rotation=(math.radians(86), 0, math.radians(-14)))
cam = bpy.context.object; cam.data.lens = 24; scn.camera = cam

# ---------- render ----------
if BUILD_ONLY:
    raise SystemExit  # caught by the importing scene script
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
scn.render.resolution_x, scn.render.resolution_y = 360, 640
scn.render.resolution_percentage = 100
scn.render.filter_size = 0.0                     # no AA blur: hard PS1 edges
scn.view_settings.view_transform = "AgX"; scn.view_settings.look = "AgX - Punchy"
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=out.rsplit(".", 1)[0] + ".blend")
print("RENDERED", out)

