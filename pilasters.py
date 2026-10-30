"""A civic building's pilasters: where Zoo's `wall_pilaster` (>= 1.150.0) stands on its walls (0.294.0, factory
roadmap 324).

The walker, 2026-10-29, of the game's vertical slice: "Things still look simple, and computer made", and of the
target, "detail and placement of hard surfaces". The slice's bank had a 22 m flank of blank stucco between its
corners. Two shapes were refused on the way, and the reasons decide this one:

  * a pilaster as a Patina cover stood proud of the wall with no collider -- geometry a body walks into -- and was
    withdrawn for it (Level Factory's Patina adapter);
  * piers carved into the wall modules (Zoo's `arch.relief_parts`) can stand only on a module seam, and the storeys
    share almost none: each is tiled round its own openings, so on the bank's east side the only seams the ground
    and first storeys share are at its far end, and a pier at the bay line would jog at the floor line (the factory's
    docs/findings/slice_look/).

So a pilaster is a solid of its own, full height at a line this module chooses, with a collider.

WHERE, in the building's frame (x east, y north, z up; a wall's centre line on the footprint's edge, its outer face
`wall_thick / 2` beyond; an opening at `pos * run` from its wall's centre, as `_opening_to_hole` puts it):

  * on a CIVIC building (`CIVIC_WORDS` in its name -- the bank, credit union, courthouse, library, post office: the
    buildings whose front is meant to look built to last) that is not an Empty, and whose storeys above ground all
    stand on one extent (a setback storey is not a wall a pier can run up);
  * on each side, every storey's openings are pooled, and the bays are laid between ANCHORS -- the wall's ends and
    each opening's centre (`lines`): one pier midway between two openings, the line a pair of windows is read about,
    and every interval divided evenly so no bay is longer than `MAX_BAY`; no pier within `OPENING_CLEAR` of an
    opening or `CORNER_CLEAR` of a corner (the quoins are there);
  * each stands `PROUD` off the outer face, its back `BURY` into the wall so no face lies on the wall's, from grade
    to the top of the top storey's walls; its front -- the module's local -Y -- faces out (a slot's rotation turns
    the module's +Y onto its bearing, so the front faces `rot + 180`).

CHOSEN, not read: 0.6 m wide and a hand proud is a pilaster's proportion on a two- or three-storey commercial front;
`MAX_BAY` 6.5 m is a bay of one or two windows. Pure: no Blender, so every number here is tested without a build.
"""
from __future__ import annotations

import math

CIVIC_WORDS = ("bank", "credit", "courthouse", "landmark", "municipal", "library", "post_office")
PIER_W = 0.6
PROUD = 0.08
BURY = 0.02
#: from a pier's edge to an opening's, and from a corner (the wall's outer edge) to a pier's
OPENING_CLEAR = 0.4
CORNER_CLEAR = 1.2
MAX_BAY = 6.5
#: the bearing a side's outward face points at, and the slot rotation that turns a module's -Y front to it
BEARING = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}


def is_civic(name: str) -> bool:
    n = str(name or "").lower()
    return any(w in n for w in CIVIC_WORDS)


def rot_for(side: str) -> float:
    return (BEARING[side] + 180.0) % 360.0


def _merge(intervals):
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def lines(run: float, openings) -> list:
    """The pier centre lines along one side, metres from its centre: ``run`` the wall's length (footprint edge to
    edge), ``openings`` ``[(u, width)]`` pooled over every storey.

    THE ANCHORS are the wall's two ends and the centre of each pooled opening (openings that overlap across storeys,
    a window over a door, are one). Each interval between two anchors is divided evenly into bays no longer than
    `MAX_BAY` -- and an interval between two openings gets at least one pier, at its middle, the line a pair of
    windows is read about. A line that would bring a pier within `OPENING_CLEAR` of an opening or `CORNER_CLEAR` of
    a corner is dropped, not moved: a moved pier is not on the bay line any more."""
    ops = _merge([(u - w / 2.0, u + w / 2.0) for u, w in openings])
    anchors = [(-run / 2.0, False)] + [((a + b) / 2.0, True) for a, b in ops] + [(run / 2.0, False)]
    out = []
    for (a, a_op), (b, b_op) in zip(anchors, anchors[1:]):
        span = b - a
        k = max(1 if (a_op and b_op) else 0, int(math.ceil(span / MAX_BAY - 1e-9)) - 1)
        for i in range(k):
            u = a + span * (i + 1) / (k + 1)
            if abs(u) > run / 2.0 - CORNER_CLEAR - PIER_W / 2.0 + 1e-9:
                continue
            if any(lo - OPENING_CLEAR - PIER_W / 2.0 < u < hi + OPENING_CLEAR + PIER_W / 2.0 for lo, hi in ops):
                continue
            out.append(round(u, 4))
    return out


def plan(spec, extent, wall_thick: float, z0: float, z1: float, openings_by_side) -> list:
    """The building's pilasters as ``{slot_id, side, centre, size, rot_y}`` -- ``size`` world-axis, ``dims`` the
    module's [width, depth, height] -- or [] for a building that takes none. ``extent`` is the storeys' common
    ``(x0, y0, x1, y1)``; ``openings_by_side`` ``{side: [(u, width)]}`` pooled over the storeys above ground; the
    pier stands from ``z0`` (grade) to ``z1`` (the top storey's wall top)."""
    if getattr(spec, "facade", False) or not is_civic(getattr(spec, "name", "")):
        return []
    x0, y0, x1, y1 = extent
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h = z1 - z0
    d = PROUD + BURY
    out = []
    for side in ("N", "E", "S", "W"):
        run = (x1 - x0) if side in ("N", "S") else (y1 - y0)
        face = {"N": y1 + wall_thick / 2.0, "S": y0 - wall_thick / 2.0,
                "E": x1 + wall_thick / 2.0, "W": x0 - wall_thick / 2.0}[side]
        sign = 1.0 if side in ("N", "E") else -1.0
        mid = face + sign * (PROUD - BURY) / 2.0
        for i, u in enumerate(lines(run, openings_by_side.get(side, ()))):
            if side in ("N", "S"):
                centre, size = (cx + u, mid, z0 + h / 2.0), (PIER_W, d, h)
            else:
                centre, size = (mid, cy + u, z0 + h / 2.0), (d, PIER_W, h)
            out.append({"slot_id": f"pilaster_{side}_{i}", "side": side,
                        "centre": tuple(round(v, 4) for v in centre), "size": tuple(round(v, 4) for v in size),
                        "dims": (PIER_W, round(d, 4), round(h, 4)), "rot_y": rot_for(side)})
    return out
