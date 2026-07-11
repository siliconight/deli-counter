#!/usr/bin/env python3
"""
stair_place.py  --  archetype-driven stair placement proposals (no Blender)
===========================================================================
Phase 3 of docs/stairwell_placement_spec.md: the PLACEMENT side of what
stairwell.py reviews. Given a spec and a building archetype, generate weighted
candidate stair zones (spec s11.2 -- corners, corridor ends, core edges, wing
junctions, rear service bands, perimeter bays, party walls; NEVER random
points), reject the impossible ones with a stated reason, score the rest with
the spec's s11.4 weights, and select the best single stair or the best PAIR
(s11.5 -- pair quality, not two individual winners).

This is a PROPOSAL tool, not an authority. Deli Counter is spec-driven: the
author owns the stairs section. Default output is a JSON block + score table
to read and paste; --write injects it only into a spec with no stairs (or with
--replace, deliberately). Every proposed stair carries the role that opts it
into stairwell.py's egress contract, so the review loop closes: place with
this tool, gate with validate.

    python stair_place.py specs/office.json --archetype office_lowrise
    python stair_place.py specs/office.json --archetype office_lowrise --count 1
    python stair_place.py specs/new.json --archetype hotel_corridor --write

Offline limits, stated plainly: Deli Counter stairs always run along Y and
always stack, so candidates are axis-aligned rects of the profile's switchback
footprint; enclosure walls, doors, and swings remain authoring work after the
proposal lands. Determinism: any probabilistic extra (service / convenience
stair) rolls on spec.seed, so the same spec proposes the same stairs forever.
"""

import argparse
import json
import math
import random
import sys

import tactical
import stairwell

# ---------------------------------------------------------------------------
# Archetype profiles (placement spec s12; ten recommended initial profiles)
# ---------------------------------------------------------------------------
# stair_count_policy: "one" | "two" | "occupancy_and_floorplate" (two when the
# plate is big or tall enough; the compact single-stair carve-out of Rule 6).
# riser_target / clear_width feed the s10 geometry defaults into the proposal.

