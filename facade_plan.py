"""A facade's composition, decided for one face over every storey where its openings are chosen (0.238.0; the
factory's roadmap 79 and its `docs/proposals/FACADE_PLANNER.md`).

WHY HERE AND NOT IN THE EMITTER. `_exterior` emits each side of each storey on its own, and `_emit_wall_run` is handed
one run with its openings already placed as fractions of it (`_opening_to_hole`), so nothing downstream of the spec can
align two storeys: it never sees two. A face is decided where its openings are first chosen -- a preset writing a spec,
or a migration over the specs -- and this module is that place. The emitter stays the executor.

WHAT THE LIBRARY WAS, measured (the factory's `docs/findings/facade_census_79/`, on the 102 buildings a themed lot can
draw): of the 169 first-storey openings in its 52 multi-storey buildings, 28 stood over a ground-floor opening; the
Empties, whose presets lay every storey on one list of bays, read 92.9 % through the same instrument. The upper storeys
were authored mirrored about their face's centre (167 of 177 openings) and the ground floors for the rooms behind them
(135 of 321), so while the ground floor holds, stacking and symmetry trade against each other.

THE ROWS. A row is one family's composition, and each names where it came from -- the grammar is not invented here (the
factory's roadmap 79 forbids that, and is right to). The walker's references: "Align repeated architecture where
construction would align it; vary the parts that would actually vary" (the factory's
`docs/reference/HUMAN_AUTHORSHIP_GUIDE.md`), and the Empties' comps (`docs/reference/EMPTIES_COMPS.md`, agreed
2026-10-04): a rowhome is "two windows per storey, stacked on the same bays".

  * `rowhome` -- two bays, each a fixed fraction off the front's centre, wider on a wider house. Was inline in
    `presets.empty_rowhome` (the Empties, 0.174.0); its output is unchanged, to the byte.
  * `midrise` -- round(width / bay) equal bays, at least two, the door in the bay nearest the lobby. Was inline in
    `presets.empty_midrise` (0.213.0, the two-bay floor 0.217.0); unchanged, to the byte.
  * `stack_mirrored` -- the library's upper storeys moved onto the openings below them, in mirrored pairs, within a bay
    (below). The first composition this module applies to buildings it did not write.

STACK_MIRRORED, the rule (`migrate_facade_stack.py` runs it over the specs). Per face, storeys upward, each against
the storey below as it now stands:
  * only an upper-storey WINDOW with no `tag` moves; every ground-floor opening, every door, breach, garage, vault
    or tagged window stays where gameplay put it, and a window keeps its kind, width, height and sill;
  * a window with a partner mirrored about the face's centre (same width) moves only WITH it, onto two openings
    below that are each other's mirror; a window on the centre line only onto an opening on it; any other window
    onto the nearest opening below; each target within `REACH` and taken once;
  * a target is turned down when the window would leave its run (`EDGE_WALLS` wall thicknesses from each end), come
    within `MIN_PIER` of another opening on its storey, or stand over a partition's junction with the wall (a room
    wall in the window) -- the window then tries the next one, and stays when none is left;
  * HELD, never moved: a window a den's drape hangs over (`lights._drapes_window`'s test, on the spec's own volume),
    any window on a wall a fire escape serves (its access opening, `FireEscape.access`), every window of a face whose
    storey extents differ from the storey below's (a setback: the mirror is not the same line), and a window whose
    mirrored partner stays -- tagged, held, or not a window -- since moving one of the two alone would break the
    symmetry the storey was authored with;
  * an Empty (`facade`) is left alone: its row composed it, and its spec is its preset's own output. Run over one,
    the rule would move each rowhome's rear window over its back door -- the preset puts them in the house's two
    bays on purpose.
Measured before it ran (`docs/findings/facade_census_79/predict.py`, its `over sym` row): 46 windows in 22 buildings
move, a median 2.0 m and at most 3.0, none into another room; stacking goes from 28 to 74 of 169 and every mirrored
opening stays mirrored.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import setbacks       # noqa: E402
import spec_loader    # noqa: E402

#: The rows. Each names its source; a value is a call until the walker changes it.
ROWS = {
    "rowhome": {
        "source": "EMPTIES_COMPS.md, Family 1: two window bays a house; was inline in presets.empty_rowhome",
        # a bay's centre, as a fraction of the front off its centre: the wide houses' and the rest
        "offset": 0.22, "offset_narrow": 0.2, "wide_from_m": 6.0,
    },
    "midrise": {
        "source": "URBAN_MIDRISE_COMPS.md: regular windows; presets.MIDRISE_BAY (0.213.0), two-bay floor (0.217.0)",
        "bay_m": 3.2, "min_bays": 2,
    },
}

#: STACK_MIRRORED's dials. REACH: the one bay the library already chose (the mid-rise row's), so a window moves at
#: most a bay. MIN_PIER: the least solid wall left between two openings on a storey. EDGE_WALLS: how many wall
#: thicknesses a window keeps clear of its run's ends (half of one is the corner's own inset, `_emit_wall_run`).
REACH = ROWS["midrise"]["bay_m"]
MIN_PIER = 0.3
EDGE_WALLS = 1.5
#: Two centres this close along a face are one line: the specs' openings are on a 0.5 m grid.
TOL = 0.05
DRAPE_NAME = "window_drape"


def bay_positions(row, width):
    """The bay centres of `row` across a front `width` metres wide, as fractions of the front (-0.5..0.5)."""
    r = ROWS[row]
    if row == "rowhome":
        bay = r["offset"] if float(width) >= r["wide_from_m"] else r["offset_narrow"]
        return [-bay, bay]
    if row == "midrise":
        bays = max(r["min_bays"], int(round(float(width) / r["bay_m"])))
        return [round((i + 0.5) / bays - 0.5, 4) for i in range(bays)]
    raise KeyError(row)


def nearest(positions, toward):
    """The index of the position nearest `toward` (the first of a tie)."""
    return min(range(len(positions)), key=lambda i: abs(positions[i] - float(toward)))


def _near(x, xs):
    return any(abs(x - y) <= TOL for y in xs)


def _run(spec, side, story):
    """(run length, centre along the wall, wall line across it) of `side` on `story`, centrelines."""
    x0, y0, x1, y1 = setbacks.storey_extent(spec, story)
    if side in ("N", "S"):
        return x1 - x0, (x0 + x1) / 2.0, (y1 if side == "N" else y0)
    return y1 - y0, (y0 + y1) / 2.0, (x1 if side == "E" else x0)


def _junctions(spec, side, story, centre, line):
    """Where the storey's partitions meet `side`, along the wall from its centre."""
    wt = float(spec.wall_thick)
    out = []
    for p in spec.partitions:
        if int(p.story) != story:
            continue
        a, b = sorted((float(p.start), float(p.end)))
        if side in ("N", "S") and p.axis == "Y":
            if (side == "N" and b >= line - wt) or (side == "S" and a <= line + wt):
                out.append(float(p.pos) - centre)
        elif side in ("E", "W") and p.axis == "X":
            if (side == "E" and b >= line - wt) or (side == "W" and a <= line + wt):
                out.append(float(p.pos) - centre)
    return out


