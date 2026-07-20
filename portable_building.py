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


def strip_greybox_base(src_glb, out_glb, slot_ids):
    """ADDITIVE base: keep the whole coherent greybox EXCEPT the swappable-slot
    surfaces that themed modules replace. Every collider stays; floors, canopy,
    pumps, aisles, counters -- all non-slot geometry -- stay greybox-visible. A
    visual is dropped ONLY if its node name carries a themed slot_id (a wall /
    opening / roof that a zoo module is instanced onto), so we don't get double
    walls. This is the baked 'theme swap': add themed art to the slots, keep the
    building deli_counter already made."""
    from pygltflib import GLTF2
    g = GLTF2().load(src_glb)
    sids = [s.lower() for s in slot_ids if s]
    kept_col = kept_vis = dropped = 0
    for n in g.nodes:
        if n.mesh is None:
            continue
        low = (n.name or "").lower()
        if "colonly" in low or "convcolonly" in low:
            kept_col += 1                       # never touch collision/nav
        elif any(sid in low for sid in sids):
            n.mesh = None                       # themed module covers this slot
            dropped += 1
        else:
            kept_vis += 1                       # floors, canopy, pumps, props
    g.save(out_glb)
    return {"kept_colliders": kept_col, "kept_greybox_visuals": kept_vis,
            "dropped_slot_visuals": dropped}


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
        stem, _scaled = themed_tscn.resolve_themed_stem(s, theme, style)
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


def build_package(slots_path, gameplay_path, module_dir, out_dir, *,
                  theme, style=1, building_id=None, greybox_glb=None):
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
        base_strip = strip_greybox_base(greybox_glb,
                                        os.path.join(out_dir, base_name),
                                        slot_ids)
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

    manifest = {
        "schema": "portable_building.v0.1", "building_id": bid, "theme": theme,
        "themed_modules": stats["themed"], "greybox_fallback": stats["greybox_fallback"],
        "bundled_modules": bundled, "missing_modules": missing,
        "markers_baked": len(gameplay.get("markers") or []),
        "greybox_base": base_strip,
        "walkable": bool(base_strip),   # floors present -> something to stand on
        "placement_check": placement,   # visual-vs-collision agreement
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
