#!/usr/bin/env python3
"""
migrate_pallet_pile.py  --  a stored loading dock's pile becomes pallet stacks (0.267.0)
====================================================================================
One-shot, idempotent migration over specs/*.json, lf_ specs excepted. Each volume named exactly
`loading_pallet_stack` -- the 4.5 x 2.5 x 1.5 m block the corner deli preset authored, which Zoo's `pallet_stack`
cannot fit and built as a plain box -- is replaced, in its place in the list, by `presets.pallet_pile` at its centre
and on its floor (its z less half its height), over the block's own footprint, and the spec is refurnished
(`migrate_furnish_recipes.migrate`): the library is a fixed point of furnish. A spec already carrying
`loading_pallet_stack_1` is not touched.

    python migrations/migrate_pallet_pile.py            # write specs/
    python migrations/migrate_pallet_pile.py --check    # report only
"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import migrate_furnish_recipes  # noqa: E402
import presets  # noqa: E402


def main():
    check = "--check" in sys.argv
    done = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        vols = d.get("volumes") or []
        if any(v.get("name") == "loading_pallet_stack_1" for v in vols):
            continue
        out, changed = [], False
        for v in vols:
            if v.get("name") != "loading_pallet_stack":
                out.append(v)
                continue
            floor_z = float(v["z"]) - float(v["size_z"]) / 2.0
            out.extend(presets.pallet_pile(float(v["x"]), float(v["y"]), floor_z, float(v["size_x"]),
                                           float(v["size_y"]), v.get("material", "wood")))
            changed = True
        if changed:
            done += 1
            if not check:
                d["volumes"] = out
                # the room is refurnished around the stacks: the library is a fixed point of furnish, and a pile
                # in six pieces with gaps is new input to it (`migrate_cooler_wall`'s reason)
                migrate_furnish_recipes.migrate(d)
                io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[pallet_pile] %d spec(s) given pallet stacks%s" % (done, " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
