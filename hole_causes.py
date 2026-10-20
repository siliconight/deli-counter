"""hole_causes.py -- why a hole in a floor is there, and what stands round it (pure, no bpy).

The factory's roadmap 265. The walker, 2026-10-19, asked why the levels have holes in their
floors -- the drop routes this repo cuts square through a slab -- and chose to keep the routes and
give each a reason to exist: "if we have holes it should be clear to the player that they are
there, but also some reason other than a perfectly cut square (what is diegetic but a signal to
the human playing the game)".

THE CAUSE of a drop hole -- a `floor_hole` link, or a `hatch` link below the roof, that cuts the
slab -- is the link's own `cause` when it names one; else, for a `hatch` link, `hatch` (it was
authored as one); else `RULES` by the rooms above and below the hole's centre; else none, and
layout_lint L28 names the hole. `RULES` are the factory's calls of 2026-10-19 under the walker's
direction, meant to be changed:

  cut     a crew broke through (the delis' hideout over their kitchen);
  broken  the floor gave way (a rowhouse bedroom over its kitchen);
  hatch   a built floor hatch (a police armory over its garage, a warehouse mezzanine).

WHAT STANDS ROUND IT, each built by Zoo (1.114.0) as a prop slot this module derives, as
`roof_hatch.py` does for a roof scuttle:

- `cut` / `broken`: a `hole_edge` round the cut -- the floor torn back irregularly, the cut's
  walls, the ceiling broken back underneath with shards hanging -- whose form names the cause, the
  floor's construction (`_slab` where the room above has a `concrete` floor: bars, not joists)
  and the ceiling below (`_plaster` where it is plaster or drywall, not a drop ceiling's tiles); a
  `hole_spoil` on the floor the drop lands on (the same form; its stock the finish of the floor
  above, `carpet` or `tile`, so the pieces that came down carry it); and, for `cut`, a `hole_kit`
  beside the hole -- the crew's tarp, saw, bag and a work light aimed in -- on a side with room.
- `hatch`: `roof_hatch` in its `floor` form -- a 3 cm safety-yellow frame round the cut and a lid
  standing open on the side nearest a wall -- with the `hatch` interactive, open by default so the
  drop stays a route.

The edge and the spoil are visual only; the kit and the hatch carry their own collision
(`prop_species.SPECIES_OWNS_COLLISION`). The slab's rectangular cut stays the collider and the
drop's route, so a body falls exactly where it did.

THE CONTRACT WITH ZOO, mirrored from `zoo_keeper.core.hole_forms`: an edge slot reaches `BAND`
past the hole each side and is `TOP` + a floor skin + the slab + a ceiling skin + `HANG` tall, its
top `TOP` above the visible floor; a spoil, kit or floor-hatch slot stands `SKIRT` below the
visible floor it rests on. Change one side, change the other.

Reads a spec DICT, as layout_lint does: the builder passes `dataclasses.asdict` of its LevelSpec.
"""
from __future__ import annotations

import math
import types
import zlib

import floors
import interactives
import layout_lint

#: A link names its own cause with one of these.
CAUSES = ("cut", "broken", "hatch")
#: Not a link's to name: a hole that opens into a stair's well is the stair's (`stair_share`). No
#: frame or torn edge stands round it -- there is no floor there to stand on -- and the gameplay
#: record says so.
STAIR = "stair"

#: The walker's direction, the factory's calls of 2026-10-19, by (room above, room below) at the
#: hole's centre.
RULES = {
    ("apartment_hideout", "kitchen"): "cut",     # the crew's hideout over the deli: they cut through
    ("bedroom", "kitchen"): "broken",            # a rowhouse bedroom's floor gave way over the kitchen
    ("armory", "garage"): "hatch",               # an equipment hatch between the armory and the bay
    ("mezz_south", "main_floor"): "hatch",       # a warehouse mezzanine's load hatch
}