def _held(spec, d, side, story, u, w, centre, line, z):
    """Why a window must not move, or None: a drape hangs over it, or a fire escape serves its wall."""
    for fe in spec.fire_escapes:
        if fe.wall == side and story in [int(s) for s in fe.served_stories]:
            return "a fire escape serves its wall"
    along = "x" if side in ("N", "S") else "y"
    across = "y" if side in ("N", "S") else "x"
    size = "size_x" if side in ("N", "S") else "size_y"
    for v in d.get("volumes") or []:
        if DRAPE_NAME not in str(v.get("name", "")):
            continue
        if (abs(float(v.get(along, 0.0)) - (centre + u)) <= max(float(v.get(size, 0.0)), w) / 2.0
                and abs(float(v.get(across, 0.0)) - line) <= 1.0
                and abs(float(v.get("z", 0.0)) - z) <= float(v.get("size_z", 0.0)) / 2.0 + 1.0):
            return "a drape hangs over it"
    return None


def _fits(t, w, others, run, wt, junctions):
    if abs(t) + w / 2.0 > run / 2.0 - EDGE_WALLS * wt + 1e-9:
        return "leaves the run"
    for (u, ow) in others:
        if abs(t - u) < (w + ow) / 2.0 + MIN_PIER - 1e-9:
            return "too near another opening"
    for j in junctions:
        if abs(t - j) < w / 2.0 + wt / 2.0:
            return "over a partition junction"
    return None


