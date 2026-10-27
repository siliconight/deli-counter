#!/usr/bin/env python3
"""
migrate_supermarket_cooler.py  --  a supermarket has its cooler wall, and is furnished as a supermarket
======================================================================================================
One-shot, idempotent migration over specs/*.json (0.275.0). The walker, 2026-10-26, walking seed 9205's
supermarket: "far too dark in teh super market", and the comps after it -- "shiny floor, bright lights, isles,
glowing freezer section, stacked high" (the factory's docs/reference/GROCERY_STORE_COMPS.md: one aisle of glass-door
reach-in cases lit from inside, brighter than the floor in front of them).

WHY. The library's three supermarkets stood no cooler at all. `migrate_cooler_wall.py` gives a convenience store
its 8 m run on its sales floor, and 0.272.0 kept supermarkets out of that rule on purpose ("their cooler wall and
glass front are their own decision"). This is that decision: a supermarket's cooler wall is the length of its back
wall, not a corner store's ten doors.

THE RULE, measured per spec rather than authored per spec, on `migrate_cooler_wall`'s own clearances:

  * the WALL: the sales floor's edge opposite its storefront glass -- the back wall the aisles' heads face, where
    a real store backs its dairy and frozen cases onto the stockroom -- else the longest other solid edge;
    `migrate_cooler_wall._edge_walls` reads them, and a glazed wall is never one;
  * its doors keep `DOOR_CLEAR` either side, and anything AUTHORED in the `AISLE` in front of it cuts the run
    short. The furnishing is stripped before the plan is made (`level_design.unfurnished`) and laid again after
    it, so a filing cabinet the old recipe stood there does not decide where the coolers go;
  * the longest stretch left, at most `RUN` long and centred on it, refused below `MIN_RUN`;
  * built as runs of at most `PIECE` (Zoo `cooler_run`'s genome width, 12.0 m), equal lengths, named
    `cooler_run_sales_<i>` -- every one routes to the species by its `cooler_run` stem.

THE SPEC IS REFURNISHED AFTER (`migrate_furnish_recipes.migrate`), for the reason `migrate_cooler_wall` gives:
the library is a fixed point of its furnishing pass, and the cooler is new input to it. That pass also lays the
supermarket's own recipe (`level_design._RECIPES["supermarket"]`, 0.275.0) in place of the shop floor's.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrations/migrate_supermarket_cooler.py            # write specs/
    python migrations/migrate_supermarket_cooler.py --check    # report only; exit 1 if any
    python migrations/migrate_supermarket_cooler.py --dir D    # another spec directory
"""
import glob
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "migrations"))

import level_design  # noqa: E402
import migrate_cooler_wall as C  # noqa: E402

NAME = "cooler_run_sales"
#: The longest wall of coolers a supermarket stands: two of Zoo's longest runs.
RUN = 24.0
#: Zoo `cooler_run`'s genome width, at most.
PIECE = 12.0
MIN_RUN = C.MIN_RUN
#: A volume whose foot stands higher than this over storey 0's floor is not in the cooler's aisle: a sign hung over
#: the floor, or the storey above.
FOOT_MAX = 2.0


def sales_floor(spec):
    """The supermarket's storey-0 selling floor (`level_design.is_supermarket_floor`), or None."""
    building = level_design.club_building_id(spec)
    for r in spec.get("rooms") or []:
        if int(r.get("story", 0) or 0) == 0 and r.get("bounds") and level_design.is_supermarket_floor(r, building):
            return r
    return None


def _in_room(v, b):
    return b[0] <= v["x"] <= b[2] and b[1] <= v["y"] <= b[3]


