"""
level_design.py  --  felt-space enrichment layer (no bpy)
=========================================================
Applies validated FPS level-design principles to a finished preset spec so
buildings come out *better by construction*, not merely measurable after the
fact. This is the generative companion to sightlines.py (which only reports):
sightlines tells you a room plays badly; this puts the anchors there so it
plays well in the first place.

Principles distilled from the references B$ collected:
  * McMillan  -- line of sight is the dial that sets difficulty; cover and
                 portals are how you turn it.
  * Foreman   -- a level is ambiguity management; SIGHTLINES are the biggest
                 lever, every sightline needs a risk/reward, LANDMARKS go in
                 first so players spend attention on opponents, not navigation;
                 if a corner rewards camping, it needs more circulation or less
                 cover.
  * Epic (Fortnite) -- aim for ~3-5 quickly-recognizable POINTS OF ENGAGEMENT
                 per space (cover / window / ledge), and distinct CALLOUT
                 landmarks you can read from a distance.
  * SMU mid-area thesis -- DON'T over-cover (it destroys enemy-position
                 readability), keep callout areas visually distinct, stage
                 attackers before they're exposed.

DELCO is a PAYDAY-style 4-player PvE co-op heist loop, NOT a PvP-symmetric
shooter -- so this layer is about the felt space (cover cadence, callout
legibility, readable engagement) that holds regardless of who the opponent is,
not attacker/defender entrance symmetry.

CONTRACT
  * Pure Python, no bpy. Operates on the spec dict.
  * ADDITIVE and IDEMPOTENT: only ever appends, never moves or removes, and
    re-running is a no-op.
  * RETRACTED: "Geometry is never touched" and "anchors only". Both stopped
    being true when `seed_cover` and `furnish` began appending solid volumes
    (0.122.0), and `enclose_teller_lines` appends PARTITIONS and a room
    (0.126.0). What still holds is that nothing authored is moved or removed;
    every addition is gated by the same validators as authored geometry.
    The game still owns what an anchor *means*.

Tunables live in the module-level constants so a preset author can reason about
them. enrich(spec) is the single entry point; make() calls it by default.
"""

import math
from typing import Optional

# A volume reads as cover if its name suggests furniture/props you'd shelter
# behind and it stands somewhere between waist height and just over head height.
_COVER_NAME_HINTS = (
    "counter", "desk", "rack", "shelf", "aisle", "island", "crate", "planter",
    "table", "bench", "cooler", "display", "kiosk", "booth", "locker",
    "cabinet", "sofa", "couch", "pew", "teller", "register", "machine", "cart",
    "dumpster", "pallet", "stack", "column", "pillar", "statue", "barrier",
    "partition_cover", "low_wall", "half_wall", "planter_box",
    # Added with the shelter pass: a seeded piece that no hint matches is a
    # solid the room has and the tagger cannot see, which is the same defect
    # facing the other way.
    "tank", "unit",
)
# Names that look big/structural and must never be tagged as cover.
_COVER_NAME_SKIP = (
    "pad", "roof", "slab", "floor", "ceiling", "canopy", "wall_", "forecourt",
    "foundation", "platform_base", "ramp", "stair",
)

# TWO DIFFERENT QUESTIONS, SO TWO DIFFERENT NUMBERS, and asking one of them
# for both is how 75% of the cover in this repo came to be furniture that does
# nothing in a fight.
#
#   * "is this a thing you'd shelter behind" -- furniture, waist high, not a
#     kerb and not a wall. That is `_COVER_MIN_Z`/`_COVER_MAX_Z`, it decides
#     what gets TAGGED, and a low piece still earns its tag: it is a thing in
#     the room, it reads as life, and the consuming game may well let a body
#     crouch behind it.
#   * "does it stop the two sides seeing each other" -- geometry, derived in
#     agent_contract.json from the heights the evaluator actually sights
#     from. That is `cover_breaks_sightline()` below, and it is the one that
#     decides whether a room can be FOUGHT in.
#
# Measured across the 14 non-facade presets 2026-09-10, on `combat_audit`'s
# basis (any solid over 0.6 m with a footprint of 0.3 m or more, which is
# the right question for "can this room be fought in" -- a structural column
# breaks a line and carries no furniture name): 177 solids, 100 of them
# (56%) below the crossing height, and 39 of 91 combat rooms furnished
# entirely below it. The heights cluster cleanly either side -- nothing at
# all sits between 1.10 and 1.20 -- so the corpus was already split by this
# number and had no way to say so.
#
# A narrower first pass counted only NAME-TAGGED furniture and reported 43
# of 91. It was wrong and is kept here rather than dropped: it missed
# `parking_garage`, whose combat rooms are covered by structural columns
# that no name hint matches, and reported two of them bare.
_COVER_MIN_Z = 0.6      # below this it's a kerb, not furniture
_COVER_MAX_Z = 2.4      # above this it's a wall, not furniture


def cover_break_height():
    """Height at which a solid stops BOTH sides seeing each other.

    From `agent_contract.json`, which derives it from the evaluator's own
    sight and aim heights. Falls back to the ratified value the way every
    other consumer of that contract does, so a missing file degrades rather
    than breaking a build.
    """
    try:
        from agent_contract import cover_break_height as _h
        return float(_h())
    except Exception:
        return 1.3


def shelter_height():
    """Height at which a solid breaks a mutual sightline ANYWHERE along it.

    `cover_break_height` is where a solid starts working; this is where it
    works from every position on the line, and it is what a PRODUCER should
    build to. At the crossing there is one workable spot and a piece has to
    land on it; at the taller eye the whole line is available and the placer
    can satisfy its other constraints. Derived in the contract from the two
    sight heights, so it follows the evaluator.
    """
    try:
        from agent_contract import shelter_height as _h
        return float(_h())
    except Exception:
        return 1.6


#: >= this stands as high cover, else low. Was a flat 1.4, chosen -- which
#: put the boundary 0.18 m above the height where cover starts working and
#: called the gap "low cover". On the shipped corpus the correction moves
#: exactly one piece (`compound/boss_desk`, 1.20 m), because the authored
#: heights cluster either side of it already.
_COVER_HIGH_Z = cover_break_height()
_COVER_MAX_FOOTPRINT = 7.0   # if BOTH plan dims exceed this it's massing, not cover
_COVER_DEDUPE_R = 1.6   # don't add a cover marker within this of an existing one
_COVER_PER_ROOM_CAP = 5      # readability ceiling (thesis: don't over-cover)
_COVER_PER_ROOM_FLOOR = 2    # a contested room wants at least this many

# Roles that earn a callout landmark (one distinct anchor per major zone).
_LANDMARK_ROLES = {
    "objective_room", "public_entry", "finale", "loot_room", "safe_room",
    "vault_room", "staging",
}


def _centroid(bounds):
    x0, y0, x1, y1 = bounds
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def _area(bounds):
    x0, y0, x1, y1 = bounds
    return abs(x1 - x0) * abs(y1 - y0)


def _in_bounds(x, y, bounds):
    x0, y0, x1, y1 = bounds
    lo_x, hi_x = (x0, x1) if x0 <= x1 else (x1, x0)
    lo_y, hi_y = (y0, y1) if y0 <= y1 else (y1, y0)
    return lo_x <= x <= hi_x and lo_y <= y <= hi_y


def _story_height(spec):
    return float(spec.get("story_height", 3.6) or 3.6)


def _volume_story(spec, vol):
    """Best-guess the story a volume sits on from its base z."""
    sh = _story_height(spec)
    base_z = float(vol.get("z", 0.0)) - float(vol.get("size_z", 0.0)) / 2.0
    return int(round(base_z / sh)) if sh else 0


def _room_for_point(spec, x, y, story):
    """The smallest room on `story` whose bounds contain (x, y), or None."""
    best, best_area = None, None
    for r in spec.get("rooms", []):
        if int(r.get("story", 0)) != int(story):
            continue
        b = r.get("bounds")
        if not b or not _in_bounds(x, y, b):
            continue
        a = _area(b)
        if best is None or a < best_area:
            best, best_area = r, a
    return best


def _cover_markers(spec):
    return [m for m in spec.get("markers", [])
            if m.get("type") in ("cover_low", "cover_high")]


def _looks_like_cover(vol):
    name = str(vol.get("name", "")).lower()
    if any(s in name for s in _COVER_NAME_SKIP):
        return False
    if not any(h in name for h in _COVER_NAME_HINTS):
        return False
    sz = float(vol.get("size_z", 0.0))
    if sz < _COVER_MIN_Z or sz > _COVER_MAX_Z:
        return False
    sx, sy = float(vol.get("size_x", 0.0)), float(vol.get("size_y", 0.0))
    if sx > _COVER_MAX_FOOTPRINT and sy > _COVER_MAX_FOOTPRINT:
        return False
    return True


def cover_from_volumes(spec):
    """Tag cover-like volumes that have no cover marker as engagement points.

    Many presets model furniture as volumes (a teller line, market aisles, a
    manager desk) but only mark a couple as AI cover -- and heist branches that
    rebuild the marker list often drop cover entirely. This re-derives cover
    anchors from the geometry that is already there, so every contested room
    reaches a readable 3-5 engagement points (capped, never over-covered), and
    so sightlines/exposure analysis sees the cover that actually exists.

    Returns the number of cover markers added.
    """
    markers = spec.setdefault("markers", [])
    sh = _story_height(spec)

    # current cover, keyed by story, for dedupe + per-room counts
    existing = _cover_markers(spec)
    per_room = {}
    for m in existing:
        rid = m.get("room")
        if rid:
            per_room[rid] = per_room.get(rid, 0) + 1

    added = 0
    for vol in spec.get("volumes", []):
        if not _looks_like_cover(vol):
            continue
        x, y = float(vol.get("x", 0.0)), float(vol.get("y", 0.0))
        story = _volume_story(spec, vol)
        room = _room_for_point(spec, x, y, story)
        if room is None:
            continue                       # outside any room -> can't anchor it
        rid = room.get("id")
        if per_room.get(rid, 0) >= _COVER_PER_ROOM_CAP:
            continue                       # readability: stop over-covering
        # dedupe against existing cover on the same story
        clash = False
        for m in existing:
            if int(m.get("story_hint", round(float(m.get("z", 0.0)) / sh) if sh else 0)) != story:
                pass  # story_hint not stored on legacy markers; fall back to xy
            dx, dy = x - float(m.get("x", 0.0)), y - float(m.get("y", 0.0))
            if (dx * dx + dy * dy) ** 0.5 < _COVER_DEDUPE_R:
                clash = True
                break
        if clash:
            continue
        sz = float(vol.get("size_z", 1.0))
        mtype = "cover_high" if sz >= _COVER_HIGH_Z else "cover_low"
        marker = {
            "type": mtype,
            "id": "AUTO_" + str(vol.get("name", "cover")).upper(),
            "x": x, "y": y, "z": round(story * sh, 3),
            "room": rid,
            "meta": {"auto": "cover_from_volume", "from": vol.get("name")},
        }
        markers.append(marker)
        existing.append(marker)
        per_room[rid] = per_room.get(rid, 0) + 1
        added += 1
    return added


def add_landmarks(spec):
    """Drop one callout landmark at the centroid of each major zone.

    Landmarks are orientation anchors: they let a crew call "vault", "lobby",
    "extraction" and read the space at a glance instead of burning attention on
    navigation (Foreman: landmarks first; thesis 6.1.6: distinct callout areas
    stop people calling the wrong room). The marker is just the anchor + a label
    -- the art team makes it visually distinct.

    Returns the number of landmarks added.
    """
    markers = spec.setdefault("markers", [])
    sh = _story_height(spec)
    existing_lm = [m for m in markers if m.get("type") == "landmark"]
    added = 0
    for r in spec.get("rooms", []):
        if r.get("role") not in _LANDMARK_ROLES:
            continue
        b = r.get("bounds")
        if not b:
            continue
        cx, cy = _centroid(b)
        story = int(r.get("story", 0))
        # skip if a landmark already sits in this room / very close
        near = any(abs(cx - float(m.get("x", 0.0))) < 2.0
                   and abs(cy - float(m.get("y", 0.0))) < 2.0
                   and int(round(float(m.get("z", 0.0)) / sh)) == story
                   for m in existing_lm) if sh else False
        if near:
            continue
        marker = {
            "type": "landmark",
            "id": str(r.get("id", "zone")).upper(),
            "x": round(cx, 3), "y": round(cy, 3), "z": round(story * sh + 1.0, 3),
            "room": r.get("id"),
            "meta": {"auto": "landmark", "label": r.get("id"),
                     "role": r.get("role")},
        }
        markers.append(marker)
        existing_lm.append(marker)
        added += 1
    return added


# room role/id keywords -> the furniture archetype seeded there
_SEED_ARCHETYPES = (
    (("office", "manager", "exec", "admin", "suite"),
     [("desk", 1.6, 0.8, 0.75), ("cabinet", 0.9, 0.5, 1.4)]),
    (("storage", "stock", "back", "parts", "ware"),
     [("shelf_run", 2.6, 0.6, 1.7), ("pallet_stack", 1.2, 1.2, 1.0)]),
    (("bay", "garage", "loading", "deck"),
     [("crate_stack", 1.2, 1.2, 1.0), ("pallet_stack", 1.2, 1.2, 0.9)]),
    (("lobby", "floor", "hall", "concourse", "public", "booking", "ward"),
     [("counter_island", 2.2, 0.8, 1.05), ("planter_box", 1.4, 0.7, 0.9)]),
)
_SEED_DEFAULT = [("crate_stack", 1.1, 1.1, 0.95)]
_SEED_MIN_AREA = 30.0     # below this a bare room still reads fine
_SEED_MAX_PIECES = 4      # thesis: don't over-cover

#: ONE PIECE PER ROOM THAT CAN ACTUALLY BE FOUGHT BEHIND, and its FOOTPRINT
#: only -- the height comes from `shelter_height()`, so the archetype decides
#: what the thing looks like and the contract decides how tall it has to be.
#:
#: Separate from `_SEED_ARCHETYPES` because they answer different questions.
#: Those are the room's furniture: a room reads as lived-in because there are
#: desks and pallets in it, and 7 of the 9 stand below the height at which
#: cover works. That is not a defect in them. It becomes one only when a room
#: has NOTHING else, which is what this fixes -- the level's brief is props for
#: cover AND life, so the fix is one of the first rather than a raise of all
#: the second.
#:
#: Matched in order, and roof sits above bay on purpose: "deck" appears in
#: both and a helipad is not a loading bay.
_SEED_SHELTER = (
    (("roof", "helipad", "rooftop", "penthouse"), ("water_tank", 1.6, 1.6)),
    (("office", "manager", "exec", "admin", "suite"), ("shelf_unit", 1.0, 0.5)),
    (("storage", "stock", "back", "parts", "ware", "utility"),
     ("shelf_run", 2.6, 0.6)),
    (("ward", "clinic", "exam", "recovery", "holding", "cell"),
     ("locker_bank", 1.4, 0.6)),
    (("bay", "garage", "loading", "deck", "service"),
     ("crate_stack_tall", 1.2, 1.2)),
    (("lobby", "floor", "hall", "concourse", "public", "booking"),
     ("kiosk", 1.2, 1.2)),
)
_SEED_SHELTER_DEFAULT = ("crate_stack_tall", 1.1, 1.1)


def _seed_shelter(room):
    key = ((room.get("role") or "") + " " + room["id"]).lower()
    for words, piece in _SEED_SHELTER:
        if any(w in key for w in words):
            return piece
    return _SEED_SHELTER_DEFAULT


def _seed_archetype(room):
    key = ((room.get("role") or "") + " " + room["id"]).lower()
    for words, arch in _SEED_ARCHETYPES:
        if any(w in key for w in words):
            return arch
    return _SEED_DEFAULT


def _room_has_cover(spec, room):
    x0, y0, x1, y1 = room["bounds"]
    sh = _story_height(spec)
    for v in spec.get("volumes", []):
        # `_COVER_MIN_Z`, not a fourth hand-written 0.6. The literal was
        # copied here and would have gone stale the first time the constant
        # moved -- the same shape as a threshold asked of two spellings of
        # one number.
        if v.get("size_z", 0) < _COVER_MIN_Z or min(v.get("size_x", 0), v.get("size_y", 0)) < 0.3:
            continue
        if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1 and                 abs(v.get("z", 0) - (room.get("story", 0) * sh + v.get("size_z", 0) / 2)) < sh:
            return True
    for m in spec.get("markers", []):
        if m.get("type") in ("cover_low", "cover_high") and                 x0 <= m.get("x", 1e9) <= x1 and y0 <= m.get("y", 1e9) <= y1:
            return True
    return False


def _room_has_shelter(spec, room):
    """Is there anything in this room a body can actually fight from?

    `_room_has_cover` asks whether the room is FURNISHED, which is what "is
    this a bare kill box" wants. This asks whether any of that furniture stops
    the two sides seeing each other, which is what "can this room be fought
    in" wants -- and 39 of the 91 combat rooms in the shipped presets answered
    yes to the first and no to the second.

    A `cover_high` marker counts whatever its volume; `_COVER_HIGH_Z` IS the
    break height, so the marker means precisely "a solid here breaks the
    line". Same reasoning as `combat_audit._cover_in_room`, and deliberately
    the same answer -- an audit and a producer disagreeing about what shelter
    is would be two instruments for one question.
    """
    x0, y0, x1, y1 = room["bounds"]
    sh = _story_height(spec)
    for v in spec.get("volumes", []):
        if v.get("size_z", 0) < _COVER_HIGH_Z or min(v.get("size_x", 0), v.get("size_y", 0)) < 0.3:
            continue
        if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1 and                 abs(v.get("z", 0) - (room.get("story", 0) * sh + v.get("size_z", 0) / 2)) < sh:
            return True
    for m in spec.get("markers", []):
        if m.get("type") == "cover_high" and                 x0 <= m.get("x", 1e9) <= x1 and y0 <= m.get("y", 1e9) <= y1:
            return True
    return False