def stack_mirrored(d, reach=REACH):
    """Move `d`'s upper-storey windows onto the openings below them, in mirrored pairs (the module's docstring), in
    place. Returns ``(moves, held)``: ``moves`` [(wall, story, from_u, to_u)] in metres along the wall from its
    centre, ``held`` [(wall, story, u, why)]."""
    if d.get("facade"):
        return [], []
    spec = spec_loader.spec_from_dict(d)
    grid = float(spec.grid)
    wt = float(spec.wall_thick)
    H = float(spec.story_height)

    def snap(v):
        return round(v / grid) * grid

    rows = {}
    for i, w in enumerate(d.get("ext_walls") or []):
        rows[(w["wall"], int(w["story"]))] = (i, w)
    moves, held = [], []
    final = {}          # (side, story) -> the storey's opening positions as they now stand
    for side in ("N", "S", "E", "W"):
        stories = sorted(s for (sd, s) in rows if sd == side)
        for story in stories:
            if story < 1 or (side, story - 1) not in rows:
                continue
            i, wd = rows[(side, story)]
            ib, _wb = rows[(side, story - 1)]
            run, centre, line = _run(spec, side, story)
            run_b, centre_b, _l = _run(spec, side, story - 1)
            ops = spec.ext_walls[i].openings
            here = [(snap(float(o.pos) * run), float(o.resolved()["width"]), o) for o in ops]
            # the storey below AS IT NOW STANDS: a third storey stacks over the second's moved windows
            below = final.get((side, story - 1),
                              [snap(float(o.pos) * run_b) for o in spec.ext_walls[ib].openings])
            movable, fixed = [], []
            for j, (u, w, o) in enumerate(here):
                if o.kind != "window" or o.tag:
                    fixed.append((u, w))
                    continue
                r = o.resolved()
                z = story * H + r["sill"] + r["height"] / 2.0
                why = None
                if abs(run - run_b) > 1e-6 or abs(centre - centre_b) > 1e-6:
                    why = "the storey below stands on another extent"
                else:
                    why = _held(spec, d, side, story, u, w, centre, line, z)
                if why:
                    held.append((side, story, u, why))
                    fixed.append((u, w))
                else:
                    movable.append((j, u, w))
            # a window whose mirrored partner stays stays with it
            keep = []
            for (j, u, w) in movable:
                if abs(u) > TOL and any(abs(fu + u) <= TOL and abs(fw - w) < 1e-6 for (fu, fw) in fixed):
                    held.append((side, story, u, "its mirrored partner stays"))
                    fixed.append((u, w))
                else:
                    keep.append((j, u, w))
            movable = keep
            if not movable:
                final[(side, story)] = [u for (u, _w, _o) in here]
                continue
            junctions = _junctions(spec, side, story, centre, line)
            # pair the movable windows: mirrored partners of one width, the centre line alone, the rest alone
            groups, done = [], set()
            for k, (j, u, w) in enumerate(movable):
                if k in done:
                    continue
                done.add(k)
                if abs(u) <= TOL:
                    groups.append(((j,), (u,), w, "centre"))
                    continue
                m = next((m for m, (j2, u2, w2) in enumerate(movable)
                          if m not in done and abs(u2 + u) <= TOL and abs(w2 - w) < 1e-6), None)
                if m is None:
                    groups.append(((j,), (u,), w, "alone"))
                else:
                    done.add(m)
                    groups.append(((j, movable[m][0]), (u, movable[m][1]), w, "pair"))
            placed = list(fixed)
            taken = set()
            new_u = {}
            for (js, us, w, how) in groups:
                if how == "pair":
                    lo_u = min(us)
                    cands = sorted((abs(b - lo_u), b) for b in below
                                   if b < -TOL and _near(-b, below) and abs(b - lo_u) <= reach + 1e-9)
                    targets = [(b, -b) for (_d, b) in cands]
                elif how == "centre":
                    targets = [(b,) for b in below if abs(b) <= TOL]
                else:
                    targets = [(b,) for (_d, b) in sorted((abs(b - us[0]), b) for b in below
                                                          if abs(b - us[0]) <= reach + 1e-9)]
                best = None
                for ts in targets:
                    if any(round(t, 3) in taken for t in ts):
                        continue
                    if all(_fits(t, w, placed + [(t2, w) for t2 in ts if t2 is not t], run, wt, junctions) is None
                           for t in ts):
                        best = ts
                        break
                if best is None:
                    placed += [(u, w) for u in us]
                    continue
                pairs = list(zip(sorted(zip(us, js)), sorted(best)))
                for ((u, j), t) in pairs:
                    taken.add(round(t, 3))
                    placed.append((t, w))
                    if abs(t - u) > 1e-9:
                        new_u[j] = (u, t)
            for j, (u, t) in sorted(new_u.items()):
                pos = round(t / run, 6)
                assert abs(snap(pos * run) - t) < 1e-9, (side, story, t, pos)
                wd["openings"][j]["pos"] = pos
                moves.append((side, story, u, t))
            final[(side, story)] = [new_u[j][1] if j in new_u else u for j, (u, _w, _o) in enumerate(here)]
    return moves, held
