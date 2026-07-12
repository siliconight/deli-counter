#!/usr/bin/env python3
"""
ladder_place.py  --  facade ladder placement proposals (no Blender)
===================================================================
Phase 2 of docs/deli_counter_ladder_placement_spec.md: the PLACEMENT side of
what ladder.py reviews, and the ladder analog of stair_place.py. Given a spec
and a building profile, propose where an EXTERIOR roof-access ladder belongs --
generated from a meaningful connection pair (a ground/service surface to the
roof), scored by the spec's s12.4 weights, with a resolved top transition
(through / side-step / parapet crossover) and validated lower + upper landings.

The spec's §23 governing question drives this: not "where can a ladder fit?"
but "what real access problem requires a ladder, and what complete route does
that ladder create?" So candidates come from connection pairs, not from empty
wall availability, and every rejected candidate carries its reason (s12.3).

This is a PROPOSAL tool, not an authority. Deli Counter is spec-driven: the
author owns the ladders section. Default output is a JSON block + score table
to read and paste; --write injects it only into a spec with no ladders (or
--replace, deliberately). Every proposed ladder carries the role, surfaces, and
transition that let it pass ladder.check -- place with this tool, gate with
validate. Determinism: any tie is broken by candidate order, so the same spec
proposes the same ladder forever.

Offline limits, stated plainly: DC ladders run vertically at (x, y) with a
cardinal `facing`, so candidates are wall-anchored points, not arbitrary
brackets; parapet crossovers, hatch covers, and weather remain authoring work
after the proposal lands.

    python ladder_place.py specs/gs_auto_shop.json --profile modern_small_commercial
    python ladder_place.py specs/x.json --profile warehouse_industrial --write
"""

import argparse
import json
import math

import tactical
import ladder as _lad

# ---------------------------------------------------------------------------
# Building profiles (spec s21) -- what a profile permits and prefers
# ---------------------------------------------------------------------------

PROFILES = {
    "modern_small_commercial": dict(
        allow_exterior_roof_ladder=True, allow_roof_hatch_ladder=True,
        allow_legacy_fire_escape=False, allow_ladder_as_egress=False,
        restrict_public_access=True, prefer_rear_or_side_facade=True,
        fall_protection_trigger_m=7.3, default_role="roof_access",
        default_access_control="locked_hatch"),
    "historic_urban_mixed_use": dict(
        allow_exterior_roof_ladder=True, allow_roof_hatch_ladder=True,
        allow_legacy_fire_escape=True, allow_ladder_as_egress=False,
        allow_fire_escape_ladder_termination="conditional",
        restrict_public_access=True, prefer_rear_or_side_facade=True,
        fall_protection_trigger_m=7.3, default_role="roof_access",
        default_access_control="locked_gate"),
    "modern_office": dict(
        allow_exterior_roof_ladder=False, allow_roof_hatch_ladder=True,
        allow_legacy_fire_escape=False, allow_ladder_as_egress=False,
        restrict_public_access=True, prefer_internal_service_access=True,
        prefer_rear_or_side_facade=True,
        fall_protection_trigger_m=7.3, default_role="roof_access",
        default_access_control="locked_hatch"),
    "warehouse_industrial": dict(
        allow_exterior_roof_ladder=True, allow_platform_ladders=True,
        allow_offset_sections=True, allow_legacy_fire_escape=False,
        allow_ladder_as_egress=False, restrict_public_access=False,
        prefer_rear_or_side_facade=True, require_vehicle_conflict_test=True,
        fall_protection_trigger_m=7.3, default_role="roof_access",
        default_access_control="ladder_guard"),
    "residential_house": dict(
        allow_exterior_roof_ladder=False, allow_roof_hatch_ladder=False,
        allow_legacy_fire_escape=False, allow_ladder_as_egress=False,
        restrict_public_access=True, prefer_rear_or_side_facade=True,
        fall_protection_trigger_m=7.3, default_role="maintenance_access",
        default_access_control="removable_section"),
    "stylized_gameplay_override": dict(
        allow_special_gameplay_ladder=True, allow_exterior_roof_ladder=True,
        allow_roof_hatch_ladder=True, allow_legacy_fire_escape=True,
        allow_ladder_as_egress=False, restrict_public_access=False,
        prefer_rear_or_side_facade=False, fall_protection_trigger_m=7.3,
        default_role="special_gameplay_route", default_access_control=None),
}

