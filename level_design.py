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


def opening_head(spec, story):
    """The highest HEAD -- sill plus height -- of any opening on `story`,
    exterior and partition alike, in metres off that storey's floor.

    From the spec's own openings through `spec_types.Opening.resolved`, so
    the per-kind defaults are read from the one place that declares them
    (door 2.2, breach 2.2, window 1.0 + 1.4, garage 3.0, teller 3.0,
    safe_deposit 2.4, vault 2.1) rather than spelled again here. A storey
    with no openings answers 0.0.
    """
    import spec_types
    head = 0.0
    for group in ("ext_walls", "partitions"):
        for w in spec.get(group) or []:
            if int(w.get("story", 0) or 0) != int(story or 0):
                continue
            for op in w.get("openings") or []:
                try:
                    r = spec_types.Opening(
                        kind=op.get("kind", "door"),
                        width=op.get("width"), height=op.get("height"),
                        sill=op.get("sill")).resolved()
                except KeyError:          # a kind this build does not know
                    continue
                head = max(head, float(r["sill"]) + float(r["height"]))
    return head


def _over_openings(spec, story, piece, h):
    """`hangs_over_openings` asked of a PIECE and a built height, for the
    two callers that must know before the volume exists (`_wall_slots`
    needs it to decide whether a slot may span a window)."""
    lift = _piece_lift(spec, piece, h)
    return hangs_over_openings(spec, story,
                               None if lift is None else lift - h / 2.0)


def hangs_over_openings(spec, story, above):
    """Is a piece whose BOTTOM is `above` metres off the floor hung clear of
    every doorway and window on this storey?

    WHAT THIS BUYS, AND WHY IT IS NOT A LOOSENING. Three of `_seed_clear`'s
    rules -- a metre off any partition, 1.5 m plus the piece from an
    exterior opening, the same from a partition's -- exist because a body
    walks through doors and along walls, and a solid standing in that
    approach is a solid it walks into. A strip hung ABOVE every opening
    head is not in anybody's approach: the reference's pennant row runs
    along the top of the wall, straight over the door, which is where a
    pennant row goes.

    MEASURED INERT ON EVERYTHING THAT SHIPPED. The bottom of every hung
    piece this pass writes today is 1.85 m (`neon_sign` 2.2 - 0.7/2 and
    `wall_tv` 2.1 - 0.5/2) or 1.28 m (`dartboard` 1.73 - 0.9/2), and each
    of those lifts is a fixed number, not a function of the storey. A plain
    door's head is 2.2 m. So no piece written before 0.139.0 can be exempt
    at any storey height, and `test_the_over_opening_exemption_reaches_no
    _older_piece` is what says so rather than this paragraph.
    """
    if above is None:
        return False
    return above >= opening_head(spec, story) - 1e-9


def _seed_clear(spec, room, px, py, placed, half=0.0, above=None,
                over_openings=False):
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
    # THE THREE RULES A PIECE HUNG OVER EVERY OPENING DOES NOT ANSWER
    # TO (`over_openings`, from `hangs_over_openings`): a metre off a
    # partition, and the 1.5 m approach to an exterior or a partition
    # opening. All three are about a body walking through a door or
    # along a wall, and a strip above every head is in nobody's path --
    # the reference's pennant row runs straight over the door. The
    # stair, ladder, vault-leaf, volume and spread rules are NOT exempt:
    # a stair's headroom and a tall volume reach up to it.
    for p in spec.get("partitions", []):
        if over_openings:
            break
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
        if over_openings:
            break
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
        if over_openings:
            break
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
#: Air left between a to-the-ceiling piece's top and the ceiling plane, so
#: the two are not coplanar (a furnace's flue runs to the slot's top). It is
#: also what a piece hung UNDER the ceiling leaves above itself, so it is
#: declared here, above `_PIECES`, which reads it at import.
_CEILING_AIR = 0.05

#: Zoo's `pack_wall` genome height max, read from
#: `zoo/zoo_keeper/genome/species/pack_wall.json` (`dimensions.height.max`),
#: 2026-09-16. A slot authored above it is a hint Zoo cannot build: it draws
#: the plain box and says so, which is "a keyword whose every match cannot be
#: built" one layer down. Declared here, above `_PIECES`, which reads it at
#: import. `test_card_shop` checks it against the genome when Zoo is
#: reachable (`DC_ZOO_ROOT`), so this number cannot drift from the file it
#: was copied out of without something failing.
PACK_WALL_CEILING = 3.2

#: THE CARD SHOP'S ROOM BUDGET, in triangles, and where it comes from --
#: because the number it replaces was not a budget.
#:
#: 0.139.0 capped this room against **10,664**, which is Zoo 0.95.0's
#: MEASUREMENT of one card-shop room at every worst-case genome corner (one
#: L case, four pack bays, four pennant rows, three tables, eight chairs).
#: Zoo publishes it under the heading "THE ROOM-LEVEL NUMBER, because a
#: species budget is not a room" and immediately gives the scale: "For
#: scale, one `cubicle_bank` is budgeted 24,000 and the club's `back_bar`
#: 8,500." A measurement of a reference furnishing is not a ceiling, and
#: treating it as one capped the shipped room BELOW the reference it cited
#: -- two pack walls where the reference has four, two pennant rows where
#: it has four -- and the walker walked it and called it a hall.
#:
#: The only real budgets in this toolchain are Zoo's per-MODULE
#: `budgets.tris_lod0`. The largest is `cubicle_bank`'s 24,000, one prop,
#: and it is the figure Zoo itself offered for scale. So a selling room is
#: allowed the triangles of one cubicle bank. That is a comparison the
#: toolchain already makes rather than a number chosen here, and the caps
#: below are set so that the worst case the palette can produce lands under
#: it (22,304, 93 %) -- see `test_card_shop`, which multiplies the caps out
#: against Zoo's own planner and FAILS if they ever exceed this.
#:
#: IT IS STILL CONSERVATIVE AND IT IS STILL NOT A FRAME TIME. There is no
#: runtime telemetry from a real session (CLAUDE.md, "every frame is spent
#: on somebody else's machine"), so this is a measured reference held
#: against a measured reference. When that data exists this is the dial,
#: and `most` is where it is spent.
_CARD_SHOP_ROOM_TRIS = 24000


def _piece(name, sizes, where, front=False, stock=None, variants=False,
           form=None, seats=None, most=None, lift=None, collision="convex",
           deck=None, lane=False, most_big=None, under=None,
           reserved_by=None, off_glass=False, backed_by=None,
           ceiling=None, under_hung=False, twin=False):
    return {"name": name, "sizes": tuple(sizes), "where": where,
            "front": front, "stock": stock, "variants": variants,
            "form": form, "seats": seats, "most": most, "lift": lift,
            "collision": collision, "deck": deck, "lane": lane,
            "most_big": most_big, "under": under, "reserved_by": reserved_by,
            "off_glass": off_glass, "backed_by": backed_by,
            "ceiling": ceiling, "under_hung": under_hung, "twin": twin}


def hung_band_bottom(spec):
    """The bottom of the LOWEST piece this pass hangs under the ceiling, in
    metres above its storey's floor -- the band the fixtures own.

    Asked by `to_ceiling_height` below, so that a piece authored "to the
    ceiling" stops under the strip rather than through it. Derived from the
    pieces themselves (`under`, via `_piece_lift`) and not written down: a
    pennant row's batten is `_CEILING_AIR` under the slab and the strip is
    0.30 deep, so at a 3.4 m storey the band starts at 2.75, and a taller
    hung piece moves it down without anything else being edited.

    `_clear_height` when nothing hangs, which is "no band".
    """
    low = None
    for p in _PIECES.values():
        if p["under"] is None:
            continue
        for size in p["sizes"]:
            h = size[2]
            if h is None:
                continue
            lift = _piece_lift(spec, p, float(h))
            if lift is None:
                continue
            bottom = lift - float(h) / 2.0
            low = bottom if low is None else min(low, bottom)
    return _clear_height(spec) if low is None else low


def to_ceiling_height(spec, piece, clear_h):
    """How tall a piece whose size says ``None`` is actually built.

    THREE LIMITS, AND THE FIRST TWO ARE WHY THIS IS NOT `min(clear_h,
    _TO_CEILING_MAX)` any more:

      * the SPECIES' own genome max (`ceiling`). `_TO_CEILING_MAX` is 4.0
        because Zoo's `furnace` tops out there; a `pack_wall` tops out at
        3.2, and a slot authored above its species' range is a hint that
        cannot be built -- Zoo draws the plain box and says so. A piece
        that names its ceiling is held to it.
      * the HUNG BAND (`under_hung`). The fixtures own the top of the wall
        (`hung_band_bottom`), so a shop fixture that fills its height stops
        `_CEILING_AIR` below them instead of standing through the pennants.
        Opt-in: a furnace's flue is meant to run to the slab, and making
        this universal would shorten every one in the library.
      * the storey's own clear height, as before.

    A piece that names neither is exactly what it was.

    ROUNDED DOWN, NOT ROUNDED. `round(x, 4)` can move a value UP by 5e-5,
    and every caller then asks a LIMIT of the result -- `_host` refuses a
    piece whose `h > clear_h` and the CRT pass refuses one that leaves no
    room above. A height derived as "exactly the clear height" that comes
    back 5e-5 over is a piece silently not placed, which is the shape
    `_wall_span` had: one quantity, two spellings, a threshold between
    them. Flooring makes the derived height never larger than the thing it
    was derived from, so both questions of it answer the same way.
    """
    top = float(clear_h)
    if piece["under_hung"]:
        top = min(top, hung_band_bottom(spec) - _CEILING_AIR)
    return _floor4(min(top, float(piece["ceiling"] or _TO_CEILING_MAX)))


def _floor4(x):
    """`x` to four decimals, never upward. See `to_ceiling_height`."""
    return math.floor(float(x) * 10000.0) / 10000.0


