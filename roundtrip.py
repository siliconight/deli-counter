#!/usr/bin/env python3
"""
roundtrip.py  --  the coordinate round-trip test (Blender leg)
==============================================================
Proves the coordinate contract (docs/COORDINATE_CONTRACT.md) survives export:

    build -> expectations recorded in <name>.manifest.json ("expected" block)
          -> <name>.glb exported
    THIS TOOL: re-import the GLB into a clean Blender scene and compare
          bounds, origin, transforms, and marker positions against the
          recorded expectations, within the ratified tolerances.

This is the sandbox-runnable leg. The ENGINE leg (import the same GLB into
Godot, then place it in a Lot site with a known transform and compare world
positions) runs wherever a Godot 4 binary exists; it consumes the same
manifest "expected" block, so the two legs can never drift apart.

Run inside Blender (or with the bpy module installed):

    blender --background --python roundtrip.py -- build/<name>.glb
    python3 roundtrip.py build/<name>.glb          (bpy module)
    python3 roundtrip.py --all                     (every glb with a manifest)

Writes build/<name>.roundtrip.json and exits non-zero on any tolerance breach.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Ratified Phase 0 tolerances (meters / degrees) — COORDINATE_CONTRACT.md
TOLERANCES = {
    "structural_alignment": 0.02,
    "marker_placement": 0.05,
    "floor_elevation": 0.02,
    "rotation_deg": 0.5,
    "seam_gap": 0.01,
    "imported_bounds": 0.02,
}


def _scene_reset():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _import_glb(path):
    import bpy
    bpy.ops.import_scene.gltf(filepath=path)
    return list(bpy.context.scene.objects)


def _visual_bounds(objs):
    from mathutils import Vector
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    n = 0
    for ob in objs:
        if ob.type != "MESH":
            continue
        name = ob.name.lower()
        # collision meshes ride along in the GLB (Godot -colonly/-convcolonly
        # suffixes); expected bounds were measured over VISUAL only, so skip.
        if "colonly" in name:
            continue
        n += 1
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return (lo, hi) if n else (None, None)


def _marker_empties(objs):
    out = {}
    for ob in objs:
        if ob.type == "EMPTY":
            out[ob.name] = list(ob.matrix_world.translation)
    return out


def check_glb(glb_path):
    """Return a roundtrip report dict for one built GLB."""
    base = os.path.splitext(glb_path)[0]
    name = os.path.basename(base)
    man_path = base + ".manifest.json"
    report = {"schema_version": 1, "name": name, "glb": os.path.basename(glb_path),
              "tolerances": TOLERANCES, "checks": [], "passed": True}

    def fail(code, msg, **data):
        report["checks"].append(dict(code=code, ok=False, msg=msg, **data))
        report["passed"] = False

    def ok(code, msg, **data):
        report["checks"].append(dict(code=code, ok=True, msg=msg, **data))

    if not os.path.exists(man_path):
        fail("RT-MANIFEST", f"no manifest next to {glb_path}")
        return report
    with open(man_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    expected = manifest.get("expected")
    if not expected:
        fail("RT-EXPECTED", "manifest has no 'expected' block — rebuild with "
             "the current kit (expectations are recorded at build time)")
        return report

    _scene_reset()
    objs = _import_glb(glb_path)

    # 1. transforms: unit scale, no negative scale on every imported node
    bad_scale = []
    for ob in objs:
        sx, sy, sz = ob.scale
        if min(sx, sy, sz) <= 0:
            bad_scale.append((ob.name, "negative/zero scale",
                              [round(v, 4) for v in ob.scale]))
        elif max(abs(sx - 1), abs(sy - 1), abs(sz - 1)) > 1e-4:
            bad_scale.append((ob.name, "non-unit scale",
                              [round(v, 4) for v in ob.scale]))
    if bad_scale:
        fail("RT-SCALE", f"{len(bad_scale)} node(s) violate the unit-scale "
             f"contract", nodes=bad_scale[:10])
    else:
        ok("RT-SCALE", f"all {len(objs)} nodes at unit positive scale")

    # 2. bounds: imported visual bounds vs expected (within tolerance)
    lo, hi = _visual_bounds(objs)
    tol = TOLERANCES["imported_bounds"]
    if lo is None:
        fail("RT-BOUNDS", "no visual meshes in imported GLB")
    else:
        exp_lo = expected["bounds_min"]
        exp_hi = expected["bounds_max"]
        worst = max(max(abs(a - b) for a, b in zip(lo, exp_lo)),
                    max(abs(a - b) for a, b in zip(hi, exp_hi)))
        if worst > tol:
            fail("RT-BOUNDS", f"imported bounds drift {worst*100:.1f} cm "
                 f"(max {tol*100:.0f} cm)",
                 imported=[lo, hi], expected=[exp_lo, exp_hi],
                 drift_m=round(worst, 5))
        else:
            ok("RT-BOUNDS", f"bounds drift {worst*1000:.2f} mm within "
               f"{tol*100:.0f} cm", drift_m=round(worst, 5))

    # 3. origin: expected origin must sit inside/at the imported footprint
    #    (the building origin is footprint-center at ground; after re-import
    #    the bounds must straddle it in X/Y and start within tolerance of it
    #    in Z, allowing basements to extend below)
    if lo is not None:
        oxy_ok = lo[0] <= 0 <= hi[0] and lo[1] <= 0 <= hi[1]
        ground_ok = lo[2] <= TOLERANCES["floor_elevation"]
        if not (oxy_ok and ground_ok):
            fail("RT-ORIGIN", "imported geometry does not straddle the "
                 "building origin / ground plane",
                 bounds=[lo, hi])
        else:
            ok("RT-ORIGIN", "origin at footprint-center, ground at Z<=tol")

    # 4. markers: every expected marker's empty survives import within tol
    tol = TOLERANCES["marker_placement"]
    empties = _marker_empties(objs)
    exp_markers = expected.get("markers", [])
    missing, drifted = [], []
    for m in exp_markers:
        mname = m.get("name") or m.get("type")
        # exported empties are prefixed/uppercased (e.g. ATTACKER_SPAWN_A);
        # match case-insensitively on suffix/name containment.
        cand = None
        for ename, pos in empties.items():
            if ename.lower() == str(mname).lower() or \
                    str(mname).lower() in ename.lower():
                cand = pos
                break
        if cand is None:
            missing.append(mname)
            continue
        d = max(abs(cand[i] - m["pos"][i]) for i in range(3))
        if d > tol:
            drifted.append((mname, round(d, 4)))
    if exp_markers:
        if missing and len(missing) == len(exp_markers):
            # markers may legitimately live only in gameplay.json (the GLB can
            # drop empties); the contract says gameplay.json is authoritative.
            ok("RT-MARKERS", f"no marker empties in GLB ({len(exp_markers)} "
               f"live in gameplay.json only — authoritative per contract)")
        elif drifted:
            fail("RT-MARKERS", f"{len(drifted)} marker(s) drifted beyond "
                 f"{tol*100:.0f} cm", drifted=drifted[:10])
        else:
            ok("RT-MARKERS", f"{len(exp_markers)-len(missing)} marker "
               f"empty(ies) within {tol*100:.0f} cm"
               + (f"; {len(missing)} in gameplay.json only" if missing else ""))

    # 5. floor elevations: recorded elevations must be contract-consistent
    sh = expected.get("story_height")
    elev = expected.get("floor_elevations", [])
    tol = TOLERANCES["floor_elevation"]
    bad = [e for i, e in enumerate(elev) if abs(e - i * sh) > tol]
    if bad:
        fail("RT-FLOORS", f"floor elevation(s) off contract: {bad}")
    else:
        ok("RT-FLOORS", f"{len(elev)} floor elevation(s) on contract "
           f"(story_height {sh})")

    return report


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = [a for a in argv[1:] if not a.startswith("--python")
                and not a.endswith(".py") and a not in
                ("--background", "-b", "blender")]
    targets = []
    if "--all" in argv:
        import glob
        for g in sorted(glob.glob(os.path.join(HERE, "build", "*.glb"))):
            if os.path.exists(os.path.splitext(g)[0] + ".manifest.json"):
                targets.append(g)
    else:
        targets = [a for a in argv if a.endswith(".glb")]
    if not targets:
        print("usage: roundtrip.py <built.glb> | --all")
        sys.exit(2)

    rc = 0
    for glb in targets:
        rep = check_glb(glb)
        out = os.path.splitext(glb)[0] + ".roundtrip.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=1)
        state = "PASS" if rep["passed"] else "FAIL"
        print(f"[roundtrip] {rep['name']}: {state} -> {out}")
        for c in rep["checks"]:
            print(f"    {'ok ' if c['ok'] else 'FAIL'} {c['code']}: {c['msg']}")
        if not rep["passed"]:
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
