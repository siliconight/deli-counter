"""themed_tscn.py -- resolve a Deli Counter slots.json against a themed Zoo kit
and emit a walkable Godot .tscn that instances the THEMED modules at each slot.

This is the art-pass counterpart to tscn_export.py's greybox serializer. It
applies Deli Counter's naming law (the same law zoo/kit.py builds to), so every
slot resolves to the exact `<type>_<theme>_<style>[_w<cm>][_state].glb` stem the
Zoo kit produced:

  - wall remainder (size_mod 'end') -> ONE unit `wallEnd_<theme>_<style>` module,
    SCALED per-slot by the slot transform (the single exception to exact-fit).
  - everything else -> exact-fit `<type>_<theme>_<style>_w<cm>` (never stretched).
  - interactive slots instance their DEFAULT state's stem; non-default states are
    swapped in by game code at runtime.

Because the Zoo modules carry their own collision, the resulting scene is
walkable directly -- no greybox overlay needed. A themed module that is missing
from the library falls back to the slot's greybox `current_ref` so the art pass
stays progressive (you can walk a half-themed building).

Transform math (Blender Z-up -> Godot Y-up, incl. rot_y + scale) is REUSED from
tscn_export._godot_transform so the themed scene lines up with the baked GLB.

CLI:
    python themed_tscn.py <slots.json> --theme street --style 1 \
        --library art/zoo --res-root res://art/zoo --out build/<name>_street.tscn
"""
from __future__ import annotations

import json
import os

from tscn_export import _godot_transform, _ref_path


# --- Deli Counter's naming law (mirrors zoo/kit.py; DC owns the convention) ---
def slot_typename(role: str, size_mod: str) -> str:
    if role == "wall" and size_mod == "end":
        return "wallEnd"
    return role


def module_stem(typ: str, theme: str, style: int,
                width_cm: int = None, state: str = None) -> str:
    base = f"{typ}_{theme}_{style:02d}"
    if width_cm is not None:
        base += f"_w{int(round(width_cm))}"
    if state:
        base += f"_{state}"
    return base


def _default_stem_state(slot: dict) -> str | None:
    """The stem-state suffix for the slot's DEFAULT instance (interactive slots
    show their default state at rest; other states are game-swapped)."""
    inter = slot.get("interactive")
    if not inter:
        return None
    # default state carries the base stem (no suffix), same as kit.py
    return None


def resolve_themed_stem(slot: dict, theme: str, style: int):
    """Return (stem, is_scaled_unit) for a slot, or (None, False) if unroleable."""
    role = slot.get("role")
    fit = slot.get("fit", {})
    dims = fit.get("dims")
    if role is None or not dims or len(dims) < 3:
        return None, False
    typ = slot_typename(role, slot.get("size_mod"))
    exact = typ != "wallEnd"
    width_cm = int(round(dims[0] * 100)) if exact else None
    stem = module_stem(typ, theme, style, width_cm, _default_stem_state(slot))
    return stem, (not exact)


def _themed_available(library_dir: str, stem: str) -> bool:
    if not library_dir:
        return True  # no library given -> trust the plan (progressive art)
    return os.path.exists(os.path.join(library_dir, stem + ".glb"))


def themed_slot_ids(slots, theme, style, library_dir):
    """The slot_ids that resolve to an AVAILABLE themed module (not a greybox
    fallback). These are exactly the slots whose greybox visual should be
    stripped from the base -- the fallback slots keep their greybox geometry in
    the shell so the package stays closed (no dangling ref to an unbundled
    greybox module) and the building stays fully visible (progressive art)."""
    out = []
    for sl in slots:
        stem, _ = resolve_themed_stem(sl, theme, style)
        if stem and _themed_available(library_dir, stem) and sl.get("slot_id"):
            out.append(sl.get("slot_id"))
    return out


# --- fit-to-ground-truth placement ------------------------------------------
# The greybox is the shell's truth (collision + nav). We orient each module so
# its footprint matches the greybox slot's, instead of trusting a dims
# convention -- so walls (world-oriented by deli) fall out to 0 deg and
# canonical openings to 90/270, with nothing hard-coded.
_BBOX_CACHE = {}