_STAIR_FIELDS = ("x", "y", "from_story", "to_story", "width", "run",
                 "style", "facing", "exterior", "transfer", "cut_slabs",
                 "step_rise", "n_steps", "id", "role", "stack_id", "meta")


def _stair_reserved_rects(spec):
    """Footprint + landing rects for every stair in a dict spec (all
    stories -- conservative for cover seeding)."""
    try:
        import stairwell
        from spec_types import Stairwell
    except ImportError:
        return []
    rects = []
    for s in spec.get("stairs", []) or []:
        try:
            st = Stairwell(**{k: s[k] for k in _STAIR_FIELDS if k in s})
        except TypeError:
            continue
        rects.append(stairwell.footprint_rect(st))
        rects.extend(e["rect"] for e in stairwell.stair_endpoints(st))
        # ...and the RESERVED rectangle the builder cuts and guards
        # (`flight_rect`). The guards stand just outside it
        # (`stairwell.stair_guards`, up to GUARD_THICK past its edge), up to
        # 0.55 m beyond `footprint_rect`, so a piece cleared against the
        # footprint alone could stand inside a guard wall.
        if getattr(st, "style", None) != "spiral":
            lo = min(st.from_story, st.to_story)
            hi = max(st.from_story, st.to_story)
            for k in range(lo, hi):
                rects.append(stairwell.flight_rect(st, k))
    return rects


#: A collision-free volume whose bottom is this far above its room's floor
#: is HUNG -- a neon sign, a bracket TV -- and is over the furniture, not
#: among it: a floor piece stands under it, and it hangs over a floor piece.
_HUNG_MIN = 1.8


def _on_storey(vz, vh, floor, sh):
    """Does a volume centred at `vz`, `vh` tall, reach into the storey whose
    floor is at `floor`? A slab-thick tolerance either side, so a piece
    standing on the floor and one hanging under the ceiling both count."""
    return vz + vh / 2.0 > floor + 0.05 and vz - vh / 2.0 < floor + sh - 0.05


def _seed_clear(spec, room, px, py, placed, half=0.0, above=None):
    """Candidate point clear of walls, openings, verticals, props, markers.
    `half` is the worst-case half-extent of the piece that will stand here:
    clearances are measured from the piece's EDGE, not its center -- a 2.6 m
    shelf run can intrude a ladder's climb envelope while its center is
    comfortably clear (found by the 100-seed regression sweep).

    `above`, when given, is the BOTTOM of a hung piece above the room's
    floor: volumes whose top is below it are not in its way. When it is
    None the piece stands on the floor and hung collision-free volumes
    (`_HUNG_MIN`) are not in its way. Everything else -- walls, openings,
    stairs, ladders, markers, the spread -- is asked as before."""
    story = room.get("story", 0)
    sh = _story_height(spec)
    floor = story * sh
    for p in spec.get("partitions", []):
        if p.get("story", 0) != story:
            continue
        if p["axis"] == "Y":
            cy = max(p["start"], min(py, p["end"]))
            d = math.hypot(px - p["pos"], py - cy)
        else:
            cx = max(p["start"], min(px, p["end"]))
            d = math.hypot(px - cx, py - p["pos"])
        if d < 1.0:
            return False
    for v in spec.get("volumes", []):
        vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
        # ON THIS STOREY. Until 0.132.0 every volume in the building was in
        # the way of every candidate, whatever its storey: a ground floor's
        # furniture blocked the floor above it in plan. Harmless while rooms
        # were sparse; a club's main floor is dense enough that the room
        # over it could not stand its stage anywhere. A volume is in the
        # way when its vertical extent overlaps the room's storey.
        if not _on_storey(vz, vh, floor, sh):
            continue
        if above is not None:
            if vz + vh / 2.0 - floor <= above:
                continue
        elif v.get("collision") == "none" and vz - vh / 2.0 - floor >= _HUNG_MIN:
            continue
        if abs(v["x"] - px) < v.get("size_x", 1) / 2 + 0.9 + half and \
                abs(v["y"] - py) < v.get("size_y", 1) / 2 + 0.9 + half:
            return False
    for s in spec.get("stairs", []):
        if math.hypot(s["x"] - px, s["y"] - py) < 2.6 + half:
            return False
    # the stair RESERVATION is bigger than a radius: the flight footprint
    # plus both landing rects (they reach ~run/2 + 2 m along the ascent
    # axis). Cover standing on a landing is a hard error since v0.78.
    for rect in _stair_reserved_rects(spec):
        if px + half > rect[0] - 0.3 and px - half < rect[2] + 0.3 and \
                py + half > rect[1] - 0.3 and py - half < rect[3] + 0.3:
            return False
    for l in spec.get("ladders", []):
        if math.hypot(l["x"] - px, l["y"] - py) < 1.6 + half:
            return False
    for m in spec.get("markers", []):
        if m.get("type") in ("objective", "loot") and                 math.hypot(m.get("x", 1e9) - px, m.get("y", 1e9) - py) < 1.2:
            return False
    # exterior + partition opening approach clearance
    hx = spec.get("footprint_x", 20) / 2
    hy = spec.get("footprint_y", 20) / 2
    for w in spec.get("ext_walls", []):
        if w.get("story", 0) != story:
            continue
        run = spec.get("footprint_x", 20) if w["wall"] in ("N", "S") else spec.get("footprint_y", 20)
        for op in w.get("openings", []):
            u = op.get("pos", 0.0) * run
            ox, oy = {"N": (u, hy), "S": (u, -hy), "E": (hx, u), "W": (-hx, u)}[w["wall"]]
            # FROM THE EDGE, like every other check here: a flat 1.5 m from
            # the CENTRE let a 1.6 m desk stand 0.2 m off a door jamb.
            if math.hypot(ox - px, oy - py) < 1.5 + half:
                return False
    for p in spec.get("partitions", []):
        if p.get("story", 0) != story:
            continue
        run = abs(p["end"] - p["start"])
        for op in p.get("openings", []):
            u = p["start"] + (op.get("pos", 0.0) + 0.5) * run
            ox, oy = (p["pos"], u) if p["axis"] == "Y" else (u, p["pos"])
            if math.hypot(ox - px, oy - py) < 1.5 + half:
                return False
    # A VAULT DOOR'S LEAF SWINGS 2.6 m OUT. The 1.5 m radius above is a
    # door's approach; a round vault door's open and breached leaf occupies a
    # rectangle in front of its face (`vault_room.swing_rect`), and a piece
    # standing there is a leaf that cannot open -- layout_lint L22 fails it.
    import vault_room
    for x0, y0, x1, y1 in vault_room.keepout_rects(spec, story):
        if (px + half > x0 - 0.3 and px - half < x1 + 0.3
                and py + half > y0 - 0.3 and py - half < y1 + 0.3):
            return False
    for (qx, qy) in placed:
        if math.hypot(qx - px, qy - py) < 2.2:
            return False
    return True


