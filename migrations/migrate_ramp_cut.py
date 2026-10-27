#!/usr/bin/env python3
"""
migrate_ramp_cut.py  --  nothing stands in a ramp's cut (0.273.0)
==================================================================
One-shot, idempotent migration over specs/*.json for the factory's roadmap 270.

0.273.0 starts a ramp's slab cut where a body clears the slab (`stairwell.ramp_cut_span`), not at its middle, and
furnish keeps every piece off the cut (`level_design.ramp_holes`). Furniture placed before stood in the longer cuts.
Measured over the library before it ran:

  cbp_town_finale_midbalanced_schemafixed  storey 1: cartons_ra81f68c3_10, desk_r6b7fb888_1,
                                           chair_set_r6b7fb888_1_1                        -- furnished
  foundry_heist_vertical                   storey 0: pallets_r72ebbdd3_6, barrel_drum_r72ebbdd3_7 -- furnished
                                                     forklift_cover, loading_crate_stack_a        -- AUTHORED

A furnished piece moves with a refurnish (the chain every refurnishing migration runs). An authored piece is the
spec's own and is moved here, explicitly, by the least distance that clears the cut and its rail (0.3 m, the hole
clearance furnish keeps), along the ramp's width, inside the room it stood in:

  forklift_cover         x 12.0 -> 10.6  (the cut's west edge is 12.3; half its 2.6 m width, 1.3, and 0.3 clear)
  loading_crate_stack_a  x 17.0 -> 17.6  (the cut's east edge is 15.7; half its 3.0 m width, 1.5, and 0.3 clear)

    python migrations/migrate_ramp_cut.py            # write specs/
    python migrations/migrate_ramp_cut.py --check    # report only; exit 1 if any
"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402
import migrate_seed_corridor  # noqa: E402
import migrate_seed_lines  # noqa: E402
import migrate_shelter  # noqa: E402
import migrate_wall_crossing  # noqa: E402

#: The authored pieces the longer cuts reach: (spec, volume, axis, from, to), each asserted before it moves.
AUTHORED_MOVES = (("foundry_heist_vertical", "forklift_cover", "x", 12.0, 10.6),
                  ("foundry_heist_vertical", "loading_crate_stack_a", "x", 17.0, 17.6))


def in_cuts(d):
    """``[(story, volume name)]``: every volume standing on a storey whose floor a ramp cuts, inside the cut."""
    H = float(d.get("story_height", 3.0))
    out = []
    for story in sorted({int(r.get("to_story", 0)) for r in d.get("ramps") or []}):
        holes = level_design.ramp_holes(d, story)
        if not holes:
            continue
        floor = story * H
        for v in d.get("volumes") or []:
            vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
            if not (floor - 0.05 <= vz - vh / 2.0 <= floor + H - 0.1):
                continue
            for x0, y0, x1, y1 in holes:
                if (abs(v["x"] - (x0 + x1) / 2.0) < (x1 - x0) / 2.0 + v.get("size_x", 0.0) / 2.0
                        and abs(v["y"] - (y0 + y1) / 2.0) < (y1 - y0) / 2.0 + v.get("size_y", 0.0) / 2.0):
                    out.append((story, v["name"]))
                    break
    return out


def migrate(d, name):
    """Move this spec's authored pieces out of its cuts, then refurnish it. Returns what still stands in a cut."""
    for spec, vol, axis, old, new in AUTHORED_MOVES:
        if spec != name:
            continue
        v = next(x for x in d["volumes"] if x["name"] == vol)
        if abs(v[axis] - new) < 1e-9:
            continue
        assert abs(v[axis] - old) < 1e-9, (name, vol, v[axis], old)
        v[axis] = new
    migrate_furnish_recipes.migrate(d)
    migrate_shelter.migrate(d)
    migrate_seed_corridor.migrate(d)
    migrate_seed_lines.migrate(d)
    migrate_wall_crossing.migrate(d)
    return in_cuts(d)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    todo = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict) or not d.get("ramps"):
            continue
        found = in_cuts(d)
        if not found:
            continue
        todo += 1
        print("[ramp_cut] %s: %s" % (name, ", ".join("%s (storey %d)" % (n, s) for s, n in found)))
        if check:
            continue
        left = migrate(d, name)
        assert not left, (name, left)
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[ramp_cut] %d spec(s) %s" % (todo, "need it" if check else "cleared"))
    return 1 if check and todo else 0


if __name__ == "__main__":
    sys.exit(main())
