"""Preview render, runs inside Blender. Called by preview.py, not by hand.

blender -b -P preview_blender.py -- <short_dir> <build_script> <preview_dir> <json_settings>

1. Runs the short's build script with --blend-only (scene built, nothing rendered).
2. Reads the shots from the camera markers.
3. Fingerprints every preview frame (cameras, objects, bones, faces, materials, lights, meshes).
4. Renders only the shots whose fingerprint changed (or the shots asked for), small and fast.
5. Writes <preview_dir>/blender_result.json for preview.py.
"""
import bpy, sys, os, json, time, hashlib

T0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:]
SHORT, BUILD, PREV, CFG = argv[0], argv[1], argv[2], json.loads(argv[3])
FRAMES = os.path.join(PREV, "frames")
os.makedirs(FRAMES, exist_ok=True)

# ---------------------------------------------------------------- 1. build the scene
sys.argv = [sys.argv[0], "--", os.path.join(PREV, "build_frames"), "--blend-only"]
os.chdir(SHORT)
g = {"__file__": BUILD, "__name__": "__main__"}
try:
    exec(compile(open(BUILD, encoding="utf-8-sig").read(), BUILD, "exec"), g)
except SystemExit:
    pass
T_BUILD = time.time() - T0
scn = bpy.context.scene
FPS = scn.render.fps / scn.render.fps_base
STEP = int(CFG["step"])
GRID = list(range(scn.frame_start, scn.frame_end + 1, STEP))

# ---------------------------------------------------------------- 2. shots = camera markers
marks = sorted((m for m in scn.timeline_markers if m.camera), key=lambda m: m.frame)
if not marks:
    shots = [dict(name=scn.camera.name if scn.camera else "shot", cam=scn.camera.name if scn.camera else None,
                  start=scn.frame_start, end=scn.frame_end)]
else:
    shots = []
    for i, m in enumerate(marks):
        end = marks[i + 1].frame - 1 if i + 1 < len(marks) else scn.frame_end
        start = max(m.frame, scn.frame_start)
        if end >= start:
            shots.append(dict(name=m.name, cam=m.camera.name, start=start, end=end))


def shot_of(f):
    for s in shots:
        if s["start"] <= f <= s["end"]:
            return s
    return shots[0]


# ---------------------------------------------------------------- 3. fingerprints
R = 5          # decimals kept; float noise below this is ignored


def rnd(v):
    try:
        return tuple(round(float(x), R) for x in v)
    except TypeError:
        return round(float(v), R) if isinstance(v, float) else v


def mat_rows(m):
    return tuple(rnd(row) for row in m)


def node_tree_sig(tree, seen):
    if tree is None or tree.name in seen:
        return ()
    seen.add(tree.name)
    out = []
    for n in sorted(tree.nodes, key=lambda n: n.name):
        row = [n.bl_idname, n.name, n.mute]
        for s in n.inputs:
            if hasattr(s, "default_value") and not s.is_linked:
                try:
                    row.append((s.identifier, rnd(s.default_value)))
                except Exception:
                    pass
        img = getattr(n, "image", None)
        if img is not None:
            row += [img.name, getattr(n, "interpolation", None), image_sig(img)]
        for prop in ("blend_type", "operation", "data_type", "interpolation_type"):
            if hasattr(n, prop):
                row.append(getattr(n, prop))
        if getattr(n, "node_tree", None) is not None:
            row.append(node_tree_sig(n.node_tree, seen))
        if n.bl_idname in ("ShaderNodeValToRGB",):
            row.append(tuple((rnd(e.position), rnd(e.color)) for e in n.color_ramp.elements))
        out.append(tuple(row))
    out.append(tuple(sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                            for l in tree.links)))
    return tuple(out)


_img_cache = {}


def image_sig(img):
    if img.name in _img_cache:
        return _img_cache[img.name]
    sig = [img.filepath, tuple(img.size), img.source]
    if img.source == "GENERATED" or img.packed_file or img.is_dirty or not img.filepath:
        try:
            import numpy as np
            px = np.empty(len(img.pixels), dtype=np.float32)
            img.pixels.foreach_get(px)
            sig.append(hashlib.md5(np.round(px, 4).tobytes()).hexdigest())
        except Exception:
            sig.append(len(img.pixels))
    elif img.filepath:
        p = bpy.path.abspath(img.filepath)
        sig.append(os.path.getmtime(p) if os.path.exists(p) else None)
    _img_cache[img.name] = tuple(sig)
    return _img_cache[img.name]


def h(x):
    return hashlib.md5(repr(x).encode()).hexdigest()


_mat_static = {}