def seed_cover(spec):
    """Give every combat room something to fight from, and bare ones furniture.

    TWO PASSES, BECAUSE THERE ARE TWO WAYS A COMBAT ROOM FAILS and only one of
    them used to be looked at.

      * BARE. Big room, combat intent, not one solid in it -- the audit calls
        it a kill box. Gets 2-4 archetype pieces, spread out.
      * FURNISHED AND UNFIGHTABLE. Crates, desks, a counter, all modelled and
        lit, and every one of them short enough that both sides shoot over the
        top. Gets ONE piece at `shelter_height()` and keeps its furniture.

    The second was invisible: the guard was `_room_has_cover`, which answers
    "is there furniture here", so a room full of 0.9 m crates was covered and
    skipped, and the one thing it lacked was the one thing never added. **39
    of the 91 combat rooms in the shipped presets.** They look built and they
    cannot be fought in, which is the failure that survives a look at the
    screen.

    ONE piece, not a raise of the furniture. The brief for these levels is
    props that give cover AND life without overkill; a furnished room is not
    short of life. The over-cover thesis this module is built on argues
    against the alternative directly.

    Deterministic (spec seed + room id), additive, idempotent -- a re-run sees
    the shelter piece and skips -- and it never places near a door, an
    objective, a stair or a ladder. A room where nothing fits keeps its
    finding rather than getting a crate jammed into a doorway.

    Returns the number of volumes created.
    """
    import random
    base_seed = spec.get("seed", 0)
    added = 0
    building = club_building_id(spec)
    for room in spec.get("rooms", []):
        if not room.get("combat_range"):
            continue
        # A STRIP CLUB'S CLUB ROOMS ARE THE CLUB RECIPE'S. This pass keys
        # its pieces on the room's words, and on the `strip_club` preset
        # that put a kiosk, two planters and a counter island on the
        # main floor, shelf runs and pallets in the back bar (`back` is
        # a storage word), crate stacks in the VIP lounge -- and the
        # recipe, counting them as furniture already there, stopped its
        # wall run before the neon sign. What the recipe places is what
        # the room fights from: the vending machine when the wall run
        # draws it (1.83-1.9 m, solid), else the stage -- whose visual
        # volume reaches the ceiling and collides with nothing, and whose
        # deck is 1.18 m: both shelter instruments count it, and a
        # standing body sees over it. Stated here, not settled here.
        if is_strip_club_room(room, building):
            continue
        x0, y0, x1, y1 = room["bounds"]
        area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        if area < _SEED_MIN_AREA:
            continue
        bare = not _room_has_cover(spec, room)
        needs_shelter = not _room_has_shelter(spec, room)
        if not bare and not needs_shelter:
            continue
        rng = random.Random(f"{base_seed}:{room['id']}:seed_cover")
        arch = _seed_archetype(room)
        want = min(_SEED_MAX_PIECES, max(2, int(area // 45) + 1)) if bare else 0
        # jittered grid candidates, then greedy spread
        cands = []
        for i in range(6):
            for j in range(6):
                px = x0 + 1.2 + (i + rng.random() * 0.6) * (x1 - x0 - 2.4) / 6
                py = y0 + 1.2 + (j + rng.random() * 0.6) * (y1 - y0 - 2.4) / 6
                cands.append((px, py))
        rng.shuffle(cands)
        placed = []
        sh = _story_height(spec)

        # THE SHELTER PIECE FIRST, and only when the room has none. A room
        # full of 0.9 m crates used to be "covered" and skipped entirely, so
        # the one thing it was missing was the one thing never added.
        #
        # It is ONE piece. The brief for these levels is props that give cover
        # AND life without overkill, and a room that already has furniture is
        # not short of life -- it is short of somewhere to fight from. A room
        # that has neither gets this and then its furniture below.
        if needs_shelter:
            s_name, s_x, s_y = _seed_shelter(room)
            s_z = shelter_height()
            s_half = max(s_x, s_y) / 2.0
            for (px, py) in cands:
                if not _seed_clear(spec, room, px, py, placed, half=s_half):
                    continue
                sx, sy = (s_y, s_x) if rng.random() < 0.5 else (s_x, s_y)
                spec.setdefault("volumes", []).append({
                    "name": f"{s_name}_{room['id']}_shelter",
                    "x": round(px, 2), "y": round(py, 2),
                    "z": round(room.get("story", 0) * sh + s_z / 2, 3),
                    "size_x": sx, "size_y": sy, "size_z": round(s_z, 3),
                    "collision": "convex",
                    "material": _prop_material(spec, s_name),
                })
                placed.append((px, py))
                added += 1
                break
            # A room where nothing fits keeps its finding rather than getting
            # a piece jammed into a doorway. `combat_audit` still reports it,
            # which is the honest outcome: the geometry has no room for
            # shelter, and that is a fact about the room.

        arch_half = max(max(sx, sy) / 2 for _, sx, sy, _ in arch)
        for (px, py) in cands:
            if len(placed) >= want:
                break
            if not _seed_clear(spec, room, px, py, placed, half=arch_half):
                continue
            name, sx, sy, sz = arch[len(placed) % len(arch)]
            if rng.random() < 0.5:
                sx, sy = sy, sx      # vary orientation
            spec.setdefault("volumes", []).append({
                "name": f"{name}_{room['id']}_{len(placed)}",
                "x": round(px, 2), "y": round(py, 2),
                "z": round(room.get("story", 0) * sh + sz / 2, 3),
                "size_x": sx, "size_y": sy, "size_z": sz,
                "collision": "convex",
                "material": _prop_material(spec, name),
            })
            placed.append((px, py))
            added += 1
    return added


#: FURNITURE: what a room gets, as a RECIPE per room KIND (0.131.0).
#:
#: WHAT THIS REPLACED, kept because each part of it was a finding. Until
#: 0.130.0 this was `_FURNITURE`, six rows of room keywords matched by
#: SUBSTRING against "role id", each naming three or four pieces placed round
#: robin (`pieces[k % len(pieces)]`) at one size each, and a
#: `_FURNITURE_DEFAULT` of a low table and a chair for everything else. The
#: walker, in `country_club_a01`'s 560 m2 `wine_cellar` on cold run 9052:
#: "need a lot more species for this room, its just a bunch of chairs and
#: tables with nothing on it, boring". Measured then: that room matched no
#: keyword and got 27 pieces of 2 species; 272 of 691 library rooms took the
#: default row; "hall" sent `cellar_hall` to lobby counters and "service"
#: sent `food_service` to workbenches; one size per species meant one mesh,
#: repeated (six furniture GLBs for 97 pieces in that building); and nothing
#: ever stood on a top (docs/proposals/INTERIOR_FURNISHING.md).
#:
#: NOTHING MID-FLOOR REACHES SHELTER HEIGHT, which is the invariant and not
#: the one first written here. The 0.122.0 draft said every floor piece sits
#: below `_COVER_MIN_Z` (0.60) and `test_furnish` refuted it on its first
#: run: a desk is 0.75 and a floor safe is 1.00. A desk IS low cover, here
#: and in a real office. What `seed_cover`'s over-cover thesis protects is
#: SHELTER -- somewhere a body can fight from, at `cover_break_height` --
#: and this pass never creates one: anything that tall goes against a wall.
#:
#: Names are chosen so `prop_species.species_for_name` routes every one of
#: them to a species Zoo builds, at a size inside that species' genome
#: range. A furniture volume that comes out a grey box is the defect this
#: pass exists to reduce.
#:
#: A piece: ``name`` (what routes it), ``sizes`` as (long, short, height)
#: with height None for "to the ceiling", ``where`` wall / floor / cluster,
#: ``front`` when the species has a face a body uses (it must face the
#: room), ``stock`` / ``form`` / ``variants`` for Zoo's dressing fields,
#: ``seats`` for the chairs a host brings, ``most`` per room.
#:
#: 0.132.0: ``where`` may also be ``centre`` (the room's middle first: a
#: stage) or ``seat`` (only ever brought by a host, never placed alone);
#: ``variants`` is True for Zoo's usual four or the count itself
#: (`neon_sign` has 24, one per name); ``lift`` is the height of a HUNG
#: piece's centre above the floor (a sign, a bracket TV) in place of h/2;
#: ``collision`` "none" for a piece a body never meets; ``deck`` the height
#: of the invisible collider written under a visual-only tall piece -- a
#: stage is authored to the ceiling so Zoo runs the pole up, and a body
#: meets its 0.8 m platform, not a box to the slab (see `_volume`).
#:
#: 0.136.0: ``lane`` marks a piece that needs a clear THROWING LANE in front of
#: it (`dart_lane`); ``most_big`` is ``(area, most)``, a larger room's allowance.
def _piece(name, sizes, where, front=False, stock=None, variants=False,
           form=None, seats=None, most=None, lift=None, collision="convex",
           deck=None, lane=False, most_big=None):
    return {"name": name, "sizes": tuple(sizes), "where": where,
            "front": front, "stock": stock, "variants": variants,
            "form": form, "seats": seats, "most": most, "lift": lift,
            "collision": collision, "deck": deck, "lane": lane,
            "most_big": most_big}


_PIECES = {p["name"]: p for p in (
    # --- against a wall, front to the room ---
    _piece("shelf_run", ((2.6, 0.6, 1.9), (2.0, 0.5, 1.9), (1.2, 0.5, 1.8),
                         (2.4, 0.6, 2.1)), "wall", front=True),
    _piece("rack_wine", ((1.8, 0.4, 1.9), (1.2, 0.4, 1.9), (2.4, 0.45, 2.0)),
           "wall", front=True),
    _piece("cabinet_file", ((0.9, 0.5, 1.4), (0.6, 0.5, 1.3),
                            (0.9, 0.6, 1.05)), "wall", front=True),
    _piece("cabinet_supply", ((1.0, 0.5, 1.8), (0.9, 0.6, 1.4),
                              (1.2, 0.5, 1.05)), "wall", front=True,
           stock="storage", variants=True),
    _piece("cabinet_locker", ((1.2, 0.5, 1.9), (0.9, 0.5, 1.9),
                              (1.8, 0.5, 1.9)), "wall", front=True),
    _piece("cabinet_tool", ((0.9, 0.5, 1.8), (0.7, 0.5, 1.0),
                            (1.2, 0.6, 1.8)), "wall", front=True),
    _piece("cabinet_panel", ((0.9, 0.5, 1.8), (0.6, 0.5, 1.2)), "wall",
           front=True),
    _piece("workbench", ((2.0, 0.8, 0.9), (1.6, 0.7, 0.9), (2.4, 0.8, 0.95)),
           "wall", front=True),
    _piece("counter_service", ((2.2, 0.8, 1.05), (1.6, 0.7, 1.0),
                               (3.0, 0.8, 1.05)), "wall", front=True, most=2),
    _piece("counter_bar", ((3.0, 0.8, 1.08), (4.0, 0.8, 1.08),
                           (2.4, 0.7, 1.05)), "wall", front=True, stock="bar",
           variants=True, seats=("counter", 2, 3), most=1),
    _piece("counter_kitchen", ((2.2, 0.7, 0.92), (1.6, 0.7, 0.92),
                               (3.0, 0.7, 0.92)), "wall", front=True,
           stock="kitchen", variants=True),
    _piece("grill", ((1.2, 0.9, 1.05), (1.6, 0.9, 1.05)), "wall", front=True,
           most=1),
    # A FLOOR SAFE HAS A DOOR, and until 0.131.0 it was a floor piece written
    # with no rotation: in bank_branch_a02's basement one stood beside the new
    # vault door showing its blank back to the approach.
    _piece("safe_floor", ((0.9, 0.9, 1.0), (0.6, 0.6, 0.8), (0.8, 0.7, 1.2)),
           "wall", front=True, most=2),
    _piece("tank_water", ((1.2, 1.2, 1.8), (1.4, 1.4, 2.2)), "wall", most=1),
    # Zoo's furnace and water heater stand on a pad the slot's footprint and
    # run the flue to the slot's top, "so the volume should be authored to
    # the ceiling" (Zoo 0.84.0): height None is the storey's clear height.
    _piece("furnace", ((1.0, 0.9, None), (1.2, 1.2, None)), "wall",
           front=True, form="furnace", most=1),
    _piece("water_heater", ((0.6, 0.6, None), (0.5, 0.5, None)), "wall",
           front=True, form="water_heater", most=1),
    # Zoo 0.87.0 rebuilt the vending machine with four variants and a brand
    # on each; with `most=1` and no variant every machine of one size in a
    # building sold the same thing. Up to three a room where a recipe
    # places them (lobbies, halls, shop floors, clubs), each its own brand.
    _piece("vending", ((0.85, 0.75, 1.83), (1.0, 0.8, 1.9)), "wall",
           front=True, most=3, variants=True),
    _piece("atm", ((0.6, 0.55, 1.45),), "wall", front=True, most=1),
    _piece("payphone", ((0.75, 0.5, 2.3),), "wall", front=True, most=1),
    _piece("chair_waiting", ((2.4, 0.6, 0.9), (1.8, 0.6, 0.9),
                             (3.0, 0.6, 0.9)), "wall", front=True),
    _piece("booth", ((1.8, 0.75, 1.15), (2.4, 0.75, 1.15)), "wall",
           front=True, form="booth", variants=True),
    _piece("sofa", ((2.0, 0.9, 0.85), (1.6, 0.85, 0.85)), "wall", front=True,
           form="sofa", variants=True, most=2),
    # --- on the floor ---
    _piece("desk", ((1.6, 0.8, 0.75), (1.4, 0.7, 0.75), (1.8, 0.9, 0.76)),
           "floor", front=True, stock="office", variants=True,
           seats=("desk", 1, 1)),
    _piece("table_low", ((1.0, 0.6, 0.45), (1.2, 0.6, 0.45)), "floor"),
    _piece("table_dining", ((1.2, 0.8, 0.74), (0.9, 0.9, 0.74),
                            (1.6, 0.9, 0.74)), "floor", seats=("table", 0, 4)),
    _piece("table_tasting", ((1.2, 0.8, 0.9), (1.0, 1.0, 0.9)), "floor",
           seats=("table", 2, 2)),
    _piece("table_work", ((1.6, 0.8, 0.9), (1.2, 0.7, 0.9)), "floor"),
    _piece("table_count", ((1.6, 0.9, 0.76), (2.0, 0.9, 0.76)), "floor",
           stock="vault", variants=True, seats=("table", 0, 2)),
    _piece("pool_table", ((2.0, 1.14, 0.79), (2.4, 1.3, 0.8)), "floor",
           variants=True, most=2),
    # --- in clusters of 2-4, packed 0.3-0.8 m apart ---
    _piece("cartons", ((0.9, 0.6, 1.0), (1.2, 0.8, 1.4), (0.6, 0.4, 0.6),
                       (1.6, 1.2, 1.2), (0.5, 0.4, 0.9)), "cluster",
           variants=True),
    _piece("dust_sheet", ((2.0, 0.9, 0.85), (1.0, 0.8, 0.9), (0.8, 0.8, 1.0),
                          (1.8, 1.0, 1.4)), "cluster", variants=True),
    _piece("barrel_wine", ((0.6, 0.6, 0.9), (0.58, 0.58, 0.88),
                           (0.8, 0.8, 1.2)), "cluster"),
    _piece("barrel_drum", ((0.58, 0.58, 0.88), (0.6, 0.6, 0.9)), "cluster"),
    _piece("pallets", ((1.2, 1.0, 0.95), (1.2, 1.0, 1.4), (1.0, 1.0, 0.7)),
           "cluster"),
    _piece("litter_bin", ((0.6, 0.6, 1.0), (0.5, 0.5, 0.85)), "cluster"),
    _piece("stanchion", ((0.35, 0.35, 1.0),), "cluster"),
    # --- THE STRIP CLUB (Zoo 0.88.0). The walker: "strip clubs should have
    # a dingy lived in feel, dark with colored lights, couches and bars";
    # the layout comp is a one-storey windowless neighbourhood club with two
    # bar areas whose pole stage stands INSIDE the bar with stools round it,
    # CRTs on brackets. Names route to Zoo's `club_stage`, `bar_stool`,
    # `crt_tv`, `booth_seat`, `neon_sign`, `cocktail_table`, `club_chair`
    # (`prop_species`); sizes sit inside each genome's range. ---
    #
    # A STAGE IS AUTHORED TO THE CEILING (height None): Zoo builds the 0.8 m
    # platform (bar_stage: the 1.18 m deck) and runs the pole to the slot's
    # top; at 0.8 m it builds a platform with no rail and no pole. The
    # visual volume carries no collision of its own -- a box to the slab
    # in the middle of the main floor would be a wall to the nav bake and
    # to a body -- and `_volume` writes an invisible `stage_deck_*` collider
    # of the platform's height under it, which is what Zoo's own colliders
    # (bands inscribed in the outline, the steps) agree with.
    _piece("stage_bar", ((6.0, 3.6, None), (5.0, 3.2, None), (7.0, 4.0, None)),
           "centre", form="bar_stage", stock="bar", variants=True,
           seats=("stool", 6, 10), most=1, collision="none", deck=1.18),
    # no variant on the round stage: Zoo's `honour_dressing` drops one on a
    # `club_stage` without stock ("would change nothing but wear noise"),
    # and with it the form -- the all-or-nothing rule, asked of Zoo in
    # `test_zoo_honours_every_dressing_furnish_writes`
    _piece("stage_round", ((5.0, 4.0, None), (4.0, 4.0, None), (6.0, 5.0, None)),
           "centre", form="round", most=1, collision="none", deck=0.8),
    # A BAR COUNTER FOR THE LONG ROOM, stools along its front -- and, since
    # 0.137.0, Zoo's `bar` FORM (a brass foot rail under the customer
    # overhang, tap towers and a register on the service side) and its
    # DENSE bar top (`bar_dense`: liquor rows, glass towers, cocktails and
    # a speed rail of spouted bottles) in place of the sparse `bar` stock.
    # The dive bar is a later slice and keeps `counter_bar` as it is.
    _piece("counter_club", ((4.0, 0.8, 1.08), (5.0, 0.8, 1.1), (3.0, 0.8, 1.08)),
           "wall", front=True, form="bar", stock="bar_dense", variants=True,
           seats=("stool", 3, 5), most=2),
    # THE BACK BAR (Zoo 0.92.0) -- never placed on its own: it belongs to a
    # bar counter and `back_bar_club_counters` stands it against the wall
    # behind one, with a bartender's aisle between. `where` is `pair` for
    # the same reason `bar_stool`'s is `seat`.
    _piece("back_bar", ((3.0, 0.5, 2.4), (4.0, 0.5, 2.4), (5.0, 0.5, 2.4)),
           "pair", front=True, variants=True),
    # THE BAR'S RETURN END -- the short leg that makes the counter an L
    # where the room's corner allows, closing one end of the staff aisle.
    # A PLAIN counter and not a `counter_club`: it is the bar's panelled
    # end, so it carries no foot rail, no taps, no register and no bottles
    # (the `bar` form and the dense top belong on the run a customer
    # stands at), and no stools, because there is nothing to sit at. Named
    # `counter_end` so `prop_species` routes it to `counter` on the
    # keyword the row already holds.
    _piece("counter_end", ((1.25, 0.8, 1.08),), "pair", front=True),
    _piece("sofa_club", ((2.0, 0.9, 0.85), (2.4, 0.9, 0.85), (1.6, 0.85, 0.85)),
           "wall", front=True, form="sofa", variants=True, most=4),
    # HUNG ON THE WALL, in free air above the furniture: the sign's centre
    # at 2.2 m (Lux's `neon` spill sits proud of its face), the TV's at
    # 2.1 m, tipped toward the room by Zoo. No collision: a body's head is
    # 1.8 m and the nav bake's clearance is the same number.
    # ONE sign a room: the variant is the club's name (crc32 of the
    # building), so a second sign is the same name again -- seen twice on
    # `a01`'s east wall, 7 m apart, in the first frames.
    _piece("neon_sign", ((1.6, 0.1, 0.7), (1.4, 0.1, 0.6), (2.0, 0.1, 0.7)),
           "wall", front=True, variants=24, most=1, lift=2.2,
           collision="none"),
    # A VARIANT IS A BALLGAME (0.135.1). Zoo 0.90.0 draws the screen from the
    # variant -- 0 and 1 are always one football and one baseball game -- and
    # honours form `bracket` with variants 0..3. Zoo 0.89.0 dropped the form
    # when a variant was asked (measured: a stand set was built), so 0.135.0
    # wrote none and a01's three sets showed one game, all football.
    _piece("wall_tv", ((0.6, 0.55, 0.5), (0.7, 0.6, 0.55)), "wall",
           front=True, form="bracket", most=3, lift=2.1, collision="none",
           variants=True),
    _piece("table_cocktail", ((0.75, 0.75, 0.74), (0.8, 0.8, 0.76),
                              (0.7, 0.7, 0.72)), "floor", form="cloth",
           stock="bar", variants=True, seats=("club", 2, 3)),
    # THE DARTBOARD (Zoo 0.91.0). The walker: "dart boards in the strip
    # clubs. The kind where you use chalk to keep your score". Zoo's
    # `dartboard` is a wall cabinet whose slot is the OPEN footprint -- the
    # doors swung out -- and whose BULL IS THE SLOT'S CENTRE HEIGHT, so
    # `lift` is the regulation bull height, 1.73 m above the floor. Zoo
    # builds the cabinet box's collider and nothing for the doors, so the
    # volume carries none of its own (a box to the doors' reach would stop
    # a body in mid-air). A piece with a `lane` is placed last, where the
    # oche distance and a standing body are clear in front of it
    # (`place_fixtures`). One a room; a floor past 300 m2 may take two.
    _piece("dartboard", ((1.1, 0.36, 0.9), (1.2, 0.38, 0.92)), "wall",
           front=True, variants=True, most=1, most_big=(300.0, 2),
           lift=1.73, collision="none", lane=True),
    # THE CIGARETTE MACHINE (Zoo 0.91.0). The walker: "retro cigarettes'
    # machines in the strip club. (Maybe we'll put em in other buildings
    # too, it was the 1990s where smoking in public was still legal in
    # PA)". A floor-standing pull-knob machine against a wall, front to the
    # room. NAMED `cigarettes`, not `cigarette_machine`: "machine" is one of
    # `_COVER_NAME_HINTS`, and `cover_from_volumes` would mark every one as
    # cover, which the vending machine beside it is not.
    _piece("cigarettes", ((0.88, 0.45, 1.5), (0.9, 0.48, 1.55)), "wall",
           front=True, variants=True, most=1),
    # the seats a club host brings: never placed on their own
    _piece("club_chair", ((0.78, 0.75, 0.78),), "seat", variants=True),
    _piece("bar_stool", ((0.42, 0.42, 0.76),), "seat", variants=True),
)}

#: The invisible colliders `_volume` writes under a visual-only piece. Not
#: pieces -- nothing places one -- but a stem the idempotence mark and the
#: refurnish migration must know, or a room is furnished twice.
_COLLIDER_STEMS = ("stage_deck",)

#: The chairs a host brings: a table's go round it, a desk's sits at its
#: front, a bar's stand along the room side. They are `chair_set_*` so they
#: route to `chair` and the idempotence mark knows them. A club host brings
#: `club_chair`s (a cocktail table) or `bar_stool`s (a bar), whose sizes are
#: their pieces'.
_SEAT = (0.5, 0.5)
_SEAT_PIECES = {"stool": "bar_stool", "club": "club_chair"}

#: Room KINDS, matched on WHOLE TOKENS of the room id, in this order: the
#: first kind any token of the id names wins, so `wine_cellar` is a wine
#: cellar before it is a basement and `cellar_hall` a basement before it is a
#: lobby. Tokens, not substrings -- "hall" inside `cellar_hall` sent it to
#: lobby counters and "service" inside `food_service` to workbenches. The
#: id's tokens come first because the id is what the author wrote about
#: this room; the role is what the grammar needed from it.
_ROOM_KINDS = (
    ("corridor", ("corridor", "approach", "landing", "stair", "stairwell",
                  "stairs", "catwalk", "vomitory", "gantry", "bridge",
                  "hallway", "passage")),
    ("wine_cellar", ("wine", "barrel", "champagne", "cask")),
    ("vault", ("vault", "count", "counting", "cage", "safe", "evidence",
               "strong", "deposit", "lockup", "armory", "money", "cash",
               "bond", "bonded", "loot")),
    ("kitchen", ("kitchen", "deli", "prep", "cooler", "walkin", "dough",
                 "food", "galley")),
    ("locker", ("locker", "lockers")),
    ("mechanical", ("utility", "server", "boiler", "mech", "plant",
                    "machine", "maintenance", "equipment", "comms")),
    ("office", ("office", "offices", "manager", "exec", "executive", "suite",
                "security", "control", "detective", "admin", "boardroom",
                "study", "clerk", "dispatch", "ops", "curator", "bullpen",
                "harbormaster", "judges", "chambers", "booth", "booths",
                "attendant", "press", "broadcast")),
    ("storage", ("storage", "stock", "stockroom", "store", "parts", "supply",
                 "archive", "records", "stash", "baggage", "parcel",
                 "receiving", "shed", "gear", "sort", "backstock")),
    ("garage", ("garage", "bay", "dock", "loading", "workshop", "works",
                "laydown")),
    ("club", ("lounge", "club", "bar", "dining", "taproom", "parlor",
              "gaming", "social", "vip", "skybox", "tavern", "pub", "game",
              "trophy")),
    ("apartment", ("apartment", "bedroom", "living", "flat", "home")),
    ("basement", ("basement", "cellar", "under", "lower")),
    ("lobby", ("lobby", "waiting", "reception", "concourse", "foyer",
               "atrium", "entry", "checkin", "booking", "public", "rotunda",
               "banking", "fare")),
    # BEYOND THE PROPOSAL'S TABLE, and why. Its lobby row names lobby,
    # waiting, reception and concourse; the first draft here added "hall"
    # and "floor" to it, and the library came back with 130 payphones and
    # 145 ATMs, one in nearly every `upper_hall` and `sales_floor`. A hall
    # is somewhere people sit; a shop floor is shelving and stock.
    ("shop_floor", ("floor", "sales", "retail", "showroom", "market",
                    "aisle", "aisles", "stall", "customer", "shop")),
    ("hall", ("hall", "gallery", "galleries", "exhibit", "chapel",
              "assembly", "courtroom", "courtrooms", "viewing", "artifact")),
)
#: A room whose id names no kind is read by its ROLE: the role's own tokens
#: through the same table (`public_entry` is a lobby, `loot_room` a vault),
#: except the level grammar's roles, which say what the level needs from a
#: room and nothing about what is in it -- `open_floor` is not a shop.
_ROLE_KINDS = {"staff_only": "locker", "connector": None,
               "objective_room": None, "fortifiable": None, "open_floor": None,
               "staging": None, "route_node": None, "finale": None}

#: THE STRIP CLUB, read ahead of the table above and only inside a building
#: whose id says `strip_club`: the same tokens name a country club's lounge
#: and a tavern's bar, which are the `club` kind and not this one. A
#: `main_floor` is the club floor here and a shop floor anywhere else (0.131.0
#: furnished `strip_club_a01`'s main floor with shelving and a vending
#: machine); `champagne` was a wine cellar. In the library this claims
#: `main_floor` x3, `vip_wing`, `back_bar`, `vip_mezz` and `champagne_wing`;
#: the cash offices, back rooms, cellar and count room keep their kinds.
_STRIP_CLUB_TOKENS = frozenset(("club", "lounge", "vip", "champagne", "go",
                                "gogo", "cabaret", "bar", "stage", "dance"))
_STRIP_CLUB_ID = "strip_club"


def _strip_club_building(building):
    return _STRIP_CLUB_ID in str(building or "").lower()


def club_building_id(spec):
    """The id a building's KIND is read from: its name and, on a
    generated spec, the recipe that made it (`preset`). A dict spec or a
    loaded `LevelSpec`. Level Factory names its levels
    `lf_<mission>_<seed>`, so a `strip_club` recipe it built for
    `club_block_001` is `lf_club_block_001_7`, and read by name alone it
    is a shop floor with a vending machine (0.131.0's defect, one layer
    up). The recipe's name says what the name does not."""
    if isinstance(spec, dict):
        parts = (spec.get("name"), spec.get("preset"))
    else:
        parts = (getattr(spec, "name", None), getattr(spec, "preset", None))
    return " ".join(str(p) for p in parts if p)


def is_strip_club_room(room, building):
    """Is `room` (a dict with `id`) a club room of a strip club building?
    The one rule, shared by `furnish` and the light manifest."""
    if not _strip_club_building(building):
        return False
    tokens = set(str(room.get("id", "")).lower().replace("-", "_").split("_"))
    return bool(tokens & _STRIP_CLUB_TOKENS) or {"main", "floor"} <= tokens

#: What each kind is made of (the proposal's table). `anchors` are placed
#: first, one or two of them; about half the target is the `wall` run; the
#: rest alternates `floor` sets and `clusters` of ``(pool, least, most)``.
_RECIPES = {
    "basement": {"anchors": ("furnace", "water_heater"),
                 "wall": ("shelf_run", "cabinet_file", "workbench"),
                 "floor": (),
                 "clusters": ((("cartons", "pallets", "barrel_drum",
                                "dust_sheet"), 2, 4),)},
    "wine_cellar": {"anchors": ("rack_wine",),
                    "wall": ("rack_wine", "rack_wine", "shelf_run"),
                    "floor": ("table_tasting",),
                    "clusters": ((("barrel_wine",), 2, 4),
                                 (("cartons", "dust_sheet"), 2, 3))},
    "storage": {"anchors": ("shelf_run",),
                "wall": ("shelf_run", "cabinet_supply", "cabinet_file"),
                "floor": (),
                "clusters": ((("cartons", "pallets"), 2, 4),)},
    "mechanical": {"anchors": ("water_heater", "furnace", "tank_water"),
                   "wall": ("cabinet_panel", "shelf_run"),
                   "floor": (),
                   "clusters": ((("barrel_drum", "cartons", "litter_bin"),
                                 2, 3),)},
    "club": {"anchors": ("counter_bar", "pool_table"),
             "wall": ("booth", "shelf_run", "booth", "vending"),
             "floor": ("table_dining",),
             "clusters": (), "fixtures": ("cigarettes",)},
    # THE STRIP CLUB. Anchors are chosen by the room's shape
    # (`_club_anchors`), all of them placed: a bar stage as the centrepiece
    # with stools round it, or in a long room a round stage and a bar
    # counter on a wall, and a second bar past 300 m2. The wall run is
    # couches, the name in neon, CRTs on brackets; the floor is cocktail
    # tables with two or three tub chairs each. Denser than a hall
    # (`per_area`): a club floor is small tables, not open space.
    "strip_club": {"anchors": ("stage_bar",),
                   "wall": ("sofa_club", "neon_sign", "wall_tv", "sofa_club",
                            "wall_tv", "sofa_club", "vending"),
                   "floor": ("table_cocktail",),
                   "clusters": (), "per_area": 24.0, "all_anchors": True,
                   # placed after the room is furnished (`place_fixtures`)
                   "fixtures": ("dartboard", "cigarettes")},
    "office": {"anchors": ("desk",),
               "wall": ("cabinet_file", "shelf_run", "cabinet_file"),
               "floor": ("desk",),
               "clusters": ((("cartons",), 2, 3),)},
    "kitchen": {"anchors": ("grill",),
                "wall": ("counter_kitchen", "shelf_run", "counter_kitchen"),
                "floor": ("table_work",),
                "clusters": ((("cartons", "litter_bin"), 2, 3),)},
    "locker": {"anchors": ("cabinet_locker",),
               "wall": ("cabinet_locker", "chair_waiting"),
               "floor": (),
               "clusters": ((("cartons",), 2, 3),)},
    "vault": {"anchors": ("safe_floor",),
              "wall": ("shelf_run", "cabinet_locker", "safe_floor"),
              "floor": ("table_count",),
              "clusters": ((("cartons",), 2, 3),)},
    "lobby": {"anchors": ("counter_service",),
              "wall": ("chair_waiting", "chair_waiting", "sofa", "atm",
                       "vending", "payphone"),
              "floor": ("table_low",),
              "clusters": ((("stanchion",), 3, 4), (("litter_bin",), 1, 1)),
              "fixtures": ("cigarettes",)},
    "hall": {"anchors": ("counter_service",),
             "wall": ("chair_waiting", "shelf_run", "chair_waiting",
                      "cabinet_file", "vending"),
             "floor": ("table_dining",),
             "clusters": ((("litter_bin",), 1, 1),),
             "fixtures": ("cigarettes",)},
    "shop_floor": {"anchors": ("counter_service",),
                   "wall": ("shelf_run", "shelf_run", "cabinet_file",
                            "vending"),
                   "floor": (),
                   "clusters": ((("cartons",), 2, 3), (("litter_bin",), 1, 1))},
    "garage": {"anchors": ("workbench",),
               "wall": ("shelf_run", "cabinet_tool"),
               "floor": (),
               "clusters": ((("barrel_drum", "pallets"), 2, 4),)},
    "apartment": {"anchors": ("sofa",),
                  "wall": ("shelf_run", "cabinet_file"),
                  "floor": ("table_dining",),
                  "clusters": ((("cartons",), 2, 3),)},
    # A corridor is for walking through: at most two pieces, on its walls.
    "corridor": {"anchors": (), "wall": ("litter_bin", "cabinet_file",
                                         "vending"),
                 "floor": (), "clusters": (), "cap": 2},
    # Anything else: a wall run and ONE cluster. Not a table and chairs --
    # that default is what the walker called boring.
    "fallback": {"anchors": (), "wall": ("shelf_run", "cabinet_file",
                                         "chair_waiting"),
                 "floor": (),
                 "clusters": ((("cartons", "dust_sheet"), 2, 4),),
                 "one_cluster": True},
}
#: Below grade, a room that is not a basement, vault or corridor by name
#: still gets a basement's clutter among its clusters.
_BASEMENT_CLUSTER = (("cartons", "dust_sheet"), 2, 3)
#: A club room longer than this (long side over short) gets a round stage
#: and a wall bar rather than the bar stage in its middle; past this area it
#: gets a second bar (the comparison club has two bar areas).
_CLUB_LONG_ASPECT = 2.5
_CLUB_SECOND_BAR_AREA = 300.0


def _club_anchors(room):
    x0, y0, x1, y1 = room["bounds"]
    w, d = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    long_room = max(w, d) / min(w, d) >= _CLUB_LONG_ASPECT
    out = ["stage_round", "counter_club"] if long_room else ["stage_bar"]
    if w * d >= _CLUB_SECOND_BAR_AREA:
        out.append("counter_club")
    return tuple(out)

#: At most this many of one (piece, size) in a room: past it a room reads as
#: one mesh repeated, which is the other half of "boring".
_SAME_PIECE_MAX = 4
#: Sizes per piece per BUILDING, drawn from the piece's list by the spec's
#: seed: a building has a few desk sizes, not one and not all of them.
_PALETTE = 3
#: Gap between members of a cluster, edge to edge (the proposal's 0.3-0.8 m).
#: Below the 0.8 m a 0.4 m-radius body needs, so a cluster is one obstacle to
#: the navmesh, and is cleared from everything else as one.
_CLUSTER_GAP = (0.3, 0.8)
#: A cluster's longest side; past it a cluster is a wall across the room.
_CLUSTER_MAX_SPAN = 3.6
#: A cluster member's height ceiling: every cluster stands mid-floor.
_CLUSTER_MAX_H = 1.5
#: A chair's small turn off square when it is turned at all (degrees).
_SEAT_TURN = (10.0, 20.0)

#: Names 0.122.0-0.130.0 wrote, so a room those versions furnished is still
#: recognised as furnished (the idempotence mark) and is not furnished again.
_LEGACY_STEMS = ("chair", "cabinet_file", "shelf_run", "cabinet_supply",
                 "table_work", "workbench", "cabinet_tool", "cabinet_locker",
                 "safe_floor", "tank_water", "cabinet_panel", "chair_waiting",
                 "table_low", "counter_service", "desk")
_FURNISH_MIN_AREA = 9.0    # below this a room is a cupboard
#: A chair is a SEAT AND A BACK, 0.9 m to the top of the back. 0.45 m -- the
#: seat alone -- was the first value here, and it is below Zoo's `chair`
#: height range (0.5-1.1), so every chair this pass wrote in 0.122.0 and
#: 0.123.0 fell back to a plain box: cold run 9045's hall frame is a table
#: flanked by two wooden cubes. Still well under shelter height.
_CHAIR_H = 0.9
_FURNISH_PER_AREA = 16.0   # one piece per this many square metres
_FURNISH_MAX = 10          # past this a room stops being walkable


def _room_tag(room):
    """A room's tag for furniture names: ``r`` and a crc32 of its id. Digits
    only after the ``r``, so no species keyword can appear in it."""
    import zlib
    return "r%08x" % (zlib.crc32(str(room.get("id", "")).encode("utf-8")) & 0xFFFFFFFF)


#: What a placed piece is made of, by the first keyword in its name. A piece
#: that names nothing is wood. NEVER the building's `default_material`: that is
#: the wall skin, and a solid wearing the wall is a solid nobody sees until they
#: walk into it (the walker, cold run 9048).
#:
#: A SOFA'S MATERIAL IS ITS UPHOLSTERY (Zoo 0.88.0, "not Zoo's, found on the
#: way"): `booth_seat` takes the slot's material as the kind it is covered
#: in, and every booth and sofa this pass wrote wore `wood`, so a sofa built
#: from one carried no leather at all. Leather now, on every booth, sofa and
#: couch in the library. A stool's slot material builds its column -- bare
#: chrome, not a wood post; a sign's backer and a TV's housing are painted
#: sheet (delco_1997's plastic pack is red-orange and not tintable).
_PROP_MATERIALS = (
    (("safe", "tank", "locker", "panel", "hvac", "vault", "roof_ac", "ac_unit",
      "condenser", "generator", "dumpster", "furnace", "heater", "grill",
      "vending", "atm", "payphone", "stanchion", "litter_bin", "drum"),
     "metal"),
    (("booth", "sofa", "couch"), "leather"),
    (("stool",), "metal_bare"),
    (("neon", "tv", "cigarette"), "metal_painted"),
    # the species' own kind, so Zoo's stem carries no `_m` (0.136.0)
    (("dartboard",), "wood_stained"),
    # ...and the back bar's, for the same reason (0.137.0). No earlier row
    # here claims it -- the `bar_` keyword that would is in
    # `prop_species.PROP_SPECIES`, not in this table, and it is handled
    # there.
    (("back_bar",), "wood_stained"),
)
_PROP_MATERIAL_DEFAULT = "wood"
_PROP_ACOUSTIC = {"wood": ("Wood", 0.35, 0.3), "metal": ("Metal", 0.2, 0.15),
                  "leather": ("Curtain", 0.6, 0.5),
                  "metal_bare": ("Metal", 0.2, 0.15),
                  "metal_painted": ("Metal", 0.25, 0.2),
                  "wood_stained": ("Wood", 0.35, 0.3)}

#: The surfaces a strip club room wears (Pixelcoat 0.42.0's club grammars):
#: a medallion carpet with worn paths on the floor, burgundy flocked paper on
#: the partitions between club rooms, muddy brown paint over block outside.
#: Declared in the palette the way a prop's material is, with an acoustic.
#: The exterior wall's INNER face is the same module as its outer one, so
#: the outside walls of a club room stay painted block from inside -- a
#: partition is one slot with one material on both faces, and Deli Counter
#: has no per-room wall material (docs/GAMEPLAY_JSON_CONTRACT.md says what
#: one would need).
_CLUB_FINISHES = {"carpet_club": ("Curtain", 0.85, 0.75),
                  "wallpaper_club": ("Drywall", 0.4, 0.35),
                  "paint_block": ("Concrete", 0.65, 0.55)}


def _declare_material(spec, mat, acoustic):
    """Declare `mat` in the spec's palette with `(acoustic, absorption,
    damping)` unless it is there -- the validator refuses an undeclared id.
    Appended, never inserted: styles are the palette's order."""
    have = {m.get("id") for m in spec.get("materials") or []}
    if mat not in have:
        a, absorption, damping = acoustic
        spec.setdefault("materials", []).append(
            {"id": mat, "acoustic": a, "absorption": absorption,
             "damping": damping})
    return mat


def _prop_material(spec, name):
    """The material a placed piece wears, declared in the spec's palette if it
    is not already -- the validator refuses an undeclared material id."""
    key = (name or "").lower()
    mat = _PROP_MATERIAL_DEFAULT
    for words, m in _PROP_MATERIALS:
        if any(w in key for w in words):
            mat = m
            break
    if mat != "wood":
        _declare_material(spec, mat, _PROP_ACOUSTIC[mat])
    return mat


def dress_club_rooms(spec):
    """The strip club's surfaces (`_CLUB_FINISHES`), in place, idempotent:
    every club room's floor is `carpet_club` unless it names its own; a
    partition with a club room on BOTH faces is `wallpaper_club`; the
    exterior walls and the default are `paint_block`. Returns the count of
    fields set. Nothing outside a `strip_club` building is touched."""
    name = club_building_id(spec)
    if not _strip_club_building(name):
        return 0
    club = [r for r in spec.get("rooms") or [] if is_strip_club_room(r, name)]
    if not club:
        return 0
    n = 0
    for r in club:
        if not r.get("floor_material") and not r.get("material"):
            r["floor_material"] = _declare_material(
                spec, "carpet_club", _CLUB_FINISHES["carpet_club"])
            n += 1
    sh = _story_height(spec)

    def _rooms_on(story, axis, pos, lo, hi):
        """Club rooms whose bound lies on the partition's line over its
        span, split by side: (below/west, above/east)."""
        sides = [[], []]
        for r in club:
            if int(r.get("story", 0) or 0) != story:
                continue
            x0, y0, x1, y1 = r["bounds"]
            a0, a1, b0, b1 = ((x0, x1, y0, y1) if axis == "X"
                              else (y0, y1, x0, x1))
            if min(a1, hi) - max(a0, lo) <= 0.5:
                continue
            if abs(b1 - pos) < 0.05:
                sides[0].append(r)
            elif abs(b0 - pos) < 0.05:
                sides[1].append(r)
        return sides
    for p in spec.get("partitions") or []:
        if p.get("material") == "wallpaper_club":
            continue
        lo, hi = sorted((float(p["start"]), float(p["end"])))
        below, above = _rooms_on(int(p.get("story", 0) or 0), p["axis"],
                                 float(p["pos"]), lo, hi)
        if below and above:
            p["material"] = _declare_material(
                spec, "wallpaper_club", _CLUB_FINISHES["wallpaper_club"])
            n += 1
    default = spec.get("default_material")
    for w in spec.get("ext_walls") or []:
        if w.get("material") in (None, default, "concrete", "block_wall"):
            if w.get("material") != "paint_block":
                w["material"] = _declare_material(
                    spec, "paint_block", _CLUB_FINISHES["paint_block"])
                n += 1
    if default != "paint_block":
        spec["default_material"] = _declare_material(
            spec, "paint_block", _CLUB_FINISHES["paint_block"])
        n += 1
    del sh
    return n


def _room_kind(room, building=None):
    """The furnishing KIND of a room: a strip club's club rooms first
    (`is_strip_club_room`, which needs the building's id), then its id's
    whole tokens, then below grade a basement, then its role, then
    ``fallback``."""
    if is_strip_club_room(room, building):
        return "strip_club"
    tokens = set(str(room.get("id", "")).lower().replace("-", "_").split("_"))
    for kind, words in _ROOM_KINDS:
        if tokens.intersection(words):
            return kind
    if int(room.get("story", 0) or 0) < 0:
        return "basement"
    role = str(room.get("role") or "").lower()
    if role in _ROLE_KINDS:
        return _ROLE_KINDS[role] or "fallback"
    tokens = set(role.replace("-", "_").split("_"))
    for kind, words in _ROOM_KINDS:
        if tokens.intersection(words):
            return kind
    return "fallback"


def _room_volume_count(spec, room):
    """Volumes standing in this room on its own storey -- what is already
    there, so an authored room is topped up rather than doubled."""
    x0, y0, x1, y1 = room["bounds"]
    sh = _story_height(spec)
    story = room.get("story", 0)
    n = 0
    for v in spec.get("volumes", []):
        if not (x0 <= v.get("x", 1e9) <= x1 and y0 <= v.get("y", 1e9) <= y1):
            continue
        if abs(v.get("z", 0) - (story * sh + v.get("size_z", 0) / 2)) < sh:
            n += 1
    return n


#: How close a wall line may be to the building's own edge before it is
#: treated as an EXTERIOR wall, whose openings furniture must clear.
_FURNISH_EXT_KEEPOUT = 0.5
#: Clearance either side of an exterior opening, beyond its half width. A
#: door needs its approach and a window its sill; 0.9 m is `_seed_clear`'s
#: own clearance between pieces, so a doorway gets what a desk gets.
_FURNISH_OPENING_CLEAR = 0.9
#: Past `_FURNISH_MAX` pieces a room is a HALL, and halls are furnished
#: sparser than offices: one piece per this many square metres, to a hard cap.
_FURNISH_HALL_PER_AREA = 40.0
_FURNISH_HALL_MAX = 30


def _ext_openings(spec, story):
    """``{wall: [(centre_along, half_width), ...]}`` for one storey's exterior
    openings, in the room coordinates `bounds` use -- or None when the storey
    has a setback, whose extent is not the footprint and is not re-derived
    here.

    The position rule is `Builder._opening_to_hole`'s: an opening sits at
    `pos * run` from its wall's centre, `run` being the storey's extent along
    that wall (`footprint_x` for N and S, `footprint_y` for E and W)."""
    if spec.get("setbacks"):
        return None
    fx = float(spec.get("footprint_x", 0.0))
    fy = float(spec.get("footprint_y", 0.0))
    out = {"N": [], "S": [], "E": [], "W": []}
    for w in spec.get("ext_walls", []) or []:
        if w.get("story", 0) != story or w.get("wall") not in out:
            continue
        run = fx if w["wall"] in ("N", "S") else fy
        for op in w.get("openings", []) or []:
            out[w["wall"]].append((float(op.get("pos", 0.0)) * run,
                                   float(op.get("width", 1.0)) / 2.0))
    return out


def _clear_of_openings(openings, wall, centre, half_len):
    """Does a piece centred at `centre` along `wall`, `half_len` either side,
    stay clear of every opening in that wall?"""
    for c, hw in (openings or {}).get(wall, ()):
        if abs(centre - c) < half_len + hw + _FURNISH_OPENING_CLEAR:
            return False
    return True


#: Air between a wall-slotted piece's back and the wall's face.
_WALL_PIECE_AIR = 0.01


def _wall_slots(spec, room, w, d, rng, with_front=False):
    """Candidate ``(x, y, sx, sy, rot_z)`` flush against the room's walls, the
    piece's long axis lying ALONG the wall. A shelf run standing across a
    wall rather than along it is how a 2.6 m unit ends up sticking into the
    middle of the floor.

    EXTERIOR WALLS, AND WHY THEY WERE BANNED FOR ONE VERSION. `_seed_clear`
    keeps a piece a metre off any PARTITION, which is where interior doors
    are, and knows nothing about the openings in an exterior wall -- so in
    0.122.0's first build a shelf run stood across the door of `office`'s
    exec suite and the nav gate reported the objective unreachable. The ban
    that fixed it also emptied every hall whose long walls are exterior,
    which cold run 9044's brewery frame showed. Exterior walls are back,
    clear of each opening by `_ext_openings`, and only a storey with a
    setback -- whose extent is not the footprint -- keeps the exclusion.

    ``with_front`` appends the compass bearing the piece's front must face
    (away from its wall), so the caller can turn a piece the emitter will
    not turn -- `_front_turn` -- rather than trust `rot_z`, which is right
    only for a piece longer than it is deep.
    """
    x0, y0, x1, y1 = room["bounds"]
    hx = float(spec.get("footprint_x", 0.0)) / 2.0
    hy = float(spec.get("footprint_y", 0.0)) / 2.0
    openings = _ext_openings(spec, room.get("story", 0))
    out = []
    long_side, short_side = max(w, d), min(w, d)
    # A PIECE'S BACK STANDS OFF THE WALL'S FACE, not its centreline. A room's
    # bound lies on the wall's centreline, and this was a flat 0.12 m -- half
    # a 0.24 m wall -- while every wall is built at `wall_thick` (0.3), so
    # every wall-slotted piece stood 0.03 m inside its wall. Measured by Zoo
    # on cold run 9052's lobby: waiting-chair backs coplanar with the wall's
    # inner face, 0.00 mm apart, 3.09 m2 of flicker ("z fighting on the
    # [chairs] on the steel", the walker).
    back = float(spec.get("wall_thick") or 0.3) / 2.0 + _WALL_PIECE_AIR

    def _wall_of(value, half, lo_name, hi_name):
        """The exterior wall a room edge lies on, or None when interior."""
        if not half or abs(abs(value) - half) >= _FURNISH_EXT_KEEPOUT:
            return None
        return lo_name if value < 0 else hi_name

    # N and S walls: the long axis runs in x
    for wy, inset in ((y0, +1), (y1, -1)):
        ext = _wall_of(wy, hy, "S", "N")
        if ext and openings is None:
            continue
        span = (x1 - x0) - long_side - 0.6
        if span <= 0:
            continue
        for _ in range(4):
            px = x0 + 0.3 + long_side / 2.0 + rng.random() * span
            if ext and not _clear_of_openings(openings, ext, px, long_side / 2.0):
                continue
            # against the S wall (inset +1) the front must face N; against
            # the N wall, S. Long axis along x, so no long-axis turn is added.
            out.append((px, wy + inset * (short_side / 2.0 + back),
                        long_side, short_side, 180.0 if inset > 0 else 0.0,
                        0.0 if inset > 0 else 180.0))
    # E and W walls: the long axis runs in y
    for wx, inset in ((x0, +1), (x1, -1)):
        ext = _wall_of(wx, hx, "W", "E")
        if ext and openings is None:
            continue
        span = (y1 - y0) - long_side - 0.6
        if span <= 0:
            continue
        for _ in range(4):
            py = y0 + 0.3 + long_side / 2.0 + rng.random() * span
            if ext and not _clear_of_openings(openings, ext, py, long_side / 2.0):
                continue
            # against the W wall the front must face E; against the E wall,
            # W. `long_axis_first` already turns this piece 90, so the front
            # sits at 90 + rot_z + 180: 180 here gives E, 0 gives W.
            out.append((wx + inset * (short_side / 2.0 + back), py,
                        short_side, long_side, 180.0 if inset > 0 else 0.0,
                        90.0 if inset > 0 else 270.0))
    rng.shuffle(out)
    return out if with_front else [o[:5] for o in out]


def _furnish_target(area, per_area=None):
    """How many pieces a room of `area` square metres wants.

    One per `_FURNISH_PER_AREA` up to `_FURNISH_MAX`: an office. Past that the
    room is a hall and gets one per `_FURNISH_HALL_PER_AREA`, to
    `_FURNISH_HALL_MAX`. A 120 m2 office wants 8; cold run 9044's brewery
    hall, about 1,000 m2, wanted 63 at office density, got 10 under the old
    cap and wants 25 now. A recipe with its own `per_area` (the strip club)
    is one per that many, to the hall cap."""
    if per_area:
        return min(max(1, int(round(area / per_area))), _FURNISH_HALL_MAX)
    office = max(1, int(round(area / _FURNISH_PER_AREA)))
    hall = max(_FURNISH_MAX, int(round(area / _FURNISH_HALL_PER_AREA)))
    return min(office, hall, _FURNISH_HALL_MAX)


#: Air left between a to-the-ceiling piece's top and the ceiling plane, so
#: the two are not coplanar (a furnace's flue runs to the slot's top).
_CEILING_AIR = 0.05
#: Zoo's `furnace` genome tops out at 4.0 m; a taller storey gets a 4.0 m slot.
_TO_CEILING_MAX = 4.0


def _clear_height(spec):
    """A storey's floor-to-ceiling height less `_CEILING_AIR`: the storey
    height less the thicker of the floor and roof slabs, the slab a piece
    could stand under."""
    cap = max(float(spec.get("floor_thick") or 0.3),
              float(spec.get("roof_thick") or 0.0))
    return _story_height(spec) - cap - _CEILING_AIR


def _front_turn(name, sx, sy, front):
    """The `rot_z` that points a piece's front -- its module's local -Y -- at
    compass bearing `front`, given how the slot will be RECORDED.

    `deli_counter` records a hinted volume long side first and adds 90 when
    that side is y (`prop_species.long_axis_first`), and a slot's rotation
    turns the module's +Y onto its bearing, so the front points at
    ``long_turn + rot_z + 180``. A SQUARE piece is never turned, and
    `_wall_slots`'s own rotation assumes it was: until 0.131.0 a 1.2 x 1.2
    water tank on an east or west wall faced along the wall, not into the
    room. This asks the same question the emitter asks instead.
    """
    import prop_species
    turned = (prop_species.species_for_name(name) is not None
              and sy > sx + 1e-9)
    return round((front + 180.0 - (90.0 if turned else 0.0)) % 360.0, 4)


def _nested_rects(spec, room):
    """Bounds of the rooms on `room`'s storey that stand inside it: smaller
    and overlapping, the rule `floors.nested_room_voids` and
    `layout_lint._room_at` use -- the innermost room owns its floor.

    FOUND IN THE LIBRARY, NOT GUESSED: 0.130.0 walls a vault room inside
    `bank_branch_a02`'s `vault_west`, and the first refurnish here stood one
    of `vault_west`'s count tables and its chair inside the vault, among the
    vault room's own furniture. `_seed_clear` keeps a piece a metre off the
    vault's partitions but has no notion that the floor beyond them is
    another room's."""
    b = room["bounds"]
    area = (b[2] - b[0]) * (b[3] - b[1])
    story = int(room.get("story", 0) or 0)
    out = []
    for other in spec.get("rooms", []) or []:
        if other is room or int(other.get("story", 0) or 0) != story:
            continue
        ob = other.get("bounds")
        if not ob or (ob[2] - ob[0]) * (ob[3] - ob[1]) >= area:
            continue
        if ob[2] > b[0] and ob[0] < b[2] and ob[3] > b[1] and ob[1] < b[3]:
            out.append(tuple(ob))
    return out


def _over_rects(rects, px, py, hx, hy):
    """Does a box centred (px, py), half extents (hx, hy), overlap any rect?"""
    return any(px + hx > r[0] and px - hx < r[2] and py + hy > r[1]
               and py - hy < r[3] for r in rects)


def _palette(spec, key):
    """This building's sizes of one piece: `_PALETTE` of the piece's sizes,
    drawn by the spec's seed, in the piece's own order."""
    import random
    sizes = list(_PIECES[key]["sizes"])
    if len(sizes) <= _PALETTE:
        return sizes
    rng = random.Random(f"{spec.get('seed', 0)}:{key}:palette")
    keep = sorted(rng.sample(range(len(sizes)), _PALETTE))
    return [sizes[i] for i in keep]


def _furnish_plan(recipe, clusters, want, rng):
    """``[("host", key) | ("cluster", pool, n)]`` for one room: one or two
    anchors, about half the target as a wall run, the rest floor sets and
    clusters in turn. A `one_cluster` recipe is a wall run and one cluster."""
    items = []
    anchors = list(recipe["anchors"])
    if recipe.get("all_anchors"):
        n_anchor = min(len(anchors), want)
        items += [("host", a) for a in anchors[:n_anchor]]
    else:
        n_anchor = min(len(anchors), want, 1 if want < 6 else 2)
        if n_anchor:
            chosen = [anchors[0]]
            if n_anchor > 1:
                chosen.append(rng.choice(anchors[1:]))
            items += [("host", a) for a in chosen]
    rest = want - n_anchor
    wall = list(recipe["wall"])
    rng.shuffle(wall)
    floor = list(recipe["floor"])
    if recipe.get("one_cluster") and clusters and rest > 0:
        pool, lo, hi = clusters[0]
        k = min(rest, rng.randint(lo, hi))
        items.append(("cluster", pool, k))
        rest -= k
        items += [("host", wall[i % len(wall)]) for i in range(rest)] if wall else []
        return items
    n_wall = min(rest, int(round(want / 2.0))) if wall else 0
    items += [("host", wall[i % len(wall)]) for i in range(n_wall)]
    rest -= n_wall
    turn = 0
    # Clusters in TURN, from a seeded start: drawn at random, a wine cellar
    # with five pieces to spare took barrels three times and never its
    # cartons and dust sheets.
    ci = rng.randrange(len(clusters)) if clusters else 0
    while rest > 0:
        if floor and (not clusters or turn % 2 == 0):
            items.append(("host", rng.choice(floor)))
            rest -= 1
        elif clusters:
            pool, lo, hi = clusters[ci % len(clusters)]
            ci += 1
            k = max(1, min(rest, rng.randint(lo, hi)))
            items.append(("cluster", pool, k))
            rest -= k
        elif wall:
            items.append(("host", rng.choice(wall)))
            rest -= 1
        else:
            break
        turn += 1
    return items


def _make_volume(spec, key, name, px, py, sx, sy, h, rot, story, sh, building):
    """A placed piece's volume: position, size, collision, material and
    Zoo's dressing fields. `furnish` and `place_fixtures` both build here."""
    import zlib
    p = _PIECES[key]
    vol = {
        "name": name,
        "x": round(px, 2), "y": round(py, 2),
        "z": round(story * sh + (p["lift"] if p["lift"] is not None
                                 else h / 2.0), 3),
        "size_x": round(sx, 3), "size_y": round(sy, 3),
        "size_z": round(h, 3),
        "collision": p["collision"],
        "material": _prop_material(spec, key),
    }
    if rot:
        vol["rot_z"] = rot
    if p["stock"]:
        vol["stock"] = p["stock"]
    if p["form"]:
        vol["form"] = p["form"]
    # THE VARIANT IS THE NAME'S crc32, as Zoo 0.84.0 asks, and only
    # on a species that has variants to give: Zoo drops ALL THREE
    # fields when one cannot be honoured, so a variant on a chair
    # would not only be ignored, it would cost a furnace its form.
    # A species with its own count (`neon_sign`, 24 names) draws
    # from that count, and from the BUILDING's id rather than the
    # name's: a club has one name over its door and in its rooms.
    if p["variants"]:
        mod = int(p["variants"]) if int(p["variants"]) > 1 else 4
        key_text = (str(building or "") if mod > 4 else name)
        n = (zlib.crc32(key_text.encode("utf-8")) & 0xFFFFFFFF) % mod
        if n:
            vol["variant"] = n
    return vol


# ---------------------------------------------------------------------------
# FIXTURES -- the dartboard and the cigarette machine (0.136.0)
# ---------------------------------------------------------------------------
#
# WHY A SECOND PASS, AND WHY IT IS SAFE TO RUN ON THE LIBRARY. A fixture
# written into a recipe's wall run would re-deal every room of its kind: the
# run is shuffled and cycled, so one more entry moves every piece after it.
# Placed after the room is furnished, from the spec's own volumes and a
# random stream of its own, it moves nothing -- and because it reads only
# the spec, a room furnished in this call and a room a previous release
# furnished get the same answer. `furnish` ends with this pass;
# `migrate_club_fixtures.py` is this pass alone over `specs/`.
#
# THE PREMISE THIS REPLACES, REFUTED AND KEPT. The request said re-furnishing
# the library with today's code does not reproduce today's specs, citing
# `migrate_club_rooms.py --check` a01 -87/+85, a02 -76/+75, a03 -149/+145.
# Those are counts, not a diff: volumes removed, and `furnish`'s own return
# value, which does not count the `stage_deck` colliders it writes (one per
# club stage). Measured on 0.135.1 before any of this was written: strip and
# refurnish all 126 room-bearing specs and compare the JSON (sort_keys) --
# 126 identical, 0 different. The library IS a fixed point of `furnish`, and
# this pass keeps it one.

#: The oche: the throwing line, 2.37 m from the face of the board (the
#: regulation soft-tip and steel-tip distance in American bars).
_OCHE = 2.37


def _body_radius():
    """The player's body radius from `agent_contract.json` (not the nav
    bake's, which carries a safety margin)."""
    try:
        from agent_contract import contract
        return float(contract()["characters"]["player"]["radius_m"])
    except Exception:
        return 0.35


def _front_of(vol):
    """The compass bearing a placed wall piece faces, inverted from
    `_front_turn`: a piece deeper than it is wide was turned 90 by the
    emitter."""
    sx, sy = float(vol["size_x"]), float(vol["size_y"])
    return round((float(vol.get("rot_z", 0.0)) + 180.0 + (90.0 if sy > sx + 1e-9 else 0.0)) % 360.0, 4)


def dart_lane(vol):
    """``(x0, y0, x1, y1)``: the floor a dartboard needs clear in front of it.

    From the slot's BACK (the wall) out through the slot's depth, the oche
    distance and a standing body's depth (two body radii), as wide as the
    slot plus a body radius either side. Measured from the slot's front, not
    the board's face: the board is inside the cabinet, so the lane is at
    least the oche and a body from the board, never less."""
    sx, sy = float(vol["size_x"]), float(vol["size_y"])
    front = math.radians(_front_of(vol))
    fx, fy = round(math.sin(front)), round(math.cos(front))
    along, depth = max(sx, sy), min(sx, sy)
    r = _body_radius()
    length = depth + _OCHE + 2.0 * r
    half = along / 2.0 + r
    bx, by = float(vol["x"]) - fx * depth / 2.0, float(vol["y"]) - fy * depth / 2.0
    ex, ey = bx + fx * length, by + fy * length
    if fx:
        return (min(bx, ex), by - half, max(bx, ex), by + half)
    return (bx - half, min(by, ey), bx + half, max(by, ey))


def _rect_hits(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _rect_point_dist(rect, x, y):
    dx = max(rect[0] - x, 0.0, x - rect[2])
    dy = max(rect[1] - y, 0.0, y - rect[3])
    return math.hypot(dx, dy)


def dart_lane_blockers(spec, room, lane, skip=()):
    """What stands in a throwing lane, as strings; empty when it is clear.

    The lane must lie inside the room (its walls' inner faces); no volume on
    the storey may stand in it (except one hung in free air over a body's
    head, `_HUNG_MIN`, and the names in ``skip``); no partition may cross it;
    it may not come within a door's approach (1.5 m of an opening's centre,
    `_seed_clear`'s radius), a stair's reservation (0.3 m round it, the same),
    a ladder (1.6 m), a vault door's swing or an objective or loot marker
    (1.2 m)."""
    out = []
    story = room.get("story", 0)
    sh = _story_height(spec)
    floor = story * sh
    wt = float(spec.get("wall_thick") or 0.3) / 2.0
    x0, y0, x1, y1 = room["bounds"]
    if lane[0] < x0 + wt - 1e-6 or lane[1] < y0 + wt - 1e-6 or \
            lane[2] > x1 - wt + 1e-6 or lane[3] > y1 - wt + 1e-6:
        out.append("room")
    for v in spec.get("volumes", []):
        if v.get("name") in skip:
            continue
        vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
        if not _on_storey(vz, vh, floor, sh):
            continue
        if v.get("collision") == "none" and vz - vh / 2.0 - floor >= _HUNG_MIN:
            continue
        hx, hy = float(v.get("size_x", 1.0)) / 2.0, float(v.get("size_y", 1.0)) / 2.0
        if abs(float(v.get("rot_z", 0.0))) % 90.0 > 1e-6:
            hx = hy = math.hypot(hx, hy)
        if _rect_hits(lane, (v["x"] - hx, v["y"] - hy, v["x"] + hx, v["y"] + hy)):
            out.append("volume:" + str(v.get("name")))
    for p in spec.get("partitions", []):
        if p.get("story", 0) != story:
            continue
        lo, hi = sorted((float(p["start"]), float(p["end"])))
        pos = float(p["pos"])
        seg = (pos - 0.01, lo, pos + 0.01, hi) if p["axis"] == "Y" else (lo, pos - 0.01, hi, pos + 0.01)
        if _rect_hits(lane, seg):
            out.append("partition")
        run = abs(float(p["end"]) - float(p["start"]))
        for op in p.get("openings", []):
            u = float(p["start"]) + (float(op.get("pos", 0.0)) + 0.5) * run
            ox, oy = (pos, u) if p["axis"] == "Y" else (u, pos)
            if _rect_point_dist(lane, ox, oy) < 1.5:
                out.append("door")
    hxf = spec.get("footprint_x", 20) / 2
    hyf = spec.get("footprint_y", 20) / 2
    for w in spec.get("ext_walls", []):
        if w.get("story", 0) != story:
            continue
        run = spec.get("footprint_x", 20) if w["wall"] in ("N", "S") else spec.get("footprint_y", 20)
        for op in w.get("openings", []):
            u = op.get("pos", 0.0) * run
            ox, oy = {"N": (u, hyf), "S": (u, -hyf), "E": (hxf, u), "W": (-hxf, u)}[w["wall"]]
            if _rect_point_dist(lane, ox, oy) < 1.5:
                out.append("door")
    for r in _stair_reserved_rects(spec):
        if _rect_hits(lane, (r[0] - 0.3, r[1] - 0.3, r[2] + 0.3, r[3] + 0.3)):
            out.append("stair")
    for lad in spec.get("ladders", []):
        if _rect_point_dist(lane, lad["x"], lad["y"]) < 1.6:
            out.append("ladder")
    for m in spec.get("markers", []):
        if m.get("type") in ("objective", "loot") and \
                _rect_point_dist(lane, m.get("x", 1e9), m.get("y", 1e9)) < 1.2:
            out.append("marker")
    import vault_room
    for k in vault_room.keepout_rects(spec, story):
        if _rect_hits(lane, (k[0] - 0.3, k[1] - 0.3, k[2] + 0.3, k[3] + 0.3)):
            out.append("vault")
    return out


_FIXTURE_NAME = None


def _room_names(spec, rtag):
    """(stem, seq) of every generated volume carrying a room's tag."""
    import re
    global _FIXTURE_NAME
    if _FIXTURE_NAME is None:
        _FIXTURE_NAME = re.compile(r"^(?P<stem>[a-z_]+?)_(?P<tag>r[0-9a-f]{8})_(?P<seq>\d+)(_\d+)?$")
    out = []
    for v in spec.get("volumes", []):
        m = _FIXTURE_NAME.match(str(v.get("name", "")))
        if m and m.group("tag") == rtag:
            out.append((m.group("stem"), int(m.group("seq")), v))
    return out


def fixture_limit(key, area):
    p = _PIECES[key]
    limit = p["most"] or 1
    if p["most_big"] and area >= p["most_big"][0]:
        limit = p["most_big"][1]
    return limit


#: How many draws of `_wall_slots` a fixture takes before a room goes
#: without one. MEASURED on the library: at 1 (a wall run's single draw)
#: `strip_club_a03`'s main floor had no dartboard -- of 26 spots, 13 passed
#: `_seed_clear` and every lane met a volume (16), a stair's reservation (8),
#: a door's approach (4) or the room's edge (2).
_FIXTURE_ROUNDS = 6


def _place_fixture(spec, room, key, k, building):
    """One fixture into one room, or None: the recipe's wall placement --
    this building's size palette, `_wall_slots`, the nested rooms, the
    clearance `_seed_clear` asks of every piece (hung, for a piece with a
    `lift`) -- and a lane kept clear, from a random stream of its own."""
    import random
    p = _PIECES[key]
    story = room.get("story", 0)
    sh = _story_height(spec)
    clear_h = _clear_height(spec)
    rtag = _room_tag(room)
    names = _room_names(spec, rtag)
    seq = 1 + max((s for _stem, s, _v in names), default=0)
    lanes = [dart_lane(v) for stem, _s, v in names if stem in _PIECES and _PIECES[stem]["lane"]]
    inner = _nested_rects(spec, room)
    rng = random.Random(f"{spec.get('seed', 0)}:{room['id']}:fixture:{key}:{k}")
    sizes = list(_palette(spec, key))
    rng.shuffle(sizes)
    # `_wall_slots` draws four spots a wall; a fixture is one piece with a
    # stricter test than a wall run's, so it draws `_FIXTURE_ROUNDS` times
    # that many before a room goes without
    rounds = [(size, spot) for _r in range(_FIXTURE_ROUNDS) for size in sizes
              for spot in _wall_slots(spec, room, size[0], size[1], rng, with_front=True)]
    for (w, d, h), (qx, qy, sx, sy, _rot, front) in rounds:
        if h is None:
            h = min(clear_h, _TO_CEILING_MAX)
        if h > clear_h:
            continue
        half = max(w, d) / 2.0
        hung = p["lift"] is not None
        above = (p["lift"] - h / 2.0) if hung else None
        if _over_rects(inner, qx, qy, half, half):
            continue
        if not _seed_clear(spec, room, qx, qy, [], half=half, above=above):
            continue
        rot = _front_turn(key, sx, sy, front)
        probe = {"x": round(qx, 2), "y": round(qy, 2), "size_x": sx, "size_y": sy, "rot_z": rot}
        if p["lane"]:
            lane = dart_lane(probe)
            if dart_lane_blockers(spec, room, lane):
                continue
            # two lanes stand a body apart: a thrower at one board is not
            # standing in the next board's lane (a01's main floor put two
            # at right angles in one corner, their lanes overlapping)
            gap = 2.0 * _body_radius()
            if any(_rect_hits(lane, (q[0] - gap, q[1] - gap, q[2] + gap, q[3] + gap))
                   for q in lanes):
                continue
        elif _over_rects(lanes, qx, qy, sx / 2.0, sy / 2.0):
            continue
        vol = _make_volume(spec, key, f"{key}_{rtag}_{seq}", qx, qy, sx, sy, h, rot,
                           story, sh, building)
        spec.setdefault("volumes", []).append(vol)
        return vol
    return None


def place_fixtures(spec):
    """Every room's FIXTURES (a recipe's ``fixtures``), where a room has none
    yet: one of each, two of a piece whose ``most_big`` area the room
    reaches. Idempotent and deterministic; reads nothing but the spec.
    Returns the number of volumes placed."""
    building = club_building_id(spec)
    added = 0
    for room in spec.get("rooms", []) or []:
        x0, y0, x1, y1 = room["bounds"]
        area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        if area < _FURNISH_MIN_AREA:
            continue
        fixtures = _RECIPES[_room_kind(room, building)].get("fixtures") or ()
        rtag = _room_tag(room)
        for key in fixtures:
            for k in range(fixture_limit(key, area)):
                have = sum(1 for stem, _s, _v in _room_names(spec, rtag) if stem == key)
                if have > k:
                    continue
                if _place_fixture(spec, room, key, k, building) is None:
                    break
                added += 1
    return added


# ---------------------------------------------------------------------------
# THE CLUB'S BACK BAR -- a staff side behind every bar counter (0.137.0)
# ---------------------------------------------------------------------------
#
# The walker, 2026-09-15, with three photos of a lounge bar
# (docs/SET_DRESSING_REFERENCES.md, "The walker's club bar reference"). The
# third is shot from above: bartenders WORKING between the counter and the
# back bar, and "just to show the clearance the bar should have for
# bartenders to stand behind, similar to the bank teller row".
#
# `enclose_teller_lines` (0.126.0) is the precedent and this follows its
# SHAPE -- one pass over the finished spec, a report row per bar saying
# enclosed or why not, no geometry moved where the room cannot hold it --
# but not its walls. A teller line's staff side is a locked room behind two
# doors; a bar's is a working aisle you walk into round the end of the
# counter, and the reference asks for "a lighter enclosure: no locked
# doors, a BAR FLAP at one end or both".
#
# WHAT THE COUNTER HAD TO GIVE UP. Until this pass a `counter_club` stood
# flush against its wall (`_wall_slots`: the piece's back `wall_thick / 2 +
# _WALL_PIECE_AIR` off the room's bound), which leaves 1 cm behind it and
# no staff side at all. The counter is MOVED into the room by the back
# bar's depth plus the aisle, and its stools move with it, so the bar's
# customer front is where it was relative to its stools and the wall
# behind it is now the back bar's.
#
# THE AISLE'S WIDTH IS DERIVED FROM BOTH CONTRACT NUMBERS, not chosen.
# It is a corridor -- a body walks its length -- so it is at least
# `min_corridor_width` 1.1 m, the navmesh's own rule (2 x bake radius +
# 0.3; narrower bakes as an island, as twin_a01's 0.9 m flights did). And
# it is entered at its END, through the gap between the counter's end and
# the back bar's: that gap IS the bar flap, and a flap is a door, so it is
# at least `min_door_width` 1.25 m. One aisle cannot be two widths, so it
# is the greater of them and the flap is the aisle's own cross-section.
# The reference's figure of "~0.9 m" is below both and is not used.
#
# WHY THERE IS NO FLAP LEAF. Deli Counter has no door in the middle of a
# volume, and a solid one across the only route to the staff side would
# make the aisle an island -- the exact defect the nav gate exists to
# catch. The bar flap here is an opening, not a leaf, and the report says
# its measured width.

#: Zoo's `back_bar` genome: the default depth and height, and the width
#: range a unit can be built at.
BACK_BAR_DEPTH = 0.5
BACK_BAR_H = 2.4
BACK_BAR_W = (1.6, 6.0)
#: How much of the aisle's length the bartender marker stands in from the
#: mouth: a body's radius and a little, so the marker is not in the
#: doorway it is reached through.
_BARTENDER_IN = 0.8
#: A counter end with less than the aisle's own width plus the counter's
#: depth between it and the room's side wall makes the bar an L: there is
#: no walking round that end, so the return leg closes it and the other
#: end is the flap.


def bar_aisle_width():
    """The clear aisle behind a club bar: the greater of the corridor and
    the door minimums (see the section note). One number, asked once."""
    import agent_contract
    return round(max(agent_contract.min_corridor_width(),
                     agent_contract.min_door_width()), 4)


def _axis_of(bearing):
    """``(dx, dy)`` for a compass bearing that is square to the axes, or
    None: a counter set at an angle has no wall behind it to speak of."""
    b = round(float(bearing) % 360.0, 3)
    return {0.0: (0.0, 1.0), 90.0: (1.0, 0.0), 180.0: (0.0, -1.0),
            270.0: (-1.0, 0.0)}.get(b)


def _rect_of(v):
    sx, sy = float(v["size_x"]) / 2.0, float(v["size_y"]) / 2.0
    return (float(v["x"]) - sx, float(v["y"]) - sy,
            float(v["x"]) + sx, float(v["y"]) + sy)


def _rect_clear(spec, room, rect, skip, pad=0.0):
    """What stands in `rect` on this room's storey, by name. `skip` is the
    set of volume names that belong to the bar being built. A HUNG piece
    over a body's head is not in the way, the same rule `dart_lane_blockers`
    uses."""
    out = []
    story = room.get("story", 0)
    sh = _story_height(spec)
    floor = story * sh
    box = (rect[0] - pad, rect[1] - pad, rect[2] + pad, rect[3] + pad)
    x0, y0, x1, y1 = room["bounds"]
    wt = float(spec.get("wall_thick") or 0.3) / 2.0
    if box[0] < x0 + wt - 1e-6 or box[1] < y0 + wt - 1e-6 or \
            box[2] > x1 - wt + 1e-6 or box[3] > y1 - wt + 1e-6:
        out.append("room")
    for v in spec.get("volumes", []):
        if v.get("name") in skip:
            continue
        vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
        if not _on_storey(vz, vh, floor, sh):
            continue
        if v.get("collision") == "none" and vz - vh / 2.0 - floor >= _HUNG_MIN:
            continue
        if _rect_hits(box, _rect_of(v)):
            out.append("volume:" + str(v.get("name")))
    for p in spec.get("partitions", []):
        if p.get("story", 0) != story:
            continue
        lo, hi = sorted((float(p["start"]), float(p["end"])))
        pos = float(p["pos"])
        seg = ((pos - 0.01, lo, pos + 0.01, hi) if p["axis"] == "Y"
               else (lo, pos - 0.01, hi, pos + 0.01))
        if _rect_hits(box, seg):
            out.append("partition")
    for rect2 in _stair_reserved_rects(spec):
        if _rect_hits(box, rect2):
            out.append("stair")
    for lad in spec.get("ladders", []):
        if _rect_point_dist(box, lad["x"], lad["y"]) < 1.0:
            out.append("ladder")
    return out


def _club_bar_counters(spec, building):
    """``[(room, counter volume, seq)]`` -- every club bar counter in a
    strip club, in a stable order."""
    out = []
    if not _strip_club_building(building):
        return out
    for room in spec.get("rooms", []) or []:
        if not is_strip_club_room(room, building):
            continue
        rtag = _room_tag(room)
        for stem, seq, v in sorted(_room_names(spec, rtag),
                                   key=lambda t: (t[0], t[1])):
            if stem == "counter_club":
                out.append((room, v, seq))
    return out


def back_bar_club_counters(spec):
    """Stand a BACK BAR against the wall behind every club bar counter,
    with a bartender's aisle between, and prove the staff side is a place a
    body can be.

    Per bar, in one pass and in this order:

      * the counter moves into the room by the back bar's depth plus the
        aisle (`bar_aisle_width`), and its stools move with it;
      * a `back_bar` volume goes flush against the wall, as long as the
        counter (inside Zoo's genome range) and to the storey's clear
        height;
      * where the counter's end is against a perpendicular wall, a return
        leg across the aisle closes that end and the bar is an L;
      * a `patrol_point` marker stands in the aisle, so the nav gate
        answers whether a bartender can be reached there rather than
        anybody assuming it;
      * the whole thing is skipped, and the report says why, when the room
        cannot hold it.

    Idempotent (a counter that already has its `back_bar_<tag>_<seq>` is
    left alone), deterministic, and reads nothing but the spec. Returns
    ``[report]``, one row per bar counter.
    """
    building = club_building_id(spec)
    aisle = bar_aisle_width()
    sh = _story_height(spec)
    clear_h = _clear_height(spec)
    report = []
    for room, v, seq in _club_bar_counters(spec, building):
        rtag = _room_tag(room)
        entry = {"room": room["id"], "counter": v["name"], "built": False,
                 "why": "", "aisle_m": None, "flap_m": None, "l_shaped": False}
        report.append(entry)
        if any(n == "back_bar" and s == seq
               for n, s, _v in _room_names(spec, rtag)):
            entry["built"] = True
            entry["why"] = "already"
            continue
        front = _front_of(v)
        d = _axis_of(front)
        if d is None:
            entry["why"] = ("the counter is set at %g deg, not square to a "
                            "wall" % front)
            continue
        fx, fy = d
        story = room.get("story", 0)
        floor = story * sh
        x0, y0, x1, y1 = room["bounds"]
        wt = float(spec.get("wall_thick") or 0.3) / 2.0
        # ONE COORDINATE, so the arithmetic is written once: `t` measures
        # from the INNER FACE of the wall behind the counter, along the
        # counter's front bearing, into the room. `along` is the other axis.
        # A first draft did this in x and y with a sign per branch and had
        # two spellings of the aisle in it before the line that used it.
        if fy:
            dirn = fy
            wall = (y0 + wt) if dirn > 0 else (y1 - wt)
            back_t = abs(float(v["y"]) - float(v["size_y"]) / 2.0 * dirn - wall)
            run, thick = float(v["size_x"]), float(v["size_y"])
            along = float(v["x"])
            a_lo, a_hi = x0 + wt, x1 - wt
            extent = (y1 - y0) - 2 * wt
        else:
            dirn = fx
            wall = (x0 + wt) if dirn > 0 else (x1 - wt)
            back_t = abs(float(v["x"]) - float(v["size_x"]) / 2.0 * dirn - wall)
            run, thick = float(v["size_y"]), float(v["size_x"])
            along = float(v["y"])
            a_lo, a_hi = y0 + wt, y1 - wt
            extent = (x1 - x0) - 2 * wt

        def _rect(t0, t1, u0, u1):
            """A rectangle from `t0` to `t1` off the wall, spanning `u0` to
            `u1` along it, in the spec's own x/y."""
            p0, p1 = wall + dirn * t0, wall + dirn * t1
            lo, hi = min(p0, p1), max(p0, p1)
            uu0, uu1 = min(u0, u1), max(u0, u1)
            return (uu0, lo, uu1, hi) if fy else (lo, uu0, hi, uu1)

        need = BACK_BAR_DEPTH + aisle
        shift = round(need - back_t, 4)
        if shift < -1e-6:
            entry["why"] = ("the counter already stands %.2f m off its wall"
                            % back_t)
            continue
        lane = extent - (need + thick)
        if lane < _CUSTOMER_LANE:
            entry["why"] = ("moving the counter %.2f m leaves %.2f m of "
                            "customer floor in front of it" % (shift, lane))
            continue
        mine = {v["name"]} | {sv["name"] for n, s, sv in _room_names(spec, rtag)
                              if n == "bar_stool" and s == seq}
        u0, u1 = along - run / 2.0, along + run / 2.0
        bar_rect = _rect(0.0, BACK_BAR_DEPTH, u0, u1)
        aisle_rect = _rect(BACK_BAR_DEPTH, need, u0, u1)
        counter_rect = _rect(need, need + thick, u0, u1)
        blockers = (_rect_clear(spec, room, bar_rect, mine)
                    + _rect_clear(spec, room, aisle_rect, mine)
                    + _rect_clear(spec, room, counter_rect, mine))
        if blockers:
            entry["why"] = "the staff side is not clear: " + ", ".join(
                sorted(set(blockers))[:3])
            continue
        # THE MOUTHS, one at each end of the aisle: the aisle's own
        # cross-section carried a door's width past the counter's end. The
        # `reach` is how much floor there is between that end and the
        # room's side wall, which is what decides whether a body can get in
        # at all.
        mouths = {}
        for side in ("a", "b"):
            end, s = (u0, -1.0) if side == "a" else (u1, 1.0)
            m = _rect(BACK_BAR_DEPTH, need, end, end + s * aisle)
            reach = abs((a_lo if side == "a" else a_hi) - end)
            mouths[side] = (m, reach, _rect_clear(spec, room, m, mine))
        open_ends = [s for s in ("a", "b")
                     if not mouths[s][2] and mouths[s][1] >= aisle - 1e-6]
        if not open_ends:
            entry["why"] = ("neither end of the aisle opens %.2f m clear "
                            "(a: %.2f m %s; b: %.2f m %s)"
                            % (aisle, mouths["a"][1],
                               ",".join(sorted(set(mouths["a"][2]))) or "clear",
                               mouths["b"][1],
                               ",".join(sorted(set(mouths["b"][2]))) or "clear"))
            continue

        # --- from here the bar is built -----------------------------------
        entry["aisle_m"] = round(aisle, 3)
        entry["flap_m"] = round(aisle, 3)
        entry["shift_m"] = round(shift, 3)
        if fy:
            v["y"] = round(float(v["y"]) + fy * shift, 2)
        else:
            v["x"] = round(float(v["x"]) + fx * shift, 2)
        for name, s, sv in _room_names(spec, rtag):
            if name == "bar_stool" and s == seq:
                if fy:
                    sv["y"] = round(float(sv["y"]) + fy * shift, 2)
                else:
                    sv["x"] = round(float(sv["x"]) + fx * shift, 2)
        bw = max(BACK_BAR_W[0], min(BACK_BAR_W[1], run))
        bh = min(BACK_BAR_H, clear_h)
        cx = (bar_rect[0] + bar_rect[2]) / 2.0
        cy = (bar_rect[1] + bar_rect[3]) / 2.0
        sx, sy = (bw, BACK_BAR_DEPTH) if fy else (BACK_BAR_DEPTH, bw)
        bar = _make_volume(spec, "back_bar", "back_bar_%s_%d" % (rtag, seq),
                           cx, cy, sx, sy, bh,
                           _front_turn("back_bar", sx, sy, front), story, sh,
                           building)
        spec.setdefault("volumes", []).append(bar)
        # THE L. Where one end of the counter stands against a
        # perpendicular wall there is no walking round it, so a return leg
        # across the aisle closes that end and the bar reads as the
        # reference's L in dark stained wood. The other end is the flap.
        closed = [s for s in ("a", "b")
                  if s not in open_ends and mouths[s][1] <= aisle + thick]
        if closed:
            side = closed[0]
            end, s = (u0, -1.0) if side == "a" else (u1, 1.0)
            leg_u = end + s * thick / 2.0
            leg_t = (BACK_BAR_DEPTH + need) / 2.0
            lcx, lcy = (leg_u, wall + dirn * leg_t) if fy \
                else (wall + dirn * leg_t, leg_u)
            lsx, lsy = (thick, aisle) if fy else (aisle, thick)
            leg = _make_volume(spec, "counter_end",
                               "counter_end_%s_%d" % (rtag, seq),
                               lcx, lcy, lsx, lsy, float(v["size_z"]),
                               _front_turn("counter_end", lsx, lsy,
                                           (front + (90.0 if s > 0 else 270.0)) % 360.0),
                               story, sh, building)
            if not _rect_clear(spec, room, _rect_of(leg),
                               mine | {bar["name"]}):
                spec["volumes"].append(leg)
                entry["l_shaped"] = True
        # THE BARTENDER, so the nav gate ANSWERS whether the staff side is
        # a place a body can be rather than anybody assuming it: a marker
        # in the aisle, a step in from the open end.
        end, s = (u0, 1.0) if open_ends[0] == "a" else (u1, -1.0)
        mu = end + s * _BARTENDER_IN
        mt = (BACK_BAR_DEPTH + need) / 2.0
        px, py = (mu, wall + dirn * mt) if fy else (wall + dirn * mt, mu)
        spec.setdefault("markers", []).append({
            "type": "patrol_point", "id": "bartender_%s_%d" % (rtag, seq),
            "x": round(px, 3), "y": round(py, 3), "z": round(floor, 3),
            "rot_z": round(front, 3), "room": room["id"],
            "meta": {"role": "bartender", "aisle_m": round(aisle, 3)}})
        entry["built"] = True
    return report


#: A customer needs somewhere to stand in front of a bar: a stool's depth
#: and a body, which is `_SEAT` plus two radii. The moved counter keeps at
#: least this much floor between its front and the far side of the room.
_CUSTOMER_LANE = 2.0


def furnish(spec):
    """Put FURNITURE in the rooms -- a different question from cover.

    `seed_cover` asks whether a room can be fought in and deliberately keeps
    its count low; this asks whether a room looks like what it is, and the
    two do not trade against each other because nothing placed mid-floor here
    reaches SHELTER height and everything that tall goes against a wall.
    (An earlier line here said mid-floor pieces stay below `_COVER_MIN_Z`;
    `test_furnish` refuted it -- a desk is 0.75 m.)

    Each room is read as a KIND (`_room_kind`) and furnished by that kind's
    RECIPE (`_RECIPES`): anchors first, about half the target along the
    walls, then floor sets (a table and its chairs, a desk and its chair)
    and clusters of 2-4 small pieces packed 0.3-0.8 m apart. The count is
    still `_furnish_target` less what the room already holds. Pieces come in
    a small per-building size palette, no more than `_SAME_PIECE_MAX` of one
    (piece, size) per room, and carry Zoo's dressing: `stock` on desks, bar
    and kitchen counters, count tables and supply cabinets, a `form` for the
    furnace, water heater, booth and sofa, and a `variant` from a crc32 of
    the piece's name on every species with `module_variants`.

    Deterministic (spec seed + room id), additive and idempotent: a room this
    pass (or 0.122.0-0.130.0) has furnished is recognised by name and
    skipped. Returns the number of volumes created.
    """
    import collections
    import random
    import zlib
    base_seed = spec.get("seed", 0)
    sh = _story_height(spec)
    clear_h = _clear_height(spec)
    stems = set(_PIECES) | set(_LEGACY_STEMS) | set(_COLLIDER_STEMS) | {"chair_set"}
    added = 0
    building = club_building_id(spec)
    dress_club_rooms(spec)
    for room in spec.get("rooms", []):
        x0, y0, x1, y1 = room["bounds"]
        area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        if area < _FURNISH_MIN_AREA:
            continue
        # IDEMPOTENT BY MARK, NOT BY COUNT. Counting the room's volumes is
        # not enough: a first pass that ran out of clear floor leaves the
        # count short, and a second pass then finds the spots the first
        # pass's own pieces opened up and adds more. `test_the_shelter_pass
        # _is_idempotent` caught exactly that -- five extra pieces in a
        # hospital on a re-enrich. A room this pass has already touched is
        # recognisable from its volume NAMES and is skipped outright.
        #
        # THE ROOM IS NAMED BY A HASH, NOT BY ITS ID. `prop_species` matches
        # keywords anywhere in a volume's name, in table order, so a room id
        # that contains one hijacks every piece in it: in a room called
        # `teller_line`, `chair_set_teller_line_1_1` routes to `teller_line`
        # before `chair` is ever tried, and Zoo builds the fallback box.
        # Cold run 9046's kit reported 17 such fallbacks. A crc32 of the id
        # is deterministic and made of digits, which no keyword is.
        rtag = _room_tag(room)
        mark = f"_{rtag}_"
        # `rsplit("_", 2)[0]` was the first spelling of this and it fails on
        # any room id carrying an underscore -- `chair_waiting` in room
        # `waiting_area` splits to `chair_waiting_waiting`, matches no stem,
        # and the room is furnished a second time under the same names.
        # Prefix and mark, which neither the stem nor the id can confuse.
        if any(mark in v.get("name", "") and
               any(v["name"].startswith(s + "_") for s in stems)
               for v in spec.get("volumes", [])):
            continue
        kind = _room_kind(room, building)
        recipe = _RECIPES[kind]
        if kind == "strip_club":
            recipe = dict(recipe, anchors=_club_anchors(room))
        have = _room_volume_count(spec, room)
        want = max(0, _furnish_target(area, recipe.get("per_area")) - have)
        if recipe.get("cap") is not None:
            want = min(want, recipe["cap"])
        if want <= 0:
            continue
        rng = random.Random(f"{base_seed}:{room['id']}:furnish")
        story = room.get("story", 0)
        clusters = list(recipe["clusters"])
        if story < 0 and kind not in ("basement", "vault", "corridor",
                                      "wine_cellar"):
            clusters.append(_BASEMENT_CLUSTER)
        rcx, rcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        inner = _nested_rects(spec, room)
        placed = []
        per_size = collections.Counter()
        per_name = collections.Counter()
        seq = [0]
        floor_cands = []
        # the candidate grid scales with the room: a fixed 5 x 5 capped every
        # hall at 25 floor positions before clearance removed any of them
        gx = max(5, min(14, int((x1 - x0) // 3.0)))
        gy = max(5, min(14, int((y1 - y0) // 3.0)))
        for i in range(gx):
            for j in range(gy):
                px = x0 + 1.0 + (i + rng.random() * 0.6) * (x1 - x0 - 2.0) / gx
                py = y0 + 1.0 + (j + rng.random() * 0.6) * (y1 - y0 - 2.0) / gy
                floor_cands.append((px, py))
        rng.shuffle(floor_cands)

        def _volume(key, px, py, sx, sy, h, rot, seq_no=None):
            p = _PIECES[key]
            if seq_no is None:
                seq[0] += 1
                seq_no = seq[0]
            return _make_volume(spec, key, f"{key}_{rtag}_{seq_no}", px, py,
                                sx, sy, h, rot, story, sh, building)

        def _deck(key, vol):
            """The invisible collider under a visual-only tall piece (a
            stage authored to the ceiling): the platform's height, the
            piece's footprint, no slot of its own (`visual: false`)."""
            p = _PIECES[key]
            if not p["deck"]:
                return None
            return {
                "name": vol["name"].replace(key, _COLLIDER_STEMS[0], 1),
                "x": vol["x"], "y": vol["y"],
                "z": round(story * sh + p["deck"] / 2.0, 3),
                "size_x": vol["size_x"], "size_y": vol["size_y"],
                "size_z": p["deck"], "collision": "convex", "visual": False,
                "material": vol["material"],
            }

        def _seats(host, centre, how, lo, hi, extra=()):
            """A host's chairs, each through the same clearance as every
            other piece minus the host and its own set, facing the host.
            `centre` is the host's UNROUNDED centre, the one in `placed`:
            the first draft read the rounded `x`/`y` back off the volume,
            never matched its own entry in `placed`, and the 2.2 m spread
            refused every chair in the library.

            `how`: `desk` (one, at the front), `counter` (along the front),
            `table` (round it), `club` (tub chairs round a cocktail table),
            `stool` (bar stools: along a counter's front when the host has
            one, else RINGED round it -- the bar stage). `extra` are volumes
            that belong to the host (its deck collider) and are no more in a
            seat's way than the host is."""
            n = rng.randint(lo, hi)
            if n <= 0:
                return 0
            px, py = centre
            sx, sy = host["size_x"], host["size_y"]
            seat_key = _SEAT_PIECES.get(how)
            seat_w, seat_d, seat_h = (_PIECES[seat_key]["sizes"][0]
                                      if seat_key else _SEAT + (_CHAIR_H,))
            ring = how == "stool" and host.get("_front") is None
            spots = []
            if how in ("desk", "counter") or (how == "stool" and not ring):
                f = math.radians(host["_front"])
                ux, uy = round(math.sin(f)), round(math.cos(f))
                depth = sy if uy else sx
                length = sx if uy else sy
                out = depth / 2.0 + seat_d / 2.0 + (
                    rng.uniform(0.05, 0.3) if how == "desk" else 0.2)
                if how == "desk":
                    spots.append((px + ux * out, py + uy * out))
                else:
                    step = length / n
                    for i in range(n):
                        t = -length / 2.0 + step * (i + 0.5)
                        spots.append((px + ux * out + (t if uy else 0.0),
                                      py + uy * out + (t if ux else 0.0)))
            elif ring:
                # round the bar, a stool's depth and a hand off its band,
                # evenly along the perimeter from a seeded phase
                out = seat_d / 2.0 + 0.15
                hx, hy = sx / 2.0 + out, sy / 2.0 + out
                per = 4.0 * (hx + hy)
                phase = rng.random() * per
                for i in range(n):
                    t = (phase + i * per / n) % per
                    if t < 2 * hx:
                        spots.append((px - hx + t, py - hy))
                    elif t < 2 * hx + 2 * hy:
                        spots.append((px + hx, py - hy + (t - 2 * hx)))
                    elif t < 4 * hx + 2 * hy:
                        spots.append((px + hx - (t - 2 * hx - 2 * hy), py + hy))
                    else:
                        spots.append((px - hx, py + hy - (t - 4 * hx - 2 * hy)))
            else:
                along_x = sx >= sy
                long_sides = [(0, -1), (0, 1)] if along_x else [(-1, 0), (1, 0)]
                ends = [(-1, 0), (1, 0)] if along_x else [(0, -1), (0, 1)]
                rng.shuffle(long_sides)
                rng.shuffle(ends)
                for ex, ey in (long_sides + ends)[:n]:
                    # SOME ARE PULLED OUT: a chair left where somebody got up
                    gap = 0.2 + (rng.uniform(0.1, 0.35) if rng.random() < 0.4
                                 else 0.0)
                    side = sx if ey else sy
                    lat = rng.uniform(-1.0, 1.0) * max(0.0, min(0.15,
                                                                (side - seat_w) / 2))
                    spots.append((px + ex * (sx / 2 + seat_d / 2 + gap) + (lat if ey else 0.0),
                                  py + ey * (sy / 2 + seat_d / 2 + gap) + (lat if ex else 0.0)))
            n_set = 0
            siblings = []
            seat_half = max(seat_w, seat_d) / 2.0
            edge = 0.15 + seat_half
            for j, (cx, cy) in enumerate(spots):
                if not (x0 + edge < cx < x1 - edge and y0 + edge < cy < y1 - edge):
                    continue
                if _over_rects(inner, cx, cy, seat_half, seat_half):
                    continue
                # THE CHAIR PASSES THE SAME CLEARANCE AS EVERY OTHER PIECE,
                # minus its own host and its own set, which it must stand
                # beside. The first 0.123.0 draft skipped the check and put a
                # chair on `credit_union_a02`'s upper stair landing.
                view = dict(spec, volumes=[v for v in spec["volumes"]
                                           if v is not host and
                                           not any(v is s for s in siblings)
                                           and not any(v is e for e in extra)])
                # `placed` enforces a 2.2 m SPREAD between pieces, which is
                # right for hosts and wrong for a host's own chairs.
                others = [q for q in placed if q != (px, py)]
                if not _seed_clear(view, room, cx, cy, others, half=seat_half):
                    continue
                # FACING THE HOST. Slot rotation is a COMPASS bearing --
                # `Builder._slot_orient` puts N at 0, E at 90, S at 180, W at
                # 270 -- turning a module's local +Y onto that bearing. A
                # chair's seated front is its local -Y (its back panel is at
                # +Y), so the front points at bearing + 180, and aiming it at
                # the host from a chair offset (dx, dy) gives atan2(dx, dy).
                # The first 0.124.0 draft used atan2(-dx, dy): right for the
                # chairs north and south of a table, backwards for the ones
                # east and west, caught by re-reading the wall convention
                # before a rebuild rather than after.
                if how in ("table", "club") or ring:
                    face = math.degrees(math.atan2(cx - px, cy - py))
                else:
                    face = host["_front"]
                if ring:
                    # a stool at an oval bar faces the bar wherever it
                    # stands; the slot is square, so any turn fits
                    rot = round(face % 360.0, 1)
                else:
                    rot = float(int(round(face / 90.0)) * 90 % 360)
                # ...and SOME ARE TURNED a little off square. The composer
                # keeps a turn inside its quarter (`themed_tscn._fit_rotation`).
                if not ring and rng.random() < 0.5:
                    rot = round((rot + rng.choice((-1.0, 1.0)) *
                                 rng.uniform(*_SEAT_TURN)) % 360.0, 1)
                if seat_key:
                    chair = _volume(seat_key, cx, cy, seat_w, seat_d, seat_h,
                                    rot, seq_no=f"{host['_seq']}_{j + 1}")
                else:
                    chair = {
                        "material": _prop_material(spec, "chair"),
                        "name": f"chair_set_{rtag}_{host['_seq']}_{j + 1}",
                        "x": round(cx, 2), "y": round(cy, 2),
                        "z": round(story * sh + _CHAIR_H / 2.0, 3),
                        "size_x": _SEAT[0], "size_y": _SEAT[1],
                        "size_z": _CHAIR_H,
                        "collision": "convex",
                        "rot_z": rot,
                    }
                spec["volumes"].append(chair)
                siblings.append(chair)
                n_set += 1
            return n_set

        def _host(key):
            """Place one piece that stands alone. True when it stood."""
            nonlocal added
            p = _PIECES[key]
            if p["most"] is not None and per_name[key] >= p["most"]:
                return False
            sizes = [s for s in _palette(spec, key)
                     if per_size[(key, s)] < _SAME_PIECE_MAX]
            rng.shuffle(sizes)
            for size in sizes:
                w, d, h = size
                if h is None:
                    h = min(clear_h, _TO_CEILING_MAX)
                if h > clear_h:
                    continue
                half = max(w, d) / 2.0
                if p["where"] in ("seat", "pair"):
                    return False
                if p["where"] == "wall":
                    spots = [(qx, qy, sx, sy, front) for qx, qy, sx, sy, _r, front
                             in _wall_slots(spec, room, w, d, rng, with_front=True)]
                elif p["where"] == "centre":
                    # the room's middle first, then the grid from the middle
                    # out; the long side along the room's long axis
                    sx, sy = (w, d) if (x1 - x0) >= (y1 - y0) else (d, w)
                    near = sorted(floor_cands,
                                  key=lambda q: math.hypot(q[0] - rcx, q[1] - rcy))
                    spots = [(rcx, rcy, sx, sy, None)] + [
                        (qx, qy, sx, sy, None) for qx, qy in near]
                else:
                    spots = []
                    for qx, qy in floor_cands:
                        if p["front"]:
                            # A floor piece with a front faces AWAY from the
                            # room's middle, so whoever uses it -- a desk's
                            # sitter -- faces the room.
                            dx, dy = qx - rcx, qy - rcy
                            front = ((90.0 if dx > 0 else 270.0)
                                     if abs(dx) > abs(dy) else
                                     (0.0 if dy > 0 else 180.0))
                            sx, sy = (w, d) if front in (0.0, 180.0) else (d, w)
                        else:
                            front = None
                            sx, sy = (w, d) if rng.random() < 0.5 else (d, w)
                        spots.append((qx, qy, sx, sy, front))
                hung = p["lift"] is not None
                above = (p["lift"] - h / 2.0) if hung else None
                for qx, qy, sx, sy, front in spots:
                    if _over_rects(inner, qx, qy, half, half):
                        continue
                    # a hung piece takes no share of the floor: it clears
                    # what reaches up to it and holds no spread against
                    # the pieces standing under it
                    if not _seed_clear(spec, room, qx, qy,
                                       [] if hung else placed, half=half,
                                       above=above):
                        continue
                    rot = (_front_turn(key, sx, sy, front)
                           if front is not None else 0.0)
                    vol = _volume(key, qx, qy, sx, sy, h, rot)
                    spec.setdefault("volumes", []).append(vol)
                    deck = _deck(key, vol)
                    if deck:
                        spec["volumes"].append(deck)
                    if not hung:
                        placed.append((qx, qy))
                    per_size[(key, size)] += 1
                    per_name[key] += 1
                    added += 1
                    if p["seats"]:
                        how, lo, hi = p["seats"]
                        vol["_front"] = front
                        vol["_seq"] = seq[0]
                        added += _seats(vol, (qx, qy), how, lo, hi,
                                        extra=(deck,) if deck else ())
                        del vol["_front"], vol["_seq"]
                    return True
            return False

        def _cluster(pool, n):
            """Place 2-4 small pieces as one group. Returns pieces placed."""
            nonlocal added
            members = []
            planned = collections.Counter()
            for _ in range(n):
                key = rng.choice(pool)
                sizes = [s for s in _palette(spec, key)
                         if s[2] is not None and s[2] <= _CLUSTER_MAX_H
                         and per_size[(key, s)] + planned[(key, s)] < _SAME_PIECE_MAX]
                if not sizes:
                    continue
                size = rng.choice(sizes)
                planned[(key, size)] += 1
                w, d, _h = size
                members.append((key, size) + ((w, d) if rng.random() < 0.5
                                               else (d, w)))
            while members:
                # a row, or two rows when there are four
                rows = ([members[:2], members[2:]] if len(members) == 4
                        else [members])
                lay, y = [], 0.0
                bw = 0.0
                for row in rows:
                    depth = max(m[3] for m in row)
                    x = 0.0
                    for i, m in enumerate(row):
                        if i:
                            x += rng.uniform(*_CLUSTER_GAP)
                        lay.append((m, x + m[2] / 2.0, y + depth / 2.0))
                        x += m[2]
                    bw = max(bw, x)
                    y += depth + rng.uniform(*_CLUSTER_GAP)
                bd = max(m_y + m[3] / 2.0 for m, _mx, m_y in lay)
                if max(bw, bd) <= _CLUSTER_MAX_SPAN or len(members) == 1:
                    break
                members.pop()
            if not members:
                return 0
            lay = [(m, mx - bw / 2.0, my - bd / 2.0) for m, mx, my in lay]
            if rng.random() < 0.5:           # the whole group turned 90
                lay = [((m[0], m[1], m[3], m[2]), my, mx) for m, mx, my in lay]
                bw, bd = bd, bw
            half = max(bw, bd) / 2.0
            for cx, cy in floor_cands:
                # the group stands a body's width off the room's bounds, as a
                # piece on a candidate does, so no wall and group make a slot
                if not (x0 + 1.0 <= cx - bw / 2.0 and cx + bw / 2.0 <= x1 - 1.0
                        and y0 + 1.0 <= cy - bd / 2.0 and cy + bd / 2.0 <= y1 - 1.0):
                    continue
                if _over_rects(inner, cx, cy, bw / 2.0, bd / 2.0):
                    continue
                if not _seed_clear(spec, room, cx, cy, placed, half=half):
                    continue
                for (key, size, sx, sy), mx, my in lay:
                    rot = 180.0 if rng.random() < 0.5 else 0.0
                    vol = _volume(key, cx + mx, cy + my, sx, sy, size[2], rot)
                    spec.setdefault("volumes", []).append(vol)
                    per_size[(key, size)] += 1
                    per_name[key] += 1
                    added += 1
                placed.append((cx, cy))
                return len(lay)
            return 0

        short = 0
        for item in _furnish_plan(recipe, clusters, want, rng):
            if item[0] == "host":
                short += 0 if _host(item[1]) else 1
            else:
                short += item[2] - _cluster(item[1], item[2])
        # A PIECE THAT FITS NOWHERE LEAVES ITS SHARE TO THE FLOOR. Wall runs
        # stand only where `_seed_clear` lets them, a metre off any
        # partition, so a room walled in by partitions places none of its
        # run; that share goes to its floor sets and clusters, once each,
        # rather than leaving the room emptier than its recipe says.
        tries = 0
        while short > 0 and tries < 4 and (recipe["floor"] or clusters):
            tries += 1
            if recipe["floor"] and (not clusters or tries % 2):
                short -= 1 if _host(rng.choice(recipe["floor"])) else 0
            else:
                pool, lo, hi = rng.choice(clusters)
                short -= _cluster(pool, max(1, min(short, hi)))
    # THE BACK BARS BEFORE THE FIXTURES, because this pass MOVES counters
    # (0.137.0) and a dartboard's throwing lane is measured against where
    # the furniture actually stands. Both read only the spec, so a room
    # this call furnished and a room an earlier release furnished get the
    # same answer.
    added += sum(1 for r in back_bar_club_counters(spec)
                 if r["built"] and r["why"] != "already")
    # FIXTURES LAST, over every room, from the spec alone (0.136.0): a room
    # furnished in this call and a room furnished by an earlier release get
    # the same pass, so `migrate_club_fixtures.py` is this line.
    return added + place_fixtures(spec)


def enrich(spec):
    """Apply the full felt-space layer to a finished spec, in place.

    Idempotent and additive. Returns a small report dict so callers/tests can
    see what was added.
    """
    report = {
        # COVER FIRST, FURNITURE SECOND, and the order is load-bearing.
        # Furniture ran first for one draft and `test_cover_breaks_sightlines`
        # refused it: eleven rooms across the corpus ended with cover and no
        # SHELTER, because a furnished room fills the candidate grid and
        # `_seed_clear` then has nowhere to stand the one piece a body can
        # fight from. Gameplay-critical placement gets first pick of the
        # floor; furniture counts what is already there and fills the rest.
        # The teller line's staff side is walled BEFORE anything is placed,
        # so cover and furniture clear its walls and its locked doors.
        "tellers_enclosed": sum(r["enclosed"]
                                for r in enclose_teller_lines(spec)),
        # A VAULT IS A ROOM, walled and doored before anything is placed, for
        # the same reason: cover and furniture clear its walls, its deposit
        # boxes and the swing of its door (`vault_room.enclose_vaults`).
        "vaults_enclosed": sum(r["enclosed"] for r in
                               __import__("vault_room").enclose_vaults(spec)),
        "cover_seeded": seed_cover(spec),
        "furnished": furnish(spec),
        "cover_added": cover_from_volumes(spec),
        "landmarks_added": add_landmarks(spec),
    }
    return report


# ---------------------------------------------------------------------------
# TELLER ENCLOSURE -- the staff side of a teller line is its own locked room
# ---------------------------------------------------------------------------
#
# The walker, cold run 9048: "this bank teller booth should connect and be
# locked to the public... So its a section where only employees can be there
# and enter/exit, we only have the front of the teller windows." Measured
# before this existed: the bank preset and every `bank_branch` / `bank_job`
# spec author the teller line as a free-standing 12 x 0.8 x 2.4 m glass
# barrier in the lobby (Deli Counter 0.119.0), walked round at either end --
# the public side and the staff side were one room.

#: A teller line: a volume this long and this tall whose name says teller.
#: `teller_desk_*` (the towers' discrete desks) are islands, not a line.
_TELLER_NAMES = ("teller_counter", "teller_line")
_TELLER_MIN_LENGTH = 6.0
_TELLER_MIN_HEIGHT = 2.0
#: How deep the staff side may be, counter face to back wall. Shallower than
#: a body plus a door leaf cannot hold a person working the counter; deeper
#: is a back office, not the space behind a teller line.
_STAFF_MIN_DEPTH = 1.85
_STAFF_MAX_DEPTH = 6.0
_STAFF_DOOR_WIDTH = 1.25            # agent_contract min_door_width_m
_LEAF_MARGIN = 0.3                  # layout_lint.LEAF_MARGIN

#: The staff door's state machine: an ordinary door that ships LOCKED, with
#: unlock / lock and the usual toggle once unlocked. Merged over the inferred
#: door machine (`interactives.derive_interactive`), so the id, material and
#: breach class still come from the opening.
STAFF_DOOR_MACHINE = {
    "states": ["locked", "closed", "open"],
    "default": "locked",
    "transitions": [
        {"event": "unlock", "from": "locked", "to": "closed"},
        {"event": "lock", "from": "closed", "to": "locked"},
        {"event": "toggle", "from": "closed", "to": "open"},
        {"event": "toggle", "from": "open", "to": "closed"},
    ],
    "reversible": True,
    "collision_per_state": {"locked": True, "closed": True, "open": False},
    "access": "staff",
}


def _teller_lines(spec):
    H = float(spec.get("story_height") or 3.0)
    out = []
    for v in spec.get("volumes") or []:
        name = (v.get("name") or "").lower()
        if not any(n in name for n in _TELLER_NAMES):
            continue
        sx, sy, sz = v.get("size_x", 0), v.get("size_y", 0), v.get("size_z", 0)
        if max(sx, sy) < _TELLER_MIN_LENGTH or sz < _TELLER_MIN_HEIGHT:
            continue
        story = int(round((v["z"] - sz / 2.0) / H))
        out.append((v, story, "X" if sx >= sy else "Y"))
    return out


def _room_containing(spec, story, x, y):
    best, area = None, None
    for r in spec.get("rooms") or []:
        if r.get("story", 0) != story or not r.get("bounds"):
            continue
        x0, y0, x1, y1 = r["bounds"]
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            a = (x1 - x0) * (y1 - y0)
            if area is None or a < area:
                best, area = r, a
    return best


def _public_side(spec, story, room, axis, centre):
    """+1 / -1: the side of the counter line the room's exterior doors are
    on, or None when the room has no exterior door on either side."""
    hx = spec["footprint_x"] / 2.0
    hy = spec["footprint_y"] / 2.0
    x0, y0, x1, y1 = room["bounds"]
    votes = 0
    for w in spec.get("ext_walls") or []:
        if w.get("story", 0) != story:
            continue
        face = w.get("wall")
        for op in w.get("openings") or []:
            if op.get("kind") not in ("door", "garage"):
                continue
            if face in ("N", "S"):
                u, fixed = op.get("pos", 0.0) * spec["footprint_x"], (
                    hy if face == "N" else -hy)
                if not (x0 - 1e-6 <= u <= x1 + 1e-6):
                    continue
                if axis == "X":
                    votes += 1 if fixed > centre else -1
            else:
                u, fixed = op.get("pos", 0.0) * spec["footprint_y"], (
                    hx if face == "E" else -hx)
                if not (y0 - 1e-6 <= u <= y1 + 1e-6):
                    continue
                if axis == "Y":
                    votes += 1 if fixed > centre else -1
    return None if votes == 0 else (1 if votes > 0 else -1)


def _back_wall(spec, story, axis, centre, c0, c1, side):
    """The nearest wall parallel to the counter on `side`, spanning it:
    ``(pos, host_partition_or_None)`` or None."""
    hx = spec["footprint_x"] / 2.0
    hy = spec["footprint_y"] / 2.0
    best = None
    for p in spec.get("partitions") or []:
        if p.get("story", 0) != story or str(p.get("axis")).upper() != axis:
            continue
        pos = float(p["pos"])
        if (pos - centre) * side <= 0:
            continue
        lo, hi = sorted((p.get("start", -1e9), p.get("end", 1e9)))
        if lo > c0 + 1e-6 or hi < c1 - 1e-6:
            continue
        if best is None or abs(pos - centre) < abs(best[0] - centre):
            best = (pos, p)
    ext = (hy if side > 0 else -hy) if axis == "X" else (hx if side > 0 else -hx)
    if best is None or abs(ext - centre) < abs(best[0] - centre):
        best = (ext - side * (spec.get("wall_thick") or 0.3) / 2.0, None)
    return best


def enclose_teller_lines(spec):
    """Close the staff side of every teller line into its own room behind two
    LOCKED staff doors. Idempotent: a spec that already has a
    ``teller_staff_*`` room is left alone. Returns ``[report]``, one entry per
    teller line: ``{"volume", "enclosed": bool, "why"}``.

    For a teller line along x at y = c: the public side is the side the
    room's exterior doors are on; the staff side runs from the counter's
    centre line to the nearest parallel wall on the other side, across the
    counter's length. Two partitions close its ends, each with a locked
    `staff_door` (`STAFF_DOOR_MACHINE`), and a `staff_only` room is added
    innermost inside the host room. A line is left open, and the report says
    why, when the staff side is shallower than `_STAFF_MIN_DEPTH` or deeper
    than `_STAFF_MAX_DEPTH`, when the back wall has a doorway inside the
    counter's span (the space would not be closed), or when a stair, ladder
    or solid volume stands where a new wall would.
    """
    report = []
    if any(str(r.get("id", "")).startswith("teller_staff")
           for r in spec.get("rooms") or []):
        return report
    if not spec.get("footprint_x") or not spec.get("footprint_y"):
        return report
    for k, (v, story, axis) in enumerate(_teller_lines(spec)):
        entry = {"volume": v["name"], "enclosed": False, "why": ""}
        report.append(entry)
        room = _room_containing(spec, story, v["x"], v["y"])
        if room is None:
            entry["why"] = "no room holds the teller line"
            continue
        centre = v["y"] if axis == "X" else v["x"]
        along = v["x"] if axis == "X" else v["y"]
        length = v["size_x"] if axis == "X" else v["size_y"]
        thick = v["size_y"] if axis == "X" else v["size_x"]
        c0, c1 = along - length / 2.0, along + length / 2.0
        public = _public_side(spec, story, room, axis, centre)
        if public is None:
            entry["why"] = "no exterior door says which side is public"
            continue
        staff = -public
        back = _back_wall(spec, story, axis, centre, c0, c1, staff)
        if back is None:
            entry["why"] = "no wall behind the counter"
            continue
        wall_pos, host = back
        depth = abs(wall_pos - centre) - thick / 2.0
        if not (_STAFF_MIN_DEPTH <= depth <= _STAFF_MAX_DEPTH):
            entry["why"] = f"staff side {depth:.2f} m deep"
            continue
        if host is not None:
            lo, hi = sorted((host["start"], host["end"]))
            blocked = False
            for op in host.get("openings") or []:
                if op.get("kind", "door") not in ("door", "garage", "breach"):
                    continue
                u = (lo + hi) / 2.0 + op.get("pos", 0.0) * (hi - lo)
                w = float(op.get("width") or 1.0)
                if u + w / 2.0 > c0 - _LEAF_MARGIN and u - w / 2.0 < c1 + _LEAF_MARGIN:
                    blocked = True
            if blocked:
                entry["why"] = "the back wall has a doorway inside the line"
                continue
        z_lo = story * float(spec.get("story_height") or 3.0)
        n_lo, n_hi = sorted((centre, wall_pos))
        clash = None
        for other in spec.get("volumes") or []:
            if other is v or other.get("collision") == "none":
                continue
            if other["z"] + other["size_z"] / 2.0 <= z_lo + 1e-6:
                continue
            if other["z"] - other["size_z"] / 2.0 >= z_lo + spec["story_height"] - 1e-6:
                continue
            ox0, ox1 = other["x"] - other["size_x"] / 2.0, other["x"] + other["size_x"] / 2.0
            oy0, oy1 = other["y"] - other["size_y"] / 2.0, other["y"] + other["size_y"] / 2.0
            a_lo, a_hi, p_lo, p_hi = ((ox0, ox1, oy0, oy1) if axis == "X"
                                      else (oy0, oy1, ox0, ox1))
            for line in (c0, c1):
                if a_lo - 0.1 < line < a_hi + 0.1 and p_hi > n_lo and p_lo < n_hi:
                    clash = other["name"]
        for rect in _stair_reserved_rects(spec):
            x0, y0, x1, y1 = rect
            zx0, zx1 = (c0, c1) if axis == "X" else (n_lo, n_hi)
            zy0, zy1 = (n_lo, n_hi) if axis == "X" else (c0, c1)
            if x1 > zx0 - 0.5 and x0 < zx1 + 0.5 and y1 > zy0 - 0.5 and y0 < zy1 + 0.5:
                clash = "a stair"
        for lad in spec.get("ladders") or []:
            lx, ly = lad["x"], lad["y"]
            a, p = (lx, ly) if axis == "X" else (ly, lx)
            if c0 - 1.0 < a < c1 + 1.0 and n_lo - 1.0 < p < n_hi + 1.0:
                clash = "a ladder"
        if clash:
            entry["why"] = f"{clash} stands where a staff wall would"
            continue
        wall_axis = "Y" if axis == "X" else "X"
        material = (host or {}).get("material") or spec.get("default_material")
        for end, tag in ((c0, "a"), (c1, "b")):
            part = {"story": story, "axis": wall_axis, "pos": round(end, 3),
                    "start": round(centre, 3), "end": round(wall_pos, 3),
                    "openings": [{"kind": "door", "pos": 0.0,
                                  "width": _STAFF_DOOR_WIDTH,
                                  "tag": f"staff_door_{k}{tag}",
                                  "interactive": dict(STAFF_DOOR_MACHINE)}]}
            if material:
                part["material"] = material
            spec.setdefault("partitions", []).append(part)
        bx = ([c0, n_lo, c1, n_hi] if axis == "X" else [n_lo, c0, n_hi, c1])
        spec.setdefault("rooms", []).append({
            "id": f"teller_staff_{k}", "story": story,
            "bounds": [round(b, 3) for b in bx], "role": "staff_only",
            "fortifiable": True, "combat_range": "close"})
        entry["enclosed"] = True
        entry["why"] = f"staff side {depth:.2f} m deep, two locked doors"
    return report
