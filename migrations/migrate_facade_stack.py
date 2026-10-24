#!/usr/bin/env python3
"""
migrate_facade_stack.py  --  the library's upper storeys stand over the openings below
======================================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.238.0 (the
factory's roadmap 79, its `docs/proposals/FACADE_PLANNER.md`, step 3).

Measured on the library before it ran (the factory's
`docs/findings/facade_census_79/`): of the 169 first-storey openings in the 52
multi-storey buildings a themed lot can draw, 28 stood over a ground-floor
opening. The upper storeys had been authored mirrored about each face's centre,
the ground floors for the rooms behind them, and nothing ever asked the two to
meet.

Each library spec -- not a Level Factory transient (`lf_*`), not an Empty,
which its own row composed -- goes through `facade_plan.stack_mirrored`: an
untagged upper-storey window moves onto an opening of the storey below, a
mirrored pair only together onto a mirrored pair, within a bay; every
ground-floor opening, door, breach and tagged window stays where gameplay put
it. A spec that changed is REFURNISHED (`migrate_furnish_recipes.migrate`), so
it stays a fixed point of furnish: a moved window moves the fixtures beside it.

    python migrations/migrate_facade_stack.py            # write specs/
    python migrations/migrate_facade_stack.py --check    # report only; exit 1 if any would change
    python migrations/migrate_facade_stack.py --dir D    # another spec directory
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
    """Compose one spec dict's faces and refurnish it if a window moved, in place: ``(moves, held)``."""
    moves, held = facade_plan.stack_mirrored(d)
    if moves and d.get("rooms"):
        migrate_furnish_recipes.migrate(d)
    return moves, held


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = argv[argv.index("--dir") + 1] if "--dir" in argv else os.path.join(HERE, "specs")
    changed, windows, held_n = [], 0, 0
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
        moves, held = migrate(d)
        held_n += len(held)
        if not moves:
            continue
        changed.append(name)
        windows += len(moves)
        print("  %s: %s" % (name, ", ".join("%s%d %+.2f -> %+.2f" % m for m in moves)))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[facade_stack] %d window(s) in %d spec(s) %s; %d held where they stood"
          % (windows, len(changed), "to move" if check else "moved", held_n))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
