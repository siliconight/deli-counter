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


def _seed_clear(spec, room, px, py, placed, half=0.0):
    """Candidate point clear of walls, openings, verticals, props, markers.
    `half` is the worst-case half-extent of the piece that will stand here:
    clearances are measured from the piece's EDGE, not its center -- a 2.6 m
    shelf run can intrude a ladder's climb envelope while its center is
    comfortably clear (found by the 100-seed regression sweep)."""
    story = room.get("story", 0)
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
    for room in spec.get("rooms", []):
        if not room.get("combat_range"):
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


#: Room role/id keywords -> the FURNITURE placed there, as
#: ``(name, w, d, h, where)``. `where` is "wall" for anything that stands
#: against one and "floor" for anything that does not.
#:
#: NOTHING MID-FLOOR REACHES SHELTER HEIGHT, which is the invariant and not
#: the one first written here. The first draft said every floor piece sits
#: below `_COVER_MIN_Z` (0.60) and `test_furnish` refuted it on its first
#: run: a desk is 0.75 and a floor safe is 1.00. A desk IS low cover, here
#: and in a real office, and furnishing rooms with nothing but chairs to
#: avoid saying so would be the tail wagging the dog. What `seed_cover`'s
#: over-cover thesis protects is SHELTER -- somewhere a body can fight
#: from, at `cover_break_height` -- and this pass never creates one:
#: anything that tall goes flush against a wall, where it is a bookcase
#: rather than a redoubt.
#:
#: Names are chosen so `prop_species.species_for_name` routes every one of
#: them to a species Zoo builds. A furniture volume that comes out a grey
#: box is the defect this pass exists to reduce.
_FURNITURE = (
    (("office", "manager", "exec", "admin", "suite", "detective", "staff"),
     (("desk", 1.6, 0.8, 0.75, "floor"),
      ("chair", 0.55, 0.55, 0.9, "floor"),
      ("cabinet_file", 0.9, 0.5, 1.4, "wall"),
      ("shelf_run", 2.0, 0.4, 1.9, "wall"))),
    (("storage", "stock", "back", "parts", "ware", "supply"),
     (("shelf_run", 2.6, 0.6, 1.9, "wall"),
      ("cabinet_supply", 1.0, 0.5, 1.8, "wall"),
      ("table_work", 1.6, 0.8, 0.55, "floor"))),
    (("bay", "garage", "loading", "dock", "shop", "service"),
     (("workbench", 2.0, 0.8, 0.9, "wall"),
      ("shelf_run", 2.4, 0.6, 1.9, "wall"),
      ("cabinet_tool", 0.9, 0.5, 1.8, "wall"))),
    (("vault", "loot", "safe_room", "armory", "evidence"),
     (("shelf_run", 2.2, 0.5, 1.9, "wall"),
      ("cabinet_locker", 1.2, 0.5, 1.9, "wall"),
      ("safe_floor", 0.9, 0.9, 1.0, "floor"))),
    (("utility", "plant", "mech", "boiler", "server"),
     (("tank_water", 1.2, 1.2, 1.8, "wall"),
      ("cabinet_panel", 0.9, 0.5, 1.8, "wall"),
      ("shelf_run", 2.0, 0.5, 1.9, "wall"))),
    (("lobby", "public", "hall", "concourse", "booking", "ward", "waiting",
      "entry", "floor", "retail", "shop_floor"),
     (("chair_waiting", 2.4, 0.6, 0.9, "wall"),
      ("table_low", 1.0, 0.6, 0.45, "floor"),
      ("counter_service", 2.2, 0.8, 1.05, "wall"))),
)
#: Anything whose role matches nothing above. A room with a table and two
#: chairs reads as a room; a room with nothing reads as a corridor.
_FURNITURE_DEFAULT = (("table_low", 1.2, 0.8, 0.5, "floor"),
                      ("chair", 0.55, 0.55, 0.9, "floor"))
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
_PROP_MATERIALS = (
    (("safe", "tank", "locker", "panel", "hvac", "vault", "roof_ac", "ac_unit",
      "condenser", "generator", "dumpster"), "metal"),
)
_PROP_MATERIAL_DEFAULT = "wood"
_PROP_ACOUSTIC = {"wood": ("Wood", 0.35, 0.3), "metal": ("Metal", 0.2, 0.15)}


