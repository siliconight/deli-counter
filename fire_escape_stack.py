"""A walk-up's fire escape: where Zoo's `fire_escape` (>= 1.110.0) stands on a mid-rise Empty's front, a storey a
slot (0.220.0, factory roadmaps 156 and 241).

The walker's photo of a brick walk-up: "this is something i'd like to see in our toolset, fireescape stairs brick"
(the factory root's docs/proposals/FIRE_ESCAPE.md, step 2). Zoo draws one storey of a fire escape from a slot's box
alone; this says where each storey's box stands, as `shop_awning.py` says where an awning hangs.

WHICH BUILDINGS (`presets.empty_midrise`): a walk-up -- `WALKUP_STOREYS` storeys or fewer -- and not a corner block,
whose awning runs the front. CHOSEN, not read from a code: the height a walk-up stops at, before a building takes a
lift and its stairs inside.

WHERE, in the building's frame (x along the front, y back into the house, z up; the front wall `S`, its outer face
at -(footprint_y + wall_thick) / 2; storey s's walking surface at s * story_height + floor_thick / 2, as
`_opening_to_hole` cuts its openings):
  * on the front, centred on the window column at the end farther from the front door -- the opening its preset
    tagged `front_door` -- a bay's spacing less `MARGIN` either side, at most `WIDTH_MAX`;
  * `DEPTH` out from the wall, its back `SINK` inside the wall's outer face;
  * a landing a storey, from the second to the top. Under each but the top a flight bay a storey tall, its deck's
    top on the storey's walking surface, `flight_a` and `flight_b` alternating from the second, so the stack
    switches back; the top landing `top_a` or `top_b`, whichever the last flight comes up into, its deck and guard
    tall;
  * the drop ladder under the lowest landing's hatch, its foot `DROP_FOOT` over the ground floor's walking surface.
The numbers Zoo draws to are Zoo's (`fire_escape_forms`), repeated here and pinned by the tests, because Deli Counter
does not import Zoo: `ZOO_DECK` (the deck's top over its box's bottom), `ZOO_GUARD` and `ZOO_PROUD` (the guard over
the deck, and its posts over that), `ZOO_BAND` (the stair band, 22 in, behind the deck's front bar), `ZOO_HATCH`.

No collision: the lowest landing stands a storey up, and Level Factory reads an Empty's street edge off its
colliders. Pure: no Blender, so every number here is tested without a build.
"""
from __future__ import annotations

#: a walk-up's storeys at the most
WALKUP_STOREYS = 6
DEPTH = 1.2
MARGIN = 0.2
WIDTH_MAX = 2.8
SINK = 0.008
DROP_FOOT = 2.2
LADDER = (0.45, 0.05)
#: Zoo's `fire_escape_forms`: FRAME, GUARD_H, POST_PROUD, FLIGHT_W, HATCH
ZOO_DECK = 0.0508
ZOO_GUARD = 0.9144
ZOO_PROUD = 0.006
ZOO_BAND = 0.5588
ZOO_HATCH = 0.75
SIDES = ("front",)


def bay(spec):
    """``(x, spacing)``: the front's window column at the end farther from the front door, and the columns'
    spacing, in metres. None where the front has no window above the ground floor."""
    cols = sorted({round(op.pos, 4) for w in spec.ext_walls if w.wall == "S" and w.story == 1
                   for op in w.openings if op.kind == "window"})
    if not cols:
        return None
    door = [op.pos for w in spec.ext_walls if w.wall == "S" and w.story == 0 for op in w.openings
            if getattr(op, "tag", None) == "front_door"]
    d = door[0] if door else 0.0
    end = max((cols[0], cols[-1]), key=lambda p: (abs(p - d), p))
    return end * float(spec.footprint_x), float(spec.footprint_x) / len(cols)


def plan(spec):
    """``[{"slot_id", "form", "centre", "size"}]`` for a spec whose `fire_escape_stack` is "front", else []. A side
    it does not know, a building with no storey to land on or a front with no window is refused, not dropped."""
    side = getattr(spec, "fire_escape_stack", None)
    if not side:
        return []
    if side not in SIDES:
        raise ValueError("fire_escape_stack %r is not one of %s" % (side, SIDES))
    n = int(spec.n_stories)
    if n < 2:
        raise ValueError("a fire escape on a building of %d storey(s) has no landing" % n)
    got = bay(spec)
    if got is None:
        raise ValueError("a fire escape on a front with no window above the ground floor")
    x, spacing = got
    w = round(min(WIDTH_MAX, spacing - 2 * MARGIN), 4)
    h, ft = float(spec.story_height), float(spec.floor_thick)
    face = -(float(spec.footprint_y) + float(spec.wall_thick)) / 2.0
    yc = face + SINK - DEPTH / 2.0

    def deck_bottom(s):
        return s * h + ft / 2.0 - ZOO_DECK

    flights = ["flight_a" if (s - 1) % 2 == 0 else "flight_b" for s in range(1, n - 1)]
    out = [{"slot_id": "fire_escape_%d" % s, "form": f, "centre": (x, yc, deck_bottom(s) + h / 2.0),
            "size": (w, DEPTH, h)} for s, f in zip(range(1, n - 1), flights)]
    top_h = round(ZOO_DECK + ZOO_GUARD + ZOO_PROUD, 4)
    top = "top_a" if not flights or flights[-1] == "flight_b" else "top_b"
    out.append({"slot_id": "fire_escape_%d" % (n - 1), "form": top,
                "centre": (x, yc, deck_bottom(n - 1) + top_h / 2.0), "size": (w, DEPTH, top_h)})
    # the drop, under the lowest landing's hatch: a form `_a`'s hatch is at -x, `_b`'s at +x
    side_x = -1.0 if (flights[0] if flights else top).endswith("_a") else 1.0
    dx = x + side_x * (w / 2.0 - (ZOO_DECK + ZOO_HATCH) / 2.0)
    dy = yc - DEPTH / 2.0 + ZOO_DECK + ZOO_BAND / 2.0
    hang = deck_bottom(1) + SINK                     # its top, SINK inside the lowest landing's deck frame
    foot = ft / 2.0 + DROP_FOOT
    out.append({"slot_id": "fire_escape_drop", "form": "drop", "centre": (dx, dy, (hang + foot) / 2.0),
                "size": (LADDER[0], LADDER[1], round(hang - foot, 4))})
    return out