# -- the contract with Zoo's core.hole_forms ---------------------------------------------------------
BAND = 0.30
TOP = 0.012
SKIN = floors.SKIN_THICK
HANG = 0.30
SKIRT = 0.004
VARIANTS = 4
#: The genomes' sizes, ``(min, max)`` metres for width, depth and height. A slot outside them is not
#: built as its species: Zoo builds the plain box at the slot's size instead (`kit._species_fit`),
#: which over a hole would cover it and might close the drop. So a slot that would fall outside is
#: left out, the build log says so, and L28 names a hole whose edge or hatch it was.
GENOME_DIMS = {
    "hole_edge": ((1.2, 6.8), (1.2, 6.8), (0.4, 1.4)),
    "hole_spoil": ((0.8, 7.0), (0.8, 7.0), (0.04, 0.10)),
    "hole_kit": ((1.3, 2.2), (0.55, 1.0), (0.55, 0.95)),
    "roof_hatch": ((0.9, 2.4), (0.9, 2.4), (0.03, 0.35)),
}

#: `_vertical_links` cuts a drop with no size_x / size_y at this.
DEFAULT_HOLE = 1.5
#: The spoil reaches this far past the hole on each side, and is this tall (under the step limit).
SPILL = 0.25
SPOIL_H = 0.10
#: Zoo's `hole_spoil` genome: no side shorter or longer than these.
SPOIL_MIN, SPOIL_MAX = GENOME_DIMS["hole_spoil"][0]
#: A spoil keeps at least this share of the hole's own area clear of furniture, or it is not laid.
SPOIL_KEEP = 0.5
#: A spoil is cut back to stand SPOIL_OFF off a piece, and meets one only nearer than SPOIL_MEETS:
#: two numbers, so a cut never meets the piece it was cut from again by a float's last digit.
SPOIL_OFF, SPOIL_MEETS = 0.02, 0.01
#: The crew's kit: width (along the hole's side), depth, height; its near edge this far off the hole.
KIT = (1.4, 0.7, 0.7)
KIT_GAP = BAND + 0.05
#: A floor hatch: its frame stands this far outside the hole each side, and is this tall.
HATCH_CURB = 0.08
HATCH_FRAME = 0.03
#: Clearances for the kit, metres: off a piece, off a stair's or another hole's rect, off a ladder.
KIT_OFF_PIECE = 0.15
KIT_OFF_STAIR = 0.30
KIT_OFF_LADDER = 1.0

_ROT = {"N": 0, "E": 90, "S": 180, "W": 270}      # roof_hatch.py's: local +Y toward that side
_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
_SLAB_FLOORS = ("concrete",)
_PLASTER_CEILINGS = ("plaster", "drywall")


def _rect(link):
    sx = float(link.get("size_x") or DEFAULT_HOLE)
    sy = float(link.get("size_y") or DEFAULT_HOLE)
    x, y = float(link["x"]), float(link["y"])
    return (x - sx / 2.0, y - sy / 2.0, x + sx / 2.0, y + sy / 2.0)


