#!/usr/bin/env python3
"""
review_render.py  --  the standard visual review package (Production §16)
=========================================================================
Renders every configuration under IDENTICAL presentation conditions so
buildings are compared against each other, never against different lighting:

    build/review/<name>/front.png  rear.png  left.png  right.png  roof.png
                        entrance.png  objective.png  gameplay_height.png
                        collision.png
                        sheet.png            (contact sheet)
                        review.json          (camera + render provenance)

Consistent by construction: fixed FOV, fixed exposure, neutral sun+sky rig,
fixed resolution, camera positions derived from the recorded bounds (never
hand-placed), and a 1.8 m character-height reference at the primary entrance.

Run inside Blender (or with the bpy module):

    blender --background --python review_render.py -- build/<name>.glb
    python3 review_render.py build/<name>.glb [--fast]

--fast drops to 8 samples / half resolution for iteration; production sheets
use the defaults. Floor plans and sightline overlays (the SVG views) are
already produced by validate.py; this tool adds the rendered views.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

RES = (960, 540)
SAMPLES = 24
FOV_DEG = 50.0
EYE = 1.6              # gameplay-height camera
CHAR_H = 1.8           # character reference


def _reset():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _import_glb(path):
    import bpy
    bpy.ops.import_scene.gltf(filepath=path)
    return list(bpy.context.scene.objects)


def _split_collision(objs):
    vis, col = [], []
    for ob in objs:
        if ob.type != "MESH":
            continue
        (col if ("colonly" in ob.name.lower()) else vis).append(ob)
    return vis, col


def _bounds(objs):
    from mathutils import Vector
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


def _rig_world():
    """Neutral review lighting: one sun, flat grey world. Identical for every
    configuration reviewed, ever."""
    import bpy
    w = bpy.data.worlds.new("review_world")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.57, 0.60, 1.0)
    bg.inputs[1].default_value = 0.8
    bpy.context.scene.world = w
    sun = bpy.data.lights.new("review_sun", type="SUN")
    sun.energy = 3.0
    sun.angle = math.radians(15)
    ob = bpy.data.objects.new("review_sun", sun)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(50), 0, math.radians(35))


def _char_ref(pos):
    """1.8 m grey capsule-proxy box at the primary entrance."""
    import bpy
    import bmesh
    mesh = bpy.data.meshes.new("char_ref")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    from mathutils import Matrix
    mesh.transform(Matrix.Diagonal((0.45, 0.30, CHAR_H, 1.0)))
    ob = bpy.data.objects.new("char_ref", mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (pos[0], pos[1], pos[2] + CHAR_H / 2)
    mat = bpy.data.materials.new("char_ref_mat")
    mat.diffuse_color = (0.9, 0.35, 0.1, 1.0)
    mesh.materials.append(mat)
    return ob


def _headlamp():
    """A camera-riding point light so interior views are readable; identical
    energy for every review render (part of the neutral rig)."""
    import bpy
    lamp = bpy.data.lights.new("review_headlamp", type="POINT")
    lamp.energy = 0.0
    lamp.shadow_soft_size = 0.5
    ob = bpy.data.objects.new("review_headlamp", lamp)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _camera():
    import bpy
    cam = bpy.data.cameras.new("review_cam")
    cam.angle = math.radians(FOV_DEG)
    ob = bpy.data.objects.new("review_cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def _aim(cam, pos, target):
    from mathutils import Vector
    cam.location = pos
    d = Vector(target) - Vector(pos)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _frame_distance(size_u, size_v):
    """Distance so the larger extent fits the FOV with 15% margin."""
    half = max(size_u, size_v) * 0.5 * 1.15
    return half / math.tan(math.radians(FOV_DEG) / 2)


def _render(path, samples, res):
    import bpy
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.exposure = 0.0
    sc.view_settings.view_transform = "Standard"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _hide(objs, hide):
    for ob in objs:
        ob.hide_render = hide


def _entrance_pos(base, lo, hi):
    """Primary entrance guess: main_entry-tagged opening from gameplay.json,
    else mid-front (min-Y face) at ground."""
    gp_path = base + ".gameplay.json"
    if os.path.exists(gp_path):
        with open(gp_path, "r", encoding="utf-8") as f:
            gp = json.load(f)
        for op in gp.get("openings", []):
            if op.get("tag") == "main_entry" and "pos_xyz" in op:
                return op["pos_xyz"]
        for op in gp.get("openings", []):
            if op.get("kind") in ("door", "garage") and "pos_xyz" in op:
                return op["pos_xyz"]
    return [(lo[0] + hi[0]) / 2, lo[1], 0.0]


def _objective_pos(base):
    gp_path = base + ".gameplay.json"
    if os.path.exists(gp_path):
        with open(gp_path, "r", encoding="utf-8") as f:
            gp = json.load(f)
        for o in gp.get("objectives", []):
            return [o.get("x", 0), o.get("y", 0), o.get("z", 0)]
        for m in gp.get("markers", []):
            if m.get("type") == "objective":
                return [m.get("x", 0), m.get("y", 0), m.get("z", 0)]
    return None


def render_review(glb_path, fast=False):
    import bpy
    base = os.path.splitext(glb_path)[0]
    name = os.path.basename(base)
    out_dir = os.path.join(os.path.dirname(glb_path), "review", name)
    os.makedirs(out_dir, exist_ok=True)
    samples = 8 if fast else SAMPLES
    res = (RES[0] // 2, RES[1] // 2) if fast else RES

    _reset()
    objs = _import_glb(glb_path)
    vis, col = _split_collision(objs)
    if not vis:
        raise SystemExit(f"[review] no visual meshes in {glb_path}")
    lo, hi = _bounds(vis)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    cz = (lo[2] + hi[2]) / 2
    sx, sy, sz = hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]

    _rig_world()
    cam = _camera()
    lamp = _headlamp()
    ent = _entrance_pos(base, lo, hi)
    char = _char_ref(ent)
    _hide(col, True)

    shots = {}
    INTERIOR_LAMP_W = 120.0

    def shot(label, pos, target, interior=False):
        _aim(cam, pos, target)
        lamp.location = pos
        lamp.data.energy = INTERIOR_LAMP_W if interior else 0.0
        p = os.path.join(out_dir, f"{label}.png")
        _render(p, samples, res)
        shots[label] = {"camera": [round(v, 3) for v in pos],
                        "target": [round(v, 3) for v in target],
                        "headlamp_w": lamp.data.energy}

    # four exterior elevations at eye-ish height, framed from bounds
    d_ns = _frame_distance(sx, sz)
    d_ew = _frame_distance(sy, sz)
    t = (cx, cy, cz)
    shot("front", (cx, lo[1] - d_ns, cz + sz * 0.25), t)   # -Y face
    shot("rear",  (cx, hi[1] + d_ns, cz + sz * 0.25), t)
    shot("left",  (lo[0] - d_ew, cy, cz + sz * 0.25), t)
    shot("right", (hi[0] + d_ew, cy, cz + sz * 0.25), t)
    # roof: top-down oblique
    d_top = _frame_distance(sx, sy)
    shot("roof", (cx + 0.15 * sx, cy - 0.25 * sy, hi[2] + d_top), (cx, cy, hi[2]))
    # primary entrance: gameplay-height, three-quarter
    shot("entrance", (ent[0] + 6.0, ent[1] - 8.0, EYE + 1.0),
         (ent[0], ent[1], EYE))
    # objective room: gameplay-height from just outside the point
    obj = _objective_pos(base)
    if obj:
        shot("objective", (obj[0] + 3.5, obj[1] - 3.5, obj[2] + EYE),
             (obj[0], obj[1], obj[2] + EYE * 0.6), interior=True)
    # gameplay-height interior: from the entrance looking in
    shot("gameplay_height", (ent[0], ent[1] + 1.0, EYE),
         (cx, cy, EYE), interior=True)
    # collision visualization: hide visual, show collision
    _hide(vis, True)
    _hide([char], True)
    _hide(col, False)
    shot("collision", (cx, lo[1] - d_ns, cz + sz * 0.25), t)
    _hide(vis, False)
    _hide([char], False)
    _hide(col, True)

    # contact sheet
    sheet = _contact_sheet(out_dir, list(shots), name)

    review = {
        "schema_version": 1, "name": name,
        "resolution": res, "samples": samples, "fov_deg": FOV_DEG,
        "character_reference_m": CHAR_H,
        "lighting": "neutral review rig (sun 3.0 + grey world 0.8)",
        "bounds": [lo, hi],
        "shots": shots,
        "sheet": os.path.basename(sheet) if sheet else None,
    }
    with open(os.path.join(out_dir, "review.json"), "w", encoding="utf-8") as f:
        json.dump(review, f, indent=1)
    print(f"[review] {name}: {len(shots)} view(s) -> {out_dir}")
    return out_dir


def _contact_sheet(out_dir, labels, name):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[review] PIL not available; no contact sheet")
        return None
    imgs = []
    for lb in labels:
        p = os.path.join(out_dir, f"{lb}.png")
        if os.path.exists(p):
            imgs.append((lb, Image.open(p)))
    if not imgs:
        return None
    w, h = imgs[0][1].size
    cols = 3
    rows = (len(imgs) + cols - 1) // cols
    pad, cap = 8, 22
    sheet = Image.new("RGB", (cols * (w + pad) + pad,
                              rows * (h + pad + cap) + pad + 30), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 6), f"REVIEW SHEET — {name}", fill=(240, 240, 240))
    for i, (lb, im) in enumerate(imgs):
        r, c = divmod(i, cols)
        x = pad + c * (w + pad)
        y = 30 + pad + r * (h + pad + cap)
        sheet.paste(im, (x, y))
        d.text((x + 2, y + h + 4), lb, fill=(200, 200, 200))
    out = os.path.join(out_dir, "sheet.png")
    sheet.save(out)
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = [a for a in argv[1:] if a.endswith(".glb") or a == "--fast"]
    fast = "--fast" in argv
    globs = [a for a in argv if a.endswith(".glb")]
    if not globs:
        print("usage: review_render.py <built.glb> [--fast]")
        sys.exit(2)
    for g in globs:
        render_review(g, fast=fast)


if __name__ == "__main__":
    main()
