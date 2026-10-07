#!/usr/bin/env python3
"""
migrate_wall_crossing.py  --  a piece through a wall is trimmed back to its side
================================================================================
Deli Counter 0.199.0: the rule `presets.make` runs on every recipe, and the
one-shot, idempotent migration over specs/*.json that brings the library to
it.

MEASURED FIRST (the factory's docs/findings/pieces_through_walls/; layout_lint
L25 asks the same question): 19 pieces in 15 of the 146 non-LF specs reach
past both faces of a wall the builder stands. Seven pass THROUGH one: each of
the six delis' case, authored by `presets.corner_deli` 7.0 m long from x -14.0
with its own partition at x -8.0, so 0.825 m of it stood out in the market
aisles (cold run 9189's composed deli_a01 builds it so: the case at
x -14.0..-7.0, partition `int_0_0_seg6` at x -8.0 across it); and
`warehouse`'s 16 m shelving run, 3.85 m into the room past x 8.0. Of the 23
recipes, `corner_deli` and `hospital` generate one: the case, and the waiting
seats 0.35 m into the next room.

THE RULE, in the spec's frame (metres, the footprint centred on 0): a piece
THROUGH a wall (`layout_lint.wall_crossings`, shape ``through``) keeps the end
on the side its centre stands, and its far end comes back to that side's face
of the wall less `level_design._WALL_PIECE_AIR`, the air a wall-slotted piece
keeps to its wall. Only that one axis moves: the piece keeps its height, its
depth and its near end. REFUSED and reported, never forced:
  * a piece ALONG a wall, centred on its line: which side is it on?
  * a turned piece (`rot_z` not a half turn): its art is not its box;
  * a cut that would leave less than `KEEP_MIN` of the piece: a different
    piece, which its author should name;
  * a cut from under a marker, an objective or a loot point: what stands
    there would stand on nothing.

    python migrate_wall_crossing.py            # write specs/
    python migrate_wall_crossing.py --check    # report only; exit 1 if any
    python migrate_wall_crossing.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint  # noqa: E402
import level_design  # noqa: E402

#: The least share of a piece a cut may leave. A centre off the wall loses
#: under half plus the air, so this bites only where the centre hugs a face.
KEEP_MIN = 0.5
#: Cuts one spec may take before it stands clear: one per piece and wall.
ROUNDS = 64


def _on_the_cut(spec, v, axis, lo, hi):
    """Ids of the markers, objectives and loot standing on the part a cut
    takes away: in plan inside it, and on the piece's storey."""
    other = "y" if axis == "x" else "x"
    c, half = float(v[other]), float(v["size_" + other]) / 2.0
    sh = float(layout_lint._spec_value(spec, "story_height"))
    story = layout_lint.piece_story(spec, v)
    if story is None:
        story = int((float(v.get("z", 0.0)) - float(v.get("size_z", 0.0)) / 2.0) // sh)
    out = []
    for kind in ("markers", "objectives", "loot"):
        for m in spec.get(kind) or []:
            if not (lo <= float(m.get(axis, 0.0)) <= hi
                    and c - half <= float(m.get(other, 0.0)) <= c + half):
                continue
            if story * sh - 0.25 <= float(m.get("z", 0.0)) < (story + 1) * sh:
                out.append(str(m.get("id") or m.get("type") or kind))
    return out


def _why_not(spec, v, row):
    """``(why, cut)``: the reason a crossing is not trimmed, or None and the
    piece's new ``(lo, hi)`` on the wall's axis."""
    a = row["axis"]
    f0, f1 = row["faces"]
    if row["shape"] == "along":
        return ("it stands along %s, centred on its line: which side is it "
                "on?" % row["wall"]), None
    rz = float(v.get("rot_z", 0.0) or 0.0) % 180.0
    if min(rz, 180.0 - rz) > 1e-6:
        return ("it is turned %g degrees: its art is not its box"
                % float(v.get("rot_z"))), None
    c, length = float(v[a]), float(v["size_" + a])
    lo, hi = c - length / 2.0, c + length / 2.0
    air = level_design._WALL_PIECE_AIR
    if c < f0:
        new, taken = (lo, f0 - air), (f0 - air, hi)
    else:
        new, taken = (f1 + air, hi), (lo, f1 + air)
    if new[1] - new[0] < KEEP_MIN * length:
        return ("the cut would leave %.2f of its %.2f m, less than half of it"
                % (new[1] - new[0], length)), None
    under = _on_the_cut(spec, v, a, *taken)
    if under:
        return ("the cut would take the ground from under %s"
                % ", ".join(under)), None
    return None, new


def trim(spec):
    """``(trimmed, refused)`` for one spec dict, in place. ``trimmed`` holds a
    record a cut, ``{name, wall, axis, from, to}`` (the piece's ends on that
    axis before and after); ``refused`` holds ``(name, wall, why)``."""
    trimmed, refused, skip = [], [], set()
    for _ in range(ROUNDS):
        row = next((r for r in layout_lint.wall_crossings(spec)
                    if (r["index"], r["wall"]) not in skip), None)
        if row is None:
            break
        v = spec["volumes"][row["index"]]
        why, new = _why_not(spec, v, row)
        if why:
            refused.append((row["name"], row["wall"], why))
            skip.add((row["index"], row["wall"]))
            continue
        a = row["axis"]
        c, length = float(v[a]), float(v["size_" + a])
        v[a] = round((new[0] + new[1]) / 2.0, 4)
        v["size_" + a] = round(new[1] - new[0], 4)
        trimmed.append({"name": row["name"], "wall": row["wall"], "axis": a,
                        "from": [round(c - length / 2.0, 4), round(c + length / 2.0, 4)],
                        "to": [round(new[0], 4), round(new[1], 4)]})
    return trimmed, refused


def migrate(d):
    """``(changed, why)`` for one spec dict, in place."""
    trimmed, refused = trim(d)
    why = "; ".join("'%s' at %s: %s" % r for r in refused) or None
    return bool(trimmed), why


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    n = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        trimmed, refused = trim(d)
        for name, wall, why in refused:
            print(f"[wall_crossing] {os.path.basename(p)}: '{name}' at {wall} "
                  f"REFUSED -- {why}")
        if not trimmed:
            continue
        n += 1
        for t in trimmed:
            print(f"[wall_crossing] {os.path.basename(p)}: '{t['name']}' through "
                  f"{t['wall']}: {t['axis']} {t['from'][0]}..{t['from'][1]} -> "
                  f"{t['to'][0]}..{t['to'][1]}")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print(f"[wall_crossing] {n} spec(s) {'need' if check else 'given'} a piece trimmed off a wall")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