# s12.4 scoring weights, verbatim
WEIGHTS = dict(
    service_adjacency=20, destination_relevance=25, route_continuity=30,
    rear_or_side_facade_fit=12, clear_lower_landing=20, clear_upper_landing=25,
    structural_alignment=10, security_fit=8, gameplay_value=0,
    public_facade_penalty=-12, door_window_conflict=-40, vehicle_conflict=-40,
    weather_hazard=-15, utility_hazard=-30, excessive_climb_penalty=-25,
    visual_noise_penalty=-5)

SERVICE_ROLES = {"mechanical", "utility", "service_access", "maintenance",
                 "back_of_house", "loading", "storage", "kitchen"}
# volume name fragments that read as a real rooftop destination vs a hazard
_EQUIP_HINTS = ("hvac", "condenser", "unit", "equipment", "mechanical",
                "sign", "antenna", "vent", "compressor", "chiller", "tank")
_HAZARD_HINTS = ("scupper", "drain", "exhaust", "transformer", "electrical",
                 "fuel", "grease", "steam")
_WALL_INSET = 0.35        # ladder rail sits this far off the facade plane


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _wall_anchor(spec, wall, frac):
    """A point just inside the given exterior wall at fractional position
    `frac` in [-0.5, 0.5] along its run, with the cardinal facing the climber
    uses to face that wall."""
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    if wall == "N":
        return frac * spec.footprint_x, hy - _WALL_INSET, "N"
    if wall == "S":
        return frac * spec.footprint_x, -hy + _WALL_INSET, "S"
    if wall == "E":
        return hx - _WALL_INSET, frac * spec.footprint_y, "E"
    return -hx + _WALL_INSET, frac * spec.footprint_y, "W"


def _wall_has_opening_near(spec, wall, u, story, tol):
    """Is there a door/window on `wall` at `story` within `tol` of run-position
    u (world coord along the wall)?"""
    run = spec.footprint_x if wall in ("N", "S") else spec.footprint_y
    for w in spec.ext_walls:
        if w.story != story or w.wall != wall:
            continue
        for op in w.openings:
            if abs(op.pos * run - u) <= tol:
                return op.kind
    return None


def _nearest_volume(spec, x, y, hints):
    """Nearest named volume whose name matches any hint, and its distance."""
    best, bd = None, math.inf
    for v in getattr(spec, "volumes", []):
        nm = v.name.lower()
        if not any(h in nm for h in hints):
            continue
        d = math.hypot(v.x - x, v.y - y)
        if d < bd:
            best, bd = v, d
    return best, bd


def _grade_room_at(spec, x, y):
    return tactical._room_at(spec, 0, x, y)


def _roof_walkable(spec):
    """Is the top slab a usable dismount surface? True unless roof=='none'."""
    return getattr(spec, "roof", "solid") != "none" and spec.n_stories >= 1


# ---------------------------------------------------------------------------
# Candidate generation from connection pairs (spec s12.2)
# ---------------------------------------------------------------------------

def candidate_walls(spec, profile):
    """Ordered exterior walls to consider, service-facing first. Front (the
    most-doored wall) is deprioritized; rear/side preferred (Rule 3, s7.1)."""
    front, rear = _front_rear_walls(spec)
    order = [rear] + [w for w in ("N", "S", "E", "W") if w not in (front, rear)]
    order.append(front)         # public facade last (still allowed, penalized)
    return order, front, rear


def _front_rear_walls(spec):
    doors = {"N": 0, "S": 0, "E": 0, "W": 0}
    for w in spec.ext_walls:
        if w.story != 0:
            continue
        doors[w.wall] += sum(1 for o in w.openings
                             if o.kind in ("door", "garage"))
    front = max(doors, key=lambda k: doors[k]) if any(doors.values()) else "S"
    return front, {"N": "S", "S": "N", "E": "W", "W": "E"}[front]