PROFILES = {
    "residential_house": dict(
        min_floors=1, max_floors=3, stair_count_policy="one",
        preferred_shape="straight",
        primary_zones=("core_edge", "party_wall", "perimeter_bay"),
        secondary_zones=("exterior_corner",),
        convenience_stair_probability=0.0, service_stair_probability=0.0,
        allow_open_primary_stair=True, prefer_direct_exterior_discharge=False,
        separation_factor=0.33, riser_target=0.19, clear_width=1.0),
    "urban_storefront_narrow": dict(
        min_floors=2, max_floors=4, stair_count_policy="one",
        preferred_shape="straight",
        primary_zones=("party_wall", "rear_service"),
        secondary_zones=("exterior_corner", "core_edge"),
        convenience_stair_probability=0.0, service_stair_probability=0.10,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.18, clear_width=1.1),
    "restaurant_two_story": dict(
        min_floors=2, max_floors=2, stair_count_policy="occupancy_and_floorplate",
        preferred_shape="switchback",
        primary_zones=("rear_service", "party_wall"),
        secondary_zones=("exterior_corner", "perimeter_bay"),
        convenience_stair_probability=0.10, service_stair_probability=0.35,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.17, clear_width=1.2),
    "office_lowrise": dict(
        min_floors=2, max_floors=4, stair_count_policy="two",
        preferred_shape="switchback",
        primary_zones=("core_edge", "corridor_end"),
        secondary_zones=("perimeter_bay", "exterior_corner"),
        convenience_stair_probability=0.15, service_stair_probability=0.15,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.17, clear_width=1.2),
    "office_midrise": dict(
        min_floors=3, max_floors=12, stair_count_policy="two",
        preferred_shape="switchback",
        primary_zones=("core_edge", "corridor_end"),
        secondary_zones=("perimeter_bay", "exterior_corner"),
        convenience_stair_probability=0.15, service_stair_probability=0.20,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.17, clear_width=1.2),
    "hotel_corridor": dict(
        min_floors=2, max_floors=10, stair_count_policy="two",
        preferred_shape="switchback",
        primary_zones=("corridor_end", "perimeter_bay"),
        secondary_zones=("core_edge", "exterior_corner"),
        convenience_stair_probability=0.10, service_stair_probability=0.25,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.17, clear_width=1.2),
    "apartment_corridor": dict(
        min_floors=2, max_floors=8, stair_count_policy="two",
        preferred_shape="switchback",
        primary_zones=("corridor_end", "perimeter_bay"),
        secondary_zones=("core_edge", "exterior_corner"),
        convenience_stair_probability=0.05, service_stair_probability=0.10,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.17, clear_width=1.2),
    "school_wings": dict(
        min_floors=1, max_floors=4, stair_count_policy="two",
        preferred_shape="switchback",
        primary_zones=("corridor_end", "wing_junction"),
        secondary_zones=("perimeter_bay", "exterior_corner"),
        convenience_stair_probability=0.10, service_stair_probability=0.15,
        allow_open_primary_stair=False, prefer_direct_exterior_discharge=True,
        separation_factor=0.33, riser_target=0.16, clear_width=1.4),
    "warehouse_mezzanine": dict(
        min_floors=1, max_floors=2, stair_count_policy="one",
        preferred_shape="straight",
        primary_zones=("exterior_corner", "perimeter_bay"),
        secondary_zones=("rear_service",),
        convenience_stair_probability=0.0, service_stair_probability=0.30,
        allow_open_primary_stair=True, prefer_direct_exterior_discharge=True,
        separation_factor=0.50, riser_target=0.19, clear_width=1.0),
    "parking_structure": dict(
        min_floors=2, max_floors=8, stair_count_policy="two",
        preferred_shape="switchback",
        primary_zones=("exterior_corner",),
        secondary_zones=("perimeter_bay",),
        convenience_stair_probability=0.0, service_stair_probability=0.0,
        allow_open_primary_stair=True, prefer_direct_exterior_discharge=True,
        separation_factor=0.50, riser_target=0.17, clear_width=1.2),
}

# s11.4 weighted score, verbatim weights
WEIGHTS = dict(corridor_connection_quality=30, discharge_quality=25,
               vertical_stack_efficiency=20, separation_from_other_stairs=15,
               structural_grid_alignment=10, archetype_fit=10,
               exterior_visibility=5,
               usable_area_damage=-20, corridor_dead_end_penalty=-20,
               route_dependency_penalty=-30, gameplay_chokepoint_penalty=-40)

_PERIMETER_NEAR = 2.5    # m from a rect edge to an exterior wall = "touches"
_TREAD_DEPTH = 0.28      # s10 commercial default
_ANCHOR_FIT_RADIUS = 3.0  # stairwell.py archetype-fit test uses this too


# ---------------------------------------------------------------------------
# Proposal geometry
# ---------------------------------------------------------------------------

def stair_dims(spec, profile):
    """(footprint_w, run, step_rise, clear_width, style) from the s10 riser
    math: uniform risers near the profile target, treads 0.28 m, run snapped
    to the main 0.5 m layout grid."""
    H = spec.story_height
    n = max(6, round(H / profile["riser_target"]))
    rise = H / n
    run = min(8.0, max(3.0, round((n * _TREAD_DEPTH) / 0.5) * 0.5))
    style = profile["preferred_shape"]
    w = profile["clear_width"]
    fw = 2 * w if style == "switchback" else w
    return fw, run, rise, w, style


def _front_rear_walls(spec):
    """Front = story-0 exterior wall with the most doors; rear = opposite.
    Falls back to S front / N rear (Deli Counter's usual storefront framing)."""
    doors = {"N": 0, "S": 0, "E": 0, "W": 0}
    for w in spec.ext_walls:
        if w.story != 0:
            continue
        doors[w.wall] += sum(1 for o in w.openings if o.kind in ("door", "garage"))
    front = max(doors, key=lambda k: doors[k]) if any(doors.values()) else "S"
    return front, {"N": "S", "S": "N", "E": "W", "W": "E"}[front]