def _overlaps(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def _same(a, b):
    return all(abs(p - q) < 1e-6 for p, q in zip(a, b))


def _rooms_at(spec, story, x, y):
    """``(room above, room below)`` at (x, y) for a hole in storey `story`'s floor, dicts or None."""
    by = layout_lint._rooms_by_story(spec)
    return (layout_lint._room_at(by.get(int(story), []), x, y),
            layout_lint._room_at(by.get(int(story) - 1, []), x, y))


def is_drop(spec, link):
    """Can a body drop through this link's hole: a `floor_hole`, or a `hatch` below the roof, that
    cuts the slab and says where it is? A hatch on the roof is `roof_hatch.py`'s."""
    if link.get("story") is None or link.get("x") is None or link.get("y") is None:
        return False
    if not link.get("cut_slab", True):
        return False
    top = int(layout_lint._spec_value(spec, "n_stories"))
    return (link.get("kind") == "floor_hole"
            or (link.get("kind") == "hatch" and int(link["story"]) < top))


def drop_links(spec):
    """The links a body can drop through (`is_drop`), in the spec's order."""
    return [v for v in spec.get("vertical_links") or [] if is_drop(spec, v)]


def without_holes(spec):
    """Leave out every hole in a floor a player would see, in place: ``(links, slab_holes)`` removed.

    A HOLE IS AN OPTIONAL ROUTE (0.237.0, the factory's roadmap 269). The walker, 2026-10-20: "stairs and ladders
    should be the primary way to get between floors in this game...with the holes in floors being somewhat rare...but
    still at our disposal". A drop (`is_drop`) goes, unless it opens into a stair's own well (`cause_for` says
    `stair`: nothing of it shows, and the stair is the route there anyway). So do the authored ``slab_holes`` whose
    plan overlaps a removed drop's hole on ANY storey -- a recipe authors the slab hole beside the link, and an
    atrium or a shaft cuts every storey it passes through while its link names one; left behind, a slab hole is an
    undeclared drop. A roof hatch is not a hole in a floor (`is_drop`), and a stair or a ladder is not touched."""
    links, keep = [], []
    for v in spec.get("vertical_links") or []:
        (links if is_drop(spec, v) and cause_for(spec, v) != STAIR else keep).append(v)
    if not links:
        return [], []
    spec["vertical_links"] = keep
    rects = [_rect(v) for v in links]
    holes, left = [], []
    for h in spec.get("slab_holes") or []:
        (holes if any(_overlaps(_rect(h), r) for r in rects) else left).append(h)
    if "slab_holes" in spec:
        spec["slab_holes"] = left
    return links, holes


def _stair_cuts(spec, story):
    """The plan rects the stairs cut in storey `story`'s floor: `stairwell.slab_openings` of the
    stairs alone, read as layout_lint reads a dict's stairs."""
    import stairwell
    stairs = [st for st in (layout_lint._stair_obj(r) for r in spec.get("stairs") or [])
              if st is not None]
    return stairwell.slab_openings(types.SimpleNamespace(slab_holes=[], stairs=stairs)).get(
        int(story), [])


def stair_share(spec, link):
    """The share of a drop's hole that lies in a stair's well on its storey, 0..1. THE CAPTURED
    CASE: deli_a01-a03's `roof_drop_to_stair` hatch is cut wholly inside `deli_stair_up`'s well and
    rowhouse_raid's hatch 0.70 inside its stair's; a floor hatch built round either hung over the
    stair, and `circulation.check_shell` read its frame inside the stair's column."""
    r = _rect(link)
    inside = sum(max(0.0, min(r[2], q[2]) - max(r[0], q[0]))
                 * max(0.0, min(r[3], q[3]) - max(r[1], q[1]))
                 for q in _stair_cuts(spec, link["story"]))
    return min(1.0, inside / ((r[2] - r[0]) * (r[3] - r[1])))


def cause_for(spec, link):
    """The hole's cause: the link's own; `STAIR` for a hole opening into a stair's well; a hatch's
    by its kind; `RULES` by its rooms; else None."""
    own = link.get("cause")
    if own:
        if own not in CAUSES:
            raise ValueError("a vertical link's cause %r is not one of %s"
                             % (own, ", ".join(CAUSES)))
        return own
    if stair_share(spec, link) > 0.0:
        return STAIR
    if link.get("kind") == "hatch":
        return "hatch"
    up, dn = _rooms_at(spec, link["story"], float(link["x"]), float(link["y"]))
    if up is None or dn is None:
        return None
    return RULES.get((up["id"], dn["id"]))


def _surface(spec, room, surface):
    mapping = floors.FLOOR_BY_ROLE if surface == "floor" else floors.CEILING_BY_ROLE
    return floors._material(types.SimpleNamespace(**room), surface, mapping,
                            spec.get("default_material"))


def form_for(spec, link, cause):
    """Zoo's form for a `cut` or `broken` hole: the cause, `_slab` where the floor above is
    concrete, `_plaster` where the ceiling below is plaster or drywall."""
    up, dn = _rooms_at(spec, link["story"], float(link["x"]), float(link["y"]))
    slab = up is not None and _surface(spec, up, "floor") in _SLAB_FLOORS
    plaster = dn is not None and _surface(spec, dn, "ceiling") in _PLASTER_CEILINGS
    return cause + ("_slab" if slab else "") + ("_plaster" if plaster else "")


def _finish(spec, link):
    """The spoil's stock: the finish of the floor above, as the pieces that came down carry it."""
    up, _dn = _rooms_at(spec, link["story"], float(link["x"]), float(link["y"]))
    kind = _surface(spec, up, "floor") if up is not None else None
    return kind if kind in ("carpet", "tile") else "none"


def _cuts(spec):
    """Every slab cut a drop could fall through, as `ladder.drop_landing` reads them: the authored
    holes and every drop link's own, whatever order the builder appends them in."""
    out = [dict(h) for h in spec.get("slab_holes") or []]
    for v in drop_links(spec):
        r = _rect(v)
        out.append({"story": int(v["story"]), "x": (r[0] + r[2]) / 2.0, "y": (r[1] + r[3]) / 2.0,
                    "size_x": r[2] - r[0], "size_y": r[3] - r[1]})
    return out


def _pieces(spec, story):
    """Plan boxes ``(x0, y0, x1, y1)`` of the volumes standing on storey `story`."""
    out = []
    for v in spec.get("volumes") or []:
        if layout_lint.piece_story(spec, v) != int(story):
            continue
        hx, hy = float(v.get("size_x", 0.0)) / 2.0, float(v.get("size_y", 0.0)) / 2.0
        out.append((float(v["x"]) - hx, float(v["y"]) - hy, float(v["x"]) + hx, float(v["y"]) + hy))
    return out


def _door_zones(spec, story):
    """Plan boxes in front of every door-like opening on storey `story`, both sides of its wall,
    `layout_lint.DOOR_APPROACH_M` deep and 0.15 m wider than the door each side."""
    import partition_bounds
    out = []
    depth = float(layout_lint.DOOR_APPROACH_M)
    fx = float(layout_lint._spec_value(spec, "footprint_x"))
    fy = float(layout_lint._spec_value(spec, "footprint_y"))
    for p in spec.get("partitions") or []:
        if int(p.get("story", 0) or 0) != int(story):
            continue
        ax, pos = str(p.get("axis", "X")).upper(), float(p.get("pos", 0.0))
        for along, w, _label in partition_bounds.host_openings(spec, p, False):
            half = w / 2.0 + 0.15
            if ax == "X":
                out.append((along - half, pos - depth, along + half, pos + depth))
            else:
                out.append((pos - depth, along - half, pos + depth, along + half))
    for wall in spec.get("ext_walls") or []:
        if int(wall.get("story", 0) or 0) != int(story):
            continue
        face = wall.get("wall")
        for along, w, _label in partition_bounds.host_openings(spec, wall, True):
            half = w / 2.0 + 0.15
            if face in ("N", "S"):
                y = fy / 2.0 if face == "N" else -fy / 2.0
                out.append((along - half, y - depth, along + half, y + depth))
            else:
                x = fx / 2.0 if face == "E" else -fx / 2.0
                out.append((x - depth, along - half, x + depth, along + half))
    return out


def _keep_clear(spec, link, story):
    """What a prop beside the hole must keep off on storey `story`: ``(pieces, stairs, doors,
    ladders)`` -- stair holes and walks and every other hole's rect, the hole's own left out."""
    hole = _rect(link)
    holes_, walks = layout_lint.stair_space(spec)
    stairs = [r for r in list(holes_.get(story, [])) + list(walks.get(story, []))
              if not _same(r, hole)]
    stairs += [_rect(v) for v in drop_links(spec)
               if int(v["story"]) == story and not _same(_rect(v), hole)]
    ladders = []
    for ld in spec.get("ladders") or []:
        lo = min(int(ld.get("from_story", 0)), int(ld.get("to_story", 0)))
        hi = max(int(ld.get("from_story", 0)), int(ld.get("to_story", 0)))
        if lo <= story <= hi:
            ladders.append((float(ld["x"]), float(ld["y"])))
    return _pieces(spec, story), stairs, _door_zones(spec, story), ladders


def _spoil_rect(spec, link, land):
    """The spoil's plan box on storey `land`'s floor: the hole and SPILL each side, inside the room
    there, cut back from every piece, stair hole and walk, and other hole on that floor; None when
    that leaves less than SPOIL_KEEP of the hole's area or a side shorter than Zoo's SPOIL_MIN."""
    hole = _rect(link)
    r = [hole[0] - SPILL, hole[1] - SPILL, hole[2] + SPILL, hole[3] + SPILL]
    cx, cy = float(link["x"]), float(link["y"])
    room = layout_lint._room_at(layout_lint._rooms_by_story(spec).get(int(land), []), cx, cy)
    if room is not None:
        inset = float(layout_lint._spec_value(spec, "wall_thick")) / 2.0 + 0.02
        b = room["bounds"]
        r = [max(r[0], b[0] + inset), max(r[1], b[1] + inset),
             min(r[2], b[2] - inset), min(r[3], b[3] - inset)]
    holes_, walks = layout_lint.stair_space(spec)
    pieces = (_pieces(spec, land) + list(holes_.get(int(land), [])) + list(walks.get(int(land), []))
              + [_rect(v) for v in drop_links(spec) if int(v["story"]) == int(land)])
    for _ in range(len(pieces) + 1):
        hit = next((p for p in pieces if _overlaps(r, p, SPOIL_MEETS)), None)
        if hit is None:
            break
        # cut back the side that keeps the most of the box
        g = SPOIL_OFF
        options = [(hit[2] + g, r[1], r[2], r[3]), (r[0], r[1], hit[0] - g, r[3]),
                   (r[0], hit[3] + g, r[2], r[3]), (r[0], r[1], r[2], hit[1] - g)]
        options = [o for o in options if o[2] - o[0] >= SPOIL_MIN and o[3] - o[1] >= SPOIL_MIN]
        if not options:
            return None
        r = list(max(options, key=lambda o: (o[2] - o[0]) * (o[3] - o[1])))
    else:
        return None
    if r[2] - r[0] < SPOIL_MIN or r[3] - r[1] < SPOIL_MIN:
        return None
    keep = (max(0.0, min(r[2], hole[2]) - max(r[0], hole[0]))
            * max(0.0, min(r[3], hole[3]) - max(r[1], hole[1])))
    if keep < SPOIL_KEEP * (hole[2] - hole[0]) * (hole[3] - hole[1]):
        return None
    # Zoo's longest side: trimmed about the hole's centre, never off the hole
    for lo, hi, c in ((0, 2, cx), (1, 3, cy)):
        if r[hi] - r[lo] > SPOIL_MAX:
            a = max(r[lo], min(c - SPOIL_MAX / 2.0, r[hi] - SPOIL_MAX))
            r[lo], r[hi] = a, a + SPOIL_MAX
    return tuple(r)


def _kit_place(spec, link):
    """``(side, center_xy, plan_box)`` for the crew's kit beside a `cut` hole, or None: the first
    side, the one reaching furthest into the room above first, whose box lies inside that room and
    off every piece, stair, other hole, door approach and ladder on its storey."""
    story = int(link["story"])
    hole = _rect(link)
    up, _dn = _rooms_at(spec, story, float(link["x"]), float(link["y"]))
    if up is None:
        return None
    b = up["bounds"]
    inset = float(layout_lint._spec_value(spec, "wall_thick")) / 2.0 + 0.05
    kw, kd, _kh = KIT
    cx, cy = (hole[0] + hole[2]) / 2.0, (hole[1] + hole[3]) / 2.0
    cands = {"S": (cx, hole[1] - KIT_GAP - kd / 2.0, kw, kd),
             "N": (cx, hole[3] + KIT_GAP + kd / 2.0, kw, kd),
             "W": (hole[0] - KIT_GAP - kd / 2.0, cy, kd, kw),
             "E": (hole[2] + KIT_GAP + kd / 2.0, cy, kd, kw)}
    pieces, stairs, doors, ladders = _keep_clear(spec, link, story)
    room_c = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
    # to the millimetre, so sides as far from the centre tie and their names decide, not a float's
    # last digit (-3.9 + 0.7 against -6.1 - 0.7)
    order = sorted(cands, key=lambda s: (round(math.hypot(cands[s][0] - room_c[0],
                                                          cands[s][1] - room_c[1]), 3), s))
    for side in order:
        x, y, w, d = cands[side]
        box = (x - w / 2.0, y - d / 2.0, x + w / 2.0, y + d / 2.0)
        if (box[0] < b[0] + inset or box[1] < b[1] + inset
                or box[2] > b[2] - inset or box[3] > b[3] - inset):
            continue
        if any(_overlaps(box, p, KIT_OFF_PIECE) for p in pieces):
            continue
        if any(_overlaps(box, s, KIT_OFF_STAIR) for s in stairs):
            continue
        if any(_overlaps(box, z) for z in doors):
            continue
        if any(box[0] - KIT_OFF_LADDER < lx < box[2] + KIT_OFF_LADDER
               and box[1] - KIT_OFF_LADDER < ly < box[3] + KIT_OFF_LADDER for lx, ly in ladders):
            continue
        return side, (x, y), box
    return None


def _hinge_side(spec, link):
    """The side a floor hatch's lid stands on: the hole's side nearest a wall of the room above,
    among the sides whose edge keeps off the storey's stairs, other holes and door approaches; the
    nearest of all when none does."""
    story = int(link["story"])
    hole = _rect(link)
    up, _dn = _rooms_at(spec, story, float(link["x"]), float(link["y"]))
    if up is None:
        return "N"
    b = up["bounds"]
    gaps = {"W": hole[0] - b[0], "S": hole[1] - b[1], "E": b[2] - hole[2], "N": b[3] - hole[3]}
    _pieces_, stairs, doors, _ladders = _keep_clear(spec, link, story)
    c = HATCH_CURB
    strips = {"W": (hole[0] - c, hole[1], hole[0], hole[3]), "E": (hole[2], hole[1], hole[2] + c, hole[3]),
              "S": (hole[0], hole[1] - c, hole[2], hole[1]), "N": (hole[0], hole[3], hole[2], hole[3] + c)}
    order = sorted(gaps, key=lambda s: (round(gaps[s], 3), s))      # to the mm, as `_kit_place`
    clear = [s for s in order if not any(_overlaps(strips[s], r) for r in stairs + doors)]
    return (clear or order)[0]


def fits(species, dims):
    """Can Zoo build `species` at a slot's local ``(w, d, h)``? Its own test, mirrored."""
    return all(lo - 1e-6 <= float(v) <= hi + 1e-6 for v, (lo, hi) in zip(dims, GENOME_DIMS[species]))


def _hatch_world(link):
    hole = _rect(link)
    return (hole[2] - hole[0] + 2.0 * HATCH_CURB, hole[3] - hole[1] + 2.0 * HATCH_CURB)


def _edge_dims(spec, link):
    hole = _rect(link)
    thick = float(layout_lint._spec_value(spec, "floor_thick"))
    return (hole[2] - hole[0] + 2.0 * BAND, hole[3] - hole[1] + 2.0 * BAND,
            TOP + 2.0 * SKIN + thick + HANG)


def _main(spec, link, cause):
    """``(species, local dims)`` of what says a caused hole's cause at its edge: a floor hatch's
    frame or a hole edge (a square hatch's local footprint is its world's; a turned one's is the
    world's turned, which `fits` asks the same of)."""
    if cause == "hatch":
        w, d = _hatch_world(link)
        return "roof_hatch", (w, d, HATCH_FRAME)
    return "hole_edge", _edge_dims(spec, link)


def _variant(spec, slot_id):
    return zlib.crc32(("%s:%s" % (spec.get("name", ""), slot_id)).encode("utf-8")) % VARIANTS


def _slot(spec, slot_id, species, material, style, form, stock, variant, center, dims, rot):
    return {
        "slot_id": slot_id, "role": "prop", "size_mod": "full",
        "style": style, "material": material, "species": species,
        "stock": stock, "variant": variant, "form": form,
        "current_ref": "prop_greybox_01", "kit_axis": "material",
        "wall": None, "story": None, "facing": None,
        "transform": {"translation": [round(center[0], 4), round(center[1], 4),
                                      round(center[2], 4)],
                      "rot_y": float(rot), "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [round(dims[0], 4), round(dims[1], 4), round(dims[2], 4)],
                "pivot": "center", "openings": [], "collision": "none"},
    }


def _local(world, rot):
    """A slot's local (w, d) for a world-axis footprint turned by `rot`."""
    return (world[1], world[0]) if int(rot) % 180 else (world[0], world[1])


def _ring(sid, hole, z, band, height):
    """The greybox of a slot that stands ROUND a hole: four boxes `band` wide outside the hole's rect, named
    ``<sid>_n`` / ``_s`` / ``_e`` / ``_w`` so each is the slot's own node (`themed_tscn.owns_node`) -- their union is
    the slot's footprint, which the placement gate and the composer's fit read, and nothing is drawn over the hole.

    A GREYBOX IS A DRAWING OF THE SPACE, and the walk test reads it: Lot bakes its walk navmeshes from visual meshes
    too (`geometry_parsed_geometry_type = 2`), on the candidate's greybox lot. Cold run 9340 (restaurant_row_001,
    Deli Counter 0.236.0) drew the edge as one box over the hole, its top 12 mm above the floor; the bake took it
    for floor, and all four walkers on both of deli_a03's candidates were sent to a target inside the hole and
    stuck in its corner against the slab's cut (WALKTEST_WALKER_STUCK 0 -> 8)."""
    sx, sy = hole[2] - hole[0], hole[3] - hole[1]
    x, y = (hole[0] + hole[2]) / 2.0, (hole[1] + hole[3]) / 2.0
    return [("%s_n" % sid, (x, hole[3] + band / 2.0, z), (sx + 2.0 * band, band, height)),
            ("%s_s" % sid, (x, hole[1] - band / 2.0, z), (sx + 2.0 * band, band, height)),
            ("%s_e" % sid, (hole[2] + band / 2.0, y, z), (band, sy, height)),
            ("%s_w" % sid, (hole[0] - band / 2.0, y, z), (band, sy, height))]


def hole_slots(spec, style_for):
    """``(slots, notes)`` for every caused drop hole in a spec dict.

    ``slots`` is ``[(slot, gameplay_interactive or None, boxes)]``, ``boxes`` the greybox's
    ``[(node name, center, size)]``, world-axis aligned: the spoil's and the kit's one box, the
    edge's and the floor hatch's a ring round the hole (`_ring`), so nothing is drawn over it.
    `style_for(material)` is the builder's skin style for a material. ``notes`` says what was left
    out and why -- a spoil with no floor clear for it, a kit with no side, a slot outside its
    species' sizes (`fits`) -- for the build log."""
    import ladder as _ladder
    sh = float(layout_lint._spec_value(spec, "story_height"))
    cuts = _cuts(spec)
    slots, notes, laid = [], [], {}
    for link in drop_links(spec):
        cause = cause_for(spec, link)
        if cause in (None, STAIR):
            continue
        story = int(link["story"])
        hole = _rect(link)
        x, y = (hole[0] + hole[2]) / 2.0, (hole[1] + hole[3]) / 2.0
        zf = story * sh + SKIN                              # the visible floor of the hole's storey
        tag = "%d_%d_%d" % (story, round(x * 10), round(y * 10))
        species, dims = _main(spec, link, cause)
        if not fits(species, dims):
            notes.append("%s_%s: no %s -- %s m is outside its sizes, and Zoo would build a box "
                         "over the hole" % ("floor_hatch" if cause == "hatch" else "hole_edge", tag,
                                            species, " x ".join("%g" % round(v, 3) for v in dims)))
            species = None
        if cause == "hatch":
            if species is None:
                continue
            sid = "floor_hatch_%s" % tag
            world = _hatch_world(link)
            # the slot's local -Y is the hinge side (roof_hatch.py's convention)
            rot = _ROT[_OPPOSITE[_hinge_side(spec, link)]]
            w, d = _local(world, rot)
            center = (x, y, zf - SKIRT + HATCH_FRAME / 2.0)
            slot = _slot(spec, sid, "roof_hatch", "metal", style_for("metal"), "floor", None, 0,
                         center, (w, d, HATCH_FRAME), rot)
            machine = interactives.derive_interactive(spec.get("name", ""), sid, story, "hatch", 0.0)
            slot["interactive"] = interactives.slot_interactive(machine)
            entry = interactives.gameplay_interactive(
                machine, sid,
                {"translation": [round(c, 3) for c in center], "rot_y": float(rot)},
                building=spec.get("name"))
            slots.append((slot, entry, _ring(sid, hole, center[2], HATCH_CURB, HATCH_FRAME)))
            continue
        form = form_for(spec, link, cause)
        # the edge, round the cut, its top TOP above the visible floor
        if species is not None:
            w, d, h_edge = dims
            center = (x, y, zf + TOP - h_edge / 2.0)
            sid = "hole_edge_%s" % tag
            slots.append((_slot(spec, sid, "hole_edge", "wood", style_for("wood"), form, None,
                                _variant(spec, sid), center, (w, d, h_edge), 0),
                          None, _ring(sid, hole, center[2], BAND, h_edge)))
        # the spoil, on the floor the drop lands on -- one a place: a stacked shaft's drops land
        # on one floor, and two spoils there would share it face for face
        land = _ladder.drop_landing(story, x, y, cuts)
        r = _spoil_rect(spec, link, land)
        sid = "hole_spoil_%s" % tag
        if r is None:
            notes.append("%s: no spoil -- no floor under the hole clear of furniture for one" % sid)
        elif any(_overlaps(r, q) for q in laid.get(land, [])):
            notes.append("%s: no spoil -- another drop's spoil lies there already" % sid)
        else:
            laid.setdefault(land, []).append(r)
            w, d = r[2] - r[0], r[3] - r[1]
            center = ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0, land * sh + SKIN - SKIRT + SPOIL_H / 2.0)
            slots.append((_slot(spec, sid, "hole_spoil", "wood", style_for("wood"), form,
                                _finish(spec, link), _variant(spec, sid), center,
                                (w, d, SPOIL_H), 0),
                          None, [(sid, center, (w, d, SPOIL_H))]))
        if cause != "cut":
            continue
        # the crew's kit beside the hole, its local +Y toward it
        sid = "hole_kit_%s" % tag
        placed = _kit_place(spec, link) if fits("hole_kit", KIT) else None
        if placed is None:
            notes.append("%s: no kit -- no side of the hole has room for one" % sid)
            continue
        side, (kx, ky), box = placed
        center = (kx, ky, zf - SKIRT + KIT[2] / 2.0)
        slots.append((_slot(spec, sid, "hole_kit", "plastic", style_for("plastic"), "cut", None,
                            _variant(spec, sid), center, KIT, _ROT[_OPPOSITE[side]]),
                      None, [(sid, center, (box[2] - box[0], box[3] - box[1], KIT[2]))]))
    return slots, notes


def uncaused(spec):
    """``(bad, none, bare, past)``, each ``[(link, room above id, room below id, detail)]``: the
    drop links naming a cause that is not one of `CAUSES` (detail: the cause), those no cause
    covers (None), those whose cause's edge or hatch is outside its species' sizes (the species
    and its slot's dims), and those reaching only partly into a stair's well (the share in it) --
    all but the first ship as a bare cut, or part of one. layout_lint L28 names all four."""
    bad, none, bare, past = [], [], [], []
    for link in drop_links(spec):
        up, dn = _rooms_at(spec, link["story"], float(link["x"]), float(link["y"]))
        ids = (up["id"] if up else None, dn["id"] if dn else None)
        if link.get("cause") and link["cause"] not in CAUSES:
            bad.append((link,) + ids + (link["cause"],))
            continue
        cause = cause_for(spec, link)
        if cause is None:
            none.append((link,) + ids + (None,))
        elif cause == STAIR:
            share = stair_share(spec, link)
            if share < 1.0 - 1e-6:
                past.append((link,) + ids + (share,))
        else:
            species, dims = _main(spec, link, cause)
            if not fits(species, dims):
                bare.append((link,) + ids + ((species, dims),))
    return bad, none, bare, past
