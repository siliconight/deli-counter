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

Offline limits, stated plainly: candidates are axis-aligned rects of the
profile's footprint, evaluated in ALL FOUR cardinal facings -- a candidate is
(x, y, facing), never just a rectangle -- and every candidate must prove its
whole circulation system: lower landing, flight, upper landing, plus an
approach room capable of enclosing the stair. Anchors that don't fit are
REJECTED with a reason, never clamped back inside the shell (clamping used to
collapse distinct strategies onto the same awkward edge spot). Enclosure
walls, doors, and swings remain authoring work after the proposal lands.
Determinism: any probabilistic extra (service / convenience stair) rolls on
spec.seed, so the same spec proposes the same stairs forever.
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

FACINGS = ("N", "E", "S", "W")
# entry approach comes FROM this world direction (outward from the first
# tread) under each facing; used to break score ties toward interior approach
_ENTRY_DIR = {"N": (0, -1), "S": (0, 1), "E": (-1, 0), "W": (1, 0)}


def _clearance_extents(fw, run, facing):
    """Required clear distance from the anchor to the inner shell on each
    world side (W, S, E, N order as a dict), INCLUDING the landings: the
    ascent axis needs run/2 + LANDING_DEPTH at the entry end and
    run/2 + EXIT_STEP_OFF + LANDING_DEPTH at the exit end."""
    entry = run / 2 + stairwell.LANDING_DEPTH
    exit_ = run / 2 + stairwell.EXIT_STEP_OFF + stairwell.LANDING_DEPTH
    half = fw / 2
    if facing == "N":       # ascends +Y: entry south, exit north
        return {"W": half, "E": half, "S": entry, "N": exit_}
    if facing == "S":
        return {"W": half, "E": half, "N": entry, "S": exit_}
    if facing == "E":       # ascends +X: entry west, exit east
        return {"S": half, "N": half, "W": entry, "E": exit_}
    return {"S": half, "N": half, "E": entry, "W": exit_}


