#!/usr/bin/env python3
"""
migrate_stair_walls.py  --  move every stair whose hole cuts a wall
===================================================================
One-shot, idempotent migration over specs/*.json for `layout_lint` L21 (a
stair's hole may not cut a wall or open under a doorway; the rule and the
walker's captured case are in `layout_lint.stair_wall_findings`). Each named
stair is re-seated by `stair_pitch.clear_walls`: its own facing then the other
three, short shifts along both axes, keeping the first seat that satisfies the
circulation contract, L19 and L21 and adds no other lint failure. The walls
and rooms are never moved. `lf_*` specs are Level Factory's per-run transients
and are skipped.

    python migrate_stair_walls.py                 # write specs/
    python migrate_stair_walls.py --check         # report only; exit 1 on any L21
    python migrate_stair_walls.py --dir OTHER     # a different spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint  # noqa: E402
import stair_pitch  # noqa: E402


def main():
    check = "--check" in sys.argv
    root = os.path.join(HERE, "specs")
    if "--dir" in sys.argv:
        root = sys.argv[sys.argv.index("--dir") + 1]
    specs = findings = 0
    moved = {}
    unresolved = []
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(p)
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if d.get("facade") or not d.get("stairs") or not d.get("footprint_x"):
            continue
        found = layout_lint.stair_wall_findings(d)
        if not found:
            continue
        specs += 1
        findings += len(found)
        if check:
            for f in found:
                print(f"  {name}: {f}")
            continue
        r = stair_pitch.clear_walls(d)
        for sid, seat in r["reseated"].items():
            moved[(name, sid)] = seat
        unresolved += [(name, s) for s in r["unresolved"]]
        if r["reseated"]:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    for (name, sid), (facing, axis, d) in sorted(moved.items()):
        shift = (f"x {d[0]:+g} m, y {d[1]:+g} m" if axis == "xy"
                 else f"{axis} {d:+g} m")
        print(f"  {name} {sid}: facing {facing}, {shift}")
    verb = "found" if check else "re-seated"
    print(f"[stair_walls] {specs} spec(s), {findings} L21 finding(s); "
          f"{len(moved)} stair(s) {verb if not check else 'to move'}, "
          f"{len(unresolved)} unresolved {unresolved}")
    return 1 if (check and findings) or unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