def _circulation_rooms(spec, story=None):
    return [r for r in spec.rooms
            if (r.role or "") in stairwell.CIRCULATION_ROLES
            and (story is None or r.story == story)]


def candidate_zones(spec, profile):
    """Deterministic candidate anchors by zone family (s11.2). Returns a list
    of dicts {zone, x, y}; families that don't apply yield nothing."""
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    fw, run, _, _, _ = stair_dims(spec, profile)
    inset_x = hx - spec.wall_thick - 0.3 - fw / 2
    inset_y = hy - spec.wall_thick - 0.3 - run / 2
    if inset_x <= 0 or inset_y <= 0:
        return []
    out = []

    def add(zone, x, y):
        x = max(-inset_x, min(inset_x, x))
        y = max(-inset_y, min(inset_y, y))
        out.append({"zone": zone, "x": round(x, 2), "y": round(y, 2)})

    # 1. exterior corners
    for sx in (-1, 1):
        for sy in (-1, 1):
            add("exterior_corner", sx * inset_x, sy * inset_y)

    # 2. corridor-axis ends (long axis of each grade circulation room)
    for r in _circulation_rooms(spec, story=0):
        x0, y0, x1, y1 = r.bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if (x1 - x0) >= (y1 - y0):
            add("corridor_end", x0 + fw / 2 + 0.3, cy)
            add("corridor_end", x1 - fw / 2 - 0.3, cy)
        else:
            add("corridor_end", cx, y0 + run / 2 + 0.3)
            add("corridor_end", cx, y1 - run / 2 - 0.3)

    # 3. central core edges (the sides of the middle bay of the plate)
    add("core_edge", -hx / 3, 0.0)
    add("core_edge", hx / 3, 0.0)
    add("core_edge", 0.0, -hy / 3)
    add("core_edge", 0.0, hy / 3)

    # 4. wing junctions (shared-edge midpoints of adjacent circulation rooms)
    circ = _circulation_rooms(spec, story=0)
    for i, ra in enumerate(circ):
        for rb in circ[i + 1:]:
            ov_x = (max(ra.bounds[0], rb.bounds[0]),
                    min(ra.bounds[2], rb.bounds[2]))
            ov_y = (max(ra.bounds[1], rb.bounds[1]),
                    min(ra.bounds[3], rb.bounds[3]))
            if ov_x[1] - ov_x[0] >= 1.2 and abs(ov_y[1] - ov_y[0]) < 0.1:
                add("wing_junction", (ov_x[0] + ov_x[1]) / 2, ov_y[0])
            elif ov_y[1] - ov_y[0] >= 1.2 and abs(ov_x[1] - ov_x[0]) < 0.1:
                add("wing_junction", ov_x[0], (ov_y[0] + ov_y[1]) / 2)

    # 5. rear service band (rear wall: center + quarter points)
    _, rear = _front_rear_walls(spec)
    if rear == "N":
        for fx in (-0.5, 0.0, 0.5):
            add("rear_service", fx * inset_x, inset_y)
    elif rear == "S":
        for fx in (-0.5, 0.0, 0.5):
            add("rear_service", fx * inset_x, -inset_y)
    elif rear == "E":
        for fy in (-0.5, 0.0, 0.5):
            add("rear_service", inset_x, fy * inset_y)
    else:
        for fy in (-0.5, 0.0, 0.5):
            add("rear_service", -inset_x, fy * inset_y)

    # 6. perimeter bays (mid of each wall)
    add("perimeter_bay", 0.0, inset_y)
    add("perimeter_bay", 0.0, -inset_y)
    add("perimeter_bay", inset_x, 0.0)
    add("perimeter_bay", -inset_x, 0.0)

    # 7. party-wall bands (long side walls of a narrow plate, aspect >= 1.8)
    if spec.footprint_y / spec.footprint_x >= 1.8:      # long in Y
        for fy in (-0.5, 0.0, 0.5):
            add("party_wall", inset_x, fy * inset_y)
            add("party_wall", -inset_x, fy * inset_y)
    elif spec.footprint_x / spec.footprint_y >= 1.8:    # long in X
        for fx in (-0.5, 0.0, 0.5):
            add("party_wall", fx * inset_x, inset_y)
            add("party_wall", fx * inset_x, -inset_y)

    # dedupe anchors that collapsed onto each other after clamping
    seen, uniq = set(), []
    for c in out:
        key = (round(c["x"], 1), round(c["y"], 1))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def zone_families_at(spec, profile, x, y):
    """Zone families whose anchors sit within _ANCHOR_FIT_RADIUS of (x, y).
    stairwell.py uses this for the STAIR_LOW_ARCHETYPE_FIT intel warning."""
    fams = set()
    for c in candidate_zones(spec, profile):
        if math.hypot(c["x"] - x, c["y"] - y) <= _ANCHOR_FIT_RADIUS:
            fams.add(c["zone"])
    return fams


