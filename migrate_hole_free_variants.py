#!/usr/bin/env python3
"""
migrate_hole_free_variants.py  --  a family's variant without a hole in its floor
=================================================================================
One-shot, idempotent migration for the factory's roadmap 269. The walker,
2026-10-20: "stairs and ladders should be the primary way to get between floors
in this game...with the holes in floors being somewhat rare...but still at our
disposal to use if needed/desired to add some more ways to navigate levels".

Level Factory draws a level without a hole by swapping a lot's building for a
variant of its family that has none -- and the deli family had no such variant
a themed lot could draw: deli_a01 and deli_a03 both carried the 2.2 m cut drop
from the apartment hideout into the kitchen (deli_a02 is not themeable). So
every corner-deli level carried one (the factory's
`docs/findings/hole_frequency/`).

Each spec in HOLE_FREE loses the holes in its floors a player would see
(`hole_causes.without_holes`: the drop link and the authored slab hole under
it; a hatch into the stair's own well stays) and is REFURNISHED, so it stays a
fixed point of furnish (`test_club_fixtures`): the hideout's floor where the
hole was is floor again, and furnish lays a room round what stands in it.

    python migrate_hole_free_variants.py            # write specs/
    python migrate_hole_free_variants.py --check    # report only; exit 1 if any would change
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hole_causes               # noqa: E402
import migrate_furnish_recipes   # noqa: E402

#: The variants that carry no hole. A call, made 2026-10-20 and meant to be
#: changed: deli_a01, because deli_a03 keeps the drop the factory's cold runs
#: 9340 and 9341 proved and priced.
HOLE_FREE = ("deli_a01",)


def migrate(d):
    """Leave out one spec dict's holes and refurnish it, in place: ``(links, slab_holes)`` removed."""
    links, holes = hole_causes.without_holes(d)
    if links:
        migrate_furnish_recipes.migrate(d)
    return links, holes


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    changed = []
    for name in HOLE_FREE:
        p = os.path.join(HERE, "specs", name + ".json")
        d = json.load(open(p, encoding="utf-8"))
        links, holes = migrate(d)
        if not links:
            continue
        changed.append((name, links, holes))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    for name, links, holes in changed:
        print("  %s: %s, %d slab hole(s)" % (
            name, ", ".join("%s %s at (%g, %g)" % (v.get("kind"), v.get("role") or "", float(v["x"]), float(v["y"]))
                            for v in links), len(holes)))
    print("[hole_free_variants] %d spec(s) %s" % (len(changed), "to change" if check else "changed"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