def piece_back_off(piece):
    """How far a wall piece's BACK stands off the wall FACE, or 0.

    A piece that gets a unit standing behind it (`backed_by`) is placed at
    its FINAL depth straight away -- the backing unit's depth plus the
    staff aisle -- instead of flush against the wall for a later pass to
    shove forward. `_WALL_PIECE_AIR` is inside this number rather than on
    top of it, so the back lands on exactly what `_staff_side_plan` asks
    for and its "already stands off its wall" branch does not fire on a
    1 cm overshoot.

    WHY, MEASURED. `card_shop_counters` moved the counter after the room
    was furnished, so the strip it moved into had been open floor for the
    whole of `seed_cover` and `furnish`: on `card_shop_a01` BOTH counters
    were then refused, one by `kiosk_sales_floor_shelter` (a shelter piece
    placed before any furniture) and one by `folding_chair_..._4_3` (a play
    chair placed after the counter). The pass reported both correctly and
    the shop came back with no pack wall, no CRT and no shopkeeper. Placed
    at its final depth, the counter's own `_seed_clear` keepout covers the
    staff band for every piece that comes after it, and the pieces that
    came before it are what keep it off that wall.
    """
    key = piece["backed_by"]
    if not key:
        return 0.0
    depth = {"pack_wall": PACK_WALL_DEPTH, "back_bar": BACK_BAR_DEPTH}[key]
    return round(depth + staff_aisle_width() - _WALL_PIECE_AIR, 4)


def _piece_lift(spec, p, h):
    """The height of a hung piece's CENTRE above its storey's floor, or None
    for a piece that stands on it.

    `lift` is a fixed height -- a dartboard's bull is 1.73 m whatever the
    storey is. `under` is the gap between the piece's TOP and the ceiling
    PLANE, which is the only way to say "along the top of the wall": a
    pennant row batten is screwed under the ceiling, so its height is the
    storey's and not a number. A fixed 2.95 would have been right at the
    card shop's 3.4 m storey and 0.6 m inside the slab at the strip club's
    3.6 m one.

    ONE FUNCTION, THREE CALLERS -- `_host`, `_place_fixture` and
    `_make_volume` each need this number, and `_host` needs it before the
    volume exists (it is what `_seed_clear`'s `above` is measured from).
    The first draft computed it twice and the two spellings drifted by
    `_CEILING_AIR`.
    """
    if p["lift"] is not None:
        return float(p["lift"])
    if p["under"] is None:
        return None
    return _clear_height(spec) - float(p["under"]) - h / 2.0


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
    # --- THE 1990s TRADING CARD SHOP (Zoo 0.95.0). The walker, 2026-09-15,
    # with nine photographs written up in
    # `docs/SET_DRESSING_REFERENCES.md`: a small sports-card shop, wood
    # panelling on the lower walls, a row of felt pennants along the top of
    # them, tall shelving of wax boxes faced out, and a glass-top showcase
    # counter in front with a register and a CRT behind it. Names route to
    # Zoo's `display_case`, `pack_wall`, `pennant_row`, `folding_table` and
    # `folding_chair` (`prop_species`); every size sits inside its genome's
    # range, read from `zoo/zoo_keeper/genomes/`, not from a brief. ---
    #
    # THE SHOWCASE COUNTER, and its DEPTH is the load-bearing number. Zoo
    # builds the case `params.case_depth` (0.60) deep whatever the slot is,
    # and `display_case_forms.pick_form` reads the slot's own depth: `auto`
    # takes the L when `d >= 2 * case_depth + 0.10`. So a 0.6 m slot is a
    # flat case and a deep one is an L whose inner corner Zoo leaves OPEN --
    # "which is where the staff stand and where Deli Counter's own aisle
    # runs", its collision comment says. `card_shop_counters` below is what
    # deepens the slot, and only where a perpendicular wall closes one end.
    # `off_glass` BECAUSE OF WHAT STANDS BEHIND IT, not because of the case:
    # `card_shop_counters` puts a 2.2 m pack wall flush against whatever
    # wall the case took, and on `card_shop_a01`'s first build one of the
    # two counters landed on the STOREFRONT -- a slatwall gondola across a
    # 4.0 m shop window, from the inside. A glass front is the one wall a
    # shop does not board up.
    _piece("display_case", ((2.4, 0.6, 1.0), (3.6, 0.6, 1.05),
                            (1.8, 0.6, 0.95)), "wall", front=True,
           variants=True, most=2, off_glass=True, backed_by="pack_wall"),
    # THE COUNTER'S RETURN END -- the short case that closes one end of the
    # staff aisle where a perpendicular wall already does, so the counter
    # reads as the reference's L and the other end is the way in. `pair`,
    # for the reason `back_bar`'s is: it belongs to a counter and
    # `card_shop_counters` is the only thing that stands one.
    #
    # WHY THIS IS A SECOND CASE AND NOT ZOO'S OWN `L` FORM, which would be
    # one module with one L-shaped glass top. Zoo takes the L from the
    # slot's DEPTH (`display_case_forms.pick_form`: `d >= 2 * case_depth +
    # 0.10`), so asking for it means authoring a slot 1.85 m deep whose
    # back 1.25 m is the aisle -- and Deli Counter writes ONE CONVEX BOX
    # over a hinted volume's whole slot unless the species is in
    # `prop_species.SPECIES_OWNS_COLLISION`. That box is the aisle, sealed:
    # the same defect `cubicle_bank` recorded in Zoo 0.93.0, and it would
    # be invisible to the nav gate, which grades the GREYBOX shells where
    # that box is the only collider there is. Putting `display_case` in
    # that set instead would take the collider off every showcase in the
    # library -- twelve authored ones, six of which build as the species --
    # to buy a corner. What the expensive version buys is one continuous
    # glass top rather than two cases meeting; it is worth reopening the
    # day a hinted volume can declare a collider that is not its slot.
    _piece("display_case_end", ((1.25, 0.6, 1.0),), "pair", front=True,
           variants=True),
    # THE PACK WALL: a gondola run of booster displays under a coloured
    # header a bay. Zoo's `bay_max` is 1.2, so a 3.6 m slot is three bays
    # each carrying a different game -- one wide slot reads as a run, which
    # is what the reference's aisle is. Placed BOTH by a wall run and by
    # `card_shop_counters` (behind the counter), so `where` is `wall` and
    # not the `pair` a back bar gets.
    # `most` IS THE ROOM'S TOTAL, AND `reserved_by` IS WHAT MAKES IT ONE:
    # `card_shop_counters` stands one pack wall per showcase counter, after
    # the wall run has spent the cap, so without it a two-counter floor
    # draws `most` PLUS two.
    #
    # THE CAP WAS 2 AND IS 4, AND THE FIRST NUMBER WAS A MISREADING RATHER
    # THAN A TRADEOFF. 0.139.0 held the room against 10,664 as if that were
    # a ceiling. It is not a budget at all: Zoo's own entry calls it "THE
    # ROOM-LEVEL NUMBER, because a species budget is not a room" and it is
    # a MEASUREMENT of one furnishing -- one L case, four pack bays, four
    # pennant rows, three tables, eight chairs -- published "for scale"
    # beside the one real budget in the file, `cubicle_bank`'s 24,000. So
    # the shipped shop was capped BELOW Zoo's own reference room while
    # citing that room as its limit, and the walker's verdict on the frame
    # was "the card shop should feel saturated". `_CARD_SHOP_ROOM_TRIS` is
    # the budget now and the arithmetic is there.
    #
    # HEIGHT IS FREE, AND THAT IS MEASURED, NOT ASSUMED. The heights here
    # were 2.2/2.2/2.4 in a room whose clear height is 3.10, leaving a
    # metre of bare wall over the product -- reference property 1 is the
    # opposite ("product goes to the ceiling, not to waist height"). Zoo's
    # genome runs 1.6 to 3.2 and its own note names the reference
    # "floor-to-ceiling gondola shelving". Planned through
    # `pack_wall_forms.plan` at every palette width over 2.2 - 3.2 m:
    # triangles DO NOT MOVE (a 2.4 m bay is 1,416 at every height), because
    # `CAPS["shelves_per_bay"]` (6) binds at every one of them and the cost
    # is bays, not metres. What it buys, measured on a 2.4 m bay: the top
    # stocked shelf rises from 1.78 m to 2.21 m at 2.70.
    #
    # WHAT IT COSTS, said rather than quietly narrowed: the six shelves
    # spread to fill the taller bay, so the pitch goes 0.259 -> 0.331 and a
    # bay reads slightly airier per metre. That cap is Zoo's
    # (`shelves_per_bay`), not this file's, and raising it is Zoo's call
    # with Zoo's budget -- 578 triangles a bay against 6,000.
    #
    # `None` IS THE HEIGHT, and `ceiling` / `under_hung` are what make that
    # safe: the species' own genome max, and the pennant band left free.
    # See `to_ceiling_height`.
    _piece("pack_wall", ((2.4, 0.5, None), (1.2, 0.5, None),
                         (3.6, 0.5, None)), "wall", front=True, variants=True,
           most=4, reserved_by="display_case",
           ceiling=PACK_WALL_CEILING, under_hung=True),
    # THE ISLAND GONDOLA -- the same species standing in the OPEN FLOOR,
    # back to back with itself, with a walkable aisle all round it.
    #
    # REFERENCE PROPERTY 2, and the frame is the argument: "two of the
    # photos show gondola endcaps and low island displays on casters
    # standing in the open floor, with aisles between them rather than one
    # clear span. The current recipe treats the floor as circulation and
    # puts everything against a wall. That is what makes the frame read as
    # a hall: there is nothing between the camera and the far wall."
    #
    # `twin` BECAUSE A GONDOLA HAS ONE FACE. `pack_wall`'s back panel owns
    # +Y and carries no product; a single one mid-floor is a blank slatwall
    # sheet seen from half the room. An island in a shop IS two of them
    # back to back, which is what `where: "island"` writes -- one volume a
    # face, sharing a spine, each facing its own aisle. It doubles the
    # island's triangles and that is affordable at 1,416 a module against
    # `_CARD_SHOP_ROOM_TRIS`; the cheap version was not shipped because the
    # expensive one fits.
    #
    # NARROWER THAN THE WALL RUN. 2.4 m is an island, 3.6 m is a partition
    # across a 11 m room, and the reference's islands are endcaps. The cap
    # is 2 a room: at the palette's worst that is 4 modules x 1,416 =
    # 5,664, which is what is left under the room budget once the counters,
    # the wall gondolas, the pennants and the CRTs have taken theirs. A
    # third island is 2,832 more and would put the room at 25,136, over.
    _piece("pack_wall_island", ((2.4, 0.5, None), (1.8, 0.5, None),
                                (1.2, 0.5, None)), "island", front=True,
           variants=True, most=2, twin=True,
           ceiling=PACK_WALL_CEILING, under_hung=True),
    # THE PENNANTS, along the TOP of the wall -- `under`, not `lift`: the
    # batten is screwed under the ceiling, so its height is the storey's.
    # No collision: 2.9 m up at a 3.4 m storey, and Zoo's genome declares
    # `collision: false` for the same reason ("a body cannot reach a
    # pennant and a collider up there is a shape the navmesh bake carries
    # for nothing").
    #
    # `most` IS A BUDGET, NOT A TASTE. A pennant row costs what its budget
    # says however long it is -- `pennant_forms.max_pennants` is
    # `(budget - 12) // 20` = 44, so a 4 m strip and a 14 m strip both draw
    # ~892 triangles and length buys only spacing.
    #
    # THE CAP WAS 2 AND IS 4, which is ONE PER WALL and is Zoo's own
    # reference room ("one pennant row a wall"). 0.139.0 cut it to two
    # because four rows are "a third of Zoo's measured room (3,568 of
    # 10,664)" -- a third of a MEASUREMENT of a reference furnishing, which
    # was never the ceiling it was being read as (`_CARD_SHOP_ROOM_TRIS`).
    # 3,568 is 15 % of the budget that does exist. What the two extra rows
    # buy is the other two walls carrying colour at the one height nothing
    # else in the room reaches.
    _piece("pennant_row", ((6.0, 0.08, 0.3), (4.0, 0.08, 0.3),
                           (8.0, 0.08, 0.3)), "wall", front=True,
           variants=True, most=4, under=_CEILING_AIR, collision="none"),
    # THE PLAY AREA: banquet tables with two or three folding chairs each.
    # `cards` is `_surface_stock`'s seventh flavour (Zoo 0.95.0) -- a
    # playmat, card piles, deck boxes and dice, planned once per SIDE of
    # the top so two players' worth face each other.
    #
    # VARIANTS IS 2 AND NOT `True` ON BOTH FOLDING PIECES, and the number
    # is Zoo's `module_variants`, not a taste. `_make_volume` reads a bare
    # `True` as FOUR (`int(True)` is 1, which is not `> 1`), and Zoo's rule
    # is all-or-nothing: a variant outside 0..1 drops the `cards` stock
    # with it, so a play table asked for variant 2 would have come back
    # bare and nothing would have said why. Caught by
    # `test_zoo_honours_every_dressing_furnish_writes`, which is only run
    # when the Zoo repo is reachable -- see `DC_ZOO_ROOT` in that file.
    _piece("folding_table", ((1.8, 0.76, 0.74), (2.4, 0.76, 0.74),
                             (1.2, 0.7, 0.74)), "floor", stock="cards",
           variants=2, seats=("folding", 2, 3)),
    # the seats a play table brings: never placed on their own
    _piece("folding_chair", ((0.46, 0.5, 0.85),), "seat", variants=2),
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
_SEAT_PIECES = {"stool": "bar_stool", "club": "club_chair",
                "folding": "folding_chair"}

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


