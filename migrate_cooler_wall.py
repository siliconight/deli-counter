#!/usr/bin/env python3
"""
migrate_cooler_wall.py  --  a walk-in cooler has its reach-in doors
===================================================================
One-shot, idempotent migration over specs/*.json for Zoo 1.12.0's
`cooler_run`: the convenience store's glowing reach-in cooler wall. The
walker, 2026-09-28: "do the cooler wall next".

WHY. Five store specs already place a `cooler_run` volume (8.0 x 2.8 x 2.2
against the stockroom partition, from the `gas_station` preset). The stores
built otherwise -- `gas_station_a02`, the one club_block_014 stands, and
`fuel_stop_heist` -- have a `walk_in_cooler` ROOM and no cooler wall at all,
so the drinks a convenience store is built round are behind a partition
nobody sees. A reach-in wall is the walk-in's customer-facing side, so this
puts one there.

THE RULE, measured per spec rather than authored per spec:

  * the WALL: a side of the `walk_in_cooler` room shared with a customer
    room (`CUSTOMER_ROOMS`), found from the room bounds; the run stands in
    the customer room with its back `WALL_BACK` off the partition's centre
    line (half the 0.3 m partition and 2 cm);
  * the DOORS in that partition keep `DOOR_CLEAR` either side of their
    opening -- a02's `cooler_door_1`, the food-service door into the walk-in,
    is on exactly this wall;
  * the AISLE: nothing may stand within `AISLE` of the run's front; a volume
    that does cuts the run short rather than being moved;
  * the longest stretch left is used if it is at least `MIN_RUN` (the genome's
    1.6 m); otherwise the spec is REFUSED and reported, not forced.

FACING. Zoo builds a module's doors on its -Y face. A volume long in x is
emitted unturned, and its -Y face points to the spec's -y; a volume long in
y is turned 90 degrees by `prop_species.long_axis_first` and its -Y face
points to -x -- both MEASURED on cold run 9096's package from shipped node
transforms (the register counter, unturned, faces the south entry doors; an
aisle shelf in `deli_a01`, turned, faces -x). So the run needs `rot_z` 180
only when its customer room is on the +y or +x side.

THE ROOM IS REFURNISHED AFTER, and has to be. The library is a fixed point of
its furnishing pass (`test_club_fixtures`'s
`...is_still_a_fixed_point_of_furnish`): a spec's generated furniture is
exactly what `level_design.furnish` makes of everything else in it. A cooler
is new input to that pass, so the first commit of this migration -- which
only appended the volume -- was refused by Deli Counter's pre-commit gate on
exactly that test. Each spec given a cooler is therefore refurnished with
`migrate_furnish_recipes.migrate`, the furnishing the rest of the library
carries. Measured: gas_station_a02 trades a carton stack for a litter bin;
fuel_stop_heist loses two carton stacks and a work table the 4.12 m run and
its aisle displaced.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrate_cooler_wall.py            # write specs/
    python migrate_cooler_wall.py --check    # report only; exit 1 if any
    python migrate_cooler_wall.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

NAME = "cooler_run"
CUSTOMER_ROOMS = ("sales_floor", "food_service")
DEPTH = 0.9
HEIGHT = 2.2
WALL_BACK = 0.17
DOOR_CLEAR = 0.35
AISLE = 0.9
CORNER = 0.10
MIN_RUN = 1.6
EPS = 1e-6


def _sides(wk, room):
    """``[(axis, line, lo, hi, sign)]``: each side of the walk-in ``wk``
    shared with ``room`` (both ``[x0, y0, x1, y1]``). ``axis`` 'X' is a wall
    along x at y = ``line``; ``sign`` is the side the customer room is on."""
    out = []
    ox0, ox1 = max(wk[0], room[0]), min(wk[2], room[2])
    oy0, oy1 = max(wk[1], room[1]), min(wk[3], room[3])
    if ox1 - ox0 > EPS:
        if abs(wk[1] - room[3]) < EPS:
            out.append(("X", wk[1], ox0, ox1, -1))
        if abs(wk[3] - room[1]) < EPS:
            out.append(("X", wk[3], ox0, ox1, +1))
    if oy1 - oy0 > EPS:
        if abs(wk[0] - room[2]) < EPS:
            out.append(("Y", wk[0], oy0, oy1, -1))
        if abs(wk[2] - room[0]) < EPS:
            out.append(("Y", wk[2], oy0, oy1, +1))
    return out


def _subtract(intervals, a, b):
    out = []
    for lo, hi in intervals:
        if b <= lo or a >= hi:
            out.append((lo, hi))
            continue
        if a > lo:
            out.append((lo, a))
        if b < hi:
            out.append((b, hi))
    return out


def plan_cooler(spec):
    """``(volume, report)``: the cooler wall this spec should carry, or
    ``(None, why)``."""
    rooms = {r["id"]: r.get("bounds") for r in spec.get("rooms") or []}
    wk = rooms.get("walk_in_cooler")
    if not wk:
        return None, "no walk_in_cooler room"
    best = None
    for rid in CUSTOMER_ROOMS:
        room = rooms.get(rid)
        if not room:
            continue
        for axis, line, lo, hi, sign in _sides(wk, room):
            intervals = [(lo + CORNER, hi - CORNER)]
            for p in spec.get("partitions") or []:
                if p.get("axis") != axis or abs(float(p.get("pos", 0.0)) - line) > EPS:
                    continue
                s, e = float(p["start"]), float(p["end"])
                mid, run = (s + e) / 2.0, e - s
                for op in p.get("openings") or []:
                    c = mid + float(op.get("pos", 0.0)) * run
                    half = float(op.get("width") or 1.0) / 2.0 + DOOR_CLEAR
                    intervals = _subtract(intervals, c - half, c + half)
            back = line + sign * WALL_BACK
            front = back + sign * DEPTH
            band = sorted((back, front + sign * AISLE))
            for v in spec.get("volumes") or []:
                vx0, vx1 = v["x"] - v["size_x"] / 2.0, v["x"] + v["size_x"] / 2.0
                vy0, vy1 = v["y"] - v["size_y"] / 2.0, v["y"] + v["size_y"] / 2.0
                along = (vx0, vx1) if axis == "X" else (vy0, vy1)
                across = (vy0, vy1) if axis == "X" else (vx0, vx1)
                if across[1] <= band[0] + EPS or across[0] >= band[1] - EPS:
                    continue
                # the whole-site pads a building stands on are not furniture
                if v["size_x"] * v["size_y"] > 400.0:
                    continue
                intervals = _subtract(intervals, along[0] - 0.05, along[1] + 0.05)
            for a, b in intervals:
                if b - a >= MIN_RUN and (best is None or b - a > best[1] - best[0]):
                    best = (a, b, axis, back, sign, rid)
    if best is None:
        return None, "no stretch of the walk-in's customer side is %.1f m clear" % MIN_RUN
    a, b, axis, back, sign, rid = best
    cy = back + sign * DEPTH / 2.0
    length = round(b - a, 3)
    if axis == "X":
        vol = {"name": NAME, "x": round((a + b) / 2.0, 4), "y": round(cy, 4), "z": HEIGHT / 2.0,
               "size_x": length, "size_y": DEPTH, "size_z": HEIGHT}
    else:
        vol = {"name": NAME, "x": round(cy, 4), "y": round((a + b) / 2.0, 4), "z": HEIGHT / 2.0,
               "size_x": DEPTH, "size_y": length, "size_z": HEIGHT}
    # THE MATERIAL MUST BE DECLARED: the validator refuses a volume whose
    # material the spec's palette lacks, and neither store declares `glass`
    # (the first run of this migration used it and the gate's spec check
    # refused fuel_stop_heist). The walk-in's own `cooler_panel` is the right
    # word for it and both stores declare it; a store without it gets `metal`
    # declared the way furnishing declares a prop's. Zoo's recipe builds its
    # own steel and glass whatever the slot says -- this is the slot's label
    # and its acoustics.
    have = {m.get("id") for m in spec.get("materials") or []}
    if "cooler_panel" in have:
        mat = "cooler_panel"
    else:
        import level_design
        mat = level_design._declare_material(spec, "metal", level_design._PROP_ACOUSTIC["metal"])
    vol.update({"collision": "convex", "material": mat})
    if sign > 0:
        vol["rot_z"] = 180.0
    return vol, "%s side of the walk-in, facing %s, %.2f m long" % (axis, rid, length)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    placed = refused = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if any(v.get("name") == NAME for v in d.get("volumes") or []):
            continue
        vol, why = plan_cooler(d)
        if vol is None:
            if why != "no walk_in_cooler room":
                refused += 1
                print(f"[cooler_wall] {os.path.basename(p)}: REFUSED -- {why}")
            continue
        placed += 1
        print(f"[cooler_wall] {os.path.basename(p)}: {why}")
        if check:
            continue
        d["volumes"].append(vol)
        # the room is refurnished around the cooler: see the docstring
        import migrate_furnish_recipes
        migrate_furnish_recipes.migrate(d)
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "need a cooler wall" if check else "given a cooler wall"
    print(f"[cooler_wall] {placed} spec(s) {verb}, {refused} refused")
    return 1 if check and placed else 0


if __name__ == "__main__":
    sys.exit(main())
