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

    THE NINE NUMBERS ARE THE MATRIX'S ROWS, not its axes. Godot's text
    format writes `Transform3D(` + basis.rows[0], rows[1], rows[2], origin
    `)`; an axis (column) is read down the three triplets. Read as rows, this
    list is M = Ry(-t) x Scale_local: the slot's scale in the MODULE'S OWN
    frame -- deli_counter emits a wall remainder's scale as [length,
    thickness, height] whatever way the wall runs (`_volumes`: "a unit box
    scaled by LOCAL dims and then turned by rot_y") -- applied BEFORE the
    turn. The angle's sign is the convention every opening module in every
    package has been placed with; do not change it.

    The rotation is not the slot's raw rot_y; it is chosen per-slot by fitting
    the module to the greybox extent (the ground truth) in themed_tscn.

    HISTORY, KEPT. From 0.81.0 to 0.119.0 this docstring called the triplets
    "transformed axes" and the product "Scale_world x Ry(t), scale applied
    after the rotation" -- a description of the transpose of what the engine
    builds from these numbers. The numbers were right; the words were wrong,
    and nothing could tell, because the only scaled module is a unit cube and
    `_fit_rotation` fitted it unscaled, tied at all four angles and answered
    0 -- and a scale-only basis reads the same either way. 0.120.0 believed
    the words, "corrected" the code to Ry(t) x S in column terms, and cold
    run 9013 shipped the remainders across their walls in the other
    direction (`module_pose_census`, off the engine: 6 across on
    bank_tower_a01, where the gate -- computing extents from the same
    columns -- said 165 of 165 sat). 0.120.1 restores the numbers, says what
    they are, and sums extents by rows where the placed footprint is
    computed. The fit given the slot's scale is the fix that stands.
    """
    t = math.radians(rot_y_deg or 0.0)
    c, s = math.cos(t), math.sin(t)
    sc = (scale or [1.0, 1.0, 1.0])
    gsx, gsy, gsz = sc[0], sc[2], sc[1]      # y<->z remap with the axis change
    return [c * gsx, 0.0, -s * gsz,          # row 0: world X from (local X, Y, Z)
            0.0, gsy, 0.0,                   # row 1: world Y (up)
            s * gsx, 0.0, c * gsz]           # row 2: world Z


def placed_extent(basis, ext):
    """World-axis extents of a box of module-local extents `ext` placed by
    `basis` (the nine numbers as written to the scene, i.e. ROWS): the extent
    along world axis i is the row-i sum of |M[i][j]| * ext[j]. Summing the
    triplets as if they were columns gives the transpose's answer, which for
    a turned, scaled unit cube is the footprint swapped -- the gate agreed
    with a wrong scene on cold run 9013 exactly that way."""
    return [abs(basis[3 * i]) * ext[0] + abs(basis[3 * i + 1]) * ext[1]
            + abs(basis[3 * i + 2]) * ext[2] for i in range(3)]


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