def candidate_zones(spec, profile):
    """Deterministic exterior roof-access candidates: for each preferred wall,
    anchor points at the center and quarter positions. Each candidate is a
    connection pair {grade/service surface -> roof}."""
    if not profile.get("allow_exterior_roof_ladder", False):
        return []
    if not _roof_walkable(spec):
        return []
    walls, front, rear = candidate_walls(spec, profile)
    cands = []
    for wall in walls:
        for frac in (0.0, -0.3, 0.3):
            x, y, facing = _wall_anchor(spec, wall, frac)
            cands.append({"wall": wall, "x": round(x, 2), "y": round(y, 2),
                          "facing": facing, "frac": frac,
                          "is_front": wall == front, "is_rear": wall == rear})
    # dedupe collapsed anchors
    seen, out = set(), []
    for c in cands:
        key = (round(c["x"], 1), round(c["y"], 1))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Rejection (spec s12.3) -- every rejection carries a reason
# ---------------------------------------------------------------------------

def _cand_ladder(spec, cand, profile):
    from spec_types import Ladder
    return Ladder(x=cand["x"], y=cand["y"], from_story=0, to_story=spec.n_stories,
                  facing=cand["facing"], role=profile["default_role"],
                  placement_mode="exterior_wall", lower_surface="grade",
                  upper_surface="roof")


def reject_reason(spec, cand, profile):
    """Reason string if the candidate fails a hard test (s12.3), else None."""
    wall = cand["wall"]
    run = spec.footprint_x if wall in ("N", "S") else spec.footprint_y
    u = cand["frac"] * run
    # door/window in the climb zone at any served story
    for s in range(0, spec.n_stories):
        kind = _wall_has_opening_near(spec, wall, u, s, tol=1.0)
        if kind in ("door", "garage", "breach"):
            return f"door_in_climb_zone:{wall}@{s}"
        if kind == "window":
            return f"window_in_climb_zone:{wall}@{s}"
    # upper landing must be walkable roof
    if not _roof_walkable(spec):
        return "roof_not_walkable"
    # utility/electrical hazard volume at the base
    hz, hd = _nearest_volume(spec, cand["x"], cand["y"], _HAZARD_HINTS)
    if hz is not None and hd < 1.5:
        return f"hazard_at_base:{hz.name}"
    # long climb with no offset support in the profile
    climb = spec.n_stories * spec.story_height
    if climb > profile["fall_protection_trigger_m"] \
            and not profile.get("allow_offset_sections", False):
        return f"climb_too_tall_for_profile:{climb:.1f}m"
    return None


# ---------------------------------------------------------------------------
# Scoring (spec s12.4) and transition selection (s10.1-10.2)
# ---------------------------------------------------------------------------

def _select_transition(spec, cand):
    """Resolve the top transition from parapet presence (Rule 5/6). Exterior
    ladder to a parapeted roof -> crossover; otherwise a through step-off."""
    has_parapet = any(p.story >= spec.n_stories - 1
                      for p in getattr(spec, "parapets", []))
    if has_parapet:
        return "parapet_crossover_platform", 0.24     # within 0.18-0.30 through
    return "through_step_off", 0.24


