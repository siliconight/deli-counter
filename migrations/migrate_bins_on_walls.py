#!/usr/bin/env python3
"""
migrate_bins_on_walls.py  --  the library's litter bins stand against a wall (0.266.0)
=====================================================================================
One-shot, idempotent migration over specs/*.json, lf_ specs excepted. The walker, walking cold run 9386: "garbage
cans are usually up against walls inside buildings". `level_design.stand_bins_on_walls` -- the last step of
`furnish` since 0.266.0 -- over every stored spec: each bin furnish stood goes to the nearest spot flush against a
wall of its room, or goes when none is clear. Nothing else in any spec moves, so no refurnish follows.

    python migrations/migrate_bins_on_walls.py            # write specs/
    python migrations/migrate_bins_on_walls.py --check    # report only
"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import level_design  # noqa: E402


def main():
    check = "--check" in sys.argv
    specs = moved = removed = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict) or not d.get("rooms"):
            continue
        m, r = level_design.stand_bins_on_walls(d)
        if m or r:
            specs += 1
            moved += m
            removed += r
            if not check:
                io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[bins_on_walls] %d specs: %d bins moved to a wall, %d with no clear wall removed%s"
          % (specs, moved, removed, " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
