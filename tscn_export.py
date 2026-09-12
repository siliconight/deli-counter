"""tscn_export.py - emit a Godot .tscn that instances module GLBs from a Deli
Counter slot manifest.

bpy-free on purpose: it operates purely on slot data (the same records written to
<name>.slots.json), so it runs OUTSIDE Blender - build.py calls it as a post-build
step. Each slot becomes an instanced-scene node referencing
res://<root>/<ref>.glb at the slot transform, converted from Blender Z-up to
Godot Y-up. Because every instance points at the one PackedScene resource,
editing a module .glb updates every instance in the editor (native Godot prefab
behaviour) - the alternative to the baked single-GLB output.

This is the SCENE serializer of the build; the baked .glb is the other. Both
read the same slot manifest, so they never disagree about what goes where.
"""

import json
import math
import os


def _f(v):
    return repr(round(float(v), 6))


def _godot_transform(translation, rot_y_deg, scale):
    """Blender Z-up slot transform -> Godot Transform3D string.

    Position: (bx,by,bz) -> (bx, bz, -by) (the glTF axis convention DC already
    uses on export, so the .tscn lines up with the baked .glb).
    Rotation: rot about Blender +Z by t == rot about Godot +Y by t (derived:
    C.Rz.C^-1 = Ry under the same axis change). Scale remaps y<->z with the axes.
    """
    bx, by, bz = (translation or [0.0, 0.0, 0.0])[:3]
    ox, oy, oz = bx, bz, -by
    vals = godot_basis(rot_y_deg, scale) + [ox, oy, oz]
    return "Transform3D(" + ", ".join(_f(v) for v in vals) + ")"


def godot_basis(rot_y_deg, scale):
    """The 3x3 placement basis (9 floats, column-major) for a slot. THE single
    source of truth for module orientation -- the placement verifier reuses it,
    so the scene and its check can never drift apart.

    basis = Ry(t) x Scale_local. The rotation is NOT the slot's raw rot_y; it
    is chosen per-slot by fitting the module to the greybox extent (the ground
    truth) in themed_tscn, with nothing hard-coded. Scale is the slot's
    fit.dims in the MODULE'S OWN frame -- deli_counter emits a wall
    remainder's scale as [length, thickness, height] whatever way the wall
    runs (`_volumes`: "a unit box scaled by LOCAL dims and then turned by
    rot_y lands correctly") -- so it is applied BEFORE the rotation.

    This docstring said the opposite from 0.81.0 to 0.119.0 ("scale is
    world-axis-aligned, applied AFTER the rotation") and the code did what it
    said: Scale_world x Ry(t). Nothing noticed, because every scaled module is
    a `wallEnd` unit cube, whose extents are 1 x 1 x 1 at every rotation, so
    `_fit_rotation` tied at all four angles and answered 0 -- and at 0 the
    two orders agree. On any wall that runs along Y (rot_y 90/270) the
    remainder therefore stood with its LENGTH across the wall: a fin. Measured
    2026-09-12 on cold runs 9001-9012: 237 of 777 wallEnd nodes, every one on
    a turned wall (`int_0_1_seg1` of bank_branch_a03: slot rot_y 90, scale
    [1.875, 0.3, 3.3], placed basis scale-only, 1.875 m along X beside a
    doorway). The walker saw it on 9005 and again on 9012; the pose census
    could not, because it compares the SORTED horizontal extents.
    """
    t = math.radians(rot_y_deg or 0.0)
    c, s = math.cos(t), math.sin(t)
    sc = (scale or [1.0, 1.0, 1.0])
    gsx, gsy, gsz = sc[0], sc[2], sc[1]      # y<->z remap with the axis change
    return [c * gsx, 0.0, -s * gsx,          # transformed X axis (module length)
            0.0, gsy, 0.0,                   # transformed Y axis (up)
            s * gsz, 0.0, c * gsz]           # transformed Z axis (module depth)


def _ref_path(res_root, ref):
    return f"{res_root.rstrip('/')}/{ref}.glb"


def write_tscn(slots, building_id, out_path, res_root="res://"):
    """Write a .tscn instancing each slot's module. Returns the path."""
    # unique module refs -> ext_resource ids (one resource, reused N times)
    ids = {}
    order = []
    for sl in slots:
        ref = sl.get("current_ref")
        if ref and ref not in ids:
            ids[ref] = f"{len(order) + 1}_{ref}"
            order.append(ref)

    out = []
    out.append(f"[gd_scene load_steps={len(order) + 1} format=3]")
    out.append("")
    for ref in order:
        out.append(f'[ext_resource type="PackedScene" '
                   f'path="{_ref_path(res_root, ref)}" id="{ids[ref]}"]')
    out.append("")
    out.append(f'[node name="{building_id or "Building"}" type="Node3D"]')
    out.append("")
    for sl in slots:
        ref = sl.get("current_ref")
        if not ref:
            continue
        name = sl.get("slot_id") or ref
        tf = sl.get("transform", {})
        xform = _godot_transform(tf.get("translation"), tf.get("rot_y"),
                                 tf.get("scale"))
        out.append(f'[node name="{name}" parent="." '
                   f'instance=ExtResource("{ids[ref]}")]')
        out.append(f"transform = {xform}")
        out.append("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return out_path


def tscn_from_manifest(manifest_path, out_path, res_root="res://"):
    """Build a .tscn from a written <name>.slots.json (no Blender needed)."""
    with open(manifest_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return write_tscn(data.get("slots", []), data.get("building_id"),
                      out_path, res_root)