# ---------------------------------------------------------------------------
# Rejection (s11.3) -- every rejection carries its reason
# ---------------------------------------------------------------------------

def _cand_stair(spec, profile, cand):
    """A hypothetical Stairwell at this candidate, for footprint/graph reuse."""
    from spec_types import Stairwell
    _, run, rise, w, style = stair_dims(spec, profile)
    return Stairwell(x=cand["x"], y=cand["y"],
                     from_story=(-1 if spec.has_basement else 0),
                     to_story=spec.n_stories - 1,
                     width=w, run=run, style=style, step_rise=rise)


def reject_reason(spec, profile, cand, flat_graph):
    """Return a rejection reason string, or None if the candidate survives."""
    st = _cand_stair(spec, profile, cand)
    rect = stairwell.footprint_rect(st)
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    inner = spec.wall_thick + 0.1
    if rect[0] < -hx + inner or rect[2] > hx - inner \
            or rect[1] < -hy + inner or rect[3] > hy - inner:
        return "does_not_fit_inside_shell"

    served = stairwell.floors_served(spec, st)
    rect_area = (rect[2] - rect[0]) * (rect[3] - rect[1])
    for r in spec.rooms:
        if r.story not in served:
            continue
        ov = stairwell._overlap_area(rect, r.bounds)
        role = r.role or ""
        if (r.objective or role == "objective_room") and ov > 0.2 * rect_area:
            return f"overlaps_protected_room:{r.id}"
        if role in stairwell.CIRCULATION_ROLES:
            ra = (r.bounds[2] - r.bounds[0]) * (r.bounds[3] - r.bounds[1])
            if ra > 0 and ov > 0.6 * ra:
                return f"consumes_circulation:{r.id}"

    if spec.rooms:
        for s in served:
            if not any(r.story == s for r in spec.rooms):
                continue
            room = stairwell._approach_room(spec, s, st)
            if room and (room.role or "") in stairwell.PROHIBITED_APPROACH_ROLES:
                return f"entrance_through_prohibited_room:{room.id}@{s}"
        if 0 in served and any(r.story == 0 for r in spec.rooms):
            room = stairwell._approach_room(spec, 0, st)
            if room is None:
                return "no_room_covers_candidate_at_grade"
            dests = stairwell._exterior_rooms(spec, 0)
            if dests and stairwell._bfs_path(flat_graph, room.id, dests) is None:
                return f"no_ground_discharge_from:{room.id}"

    for i, ex in enumerate(spec.stairs):
        if stairwell._rects_overlap(rect, stairwell.footprint_rect(ex)):
            return f"overlaps_existing_stair:{stairwell.stair_ident(ex, i)}"
    return None


# ---------------------------------------------------------------------------
# Scoring (s11.4) and pair selection (s11.5)
# ---------------------------------------------------------------------------

