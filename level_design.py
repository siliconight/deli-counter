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
  * ADDITIVE and IDEMPOTENT: only ever appends anchors, never moves or removes
    one, and re-running is a no-op. Geometry is never touched -- an enrichment
    pass can no more break a level than an art pass can.
  * Anchors only (markers). The game still owns what an anchor *means*.

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
)
# Names that look big/structural and must never be tagged as cover.
_COVER_NAME_SKIP = (
    "pad", "roof", "slab", "floor", "ceiling", "canopy", "wall_", "forecourt",
    "foundation", "platform_base", "ramp", "stair",
)

_COVER_MIN_Z = 0.6      # below this it's a kerb, not cover
_COVER_MAX_Z = 2.4      # above this it's a wall, not cover
_COVER_HIGH_Z = 1.4     # >= this stands as high cover, else low cover
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
        if v.get("size_z", 0) < 0.6 or min(v.get("size_x", 0), v.get("size_y", 0)) < 0.3:
            continue
        if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1 and                 abs(v.get("z", 0) - (room.get("story", 0) * sh + v.get("size_z", 0) / 2)) < sh:
            return True
    for m in spec.get("markers", []):
        if m.get("type") in ("cover_low", "cover_high") and                 x0 <= m.get("x", 1e9) <= x1 and y0 <= m.get("y", 1e9) <= y1:
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
            if math.hypot(ox - px, oy - py) < 1.5:
                return False
    for p in spec.get("partitions", []):
        if p.get("story", 0) != story:
            continue
        run = abs(p["end"] - p["start"])
        for op in p.get("openings", []):
            u = p["start"] + (op.get("pos", 0.0) + 0.5) * run
            ox, oy = (p["pos"], u) if p["axis"] == "Y" else (u, p["pos"])
            if math.hypot(ox - px, oy - py) < 1.5:
                return False
    for (qx, qy) in placed:
        if math.hypot(qx - px, qy - py) < 2.2:
            return False
    return True


def seed_cover(spec):
    """Create actual cover VOLUMES in combat-intent rooms that have none --
    the audit calls these kill boxes: big rooms with combat_range and not one
    solid to shelter behind. Deterministic (spec seed + room id), additive,
    idempotent (rooms that already have any waist-high solid are untouched),
    and respectful of the over-cover thesis (2-4 pieces, spread out, never
    near a door, an objective, a stair, or a ladder). cover_from_volumes then
    tags the new pieces as engagement points like any authored furniture.

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
        if area < _SEED_MIN_AREA or _room_has_cover(spec, room):
            continue
        rng = random.Random(f"{base_seed}:{room['id']}:seed_cover")
        arch = _seed_archetype(room)
        want = min(_SEED_MAX_PIECES, max(2, int(area // 45) + 1))
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
            })
            placed.append((px, py))
            added += 1
    return added


def enrich(spec):
    """Apply the full felt-space layer to a finished spec, in place.

    Idempotent and additive. Returns a small report dict so callers/tests can
    see what was added.
    """
    report = {
        "cover_seeded": seed_cover(spec),
        "cover_added": cover_from_volumes(spec),
        "landmarks_added": add_landmarks(spec),
    }
    return report
