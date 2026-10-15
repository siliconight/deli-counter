#!/usr/bin/env python3
"""
migrate_basement_wall.py  --  the delis' basement divider runs wall to wall, and the utility room gets a door
===========================================================================================================
Deli Counter 0.222.0: the rule `presets.corner_deli` now builds, and the one-shot, idempotent migration over
specs/*.json that brings the library to it.

MEASURED FIRST (the factory's docs/findings/walk_2026-10-14/partition_gaps.py): in every deli the basement
divider along X at y 1.0 stood x -12..12, under rooms that meet across the whole basement, x -19..19. That left
7.00 m open at each end: the corridor into cold storage, and the utility room into the vault -- the objective
room, beside the 1.4 m breach that was its way in. Authored so by Deli Counter 0.80.0's `corner_deli` and carried
into all six delis since. The walker, cold run 9305's deli_a01: "this wall supposed to stop here and have this
big opening?"; asked, "close the basement".

Wall to wall, the divider leaves the utility room's two breach panels its only ways in, and a room a body reaches
only by breaching gets a door unless it is the objective (the walker, 2026-10-06; layout_lint L24 -- 0.197.0 had
found the utility room open floor through this very gap). Asked, the walker chose the door, from the corridor.

THE RULE, two steps, each from the spec's own numbers:
  1. a storey -1 partition along X at y 1.0 carrying the door tagged `basement_corridor` runs to the footprint's
     half-width both ways, and each of its openings keeps its ABSOLUTE position. The builder places an opening at
     snap(pos * run) from the run's centre, so the 24 m run put the door at snap(-0.35 * 24) = -8.5 and the
     breach at snap(0.3 * 24) = 7.0; the new fractions are those positions over the new run.
  2. the storey -1 partition along Y carrying the door tagged `cold_room_door` -- the corridor's and the utility
     room's shared wall south of the divider -- gains a door tagged `corridor_to_utility`, as wide as that one,
     midway between its breach and the divider: snap(-0.32 * 28) = -9.0 and 1.0, so y -4.0.
Nothing else in a spec moves. A spec already migrated is left alone. A divider of any other span is refused and
named, never forced.

    python migrate_basement_wall.py            # write specs/
    python migrate_basement_wall.py --check    # report only; exit 1 if any
    python migrate_basement_wall.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
#: The span 0.80.0's `corner_deli` authored, and the tags that mark the deli's two basement walls.
OLD = (-12.0, 12.0)
TAG = "basement_corridor"
COLD = "cold_room_door"
UTILITY = "corridor_to_utility"


def _snap(v, grid):
    return round(v / grid) * grid


def _at(o, p, grid):
    """Where the builder stands an opening: snap(pos * run) from the run's centre, plus that centre."""
    lo, hi = float(p["start"]), float(p["end"])
    return (lo + hi) / 2.0 + _snap(float(o["pos"]) * (hi - lo), grid)


def migrate(d):
    """Bring one spec dict to the rule, in place. ``[what changed]``, empty when nothing did."""
    said = []
    half = float(d["footprint_x"]) / 2.0
    grid = float(d.get("grid", 0.5))
    parts = d.get("partitions") or []
    dividers = [p for p in parts if p.get("story") == -1 and p.get("axis") == "X"
                and abs(float(p.get("pos", 0.0)) - 1.0) < 1e-9
                and any(o.get("tag") == TAG for o in p.get("openings") or ())]
    for p in dividers:
        lo, hi = float(p["start"]), float(p["end"])
        if (lo, hi) == (-half, half):
            continue
        if (lo, hi) != OLD:
            raise SystemExit("%s: its basement divider stands %g..%g, not the deli's %g..%g; not touched"
                             % (d.get("name"), lo, hi, OLD[0], OLD[1]))
        run, new_run = hi - lo, 2.0 * half
        for o in p.get("openings") or ():
            u = _snap(float(o["pos"]) * run, grid)    # where it was built, from the run's centre, 0.0
            o["pos"] = u / new_run                       # the same place on the new run, centred on 0.0 too
            said.append("%s %s kept at x %+.2f" % (o.get("kind"), o.get("tag", ""), u))
        p["start"], p["end"] = -half, half
        said.insert(0, "basement divider %g..%g -> %g..%g" % (lo, hi, -half, half))
    for div in dividers:
        for p in parts:
            if not (p.get("story") == -1 and p.get("axis") == "Y"
                    and any(o.get("tag") == COLD for o in p.get("openings") or ())):
                continue
            if any(o.get("tag") == UTILITY for o in p.get("openings") or ()):
                continue
            cold = [o for o in p["openings"] if o.get("tag") == COLD][0]
            # the breach on the divider's south side: the corridor's and the utility room's shared wall
            south = [o for o in p["openings"] if o.get("kind") == "breach" and _at(o, p, grid) < div["pos"]]
            if len(south) != 1:
                raise SystemExit("%s: %d breaches south of the divider on the cold-room wall, not one; not touched"
                                 % (d.get("name"), len(south)))
            y = (_at(south[0], p, grid) + float(div["pos"])) / 2.0
            centre = (float(p["start"]) + float(p["end"])) / 2.0
            p["openings"].append({"kind": "door", "pos": (y - centre) / (float(p["end"]) - float(p["start"])),
                                  "width": cold["width"], "tag": UTILITY})
            said.append("door %s added at y %+.2f" % (UTILITY, y))
    return said


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
        said = migrate(d)
        if not said:
            continue
        changed += 1
        print("%s: %s" % (os.path.basename(path), "; ".join(said)))
        if not check:
            io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("%d spec(s) %s" % (changed, "to migrate" if check else "migrated"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