def _prop_material(spec, name):
    """The material a placed piece wears, declared in the spec's palette if it
    is not already -- the validator refuses an undeclared material id."""
    key = (name or "").lower()
    mat = _PROP_MATERIAL_DEFAULT
    for words, m in _PROP_MATERIALS:
        if any(w in key for w in words):
            mat = m
            break
    have = {m.get("id") for m in spec.get("materials") or []}
    if mat not in have and mat != "wood":
        acoustic, absorption, damping = _PROP_ACOUSTIC[mat]
        spec.setdefault("materials", []).append(
            {"id": mat, "acoustic": acoustic, "absorption": absorption,
             "damping": damping})
    return mat


def _furniture_for(room):
    key = ((room.get("role") or "") + " " + str(room.get("id", ""))).lower()
    for words, pieces in _FURNITURE:
        if any(w in key for w in words):
            return pieces
    return _FURNITURE_DEFAULT


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


def _wall_slots(spec, room, w, d, rng):
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
                        long_side, short_side, 180.0 if inset > 0 else 0.0))
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
                        short_side, long_side, 180.0 if inset > 0 else 0.0))
    rng.shuffle(out)
    return out


def _furnish_target(area):
    """How many pieces a room of `area` square metres wants.

    One per `_FURNISH_PER_AREA` up to `_FURNISH_MAX`: an office. Past that the
    room is a hall and gets one per `_FURNISH_HALL_PER_AREA`, to
    `_FURNISH_HALL_MAX`. A 120 m2 office wants 8; cold run 9044's brewery
    hall, about 1,000 m2, wanted 63 at office density, got 10 under the old
    cap and wants 25 now."""
    office = max(1, int(round(area / _FURNISH_PER_AREA)))
    hall = max(_FURNISH_MAX, int(round(area / _FURNISH_HALL_PER_AREA)))
    return min(office, hall, _FURNISH_HALL_MAX)


