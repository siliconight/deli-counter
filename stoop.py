"""An Empty's stoop: the steps up to a raised front door (0.211.0, factory roadmap 240).

The comps, a Philadelphia rowhouse street: "three or four steps up to each door, with iron railings;
the first floor stands above the sidewalk" (the factory's docs/reference/PHILLY_STREET_COMPS.md).
Philadelphia's own guide says the same without a number -- "Most existing rowhouses are a few steps
up from the street" (City Planning Commission, *Philadelphia Rowhouse Manual*, 2008, p. 13) -- and the
residential code fills the blank: a riser at most 7 3/4 in, a tread at least 10 in (IRC R311.7.5).
The design, and why three risers: the factory's docs/proposals/ROWHOUSE_STOOP.md.

THE CONTRACT DECIDES THE COLLISION. A 7 in riser is 1.7 times the contract's unassisted step
(`clearances.unassisted_step_max_m`, 0.1025 m), so a collider a step is a wall to the contract body.
As the stairs do (`stairwell.ramp_foot_extension`, `stairwell.ramp_head_trim`), the stoop is walked on
ONE smooth ramp whose top face IS the nosing line -- through the landing's front edge and every
tread's, down to the ground one tread past the bottom riser -- under stepped visuals; its head ends on
the landing's edge, so nothing stands proud of the landing a body coming down would meet. Under each
tread but the lowest, a collider stops one riser short of it, as the stairs' do, so a body coming at
the steps from the side meets a block, not the space under the ramp. The pitch is atan(riser / tread).

WHERE IT STANDS: Level Factory's terrace keeps every Empty's front 2.0 m behind the sidewalk's back
edge (`level_factory/packages/pipeline/empties.py`, `FRONTAGE`); the stoop, its ramp's foot included,
is `depth(...)` deep and must stay inside that (`test_stoop.py` holds it to `TERRACE_FRONTAGE`).

Frame: the building's -- x along the front, y back into the house, z up, the front wall `S` at
-footprint_y / 2. Pure: no Blender, so every number here is tested without a build.
"""
from __future__ import annotations

import math

IN = 0.0254
#: the working riser and tread, inside the code's 7 3/4 in and 10 in (IRC R311.7.5); rounded to
#: the tenth of a millimetre, so a spec carries 0.2794 and not a float's tail
RISER = round(7 * IN, 4)             # 0.1778 m
TREAD = round(11 * IN, 4)            # 0.2794 m
#: the comps' "three or four"; three is what the terrace's 2.0 m holds with a 0.9 m landing
RISERS = 3
#: the landing in front of the door, and the stoop's width across the front
LANDING = 0.9
WIDTH = 1.5
#: a piece rests in the ground below it, whatever lies there (Zoo's floater rule: past 2 mm)
SKIRT = 0.05
#: the ramp collider's thickness, the stairs' own (`stairwell.ramp_foot_extension`'s default)
RAMP_THICK = 0.25
#: the terrace's frontage a stoop must fit inside (`level_factory/packages/pipeline/empties.py`)
TERRACE_FRONTAGE = 2.0


def front_door(spec):
    """``(x, width, sill)`` of the storey-0 opening on the front wall `S` tagged ``front_door``,
    its centre placed as the wall builder places it (`snap(pos * run)`), or None."""
    for w in spec.ext_walls:
        if w.wall != "S" or w.story != 0:
            continue
        for op in w.openings:
            if getattr(op, "tag", None) == "front_door":
                r = op.resolved()
                g = spec.grid
                u = round(op.pos * spec.footprint_x / g) * g
                return u, r["width"], r["sill"]
    return None


def rise(spec, door=None):
    """The height of the front door's threshold above grade: the floor slab's top (`floor_thick`
    / 2, the slab centred on grade) plus the door's sill -- `_opening_piece`'s `open_bottom`."""
    door = door or front_door(spec)
    return spec.floor_thick / 2.0 + door[2]


def depth(risers=RISERS, tread=TREAD, landing=LANDING):
    """How far the stoop reaches out of the front face, its ramp's foot included."""
    return landing + risers * tread


def plan(spec):
    """The stoop's pieces in the building's frame, or None when the spec asks for none. Boxes are
    ``(centre, size)``; ``ramp`` adds ``pitch`` (radians, about x, its high end toward the house)."""
    st = getattr(spec, "stoop", None)
    if not st:
        return None
    door = front_door(spec)
    if door is None:
        raise ValueError("%s asks for a stoop and has no storey-0 front door tagged front_door"
                         % spec.name)
    n = int(st["risers"])
    tread, landing, width = float(st["tread"]), float(st["landing"]), float(st["width"])
    total = rise(spec, door)
    riser = total / n
    x = door[0]
    face = -spec.footprint_y / 2.0 - spec.wall_thick / 2.0
    head = face - landing                       # the landing's front edge
    foot = head - n * tread                     # where the nosing line meets grade
    out = {"x": x, "face_y": face, "rise": total, "riser": riser, "tread": tread,
           "risers": n, "width": width, "head_y": head, "foot_y": foot,
           "depth": face - foot, "pitch_deg": math.degrees(math.atan2(riser, tread))}
    out["landing"] = ((x, face - landing / 2.0, (total - SKIRT) / 2.0),
                      (width, landing, total + SKIRT))
    treads, unders = [], []
    for k in range(1, n):
        top = total - k * riser
        cy = head - (k - 0.5) * tread
        treads.append(((x, cy, (top - SKIRT) / 2.0), (width, tread, top + SKIRT)))
        # one riser short of the tread, so the ramp is the only surface a foot meets
        under = top - riser
        if under > 1e-6:
            unders.append(((x, cy, (under - SKIRT) / 2.0), (width, tread, under + SKIRT)))
    out["treads"], out["unders"] = treads, unders
    # the ramp: its TOP FACE from (foot, 0) to (head, total), the slab hanging below it
    run = head - foot
    length = math.hypot(run, total)
    pitch = math.atan2(total, run)
    mid_y, mid_z = (head + foot) / 2.0, total / 2.0
    # the top face's upward normal is (0, -total, run) / length
    cy = mid_y + (RAMP_THICK / 2.0) * total / length
    cz = mid_z - (RAMP_THICK / 2.0) * run / length
    out["ramp"] = ((x, cy, cz), (width, length, RAMP_THICK), pitch)
    return out


def surface_z(p, y):
    """The walked surface's height at ``y`` in front of the house: the ramp's top face from its
    foot to the landing's edge, the landing's top beyond it, grade before the foot."""
    if y >= p["head_y"]:
        return p["rise"]
    if y <= p["foot_y"]:
        return 0.0
    return p["rise"] * (y - p["foot_y"]) / (p["head_y"] - p["foot_y"])
