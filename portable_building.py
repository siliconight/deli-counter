"""portable_building.py -- package one themed, walkable building as a
self-contained Godot 4.x handoff that a stranger drops into their own project
with NONE of our toolchain (no Blender, zoo, deli, pixelcoat, and no editor
addon).

Given a Deli Counter slots.json + gameplay.json and a themed Zoo kit, it emits:

    <pkg>/
      project.godot                 autoload-free, plugin-free, main scene set
      <building>.tscn               the walkable building (themed module
                                    instances w/ collision + markers as PLAIN
                                    Node3D nodes -- no import addon needed)
      <building>_main.tscn          entry scene; instances the building and,
                                    under --lf-portability-check, prints the
                                    marker and quits
      art/zoo/*.glb                 the themed modules (textures embedded)
      HANDOFF.md, portable_resource_manifest.json

Markers (spawns/objectives/etc.) are BAKED as plain Node3D nodes in groups, so
gameplay code in the recipient's project finds them by group with zero deps.

Closure self-check: no absolute paths anywhere, and every ext_resource path
resolves inside the package. That is the same contract level_factory's
portability-test enforces; this makes a single building pass it standalone.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil

import themed_tscn  # sibling module (resolver + transform reuse)


# --- markers: Blender Z-up gameplay pos -> Godot Y-up plain Node3D ------------
def _godot_pos(p):
    bx, by, bz = (list(p) + [0, 0, 0])[:3]
    return bx, bz, -by  # same mapping tscn_export uses for translation


def _ladder_climb_nodes(gameplay: dict):
    """Bake the CLIMB CONTRACT for every ladder into the composed scene
    (docs/LADDER_CLIMB_CONTRACT.md). DC's gameplay export knows each ladder's
    base anchor, climb height, clear width and facing -- but a bare point
    marker is not climbable. This emits, per ladder:

        Ladders/Ladder_<id>   Area3D, groups ["ladder_area3d", "dc_ladder"],
                              positioned at the base anchor, rotated so the
                              node's +Z axis points at the APPROACH side (the
                              face a climber mounts from) -- the community
                              Source-style convention, so third-party climb
                              controllers work against DC packages unmodified.
          CollisionShape3D    BoxShape3D spanning the climbable volume: the
                              full climb height (plus mount headroom) and the
                              ladder's width (plus catch margin), protruding
                              ~0.8 m onto the approach side.
          TopOfLadder         Node3D at the step-off height, for controllers
                              to detect top-mounting/dismounting.
        metadata: climb_height, facing.

    There is NO state here -- unlike a door, a ladder is pure geometry plus
    intent, so the package stays a plain content drop-in; movement lives in
    whatever player controller the host game (or LF's walk preview) runs.

    Returns (sub_resources_text, nodes_text) -- shapes must be spliced in
    BEFORE the first [node] section (tscn parses sequentially)."""
    ladders = [m for m in (gameplay.get("markers") or [])
               if m.get("type") == "ladder"]
    if not ladders:
        return "", ""
    # +Z of the area must point at the approach side. DC's marker `facing` is
    # the direction the rungs face (the approach direction). Row-major basis
    # of a yaw that maps local +Z onto that direction, in Godot Y-up space
    # (spec (x,y,z) -> godot (x, z, -y), so spec N=+y -> godot -z).
    basis = {"S": "1, 0, 0, 0, 1, 0, 0, 0, 1",
             "E": "0, 0, 1, 0, 1, 0, -1, 0, 0",
             "N": "-1, 0, 0, 0, 1, 0, 0, 0, -1",
             "W": "0, 0, -1, 0, 1, 0, 1, 0, 0"}
    subs, nodes = [], []
    nodes.append('[node name="Ladders" type="Node3D" parent="."]')
    nodes.append("")
    for i, m in enumerate(ladders):
        h = float(m.get("climb_height", 3.0))
        w = float(m.get("width", 0.5))
        facing = str(m.get("facing", "S")).upper()
        gx, gy, gz = _godot_pos([m.get("x", 0.0), m.get("y", 0.0),
                                 m.get("z", 0.0)])
        sid = f"LadderClimbBox_{i}"
        # width + catch margin; climb height + mount headroom; 0.8 deep on
        # the approach side (thin areas are glitchy to catch, per the
        # Source-style reference rig).
        subs.append(f'[sub_resource type="BoxShape3D" id="{sid}"]')
        subs.append(f"size = Vector3({round(w + 0.6, 3)}, {round(h + 1.0, 3)}"
                    f", 0.8)")
        subs.append("")
        name = re.sub(r"[^A-Za-z0-9_]", "_",
                      str(m.get("id") or m.get("name") or f"ladder_{i}"))
        b = basis.get(facing, basis["S"])
        nodes.append(f'[node name="Ladder_{name}" type="Area3D" '
                     f'parent="Ladders" groups=["ladder_area3d", "dc_ladder"]]')
        nodes.append(f"transform = Transform3D({b}, {round(gx, 4)}, "
                     f"{round(gy, 4)}, {round(gz, 4)})")
        nodes.append(f"metadata/climb_height = {round(h, 3)}")
        nodes.append(f'metadata/facing = "{facing}"')
        nodes.append("")
        nodes.append(f'[node name="CollisionShape3D" type="CollisionShape3D" '
                     f'parent="Ladders/Ladder_{name}"]')
        # box centre: half the climb height up, protruding onto the approach
        # side (+Z, local) so the volume starts at the ladder face.
        nodes.append(f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, "
                     f"{round(h / 2.0, 4)}, 0.45)")
        nodes.append(f'shape = SubResource("{sid}")')
        nodes.append("")
        nodes.append(f'[node name="TopOfLadder" type="Node3D" '
                     f'parent="Ladders/Ladder_{name}"]')
        nodes.append(f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, "
                     f"{round(h - 0.2, 4)}, 0)")
        nodes.append("")
    return "\n".join(subs), "\n".join(nodes)


def splice_ladder_contract(tscn_path, gameplay):
    """Insert the ladder climb contract into a written scene: sub_resources
    before the first [node] block (tscn parses sequentially), climb nodes
    appended, load_steps bumped to match. No-op when the level has no
    ladders."""
    subs, nodes = _ladder_climb_nodes(gameplay)
    if not nodes:
        return 0
    text = open(tscn_path, encoding="utf-8").read()
    n_res = subs.count("[sub_resource")
    m = re.search(r"\[gd_scene load_steps=(\d+)", text)
    if m:
        text = text.replace(m.group(0),
                            f"[gd_scene load_steps={int(m.group(1)) + n_res}",
                            1)
    first_node = text.find("\n[node ")
    if first_node < 0:
        return 0
    text = (text[:first_node] + "\n" + subs + text[first_node:]
            + "\n" + nodes + "\n")
    open(tscn_path, "w", encoding="utf-8").write(text)
    return n_res


def _marker_nodes(gameplay: dict) -> str:
    """Emit plain Node3D marker nodes grouped by type. Recipient game code does
    get_tree().get_nodes_in_group('attacker_spawn') etc. -- no addon."""
    out = []
    markers = gameplay.get("markers") or []
    if markers:
        out.append('[node name="Markers" type="Node3D" parent="."]')
        out.append("")
    for m in markers:
        name = str(m.get("name") or m.get("type") or "marker")
        typ = str(m.get("type") or "marker")
        x = m.get("x", (m.get("pos") or [0, 0, 0])[0])
        y = m.get("y", (m.get("pos") or [0, 0, 0])[1])
        z = m.get("z", (m.get("pos") or [0, 0, 0])[2])
        gx, gy, gz = _godot_pos([x, y, z])
        safe = re.sub(r"[^A-Za-z0-9_]", "_", name)
        out.append(f'[node name="{safe}" type="Node3D" parent="Markers" '
                   f'groups=["{typ}", "dc_marker"]]')
        out.append(f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, "
                   f"{round(gx,4)}, {round(gy,4)}, {round(gz,4)})")
        out.append(f'metadata/marker_type = "{typ}"')
        out.append("")
    return "\n".join(out)


_PROJECT_GODOT = """; Portable themed building -- autoload-free, no editor plugins.
config_version=5

[application]
config/name="{name} (portable building)"
run/main_scene="res://{main}"

[rendering]
renderer/rendering_method="gl_compatibility"

[debug]
gdscript/warnings/inference_on_variant=1
"""

_MAIN_TSCN = """[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://{building}" id="1_building"]

[sub_resource type="GDScript" id="entry"]
script/source = "extends Node3D
# Portable entry. Self-contained (no addons): instances the building, and under
# the clean-project portability check prints the marker and quits.

func _ready() -> void:
\tadd_child(preload('res://{building}').instantiate())
\tprint('scene instantiated ok')
\tif '--lf-portability-check' in OS.get_cmdline_user_args():
\t\tget_tree().quit()
"

[node name="Main" type="Node3D"]
script = SubResource("entry")

[node name="Building" parent="." instance=ExtResource("1_building")]
"""

# A real absolute path at the START of a resource ref: Windows drive or unix
# root. NOT anchored inside "res://" (whose "s://" once tripped a drive match).
_ABS_START = re.compile(r'^(?:[A-Za-z]:[\\/]|/(?:home|Users|mnt|tmp|var|private|Projects)/)')
_REF = re.compile(r'(?:path=|preload\(|load\()\s*["\']([^"\']+)["\']')


def strip_greybox_base(src_glb, out_glb, slot_ids, drop_nodes=()):
    """ADDITIVE base: keep the whole coherent greybox EXCEPT the swappable-slot
    surfaces that themed modules replace. Every collider stays; floors, canopy,
    pumps, aisles, counters -- all non-slot geometry -- stay greybox-visible. A
    visual is dropped ONLY if its node name carries a themed slot_id (a wall /
    opening that a zoo module is instanced onto), so we don't get double walls.
    This is the baked 'theme swap': add themed art to the slots, keep the
    building deli_counter already made.

    drop_nodes: extra visual node NAMES to drop -- slots whose greybox surface
    is not name-linked to the slot id. The roof slot is the case in point: its
    greybox surface is the top slab ('slab_<n>'), which never carries
    'roof_footprint', so the name test above can't find it and the roof module
    would cohabit the slab's exact volume -- a full-footprint z-fight (the
    flickering-ceiling bug). build_package resolves these geometrically."""
    from pygltflib import GLTF2
    g = GLTF2().load(src_glb)
    # EXACT match, not substring. A slot's id IS its greybox node's name --
    # `_record_wall_slot` stores `slot_id: vname`, openings and volumes do the
    # same -- and `drop_nodes` exists precisely for the slots that are NOT
    # name-linked (the roof/slab case). So substring matching bought nothing
    # and cost this:
    #
    #   slot_id "VAULT"  is a substring of  node "VAULTLEDGE_0"
    #
    # The vault got a themed module, so its id entered this list; the LEDGE has
    # no module (it is a `vault_ledge`, not a volume) and never could. Its
    # visual was dropped by the vault's id while its collider stayed, and the
    # result was a body-blocking box you cannot see. Invisible collision fails
    # dangerously and silently; a missed drop fails as double geometry, which
    # is visible on the first walk. Exact match fails the safe way.
    sids = {s.lower() for s in slot_ids if s}
    dropset = set(drop_nodes or ())
    kept_col = kept_vis = dropped = 0
    for n in g.nodes:
        if n.mesh is None:
            continue
        low = (n.name or "").lower()
        if "colonly" in low or "convcolonly" in low:
            kept_col += 1                       # never touch collision/nav
        elif low in sids or (n.name or "") in dropset:
            n.mesh = None                       # themed module covers this slot
            dropped += 1
        else:
            kept_vis += 1                       # floors, canopy, pumps, props
    g.save(out_glb)
    return {"kept_colliders": kept_col, "kept_greybox_visuals": kept_vis,
            "dropped_slot_visuals": dropped,
            "dropped_covered_nodes": sorted(dropset)}


def roof_covered_nodes(greybox_glb, slots, themed_ids):
    """Visual greybox nodes an exact ROOF SWAP replaces, found geometrically.

    A roof slot's fit box (centre + dims, spec Z-up) equals the top slab it
    dresses; the slab node's name ('slab_<n>') carries no slot id, so the
    name-based strip can't see it. Convert the slot box to glb Y-up
    ((x,y,z) -> (x,z,-y)) and match any visual node whose world AABB equals it
    within 5 cm. Only slots that actually GET a themed module count -- a
    greybox-fallback roof keeps its slab."""
    themed = set(themed_ids or ())
    roofs = [s for s in slots if s.get("role") == "roof"
             and s.get("slot_id") in themed]
    if not roofs:
        return []
    boxes = _glb_visual_bboxes(greybox_glb)
    out = []
    for s in roofs:
        t = (s.get("transform") or {}).get("translation") or [0.0, 0.0, 0.0]
        d = (s.get("fit") or {}).get("dims") or [0.0, 0.0, 0.0]
        c = (t[0], t[2], -t[1])
        dd = (d[0], d[2], d[1])
        for nm, (lo, hi) in boxes.items():
            cc = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
            nd = [hi[i] - lo[i] for i in range(3)]
            if all(abs(cc[i] - c[i]) < 0.05 for i in range(3)) and \
                    all(abs(nd[i] - dd[i]) < 0.05 for i in range(3)):
                out.append(nm)
    return sorted(set(out))


def _glb_visual_bboxes(glb_path):
    """{node_name: (lo, hi)} for visual (non-collision) meshed nodes, in the
    glb's own (world) space.

    A node's POSITION accessor min/max are LOCAL. The greybox positions an
    opening's parts (lintel / sill / pane) by NODE TRANSLATION, with the vertex
    data centred at each part's own origin -- so unioning the raw local boxes
    collapses three vertically-stacked parts into one short box (the old
    height-advisory false positive). We add each node's translation so a
    multi-part slot measures its true extent. Greybox nodes are translation-only
    (the baked-flat export convention); module parts carry translation 0, so
    this is a no-op for them and the horizontal footprint check is unchanged."""
    from pygltflib import GLTF2
    g = GLTF2().load(glb_path)
    out = {}
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
            acc = g.accessors[p.attributes.POSITION]
            if acc.min and acc.max:
                ok = True
                for i in range(3):
                    lo[i] = min(lo[i], acc.min[i])
                    hi[i] = max(hi[i], acc.max[i])
        if ok:
            t = n.translation or [0.0, 0.0, 0.0]
            out[nm] = ([lo[i] + t[i] for i in range(3)],
                       [hi[i] + t[i] for i in range(3)])
    return out


def _overall_extent(bboxes):
    if not bboxes:
        return None
    lo = [1e18] * 3
    hi = [-1e18] * 3
    for (l, h) in bboxes.values():
        for i in range(3):
            lo[i] = min(lo[i], l[i])
            hi[i] = max(hi[i], h[i])
    return [round(hi[i] - lo[i], 3) for i in range(3)]


def _slot_greybox_extent(gb_bboxes, slot_id):
    """Union bbox of greybox nodes carrying the slot_id (an opening's
    lintel/sill/pane sub-parts all share the slot_id)."""
    lo = [1e18] * 3
    hi = [-1e18] * 3
    found = False
    for nm, (l, h) in gb_bboxes.items():
        # PRECISE match: the slot's own node, or a named sub-part
        # (<slot_id>_lintel/_sill/_pane/...). A bare substring test would let
        # 'ext_0_N_seg1' also swallow 'ext_0_N_seg10'..'seg19' -- masked before
        # only because the local-space union collapsed them onto the origin.
        if nm == slot_id or nm.startswith(slot_id + "_"):
            found = True
            for i in range(3):
                lo[i] = min(lo[i], l[i])
                hi[i] = max(hi[i], h[i])
    return [round(hi[i] - lo[i], 3) for i in range(3)] if found else None


def verify_placement(greybox_glb, slots, module_dir, theme, style, tol=0.25):
    """GROUND-TRUTH GATE. The greybox carries the collision + nav; every themed
    module must reproduce its slot's greybox FOOTPRINT, or the visual won't sit
    on the collision. Orientation/resolver-width/scale bugs surface here as a
    horizontal placed_extent != greybox_extent.

    The check uses the SAME fit rotation the scene emits (themed_tscn._fit_rotation
    over tscn_export.godot_basis), so gate and scene can never drift. The gate is
    HORIZONTAL: X/Z footprint is the hard invariant (that is what rides on the
    collision). Height (Y) is checked SEPARATELY, against the slot's AUTHORED
    dims height -- not the greybox drawn extent. The greybox deliberately omits
    an opening's open aperture (a doorway greyboxes only its header lintel), so
    its drawn solid height is not a meaningful height reference; the authored
    dims height is what zoo is contracted to build. A module whose height
    departs from the authored opening height is a real zoo build regression and
    is reported as an advisory (never fails the footprint gate)."""
    import tscn_export as _te
    gb = _glb_visual_bboxes(greybox_glb)
    cache = {}
    checked = matched = 0
    mismatches = []
    height_warnings = []
    for s in slots:
        sid = s.get("slot_id")
        if not sid:
            continue
        # shared resolution (incl. the style-01 fallback) so the gate checks
        # EXACTLY the modules the composer places -- never a subset.
        stem, _scaled, _fell = themed_tscn.resolve_slot_ref(
            s, theme, style, module_dir)
        if not stem:
            continue
        mp = os.path.join(module_dir, stem + ".glb")
        if not os.path.exists(mp):
            continue
        ge = _slot_greybox_extent(gb, sid)
        if ge is None:
            continue
        if stem not in cache:
            cache[stem] = _overall_extent(_glb_visual_bboxes(mp))
        me = cache[stem]
        if me is None:
            continue
        tf = s.get("transform", {})
        rot = themed_tscn._fit_rotation(me, ge, fallback=(tf.get("rot_y") or 0))
        b = _te.godot_basis(rot, tf.get("scale"))
        placed = [round(abs(b[i]) * me[0] + abs(b[3 + i]) * me[1]
                        + abs(b[6 + i]) * me[2], 3) for i in range(3)]
        checked += 1
        horiz_ok = abs(placed[0] - ge[0]) <= tol and abs(placed[2] - ge[2]) <= tol
        if horiz_ok:
            matched += 1
        else:
            mismatches.append({"slot": sid, "stem": stem, "fit_rot": rot,
                               "greybox_extent": ge, "placed_extent": placed})
        # Height vs the AUTHORED opening height (slot dims[2]), which is what
        # zoo builds to -- not the greybox's partial drawn extent. A departure
        # here means zoo did not build the module to the authored height.
        dims = (s.get("fit") or {}).get("dims") or []
        authored_h = round(dims[2], 3) if len(dims) >= 3 else None
        if authored_h is not None and abs(placed[1] - authored_h) > tol:
            height_warnings.append({"slot": sid, "stem": stem,
                                    "authored_h": authored_h,
                                    "module_h": placed[1]})
    return {"checked": checked, "matched": matched,
            "mismatched": len(mismatches), "mismatches": mismatches[:20],
            "height_warnings": height_warnings[:20],
            "height_warning_count": len(height_warnings),
            "ok": not mismatches}


def splice_layer_instance(tscn_path, res_path, node_name):
    """Instance an extra CONTENT LAYER (dressing props, light fixtures) at
    identity in a written scene: ext_resource spliced before the first node
    (tscn parses sequentially), instance node appended, load_steps bumped.
    Layers are authored in the same building space as the greybox, so
    identity placement is exact by construction."""
    text = open(tscn_path, encoding="utf-8").read()
    rid = f"L_{node_name}"
    m = re.search(r"\[gd_scene load_steps=(\d+)", text)
    if m:
        text = text.replace(m.group(0),
                            f"[gd_scene load_steps={int(m.group(1)) + 1}", 1)
    # ext_resources must precede sub_resources AND nodes in a tscn --
    # splice before whichever comes first.
    cand = [i for i in (text.find("\n[sub_resource"),
                        text.find("\n[node ")) if i >= 0]
    if not cand:
        return False
    first_node = min(cand)
    ext = (f'\n[ext_resource type="PackedScene" path="{res_path}" '
           f'id="{rid}"]\n')
    node = (f'\n[node name="{node_name}" parent="." '
            f'instance=ExtResource("{rid}")]\n')
    text = text[:first_node] + ext + text[first_node:] + node
    open(tscn_path, "w", encoding="utf-8").write(text)
    return True


def build_package(slots_path, gameplay_path, module_dir, out_dir, *,
                  theme, style=1, building_id=None, greybox_glb=None,
                  dressing_glb=None, fixtures_glb=None):
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    art = os.path.join(out_dir, "art", "zoo")
    os.makedirs(art, exist_ok=True)

    slots = json.load(open(slots_path, encoding="utf-8"))
    bid = building_id or slots.get("building_id") or "building"

    # 0. greybox floors + collision base (the walkable shell under the art).
    base_res = None
    base_strip = None
    if greybox_glb and os.path.exists(greybox_glb):
        base_name = f"{bid}_base.glb"
        # Strip from the base ONLY the slots that get an available themed module.
        # Greybox-fallback slots keep their geometry in the base (they are not
        # re-emitted as external refs), so the package stays closed and the
        # building stays fully visible even when the kit is partial.
        slot_ids = themed_tscn.themed_slot_ids(
            slots.get("slots", []), theme, style, module_dir)
        covered = roof_covered_nodes(greybox_glb, slots.get("slots", []),
                                     slot_ids)
        base_strip = strip_greybox_base(greybox_glb,
                                        os.path.join(out_dir, base_name),
                                        slot_ids, drop_nodes=covered)
        base_res = f"res://{base_name}"

    # 1. themed building .tscn (res://art/zoo refs), via the validated generator.
    tscn_path = os.path.join(out_dir, f"{bid}.tscn")
    _, stats = themed_tscn.write_themed_tscn(
        slots.get("slots", []), bid, tscn_path,
        theme=theme, style=style, library_dir=module_dir,
        res_root="res://art/zoo", base_res=base_res,
        greybox_glb=(greybox_glb if greybox_glb
                     and os.path.exists(greybox_glb) else None))

    # 2. bake markers as plain nodes appended to the building scene.
    gameplay = {}
    if gameplay_path and os.path.exists(gameplay_path):
        gameplay = json.load(open(gameplay_path, encoding="utf-8"))
    marker_block = _marker_nodes(gameplay)
    if marker_block.strip():
        with open(tscn_path, "a", encoding="utf-8") as fh:
            fh.write("\n" + marker_block + "\n")
    # 2b. ladder climb contract: an Area3D volume + TopOfLadder per ladder,
    # so the package is climbable by any Source-style controller
    # (docs/LADDER_CLIMB_CONTRACT.md).
    ladder_shapes = splice_ladder_contract(tscn_path, gameplay)
    # 2c. content LAYERS the art pipeline builds alongside the kit: the
    # DRESSING pass (props: counters, shelving, signage) and the FIXTURES
    # pass (light fixtures carrying LuxEmit markers -- Lux's runtime spawner
    # turns them into placed lights). Without these the composed building
    # is skinned architecture with empty rooms; with them it is the level.
    layers = {}
    for src, sub, node in ((dressing_glb, "dressing", "Dressing"),
                           (fixtures_glb, "fixtures", "Fixtures")):
        if not (src and os.path.exists(src)):
            continue
        ldir = os.path.join(out_dir, "art", sub)
        os.makedirs(ldir, exist_ok=True)
        fname = os.path.basename(src)
        shutil.copy2(src, os.path.join(ldir, fname))
        if splice_layer_instance(tscn_path, f"res://art/{sub}/{fname}", node):
            layers[sub] = fname

    # 3. bundle the referenced module glbs into art/zoo/.
    refs = set(re.findall(r'path="res://art/zoo/([^"]+)"',
                          open(tscn_path, encoding="utf-8").read()))
    bundled, missing = [], []
    for ref in sorted(refs):
        src = os.path.join(module_dir, ref)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(art, ref))
            bundled.append(ref)
        else:
            missing.append(ref)

    # 4. entry scene + project.godot.
    main_name = f"{bid}_main.tscn"
    open(os.path.join(out_dir, main_name), "w", encoding="utf-8").write(
        _MAIN_TSCN.format(building=f"{bid}.tscn"))
    open(os.path.join(out_dir, "project.godot"), "w", encoding="utf-8").write(
        _PROJECT_GODOT.format(name=bid, main=main_name))
    open(os.path.join(out_dir, "HANDOFF.md"), "w", encoding="utf-8").write(
        f"# {bid} -- portable themed building ({theme})\n\n"
        "Self-contained Godot scene. No Blender / Level Factory / editor addon "
        "required.\n\n"
        f"- Open the folder as a Godot project and run, or instance "
        f"`res://{bid}.tscn` into your own scene.\n"
        "- Walkable: every module carries collision. Markers are plain Node3D "
        "nodes in groups (spawns/objectives/etc.) -- find them with "
        "`get_tree().get_nodes_in_group(<type>)`.\n"
        "- Modules live in `res://art/zoo/`; textures are embedded in the GLBs.\n")

    # 5. closure self-check (the portability contract, statically) + instancing
    # summary (the VRAM story: distinct GLBs = distinct Godot Mesh resources;
    # each extra slot is one MeshInstance3D sharing that mesh -- see the DC
    # "Instancing & memory" note. A baked monolith would lose all of this).
    report = _closure_check(out_dir)
    tscn_text = open(tscn_path, encoding="utf-8").read()
    per_module = {}
    for rid in re.findall(r'instance=ExtResource\("(\d+)_([^"]+)"\)', tscn_text):
        per_module[rid[1]] = per_module.get(rid[1], 0) + 1
    total_inst = sum(per_module.values())
    instancing = {
        "distinct_meshes": len(per_module),
        "module_instances": total_inst,
        "reuse_ratio": round(total_inst / max(1, len(per_module)), 1),
        "per_module": dict(sorted(per_module.items(), key=lambda kv: -kv[1])),
        "note": "distinct_meshes Mesh resources shared across module_instances "
                "MeshInstance3D; one vertex buffer + texture set per mesh in VRAM.",
    }
    # GROUND-TRUTH GATE: every themed module must sit on the greybox collision.
    placement = None
    if greybox_glb and os.path.exists(greybox_glb):
        placement = verify_placement(greybox_glb, slots.get("slots", []),
                                     module_dir, theme, style)

    # Z-FIGHT GATE: no two opaque surfaces in the composed result may share a
    # plane facing the same way (coplanar overlap flickers as the camera
    # moves). This is the check that catches a roof module cohabiting the slab
    # or a wall cap in the story plane BEFORE the package ships.
    zfight = None
    try:
        import zfight_gate
        zfight = zfight_gate.check_package(out_dir, scene_name=f"{bid}.tscn")
    except Exception as ex:  # gate must report, never crash the compose
        zfight = {"ok": False, "error": f"gate failed to run: {ex}"}

    # CIRCULATION GATE: props must keep ladders mountable, doorways passable
    # and stair footprints clear (circulation.py -- the volumes are derived
    # from the same slots+gameplay this package was composed from).
    #
    # TWO SOURCES OF PROPS, and only one of them used to be checked. The
    # dressing arm below is conditional on a dressing layer, which is correct
    # for Patina's covers -- but DC places its OWN props into the same space
    # with no dressing involved, and they were never tested. Measured on
    # art_probe_001 seed 5017: VAULT (5.0 x 3.0 x 5.0 m) sat 1.6 m inside
    # stair_1's reserved column, across 15 consecutive treads, while this
    # manifest reported circulation_check: null and DC's own check suite
    # called every variant "physically clean". The rule already forbade it;
    # nothing had ever handed it the greybox.
    circ = None
    if base_strip:
        try:
            import circulation
            circ = circulation.check_shell(
                os.path.join(out_dir, base_strip if isinstance(base_strip, str)
                             else f"{bid}_base.glb"), slots, gameplay)
            circ["source"] = "shell"
        except Exception as ex:  # gate must report, never crash the compose
            circ = {"ok": False, "source": "shell",
                    "error": f"gate failed to run: {ex}"}

    circ_dressing = None
    if layers.get("dressing"):
        try:
            import circulation
            circ_dressing = circulation.check_dressing(
                os.path.join(out_dir, "art", "dressing", layers["dressing"]),
                slots, gameplay)
            circ_dressing["source"] = "dressing"
        except Exception as ex:  # gate must report, never crash the compose
            circ_dressing = {"ok": False, "source": "dressing",
                             "error": f"gate failed to run: {ex}"}

    # One key, both arms, and a combined verdict -- a consumer asking "is
    # circulation clear" must not have to know which pass placed the prop.
    if circ is None and circ_dressing is not None:
        circ = circ_dressing
    elif circ is not None and circ_dressing is not None:
        circ = {"ok": bool(circ.get("ok")) and bool(circ_dressing.get("ok")),
                "shell": circ, "dressing": circ_dressing}

    manifest = {
        "schema": "portable_building.v0.1", "building_id": bid, "theme": theme,
        "themed_modules": stats["themed"], "greybox_fallback": stats["greybox_fallback"],
        "style_fallback_to_01": stats.get("style_fallback_to_01", 0),
        "bundled_modules": bundled, "missing_modules": missing,
        "markers_baked": len(gameplay.get("markers") or []),
        "ladder_climb_volumes": ladder_shapes,
        "content_layers": layers,
        "greybox_base": base_strip,
        "walkable": bool(base_strip),   # floors present -> something to stand on
        "placement_check": placement,   # visual-vs-collision agreement
        "zfight_check": zfight,         # coplanar-surface (flicker) gate
        "circulation_check": circ,      # props-vs-ladders/doorways/stairs gate
        "instancing": instancing,
        "closure": report,
    }
    open(os.path.join(out_dir, "portable_resource_manifest.json"), "w",
         encoding="utf-8").write(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def _closure_check(pkg_dir) -> dict:
    """Every resource ref is res://-relative and resolves in-package; no ref is
    an absolute filesystem path. (res:// and user:// are engine protocols, not
    absolute paths.)"""
    abs_hits, dangling = [], []
    for root, _dirs, files in os.walk(pkg_dir):
        for f in files:
            if not f.endswith((".tscn", ".tres", ".gd", ".godot")):
                continue
            text = open(os.path.join(root, f), encoding="utf-8",
                        errors="ignore").read()
            for ref in _REF.findall(text):
                if ref.startswith("res://"):
                    rel = ref[len("res://"):]
                    if not os.path.exists(os.path.join(pkg_dir, rel)):
                        dangling.append(f"{f} -> {ref}")
                elif ref.startswith("user://"):
                    continue
                elif _ABS_START.match(ref):
                    abs_hits.append(f"{f}: {ref}")
    return {"absolute_path_count": len(abs_hits),
            "absolute_paths": abs_hits[:20],
            "dangling_refs": dangling,
            "portable": len(abs_hits) == 0 and not dangling}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Package a themed walkable building "
                                             "as a dependency-free Godot handoff.")
    ap.add_argument("slots", help="<name>.slots.json")
    ap.add_argument("--gameplay", default="", help="<name>.gameplay.json (markers)")
    ap.add_argument("--modules", required=True, help="dir of themed module .glb files")
    ap.add_argument("--theme", required=True)
    ap.add_argument("--style", type=int, default=1)
    ap.add_argument("--greybox", default="",
                    help="deli greybox .glb -> stripped to a floors+collision "
                         "base so the building is walkable (recommended)")
    ap.add_argument("--out", required=True, help="output package dir")
    a = ap.parse_args()
    man = build_package(a.slots, a.gameplay, a.modules, a.out,
                        theme=a.theme, style=a.style,
                        greybox_glb=(a.greybox or None))
    c = man["closure"]
    ins = man["instancing"]
    print(f"[portable] {man['building_id']} ({man['theme']}): "
          f"{man['themed_modules']} themed instances, "
          f"{len(man['bundled_modules'])} modules bundled, "
          f"{man['markers_baked']} markers baked")
    print(f"[portable] instancing: {ins['distinct_meshes']} distinct meshes "
          f"shared across {ins['module_instances']} instances "
          f"({ins['reuse_ratio']}x reuse) -- VRAM holds distinct meshes only")
    if man.get("greybox_base"):
        gb = man["greybox_base"]
        print(f"[portable] greybox base: kept {gb['kept_greybox_visuals']} "
              f"greybox visuals (floors/canopy/props) + {gb['kept_colliders']} "
              f"colliders, dropped {gb['dropped_slot_visuals']} slot surfaces "
              f"(walkable={man['walkable']})")
    pc = man.get("placement_check")
    if pc:
        tag = "OK" if pc["ok"] else "!! MISMATCH"
        colour = "" if pc["ok"] else " -- visuals will NOT sit on the collision"
        print(f"[portable] placement check [{tag}]: {pc['matched']}/{pc['checked']} "
              f"modules match the greybox FOOTPRINT{colour}")
        for m in pc["mismatches"][:8]:
            print(f"    {m['slot']} ({m['stem']}) fit_rot={m.get('fit_rot')}: "
                  f"greybox={m['greybox_extent']} placed={m['placed_extent']}")
        hw = pc.get("height_warning_count", 0)
        if hw:
            print(f"[portable] advisory: {hw} module(s) not built to the authored "
                  f"opening height (zoo build regression, not a placement error)")
            for w in pc.get("height_warnings", [])[:4]:
                print(f"    {w['slot']} ({w['stem']}): "
                      f"authored_h={w['authored_h']} module_h={w['module_h']}")
    else:
        print("[portable] WARNING: no greybox base -- no floors; "
              "pass --greybox <shell.glb> to make it walkable")
    print(f"[portable] closure: absolute_paths={c['absolute_path_count']}, "
          f"dangling={len(c['dangling_refs'])}, PORTABLE={c['portable']}")
    if man["missing_modules"]:
        print(f"[portable] WARNING missing modules: {man['missing_modules']}")