def score_candidate(spec, cand, profile):
    """Weighted s12.4 score with every term recorded so a proposal explains
    itself. Terms normalized 0..1 before the signed weights apply."""
    t = {}
    x, y = cand["x"], cand["y"]

    # service adjacency: a service/utility room behind this base
    grade = _grade_room_at(spec, x, y)
    role = None
    for r in spec.rooms:
        if r.id == grade:
            role = r.role or ""
    t["service_adjacency"] = 1.0 if (role in SERVICE_ROLES) else (
        0.4 if role else 0.2)

    # destination relevance: rooftop equipment near the dismount
    eq, ed = _nearest_volume(spec, x, y, _EQUIP_HINTS)
    t["destination_relevance"] = (max(0.3, 1.0 - ed / 15.0)
                                  if eq is not None else 0.4)

    # route continuity: base reachable + roof walkable
    t["route_continuity"] = 1.0 if (grade or not spec.rooms) else 0.3

    t["rear_or_side_facade_fit"] = 1.0 if cand["is_rear"] else (
        0.0 if cand["is_front"] else 0.7)

    # landings: clear of nearby volumes
    _, ld = _nearest_volume(spec, x, y, _EQUIP_HINTS + _HAZARD_HINTS)
    t["clear_lower_landing"] = min(1.0, ld / 2.0) if ld < math.inf else 1.0
    t["clear_upper_landing"] = 1.0        # roof assumed clear at proposal time

    # structural alignment: near a wall (always true here) + grid-snapped
    off = (abs(x - round(x)) + abs(y - round(y))) / 2
    t["structural_alignment"] = 1.0 - off

    t["security_fit"] = 1.0 if profile.get("restrict_public_access") else 0.5
    t["gameplay_value"] = 0.0

    # penalties (0..1 before the negative weight)
    t["public_facade_penalty"] = 1.0 if cand["is_front"] else 0.0
    t["door_window_conflict"] = 0.0       # rejected earlier if present
    t["vehicle_conflict"] = 0.0           # no vehicle-path primitive yet
    hz, hd = _nearest_volume(spec, x, y, ("scupper", "drain"))
    t["weather_hazard"] = 1.0 if (hz is not None and hd < 2.0) else 0.0
    uz, ud = _nearest_volume(spec, x, y, ("transformer", "electrical", "fuel"))
    t["utility_hazard"] = 1.0 if (uz is not None and ud < 2.0) else 0.0
    climb = spec.n_stories * spec.story_height
    over = max(0.0, climb - profile["fall_protection_trigger_m"])
    t["excessive_climb_penalty"] = min(1.0, over / 5.0)
    t["visual_noise_penalty"] = 0.3 if cand["is_front"] else 0.0

    score = sum(WEIGHTS[k] * v for k, v in t.items())
    return round(score, 2), t


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------

def _service_rooms(spec, story):
    """Rooms on `story` whose role reads as a service/back-of-house space --
    the preferred origin for an interior roof-hatch ladder (spec s8.1)."""
    import ladder as _l
    out = []
    for r in spec.rooms:
        if r.story != story:
            continue
        role = r.role or ""
        if role in _l.HATCH_PREFERRED_ROLES and role not in ("connector",):
            out.append(r)
    # fall back to connectors if no dedicated service room exists
    if not out:
        for r in spec.rooms:
            if r.story == story and (r.role or "") == "connector":
                out.append(r)
    return out


def hatch_candidate_zones(spec, profile):
    """Interior roof-hatch candidates (spec s8): a hatch ladder rises from a
    top-floor service room straight to the roof. Anchor at each service room's
    centroid, kept a hatch-swing clear of the room edges and the roof edge."""
    if not profile.get("allow_roof_hatch_ladder", False):
        return []
    if not _roof_walkable(spec):
        return []
    top = spec.n_stories - 1
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    cands = []
    for r in _service_rooms(spec, top):
        x0, y0, x1, y1 = r.bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # nudge off any roof edge by the swing envelope so the cover clears
        cx = max(-hx + 1.0, min(hx - 1.0, cx))
        cy = max(-hy + 1.0, min(hy - 1.0, cy))
        cands.append({"room": r.id, "story": r.story,
                      "x": round(cx, 2), "y": round(cy, 2),
                      "facing": "S", "role": r.role or ""})
    return cands


