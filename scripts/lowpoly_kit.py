"""Shared helpers for the low-poly PS1 shorts (Blender 5.x, run inside Blender).

- load_character(): append a Quaternius Modular Men character (CC0) with its 24 actions
- add_faces():      flat pixel-art face decals per expression (Mr Omi method), stuck to the head
- nla():            lay pack animations on the timeline (cycles repeat, one-shots are cut)
- drive_root():     key root position + facing from waypoints (pack animations are in place)
- show_faces():     expression schedule -> hard-cut hide_render keys
- aim(), new_cam(), ps1_render_settings()
"""
import bpy, bmesh, math, os
from mathutils import Matrix, Vector

# Quaternius "Ultimate Modular Men" (CC0). Set LOWPOLY_PACK, or unzip the pack into <skill>/assets/.
PACK = os.environ.get("LOWPOLY_PACK") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "quaternius-modular-men",
    "Ultimate Modular Men- Feb 2022", "Individual Characters", "Blends")


# ---------------------------------------------------------------- characters
def load_character(scn, name, exclude=("Pistol",)):
    """Append <name>.blend; returns (armature, {mesh_name: obj}, {action_name: action})."""
    with bpy.data.libraries.load(os.path.join(PACK, name + ".blend")) as (src, dst):
        obj_names = [n for n in src.objects if not any(e in n for e in exclude)]
        act_names = list(src.actions)
        dst_names = list(act_names)          # dst.actions is filled in place with objects
        dst.objects = list(obj_names)
        dst.actions = act_names
    actions = dict(zip(dst_names, dst.actions))     # appended copies may be renamed .001
    arm, meshes = None, {}
    for o in dst.objects:
        scn.collection.objects.link(o)
        if o.type == "ARMATURE":
            arm = o
        elif o.type == "MESH":
            o.hide_render = False                    # the pack ships meshes render-hidden
            o.hide_set(False)
            for p in o.data.polygons:
                p.use_smooth = False                 # PS1 flat shading
            meshes[o.name] = o
    arm.animation_data_create().action = None
    return arm, meshes, actions


# ---------------------------------------------------------------- faces
TEX = 0.005                     # 5 mm texels
TX, TY = 32, 28                 # face grid: x -0.08..0.08, z 1.60..1.74 (rest pose)
X0, Z0 = -0.08, 1.60
EYES = (7, 25)                  # texel x of each eye
DARK, WHITE, BROW = (0.06, 0.04, 0.03), (0.95, 0.94, 0.9), (0.12, 0.07, 0.04)
LIP, MOUTH_IN = (0.45, 0.2, 0.15), (0.25, 0.04, 0.04)