def score_candidate(spec, profile, cand, flat_graph, others=()):
    """Weighted s11.4 score. Terms normalized 0..1; penalties 0..1 before the
    negative weights apply. Returns (score, terms) with every term recorded so
    a proposal can explain itself."""
    st = _cand_stair(spec, profile, cand)
    rect = stairwell.footprint_rect(st)
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    diag = math.hypot(spec.footprint_x, spec.footprint_y)
    t = {}

    room = None
    if spec.rooms and any(r.story == 0 for r in spec.rooms):
        room = stairwell._approach_room(spec, 0, st)

    if room is not None:
        role = room.role or ""
        t["corridor_connection_quality"] = (
            1.0 if role in stairwell.CIRCULATION_ROLES else
            0.0 if role in stairwell.PROHIBITED_APPROACH_ROLES else 0.6)
    else:
        t["corridor_connection_quality"] = 0.5 if not spec.rooms else 0.0

    edge_dist = min(rect[0] + hx, hx - rect[2], rect[1] + hy, hy - rect[3])
    perim = edge_dist <= _PERIMETER_NEAR
    if room is not None:
        dests = stairwell._exterior_rooms(spec, 0)
        path = stairwell._bfs_path(flat_graph, room.id, dests) if dests else None
        if path is None:
            t["discharge_quality"] = 0.0
        else:
            hops = len(path) - 1
            t["discharge_quality"] = max(0.2, 1.0 - 0.25 * hops)
            if profile["prefer_direct_exterior_discharge"] and not perim:
                t["discharge_quality"] *= 0.8
    else:
        t["discharge_quality"] = 1.0 if perim else 0.5

    # DC stairs stack by construction; efficiency only drops when upper
    # stories leave the shaft uncovered by any room (unrouted space).
    served = stairwell.floors_served(spec, st)
    roomed = [s for s in served if any(r.story == s for r in spec.rooms)]
    if roomed:
        covered = sum(1 for s in roomed
                      if stairwell._approach_room(spec, s, st) is not None)
        t["vertical_stack_efficiency"] = covered / len(roomed)
    else:
        t["vertical_stack_efficiency"] = 1.0

    ref = [(s.x, s.y) for s in spec.stairs] + [(o["x"], o["y"]) for o in others]
    if ref:
        near = min(math.hypot(cand["x"] - x, cand["y"] - y) for x, y in ref)
        req = max(stairwell.MIN_EGRESS_SEPARATION,
                  diag * profile["separation_factor"])
        t["separation_from_other_stairs"] = max(0.0, min(1.0, near / req))
    else:
        t["separation_from_other_stairs"] = 1.0

    off = (abs(cand["x"] / 1.0 - round(cand["x"] / 1.0))
           + abs(cand["y"] / 1.0 - round(cand["y"] / 1.0))) / 2
    t["structural_grid_alignment"] = 1.0 - off

    fams = zone_families_at(spec, profile, cand["x"], cand["y"])
    if fams & set(profile["primary_zones"]):
        t["archetype_fit"] = 1.0
    elif fams & set(profile["secondary_zones"]):
        t["archetype_fit"] = 0.6
    else:
        t["archetype_fit"] = 0.3

    t["exterior_visibility"] = 1.0 if perim else 0.0

    # a stair parked in the middle of the plate eats the most usable area
    centrality = 1.0 - min(1.0, math.hypot(cand["x"], cand["y"]) /
                           (0.5 * math.hypot(hx, hy)))
    t["usable_area_damage"] = centrality

    t["corridor_dead_end_penalty"] = 0.0
    t["route_dependency_penalty"] = 0.0
    if room is not None:
        if len(flat_graph.get(room.id, ())) <= 1 \
                and room.id not in stairwell._exterior_rooms(spec, 0):
            t["corridor_dead_end_penalty"] = 1.0
        for i, ex in enumerate(spec.stairs):
            exroom = stairwell._approach_room(spec, 0, ex)
            if exroom is not None and exroom.id == room.id:
                t["route_dependency_penalty"] = 1.0
    t["gameplay_chokepoint_penalty"] = 0.0   # priced at pair time (s11.5)

    score = sum(WEIGHTS[k] * v for k, v in t.items())
    return round(score, 2), t


def _routes_independent(spec, flat_graph, room_a, room_b):
    if room_a is None or room_b is None or room_a == room_b:
        return False
    return stairwell._shared_chokepoint(spec, flat_graph, room_a, room_b) is None