def _hatch_reject_reason(spec, cand, profile):
    import ladder as _l
    role = cand["role"]
    if role in _l.HATCH_PROHIBITED_ROLES:
        return f"prohibited_room:{cand['room']}({role})"
    # equipment in the dismount disc
    eq, ed = _nearest_volume(spec, cand["x"], cand["y"], _EQUIP_HINTS)
    if eq is not None and ed < _l.HATCH_CLEAR_RADIUS:
        return f"equipment_over_hatch:{eq.name}"
    # parapet edge collision with the cover swing
    if any(p.story >= spec.n_stories - 1
           for p in getattr(spec, "parapets", [])):
        edge = min(spec.footprint_x / 2 - abs(cand["x"]),
                   spec.footprint_y / 2 - abs(cand["y"]))
        if edge < _l.HATCH_SWING:
            return "parapet_blocks_cover_swing"
    return None


def _hatch_score(spec, cand, profile):
    import ladder as _l
    t = {}
    role = cand["role"]
    t["service_adjacency"] = 1.0 if role in SERVICE_ROLES else (
        0.6 if role in _l.HATCH_PREFERRED_ROLES else 0.3)
    eq, ed = _nearest_volume(spec, cand["x"], cand["y"], _EQUIP_HINTS)
    t["destination_relevance"] = (max(0.4, 1.0 - ed / 15.0)
                                  if eq is not None else 0.5)
    t["route_continuity"] = 1.0        # inside a room, on the service route
    t["clear_lower_landing"] = 1.0
    t["clear_upper_landing"] = 1.0
    t["security_fit"] = 1.0 if profile.get("restrict_public_access") else 0.5
    # centrality: a hatch away from the roof edge is safer (no edge fall zone)
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    edge = min(hx - abs(cand["x"]), hy - abs(cand["y"]))
    t["structural_alignment"] = min(1.0, edge / 3.0)
    score = (WEIGHTS["service_adjacency"] * t["service_adjacency"]
             + WEIGHTS["destination_relevance"] * t["destination_relevance"]
             + WEIGHTS["route_continuity"] * t["route_continuity"]
             + WEIGHTS["clear_lower_landing"] * t["clear_lower_landing"]
             + WEIGHTS["clear_upper_landing"] * t["clear_upper_landing"]
             + WEIGHTS["security_fit"] * t["security_fit"]
             + WEIGHTS["structural_alignment"] * t["structural_alignment"])
    return round(score, 2), t


def platform_candidate_zones(spec, profile):
    """Industrial platform-access candidates (spec s5.6, s12.2): one ladder
    per platform that isn't already reachable, anchored just off the platform's
    open (unguarded) edge at floor level. Generated from the platform graph,
    not empty walls (s5.9)."""
    import ladder as _l
    cands = []
    for p in getattr(spec, "platforms", []):
        open_edges = [e for e in ("N", "S", "E", "W")
                      if e not in (p.guard_edges or [])]
        edge = open_edges[0] if open_edges else "S"
        hx, hy = p.size_x / 2, p.size_y / 2
        if edge == "N":
            bx, by, facing = p.x, p.y + hy + 0.5, "S"
        elif edge == "S":
            bx, by, facing = p.x, p.y - hy - 0.5, "N"
        elif edge == "E":
            bx, by, facing = p.x + hx + 0.5, p.y, "W"
        else:
            bx, by, facing = p.x - hx - 0.5, p.y, "E"
        cands.append({"platform": p.id, "x": round(bx, 2), "y": round(by, 2),
                      "facing": facing, "z": p.z,
                      "role": p.role or "", "destination": p.destination,
                      "open_edge": edge})
    return cands


def _platform_reject_reason(spec, cand, profile):
    import ladder as _l
    p = _l._platform_by_id(spec, cand["platform"])
    if p is None:
        return "platform_missing"
    if set(p.guard_edges or []) >= {"N", "S", "E", "W"}:
        return "platform_fully_guarded_no_access_edge"
    # base in a hazard volume
    hz, hd = _nearest_volume(spec, cand["x"], cand["y"], _HAZARD_HINTS)
    if hz is not None and hd < 1.5:
        return f"hazard_at_base:{hz.name}"
    return None


