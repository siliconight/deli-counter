#!/usr/bin/env python3
"""
migrate_slush_machine.py  --  a convenience store has its frozen drink station
===============================================================================
One-shot, idempotent migration over specs/*.json for Zoo 1.15.0's
`slush_machine`: the twin-hopper frozen drink station, syrup rail and cup
tubes. The walker, 2026-09-28: "do the slush machine next".

WHY. No spec places one: not a `slush`, `frozen` or `drink` volume in the
library. The proposal (docs/proposals/GAS_STATION_SHOP.md) calls it "the
most SATURATED object in a 1990s convenience store ... A grey box in that
corner loses the whole read", so every convenience store gets one -- a spec
whose `sales_floor` carries `gondola_aisle` volumes, the snack aisles Deli
Counter 0.149.0 named (nine specs). The supermarkets, card shop and marina
have sales floors and no gondola aisles, and are left alone.

THE RULE, measured per spec rather than authored per spec:

  * the WALLS: each side of the `sales_floor` room. A glazed exterior wall
    (`level_design._glazed_walls`: every store's storefront) is skipped --
    a 2 m station stands against a wall, not across a shop window;
  * the OPENINGS: exterior ones by `level_design._ext_openings`, a
    partition's by its own `pos * run` from its centre, each kept
    `_FURNISH_OPENING_CLEAR` either side, the furnishing pass's number;
  * the AISLE: no authored volume within `island_aisle_width()` (1.25 m) of
    the station, on any side. It is a per-axis margin, so a box, not a
    radius (CLAUDE.md: over-reports near a corner by up to sqrt(2)); that
    only ever refuses a spot, never admits a bad one. It is what keeps the
    station out of a register counter's staff aisle and queue, off a coffee
    island's circulation, and out of the reach-in cooler's door swing;
  * MARKERS: none within `MARKER_CLEAR` of the footprint -- a spawn inside
    a machine is not a spawn;
  * FURNITURE the furnishing pass wrote is not an obstacle: the room is
    refurnished round the station after (below);
  * of every place left, the one NEAREST the coffee island -- the drinks go
    together -- or, in a store without one, the register counter. Otherwise
    the spec is REFUSED and reported, not forced.

FACING, the cooler wall's measured rule (`migrate_cooler_wall.py`): Zoo
builds the front on -Y; a volume long in x is emitted unturned and faces
the spec's -y, one long in y is turned by `prop_species.long_axis_first`
and faces -x. So the station needs `rot_z` 180 only when its room is on the
+y or +x side of its wall.

THE ROOM IS REFURNISHED AFTER, because the library is a fixed point of its
furnishing pass (`test_club_fixtures`'s fixed-point test): a station is new
input to that pass. Only the specs given a station are refurnished.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrate_slush_machine.py            # write specs/
    python migrate_slush_machine.py --check    # report only; exit 1 if any
    python migrate_slush_machine.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402

NAME = "slush_machine"
ROOM = "sales_floor"
#: Zoo's `slush_machine_forms.DC_SIZES[0]`: 1.6 wide holds two barrels and
#: the six-bottle rail (Zoo's `need(2, True)` is 1.52).
WIDTH, DEPTH, HEIGHT = 1.6, 0.7, 2.0
CORNER = 0.10
MARKER_CLEAR = 0.5
#: A volume whose underside is above the station is not in its way.
OVERHEAD = HEIGHT
#: The site pads a building stands on are not furniture (the cooler wall's).
PAD_AREA = 400.0
EPS = 1e-6


def is_store(spec):
    rooms = {r.get("id") for r in spec.get("rooms") or []}
    return ROOM in rooms and any(str(v.get("name", "")).startswith("gondola_aisle")
                                 for v in spec.get("volumes") or [])


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


def _obstacles(spec):
    """Authored volumes on the floor, as ``(x0, y0, x1, y1)``."""
    tags = {level_design._room_tag(r) for r in spec.get("rooms") or []}
    out = []
    for v in spec.get("volumes") or []:
        if migrate_furnish_recipes.furnished_by_this_pass(v, tags):
            continue
        if v["size_x"] * v["size_y"] > PAD_AREA:
            continue
        if float(v.get("z", 0.0)) - float(v["size_z"]) / 2.0 >= OVERHEAD:
            continue
        out.append((v["x"] - v["size_x"] / 2.0, v["y"] - v["size_y"] / 2.0,
                    v["x"] + v["size_x"] / 2.0, v["y"] + v["size_y"] / 2.0))
    return out


def _anchor(spec):
    vols = {v["name"]: v for v in spec.get("volumes") or []}
    for name in ("coffee_island", "register_counter"):
        if name in vols:
            return name, (vols[name]["x"], vols[name]["y"])
    return None, None


def _walls(spec, room):
    """``[(axis, line, lo, hi, sign, ext)]``: each side of ``room``. ``axis``
    'X' is a wall along x at y = ``line``; ``sign`` is the side the room is
    on; ``ext`` the compass letter when the side is an exterior wall."""
    x0, y0, x1, y1 = room["bounds"]
    hx = float(spec.get("footprint_x", 0.0)) / 2.0
    hy = float(spec.get("footprint_y", 0.0)) / 2.0

    def ext(value, half, lo_name, hi_name):
        if not half or abs(abs(value) - half) >= level_design._FURNISH_EXT_KEEPOUT:
            return None
        return lo_name if value < 0 else hi_name
    return [("X", y0, x0, x1, +1, ext(y0, hy, "S", "N")),
            ("X", y1, x0, x1, -1, ext(y1, hy, "S", "N")),
            ("Y", x0, y0, y1, +1, ext(x0, hx, "W", "E")),
            ("Y", x1, y0, y1, -1, ext(x1, hx, "W", "E"))]


def plan_station(spec):
    """``(volume, report)``: the station this spec should carry, or
    ``(None, why)``."""
    room = next((r for r in spec.get("rooms") or [] if r.get("id") == ROOM), None)
    if room is None:
        return None, "no %s room" % ROOM
    story = room.get("story", 0)
    openings = level_design._ext_openings(spec, story)
    if openings is None:
        return None, "the storey has a setback; its walls are not the footprint"
    glazed = level_design._glazed_walls(spec, story)
    aisle = level_design.island_aisle_width()
    clear = level_design._FURNISH_OPENING_CLEAR
    back_off = float(spec.get("wall_thick") or 0.3) / 2.0 + level_design._WALL_PIECE_AIR
    obstacles = _obstacles(spec)
    marks = [(float(m["x"]), float(m["y"])) for m in spec.get("markers") or []
             if "x" in m and "y" in m and int(m.get("story", 0) or 0) == int(story or 0)]
    anchor_name, anchor = _anchor(spec)
    best = None
    for k, (axis, line, lo, hi, sign, ext) in enumerate(_walls(spec, room)):
        if ext and ext in glazed:
            continue
        intervals = [(lo + CORNER, hi - CORNER)]
        if ext:
            for c, hw in openings.get(ext, ()):
                intervals = _subtract(intervals, c - hw - clear, c + hw + clear)
        for p in spec.get("partitions") or []:
            if int(p.get("story", 0) or 0) != int(story or 0):
                continue
            if p.get("axis") != axis or abs(float(p.get("pos", 0.0)) - line) > EPS:
                continue
            s, e = float(p["start"]), float(p["end"])
            mid, run = (s + e) / 2.0, e - s
            for op in p.get("openings") or []:
                c = mid + float(op.get("pos", 0.0)) * run
                hw = float(op.get("width") or 1.0) / 2.0
                intervals = _subtract(intervals, c - hw - clear, c + hw + clear)
        back = line + sign * back_off
        front = back + sign * DEPTH
        across = sorted((back, front))
        for bx0, by0, bx1, by1 in obstacles:
            along_b = (bx0, bx1) if axis == "X" else (by0, by1)
            across_b = (by0, by1) if axis == "X" else (bx0, bx1)
            if across_b[1] + aisle <= across[0] + EPS or across_b[0] - aisle >= across[1] - EPS:
                continue
            intervals = _subtract(intervals, along_b[0] - aisle, along_b[1] + aisle)
        for mx, my in marks:
            m_along, m_across = (mx, my) if axis == "X" else (my, mx)
            if across[0] - MARKER_CLEAR < m_across < across[1] + MARKER_CLEAR:
                intervals = _subtract(intervals, m_along - MARKER_CLEAR, m_along + MARKER_CLEAR)
        cy = (back + front) / 2.0
        for a, b in intervals:
            if b - a < WIDTH - EPS:
                continue
            lo_c, hi_c = a + WIDTH / 2.0, b - WIDTH / 2.0
            if anchor is None:
                c = (lo_c + hi_c) / 2.0
                dist = 0.0
            else:
                ax, ay = anchor
                want = ax if axis == "X" else ay
                c = min(max(want, lo_c), hi_c)
                px, py = (c, cy) if axis == "X" else (cy, c)
                dist = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            cand = (round(dist, 6), k, c, axis, cy, sign, ext)
            if best is None or cand < best:
                best = cand
    if best is None:
        return None, "no stretch of a solid %s wall is %.1f m clear with a %.2f m aisle" % (ROOM, WIDTH, aisle)
    dist, _k, c, axis, cy, sign, ext = best
    if axis == "X":
        vol = {"name": NAME, "x": round(c, 4), "y": round(cy, 4), "z": HEIGHT / 2.0,
               "size_x": WIDTH, "size_y": DEPTH, "size_z": HEIGHT}
    else:
        vol = {"name": NAME, "x": round(cy, 4), "y": round(c, 4), "z": HEIGHT / 2.0,
               "size_x": DEPTH, "size_y": WIDTH, "size_z": HEIGHT}
    # THE MATERIAL MUST BE DECLARED (the cooler wall's lesson: the validator
    # refuses an undeclared id). Zoo's recipe builds its own steel, glass
    # and glow whatever the slot says; this is the slot's label and its
    # acoustics.
    mat = level_design._declare_material(spec, "metal", level_design._PROP_ACOUSTIC["metal"])
    vol.update({"collision": "convex", "material": mat})
    if sign > 0:
        vol["rot_z"] = 180.0
    where = ("%s wall" % ext) if ext else "partition"
    return vol, "%s side at %s = %.2f, %.2f m from the %s" % (
        where, "y" if axis == "X" else "x", vol["y"] if axis == "X" else vol["x"], dist, anchor_name)


def migrate(d):
    """Place the station in one store spec dict and refurnish it: ``(volume
    or None, why)``. A spec that has one, or is not a store, is untouched."""
    if not is_store(d):
        return None, "not a convenience store"
    if any(v.get("name") == NAME for v in d.get("volumes") or []):
        return None, "already has one"
    vol, why = plan_station(d)
    if vol is None:
        return None, why
    d["volumes"].append(vol)
    migrate_furnish_recipes.migrate(d)
    return vol, why


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
        if not is_store(d) or any(v.get("name") == NAME for v in d.get("volumes") or []):
            continue
        vol, why = (plan_station(d) if check else migrate(d))
        if vol is None:
            refused += 1
            print(f"[slush_machine] {os.path.basename(p)}: REFUSED -- {why}")
            continue
        placed += 1
        print(f"[slush_machine] {os.path.basename(p)}: {why}")
        if check:
            continue
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "need a slush station" if check else "given a slush station"
    print(f"[slush_machine] {placed} spec(s) {verb}, {refused} refused")
    return 1 if check and placed else 0


if __name__ == "__main__":
    sys.exit(main())
