#!/usr/bin/env python3
"""
migrate_open_floor_rules.py  --  sort the library's open floors by the walker's table
====================================================================================
Deli Counter 0.234.0 (the factory's roadmap 260): the one-shot, idempotent migration over specs/*.json that applies
`open_floor_rules.RULES` -- each pair of rooms meeting with no wall between them named one floor (`open_to`) or walled,
with a door where nothing walkable would join the two any more (`open_floor_rules.DOORWAY_POLICY`). `presets.make`
applies the same table to every building it makes, so a regenerated spec comes out as this leaves the library.

MEASURED FIRST (the factory's docs/findings/open_floor_table_260/pairs.py): 49 open floors in 26 specs, 20 pairs of
room ids. Seven met along a footprint's own edge, where the exterior wall stands -- the gas stations' forecourts --
and 0.234.0's reading of exterior walls (`tactical.exterior_parts`) leaves 42 here.

RUN AGAIN BY 0.235.0: `apply` slides a hole off a standing wall whose two sides are a WALL row's pair (layout_lint L27),
and this moved the six delis' drops 0.5 m east, off the kitchen wall 0.234.0 had stood under them.

The mission's own `lf_*` shells are not touched: they are built every run, from the generator, not the library.
Change the table and run this again: a pair already sorted the old way is not unsorted by it -- an OPEN row turned
WALL finds no open floor to close while `open_to` names it; take that out of the spec first.

    python migrate_open_floor_rules.py            # write specs/
    python migrate_open_floor_rules.py --check    # report only; exit 1 if any spec would change
    python migrate_open_floor_rules.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

import open_floor_rules

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    folder = argv[argv.index("--dir") + 1] if "--dir" in argv else os.path.join(HERE, "specs")
    changed = 0
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if not d.get("rooms"):
            continue
        said = open_floor_rules.apply(d)
        if not said:
            continue
        changed += 1
        for line in said:
            print("%s: %s" % (os.path.basename(path), line))
        if not check:
            io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("%d spec(s) %s" % (changed, "to migrate" if check else "migrated"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
