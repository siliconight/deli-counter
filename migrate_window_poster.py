#!/usr/bin/env python3
"""
migrate_window_poster.py  --  a store tapes a pair of sale posters in its window
===============================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.170.0:
every convenience store (`migrate_slush_machine.is_store`) with a storefront
tapes one `window_poster` -- Zoo's `poster_wall` in its `store` family, two
sale sheets -- inside its shop-front glass, facing the street.

The walker, 2026-09-29, choosing where posters go: "store windows and walls".
The walls were 0.163.0 (`poster_wall_store`, OFF the glass: a run hung inside
a storefront shows the street its back); the windows waited, as that
release's note says, for "a rule of its own (the window sign's)". This is
that rule, and the placement guide's (docs/reference/): a "sparse window:
one or two notices preserve visibility through the glass", "arranged at eye
level".

THE RULE, in the spec's frame (metres, the footprint centred on 0), the
window sign's wherever it can be (`migrate_window_sign`):
  * the wall: the storey-0 `storefront_glass` exterior wall whose line is an
    edge of the sales floor, and its doors inside the sales floor's span,
    nearest the sales floor's centre first;
  * along it: beside a door -- half the lit sign box (the door +
    `lights._SIGN_PAD`) + `GAP` + half the pair -- on either side, clear of
    every opening and `GAP` clear of the window sign; none: REFUSED and
    reported, never forced;
  * across it: `INSET` inside the wall's inner face -- taped to the glass,
    where the sign hangs 15 cm in on its chains;
  * up: the band's centre on the camera's eye (`agent_contract.eye_height`),
    where the wall runs hang;
  * facing out: a volume long in x faces -y and one long in y faces -x
    (`migrate_slush_machine._front`), `rot_z` 180 turns either round.

    python migrate_window_poster.py            # write specs/
    python migrate_window_poster.py --check    # report only; exit 1 if any
    python migrate_window_poster.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract  # noqa: E402
import lights  # noqa: E402
import migrate_slush_machine  # noqa: E402
import migrate_window_sign as SIGN  # noqa: E402

NAME = "window_poster"
# w, d, h: two of Zoo's 0.46 m sale sheets and the gap between them; the
# genome's default depth; `poster_wall_forms.band_height("store")`
SIZE = (1.0, 0.01, 0.6)
GAP = 0.3                        # to a door's sign box, and to the window sign
INSET = 0.03                     # inside the wall's inner face: on the glass
VARIANTS = 4                     # the poster pieces' own count
FAMILY = "store"

#: Paper, as the specs that hang a poster run define it.
MATERIAL = {"id": "paper", "acoustic": "Wood", "absorption": 0.22, "damping": 0.18}


def _define_material(d):
    mats = d.setdefault("materials", [])
    if any(m.get("id") == MATERIAL["id"] for m in mats):
        return False
    mats.append(dict(MATERIAL))
    return True


def plan(d):
    """``(volume, why)``: the window poster this spec should tape up, or
    None and the reason it cannot."""
    room = next((r for r in d.get("rooms") or [] if r.get("id") == SIGN.ROOM
                 and int(r.get("story", 0) or 0) == 0), None)
    if room is None or not room.get("bounds"):
        return None, "no storey-0 sales floor"
    x0, y0, x1, y1 = room["bounds"]
    wt = float(d.get("wall_thick") or 0.3)
    grid = SIGN._grid(d)
    w, dp, h = SIZE
    z = agent_contract.eye_height()
    sign = next((v for v in d.get("volumes") or [] if v.get("name") == SIGN.NAME), None)
    for wall in d.get("ext_walls") or []:
        if int(wall.get("story", 0) or 0) != 0 or wall.get("material") != SIGN.STOREFRONT:
            continue
        axis, line, run, (ix, iy) = SIGN._wall_geometry(d, wall["wall"])
        edge = (y0 if wall["wall"] == "S" else y1) if axis == 0 else (x0 if wall["wall"] == "W" else x1)
        if abs(edge - line) > wt:
            continue                                   # not the sales floor's wall
        lo, hi = (x0, x1) if axis == 0 else (y0, y1)
        centre = (lo + hi) / 2.0
        ops = [(SIGN._snap(float(o.get("pos", 0.0)) * run, grid), float(o.get("width", 1.0)), o.get("kind"))
               for o in wall.get("openings") or []]
        # the window sign's span along this wall, when it hangs on it
        taken = None
        if sign is not None:
            su = sign["x"] if axis == 0 else sign["y"]
            sw = max(sign["size_x"], sign["size_y"])
            across = sign["y"] if axis == 0 else sign["x"]
            if abs(across - line) < wt + 1.0:
                taken = (su - sw / 2.0 - GAP, su + sw / 2.0 + GAP)
        doors = sorted([o for o in ops if o[2] == "door" and lo <= o[0] <= hi],
                       key=lambda o: abs(o[0] - centre))
        for u, dw, _k in doors:
            toward = 1.0 if centre >= u else -1.0
            # the far side of the door from the sales floor's centre first:
            # the sign took the near one
            for side in (-toward, toward):
                c = u + side * ((dw + lights._SIGN_PAD) / 2.0 + GAP + w / 2.0)
                a, b = c - w / 2.0, c + w / 2.0
                if a < lo + wt or b > hi - wt:
                    continue
                if any(a < ou + ow / 2.0 and b > ou - ow / 2.0 for ou, ow, _k2 in ops):
                    continue
                if taken is not None and a < taken[1] and b > taken[0]:
                    continue
                inset = wt / 2.0 + INSET + dp / 2.0
                x, y = (c, line + iy * inset) if axis == 0 else (line + ix * inset, c)
                vol = {"name": NAME, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3),
                       "size_x": w if axis == 0 else dp, "size_y": dp if axis == 0 else w,
                       "size_z": h, "collision": "none", "material": MATERIAL["id"],
                       "form": FAMILY,
                       "variant": zlib.crc32((str(d.get("name", "")) + "|window_poster").encode()) % VARIANTS}
                # out of the building: S and W already face out (-y, -x)
                if wall["wall"] in ("N", "E"):
                    vol["rot_z"] = 180.0
                return vol, None
        return None, "no clear glass beside an entrance on the %s storefront" % wall["wall"]
    return None, "no storefront on the sales floor"


def migrate(d):
    """``(changed, why)`` for one spec dict, in place."""
    if not migrate_slush_machine.is_store(d):
        return False, None
    vols = d.get("volumes") or []
    have = [i for i, v in enumerate(vols) if v.get("name") == NAME]
    if have:
        changed = _define_material(d)
        bare = dict(d, volumes=[v for v in vols if v.get("name") != NAME])
        want, _why = plan(bare)
        if want is not None and vols[have[0]] != want:
            vols[have[0]] = want
            changed = True
        return changed, None
    vol, why = plan(d)
    if vol is None:
        return False, why
    _define_material(d)
    # directly after the window sign when there is one, else before the
    # pieces `furnish` wrote (the sign's own reason: a refurnish keeps every
    # other volume in order and appends its own)
    vols = d.setdefault("volumes", [])
    at = next((i + 1 for i, v in enumerate(vols) if v.get("name") == SIGN.NAME), None)
    if at is None:
        import level_design
        import migrate_furnish_recipes
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
            print(f"[window_poster] {os.path.basename(p)}: REFUSED -- {why}")
        if not changed:
            continue
        n += 1
        v = next(v for v in d["volumes"] if v.get("name") == NAME)
        print(f"[window_poster] {os.path.basename(p)}: at ({v['x']}, {v['y']}, {v['z']}) "
              f"variant {v['variant']}{' rot 180' if v.get('rot_z') else ''}")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print(f"[window_poster] {n} spec(s) {'need' if check else 'given'} a window poster or its material")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
