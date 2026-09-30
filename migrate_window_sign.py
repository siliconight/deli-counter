#!/usr/bin/env python3
"""
migrate_window_sign.py  --  a store hangs a beer sign in its window
===================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.160.0 /
Zoo 1.27.0: every convenience store (`migrate_slush_machine.is_store`) with a
storefront hangs one `window_sign` -- Zoo's `neon_sign` in its `window`
form, an invented beer in red or blue -- inside its shop-front glass, beside
the entrance, facing the street.

The walker, 2026-09-29: "add the warm counter accent and the window sign
next", from their 1990s lighting reference on the convenience store at night:
"a small red or blue window sign ... an accent against the fluorescent
interior". Emissive, no light of its own: the reference wants the tube to be
the bright object, and a light would claim a per-mesh budget slot in a room
that has spent them (cold runs 9105-9107).

THE RULE, in the spec's frame (metres, the footprint centred on 0):
  * the wall: the storey-0 `storefront_glass` exterior wall whose line is an
    edge of the sales floor, and one of its DOORS inside the sales floor's
    span along it (the one nearest the sales floor's centre);
  * along it: beside that door, toward the sales floor's centre -- half the
    LIT SIGN BOX's width (the door + `lights._SIGN_PAD`, 0.160.0: the box
    over the entry hid the sign's door end in cold run 9113, because this
    measured from the door opening and never asked about the box) + `GAP` +
    half the sign -- or the other side when that
    overlaps another opening or leaves the sales floor; neither: REFUSED and
    reported, never forced;
  * across it: `INSET` inside the wall's inner face;
  * up: the slot's top IS the top of the glass (Zoo's `SF_GLASS_TOP`, 3.0,
    or 0.4 under the storey's top when that is lower) -- Zoo's window form
    spends the top 12% of the slot on the two chains, so they end at the
    window's head, where a real one hangs from its hooks, and not in the air;
  * facing out: a volume long in x faces -y and one long in y faces -x
    (`migrate_slush_machine._front`), `rot_z` 180 turns either round.

    python migrate_window_sign.py            # write specs/
    python migrate_window_sign.py --check    # report only; exit 1 if any
    python migrate_window_sign.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lights  # noqa: E402
import migrate_slush_machine  # noqa: E402

NAME = "window_sign"
# w, d, h: the genome's least depth. 1.2 x 0.6 letters every beer at 15.5 cm
# or more; 1.0 x 0.5, the genome's least, managed 12.9 (Zoo 1.27.0's plans).
SIZE = (1.2, 0.06, 0.6)
GAP = 0.3                        # between the door's jamb and the sign
INSET = 0.15                     # inside the wall's inner face
GLASS_TOP = 3.0                  # Zoo `arch.SF_GLASS_TOP`
HEAD_MIN = 0.4                   # Zoo `arch.SF_HEAD_MIN`
NAMES = 6                        # Zoo `club_names.WINDOW_NAMES`
STOREFRONT = "storefront_glass"
ROOM = "sales_floor"


def _wall_geometry(d, wall):
    """(axis, line, run, inward): axis 0 = the wall runs along x."""
    fx, fy = float(d.get("footprint_x", 0.0)), float(d.get("footprint_y", 0.0))
    return {"S": (0, -fy / 2.0, fx, (0.0, 1.0)), "N": (0, fy / 2.0, fx, (0.0, -1.0)),
            "W": (1, -fx / 2.0, fy, (1.0, 0.0)), "E": (1, fx / 2.0, fy, (-1.0, 0.0))}[wall]


def _snap(v, grid):
    return round(v / grid) * grid if grid else v


def plan(d):
    """``(volume, why)``: the window sign this spec should hang, or None and
    the reason it cannot."""
    room = next((r for r in d.get("rooms") or [] if r.get("id") == ROOM
                 and int(r.get("story", 0) or 0) == 0), None)
    if room is None or not room.get("bounds"):
        return None, "no storey-0 sales floor"
    x0, y0, x1, y1 = room["bounds"]
    wt = float(d.get("wall_thick") or 0.3)
    grid = d.get("grid")
    w, dp, h = SIZE
    sh = float(d.get("story_height") or 3.6)
    z = min(GLASS_TOP, sh - HEAD_MIN) - h / 2.0
    for wall in d.get("ext_walls") or []:
        if int(wall.get("story", 0) or 0) != 0 or wall.get("material") != STOREFRONT:
            continue
        axis, line, run, (ix, iy) = _wall_geometry(d, wall["wall"])
        edge = (y0 if wall["wall"] == "S" else y1) if axis == 0 else (x0 if wall["wall"] == "W" else x1)
        if abs(edge - line) > wt:
            continue                                   # not the sales floor's wall
        lo, hi = (x0, x1) if axis == 0 else (y0, y1)
        centre = (lo + hi) / 2.0
        ops = [(_snap(float(o.get("pos", 0.0)) * run, grid), float(o.get("width", 1.0)), o.get("kind"),
                float(o.get("pos", 0.0)) * run)
               for o in wall.get("openings") or []]
        doors = sorted([o for o in ops if o[2] == "door" and lo <= o[0] <= hi],
                       key=lambda o: abs(o[0] - centre))
        for u, dw, _k, u_raw in doors:
            toward = 1.0 if centre >= u else -1.0
            for side in (toward, -toward):
                # TWO CENTRES FOR ONE DOOR: the module is built at the grid-
                # snapped position, and `lights._storefront_sign` centres the
                # box on the UNSNAPPED one (gas_station_a02: -6.00 and -5.76).
                # Clear the door and the box, each where it actually is.
                reach = max(side * u + dw / 2.0, side * u_raw + (dw + lights._SIGN_PAD) / 2.0)
                c = side * (reach + GAP + w / 2.0)
                a, b = c - w / 2.0, c + w / 2.0
                if a < lo + wt or b > hi - wt:
                    continue
                if any(a < ou + ow / 2.0 and b > ou - ow / 2.0 for ou, ow, _k2, _r in ops):
                    continue
                inset = wt / 2.0 + INSET + dp / 2.0
                x, y = (c, line + iy * inset) if axis == 0 else (line + ix * inset, c)
                vol = {"name": NAME, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3),
                       "size_x": w if axis == 0 else dp, "size_y": dp if axis == 0 else w,
                       "size_z": h, "collision": "none", "material": MATERIAL["id"],
                       "form": "window",
                       "variant": zlib.crc32(str(d.get("name", "")).encode()) % NAMES}
                # out of the building: S and W already face out (-y, -x)
                if wall["wall"] in ("N", "E"):
                    vol["rot_z"] = 180.0
                return vol, None
        return None, "no room beside an entrance on the %s storefront" % wall["wall"]
    return None, "no storefront on the sales floor"


#: The sign's material, as the 166 specs that define it do. A store's own
#: table need not carry it -- none of the nine did, and `validate` refuses a
#: volume naming a material its spec does not define (cr_gas, first refused
#: by the 0.160.0 commit gate).
MATERIAL = {"id": "metal_painted", "acoustic": "Metal", "absorption": 0.25, "damping": 0.2}


def _define_material(d):
    mats = d.setdefault("materials", [])
    if any(m.get("id") == MATERIAL["id"] for m in mats):
        return False
    mats.append(dict(MATERIAL))
    return True


def migrate(d):
    """``(changed, why)`` for one spec dict, in place."""
    if not migrate_slush_machine.is_store(d):
        return False, None
    vols = d.get("volumes") or []
    have = [i for i, v in enumerate(vols) if v.get("name") == NAME]
    if have:
        # RE-PLACED where the rule has moved (0.160.0's sign-box clearance),
        # in its own slot in the list, so nothing around it moves
        changed = _define_material(d)
        want, _why = plan(d)
        if want is not None and vols[have[0]] != want:
            vols[have[0]] = want
            changed = True
        return changed, None
    _define_material(d)
    vol, why = plan(d)
    if vol is None:
        return False, why
    # BEFORE the pieces `furnish` wrote, not after them. A refurnish keeps
    # every other volume in order and appends its own, so a sign appended
    # last came back 14-18 places earlier and the spec stopped being a fixed
    # point of `migrate_furnish_recipes` (test_club_fixtures) by order alone.
    import level_design
    import migrate_furnish_recipes
    vols = d.setdefault("volumes", [])
    tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
    at = max((i + 1 for i, v in enumerate(vols)
              if not migrate_furnish_recipes.furnished_by_this_pass(v, tags)), default=0)
    vols.insert(at, vol)
    return True, None


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
        changed, why = migrate(d)
        if why:
            print(f"[window_sign] {os.path.basename(p)}: REFUSED -- {why}")
        if not changed:
            continue
        n += 1
        v = next(v for v in d["volumes"] if v.get("name") == NAME)
        print(f"[window_sign] {os.path.basename(p)}: at ({v['x']}, {v['y']}, {v['z']}) "
              f"variant {v['variant']}{' rot 180' if v.get('rot_z') else ''}")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print(f"[window_sign] {n} spec(s) {'need' if check else 'given'} a window sign or its material")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