def select(spec, profile, scored, count, flat_graph):
    """Best single candidate, or the best PAIR under s11.5: separation valid,
    routes independent, discharge pair valid -- never just the two top
    individual scores. Returns a list of candidate dicts."""
    if not scored:
        return []
    if count == 1:
        return [scored[0]]
    diag = math.hypot(spec.footprint_x, spec.footprint_y)
    required = max(stairwell.MIN_EGRESS_SEPARATION,
                   diag * profile["separation_factor"])
    best, best_score = None, -math.inf
    for i, a in enumerate(scored):
        for b in scored[i + 1:]:
            dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if dist < required:
                continue
            ra, rb = a.get("room"), b.get("room")
            if spec.rooms and any(r.story == 0 for r in spec.rooms):
                if not _routes_independent(spec, flat_graph, ra, rb):
                    continue
            pair = a["score"] + b["score"]
            pair += 10.0 * min(1.0, dist / diag)          # coverage bonus
            pair += 5.0 * min(1.0, (dist - required) / diag)  # separation bonus
            if a.get("dest") and a.get("dest") == b.get("dest"):
                pair -= 10.0        # same discharge destination: soft penalty
            if pair > best_score:
                best, best_score = (a, b), pair
    if best is None:
        return [scored[0]]          # no valid pair; caller reports the shortfall
    return list(best)


def stair_count(spec, profile):
    if spec.n_stories < 2:
        return 0
    policy = profile["stair_count_policy"]
    if policy == "one":
        return 1
    if policy == "two":
        return 2
    area = spec.footprint_x * spec.footprint_y      # occupancy_and_floorplate
    return 2 if (area > 200 or spec.n_stories >= 3) else 1


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------

