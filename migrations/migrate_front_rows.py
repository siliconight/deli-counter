#!/usr/bin/env python3
"""
migrate_front_rows.py  --  a family's street face upstairs stands on its row
============================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.296.0 (the
factory's roadmap 79, the facade planner; the walker of the slice's card shop:
"yes to window rhythm").

Each library spec -- not a Level Factory transient (`lf_*`) -- whose preset
`facade_plan.FRONT_ROWS` names goes through `facade_plan.compose_front`: the
street face of every upper storey people reach is re-laid one window to a
`midrise` bay. People stand behind those windows, and the furniture was laid
round the windows that were there, so a spec this changes is refurnished
(`migrate_furnish_recipes.migrate`, measured a fixed point on every spec it
touches before this ran) and the pieces stand round the new ones.

    python migrations/migrate_front_rows.py            # write specs/
    python migrations/migrate_front_rows.py --check    # report only; exit 1 if any would change
    python migrations/migrate_front_rows.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import facade_plan               # noqa: E402
import migrate_furnish_recipes   # noqa: E402


def migrate(d):
    """Compose and refurnish one spec dict in place: ``(faces, (removed, added))``, ``([], None)`` when the
    face was already its row's."""
    faces = facade_plan.compose_front(d)
    if not any(before != after for _w, _s, before, after in faces):
        return faces, None
    return faces, migrate_furnish_recipes.migrate(d)


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
        if not isinstance(d, dict) or d.get("preset") not in facade_plan.FRONT_ROWS:
            continue
        before = json.dumps(d, sort_keys=True)
        faces, furnished = migrate(d)
        if json.dumps(d, sort_keys=True) == before:
            continue
        changed.append(name)
        print("  %s: %s; refurnished %s" % (name, ", ".join("%s%d %d -> %d" % f for f in faces), furnished))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[front_rows] %d spec(s) %s" % (len(changed), "to compose" if check else "composed"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
