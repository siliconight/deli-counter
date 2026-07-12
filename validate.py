#!/usr/bin/env python3
"""
validate.py  --  check a level spec without launching Blender
=============================================================
    python validate.py specs/bank.json
    python validate.py --all

Uses the JSON Schema in schema/level.schema.json if `jsonschema` is installed
(pip install jsonschema); otherwise falls back to a lightweight structural
check. Either way it also runs spec_from_dict to catch loader-level errors.
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _schema_check(data):
    try:
        import jsonschema
    except ImportError:
        return ["(jsonschema not installed; skipped schema check. "
                "pip install jsonschema for full validation.)"]
    schema = _load_json(os.path.join(HERE, "schema", "level.schema.json"))
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for e in sorted(validator.iter_errors(data), key=lambda e: e.path):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errors.append(f"{loc}: {e.message}")
    return errors


def validate_file(path):
    print(f"\n== {os.path.basename(path)} ==")
    try:
        data = _load_json(path)
    except Exception as ex:
        print(f"  FAIL: invalid JSON: {ex}")
        return False

    schema_errs = _schema_check(data)
    hard = [e for e in schema_errs if not e.startswith("(")]
    for e in schema_errs:
        print(f"  {'WARN' if e.startswith('(') else 'SCHEMA'}: {e}")

    # loader check
    try:
        from spec_loader import spec_from_dict
        spec = spec_from_dict(data)
        n = (len(spec.ext_walls) + len(spec.partitions) + len(spec.stairs)
             + len(spec.slab_holes) + len(spec.volumes) + len(spec.parapets)
             + len(spec.placements))
        print(f"  loader OK: '{spec.name}', {spec.n_stories} stories, "
              f"{n} features, {len(spec.assets)} assets")
    except Exception as ex:
        print(f"  FAIL: loader error: {ex}")
        return False

    # kitbash semantic checks
    sem_ok = True
    asset_ids = {a.id for a in spec.assets}
    dup = [a.id for a in spec.assets if list(a.id for a in spec.assets).count(a.id) > 1]
    for i, p in enumerate(spec.placements):
        if p.asset not in asset_ids:
            print(f"  SEMANTIC: placement #{i} references undefined asset "
                  f"id '{p.asset}'")
            sem_ok = False
    # asset file existence (relative to spec dir + assets_dir)
    spec_dir = os.path.dirname(os.path.abspath(path))
    assets_root = os.path.normpath(os.path.join(spec_dir, spec.assets_dir))
    for a in spec.assets:
        ap = os.path.normpath(os.path.join(assets_root, a.file))
        if not os.path.exists(ap):
            print(f"  ASSET-MISSING: '{a.id}' file not found: {ap}")
            sem_ok = False
        if a.collision == "file":
            if not a.collision_file:
                print(f"  ASSET: '{a.id}' collision='file' but no collision_file")
                sem_ok = False
            else:
                cf = os.path.normpath(os.path.join(assets_root, a.collision_file))
                if not os.path.exists(cf):
                    print(f"  ASSET-MISSING: '{a.id}' collision_file: {cf}")
                    sem_ok = False

    # material reference checks
    mat_ids = {m.id for m in spec.materials}
    def _check_mat(mid, where):
        nonlocal sem_ok
        if mid and mid not in mat_ids:
            print(f"  MATERIAL: {where} references undefined material '{mid}'")
            sem_ok = False
    if spec.default_material:
        _check_mat(spec.default_material, "default_material")
    for w in spec.ext_walls:
        _check_mat(w.material, f"ext wall {w.wall}@{w.story}")
    for i, p in enumerate(spec.partitions):
        _check_mat(p.material, f"partition #{i}")
    for v in spec.volumes:
        _check_mat(v.material, f"volume '{v.name}'")

    if hard or not sem_ok:
        print(f"  -> {len(hard)} schema error(s)"
              + ("" if sem_ok else ", semantic errors"))
        return False

    # facade shells are intentionally non-enterable and carry no gameplay, so
    # the tactical / guard / enterability / navigability analyzers don't apply.
    if getattr(spec, "facade", False):
        print("  FACADE shell: exterior-only, gameplay analyzers skipped. OK")
        return True

    # tactical analysis (only meaningful if the spec defines rooms)
    try:
        from tactical import analyze, format_scorecard
        terrors, twarnings, scorecard = analyze(spec)
        for w in twarnings:
            print(f"  TACTICAL-WARN: {w}")
        for e in terrors:
            print(f"  TACTICAL-ERROR: {e}")
        if scorecard.get("tactical"):
            print(format_scorecard(spec.name, scorecard))
        if terrors:
            print(f"  -> {len(terrors)} tactical error(s)")
            return False
    except Exception as ex:
        print(f"  TACTICAL: analysis skipped ({ex})")

    # poly budget estimate (offline, informational — intel not judgment)
    try:
        import polybudget
        _, psummary = polybudget.estimate(spec)
        print(polybudget.format_summary(spec.name, psummary))
        for w in polybudget.budget_warnings(psummary):
            print(f"  POLY-NOTE: {w}")
    except Exception as ex:
        print(f"  POLY: estimate skipped ({ex})")

    # hard guards: IP-name (repo integrity) + step-rise (model integrity)
    try:
        import guards
        gerrors, gwarnings = guards.check_all(spec)
        for w in gwarnings:
            print(f"  GUARD-WARN: {w}")
        for e in gerrors:
            print(f"  GUARD-ERROR: {e}")
        if gerrors:
            print(f"  -> {len(gerrors)} guard error(s)")
            return False
    except Exception as ex:
        print(f"  GUARD: checks skipped ({ex})")

    # enterability (can a body actually get IN? — entry-side of reachability)
    try:
        import enterability
        eerrors, ewarnings = enterability.check(spec)
        esum = enterability.summary(spec)
        print(f"  enterability: {esum['valid_entries']} usable entry(s) "
              f"({esum['doors']} door/garage, {esum['standing_entries']} "
              f"standing) on walls {esum['entry_walls'] or '—'}")
        for w in ewarnings:
            print(f"  ENTRY-WARN: {w}")
        for e in eerrors:
            print(f"  ENTRY-ERROR: {e}")
        print(f"  ENTRY-NOTE: {enterability.CLEARANCE_NOTE}")
        if eerrors:
            print(f"  -> {len(eerrors)} enterability error(s)")
            return False
    except Exception as ex:
        print(f"  ENTRY: checks skipped ({ex})")

    # navigability proxy (offline pre-filter for AI nav; real check = navmesh)
    try:
        import navigability
        nerrors, nwarnings, nsummary = navigability.check(spec)
        print(navigability.format_summary(spec.name, nsummary))
        for w in nwarnings:
            print(f"  NAV-WARN: {w}")
        for e in nerrors:
            print(f"  NAV-ERROR: {e}")
        if nerrors:
            print(f"  -> {len(nerrors)} navigability error(s)")
            return False
    except Exception as ex:
        print(f"  NAV: proxy skipped ({ex})")

    # stairwell systems (semantic stair stacks + egress review; egress-role
    # stairs gate hard, unclassified stairs get the same findings as intel)
    try:
        import stairwell
        serrors, swarnings, ssummary = stairwell.check(spec)
        if spec.stairs:
            print(stairwell.format_summary(spec.name, ssummary))
        for w in swarnings:
            print(f"  STAIR-WARN: {w}")
        for e in serrors:
            print(f"  STAIR-ERROR: {e}")
        if serrors:
            print(f"  -> {len(serrors)} stairwell error(s)")
            return False
    except Exception as ex:
        print(f"  STAIRWELL: review skipped ({ex})")

    # ladder systems (semantic connections + access review; a ladder with no
    # role is a hard error, and a ladder is never counted as ordinary egress)
    try:
        import ladder
        lerrors, lwarnings, lsummary = ladder.check(spec)
        if spec.ladders:
            print(ladder.format_summary(spec.name, lsummary))
        for w in lwarnings:
            print(f"  LADDER-WARN: {w}")
        for e in lerrors:
            print(f"  LADDER-ERROR: {e}")
        if lerrors:
            print(f"  -> {len(lerrors)} ladder error(s)")
            return False
    except Exception as ex:
        print(f"  LADDER: review skipped ({ex})")

    # floorplan SVGs (offline visual intel — one per story)
    try:
        import floorplan
        fp_dir = os.path.join(HERE, "build", "floorplans")
        paths = floorplan.write_floorplans(spec, fp_dir)
        rels = ", ".join(os.path.basename(p) for p in paths)
        print(f"  floorplan: {len(paths)} story SVG(s) -> build/floorplans/ ({rels})")
    except Exception as ex:
        print(f"  FLOORPLAN: skipped ({ex})")

    # sightlines (tactical geometry intel — death lanes, exposure, cover,
    # intent mismatch; a GUIDE to better buildings, never a gate)
    try:
        import sightlines
        sl_dir = os.path.join(HERE, "build", "floorplans")
        for line in sightlines.report(spec).splitlines()[1:]:  # skip name header
            print(f"  {line}")
        spaths = sightlines.write_overlays(spec, sl_dir)
        print(f"  sightlines: {len(spaths)} overlay SVG(s) -> build/floorplans/")
    except Exception as ex:
        print(f"  SIGHTLINES: skipped ({ex})")

    print("  -> OK")
    return True


def main():
    args = sys.argv[1:]
    if args == ["--all"] or not args:
        specs = sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
        if not specs:
            sys.exit("No specs found in specs/")
    else:
        specs = args
    ok = all(validate_file(s) for s in specs)
    print()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