#: THE TRADING CARD SHOP, read on the same terms as the club above and only
#: inside a building whose id says `card_shop`: `sales_floor` and
#: `play_area` name a shop floor and nothing at all anywhere else, and this
#: kind must not claim either in a supermarket. The SELLING rooms only --
#: the stockroom keeps `storage` (which is what the reference's back room
#: is) and an apartment above keeps `apartment`, exactly as the club's cash
#: office keeps `vault`.
#:
#: `play` and `tournament` are in the set so the play area is a card-shop
#: room; which ANCHOR it gets is `_card_shop_anchors`, not this.
_CARD_SHOP_TOKENS = frozenset(("sales", "showroom", "play", "tournament",
                               "card", "cards", "counter", "gaming"))
_CARD_SHOP_ID = "card_shop"
#: The tokens inside a card shop that name the PLAY AREA rather than the
#: selling floor: a room whose id carries one anchors on tables, not on the
#: showcase counter.
_CARD_PLAY_TOKENS = frozenset(("play", "tournament", "gaming"))


def _card_shop_building(building):
    return _CARD_SHOP_ID in str(building or "").lower()


def is_card_shop_room(room, building):
    """Is `room` a selling/playing room of a card shop building? The one
    rule, as `is_strip_club_room` is the club's."""
    if not _card_shop_building(building):
        return False
    tokens = set(str(room.get("id", "")).lower().replace("-", "_").split("_"))
    return bool(tokens & _CARD_SHOP_TOKENS) or {"main", "floor"} <= tokens


def is_card_play_room(room, building):
    """Is `room` the card shop's PLAY AREA?"""
    if not is_card_shop_room(room, building):
        return False
    tokens = set(str(room.get("id", "")).lower().replace("-", "_").split("_"))
    return bool(tokens & _CARD_PLAY_TOKENS)

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
    # THE TRADING CARD SHOP (Zoo 0.95.0, Pixelcoat 0.44.0). Anchors are
    # chosen by the room (`_card_shop_anchors`): the showcase counter on a
    # selling floor, a play table in the play area. The wall run is pack
    # walls, a row of pennants along the top and the odd shelf run --
    # "clutter everywhere, no two shelves the same" -- and the floor is
    # banquet tables with two or three folding chairs each.
    #
    # WHY `pack_wall` APPEARS TWICE AND WHY THE PENNANTS ARE A FIXTURE.
    # The run is SHUFFLED and then CUT to about half the room's target, so
    # an entry in it is a lottery ticket, not a promise: MEASURED on
    # `card_shop_a01`, the sales floor drew three of the six and the
    # pennants were not among them -- a room whose reference is "a row of
    # felt pennants along the top of the walls" came back with none, and
    # every spot the probe tried was CLEAR. A fixture is placed after the
    # room is furnished, one per `fixture_limit` (the piece's own `most`),
    # with `_FIXTURE_ROUNDS` draws each: the dartboard's machinery, for
    # the same reason it was built. The ceiling on both pieces is still
    # `most` (2), which is where the triangle budget is held -- and see the
    # note on `pennant_row` in `_PIECES`: a strip costs its budget however
    # long it is, so the cap is a count and not a length.
    #
    # DENSER THAN A HALL AND SPARSER THAN A CLUB: 20 m2 a piece against the
    # club's 24 and an office's 16. A shop floor is product on the walls
    # with floor left to walk it, and the play area is the one room here
    # whose furniture stands mid-floor.
    "card_shop": {"anchors": ("display_case",),
                  "wall": ("pack_wall", "shelf_run", "pack_wall", "vending"),
                  # THE FLOOR RUN IS ISLAND GONDOLAS, and it is per-room:
                  # `_card_shop_floor` gives it to a SELLING room and gives
                  # the play area nothing, because the play area's middle is
                  # already its tables.
                  #
                  # WHAT SAT HERE BEFORE AND WHY IT IS NOT BACK.
                  # `folding_table` was the floor run until 0.139.0 emptied
                  # it, and that cap is the one of the three that was also
                  # the truer answer: the reference's tables are in the
                  # tournament area, not scattered across the shop floor.
                  # Islands are what the reference actually puts in the open
                  # floor, so the slot comes back with the right piece in it
                  # rather than the old one.
                  "floor": ("pack_wall_island",),
                  "clusters": ((("cartons",), 2, 3),),
                  "per_area": 20.0, "all_anchors": True,
                  # placed after the room is furnished (`place_fixtures`)
                  "fixtures": ("pennant_row",)},
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


#: A card-shop selling floor this big gets a SECOND showcase counter, the
#: reference's L or U of cases. The club's second-bar threshold is 300 m2
#: and a shop is a smaller room than a club floor: derived instead from
#: what a second counter NEEDS, which is a second wall run long enough to
#: hold it clear of the first -- the widest counter in the palette (3.6 m)
#: plus `_seed_clear`'s own 2.2 m spread at each end, squared: 8.0 x 8.0.
_CARD_SECOND_COUNTER_AREA = 64.0
#: Most play tables in one room. Zoo's own measured card-shop room is three
#: tables and eight chairs (0.95.0), and the triangle arithmetic in this
#: file's `_PIECES` note is written against that mix.
_CARD_PLAY_TABLES_MAX = 3


def card_play_table_floor():
    """The floor one play table and the two players at it need, in square
    metres: the widest table in the palette by its depth plus, on each
    side, a folding chair's depth and the body standing behind it.

    2.4 x (0.76 + 2 x (0.50 + 2 x 0.35)) = 7.58 m2 at today's pieces and
    `agent_contract.json`'s 0.35 m body. Derived rather than chosen,
    because a pinned number is wrong the moment the chair or the body
    moves -- the `WP_RADIUS` lesson, one room along.
    """
    tw, td = _PIECES["folding_table"]["sizes"][1][0:2]
    _cw, cd, _ch = _PIECES["folding_chair"]["sizes"][0]
    return round(tw * (td + 2.0 * (cd + 2.0 * _body_radius())), 4)


