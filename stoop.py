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

THE RAILINGS (0.212.0, the walker's calls of 2026-10-13: "railings both sides"): one a side,
`RAIL_INSET` inside the stoop's side, each Zoo's `stoop_railing` (1.105.0) in two slots -- a LEVEL
section along the landing, from its front edge to the facade, and a FLIGHT from that edge down to a
post on the bottom tread. Zoo draws either from its slot's box alone, its run along X and the high end
at +X: a level's rail along the box's top; a flight's from `RAIL_H` over the box's bottom at its post
to the box's top at the high end. So the boxes here ARE the railing: the level's bottom is the landing
and its top `RAIL_H` over it; the flight's bottom is the bottom tread, its low end the post's outer
face, its top `RAIL_H` over the landing at the landing's edge. Their colliders are written here, as
the stoop's are: a box along the landing, and a slab whose top face is the flight's rail.

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
#: THE RAILINGS (0.212.0). The rail's height over the walking line: IRC R311.7.8.1's 34-38 in, at 36
#: -- Zoo's `stoop_railing_forms.RAIL_H`, the same source and the same number
RAIL_H = round(36 * IN, 4)           # 0.9144 m
#: the railing's depth across: Zoo's top rail, a 1-1/2 in flat bar
RAIL_D = 0.038
#: and how far inside the stoop's side it stands. Flush, a flight's box shares the middle tread's
#: side plane, facing the same way, over a tread by a riser (0.2794 x 0.1778 = 0.0497 m^2); the
#: composer's z-fight gate reads a module as its box and skips a pair under 0.05 m^2
#: (`zfight_gate.AREA_MIN`), so it passed by 0.3 cm^2 -- one deeper tread from a flag. Inside it,
#: no railing face lies on a step's
RAIL_INSET = 0.05
#: the post Zoo stands at a flight's low end (1-1/4 in square), its centre `RAIL_BACK` behind the
#: bottom nosing, so it stands on the bottom tread
RAIL_POST = round(1.25 * IN, 4)      # 0.0318 m
RAIL_BACK = 0.05
#: THE TURN. Zoo draws a railing's run along its X, the high end at +X; the composer turns a module
#: by `tscn_export.godot_basis`, Ry(-t), so 270 points +X at Godot -Z -- Blender +Y, the house. 90
#: would point every flight's rail down at the street. A thin railing's footprint ties 90 and 270, and
#: the composer's fit keeps the slot's own turn on a tie (`themed_tscn._fit_rotation`).
RAIL_ROT_Y = 270.0


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
    # THE RAILINGS (0.212.0): `centre` and `size` in the building's frame, `dims` the module's (its
    # run, its depth, its height), `collider` Deli Counter's
    bottom_top = total - (n - 1) * riser               # the bottom tread's top
    post_y = head - (n - 1) * tread + RAIL_BACK        # the flight's post, on the bottom tread
    lo_y = post_y - RAIL_POST / 2.0                    # the flight's low end: the post's face
    rails = []
    for side, sgn in (("w", -1.0), ("e", 1.0)):
        rx = x + sgn * (width / 2.0 - RAIL_INSET - RAIL_D / 2.0)
        run = face - head
        centre = (rx, (head + face) / 2.0, total + RAIL_H / 2.0)
        size = (RAIL_D, run, RAIL_H)
        rails.append({"name": "stoop_rail_%s_level" % side, "form": "level",
                      "centre": centre, "size": size, "dims": (run, RAIL_D, RAIL_H),
                      "collider": ("box", centre, size)})
        run = head - lo_y
        z0, z1 = bottom_top, total + RAIL_H
        # the rail: RAIL_H over the bottom tread at the post's centre, RAIL_H over the landing at its
        # edge; the collider a slab under it, RAIL_H deep measured upright
        r_run, r_drop = head - post_y, total - bottom_top
        r_pitch = math.atan2(r_drop, r_run)
        thick = RAIL_H * math.cos(r_pitch)
        ym, zm = (post_y + head) / 2.0, (bottom_top + total) / 2.0 + RAIL_H
        rails.append({"name": "stoop_rail_%s_flight" % side, "form": "flight",
                      "centre": (rx, (lo_y + head) / 2.0, (z0 + z1) / 2.0),
                      "size": (RAIL_D, run, z1 - z0), "dims": (run, RAIL_D, z1 - z0),
                      "collider": ("slab", (rx, ym + (thick / 2.0) * math.sin(r_pitch),
                                           zm - (thick / 2.0) * math.cos(r_pitch)),
                                   (RAIL_D, math.hypot(r_run, r_drop), thick), r_pitch)})
    out["rails"] = rails
    return out


def surface_z(p, y):
    """The walked surface's height at ``y`` in front of the house: the ramp's top face from its
    foot to the landing's edge, the landing's top beyond it, grade before the foot."""
    if y >= p["head_y"]:
        return p["rise"]
    if y <= p["foot_y"]:
        return 0.0
    return p["rise"] * (y - p["foot_y"]) / (p["head_y"] - p["foot_y"])
