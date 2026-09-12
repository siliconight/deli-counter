"""themed_tscn.py -- resolve a Deli Counter slots.json against a themed Zoo kit
and emit a walkable Godot .tscn that instances the THEMED modules at each slot.

This is the art-pass counterpart to tscn_export.py's greybox serializer. It
applies Deli Counter's naming law (the same law zoo/kit.py builds to), so every
slot resolves to the exact `<type>_<theme>_<style>[_w<cm>][_state].glb` stem the
Zoo kit produced:

  - wall remainder (size_mod 'end') -> ONE unit `wallEnd_<theme>_<style>` module,
    SCALED per-slot by the slot transform (the single exception to exact-fit).
  - everything else -> exact-fit `<type>_<theme>_<style>_w<cm>` (never stretched).
  - interactive slots instance their DEFAULT state's stem VISIBLE, and every
    non-default state whose geometry differs (per `interactive.state_geometry`)
    as a HIDDEN sibling at the same transform (`<slot_id>_<state>`,
    `visible = false`), so the shipped scene contains everything the game's
    state machine swaps between -- it flips visibility, it never loads art.
    Both nodes carry `metadata/interactive_id` so netcode finds them without
    parsing names (the id correlates with gameplay.json per INTERACTIVES.md).

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
# Roles whose modules span the full story height (they cover the slab edge)
# and therefore carry a top cap in the story plane. See the sink note in
# write_themed_tscn.
_SLAB_CAP_SINK_ROLES = {"wall", "doorway", "window", "breach"}
SLAB_CAP_SINK = 0.004   # metres; > z-fight gate tolerance, < perception


def slot_typename(role: str, size_mod: str) -> str:
    if role == "wall" and size_mod == "end":
        return "wallEnd"
    return role


#: Roles built as a horizontal PLATE, whose footprint varies on BOTH axes.
#: Mirror of ``zoo_keeper.core.kit.PLATE_ROLES``.
PLATE_ROLES = ("floor", "ceiling", "roof")

#: Roles built as a free-standing VOLUME, free on ALL THREE axes.
#: Mirror of ``zoo_keeper.core.kit.VOLUME_ROLES``.
VOLUME_ROLES = ("prop",)

#: The corner: its width and depth are the wall thickness and its height the
#: storey, so width alone names fourteen solids in this library (950 posts
#: across 17 (thickness, height) pairs, 2026-09-11). Keyed on all three.
#: Mirror of ``zoo_keeper.core.kit.CORNER_ROLES`` (roadmap 64).
CORNER_ROLES = ("wallCorner",)

#: Roles whose geometry is a hole in a standing slab, cut to the slot's own
#: ``fit.openings``. Mirror of ``zoo_keeper.core.kit.OPENING_ROLES``.
OPENING_ROLES = ("doorway", "window", "breach", "vault_door")


def opening_tag(openings) -> str | None:
    """A short, stable tag for a slot's apertures, or None when it has none.

    Mirror of ``zoo_keeper.core.kit.opening_tag``. ``_w<cm>`` names a doorway
    completely only while every doorway of that width has the same aperture,
    and nothing enforces that: two 1.4 m doorway slots, one with a 2.2 m door
    and one with a 2.4 m door, both resolved to ``doorway_rockay_01_w140`` and
    one got the other's hole. Same collision ``_d`` fixed for plate depth and
    ``_v`` fixed for stairwells.

    ORDER IS KEPT: only the first opening is cut, so a different order is a
    different module. (A plate's voids are a set and sort; these do not.)
    """
    import hashlib
    if not openings:
        return None
    parts = ["%s|%.4f,%.4f,%.4f" % (str(o.get("kind") or ""),
                                    float(o.get("width") or 0.0),
                                    float(o.get("height") or 0.0),
                                    float(o.get("sill") or 0.0))
             for o in openings]
    return hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:6]


def void_tag(voids) -> str | None:
    """A short, stable tag for a plate's hole set, or None when it has none.

    Two rooms of identical footprint with stairwells in DIFFERENT places are
    different geometry, and the module key already knows that. The filename did
    not: `security_office` and `count_room` are both 22x16, planned as two
    modules, and both were named `floor_rockay_01_w2200_d1600`. One file wins
    and one room gets the other's holes -- the same class of collision the
    depth suffix fixed, one level down.

    Formatted, not hashed with repr: both repos compute this and float repr is
    not a contract. Order-independent, so the same holes listed differently are
    the same tag.
    """
    import hashlib
    if not voids:
        return None
    parts = sorted("%.4f,%.4f,%.4f,%.4f" % (float(v["x0"]), float(v["y0"]),
                                            float(v["x1"]), float(v["y1"]))
                   for v in voids)
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:6]


def module_stem(typ: str, theme: str, style: int,
                width_cm: int = None, state: str = None,
                depth_cm: int = None, voids_tag: str = None,
                openings_tag: str = None, height_cm: int = None,
                species: str = None) -> str:
    """``<type>[_<species>]_<theme>_<style:02d>[_w<cm>][_d<cm>][_h<cm>][_v<hash>][_o<hash>][_<state>]``.

    THE MIRROR OF ``zoo_keeper.core.kit.module_stem``, and the two must change
    together. Neither side parses a stem; both CONSTRUCT it from the same slot,
    so they agree only by being kept identical.

    ``depth_cm`` is for plates and volumes; ``height_cm`` only for volumes. A
    wall varies on one axis and ``_w<cm>`` identifies it completely, so every
    existing wall/doorway/window filename is untouched. A floor varies on both:
    a 44x24 room and a 44x16 room both resolved to ``floor_rockay_01_w4400``,
    and the shorter room was handed a slab eight metres too deep. A PROP varies
    on all three, and inherited the wall's argument by mistake: `cr_gas` put a
    0.9x10.0x1.8 counter and a 0.9x0.9x1.0 cube on one `prop_delco_04_w90`.
    """
    # A VOLUME'S SPECIES IS IN THE NAME (roadmap 44): `prop_desk_...` is a
    # desk built to the slot, `prop_...` the box. Two different geometries
    # of one size must not share a filename, and the composer must be
    # able to ask for the desk and fall back to the box (resolve_slot_ref).
    base = (f"{typ}_{species}_{theme}_{style:02d}"
            if species and species != typ else f"{typ}_{theme}_{style:02d}")
    if width_cm is not None:
        base += f"_w{int(round(width_cm))}"
    if depth_cm is not None:
        base += f"_d{int(round(depth_cm))}"
    if height_cm is not None:
        base += f"_h{int(round(height_cm))}"
    if voids_tag:
        base += f"_v{voids_tag}"
    if openings_tag:
        base += f"_o{openings_tag}"
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


def resolve_themed_stem(slot: dict, theme: str, style: int, state: str = None):
    """Return (stem, is_scaled_unit) for a slot, or (None, False) if unroleable.

    The slot's OWN style (material-driven, skin_style.py) wins over the
    compose-level style, which acts as the fallback for slots that carry
    none -- so skin variety is decided where the material is known (DC slot
    emission), not flattened by one global flag.

    state: an interactive stem-state suffix (e.g. 'broken'); None resolves the
    slot's default/base stem exactly as before."""
    role = slot.get("role")
    fit = slot.get("fit", {})
    dims = fit.get("dims")
    if role is None or not dims or len(dims) < 3:
        return None, False
    typ = slot_typename(role, slot.get("size_mod"))
    exact = typ != "wallEnd"
    width_cm = int(round(dims[0] * 100)) if exact else None
    depth_cm = (int(round(dims[1] * 100))
                if exact and typ in PLATE_ROLES + VOLUME_ROLES + CORNER_ROLES
                else None)
    height_cm = (int(round(dims[2] * 100))
                 if exact and typ in VOLUME_ROLES + CORNER_ROLES else None)
    vtag = void_tag(fit.get("voids")) if typ in PLATE_ROLES else None
    otag = opening_tag(fit.get("openings")) if typ in OPENING_ROLES else None
    eff_style = int(slot.get("style") or style or 1)
    # A volume's species hint (roadmap 44) names the module Zoo builds when
    # the species fits the slot; `species=None` on the slot, or a slot from
    # an older manifest, resolves the plain box exactly as before.
    species = slot.get("species") if typ in VOLUME_ROLES else None
    stem = module_stem(typ, theme, eff_style, width_cm,
                       state if state else _default_stem_state(slot),
                       depth_cm, vtag, otag, height_cm, species=species)
    return stem, (not exact)


def _themed_available(library_dir: str, stem: str) -> bool:
    if not library_dir:
        return True  # no library given -> trust the plan (progressive art)
    return os.path.exists(os.path.join(library_dir, stem + ".glb"))


def resolve_slot_ref(slot, theme, style, library_dir):
    """THE resolution every consumer must share: the styled module if built,
    else the style-01 module of the same type/width (partial kits degrade to
    fewer skins, never to greybox), else None (true greybox fallback).
    Returns (stem_or_None, is_scaled_unit, style_fell_back).

    The composer (write_themed_tscn), the base-strip (themed_slot_ids) and
    the placement gate MUST all resolve through here -- when they disagreed,
    fallback modules were placed over unstripped greybox walls and the whole
    building z-fought (caught by the z-fight gate, 0.88.0)."""
    # A hinted volume asks for its species module first and the plain box
    # second (roadmap 44): Zoo builds the box when the species does not fit
    # the slot, and the composer must land on whichever one exists rather
    # than on greybox. The style-01 degrade applies to each in turn.
    candidates = [slot]
    if slot.get("species") and slot.get("role") in VOLUME_ROLES:
        candidates.append(dict(slot, species=None))
    for cand in candidates:
        stem, scaled = resolve_themed_stem(cand, theme, style)
        if stem and _themed_available(library_dir, stem):
            return stem, scaled, False
    for cand in candidates:
        stem, _scaled = resolve_themed_stem(cand, theme, style)
        if stem and int(cand.get("style") or 1) != 1:
            stem01, scaled01 = resolve_themed_stem(dict(cand, style=1), theme, 1)
            if stem01 and _themed_available(library_dir, stem01):
                return stem01, scaled01, True
    return None, False, False


def state_variant_stems(slot, theme, style, library_dir):
    """[(state, stem, available)] for every NON-DEFAULT interactive state
    whose geometry differs from the default's -- THE MIRROR of
    ``zoo_keeper.core.kit.slot_variants``, which decides what the kit builds;
    this decides what the composer instances. The two must agree the same way
    module_stem's mirror does: by construction from the same slot.

    Which species backs a state comes from ``interactive.state_geometry``
    (state -> species; unmapped -> the slot's own type). A state resolving to
    the SAME species as the default is identical art today (a door's open
    state -- the swing is game-side presentation) and gets NO variant node,
    exactly as the kit defers building it. The variant follows the style the
    BASE actually resolved to, including its style-01 fallback, so a building
    never mixes skins across states of one fixture. A greybox-fallback slot
    gets no variants at all -- greybox has no state art.

    available=False means the state differs but its module is not in the
    library (progressive art: composer skips it, stats report it)."""
    inter = slot.get("interactive")
    if not inter:
        return []
    states = inter.get("states") or []
    default = inter.get("default") or (states[0] if states else None)
    geometry = inter.get("state_geometry") or {}
    typ = slot_typename(slot.get("role"), slot.get("size_mod"))
    default_species = geometry.get(default, typ)

    base_stem, _scaled, base_fell = resolve_slot_ref(slot, theme, style,
                                                     library_dir)
    if not base_stem:
        return []
    eff_slot = dict(slot, style=1) if base_fell else slot
    eff_style = 1 if base_fell else style

    out = []
    for st in states:
        if st == default:
            continue
        if geometry.get(st, typ) == default_species:
            continue  # identical art today; the kit deferred it too
        stem, _ = resolve_themed_stem(eff_slot, theme, eff_style, state=st)
        if stem:
            out.append((st, stem, _themed_available(library_dir, stem)))
    return out


def themed_slot_ids(slots, theme, style, library_dir):
    """The slot_ids that resolve to an AVAILABLE themed module (not a greybox
    fallback). These are exactly the slots whose greybox visual should be
    stripped from the base -- the fallback slots keep their greybox geometry in
    the shell so the package stays closed (no dangling ref to an unbundled
    greybox module) and the building stays fully visible (progressive art).
    Uses resolve_slot_ref, so a style-01 fallback slot IS themed and IS
    stripped -- the strip can never disagree with the composer."""
    out = []
    for sl in slots:
        stem, _, _ = resolve_slot_ref(sl, theme, style, library_dir)
        if stem and sl.get("slot_id"):
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
    state_refs = {}      # id(slot) -> [(state, stem)] hidden variants to place
    state_variants = 0
    state_missing = 0
    # First pass: pick a ref per slot (themed stem, else greybox current_ref).
    # When a base shell is present, a greybox-fallback slot is NOT re-emitted as
    # an external ref -- its geometry already rides in the base (the base strip
    # is told to keep exactly these slots), so the package stays closed.
    style_fell_back = 0
    for sl in slots:
        stem, _scaled, fell = resolve_slot_ref(sl, theme, style, library_dir)
        if stem:
            resolved_refs[id(sl)] = stem
            themed += 1
            if fell:
                style_fell_back += 1
            variants = state_variant_stems(sl, theme, style, library_dir)
            state_refs[id(sl)] = [(st, vs) for st, vs, ok in variants if ok]
            state_missing += sum(1 for _s, _v, ok in variants if not ok)
            continue
        if base_res:
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
        for _st, vref in state_refs.get(id(sl), []):
            if vref not in ids:
                ids[vref] = f"{len(order) + 1}_{vref}"
                order.append(vref)

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
        tr = tf.get("translation")
        # Wall-family modules are authored to the FULL story height so they
        # cover the slab edge, which puts their up-facing top cap exactly in
        # the story plane -- coplanar with the slab's top face. Grey-on-grey
        # this is invisible; themed-on-grey it z-fights (flickering stripes
        # along wall lines on the floor above). Sink these modules by a few
        # millimetres: imperceptible to the eye, decisive for the depth
        # buffer. Free-standing fixture roles (vault_door, teller_line, ...)
        # never reach the story plane and stay untouched, as does the roof
        # (an exact slab swap).
        if tr and sl.get("role") in _SLAB_CAP_SINK_ROLES:
            tr = [tr[0], tr[1], tr[2] - SLAB_CAP_SINK]
        if gb_per is not None:
            ge = _slot_extent(gb_per, sl.get("slot_id", ""))
            me = _glb_extent(os.path.join(library_dir, ref + ".glb"))
            if ge and me:
                fit = _fit_rotation(me, ge, fallback=(tf.get("rot_y") or 0))
                if fit != (tf.get("rot_y") or 0):
                    refit += 1
                rot = fit
        xform = _godot_transform(tr, rot, tf.get("scale"))
        inter = sl.get("interactive") or {}
        out.append(f'[node name="{name}" parent="." '
                   f'instance=ExtResource("{ids[ref]}")]')
        out.append(f"transform = {xform}")
        # Netcode's handle on the fixture: the stable id from gameplay.json
        # (INTERACTIVES.md). Names are for humans; metadata is the contract.
        if inter.get("id"):
            out.append(f'metadata/interactive_id = "{inter["id"]}"')
            if inter.get("default"):
                out.append(
                    f'metadata/interactive_state = "{inter["default"]}"')
        out.append("")
        # Non-default states whose geometry differs ride along HIDDEN at the
        # same transform. The game's replicated state machine swaps state by
        # flipping visibility (and toggling collision per
        # interactive.collision_per_state) -- it never loads art at runtime,
        # and a late joiner just gets told which sibling is visible.
        for st, vref in state_refs.get(id(sl), []):
            out.append(f'[node name="{name}_{st}" parent="." '
                       f'instance=ExtResource("{ids[vref]}")]')
            out.append(f"transform = {xform}")
            out.append("visible = false")
            if inter.get("id"):
                out.append(f'metadata/interactive_id = "{inter["id"]}"')
            out.append(f'metadata/interactive_state = "{st}"')
            state_variants += 1
            out.append("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return out_path, {"themed": themed, "greybox_fallback": fell_back,
                      "distinct_modules": len(order), "slots": len(slots),
                      "greybox_base": bool(base_res), "refit": refit,
                      "skipped_fallback_kept_in_base": skipped_fallback,
                      "style_fallback_to_01": style_fell_back,
                      "fit_to_greybox": gb_per is not None,
                      "state_variants": state_variants,
                      "state_variants_missing": state_missing}


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
    print(f"[themed_tscn] {stats['state_variants']} hidden state variants "
          f"placed, {stats['state_variants_missing']} missing from library")