def _platform_score(spec, cand, profile):
    t = {}
    t["destination_relevance"] = 1.0 if cand["destination"] else 0.4
    t["route_continuity"] = 1.0
    t["service_adjacency"] = 1.0 if cand["role"] in ("equipment", "catwalk",
                                                     "tank", "sign") else 0.5
    t["clear_lower_landing"] = 1.0
    t["clear_upper_landing"] = 1.0
    score = (WEIGHTS["destination_relevance"] * t["destination_relevance"]
             + WEIGHTS["route_continuity"] * t["route_continuity"]
             + WEIGHTS["service_adjacency"] * t["service_adjacency"]
             + WEIGHTS["clear_lower_landing"] * t["clear_lower_landing"]
             + WEIGHTS["clear_upper_landing"] * t["clear_upper_landing"])
    return round(score, 2), t


def fire_escape_proposal(spec, profile, count=None):
    """Generate a legacy fire-escape SYSTEM per spec s9.1: identify served
    occupied floors, place it on a service-facing facade, select a termination,
    and add the drop/termination ladder. Returns (fire_escapes, ladders,
    notes). Only proposed when the profile allows legacy fire escapes."""
    notes = []
    if not profile.get("allow_legacy_fire_escape", False):
        notes.append("profile does not allow legacy fire escapes (s21)")
        return [], [], notes
    # s9.1 step 1 -- served occupied floors are the upper stories (not grade)
    served = sorted({r.story for r in spec.rooms if r.story >= 1})
    if not served:
        served = list(range(1, spec.n_stories))
    if not served:
        notes.append("no upper occupied floors to serve")
        return [], [], notes
    # s9.1 step 2/3 -- place on the rear (service-facing) facade
    front, rear = _front_rear_walls(spec)
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    # anchor the drop ladder just outside the rear wall at grade
    if rear == "N":
        lx, ly, facing = 0.0, hy + 0.7, "S"
    elif rear == "S":
        lx, ly, facing = 0.0, -hy - 0.7, "N"
    elif rear == "E":
        lx, ly, facing = hx + 0.7, 0.0, "W"
    else:
        lx, ly, facing = -hx - 0.7, 0.0, "E"
    fe = {
        "id": "rear_fire_escape", "wall": rear,
        "served_stories": served, "along": 0.0,
        "termination": "stair_to_grade", "access": "window",
    }
    # s9.3 -- prefer a stair to grade; drop ladder only as the legacy exception.
    # If the profile flags a conditional ladder termination, use a drop ladder.
    if profile.get("allow_fire_escape_ladder_termination") == "conditional":
        fe["termination"] = "drop_ladder"
        drop = [{
            "x": round(lx, 2), "y": round(ly, 2), "from_story": 0,
            "to_story": 1, "facing": facing, "id": "fire_escape_drop_ladder",
            "role": "fire_escape_termination", "ladder_type": "fixed_vertical",
            "placement_mode": "exterior_wall", "lower_surface": "grade",
            "upper_surface": "rear_fire_escape",
            "direction": "deploy_then_bidirectional", "access_class": "emergency",
            "transition": "fire_escape_platform_entry",
            "fire_escape_id": "rear_fire_escape",
            "access_control": "removable_section",
            "counts_as_secondary_escape": True,
        }]
    else:
        drop = []      # stair_to_grade needs no ladder
    return [fe], drop, notes