def face_px(kind, x, y, eye_y, brows, mouth):
    for ex in EYES:
        dx, dy = x - ex, y - eye_y
        if kind in ("neutral", "side", "grimace"):
            sx = 1 if kind == "side" else 0          # pupils glance sideways
            if abs(dx - sx) <= 1 and -1 <= dy <= 1 and not (abs(dx - sx) == 1 and dy == 1):
                return DARK
        elif kind == "blink":
            if dy == 0 and abs(dx) <= 2:
                return DARK
        elif kind == "squint":                       # narrowed, determined
            if (dy == 0 and abs(dx) <= 2) or (dy == -1 and abs(dx) <= 1):
                return DARK
        elif kind == "dazed":                        # heavy lids, pupils drift apart
            if dy == 1 and abs(dx) <= 2:
                return DARK
            px_ = -1 if ex < 16 else 1
            if dy == 0 and abs(dx - px_) <= 1:
                return DARK
        elif kind == "xeyes":                        # knocked out
            if abs(dx) == abs(dy) and abs(dx) <= 2:
                return DARK
        elif kind == "shock":
            if dx == 0 and dy == 0:                  # pin-prick pupils
                return DARK
            if dx * dx + dy * dy <= 8:
                return WHITE
        if brows:
            inner = (dx > 0) if ex < 16 else (dx < 0)
            if kind == "shock":
                if (y == eye_y + 6 and abs(dx) <= 1) or (y == eye_y + 5 and abs(dx) == 2):
                    return BROW
            elif kind == "grimace":                  # worried: inner ends up
                if abs(dx) <= 2 and y == eye_y + 3 + (1 if inner and abs(dx) >= 1 else 0):
                    return BROW
            elif kind == "squint":                   # angry: inner ends down
                if abs(dx) <= 2 and y == eye_y + 3 - (1 if inner and abs(dx) >= 1 else 0):
                    return BROW
            elif abs(dx) <= 2 and y == eye_y + 3:
                return BROW
    if mouth:
        if kind == "shock":
            e = (x - 16) ** 2 / 4.5 + (y - 5) ** 2 / 5.5
            if e <= 0.45:
                return MOUTH_IN
            if e <= 1.0:
                return LIP
        elif kind in ("dazed", "xeyes"):             # wobbly open mouth
            if y == 6 + (x % 2) and 12 <= x <= 20:
                return LIP
        elif kind == "grimace":                      # clenched-teeth awkward smile
            if 12 <= x <= 20 and y == 7:
                return WHITE if 13 <= x <= 19 else LIP
            if 12 <= x <= 20 and y in (6, 8):
                return LIP
        elif y == 8 and 13 <= x <= 19:
            return LIP
    return None


def _face_mat(tag, kind, spec):
    img = bpy.data.images.new(f"face_{tag}_{kind}", TX, TY, alpha=True)
    px = []
    for y in range(TY):
        for x in range(TX):
            c = face_px(kind, x, y, spec["eye_y"], spec["brows"], spec["mouth"])
            px += [*c, 1.0] if c else [0, 0, 0, 0]
    img.pixels[:] = px
    img.pack()
    m = bpy.data.materials.new(f"face_{tag}_{kind}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.85
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Closest"
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(t.outputs["Color"], bsdf.inputs["Emission Color"])   # readable in shadow
    bsdf.inputs["Emission Strength"].default_value = spec.get("emit", 0.6)
    try:
        m.surface_render_method = "DITHERED"
    except AttributeError:
        m.blend_method = "CLIP"
    return m


def add_faces(scn, arm, head, tag, kinds, spec, drop):
    """Call BEFORE the armature is moved. drop(material_name, world_center) -> True deletes
    that face of the pack head (its 3D eyes/brows). Returns {kind: decal object}."""
    names = [m.name for m in head.data.materials]
    bm = bmesh.new()
    bm.from_mesh(head.data)
    mw = head.matrix_world
    gone = [f for f in bm.faces if drop(names[f.material_index], mw @ f.calc_center_median())]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.to_mesh(head.data)
    bm.free()

    bone = arm.data.bones["Head"]
    rest = arm.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
    out = {}
    for kind in kinds:
        verts, faces, idx = [], [], {}

        def v(i, j):
            if (i, j) not in idx:
                idx[(i, j)] = len(verts)
                verts.append((X0 + i * TEX, -0.30, Z0 + j * TEX))   # in front; projected back
            return idx[(i, j)]
        for x0, x1, y0, y1 in spec["regions"]:      # only where features live: every vertex hits
            for j in range(y0, y1):
                for i in range(x0, x1):
                    faces.append((v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)))
        me = bpy.data.meshes.new(f"face_{tag}_{kind}")
        me.from_pydata(verts, [], faces)
        uv = me.uv_layers.new()
        inv = {k: c for c, k in idx.items()}
        for loop in me.loops:
            i, j = inv[loop.vertex_index]
            uv.data[loop.index].uv = (i / TX, j / TY)
        me.materials.append(_face_mat(tag, kind, spec))
        o = bpy.data.objects.new(f"face_{tag}_{kind}", me)
        scn.collection.objects.link(o)
        o.parent, o.parent_type, o.parent_bone = arm, "BONE", "Head"
        o.matrix_parent_inverse = rest.inverted()
        sw = o.modifiers.new("stick", "SHRINKWRAP")
        sw.target = head
        sw.wrap_method = "PROJECT"
        sw.use_project_y = True
        sw.use_negative_direction = sw.use_positive_direction = True
        sw.offset = 0.003
        out[kind] = o
    return out


