#!/usr/bin/env python3
"""
migrate_unreached_facade.py  --  a storey nobody reaches is composed as a facade
================================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.295.0 (the
factory's roadmap 79, the facade planner's step 4 on the one storey where it
costs play nothing; the walker's vertical slice).

Each library spec -- not a Level Factory transient (`lf_*`), not an Empty,
which its own row composed -- goes through `facade_plan.compose_unreached`: on
an upper storey with no room and no stair, ladder, ramp or fire escape
arriving, each face's untagged windows are re-laid one to a `midrise` bay. No
room stands there, so nothing is refurnished; the emitter paints the windows as
an office after hours (`empty_panes.OFFICE`).

    python migrations/migrate_unreached_facade.py            # write specs/
    python migrations/migrate_unreached_facade.py --check    # report only; exit 1 if any would change
    python migrations/migrate_unreached_facade.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import facade_plan   # noqa: E402


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = argv[argv.index("--dir") + 1] if "--dir" in argv else os.path.join(HERE, "specs")
    changed = []
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(p)[:-len(".json")]
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict) or "ext_walls" not in d:
            continue
        before = json.dumps(d, sort_keys=True)
        faces = facade_plan.compose_unreached(d)
        if json.dumps(d, sort_keys=True) == before:
            continue
        changed.append(name)
        print("  %s: %s" % (name, ", ".join("%s%d %d -> %d" % f for f in faces)))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[unreached_facade] %d spec(s) %s" % (len(changed), "to compose" if check else "composed"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