def propose(spec, profile_name, count=None, mode="exterior"):
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile '{profile_name}' "
                         f"(known: {', '.join(sorted(PROFILES))})")
    profile = PROFILES[profile_name]
    notes = []

    if mode == "fire_escape":
        fes, drop, notes = fire_escape_proposal(spec, profile, count)
        return {"profile": profile_name, "mode": "fire_escape", "count": 1,
                "fire_escapes": fes, "ladders": drop, "considered": 1,
                "rejected": [], "scored": [], "notes": notes}

    if mode == "equipment":
        import ladder as _l
        if not getattr(spec, "platforms", []):
            notes.append("no platforms in the spec -- add catwalk/equipment "
                         "platforms before proposing platform-access ladders")
        cands = platform_candidate_zones(spec, profile)
        rejected, survivors = [], []
        for c in cands:
            reason = _platform_reject_reason(spec, c, profile)
            if reason:
                rejected.append({**c, "reason": reason})
                continue
            sc, terms = _platform_score(spec, c, profile)
            survivors.append({**c, "score": sc, "terms": terms})
        survivors.sort(key=lambda s: -s["score"])
        n = len(survivors) if count is None else count
        H = spec.story_height
        ladders_out = []
        for i, c in enumerate(survivors[:n]):
            base_story = 0
            top_story = max(base_story + 1, int(c["z"] // H) + 1)
            climb = c["z"] - base_story * H
            fp = ("offset" if climb > profile["fall_protection_trigger_m"]
                  else None)
            ladders_out.append({
                "x": c["x"], "y": c["y"], "from_story": base_story,
                "to_story": top_story, "facing": c["facing"],
                "id": f"{profile_name}_platform_ladder_{i}",
                "role": "maintenance_access", "ladder_type": "fixed_vertical",
                "placement_mode": "platform",
                "upper_surface": c["platform"],
                "direction": "bidirectional", "access_class": "maintenance",
                "transition": "side_step_off",
                **({"fall_protection": fp} if fp else {}),
            })
        return {"profile": profile_name, "mode": "equipment", "count": n,
                "ladders": ladders_out, "considered": len(cands),
                "rejected": rejected, "scored": survivors[:8], "notes": notes}

    if mode == "hatch":
        if not profile.get("allow_roof_hatch_ladder", False):
            notes.append(f"profile '{profile_name}' does not allow roof-hatch "
                         f"ladders")
        if not _roof_walkable(spec):
            notes.append("roof is not a walkable dismount surface -- no hatch "
                         "ladder proposed")
        cands = hatch_candidate_zones(spec, profile)
        rejected, survivors = [], []
        for c in cands:
            reason = _hatch_reject_reason(spec, c, profile)
            if reason:
                rejected.append({**c, "reason": reason})
                continue
            sc, terms = _hatch_score(spec, c, profile)
            survivors.append({**c, "score": sc, "terms": terms})
        survivors.sort(key=lambda s: -s["score"])
        n = 1 if count is None else count
        ladders_out = []
        for i, c in enumerate(survivors[:n]):
            room_story = c.get("story", spec.n_stories - 1)
            fp = ("safety_rail"
                  if (spec.n_stories - room_story) * spec.story_height
                  > profile["fall_protection_trigger_m"] else None)
            ladders_out.append({
                "x": c["x"], "y": c["y"], "from_story": room_story,
                "to_story": spec.n_stories, "facing": "S",
                "id": f"{profile_name}_hatch_ladder_{i}",
                "role": "roof_access", "ladder_type": "fixed_vertical",
                "placement_mode": "interior",
                "lower_surface": c["room"], "upper_surface": "roof",
                "direction": "bidirectional", "access_class": "staff_restricted",
                "transition": "roof_hatch_exit",
                **({"fall_protection": fp} if fp else {}),
                "access_control": profile.get("default_access_control")
                or "locked_hatch",
            })
        return {"profile": profile_name, "mode": "hatch", "count": n,
                "ladders": ladders_out, "considered": len(cands),
                "rejected": rejected, "scored": survivors[:8], "notes": notes}

    if not profile.get("allow_exterior_roof_ladder", False):
        notes.append(f"profile '{profile_name}' does not allow exterior roof "
                     f"ladders -- prefer an interior roof-hatch ladder "
                     f"(ladder spec Phase 3)")
    if not _roof_walkable(spec):
        notes.append("roof is not a walkable dismount surface (roof='none' or "
                     "no stories) -- no exterior roof ladder proposed")

    cands = candidate_zones(spec, profile)
    rejected, survivors = [], []
    for c in cands:
        reason = reject_reason(spec, c, profile)
        if reason:
            rejected.append({**c, "reason": reason})
            continue
        sc, terms = score_candidate(spec, c, profile)
        survivors.append({**c, "score": sc, "terms": terms})
    survivors.sort(key=lambda s: -s["score"])

    n = 1 if count is None else count
    chosen = survivors[:n]
    climb = spec.n_stories * spec.story_height
    ladders_out = []
    for i, c in enumerate(chosen):
        tt, step = _select_transition(spec, c)
        fp = ("safety_rail" if climb > profile["fall_protection_trigger_m"]
              else None)
        ladders_out.append({
            "x": c["x"], "y": c["y"], "from_story": 0,
            "to_story": spec.n_stories, "facing": c["facing"],
            "id": f"{profile_name}_roof_ladder_{i}",
            "role": profile["default_role"],
            "ladder_type": "fixed_vertical", "placement_mode": "exterior_wall",
            "lower_surface": "grade", "upper_surface": "roof",
            "direction": "bidirectional",
            "access_class": ("staff_restricted"
                             if profile.get("restrict_public_access")
                             else "maintenance"),
            "transition": tt,
            **({"fall_protection": fp} if fp else {}),
            **({"access_control": profile["default_access_control"]}
               if profile.get("default_access_control") else {}),
        })

    return {"profile": profile_name, "mode": "exterior", "count": n,
            "ladders": ladders_out,
            "considered": len(cands), "rejected": rejected,
            "scored": survivors[:8], "notes": notes}


def _report(p):
    lines = [f"ladder placement proposal -- profile '{p['profile']}' "
             f"[{p.get('mode', 'exterior')}]",
             f"  candidates considered: {p['considered']}   "
             f"rejected: {len(p['rejected'])}   target: {p['count']}"]
    for n in p["notes"]:
        lines.append(f"  NOTE: {n}")
    for r in p["rejected"]:
        loc = r.get("wall") or r.get("room") or r.get("platform") or "?"
        lines.append(f"  rejected {loc} ({r['x']}, {r['y']}): {r['reason']}")
    for s in p["scored"]:
        loc = s.get("wall") or s.get("room") or s.get("platform") or "?"
        extra = (f"rear={s['is_rear']} front={s['is_front']}"
                 if "is_rear" in s else f"role={s.get('role', '')}")
        lines.append(f"  scored   {loc} ({s['x']}, {s['y']}): "
                     f"{s['score']}  {extra}")
    if p.get("fire_escapes"):
        lines.append("proposed fire escapes (paste into the spec's "
                     "\"fire_escapes\" section):")
        lines.append(json.dumps(p["fire_escapes"], indent=2))
    lines.append("proposed ladders (paste into the spec's \"ladders\" "
                 "section):")
    lines.append(json.dumps(p["ladders"], indent=2))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec")
    ap.add_argument("--profile", required=True, choices=sorted(PROFILES))
    ap.add_argument("--mode",
                    choices=["exterior", "hatch", "equipment", "fire_escape"],
                    default="exterior",
                    help="exterior wall / interior roof-hatch / equipment "
                         "platform / legacy fire-escape system")
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--write", action="store_true",
                    help="inject the proposal (refused if ladders exist)")
    ap.add_argument("--replace", action="store_true",
                    help="with --write: replace an existing ladders section")
    args = ap.parse_args()

    from spec_loader import load_spec
    spec = load_spec(args.spec)
    proposal = propose(spec, args.profile, count=args.count, mode=args.mode)
    print(_report(proposal))

    if args.write:
        fes = proposal.get("fire_escapes", [])
        if not proposal["ladders"] and not fes:
            raise SystemExit("REFUSED: nothing proposed (see notes above).")
        with open(args.spec, "r", encoding="utf-8") as f:
            data = json.load(f)
        if (data.get("ladders") or data.get("fire_escapes")) \
                and not args.replace:
            raise SystemExit("REFUSED: spec already has ladders/fire escapes; "
                             "re-run with --replace to overwrite deliberately.")
        if fes:
            data["fire_escapes"] = fes
        data["ladders"] = proposal["ladders"]
        with open(args.spec, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"\nwrote {len(fes)} fire escape(s) + {len(proposal['ladders'])} "
              f"ladder(s) into {args.spec} -- run validate.py to gate it.")


if __name__ == "__main__":
    main()
