"""Freeze the built library's open floors nobody named (layout_lint L26, 0.223.0) in open_floor_baseline.json.

    python open_floor_baseline.py

A built spec is one with a manifest in build/; Level Factory's lf_ specs are not the library. Each pair is a room
tactical joins to another as one floor (`tactical.shared_open_edge`) that neither room's `open_to` names. Prints
the census and rewrites the file; `test_open_floor.py` fails on a pair this file does not hold and on one it holds
that the library no longer has, so re-run it after a spec names or walls one. It is a list for the walker to sort,
not a verdict on any pair.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402

OUT = os.path.join(HERE, "open_floor_baseline.json")
REASON = ("Two rooms on one storey whose shared edge no partition covers for tactical.OPEN_FLOOR_M, which the "
          "engine walks as one floor, and whose spec does not say so (layout_lint L26; the factory's roadmap "
          "255). FROZEN 2026-10-15 for the walker to sort, one pair at a time: say it is meant (`open_to` on "
          "either room) or build the wall. Not a verdict on any of them -- the walker's finding 5 of 2026-10-14 "
          "was one of these, and a lobby flowing into a bullpen is another. Re-run open_floor_baseline.py after "
          "each.")


def main():
    pairs = {}
    specs = 0
    for m in sorted(glob.glob(os.path.join(HERE, "build", "*.manifest.json"))):
        name = os.path.basename(m)[:-len(".manifest.json")]
        p = os.path.join(HERE, "specs", name + ".json")
        if name.startswith("lf_") or not os.path.exists(p):
            continue
        specs += 1
        got = layout_lint.open_floors(json.load(open(p, encoding="utf-8")))
        if got:
            pairs[name] = sorted("%s|%s" % (f["a"], f["b"]) for f in got)
            for f in got:
                print("%-26s story %2d  %s = %-7g  %7.2f..%-7.2f  %5.2f m uncovered  %s | %s"
                      % (name, f["story"], "y" if f["axis"] == "X" else "x", f["pos"], f["lo"], f["hi"],
                         f["uncovered"], f["a"], f["b"]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"open_floors": pairs, "reason": REASON}, fh, indent=2)
        fh.write("\n")
    total = sum(len(v) for v in pairs.values())
    print("%d open floors nobody named, in %d of %d built specs -> %s" % (total, len(pairs), specs, os.path.basename(OUT)))


if __name__ == "__main__":
    main()