def material_sig(mat):
    """static materials hashed once; animated ones (node tree has an action) hashed every frame."""
    if mat is None:
        return None
    animated = bool(mat.node_tree and mat.node_tree.animation_data and mat.node_tree.animation_data.action) \
        or bool(mat.animation_data and mat.animation_data.action)
    if not animated and mat.name in _mat_static:
        return _mat_static[mat.name]
    sig = h((mat.name, rnd(mat.diffuse_color), mat.blend_method if hasattr(mat, "blend_method") else None,
             node_tree_sig(mat.node_tree, set()) if mat.use_nodes else ()))
    if not animated:
        _mat_static[mat.name] = sig
    return sig


_mesh_static = {}


def mesh_sig(ob):
    me = ob.data
    if me.name not in _mesh_static:
        import numpy as np
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        uv = ()
        if me.uv_layers.active:
            uvs = np.empty(len(me.uv_layers.active.data) * 2, dtype=np.float32)
            me.uv_layers.active.data.foreach_get("uv", uvs)
            uv = hashlib.md5(np.round(uvs, 4).tobytes()).hexdigest()
        mi = np.empty(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", mi)
        _mesh_static[me.name] = h((len(me.vertices), len(me.polygons),
                                   hashlib.md5(np.round(co, 4).tobytes()).hexdigest(), uv,
                                   hashlib.md5(mi.tobytes()).hexdigest()))
    return _mesh_static[me.name]


def modifier_sig(ob):
    out = []
    for m in ob.modifiers:
        row = [m.type, m.name, m.show_render]
        for p in m.bl_rna.properties:
            if p.identifier in ("rna_type", "name", "type") or p.type in ("POINTER", "COLLECTION"):
                continue
            try:
                row.append((p.identifier, rnd(getattr(m, p.identifier))))
            except Exception:
                pass
        out.append(tuple(row))
    return tuple(out)


def static_global_sig():
    r = scn.render
    w = scn.world
    return h((r.engine, r.film_transparent, scn.view_settings.view_transform, scn.view_settings.look,
              rnd(scn.view_settings.exposure), rnd(scn.view_settings.gamma),
              w.name if w else None, node_tree_sig(w.node_tree, set()) if (w and w.use_nodes) else None))


_static_obj = {}


def static_obj_sig(ob):
    """things that do not change over time: geometry, modifiers, non-animated materials."""
    if ob.name not in _static_obj:
        row = [ob.name, ob.type]
        if ob.type == "MESH":
            row += [mesh_sig(ob), modifier_sig(ob)]
        elif ob.type == "LIGHT":
            d = ob.data
            row += [d.type, getattr(d, "use_shadow", None)]
        elif ob.type in ("CURVE", "FONT", "SURFACE", "META"):
            row.append(getattr(ob.data, "body", None))
        _static_obj[ob.name] = h(row)
    return _static_obj[ob.name]


import numpy as np
OBJS = [o for o in sorted(scn.objects, key=lambda o: o.name) if o.type != "CAMERA"]
_bonebuf = {}


def frame_sig(f, deps):
    """one md5 per frame: active camera + every visible object's transform, pose, materials, light."""
    md = hashlib.md5()
    nums = []
    cam = shot_of(f)["cam"]
    cam_ob = bpy.data.objects.get(cam) if cam else scn.camera
    if cam_ob:
        cd = cam_ob.data
        md.update(f"CAM {cam_ob.name} {cd.type} {cd.dof.use_dof}".encode())
        nums.extend(x for row in cam_ob.evaluated_get(deps).matrix_world for x in row)
        nums += [cd.lens, cd.ortho_scale, cd.clip_start, cd.clip_end, cd.sensor_width, cd.shift_x, cd.shift_y,
                 cd.dof.focus_distance, cd.dof.aperture_fstop]
    for ob in OBJS:
        if ob.hide_render or any(c.hide_render for c in ob.users_collection):
            md.update(b"-" + ob.name.encode())
            continue
        md.update(static_obj_sig(ob).encode())
        nums.extend(x for row in ob.evaluated_get(deps).matrix_world for x in row)
        if ob.type == "MESH":
            md.update(repr(tuple(material_sig(s.material) for s in ob.material_slots)).encode())
            if ob.data.shape_keys:
                nums.extend(k.value for k in ob.data.shape_keys.key_blocks)
        elif ob.type == "ARMATURE":
            n = len(ob.pose.bones) * 16
            buf = _bonebuf.get(ob.name)
            if buf is None or len(buf) != n:
                buf = _bonebuf[ob.name] = np.empty(n, dtype=np.float32)
            ob.pose.bones.foreach_get("matrix", buf)
            md.update(np.round(buf, 4).tobytes())
        elif ob.type == "LIGHT":
            d = ob.data
            nums.extend(d.color)
            nums += [d.energy, getattr(d, "spot_size", 0.0), getattr(d, "shadow_soft_size", 0.0)]
        elif ob.type in ("CURVE", "FONT", "SURFACE", "META", "GPENCIL", "GREASEPENCIL"):
            md.update(repr(tuple(material_sig(s.material) for s in ob.material_slots)).encode())
    if scn.world and scn.world.node_tree and scn.world.node_tree.animation_data:
        md.update(repr(node_tree_sig(scn.world.node_tree, set())).encode())
    md.update(np.round(np.array(nums, dtype=np.float64), 4).tobytes())
    return md.hexdigest()


T1 = time.time()
GSIG = static_global_sig()
fps_now = {}
t_set = 0.0
for f in GRID:
    ta = time.time()
    scn.frame_set(f)
    t_set += time.time() - ta
    fps_now[str(f)] = frame_sig(f, bpy.context.evaluated_depsgraph_get())
T_SIG = time.time() - T1
print(f"PREVIEW fingerprint {T_SIG:.1f}s (frame_set {t_set:.1f}s, hashing {T_SIG - t_set:.1f}s)", flush=True)

# ---------------------------------------------------------------- 4. what to render
state_p = os.path.join(PREV, "state.json")
old = json.load(open(state_p)) if os.path.exists(state_p) else {}
settings = dict(step=STEP, scale=CFG["scale"], samples=CFG["samples"], gsig=GSIG,
                res=[scn.render.resolution_x, scn.render.resolution_y])
same_settings = old.get("settings") == settings
old_frames = old.get("frames", {}) if same_settings else {}

why = {}
for s in shots:
    grid = [f for f in GRID if s["start"] <= f <= s["end"]]
    if CFG["mode"] == "all" or not same_settings:
        why[s["name"]] = "all" if CFG["mode"] == "all" else "first run / settings changed"
    elif CFG["mode"] == "shots":
        if s["name"] in CFG["shots"]:
            why[s["name"]] = "asked"
    else:
        missing = [f for f in grid if not os.path.exists(os.path.join(FRAMES, f"f_{f:04d}.png"))]
        changed = [f for f in grid if old_frames.get(str(f)) != fps_now[str(f)]]
        if missing:
            why[s["name"]] = f"{len(missing)} frames missing"
        elif changed:
            why[s["name"]] = f"{len(changed)}/{len(grid)} frames changed"
if CFG["mode"] == "shots":
    unknown = [n for n in CFG["shots"] if n not in {s["name"] for s in shots}]
    if unknown:
        print("PREVIEW unknown shots:", unknown, "known:", [s["name"] for s in shots])

# ---------------------------------------------------------------- 5. render the dirty shots
r = scn.render
r.resolution_percentage = int(CFG["scale"])
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.use_compositing = bool(CFG.get("compositing", False))
r.use_sequencer = False
try:
    scn.eevee.taa_render_samples = int(CFG["samples"])
except AttributeError:
    pass
if r.engine == "CYCLES":
    scn.cycles.samples = max(1, int(CFG["samples"]))
    scn.cycles.use_denoising = True

T2 = time.time()
rendered = 0
for s in shots:
    if s["name"] not in why:
        continue
    grid = [f for f in GRID if s["start"] <= f <= s["end"]]
    if not grid:
        continue
    scn.camera = bpy.data.objects[s["cam"]] if s["cam"] else scn.camera
    scn.frame_start, scn.frame_end, scn.frame_step = grid[0], grid[-1], STEP
    r.filepath = os.path.join(FRAMES, "f_####")
    ts = time.time()
    bpy.ops.render.render(animation=True)
    rendered += len(grid)
    print(f"PREVIEW rendered {s['name']} ({len(grid)} frames, {time.time() - ts:.1f}s): {why[s['name']]}", flush=True)
T_RENDER = time.time() - T2

# frames that changed but sit in shots we did not render (mode=shots) keep their old fingerprint,
# so the next automatic run still sees them as changed
new_frames = {}
for s in shots:
    for f in GRID:
        if s["start"] <= f <= s["end"]:
            k = str(f)
            new_frames[k] = fps_now[k] if (s["name"] in why or old_frames.get(k) == fps_now[k]) else old_frames.get(k)

json.dump(dict(settings=settings, frames=new_frames), open(state_p, "w"))
json.dump(dict(fps=FPS, step=STEP, frame_start=GRID[0], frame_end=max(s["end"] for s in shots),
               res=[int(scn.render.resolution_x * CFG["scale"] / 100), int(scn.render.resolution_y * CFG["scale"] / 100)],
               shots=[dict(s, t0=round((s["start"] - GRID[0]) / FPS, 3), t1=round((s["end"] + 1 - GRID[0]) / FPS, 3))
                      for s in shots],
               grid=GRID, rerendered={k: v for k, v in why.items()}, frames_rendered=rendered,
               seconds=dict(build=round(T_BUILD, 1), fingerprint=round(T_SIG, 1), render=round(T_RENDER, 1))),
          open(os.path.join(PREV, "blender_result.json"), "w"), indent=1)
print(f"PREVIEW done: build {T_BUILD:.1f}s, fingerprint {T_SIG:.1f}s, render {T_RENDER:.1f}s, {rendered} frames",
      flush=True)
