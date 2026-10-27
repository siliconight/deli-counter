#!/usr/bin/env python3
"""
migrate_aisle_markers.py  --  a supermarket hangs a numbered marker over each aisle (0.276.0)
=============================================================================================
One-shot, idempotent migration over specs/*.json. Furnish hangs a supermarket's aisle markers
(`level_design.aisle_markers`) over the lanes between its gondolas, numbered from aisle 1, in Zoo 1.131.0's
`aisle_sign` form `grocery`. The library is a fixed point of its furnishing pass, so every spec with a supermarket's
sales floor is refurnished (`migrate_furnish_recipes.migrate`); no other spec is touched.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrations/migrate_aisle_markers.py            # write specs/
    python migrations/migrate_aisle_markers.py --check    # report only; exit 1 if any would change
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "migrations"))

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402


def _supermarket(d):
    b = level_design.club_building_id(d)
    return any(level_design.is_supermarket_floor(r, b) for r in d.get("rooms") or [])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    changed = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not _supermarket(d):
            continue
        before = json.dumps(d, indent=1) + "\n"
        migrate_furnish_recipes.migrate(d)
        after = json.dumps(d, indent=1) + "\n"
        if after == before:
            continue
        changed += 1
        n = sum(1 for v in d["volumes"] if str(v.get("name", "")).startswith("aisle_sign_"))
        print(f"[aisle_markers] {os.path.basename(p)}: {n} marker(s)")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(after)
    verb = "would change" if check else "refurnished"
    print(f"[aisle_markers] {changed} spec(s) {verb}")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