def _card_shop_anchors(room, building):
    """The card shop's anchors for one room, all of them placed.

    The PLAY AREA anchors on play tables -- one per
    `card_play_table_floor`, to `_CARD_PLAY_TABLES_MAX`; a selling floor
    anchors on the showcase counter, and a second one past
    `_CARD_SECOND_COUNTER_AREA`. Keyed on the room's ID and not its shape,
    because unlike the club's stages -- where the question really is "does
    a bar stage fit in the middle of this" -- which room people play in is
    something the author said, and `_room_kind` already reads ids.

    The count is a CEILING, not a promise: `_seed_clear`'s 2.2 m spread is
    what actually stops the third table, and a room that cannot stand it
    comes back with two. The reference's "small tournament area has
    several tables in rows" is three.
    """
    x0, y0, x1, y1 = room["bounds"]
    area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    if is_card_play_room(room, building):
        n = max(1, min(_CARD_PLAY_TABLES_MAX,
                       int(area // card_play_table_floor())))
        return ("folding_table",) * n
    out = ["display_case"]
    if area >= _CARD_SECOND_COUNTER_AREA:
        out.append("display_case")
    return tuple(out)


def _card_shop_floor(room, building):
    """The card shop's FLOOR run for one room, as `_card_shop_anchors` is
    its anchors.

    A SELLING room gets island gondolas standing in the open floor; the
    PLAY AREA gets nothing, because its middle is already its tables --
    `_card_shop_anchors` puts up to `_CARD_PLAY_TABLES_MAX` of them there
    and an island between two of them is a wall across a tournament.
    Per-room for the same reason the anchors are: the two rooms share one
    `_RECIPES` entry and differ by what the author called them.
    """
    if is_card_play_room(room, building):
        return ()
    return _RECIPES["card_shop"]["floor"]

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
    # THE CARD SHOP (Pixelcoat 0.44.0). Two of these change the BUILD and
    # two of them do not, and the difference is the point:
    #
    #   * `display_case` and `pack_wall` ask for kinds that are NOT their
    #     species' default (`laminate` and `metal_painted`), so Zoo tags
    #     the stem -- `_mwood_panel`, `_mslatwall` -- and builds a different
    #     module. That is the walker's reference: a dark wood-veneer case
    #     and white slatwall behind the blisters.
    #   * `pennant_row` and the two folding pieces ask for their species'
    #     OWN kind (`cloth`, `plastic`), for the reason the dartboard row
    #     above gives: the stem then carries no `_m` and the theme's own
    #     pack resolves it. Writing nothing here would have made them
    #     `wood`, which is a kind the theme HAS -- so the pennants would
    #     have come out as timber and nothing would have said so.
    #
    # Placed last because no keyword here is claimed by any row above:
    # checked key by key against every tuple in this table (`case`,
    # `pack_wall`, `pennant`, `folding_table`, `folding_chair` appear in
    # none of them), and `_prop_material` is called with the PIECE KEY, not
    # a volume name, so there is no tag or sequence number to collide.
    (("display_case",), "wood_panel"),
    (("pack_wall",), "slatwall"),
    (("pennant",), "cloth"),
    (("folding_table", "folding_chair"), "plastic"),
)
_PROP_MATERIAL_DEFAULT = "wood"
_PROP_ACOUSTIC = {"wood": ("Wood", 0.35, 0.3), "metal": ("Metal", 0.2, 0.15),
                  "leather": ("Curtain", 0.6, 0.5),
                  "metal_bare": ("Metal", 0.2, 0.15),
                  "metal_painted": ("Metal", 0.25, 0.2),
                  "wood_stained": ("Wood", 0.35, 0.3),
                  # printed hardboard and melamine-faced board are both a
                  # thin sheet on a frame: Wood, and stiffer than the bare
                  # timber above (a lacquered face reflects more)
                  "wood_panel": ("Wood", 0.3, 0.26),
                  "slatwall": ("Wood", 0.28, 0.24),
                  # felt, on the same terms as leather's Curtain
                  "cloth": ("Curtain", 0.7, 0.6),
                  # a moulded seat pan and a folding table top: hard, thin,
                  # and not metal. The enum has no Plastic, so Wood is the
                  # nearest of the eight and is said out loud rather than
                  # implied.
                  "plastic": ("Wood", 0.25, 0.2)}

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
    """The furnishing KIND of a room: a strip club's club rooms and a card
    shop's selling rooms first (`is_strip_club_room` / `is_card_shop_room`,
    which need the building's id), then its id's whole tokens, then below
    grade a basement, then its role, then ``fallback``.

    The two building rules cannot both fire -- one asks for `strip_club` in
    the building's id and the other for `card_shop` -- so their order here
    is arbitrary and is not a precedence."""
    if is_strip_club_room(room, building):
        return "strip_club"
    if is_card_shop_room(room, building):
        return "card_shop"
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


def _glazed_walls(spec, story):
    """The compass letters of this storey's exterior walls whose MATERIAL
    is a glazing kind (`material_kind`: `glass`, `glass_facade`). Read from
    the spec's own materials, so a shop front declared `storefront_glass`
    and a club front declared `club_glass` both answer, and a brick wall
    with a window in it does not -- a window is an opening, and
    `_clear_of_openings` is what keeps a piece off one of those."""
    import material_kind
    out = set()
    for w in spec.get("ext_walls") or []:
        if int(w.get("story", 0) or 0) != int(story or 0):
            continue
        kind = material_kind.kind_for(w.get("material")
                                      or spec.get("default_material"))
        if kind in ("glass", "glass_facade"):
            out.add(w.get("wall"))
    return out


def _wall_slots(spec, room, w, d, rng, with_front=False,
                over_openings=False, off_glass=False, back_off=0.0):
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
    glazed = _glazed_walls(spec, room.get("story", 0)) if off_glass else set()
    out = []
    long_side, short_side = max(w, d), min(w, d)
    # A PIECE'S BACK STANDS OFF THE WALL'S FACE, not its centreline. A room's
    # bound lies on the wall's centreline, and this was a flat 0.12 m -- half
    # a 0.24 m wall -- while every wall is built at `wall_thick` (0.3), so
    # every wall-slotted piece stood 0.03 m inside its wall. Measured by Zoo
    # on cold run 9052's lobby: waiting-chair backs coplanar with the wall's
    # inner face, 0.00 mm apart, 3.09 m2 of flicker ("z fighting on the
    # [chairs] on the steel", the walker).
    back = (float(spec.get("wall_thick") or 0.3) / 2.0 + _WALL_PIECE_AIR
            + float(back_off or 0.0))

    def _wall_of(value, half, lo_name, hi_name):
        """The exterior wall a room edge lies on, or None when interior."""
        if not half or abs(abs(value) - half) >= _FURNISH_EXT_KEEPOUT:
            return None
        return lo_name if value < 0 else hi_name

    # N and S walls: the long axis runs in x
    for wy, inset in ((y0, +1), (y1, -1)):
        ext = _wall_of(wy, hy, "S", "N")
        if ext and (openings is None or ext in glazed):
            continue
        span = (x1 - x0) - long_side - 0.6
        if span <= 0:
            continue
        for _ in range(4):
            px = x0 + 0.3 + long_side / 2.0 + rng.random() * span
            if not over_openings and ext and not _clear_of_openings(
                    openings, ext, px, long_side / 2.0):
                continue
            # against the S wall (inset +1) the front must face N; against
            # the N wall, S. Long axis along x, so no long-axis turn is added.
            out.append((px, wy + inset * (short_side / 2.0 + back),
                        long_side, short_side, 180.0 if inset > 0 else 0.0,
                        0.0 if inset > 0 else 180.0))
    # E and W walls: the long axis runs in y
    for wx, inset in ((x0, +1), (x1, -1)):
        ext = _wall_of(wx, hx, "W", "E")
        if ext and (openings is None or ext in glazed):
            continue
        span = (y1 - y0) - long_side - 0.6
        if span <= 0:
            continue
        for _ in range(4):
            py = y0 + 0.3 + long_side / 2.0 + rng.random() * span
            if not over_openings and ext and not _clear_of_openings(
                    openings, ext, py, long_side / 2.0):
                continue
            # against the W wall the front must face E; against the E wall,
            # W. `long_axis_first` already turns this piece 90, so the front
            # sits at 90 + rot_z + 180: 180 here gives E, 0 gives W.
            out.append((wx + inset * (short_side / 2.0 + back), py,
                        short_side, long_side, 180.0 if inset > 0 else 0.0,
                        90.0 if inset > 0 else 270.0))
    rng.shuffle(out)
    return out if with_front else [o[:5] for o in out]


def island_aisle_width():
    """The clear aisle round a piece standing in the OPEN FLOOR.

    `staff_aisle_width()`, and it is a reuse rather than a new number. That
    function's derivation is not about bars and not about staff: an aisle is
    a corridor a body WALKS THE LENGTH OF, so at least
    `clearances.min_corridor_width_m` (1.10), and it is ENTERED AT ITS END
    through the gap between two units, which is a doorway, so at least
    `clearances.min_door_width_m` (1.25). A shop aisle between two island
    gondolas is exactly that shape, so it is exactly that number -- 1.25 --
    and it satisfies the corridor minimum by being the greater of the two.

    Named separately from `staff_aisle_width` only because a reader at a
    gondola is not asking about a counter; it is an alias, not a second
    body, for the reason the club's spelling is.
    """
    return staff_aisle_width()


def island_depth(d, twin):
    """The depth of a whole island of units `d` deep: one unit, or two back
    to back with `_WALL_PIECE_AIR` between the backs.

    ONE FUNCTION BECAUSE TWO CALLERS NEED IT AND MUST NOT DISAGREE.
    `_island_slots` measures the aisle against this footprint and `_island`
    places the halves inside it; the pair's offset is derived from this
    number rather than spelled a second time, which is the defect this file
    keeps finding.

    THE AIR IS NOT AN EPSILON, IT IS THE MEASURED ONE. Two backs meeting on
    exactly one plane are the shape Zoo measured on cold run 9052's lobby --
    waiting-chair backs coplanar with a wall's inner face, 0.00 mm apart,
    3.09 m2 of flicker, "z fighting on the [chairs] on the steel". Opposite
    normals did not save it there and would not here: a gondola's back panel
    is a slatwall sheet and so is its partner's. `_WALL_PIECE_AIR` is the
    number that already answers this question one surface along.
    """
    # PARENTHESISED ON PURPOSE. A conditional expression binds looser than
    # the arithmetic beside it, so this reads correctly either way -- and
    # this repo has already paid for one operator-precedence assumption
    # (`%` against `+` in a GDScript format string, CLAUDE.md). Cost: two
    # characters.
    return (float(d) * 2.0 + _WALL_PIECE_AIR) if twin else float(d)


def _island_slots(spec, room, w, d, rng, twin=False):
    """Candidate ``(x, y, sx, sy, front)`` for a piece standing in the OPEN
    FLOOR, its long axis along the room's LONG axis and an aisle clear of
    the room's bounds on every side.

    ``(sx, sy)`` is the WHOLE island's footprint: with `twin` that is two
    units deep, because an island gondola is two backs meeting and the
    caller writes both halves (`_host`). ``front`` is the bearing the FIRST
    half faces; the second faces its opposite.

    THE LONG AXIS RUNS WITH THE ROOM, which is what makes an aisle rather
    than a barricade: a 2.4 m island across an 11 m room leaves two 4 m
    gaps at its ends, and the same island across the 20 m length leaves
    aisles either side that run the room. So a room wider in x lays its
    islands along x and they face N and S.

    THE AISLE IS NOT `_seed_clear`'s SPACING. That function keeps a piece
    0.9 m from another volume's edge, which is below
    `clearances.min_corridor_width_m` (1.10) -- fine for a chair beside a
    desk and not for a run a body walks down. `_island_aisle_clear` is the
    one that answers the contract, and the caller asks both.
    """
    x0, y0, x1, y1 = room["bounds"]
    aisle = island_aisle_width()
    depth = island_depth(d, twin)
    along_x = (x1 - x0) >= (y1 - y0)
    sx, sy = (w, depth) if along_x else (depth, w)
    fronts = (0.0, 180.0) if along_x else (90.0, 270.0)
    # the island stands an AISLE off every bound, so the strip between it
    # and the wall is walkable rather than a slot
    lo_x, hi_x = x0 + aisle + sx / 2.0, x1 - aisle - sx / 2.0
    lo_y, hi_y = y0 + aisle + sy / 2.0, y1 - aisle - sy / 2.0
    if lo_x > hi_x or lo_y > hi_y:
        return []
    # a grid across the free band, at the aisle's own pitch so two islands
    # drawn from it can stand side by side with a walkable gap
    nx = max(1, int((hi_x - lo_x) / (sx + aisle)) + 1)
    ny = max(1, int((hi_y - lo_y) / (sy + aisle)) + 1)
    out = []
    for i in range(nx):
        for j in range(ny):
            px = lo_x + (hi_x - lo_x) * (i / max(1, nx - 1) if nx > 1 else 0.5)
            py = lo_y + (hi_y - lo_y) * (j / max(1, ny - 1) if ny > 1 else 0.5)
            out.append((px, py, sx, sy, rng.choice(fronts)))
    rng.shuffle(out)
    # DOWN THE MIDDLE, AND THE SHUFFLE DECIDES WHERE ALONG IT. A shop's
    # islands run down the centre band of the floor with the wall runs
    # either side; the free positions, shuffled flat, are mostly at the
    # edges of the band, and the first build put one of two islands hard
    # against the counter wall -- product where product already was, and
    # the middle of the frame still empty. Sorting by distance from the
    # room's centre line on the SHORT axis only fixes which band they stand
    # in; their position ALONG the room stays the shuffle's, so two islands
    # do not stack.
    rcx, rcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    mid = (lambda s: abs(s[1] - rcy)) if along_x else (lambda s: abs(s[0] - rcx))
    out.sort(key=mid)
    return out


def _island_aisle_clear(spec, room, px, py, sx, sy, aisle):
    """Is every solid on this storey at least `aisle` from the island's
    footprint, edge to edge?

    The contract's answer to "can a body walk round this", asked of a
    rectangle rather than a radius -- a margin allowed per axis IS a box
    here, deliberately, because an aisle is a box: the question is not "how
    far is the nearest corner" but "is there a walkable strip along this
    face". A hung piece over a body's head is not in the way, the rule
    `_seed_clear` and `dart_lane_blockers` both use.
    """
    story = room.get("story", 0)
    sh = _story_height(spec)
    floor = story * sh
    x0, y0 = px - sx / 2.0 - aisle, py - sy / 2.0 - aisle
    x1, y1 = px + sx / 2.0 + aisle, py + sy / 2.0 + aisle
    for v in spec.get("volumes", []):
        vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
        if not _on_storey(vz, vh, floor, sh):
            continue
        if v.get("collision") == "none" and vz - vh / 2.0 - floor >= _HUNG_MIN:
            continue
        r = _rect_of(v)
        if x0 < r[2] and r[0] < x1 and y0 < r[3] and r[1] < y1:
            return False
    return True


def _island(key, make, spec, px, py, w, d, h, front, twin=False):
    """Write an island's units and return how many were written.

    ONE UNIT A FACE. A gondola has one face and a blank back, so an island
    is two of them meeting on their backs -- each its own volume, each its
    own module, each facing its own aisle. `px, py` is the PAIR's centre and
    each half sits `d / 2` off it along its own bearing, so the two backs
    are coincident planes rather than overlapping solids and the pair's
    footprint is exactly the `sx, sy` the clearance was measured with.

    THE BEARING DECIDES THE SLOT'S DIMS, not a guess: a unit facing N or S
    lies long in x, one facing E or W lies long in y, and `_front_turn`
    asks the emitter's own question about which way that gets recorded
    (`prop_species.long_axis_first`). Getting this backwards is the defect
    `test_a_table_brings_its_chairs` caught one pass along, so the front is
    computed from the bearing here and nowhere else.
    """
    faces = [front] + ([(float(front) + 180.0) % 360.0] if twin else [])
    # DERIVED FROM THE FOOTPRINT THE AISLE WAS MEASURED AGAINST, not spelled
    # again: the unit sits half of whatever is left over its own depth,
    # along the way it faces. With no twin it IS the island and does not
    # move. Spelling `d / 2` here instead would put the halves 1 cm inside
    # the rectangle `_island_aisle_clear` cleared, which is the direction
    # that hides rather than the direction that fails.
    off = (island_depth(d, twin) - float(d)) / 2.0
    n = 0
    for face in faces:
        ux, uy = round(math.sin(math.radians(face)), 6), \
            round(math.cos(math.radians(face)), 6)
        sx, sy = (w, d) if face in (0.0, 180.0) else (d, w)
        vol = make(key, px + ux * off, py + uy * off, sx, sy, h,
                   _front_turn(key, sx, sy, face))
        spec.setdefault("volumes", []).append(vol)
        n += 1
    return n


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


def _make_volume(spec, key, name, px, py, sx, sy, h, rot, story, sh, building,
                 lift=None):
    """A placed piece's volume: position, size, collision, material and
    Zoo's dressing fields. `furnish` and `place_fixtures` both build here.

    `lift` OVERRIDES the piece's own hang height, for the one caller that
    knows something the piece cannot: `card_shop_counters` hangs its CRT
    clear of the top of the pack wall it stands behind, and how tall that
    pack wall is depends on the storey. Left None, the piece decides
    (`_piece_lift`), which is every other placement.
    """
    import zlib
    p = _PIECES[key]
    if lift is None:
        lift = _piece_lift(spec, p, h)
    vol = {
        "name": name,
        "x": round(px, 2), "y": round(py, 2),
        "z": round(story * sh + (h / 2.0 if lift is None else lift), 3),
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
    mod = variant_count(p)
    if mod:
        key_text = (str(building or "") if mod > 4 else name)
        n = (zlib.crc32(key_text.encode("utf-8")) & 0xFFFFFFFF) % mod
        if n:
            vol["variant"] = n
    return vol


def variant_count(piece):
    """How many variants this pass will write for a piece: 0 for one with
    none, the piece's own count when it names one, else 4.

    PUBLIC, AND THE REASON IS A TEST THAT WAS ASKING THE WRONG QUESTION.
    `test_zoo_honours_every_dressing_furnish_writes` checked variants
    `range(4 if p["variants"] else 1)` -- a 4 hardcoded beside the 4 here.
    That is right for the eleven pieces whose count is 4 and wrong at both
    ends: `neon_sign` writes 24 and the test only ever saw 0..3, and the
    card shop's two folding pieces write 2, so the test asked Zoo to honour
    a variant this pass cannot produce and refused a correct piece. One
    function, asked by the writer and by the checker.
    """
    if not piece["variants"]:
        return 0
    n = int(piece["variants"])
    return n if n > 1 else 4


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
              for spot in _wall_slots(
                  spec, room, size[0], size[1], rng, with_front=True,
                  over_openings=_over_openings(spec, story, p, size[2]),
                  off_glass=p["off_glass"], back_off=piece_back_off(p))]
    for (w, d, h), (qx, qy, sx, sy, _rot, front) in rounds:
        if h is None:
            h = min(clear_h, _TO_CEILING_MAX)
        if h > clear_h:
            continue
        half = max(w, d) / 2.0
        lift = _piece_lift(spec, p, h)
        hung = lift is not None
        above = (lift - h / 2.0) if hung else None
        if _over_rects(inner, qx, qy, half, half):
            continue
        if not _seed_clear(spec, room, qx, qy, [], half=half, above=above,
                           over_openings=hangs_over_openings(spec, story,
                                                             above)):
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
_STAFF_MARKER_IN = 0.8
#: A counter end with less than the aisle's own width plus the counter's
#: depth between it and the room's side wall makes the bar an L: there is
#: no walking round that end, so the return leg closes it and the other
#: end is the flap.


def staff_aisle_width():
    """The clear aisle on the STAFF side of a counter: the greater of the
    corridor and the door minimums from `agent_contract.json`. One number,
    asked once, by everything that has one.

    The derivation is the section note above, and it is not about bars. An
    aisle behind a counter is two things at once and the contract answers
    both: a body WALKS ITS LENGTH, so it is at least
    `clearances.min_corridor_width_m` (1.10 -- 2 x the bake radius plus a
    0.30 body margin; narrower bakes as an island, as twin_a01's 0.9 m
    flights did), and it is ENTERED AT ITS END through the gap between the
    counter's end and the backing unit's, which is a doorway and so at
    least `clearances.min_door_width_m` (1.25). One aisle cannot be two
    widths, so it is the greater: 1.25 m, and the mouth is the aisle's own
    cross-section.

    THREE COUNTERS NOW SHARE IT and none of them chose a number: the club's
    bartender side (0.137.0), the card shop's showcase counter (0.139.0),
    and the bank teller line's staff room, which asks the same contract for
    its door width and adds a leaf margin because its ends are real doors
    (`_STAFF_DOOR_WIDTH`, `_LEAF_MARGIN`). Renamed from `bar_aisle_width`
    when the second caller arrived; the old name is kept below because a
    name that says `bar` is wrong at a card counter, and a name that says
    `staff` is right at both.
    """
    import agent_contract
    return round(max(agent_contract.min_corridor_width(),
                     agent_contract.min_door_width()), 4)


#: The club's spelling of `staff_aisle_width`, kept so nothing outside this
#: module has to change. Not deprecated -- a reader at the bar is asking
#: about the bar -- and it is an alias rather than a second body, because
#: two spellings of one number is the defect this whole file keeps finding.
bar_aisle_width = staff_aisle_width


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


def _staff_side_plan(spec, room, v, seq, back_depth, aisle, seat_stem=None):
    """The geometry of a staff side behind one wall counter, or a refusal.

    ``(plan, why)`` -- exactly one of the two is None. `plan` carries the
    coordinate frame, the rectangles and the verdicts every caller of this
    shape needs; `why` is a sentence naming the measurement that refused it.

    EXTRACTED FROM `back_bar_club_counters` (0.137.0) WHEN THE SECOND
    CALLER ARRIVED, and deliberately not copied: the card shop's showcase
    counter is the same question -- can a body work behind this thing and
    get in at one end -- with a different unit behind it. Everything that
    differs between the two is an argument here (`back_depth`, `aisle`,
    `seat_stem`); everything that is the contract's answer is shared. The
    club's numbers are unchanged, and `test_club_rooms` /
    `migrate_club_rooms.py --check` are what say so.

    THE FRAME, restated because it has already cost one draft: `t` measures
    from the INNER FACE of the wall behind the counter, along the counter's
    front bearing, into the room. `along` is the other axis. A first draft
    did this in x and y with a sign per branch and had two spellings of the
    aisle in it before the line that used it.
    """
    sh = _story_height(spec)
    rtag = _room_tag(room)
    front = _front_of(v)
    d = _axis_of(front)
    if d is None:
        return None, ("the counter is set at %g deg, not square to a wall"
                      % front)
    fx, fy = d
    story = room.get("story", 0)
    x0, y0, x1, y1 = room["bounds"]
    wt = float(spec.get("wall_thick") or 0.3) / 2.0
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

    need = back_depth + aisle
    shift = round(need - back_t, 4)
    if shift < -1e-6:
        return None, ("the counter already stands %.2f m off its wall"
                      % back_t)
    lane = extent - (need + thick)
    if lane < _CUSTOMER_LANE:
        return None, ("moving the counter %.2f m leaves %.2f m of customer "
                      "floor in front of it" % (shift, lane))
    mine = {v["name"]}
    if seat_stem:
        mine |= {sv["name"] for n, s, sv in _room_names(spec, rtag)
                 if n == seat_stem and s == seq}
    u0, u1 = along - run / 2.0, along + run / 2.0
    back_rect = _rect(0.0, back_depth, u0, u1)
    aisle_rect = _rect(back_depth, need, u0, u1)
    counter_rect = _rect(need, need + thick, u0, u1)
    blockers = (_rect_clear(spec, room, back_rect, mine)
                + _rect_clear(spec, room, aisle_rect, mine)
                + _rect_clear(spec, room, counter_rect, mine))
    if blockers:
        return None, ("the staff side is not clear: "
                      + ", ".join(sorted(set(blockers))[:3]))
    # THE MOUTHS, one at each end of the aisle: the aisle's own
    # cross-section carried a door's width past the counter's end. The
    # `reach` is how much floor there is between that end and the room's
    # side wall, which is what decides whether a body can get in at all.
    mouths = {}
    for side in ("a", "b"):
        end, s = (u0, -1.0) if side == "a" else (u1, 1.0)
        m = _rect(back_depth, need, end, end + s * aisle)
        reach = abs((a_lo if side == "a" else a_hi) - end)
        mouths[side] = (m, reach, _rect_clear(spec, room, m, mine))
    open_ends = [s for s in ("a", "b")
                 if not mouths[s][2] and mouths[s][1] >= aisle - 1e-6]
    if not open_ends:
        return None, ("neither end of the aisle opens %.2f m clear "
                      "(a: %.2f m %s; b: %.2f m %s)"
                      % (aisle, mouths["a"][1],
                         ",".join(sorted(set(mouths["a"][2]))) or "clear",
                         mouths["b"][1],
                         ",".join(sorted(set(mouths["b"][2]))) or "clear"))
    return {"front": front, "fx": fx, "fy": fy, "dirn": dirn, "wall": wall,
            "story": story, "floor": story * sh, "run": run, "thick": thick,
            "along": along, "u0": u0, "u1": u1, "need": need, "shift": shift,
            "rect": _rect, "mine": mine, "mouths": mouths,
            "open_ends": open_ends, "back_rect": back_rect,
            "rtag": rtag}, None


def _shift_counter(plan, v):
    """Move a counter off its wall by the plan's `shift`, on the plan's own
    axis. Returns the volume."""
    if plan["fy"]:
        v["y"] = round(float(v["y"]) + plan["fy"] * plan["shift"], 2)
    else:
        v["x"] = round(float(v["x"]) + plan["fx"] * plan["shift"], 2)
    return v


#: The `patrol_point` roles the staff-side passes write, and therefore the
#: id prefixes `migrate_furnish_recipes` must strip before a refurnish.
#: A TUPLE AND NOT A REGEX SPELLED IN THE MIGRATION, because that regex was
#: `^bartender_(r[0-9a-f]{8})_\\d+$` -- a list of one that fell behind the
#: moment a second pass wrote a second role. MEASURED on `card_shop_a01`
#: before this existed: a strip-and-refurnish kept both `shopkeeper`
#: markers, the pass wrote them again off the stripped counters, and the
#: spec came back with four patrol points for two aisles. The club never
#: showed it because no club spec goes through this migration.
STAFF_MARKER_ROLES = ("bartender", "shopkeeper", "playfloor")


def _staff_marker(spec, room, plan, seq, role, aisle, back_depth):
    """A `patrol_point` in the aisle, a step in from its open end, so the
    nav gate ANSWERS whether the staff side is a place a body can be rather
    than anybody assuming it.

    IDEMPOTENT ON ITS OWN, and not only because the migration strips these:
    a marker whose id is already in the spec is not written again. The
    pass's other idempotence mark is the backing volume, so a caller that
    removed the volume and kept the marker -- which is exactly what a
    migration with a stale regex does -- would otherwise double it.
    """
    mid = "%s_%s_%d" % (role, plan["rtag"], seq)
    if any(m.get("id") == mid and m.get("type") == "patrol_point"
           for m in spec.get("markers") or []):
        return
    end, s = ((plan["u0"], 1.0) if plan["open_ends"][0] == "a"
              else (plan["u1"], -1.0))
    mu = end + s * _STAFF_MARKER_IN
    mt = (back_depth + plan["need"]) / 2.0
    px, py = ((mu, plan["wall"] + plan["dirn"] * mt) if plan["fy"]
              else (plan["wall"] + plan["dirn"] * mt, mu))
    spec.setdefault("markers", []).append({
        "type": "patrol_point", "id": mid,
        "x": round(px, 3), "y": round(py, 3), "z": round(plan["floor"], 3),
        "rot_z": round(plan["front"], 3), "room": room["id"],
        "meta": {"role": role, "aisle_m": round(aisle, 3)}})


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
    aisle = staff_aisle_width()
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
        plan, why = _staff_side_plan(spec, room, v, seq, BACK_BAR_DEPTH,
                                     aisle, seat_stem="bar_stool")
        if plan is None:
            entry["why"] = why
            continue

        # --- from here the bar is built -----------------------------------
        front, story = plan["front"], plan["story"]
        run, thick = plan["run"], plan["thick"]
        u0, u1, need = plan["u0"], plan["u1"], plan["need"]
        mouths, open_ends = plan["mouths"], plan["open_ends"]
        mine, _rect = plan["mine"], plan["rect"]
        entry["aisle_m"] = round(aisle, 3)
        entry["flap_m"] = round(aisle, 3)
        entry["shift_m"] = round(plan["shift"], 3)
        _shift_counter(plan, v)
        for name, s, sv in _room_names(spec, rtag):
            if name == "bar_stool" and s == seq:
                _shift_counter(plan, sv)
        bw = max(BACK_BAR_W[0], min(BACK_BAR_W[1], run))
        bh = min(BACK_BAR_H, clear_h)
        bar_rect = plan["back_rect"]
        cx = (bar_rect[0] + bar_rect[2]) / 2.0
        cy = (bar_rect[1] + bar_rect[3]) / 2.0
        sx, sy = ((bw, BACK_BAR_DEPTH) if plan["fy"]
                  else (BACK_BAR_DEPTH, bw))
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
            lcx, lcy = ((leg_u, plan["wall"] + plan["dirn"] * leg_t)
                        if plan["fy"]
                        else (plan["wall"] + plan["dirn"] * leg_t, leg_u))
            lsx, lsy = (thick, aisle) if plan["fy"] else (aisle, thick)
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
        _staff_marker(spec, room, plan, seq, "bartender", aisle,
                      BACK_BAR_DEPTH)
        entry["built"] = True
    return report


# ---------------------------------------------------------------------------
# THE CARD SHOP'S COUNTER -- a pack wall behind every showcase (0.139.0)
# ---------------------------------------------------------------------------
#
# The walker's 1990s reference, `docs/SET_DRESSING_REFERENCES.md`: "Tall
# white wire/wood shelving to the ceiling, every shelf crowded with wax
# boxes and packs, faces out. A glass-top showcase counter in front with a
# chrome frame, stacks of white card storage boxes and toploaders on top, a
# small CRT on a shelf behind."
#
# That is the club's bar one shop along -- a customer side, a counter, a
# working aisle, a unit against the wall -- so it is the club's pass with
# different units, and `_staff_side_plan` is the half they share. THE AISLE
# IS NOT A NEW NUMBER: `staff_aisle_width` derives it from
# `agent_contract.json` for both, 1.25 m, and the reason is written there.
#
# WHAT THE SHOPKEEPER MARKER IS FOR, restated because it is the only thing
# in this pass that is not geometry: the nav gate walks to `patrol_point`
# markers, so the question "can a body get behind this counter" is ANSWERED
# by a gate rather than assumed by whoever wrote the arithmetic. A card
# shop's aisle is closed at one end by the return case and at the other by
# nothing, and if that ever stops being true the gate says so.

#: Zoo's `pack_wall` genome: the depth a gondola shelf is, the height this
#: pass builds one to, and the width range a module can be built at. Read
#: from `zoo/zoo_keeper/genome/species/pack_wall.json` (0.35-0.60,
#: 0.8-8.0), not from a brief.
PACK_WALL_DEPTH = 0.5
PACK_WALL_W = (0.8, 8.0)


def counter_pack_wall_height(spec):
    """How tall the gondola behind a showcase counter is built.

    A PINNED 2.2 WAS TWO SPELLINGS OF ONE NUMBER, which is the defect this
    file keeps finding. `PACK_WALL_H` sat here and `_PIECES["pack_wall"]`
    carried its own 2.2/2.4 sizes, so the wall run and this pass agreed by
    coincidence -- and when the run's heights went to the ceiling the two
    counter gondolas, which are the most visible pack walls in the shop,
    stayed at 2.2 and the room had one fixture at two heights. `_PIECES` is
    the one place that declares it now and this reads it.

    AND THE CRT KEEPS ITS SHELF, which is the second term and is why this
    is not just `to_ceiling_height`. The reference is "a small CRT on a
    shelf behind the counter"; this pass hangs it over the gondola, so the
    gondola may not take the whole clear height or there is nowhere for it
    to go -- MEASURED at the card shop's 3.4 m storey: clear height 3.10,
    product ceiling 2.70, and a 0.50 m CRT over `_CRT_OVER_PACK` of air
    needs its bottom at 2.60, so a 2.70 gondola evicts it and the pass
    reports `crt: false`. Taking the CRT's band off first gives 2.55 and
    keeps both. A taller storey gets the full height and the CRT, because
    both terms are derived and neither is pinned.
    """
    clear_h = _clear_height(spec)
    crt_h = _PIECES["wall_tv"]["sizes"][0][2]
    return _floor4(min(to_ceiling_height(spec, _PIECES["pack_wall"], clear_h),
                       clear_h - crt_h - _CRT_OVER_PACK))
#: Air between the top of the pack wall and the bottom of the CRT hung over
#: it, so the two are not coplanar -- `_CEILING_AIR`'s reason, one surface
#: down.
_CRT_OVER_PACK = _CEILING_AIR


def _card_shop_cases(spec, building):
    """``[(room, showcase volume, seq)]`` -- every showcase counter in a
    card shop, in a stable order."""
    out = []
    if not _card_shop_building(building):
        return out
    for room in spec.get("rooms", []) or []:
        if not is_card_shop_room(room, building):
            continue
        rtag = _room_tag(room)
        for stem, seq, v in sorted(_room_names(spec, rtag),
                                   key=lambda t: (t[0], t[1])):
            if stem == "display_case":
                out.append((room, v, seq))
    return out


def card_shop_counters(spec):
    """Stand a PACK WALL against the wall behind every showcase counter in
    a card shop, with the shopkeeper's aisle between, and prove the staff
    side is a place a body can be.

    Per counter, in one pass and in this order:

      * the counter moves into the room by the pack wall's depth plus the
        aisle (`staff_aisle_width`);
      * a `pack_wall` volume goes flush against the wall, as long as the
        counter (inside Zoo's genome range) and `counter_pack_wall_height`
        tall -- the product ceiling less the CRT's own band;
      * a CRT hangs on the wall clear above it, where the storey leaves
        room -- the reference's "small CRT on a shelf behind";
      * where the counter's end is against a perpendicular wall, a return
        case closes that end and the counter is an L;
      * a `patrol_point` marker stands in the aisle;
      * the whole thing is skipped, and the report says why, when the room
        cannot hold it.

    Idempotent (a counter that already has its `pack_wall_<tag>_<seq>` is
    left alone), deterministic, and reads nothing but the spec. Returns
    ``[report]``, one row per showcase counter.
    """
    building = club_building_id(spec)
    aisle = staff_aisle_width()
    sh = _story_height(spec)
    clear_h = _clear_height(spec)
    report = []
    for room, v, seq in _card_shop_cases(spec, building):
        rtag = _room_tag(room)
        entry = {"room": room["id"], "counter": v["name"], "built": False,
                 "why": "", "aisle_m": None, "flap_m": None,
                 "l_shaped": False, "crt": False}
        report.append(entry)
        if any(n == "pack_wall" and s == seq
               for n, s, _v in _room_names(spec, rtag)):
            entry["built"] = True
            entry["why"] = "already"
            continue
        plan, why = _staff_side_plan(spec, room, v, seq, PACK_WALL_DEPTH,
                                     aisle)
        if plan is None:
            entry["why"] = why
            continue

        # --- from here the counter is built -------------------------------
        front, story = plan["front"], plan["story"]
        run, thick = plan["run"], plan["thick"]
        u0, u1, need = plan["u0"], plan["u1"], plan["need"]
        mouths, open_ends = plan["mouths"], plan["open_ends"]
        mine = plan["mine"]
        entry["aisle_m"] = round(aisle, 3)
        entry["flap_m"] = round(aisle, 3)
        entry["shift_m"] = round(plan["shift"], 3)
        _shift_counter(plan, v)
        pw_rect = plan["back_rect"]
        pw_w = max(PACK_WALL_W[0], min(PACK_WALL_W[1], run))
        pw_h = min(counter_pack_wall_height(spec), clear_h)
        cx = (pw_rect[0] + pw_rect[2]) / 2.0
        cy = (pw_rect[1] + pw_rect[3]) / 2.0
        sx, sy = ((pw_w, PACK_WALL_DEPTH) if plan["fy"]
                  else (PACK_WALL_DEPTH, pw_w))
        wall_unit = _make_volume(spec, "pack_wall",
                                 "pack_wall_%s_%d" % (rtag, seq),
                                 cx, cy, sx, sy, pw_h,
                                 _front_turn("pack_wall", sx, sy, front),
                                 story, sh, building)
        spec.setdefault("volumes", []).append(wall_unit)
        # THE CRT, over the pack wall rather than on it: a bracket set at
        # the piece's own 2.1 m lift would stand INSIDE a 2.2 m pack wall,
        # which is why `_make_volume` takes a `lift`. Skipped, and said in
        # the report, where the storey has no room above the shelving --
        # a shop under a low ceiling has the CRT on the counter and this
        # pass does not model that.
        crt_w, crt_d, crt_h = _PIECES["wall_tv"]["sizes"][0]
        crt_lift = pw_h + _CRT_OVER_PACK + crt_h / 2.0
        # THE SAME QUANTITY, ASKED TWICE. `counter_pack_wall_height` derives
        # `pw_h` as `clear_h - crt_h - _CRT_OVER_PACK` precisely so this sum
        # comes back to `clear_h`, and the two spellings of it differ in the
        # last bits -- the `_wall_span` shape, where a piece is judged too
        # tall to hang AND too short to have been shortened. The tolerance is
        # the float error of one add, not a design margin; `_floor4` on the
        # other side is what keeps it that small.
        if crt_lift + crt_h / 2.0 <= clear_h + 1e-9:
            csx, csy = ((crt_w, crt_d) if plan["fy"] else (crt_d, crt_w))
            crt = _make_volume(spec, "wall_tv", "wall_tv_%s_%d" % (rtag, seq),
                               cx, cy, csx, csy, crt_h,
                               _front_turn("wall_tv", csx, csy, front),
                               story, sh, building, lift=crt_lift)
            spec["volumes"].append(crt)
            entry["crt"] = True
            entry["crt_lift_m"] = round(crt_lift, 3)
        # THE L, on the club's rule: an end with no floor to walk round it
        # is closed by a return case, and the other end is the way in.
        closed = [s for s in ("a", "b")
                  if s not in open_ends and mouths[s][1] <= aisle + thick]
        if closed:
            side = closed[0]
            end, s = (u0, -1.0) if side == "a" else (u1, 1.0)
            leg_u = end + s * thick / 2.0
            leg_t = (PACK_WALL_DEPTH + need) / 2.0
            lcx, lcy = ((leg_u, plan["wall"] + plan["dirn"] * leg_t)
                        if plan["fy"]
                        else (plan["wall"] + plan["dirn"] * leg_t, leg_u))
            lsx, lsy = (thick, aisle) if plan["fy"] else (aisle, thick)
            leg = _make_volume(spec, "display_case_end",
                               "display_case_end_%s_%d" % (rtag, seq),
                               lcx, lcy, lsx, lsy, float(v["size_z"]),
                               _front_turn("display_case_end", lsx, lsy,
                                           (front + (90.0 if s > 0 else 270.0)) % 360.0),
                               story, sh, building)
            if not _rect_clear(spec, room, _rect_of(leg),
                               mine | {wall_unit["name"]}):
                spec["volumes"].append(leg)
                entry["l_shaped"] = True
        _staff_marker(spec, room, plan, seq, "shopkeeper", aisle,
                      PACK_WALL_DEPTH)
        entry["built"] = True
    report += card_shop_play_markers(spec)
    return report


def card_shop_play_markers(spec):
    """A `patrol_point` in the FAR CORNER of every play area, so the nav
    gate answers whether a body can get past the tables.

    WHY THIS EXISTS AND WHY IT IS A MARKER. The play area is the one room
    in this building whose furniture stands mid-floor, which is the shape
    that strands a walker -- and the nav gate only judges the points it is
    given (`nav_gate.SCOPE_TYPES`: objective, extraction, loot,
    patrol_point, rescue). A play area with no marker in it is a room the
    gate says nothing about, which reads in the report exactly like a room
    it passed. The bartender marker was added to the club for the same
    reason a release earlier.

    The point is DERIVED, not chosen: the room's four inner corners, inset
    by a body and `_seed_clear`'s own edge, ranked by distance from the
    nearest way in, first one that a body fits in. A room where none of
    the four is clear gets no marker and the report says so, because a
    marker shoved into a table would fail the gate for the wrong reason.

    Idempotent and deterministic. Returns ``[report]``, one row per play
    room.
    """
    building = club_building_id(spec)
    out = []
    if not _card_shop_building(building):
        return out
    sh = _story_height(spec)
    r_body = _body_radius()
    for room in spec.get("rooms", []) or []:
        if not is_card_play_room(room, building):
            continue
        rtag = _room_tag(room)
        entry = {"room": room["id"], "counter": None, "built": False,
                 "why": "", "aisle_m": None, "flap_m": None,
                 "l_shaped": False, "play_point": True}
        out.append(entry)
        mid = "playfloor_%s_1" % rtag
        if any(m.get("id") == mid for m in spec.get("markers") or []):
            entry["built"] = True
            entry["why"] = "already"
            continue
        x0, y0, x1, y1 = room["bounds"]
        story = int(room.get("story", 0) or 0)
        inset = 1.0 + r_body
        ways = []
        for w in spec.get("ext_walls", []) or []:
            if int(w.get("story", 0) or 0) != story:
                continue
            run = (float(spec.get("footprint_x", 0.0))
                   if w.get("wall") in ("N", "S")
                   else float(spec.get("footprint_y", 0.0)))
            hx = float(spec.get("footprint_x", 0.0)) / 2.0
            hy = float(spec.get("footprint_y", 0.0)) / 2.0
            for op in w.get("openings") or []:
                u = float(op.get("pos", 0.0)) * run
                ways.append({"N": (u, hy), "S": (u, -hy),
                             "E": (hx, u), "W": (-hx, u)}[w["wall"]])
        for p in spec.get("partitions", []) or []:
            if int(p.get("story", 0) or 0) != story:
                continue
            span = abs(float(p["end"]) - float(p["start"]))
            for op in p.get("openings") or []:
                u = float(p["start"]) + (float(op.get("pos", 0.0)) + 0.5) * span
                ways.append((float(p["pos"]), u) if p["axis"] == "Y"
                            else (u, float(p["pos"])))
        # A GRID, NOT THE FOUR CORNERS. The corners were the first draft and
        # all four were refused on `card_shop_a01`: the play area is 7 x 11
        # and `_seed_clear` holds a piece 0.9 m plus a body off every
        # volume, so a room furnished to its target has furniture within
        # that of each corner. The grid is the room inset by a body and
        # `_seed_clear`'s own 1.0 m edge, stepped at a body's DIAMETER --
        # the coarsest step that cannot skip over a gap a body fits
        # through. No rng: the order is the sort, and the sort is distance
        # from the nearest way in.
        step = max(2.0 * r_body, 0.1)
        grid = []
        nx = max(1, int((x1 - x0 - 2 * inset) / step) + 1)
        ny = max(1, int((y1 - y0 - 2 * inset) / step) + 1)
        for i in range(nx):
            for j in range(ny):
                grid.append((round(x0 + inset + i * step, 4),
                             round(y0 + inset + j * step, 4)))
        if ways:
            grid.sort(key=lambda c: (-round(min(math.hypot(c[0] - w[0],
                                                           c[1] - w[1])
                                                for w in ways), 4),
                                     c[0], c[1]))
        for cx, cy in grid:
            if not _seed_clear(spec, room, cx, cy, [], half=r_body):
                continue
            spec.setdefault("markers", []).append({
                "type": "patrol_point", "id": mid,
                "x": round(cx, 3), "y": round(cy, 3),
                "z": round(story * sh, 3), "rot_z": 0.0,
                "room": room["id"],
                "meta": {"role": "playfloor"}})
            entry["built"] = True
            break
        if not entry["built"]:
            entry["why"] = ("no inner corner of the play area is clear of "
                            "its own furniture")
    return out


#: The surfaces a card shop room wears (Pixelcoat 0.44.0's three grammars,
#: through the `card_shop` theme). Declared in the palette the way a prop's
#: material is, with an acoustic.
#:
#: THE PLAY AREA'S CARPET IS `carpet` AND NOT `carpet_tournament`, and the
#: difference is the whole wiring. Zoo 0.95.0: "a pack directory is
#: `<kind>_<theme>`, so it is `carpet` under a `tournament` theme" -- the
#: `card_shop` theme maps kind `carpet` to `carpet_tournament` and kind
#: `tile` to `vct_floor_beige`. The club needed `carpet_club` to BE a kind
#: because nothing themed it; this one is themed, so inventing a
#: `carpet_tournament` kind would have given it a pack no other theme could
#: answer and left every other theme's card shop grey.
#:
#: THE PANELLING IS THE WHOLE PARTITION, NOT A WAINSCOT, and the reference
#: says "wood-panel lower walls". Deli Counter has no band on a wall: a
#: partition is one slot with one material on both faces (the club's note
#: above says the same thing about its wallpaper), so a shop that asks for
#: panelling gets it floor to ceiling. What the expensive version buys is
#: a 1.2 m dado with drywall over it, which needs a second slot per wall
#: run and a rail module; it is not built and it is not pretended.
_CARD_SHOP_FINISHES = {"carpet": ("Curtain", 0.8, 0.7),
                       "tile": ("Concrete", 0.2, 0.15),
                       "wood_panel": ("Wood", 0.3, 0.26)}


def dress_card_shop_rooms(spec):
    """The card shop's surfaces (`_CARD_SHOP_FINISHES`), in place,
    idempotent: the play area's floor is `carpet`, every other selling
    room's is `tile`, and a partition with a card-shop room on EITHER face
    is `wood_panel`. Returns the count of fields set. Nothing outside a
    `card_shop` building is touched.

    EITHER FACE, where the club's wallpaper asks for BOTH. A club's flock
    is on the walls between club rooms and its outside walls stay painted
    block; a shop's panelling is on the walls the customer sees, and the
    wall between the sales floor and the stockroom is one of them. Since a
    partition is one slot with one material on both faces, the stockroom
    gets panelling it would not have had -- which is the cheaper of the two
    wrong answers, and is said here rather than discovered in a frame.
    """
    name = club_building_id(spec)
    if not _card_shop_building(name):
        return 0
    shop = [r for r in spec.get("rooms") or [] if is_card_shop_room(r, name)]
    if not shop:
        return 0
    n = 0
    for r in shop:
        if r.get("floor_material") or r.get("material"):
            continue
        mat = "carpet" if is_card_play_room(r, name) else "tile"
        r["floor_material"] = _declare_material(spec, mat,
                                                _CARD_SHOP_FINISHES[mat])
        n += 1
    ids = {r["id"] for r in shop}
    for p in spec.get("partitions") or []:
        if p.get("material") == "wood_panel":
            continue
        lo, hi = sorted((float(p["start"]), float(p["end"])))
        story = int(p.get("story", 0) or 0)
        pos = float(p["pos"])
        touches = False
        for r in spec.get("rooms") or []:
            if r["id"] not in ids or int(r.get("story", 0) or 0) != story:
                continue
            x0, y0, x1, y1 = r["bounds"]
            a0, a1, b0, b1 = ((x0, x1, y0, y1) if p["axis"] == "X"
                              else (y0, y1, x0, x1))
            if min(a1, hi) - max(a0, lo) <= 0.5:
                continue
            if abs(b1 - pos) < 0.05 or abs(b0 - pos) < 0.05:
                touches = True
                break
        if touches:
            p["material"] = _declare_material(
                spec, "wood_panel", _CARD_SHOP_FINISHES["wood_panel"])
            n += 1
    return n


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
    dress_card_shop_rooms(spec)
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
        elif kind == "card_shop":
            recipe = dict(recipe, anchors=_card_shop_anchors(room, building),
                          floor=_card_shop_floor(room, building))
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
                # `folding` joins the two that sit ROUND their host: a play
                # table has no front, so `host["_front"]` is None there and
                # the `else` branch below is a TypeError, not a wrong angle.
                if how in ("table", "club", "folding") or ring:
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
            # A piece a LATER pass also places keeps that pass's share of
            # its own `most` (`reserved_by`): one per host already standing
            # in this room. Anchors go first, so the count is settled by the
            # time the wall run asks.
            limit = p["most"]
            if limit is not None and p["reserved_by"]:
                limit -= per_name[p["reserved_by"]]
            if limit is not None and per_name[key] >= limit:
                return False
            sizes = [s for s in _palette(spec, key)
                     if per_size[(key, s)] < _SAME_PIECE_MAX]
            rng.shuffle(sizes)
            for size in sizes:
                w, d, h = size
                if h is None:
                    h = to_ceiling_height(spec, p, clear_h)
                if h > clear_h:
                    continue
                half = max(w, d) / 2.0
                if p["where"] in ("seat", "pair"):
                    return False
                if p["where"] == "island":
                    spots = _island_slots(spec, room, w, d, rng,
                                          twin=p["twin"])
                elif p["where"] == "wall":
                    spots = [(qx, qy, sx, sy, front)
                             for qx, qy, sx, sy, _r, front
                             in _wall_slots(spec, room, w, d, rng,
                                            with_front=True,
                                            over_openings=_over_openings(
                                                spec, story, p, h),
                                            off_glass=p["off_glass"],
                                            back_off=piece_back_off(p))]
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
                lift = _piece_lift(spec, p, h)
                hung = lift is not None
                above = (lift - h / 2.0) if hung else None
                over = hangs_over_openings(spec, story, above)
                for qx, qy, sx, sy, front in spots:
                    # AN ISLAND'S HALF-EXTENT IS ITS OWN FOOTPRINT, not the
                    # piece's longest side: `sx`/`sy` already carry the
                    # twin's doubled depth, and clearing a 1.0 m deep island
                    # as if it were 0.5 would spend the aisle twice.
                    if p["where"] == "island":
                        half = max(sx, sy) / 2.0
                    if _over_rects(inner, qx, qy, half, half):
                        continue
                    # THE CONTRACT'S AISLE, and only an island is asked for
                    # it: `_seed_clear` below keeps 0.9 m from a volume's
                    # edge, which is under `min_corridor_width_m` and is the
                    # right answer for a chair beside a desk. A run a body
                    # walks down is a corridor and gets `island_aisle_width`.
                    if p["where"] == "island" and not _island_aisle_clear(
                            spec, room, qx, qy, sx, sy, island_aisle_width()):
                        continue
                    # a hung piece takes no share of the floor: it clears
                    # what reaches up to it and holds no spread against
                    # the pieces standing under it
                    if not _seed_clear(spec, room, qx, qy,
                                       [] if hung else placed, half=half,
                                       above=above, over_openings=over):
                        continue
                    if p["where"] == "island":
                        n = _island(key, _volume, spec, qx, qy, w, d, h,
                                    front, twin=p["twin"])
                        placed.append((qx, qy))
                        per_size[(key, size)] += 1
                        per_name[key] += 1
                        added += n
                        return True
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
    # ...and the card shop's, on the same terms and for the same reason:
    # this pass MOVES a showcase counter, so it runs before the fixtures
    # that measure against where the furniture actually stands. A building
    # is a club or a shop or neither, so at most one of these two does
    # anything.
    added += sum(1 for r in card_shop_counters(spec)
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