def _anchor_bounds(spec, ext):
    """Valid anchor region (x0, y0, x1, y1) for a facing's clearance extents,
    or None when the stair system cannot fit the plate in that orientation."""
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    m = spec.wall_thick + 0.3
    x0, x1 = -(hx - m - ext["W"]), hx - m - ext["E"]
    y0, y1 = -(hy - m - ext["S"]), hy - m - ext["N"]
    if x0 > x1 or y0 > y1:
        return None
    return (x0, y0, x1, y1)


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
    of dicts {zone, x, y, facing}; families that don't apply yield nothing.

    Every anchor is generated PER FACING with that orientation's clearance
    extents (footprint + entry landing + exit landing), so an edge-hugging
    anchor already leaves the landings room. An anchor whose stair system
    cannot fit the plate in a given facing is simply not generated for it --
    nothing is clamped back inside the shell."""
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    fw, run, _, _, _ = stair_dims(spec, profile)
    out = []

    def add(zone, x, y, facing, bounds=None):
        if bounds is not None:
            x0, y0, x1, y1 = bounds
            if not (x0 - 1e-9 <= x <= x1 + 1e-9
                    and y0 - 1e-9 <= y <= y1 + 1e-9):
                return                      # rejected, not clamped
        out.append({"zone": zone, "x": round(x, 2), "y": round(y, 2),
                    "facing": facing})

    per_facing = {}
    for f in FACINGS:
        b = _anchor_bounds(spec, _clearance_extents(fw, run, f))
        if b is not None:
            per_facing[f] = b
    if not per_facing:
        return []

    _, rear = _front_rear_walls(spec)
    long_y = spec.footprint_y / spec.footprint_x >= 1.8
    long_x = spec.footprint_x / spec.footprint_y >= 1.8

    for f, (x0, y0, x1, y1) in per_facing.items():
        xr, yr = min(-x0, x1), min(-y0, y1)   # symmetric band half-widths

        # 1. exterior corners (per facing: the tightest legal tuck-in)
        for cx in (x0, x1):
            for cy in (y0, y1):
                add("exterior_corner", cx, cy, f)

        # 3. central core edges (the sides of the middle bay of the plate)
        for ax, ay in ((-hx / 3, 0.0), (hx / 3, 0.0),
                       (0.0, -hy / 3), (0.0, hy / 3)):
            add("core_edge", ax, ay, f, (x0, y0, x1, y1))

        # 5. rear service band (rear wall: center + quarter points)
        if rear == "N":
            for fx in (-0.5, 0.0, 0.5):
                add("rear_service", fx * xr, y1, f)
        elif rear == "S":
            for fx in (-0.5, 0.0, 0.5):
                add("rear_service", fx * xr, y0, f)
        elif rear == "E":
            for fy in (-0.5, 0.0, 0.5):
                add("rear_service", x1, fy * yr, f)
        else:
            for fy in (-0.5, 0.0, 0.5):
                add("rear_service", x0, fy * yr, f)

        # 6. perimeter bays (mid of each wall)
        add("perimeter_bay", 0.0, y1, f)
        add("perimeter_bay", 0.0, y0, f)
        add("perimeter_bay", x1, 0.0, f)
        add("perimeter_bay", x0, 0.0, f)

        # 7. party-wall bands (long side walls of a narrow plate)
        if long_y:
            for fy in (-0.5, 0.0, 0.5):
                add("party_wall", x1, fy * yr, f)
                add("party_wall", x0, fy * yr, f)
        elif long_x:
            for fx in (-0.5, 0.0, 0.5):
                add("party_wall", fx * xr, y1, f)
                add("party_wall", fx * xr, y0, f)

        # 2. corridor-axis ends (long axis of each grade circulation room).
        # Along-axis facings tuck the stair against the end wall with the
        # landings inboard; cross-axis facings stand it across the corridor.
        # A room edge that IS the exterior shell gets the anchor pushed in
        # by the wall allowance (a room-bounded derivation, not a clamp --
        # anchors that still don't fit their facing are dropped).
        ext = _clearance_extents(fw, run, f)
        for r in _circulation_rooms(spec, story=0):
            rx0, ry0, rx1, ry1 = r.bounds
            cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
            if (rx1 - rx0) >= (ry1 - ry0):
                add("corridor_end", max(rx0 + ext["W"] + 0.3, x0), cy, f,
                    (x0, y0, x1, y1))
                add("corridor_end", min(rx1 - ext["E"] - 0.3, x1), cy, f,
                    (x0, y0, x1, y1))
            else:
                add("corridor_end", cx, max(ry0 + ext["S"] + 0.3, y0), f,
                    (x0, y0, x1, y1))
                add("corridor_end", cx, min(ry1 - ext["N"] - 0.3, y1), f,
                    (x0, y0, x1, y1))

        # 4. wing junctions (shared-edge midpoints of circulation rooms)
        circ = _circulation_rooms(spec, story=0)
        for i, ra in enumerate(circ):
            for rb in circ[i + 1:]:
                ov_x = (max(ra.bounds[0], rb.bounds[0]),
                        min(ra.bounds[2], rb.bounds[2]))
                ov_y = (max(ra.bounds[1], rb.bounds[1]),
                        min(ra.bounds[3], rb.bounds[3]))
                if ov_x[1] - ov_x[0] >= 1.2 and abs(ov_y[1] - ov_y[0]) < 0.1:
                    add("wing_junction", (ov_x[0] + ov_x[1]) / 2, ov_y[0], f,
                        (x0, y0, x1, y1))
                elif ov_y[1] - ov_y[0] >= 1.2 and abs(ov_x[1] - ov_x[0]) < 0.1:
                    add("wing_junction", ov_x[0], (ov_y[0] + ov_y[1]) / 2, f,
                        (x0, y0, x1, y1))

    # dedupe anchors that landed on each other (across zone families)
    seen, uniq = set(), []
    for c in out:
        key = (round(c["x"], 1), round(c["y"], 1), c["facing"])
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
                     width=w, run=run, style=style, step_rise=rise,
                     facing=cand.get("facing", "N"))


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
            if room is None:
                return f"no_room_covers_candidate@{s}"
            if (room.role or "") in stairwell.PROHIBITED_APPROACH_ROLES:
                return f"entrance_through_prohibited_room:{room.id}@{s}"
            # the proposal will carry an egress role, so its approach room
            # must be able to READ as a stair enclosure -- the review's
            # STAIR_NOT_ENCLOSED gate. Profiles that allow an open primary
            # stair (house, warehouse, parking) opt out.
            if not profile["allow_open_primary_stair"] \
                    and (room.role or "") not in stairwell.ENCLOSED_STAIR_ROLES:
                return f"approach_not_enclosure_capable:{room.id}@{s}"
        if 0 in served and any(r.story == 0 for r in spec.rooms):
            room = stairwell._approach_room(spec, 0, st)
            dests = stairwell._exterior_rooms(spec, 0)
            if dests and stairwell._bfs_path(flat_graph, room.id, dests) is None:
                return f"no_ground_discharge_from:{room.id}"

    for i, ex in enumerate(spec.stairs):
        if stairwell._rects_overlap(rect, stairwell.footprint_rect(ex)):
            return f"overlaps_existing_stair:{stairwell.stair_ident(ex, i)}"

    # physical circulation: oriented entry/exit edges + landing volumes.
    # The same proof stairwell.check() gates on -- the loop must close.
    findings = stairwell.clearance_findings(spec, st, "cand")
    if findings:
        code, _ = findings[0]
        return code.lower()
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


def _combo_findings(spec, profile, cands):
    """Total clearance findings across the spec's existing stairs PLUS the
    hypothetical candidates, together. Selected stairs must not consume each
    other's landings -- a candidate that is clean alone can still park its
    footprint on another pick's landing."""
    import copy as _copy
    trial = _copy.copy(spec)
    trial.stairs = list(spec.stairs) + [_cand_stair(spec, profile, c)
                                        for c in cands]
    n = 0
    for i, st in enumerate(trial.stairs):
        n += len(stairwell.clearance_findings(trial, st, f"s{i}"))
    return n


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
    baseline = _combo_findings(spec, profile, [])
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
            # the PAIR must be physically clean together: neither member may
            # consume the other's landings
            if _combo_findings(spec, profile, [a, b]) > baseline:
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

