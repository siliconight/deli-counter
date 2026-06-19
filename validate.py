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

    if hard or not sem_ok:
        print(f"  -> {len(hard)} schema error(s)"
              + ("" if sem_ok else ", semantic errors"))
        return False
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