def furnish(spec):
    """Put FURNITURE in the rooms -- a different question from cover.

    `seed_cover` asks whether a room can be fought in and deliberately keeps
    its count low; this asks whether a room looks lived in, and the two do
    not trade against each other because nothing placed mid-floor here
    reaches SHELTER height and everything that tall goes flush against a
    wall. (An earlier line here said mid-floor pieces stay below
    `_COVER_MIN_Z`; `test_furnish` refuted it -- a desk is 0.75 m.)

    Deterministic (spec seed + room id), additive and idempotent: existing
    volumes count toward the target, so a second run adds nothing. Returns
    the number of volumes created.
    """
    import random
    base_seed = spec.get("seed", 0)
    sh = _story_height(spec)
    added = 0
    for room in spec.get("rooms", []):
        x0, y0, x1, y1 = room["bounds"]
        area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        if area < _FURNISH_MIN_AREA:
            continue
        pieces = _furniture_for(room)
        # IDEMPOTENT BY MARK, NOT BY COUNT. Counting the room's volumes is
        # not enough: a first pass that ran out of clear floor leaves the
        # count short, and a second pass then finds the spots the first
        # pass's own pieces opened up and adds more. `test_the_shelter_pass
        # _is_idempotent` caught exactly that -- five extra pieces in a
        # hospital on a re-enrich. A room this pass has already touched is
        # recognisable from its volume NAMES and is skipped outright.
        stems = {p[0] for p in pieces} | {"chair_set"}
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
        have = _room_volume_count(spec, room)
        want = max(0, _furnish_target(area) - have)
        if want <= 0:
            continue
        rng = random.Random(f"{base_seed}:{room['id']}:furnish")
        story = room.get("story", 0)
        placed = []
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
        for k in range(want):
            name, pw, pd, ph, where = pieces[k % len(pieces)]
            half = max(pw, pd) / 2.0
            spots = (_wall_slots(spec, room, pw, pd, rng) if where == "wall"
                     else [(px, py, pw, pd, 0.0) for px, py in floor_cands])
            for (px, py, sx, sy, face_room) in spots:
                if not _seed_clear(spec, room, px, py, placed, half=half):
                    continue
                vol = {
                    "name": f"{name}_{rtag}_{k + 1}",
                    "x": round(px, 2), "y": round(py, 2),
                    "z": round(story * sh + ph / 2.0, 3),
                    "size_x": round(sx, 3), "size_y": round(sy, 3),
                    "size_z": round(ph, 3),
                    "collision": "convex",
                    "material": _prop_material(spec, name),
                }
                # a wall piece's front faces into the room, not the wall
                # ("Chairs shouldnt face walls like this where humans couldnt
                # sit in them", the walker, cold run 9048)
                if face_room:
                    vol["rot_z"] = face_room
                spec.setdefault("volumes", []).append(vol)
                placed.append((px, py))
                added += 1
                # A TABLE BRINGS ITS CHAIRS. Scattered tables read as crates;
                # a table with a chair either side reads as a place people
                # sit. Up to two, on the long sides, only where they clear.
                # They belong to the table and do not count toward `want`.
                if where == "floor" and name.startswith("table") and \
                        name != "table_work":
                    table = spec["volumes"][-1]
                    along_x = sx >= sy
                    for j, sgn in enumerate((-1, 1)):
                        cx = px if along_x else px + sgn * (sx / 2 + 0.45)
                        cy = py + sgn * (sy / 2 + 0.45) if along_x else py
                        if not (x0 + 0.4 < cx < x1 - 0.4 and
                                y0 + 0.4 < cy < y1 - 0.4):
                            continue
                        # THE CHAIR PASSES THE SAME CLEARANCE AS EVERY OTHER
                        # PIECE, minus its own table, which it must stand
                        # beside. The first draft skipped the check and put a
                        # chair on `credit_union_a02`'s upper stair landing.
                        view = dict(spec, volumes=[v for v in spec["volumes"]
                                                   if v is not table])
                        # `placed` enforces a 2.2 m SPREAD between pieces,
                        # which is right for tables and wrong for a table's
                        # own chairs, 0.75 m from it -- so the set is checked
                        # against every other placed piece, not its own.
                        others = [q for q in placed if q != (px, py)]
                        if not _seed_clear(view, room, cx, cy, others,
                                           half=0.25):
                            continue
                        # FACING THE TABLE. Slot rotation is a COMPASS
                        # bearing -- `Builder._slot_orient` puts N at 0, E at
                        # 90, S at 180, W at 270 -- turning a module's local
                        # +Y onto that bearing. A chair's seated front is its
                        # local -Y (its back panel is at +Y), so the front
                        # points at bearing + 180, and aiming it at the table
                        # from a chair offset (dx, dy) gives atan2(dx, dy).
                        # The first draft used atan2(-dx, dy): right for the
                        # chairs north and south of a table, backwards for
                        # the ones east and west, caught by re-reading the
                        # wall convention before a rebuild rather than after.
                        face = math.degrees(math.atan2(cx - px, cy - py))
                        spec["volumes"].append({
                            "material": _prop_material(spec, "chair"),
                            "name": f"chair_set_{rtag}_{k + 1}_{j + 1}",
                            "x": round(cx, 2), "y": round(cy, 2),
                            "z": round(story * sh + _CHAIR_H / 2.0, 3),
                            "size_x": 0.5, "size_y": 0.5, "size_z": _CHAIR_H,
                            "collision": "convex",
                            "rot_z": float(int(round(face / 90.0)) * 90 % 360),
                        })
                        added += 1
                break
            # A piece that fits nowhere is simply not placed. A room with no
            # wall long enough for a shelf run is a fact about the room.
    return added


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