def _glb_extent(glb_path):
    """Overall visual (non-collision) bbox extent of a GLB, cached."""
    if glb_path in _BBOX_CACHE:
        return _BBOX_CACHE[glb_path]
    res = None
    try:
        from pygltflib import GLTF2
        g = GLTF2().load(glb_path)
        lo = [1e18] * 3
        hi = [-1e18] * 3
        ok = False
        for n in g.nodes:
            if n.mesh is None:
                continue
            nm = (n.name or "").lower()
            if "colonly" in nm or "convcolonly" in nm:
                continue
            t = n.translation or [0.0, 0.0, 0.0]
            for p in g.meshes[n.mesh].primitives:
                a = g.accessors[p.attributes.POSITION]
                if a.min and a.max:
                    ok = True
                    for i in range(3):
                        lo[i] = min(lo[i], a.min[i] + t[i])
                        hi[i] = max(hi[i], a.max[i] + t[i])
        res = [hi[i] - lo[i] for i in range(3)] if ok else None
    except Exception:
        res = None
    _BBOX_CACHE[glb_path] = res
    return res


def greybox_slot_extents(greybox_glb):
    """{node_name: (lo, hi)} for visual greybox nodes (per-slot ground truth)."""
    from pygltflib import GLTF2
    g = GLTF2().load(greybox_glb)
    per = {}
    for n in g.nodes:
        if n.mesh is None:
            continue
        nm = n.name or ""
        if "colonly" in nm.lower() or "convcolonly" in nm.lower():
            continue
        lo = [1e18] * 3
        hi = [-1e18] * 3
        ok = False
        for p in g.meshes[n.mesh].primitives:
            a = g.accessors[p.attributes.POSITION]
            if a.min and a.max:
                ok = True
                for i in range(3):
                    lo[i] = min(lo[i], a.min[i])
                    hi[i] = max(hi[i], a.max[i])
        if ok:
            # add node translation so a multi-part opening (lintel/sill/pane,
            # each positioned by node translation) measures its true extent,
            # not a collapsed local-space union. See portable_building
            # ._glb_visual_bboxes for the full rationale.
            t = n.translation or [0.0, 0.0, 0.0]
            per[nm] = ([lo[i] + t[i] for i in range(3)],
                       [hi[i] + t[i] for i in range(3)])
    return per


def _slot_extent(per, slot_id):
    lo = [1e18] * 3
    hi = [-1e18] * 3
    found = False
    for nm, (l, h) in per.items():
        # precise: the slot's node or a named sub-part (<slot_id>_lintel/...),
        # never a numeric sibling (seg1 must not swallow seg10). See
        # portable_building._slot_greybox_extent for the rationale.
        if slot_id and (nm == slot_id or nm.startswith(slot_id + "_")):
            found = True
            for i in range(3):
                lo[i] = min(lo[i], l[i])
                hi[i] = max(hi[i], h[i])
    return [hi[i] - lo[i] for i in range(3)] if found else None


def _fit_rotation(module_ext, gb_ext, fallback=0):
    """Up-axis rotation (0/90/180/270) whose placed HORIZONTAL footprint best
    matches the greybox slot. Height (Y) is not scored -- some opening modules
    differ in height from the greybox opening frame."""
    from tscn_export import godot_basis
    best, best_err = fallback, 1e18
    for rot in (0, 90, 180, 270):
        b = godot_basis(rot, [1.0, 1.0, 1.0])
        pl = [abs(b[i]) * module_ext[0] + abs(b[3 + i]) * module_ext[1]
              + abs(b[6 + i]) * module_ext[2] for i in range(3)]
        err = abs(pl[0] - gb_ext[0]) + abs(pl[2] - gb_ext[2])
        if err < best_err - 1e-9:
            best_err, best = err, rot
    return best