def show_faces(faces, schedule):
    """schedule: [(frame, kind), ...] sorted; each kind holds until the next entry."""
    for f, kind in schedule:
        for k, o in faces.items():
            o.hide_render = (k != kind)
            o.keyframe_insert("hide_render", frame=f)


# ---------------------------------------------------------------- animation
def nla(arm, plan):
    """plan: [(action, start, end, blend[, influence]), ...]; later entries sit on higher tracks.
    Cycles longer than the action repeat; shorter clips are cut (not sped up).
    influence < 1 mixes the clip with the tracks below it (e.g. half a run over an idle =
    a small side-step)."""
    ad = arm.animation_data
    for i, entry in enumerate(plan):
        act, start, end, blend = entry[:4]
        infl = entry[4] if len(entry) > 4 else 1.0
        tr = ad.nla_tracks.new()
        tr.name = f"{i:02d}_{act.name}"
        s = tr.strips.new(tr.name, int(start), act)
        L = act.frame_range[1] - act.frame_range[0]
        n = end - start
        if n > L:
            s.repeat = n / L
        else:
            s.action_frame_end = s.action_frame_start + n
        s.blend_in = min(blend, n / 2)
        s.blend_out = min(blend, n / 2)
        s.extrapolation = "NOTHING"
        if infl < 1.0:
            s.use_animated_influence = True
            n_in = min(blend, n / 2)
            for f, v in ((start, 0.0), (start + n_in, infl), (end - n_in, infl), (end, 0.0)):
                s.influence = v
                s.keyframe_insert("influence", frame=f)


def _smooth(t):
    return t * t * (3 - 2 * t)


def drive_root(arm, waypoints, last):
    """waypoints: [(frame, x, y, yaw, ease)], yaw 0 = facing -Y (toward the default camera).
    ease=True smooths the segment that ENDS at this waypoint (soft start/stop)."""
    for f in range(1, last + 1):
        a = waypoints[0]
        b = waypoints[-1]
        for w0, w1 in zip(waypoints, waypoints[1:]):
            if w0[0] <= f <= w1[0]:
                a, b = w0, w1
                break
        if f <= waypoints[0][0]:
            a = b = waypoints[0]
        elif f >= waypoints[-1][0]:
            a = b = waypoints[-1]
        t = 0.0 if b[0] == a[0] else (f - a[0]) / (b[0] - a[0])
        if b[4]:
            t = _smooth(t)
        arm.location = (a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, 0)
        arm.rotation_euler = (arm.rotation_euler.x, 0, a[3] + (b[3] - a[3]) * t)
        arm.keyframe_insert("location", frame=f)
        arm.keyframe_insert("rotation_euler", index=2, frame=f)


def yaw_to(dx, dy):
    """facing angle for a move direction (yaw 0 faces -Y)."""
    return math.atan2(dx, -dy)


# ---------------------------------------------------------------- cameras / render
def new_cam(scn, name, loc, target, lens):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    scn.collection.objects.link(cam)
    cam.location = loc
    aim(cam, target)
    cam.data.lens = lens
    return cam


def aim(cam, target):
    d = Vector(target) - Vector(cam.location)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def ps1_render_settings(scn, outdir):
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    scn.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scn.render.resolution_x, scn.render.resolution_y = 360, 640
    scn.render.resolution_percentage = 100
    scn.render.filter_size = 0.0
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Punchy"
    try:
        scn.eevee.taa_render_samples = 8
    except AttributeError:
        pass
    scn.render.image_settings.file_format = "PNG"
    scn.render.filepath = os.path.join(outdir, "f_")
