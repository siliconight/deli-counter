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

    basis = Scale_world x Ry(t). The rotation is NOT the slot's raw rot_y; it is
    chosen per-slot by fitting the module to the greybox extent (the ground
    truth) in themed_tscn -- walls (already world-oriented by deli) fit at 0 deg,
    canonical openings at 90/270, with nothing hard-coded. Scale is
    world-axis-aligned (deli's fit-scale gives a wall's final extents), so it is
    applied AFTER the rotation, not in the module's local frame.
    """
    t = math.radians(rot_y_deg or 0.0)
    c, s = math.cos(t), math.sin(t)
    sc = (scale or [1.0, 1.0, 1.0])
    gsx, gsy, gsz = sc[0], sc[2], sc[1]      # y<->z remap with the axis change
    return [c * gsx, 0.0, -s * gsz,          # transformed X axis
            0.0, gsy, 0.0,                   # transformed Y axis (up)
            s * gsx, 0.0, c * gsz]           # transformed Z axis


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