def plan(spec):
    """``(volumes, why)``: the cooler runs this supermarket's sales floor should stand, or ``([], why)``.
    `spec` is the spec as furnish leaves it unfurnished."""
    room = sales_floor(spec)
    if room is None:
        return [], "no storey-0 supermarket sales floor"
    b = room["bounds"]
    storefront = {w.get("wall") for w in spec.get("ext_walls") or []
                  if "glass" in str(w.get("material") or "") and int(w.get("story", 0) or 0) == 0}
    back_walls = {C._OPPOSITE[w] for w in storefront if w in C._OPPOSITE}
    best = None
    for axis, line, lo, hi, sign, ops, ext in C._edge_walls(spec, b):
        if ext and (ext in storefront or any(k == "window" for _c, _w, k, _m in ops)):
            continue
        intervals = [(lo + C.CORNER, hi - C.CORNER)]
        for c, w, _k, _m in ops:
            intervals = C._subtract(intervals, c - w / 2.0 - C.DOOR_CLEAR, c + w / 2.0 + C.DOOR_CLEAR)
        back = line + sign * C.WALL_BACK
        front = back + sign * C.DEPTH
        band = sorted((back, front + sign * C.AISLE))
        for v in spec.get("volumes") or []:
            # storey 0's only: a basement's furniture under the wall is not in its aisle
            foot = float(v.get("z", 0.0)) - float(v.get("size_z", 0.0)) / 2.0
            if foot < -0.5 or foot > FOOT_MAX:
                continue
            vx0, vx1 = v["x"] - v["size_x"] / 2.0, v["x"] + v["size_x"] / 2.0
            vy0, vy1 = v["y"] - v["size_y"] / 2.0, v["y"] + v["size_y"] / 2.0
            along = (vx0, vx1) if axis == "X" else (vy0, vy1)
            across = (vy0, vy1) if axis == "X" else (vx0, vx1)
            if across[1] <= band[0] + C.EPS or across[0] >= band[1] - C.EPS:
                continue
            if v["size_x"] * v["size_y"] > 400.0:
                continue
            intervals = C._subtract(intervals, along[0] - 0.05, along[1] + 0.05)
        side = {("X", -1): "N", ("X", +1): "S", ("Y", -1): "E", ("Y", +1): "W"}[(axis, sign)]
        for a0, a1 in intervals:
            if a1 - a0 < MIN_RUN:
                continue
            key = (side in back_walls, min(a1 - a0, RUN), a1 - a0)
            if best is None or key > best[0]:
                best = (key, a0, a1, axis, back, sign, side)
    if best is None:
        return [], "no stretch of a solid sales-floor wall is %.1f m clear" % MIN_RUN
    _key, a0, a1, axis, back, sign, side = best
    length = min(a1 - a0, RUN)
    n = max(1, int(math.ceil(length / PIECE - 1e-9)))
    each = length / n
    start = (a0 + a1) / 2.0 - length / 2.0
    cy = back + sign * C.DEPTH / 2.0
    have = {m.get("id") for m in spec.get("materials") or []}
    mat = ("cooler_panel" if "cooler_panel" in have
           else level_design._declare_material(spec, "metal", level_design._PROP_ACOUSTIC["metal"]))
    out = []
    for i in range(n):
        mid = start + (i + 0.5) * each
        if axis == "X":
            vol = {"name": "%s_%d" % (NAME, i), "x": round(mid, 4), "y": round(cy, 4), "z": C.HEIGHT / 2.0,
                   "size_x": round(each, 3), "size_y": C.DEPTH, "size_z": C.HEIGHT}
        else:
            vol = {"name": "%s_%d" % (NAME, i), "x": round(cy, 4), "y": round(mid, 4), "z": C.HEIGHT / 2.0,
                   "size_x": C.DEPTH, "size_y": round(each, 3), "size_z": C.HEIGHT}
        vol.update({"collision": "convex", "material": mat})
        if sign > 0:
            vol["rot_z"] = 180.0
        out.append(vol)
    return out, "the sales floor's %s wall, %d run(s) of %.2f m in a %.2f m stretch" % (side, n, each, a1 - a0)


def has_cooler(spec):
    room = sales_floor(spec)
    return bool(room) and any(str(v.get("name", "")).startswith("cooler_run") and _in_room(v, room["bounds"])
                              for v in spec.get("volumes") or [])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    placed = refused = 0
    import migrate_furnish_recipes
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if sales_floor(d) is None or has_cooler(d):
            continue
        bare = level_design.unfurnished(d)
        vols, why = plan(bare)
        if not vols:
            refused += 1
            print(f"[supermarket_cooler] {os.path.basename(p)}: REFUSED -- {why}")
            continue
        placed += 1
        print(f"[supermarket_cooler] {os.path.basename(p)}: {why}")
        if check:
            continue
        # a material `plan` declared on the bare copy is declared on the spec
        d["materials"] = bare.get("materials", d.get("materials"))
        d["volumes"] = (d.get("volumes") or []) + vols
        migrate_furnish_recipes.migrate(d)
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "need a cooler wall" if check else "given a cooler wall"
    print(f"[supermarket_cooler] {placed} spec(s) {verb}, {refused} refused")
    return 1 if check and placed else 0


if __name__ == "__main__":
    sys.exit(main())