def propose(spec, archetype, count=None, ignore_existing=False):
    """Full placement proposal for a spec under an archetype profile. Pure and
    deterministic (extras roll on spec.seed). Returns a dict with the proposed
    stairs, every rejection and its reason, and the scored survivors.
    ignore_existing drops the spec's current stairs from rejection and
    separation math -- use when the proposal will REPLACE them."""
    if archetype not in PROFILES:
        raise ValueError(f"unknown archetype '{archetype}' "
                         f"(known: {', '.join(sorted(PROFILES))})")
    profile = PROFILES[archetype]
    if ignore_existing and spec.stairs:
        import copy
        spec = copy.copy(spec)
        spec.stairs = []
    notes = []
    total = spec.n_stories + (1 if spec.has_basement else 0)
    if not (profile["min_floors"] <= total <= profile["max_floors"]):
        notes.append(f"building has {total} floors; '{archetype}' expects "
                     f"{profile['min_floors']}-{profile['max_floors']}")

    n = stair_count(spec, profile) if count is None else count
    flat = {}
    if spec.rooms:
        flat = stairwell._same_story_edges(spec, tactical.build_graph(spec))

    cands = candidate_zones(spec, profile)
    rejected, survivors = [], []
    for c in cands:
        reason = reject_reason(spec, profile, c, flat)
        if reason:
            rejected.append({**c, "reason": reason})
            continue
        sc, terms = score_candidate(spec, profile, c, flat)
        st = _cand_stair(spec, profile, c)
        room = (stairwell._approach_room(spec, 0, st)
                if spec.rooms and any(r.story == 0 for r in spec.rooms) else None)
        dest = None
        if room is not None:
            dests = stairwell._exterior_rooms(spec, 0)
            path = stairwell._bfs_path(flat, room.id, dests) if dests else None
            dest = path[-1] if path else None
        survivors.append({**c, "score": sc, "terms": terms,
                          "room": room.id if room else None, "dest": dest})
    survivors.sort(key=lambda s: -s["score"])

    chosen = select(spec, profile, survivors, n, flat) if n else []
    if n == 2 and len(chosen) == 2:
        d = math.hypot(chosen[0]["x"] - chosen[1]["x"],
                       chosen[0]["y"] - chosen[1]["y"])
        req = max(stairwell.MIN_EGRESS_SEPARATION,
                  math.hypot(spec.footprint_x, spec.footprint_y)
                  * profile["separation_factor"])
        if d < req:
            notes.append(f"no candidate pair satisfies the {req:.1f} m "
                         f"separation; proposing the single best stair instead")
            chosen = chosen[:1]

    roles = ["primary_egress", "secondary_egress"]
    fw, run, rise, w, style = stair_dims(spec, profile)
    stairs_out = []
    for i, c in enumerate(chosen):
        stairs_out.append({
            "x": c["x"], "y": c["y"],
            "from_story": -1 if spec.has_basement else 0,
            "to_story": spec.n_stories - 1,
            "width": w, "run": run, "style": style, "step_rise": round(rise, 3),
            "cut_slabs": True,
            "id": f"{archetype}_{roles[i] if i < 2 else 'stair'}_{i}",
            "role": roles[i] if i < 2 else "primary_egress",
        })

    # probabilistic extras roll on the spec seed: same spec, same proposal
    rng = random.Random(spec.seed)
    taken = {(c["x"], c["y"]) for c in chosen}
    extras = [("service", profile["service_stair_probability"],
               ("rear_service", "party_wall", "perimeter_bay")),
              ("public_convenience", profile["convenience_stair_probability"],
               ("core_edge", "corridor_end"))]
    for role, prob, fams in extras:
        if rng.random() >= prob:
            continue
        pick = next((s for s in survivors
                     if s["zone"] in fams and (s["x"], s["y"]) not in taken), None)
        if pick:
            taken.add((pick["x"], pick["y"]))
            stairs_out.append({
                "x": pick["x"], "y": pick["y"],
                "from_story": 0, "to_story": spec.n_stories - 1,
                "width": w, "run": run, "style": style,
                "step_rise": round(rise, 3), "cut_slabs": True,
                "id": f"{archetype}_{role}", "role": role,
            })

    return {
        "archetype": archetype,
        "stair_count": n,
        "stairs": stairs_out,
        "considered": len(cands),
        "rejected": rejected,
        "scored": survivors[:8],
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _report(proposal):
    lines = [f"stair placement proposal -- archetype '{proposal['archetype']}'",
             f"  candidates considered: {proposal['considered']}   "
             f"rejected: {len(proposal['rejected'])}   "
             f"target count: {proposal['stair_count']}"]
    for n in proposal["notes"]:
        lines.append(f"  NOTE: {n}")
    for r in proposal["rejected"]:
        lines.append(f"  rejected {r['zone']} ({r['x']}, {r['y']}): "
                     f"{r['reason']}")
    for s in proposal["scored"]:
        lines.append(f"  scored   {s['zone']} ({s['x']}, {s['y']}): "
                     f"{s['score']}  room={s['room']} dest={s['dest']}")
    lines.append("proposed stairs (paste into the spec's \"stairs\" section):")
    lines.append(json.dumps(proposal["stairs"], indent=2))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec")
    ap.add_argument("--archetype", required=True, choices=sorted(PROFILES))
    ap.add_argument("--count", type=int, default=None,
                    help="override the profile's stair count policy")
    ap.add_argument("--write", action="store_true",
                    help="inject the proposal into the spec file "
                         "(refused if the spec already has stairs)")
    ap.add_argument("--replace", action="store_true",
                    help="with --write: replace an existing stairs section")
    args = ap.parse_args()

    from spec_loader import load_spec
    spec = load_spec(args.spec)
    proposal = propose(spec, args.archetype, count=args.count,
                       ignore_existing=args.replace)
    print(_report(proposal))

    if args.write:
        with open(args.spec, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("stairs") and not args.replace:
            sys.exit("REFUSED: spec already has a stairs section; "
                     "re-run with --replace to overwrite it deliberately.")
        data["stairs"] = proposal["stairs"]
        data.setdefault("archetype", args.archetype)
        with open(args.spec, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"\nwrote {len(proposal['stairs'])} stair(s) + archetype into "
              f"{args.spec} -- run validate.py to gate it.")


if __name__ == "__main__":
    main()