def propose(spec, archetype, count=None, ignore_existing=False, profile=None):
    """Full placement proposal for a spec under an archetype profile. Pure and
    deterministic (extras roll on spec.seed). Returns a dict with the proposed
    stairs, every rejection and its reason, and the scored survivors.
    ignore_existing drops the spec's current stairs from rejection and
    separation math -- use when the proposal will REPLACE them. `profile`
    overrides the archetype's registered profile (stair_core.py uses this to
    relax the enclosure requirement, because core-first generation BUILDS the
    enclosure after placement)."""
    if archetype not in PROFILES:
        raise ValueError(f"unknown archetype '{archetype}' "
                         f"(known: {', '.join(sorted(PROFILES))})")
    if profile is None:
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

    # one survivor per anchor: the best FACING wins the spot. Ties break
    # toward an entry that is approached from the plate interior (a stair
    # against the north wall should be entered from the south), then by
    # stable facing order -- deterministic forever.
    def _facing_pref(s):
        dx, dy = _ENTRY_DIR[s.get("facing", "N")]
        return dx * -s["x"] + dy * -s["y"]

    best_at = {}
    for s in survivors:
        key = (s["x"], s["y"])
        cur = best_at.get(key)
        if cur is None or (s["score"], _facing_pref(s),
                           -FACINGS.index(s.get("facing", "N"))) \
                > (cur["score"], _facing_pref(cur),
                   -FACINGS.index(cur.get("facing", "N"))):
            best_at[key] = s
    survivors = list(best_at.values())
    survivors.sort(key=lambda s: -s["score"])

    # the numbered egress picks come from the profile's OWN zone families;
    # off-profile families (e.g. rear_service for an office) stay in the
    # survivor pool for the probabilistic extras below
    prof_zones = set(profile["primary_zones"]) | set(profile["secondary_zones"])
    main_pool = [s for s in survivors if s["zone"] in prof_zones] or survivors
    chosen = select(spec, profile, main_pool, n, flat) if n else []
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
            "facing": c.get("facing", "N"),
            "cut_slabs": True,
            "id": f"{archetype}_{roles[i] if i < 2 else 'stair'}_{i}",
            "role": roles[i] if i < 2 else "primary_egress",
            "meta": {"generated_by": "stair_place"},
        })

    # probabilistic extras roll on the spec seed: same spec, same proposal.
    # An extra must be physically clean IN COMBINATION with everything
    # already selected -- clean-alone is not enough (its footprint could
    # consume a chosen stair's landing).
    rng = random.Random(spec.seed)
    taken = {(c["x"], c["y"]) for c in chosen}
    selected = list(chosen)
    combo_base = _combo_findings(spec, profile, selected) \
        if chosen else _combo_findings(spec, profile, [])
    extras = [("service", profile["service_stair_probability"],
               ("rear_service", "party_wall", "perimeter_bay")),
              ("public_convenience", profile["convenience_stair_probability"],
               ("core_edge", "corridor_end"))]
    for role, prob, fams in extras:
        if rng.random() >= prob:
            continue
        pick = next(
            (s for s in survivors
             if s["zone"] in fams and (s["x"], s["y"]) not in taken
             and _combo_findings(spec, profile, selected + [s]) <= combo_base),
            None)
        if pick:
            selected.append(pick)
            taken.add((pick["x"], pick["y"]))
            stairs_out.append({
                "x": pick["x"], "y": pick["y"],
                "from_story": 0, "to_story": spec.n_stories - 1,
                "width": w, "run": run, "style": style,
                "step_rise": round(rise, 3),
                "facing": pick.get("facing", "N"), "cut_slabs": True,
                "id": f"{archetype}_{role}", "role": role,
                "meta": {"generated_by": "stair_place"},
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
        lines.append(f"  rejected {r['zone']} ({r['x']}, {r['y']}) "
                     f"facing {r.get('facing', 'N')}: {r['reason']}")
    for s in proposal["scored"]:
        lines.append(f"  scored   {s['zone']} ({s['x']}, {s['y']}) "
                     f"facing {s.get('facing', 'N')}: "
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