def write_themed_tscn(slots, building_id, out_path, *, theme, style=1,
                      library_dir="", res_root="res://art/zoo", base_res=None,
                      greybox_glb=None):
    """Write a walkable themed .tscn. Returns (path, stats).

    base_res: optional res:// path to the greybox FLOORS+COLLISION base GLB
    (stripped of swappable-slot visuals). Instanced at identity as the
    functional shell -- 'collision and nav live on the greybox' -- so the
    themed modules ride on top and the building has floors to stand on.

    greybox_glb: optional path to the baked greybox .glb (the shell's ground
    truth). When given, each module is oriented by FITTING its footprint to the
    greybox slot's extent instead of trusting the slot's raw rot_y -- walls
    (world-oriented by deli) fit at 0 deg, canonical openings at 90/270, with
    nothing hard-coded. The art conforms to the collision, by construction.
    """
    themed = 0
    fell_back = 0
    refit = 0
    skipped_fallback = 0
    gb_per = None
    if greybox_glb and library_dir:
        try:
            gb_per = greybox_slot_extents(greybox_glb)
        except Exception:
            gb_per = None
    resolved_refs = {}   # slot_id -> ref used (None -> not emitted)
    # First pass: pick a ref per slot (themed stem, else greybox current_ref).
    # When a base shell is present, a greybox-fallback slot is NOT re-emitted as
    # an external ref -- its geometry already rides in the base (the base strip
    # is told to keep exactly these slots), so the package stays closed.
    for sl in slots:
        stem, _scaled = resolve_themed_stem(sl, theme, style)
        if stem and _themed_available(library_dir, stem):
            resolved_refs[id(sl)] = stem
            themed += 1
        elif base_res:
            resolved_refs[id(sl)] = None       # kept in the greybox base
            skipped_fallback += 1
        else:
            resolved_refs[id(sl)] = sl.get("current_ref")  # greybox fallback
            if sl.get("current_ref"):
                fell_back += 1

    # ext_resource ids: one PackedScene per distinct ref, reused N times.
    ids, order = {}, []
    for sl in slots:
        ref = resolved_refs[id(sl)]
        if ref and ref not in ids:
            ids[ref] = f"{len(order) + 1}_{ref}"
            order.append(ref)

    steps = len(order) + 1 + (1 if base_res else 0)
    out = [f"[gd_scene load_steps={steps} format=3]", ""]
    if base_res:
        out.append(f'[ext_resource type="PackedScene" path="{base_res}" '
                   f'id="0_greybox_base"]')
    for ref in order:
        out.append(f'[ext_resource type="PackedScene" '
                   f'path="{_ref_path(res_root, ref)}" id="{ids[ref]}"]')
    out += ["", f'[node name="{building_id or "Building"}" type="Node3D"]', ""]
    if base_res:
        # Floors + all collision, at identity (the baked GLB and the themed
        # slot transforms share DC's export axis convention, so they line up).
        out.append('[node name="GreyboxBase" parent="." '
                   'instance=ExtResource("0_greybox_base")]')
        out.append("")
    for sl in slots:
        ref = resolved_refs[id(sl)]
        if not ref:
            continue
        name = sl.get("slot_id") or ref
        tf = sl.get("transform", {})
        rot = tf.get("rot_y")
        if gb_per is not None:
            ge = _slot_extent(gb_per, sl.get("slot_id", ""))
            me = _glb_extent(os.path.join(library_dir, ref + ".glb"))
            if ge and me:
                fit = _fit_rotation(me, ge, fallback=(tf.get("rot_y") or 0))
                if fit != (tf.get("rot_y") or 0):
                    refit += 1
                rot = fit
        xform = _godot_transform(tf.get("translation"), rot, tf.get("scale"))
        out.append(f'[node name="{name}" parent="." '
                   f'instance=ExtResource("{ids[ref]}")]')
        out.append(f"transform = {xform}")
        out.append("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return out_path, {"themed": themed, "greybox_fallback": fell_back,
                      "distinct_modules": len(order), "slots": len(slots),
                      "greybox_base": bool(base_res), "refit": refit,
                      "skipped_fallback_kept_in_base": skipped_fallback,
                      "fit_to_greybox": gb_per is not None}


def themed_from_manifest(manifest_path, out_path, *, theme, style=1,
                         library_dir="", res_root="res://art/zoo", base_res=None,
                         greybox_glb=None):
    with open(manifest_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return write_themed_tscn(data.get("slots", []), data.get("building_id"),
                             out_path, theme=theme, style=style,
                             library_dir=library_dir, res_root=res_root,
                             base_res=base_res, greybox_glb=greybox_glb)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Emit a walkable themed .tscn from a "
                                             "DC slots.json + a themed Zoo kit.")
    ap.add_argument("slots", help="path to <name>.slots.json")
    ap.add_argument("--theme", required=True)
    ap.add_argument("--style", type=int, default=1)
    ap.add_argument("--library", default="",
                    help="local dir of themed module .glb files (for the "
                         "themed/greybox fallback decision); optional")
    ap.add_argument("--res-root", default="res://art/zoo",
                    help="res:// path where the modules live in the Godot project")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    path, stats = themed_from_manifest(a.slots, a.out, theme=a.theme,
                                       style=a.style, library_dir=a.library,
                                       res_root=a.res_root)
    print(f"[themed_tscn] {path}")
    print(f"[themed_tscn] {stats['themed']} themed, "
          f"{stats['greybox_fallback']} greybox fallback, "
          f"{stats['distinct_modules']} distinct modules, "
          f"{stats['slots']} slots")
