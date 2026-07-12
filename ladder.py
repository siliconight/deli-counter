"""
ladder.py  --  semantic ladder connections + offline access review (no Blender)
===============================================================================
Phase 1 of docs/deli_counter_ladder_placement_spec.md: a ladder stops being
decoration on a blank wall and becomes a SYSTEM -- a specialized connection
between two usable surfaces, with a role, a safe lower approach, a resolved top
transition, a preserved climbing volume, and a route at both ends. Reviewed
offline at room-graph + surface resolution and emitted into
shell.gameplay.json as `ladders` (spec s14).

The governing rule (spec s1, s23):

    A ladder is a specialized connection between two usable surfaces. It must
    have a defined purpose, a safe approach, a safe transition at the top, and
    enough surrounding clearance to be climbed.

Like stairwell.py this is a PROXY, not the truth. It resolves surfaces from
rooms and derived tokens (roof / grade / pit), checks the climb envelope
against doors/windows/volumes, and validates the route graph -- but it cannot
see hatch covers, parapet crossovers modeled in art, or weather. A pass means
"nothing in the spec breaks the ladder-access contract", not "safe to climb".

SEVERITY: unlike stairs (where an unclassified stair is intel), a ladder with
NO role is a hard error (Rule 1 -- a ladder without a role is not generated).
Everything else follows the spec's s15 error/warning split verbatim, and the
spec's §2 invariant is absolute: a ladder is never counted as ordinary
required egress, no matter what it's labeled.
"""

import math

import tactical

# ---------------------------------------------------------------------------
# Vocabulary (spec s2, s6)
# ---------------------------------------------------------------------------

LADDER_ROLES = {
    "not_egress", "service_access", "maintenance_access", "roof_access",
    "rooftop_connector", "legacy_secondary_escape", "fire_escape_termination",
    "special_gameplay_route",
}
# roles for which counts_as_secondary_escape may be true (spec s13.3)
ESCAPE_ROLES = {"legacy_secondary_escape", "fire_escape_termination"}

TRANSITIONS = {
    "through_step_off", "side_step_off", "roof_hatch_exit", "parapet_cut_through",
    "parapet_crossover_platform", "parapet_inside_ladder", "platform_gate_entry",
    "fire_escape_platform_entry",
}

# geometry defaults (spec s10), meters
FALL_PROTECTION_TRIGGER_M = 7.30
LOWER_CLEAR_W = 1.20
LOWER_CLEAR_D = 1.20
CLIMB_HEAD_CLEAR = 2.20
GAMEPLAY_MOUNT_W = 0.80
RUNG_SPACING_MIN = 0.25
RUNG_SPACING_MAX = 0.36
FIXED_CLEAR_WIDTH_MIN = 0.41
GAMEPLAY_LOW_CLEAR = 0.50

DERIVED_SURFACES = {"roof", "grade", "site", "ground"}


# ---------------------------------------------------------------------------
# Geometry + surface helpers
# ---------------------------------------------------------------------------

def ladder_ident(ld, i):
    return getattr(ld, "id", None) or f"ladder_{i}"


def _climb_z(spec, ld):
    H = spec.story_height
    lo = min(ld.from_story, ld.to_story)
    hi = max(ld.from_story, ld.to_story)
    return lo * H, hi * H


def climb_height(spec, ld):
    z0, z1 = _climb_z(spec, ld)
    return z1 - z0


def climb_rect(ld):
    """XY rect the climbing volume + mount zone reserves. The rails sit against
    the wall the climber faces; the body + mount clearance extend outward from
    that wall into the space, so the reserved rect is the wider gameplay mount
    envelope, not just the rail width."""
    half = max(ld.width, GAMEPLAY_MOUNT_W) / 2
    reach = max(ld.depth + 1.0, 1.2)      # body + mount depth off the wall
    if ld.facing in ("N", "S"):
        # climber faces N/S: rails spread along X, body extends along Y
        dy = reach if ld.facing == "N" else -reach
        return (ld.x - half, min(ld.y, ld.y + dy),
                ld.x + half, max(ld.y, ld.y + dy))
    dx = reach if ld.facing == "E" else -reach
    return (min(ld.x, ld.x + dx), ld.y - half,
            max(ld.x, ld.x + dx), ld.y + half)


def _surface_story(spec, token, default_story):
    """Resolve a surface token to a story index, or None if it names a room
    that doesn't exist / a token we can't place."""
    if token is None:
        return default_story
    if token in ("roof",):
        return spec.n_stories
    if token in ("grade", "ground", "site"):
        return 0
    if token.startswith("pit_"):
        try:
            return -int(token.split("_", 1)[1])
        except ValueError:
            return None
    for r in spec.rooms:
        if r.id == token:
            return r.story
    return None


def _room_by_id(spec, rid):
    for r in spec.rooms:
        if r.id == rid:
            return r
    return None


def _surface_valid(spec, token, story):
    """Is this surface a real, usable standing surface at `story`?"""
    if token in DERIVED_SURFACES or (token or "").startswith("pit_"):
        if token == "roof":
            return spec.n_stories >= 1        # a roof exists
        return True                           # grade/site/pit are standing ground
    r = _room_by_id(spec, token)
    return r is not None and r.story == story


def _same_story_edges(spec, adj):
    story_of = {r.id: r.story for r in spec.rooms}
    out = {rid: set() for rid in adj}
    for a, nbrs in adj.items():
        for b in nbrs:
            if story_of.get(a) == story_of.get(b):
                out[a].add(b)
    return out


def _has_onward_route(spec, flat, token, story):
    """Does this surface connect onward (Rule 2: a valid route leads to/from
    it)? Derived surfaces (roof/grade/site) are onward by definition -- open
    space. A room needs at least one same-story neighbor OR an exterior door."""
    if token in DERIVED_SURFACES or (token or "").startswith("pit_"):
        return True
    r = _room_by_id(spec, token)
    if r is None:
        return False
    if flat.get(token):
        return True
    # a room that is itself an exterior-door room is onward (leads outside)
    return token in _exterior_rooms(spec, story)


def _exterior_rooms(spec, story):
    dests = set()
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    for w in spec.ext_walls:
        if w.story != story:
            continue
        run = spec.footprint_x if w.wall in ("N", "S") else spec.footprint_y
        eps = 0.8
        for op in w.openings:
            if op.kind not in ("door", "garage", "breach"):
                continue
            u = op.pos * run
            if w.wall == "N":
                rid = tactical._room_at(spec, story, u, hy - eps)
            elif w.wall == "S":
                rid = tactical._room_at(spec, story, u, -hy + eps)
            elif w.wall == "E":
                rid = tactical._room_at(spec, story, hx - eps, u)
            else:
                rid = tactical._room_at(spec, story, -hx + eps, u)
            if rid:
                dests.add(rid)
    return dests


def _openings_in_climb(spec, ld, rect, served_stories):
    """Doors/windows whose leaf sits inside the climb envelope (Rule 8/9,
    anti-patterns 'window ladder' / 'door collision'). Returns list of
    (kind, story, x, y)."""
    hits = []
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    for w in spec.ext_walls:
        if w.story not in served_stories:
            continue
        run = spec.footprint_x if w.wall in ("N", "S") else spec.footprint_y
        for op in w.openings:
            u = op.pos * run
            if w.wall == "N":
                px, py = u, hy
            elif w.wall == "S":
                px, py = u, -hy
            elif w.wall == "E":
                px, py = hx, u
            else:
                px, py = -hx, u
            if rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]:
                hits.append((op.kind, w.story, px, py))
    for p in getattr(spec, "partitions", []):
        if p.story not in served_stories or not p.openings:
            continue
        lo = min(p.start, p.end)
        length = abs(p.end - p.start)
        for op in p.openings:
            along = lo + (op.pos + 0.5) * length
            px, py = ((p.pos, along) if p.axis == "Y" else (along, p.pos))
            if rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]:
                hits.append((op.kind, p.story, px, py))
    return hits


def _volumes_in_climb(spec, ld, rect, z0, z1):
    """Props/equipment volumes intruding the climbing clearance (Rule 8)."""
    out = []
    for v in getattr(spec, "volumes", []):
        nm = v.name.lower()
        if any(k in nm for k in ("ladder", "rung", "rail")):
            continue
        vr = (v.x - v.size_x / 2, v.y - v.size_y / 2,
              v.x + v.size_x / 2, v.y + v.size_y / 2)
        ix = max(0.0, min(rect[2], vr[2]) - max(rect[0], vr[0]))
        iy = max(0.0, min(rect[3], vr[3]) - max(rect[1], vr[1]))
        if ix * iy > 0.05 and not (v.z + v.size_z / 2 < z0
                                   or v.z - v.size_z / 2 > z1 + CLIMB_HEAD_CLEAR):
            out.append(v.name)
    return out


# ---------------------------------------------------------------------------
# Derivation: LevelSpec -> ladders[] (gameplay.json s14)
# ---------------------------------------------------------------------------

def derive(spec):
    """One semantic dict per Ladder: identity, role, connected surfaces,
    mount/dismount anchors, climb geometry, transition, direction, access,
    egress classification (always excluded unless an escape role opts in), and
    the derived route nodes (spec s13.1). Pure and offline-derivable."""
    ladders = []
    H = spec.story_height
    for i, ld in enumerate(spec.ladders):
        lid = ladder_ident(ld, i)
        z0, z1 = _climb_z(spec, ld)
        lo_story = min(ld.from_story, ld.to_story)
        hi_story = max(ld.from_story, ld.to_story)
        role = getattr(ld, "role", None)
        lower = getattr(ld, "lower_surface", None)
        upper = getattr(ld, "upper_surface", None)
        rect = climb_rect(ld)
        h = z1 - z0
        counts_escape = bool(getattr(ld, "counts_as_secondary_escape", False)) \
            and role in ESCAPE_ROLES
        d = {
            "id": lid,
            "role": role,
            "ladder_type": getattr(ld, "ladder_type", "fixed_vertical"),
            "placement_mode": getattr(ld, "placement_mode", "interior"),
            "lower_surface": lower if lower is not None else f"story_{lo_story}",
            "upper_surface": upper if upper is not None else (
                "roof" if hi_story >= spec.n_stories else f"story_{hi_story}"),
            "lower_anchor": [ld.x, ld.y, z0],
            "upper_anchor": [ld.x, ld.y, z1],
            "climb_height_m": round(h, 3),
            "direction": getattr(ld, "direction", "bidirectional"),
            "access_class": getattr(ld, "access_class", "staff_restricted"),
            "egress_classification": (role if role in ESCAPE_ROLES
                                      and counts_escape else "not_egress"),
            "counts_as_primary_egress": False,
            "counts_as_secondary_escape": counts_escape,
            "counts_as_public_circulation": False,
            "transition": {
                "type": getattr(ld, "transition", None)
                or ("roof_hatch_exit" if hi_story >= spec.n_stories
                    and getattr(ld, "placement_mode", "interior") == "interior"
                    else "through_step_off"),
            },
            "geometry": {
                "clear_width_m": ld.width,
                "rung_spacing_m": ld.rung_spacing,
                "rung_center_to_wall_m": ld.depth,
                "climb_rect": [[rect[0], rect[1]], [rect[2], rect[1]],
                               [rect[2], rect[3]], [rect[0], rect[3]]],
            },
            "fall_protection": {
                "required": h > FALL_PROTECTION_TRIGGER_M,
                "type": getattr(ld, "fall_protection", None) or "none",
            },
            "access_control": {
                "type": getattr(ld, "access_control", None) or "none",
            },
            "route_nodes": {
                "lower_approach": [ld.x, ld.y, z0],
                "lower_mount": [ld.x, ld.y, z0 + 0.1],
                "climb_start": [ld.x, ld.y, z0 + 0.3],
                "climb_end": [ld.x, ld.y, z1 - 0.3],
                "upper_dismount": [ld.x, ld.y, z1],
                "upper_route": [ld.x, ld.y, z1],
            },
            "gameplay": {
                "player_traversable": True,
                "ai_traversable": getattr(ld, "direction", "bidirectional")
                != "scripted_direction",
                "server_authoritative_state": True,
                "interaction_required": getattr(ld, "access_control", None)
                not in (None, "none"),
                "mount_anchor_id": f"{lid}_mount",
                "dismount_anchor_id": f"{lid}_dismount",
                "occupancy_limit": 1,
            },
        }
        meta = getattr(ld, "meta", None)
        if meta:
            d["meta"] = meta
            d["gameplay"].update(meta.get("gameplay", {}))
        ladders.append(d)
    return ladders


# ---------------------------------------------------------------------------
# Review: check(spec) -> (errors, warnings, summary)
# ---------------------------------------------------------------------------

def check(spec):
    errors, warnings = [], []
    have_rooms = bool(spec.rooms)
    flat = _same_story_edges(spec, tactical.build_graph(spec)) if have_rooms else {}
    systems = derive(spec)
    counts = {"total": len(systems), "escape": 0}

    for ld, d in zip(spec.ladders, systems):
        lid = d["id"]
        role = d["role"]

        # Rule 1 -- a ladder without a role is not generated (HARD)
        if role is None:
            errors.append(
                f"LADDER LADDER_NO_ROLE: '{lid}' has no role -- a ladder is a "
                f"specialized connection with a declared purpose, never "
                f"decoration (Rule 1). Set one of "
                f"{', '.join(sorted(LADDER_ROLES))}.")
            continue
        if role not in LADDER_ROLES:
            errors.append(
                f"LADDER LADDER_NO_ROLE: '{lid}' has unknown role '{role}' "
                f"(known: {', '.join(sorted(LADDER_ROLES))}).")
            continue

        lo_story = min(ld.from_story, ld.to_story)
        hi_story = max(ld.from_story, ld.to_story)
        lower = getattr(ld, "lower_surface", None)
        upper = getattr(ld, "upper_surface", None)
        z0, z1 = _climb_z(spec, ld)
        rect = climb_rect(ld)
        served = set(range(lo_story, hi_story + 1))

        # Rule 2 -- two real, traversable surfaces
        lo_ok = lower is None or _surface_valid(spec, lower, lo_story)
        hi_ok = upper is None or _surface_valid(
            spec, upper, spec.n_stories if hi_story >= spec.n_stories
            else hi_story)
        if not lo_ok:
            errors.append(
                f"LADDER LADDER_NO_LOWER_SURFACE: '{lid}' lower surface "
                f"'{lower}' is not a usable standing surface at story "
                f"{lo_story} (Rule 2).")
        if not hi_ok:
            errors.append(
                f"LADDER LADDER_NO_UPPER_SURFACE: '{lid}' upper surface "
                f"'{upper}' is not a walkable dismount surface (Rule 2).")
        # LADDER_TO_NOWHERE: no upper destination declared and the top isn't a
        # roof / known surface -- decoration to nowhere (anti-pattern s18)
        if upper is None and hi_story < spec.n_stories \
                and not any(r.story == hi_story for r in spec.rooms):
            errors.append(
                f"LADDER LADDER_TO_NOWHERE: '{lid}' climbs to story "
                f"{hi_story} but nothing walkable exists there and no "
                f"upper_surface is declared (anti-pattern: ladder to nowhere).")

        # Rule 2 -- onward route at both ends (LADDER_ROUTE_DISCONNECTED)
        if have_rooms and lo_ok and hi_ok:
            if lower is not None and not _has_onward_route(
                    spec, flat, lower, lo_story):
                errors.append(
                    f"LADDER LADDER_ROUTE_DISCONNECTED: '{lid}' lower surface "
                    f"'{lower}' connects to nothing onward -- a valid route "
                    f"must lead to the ladder base (Rule 2).")
            if upper is not None and not _has_onward_route(
                    spec, flat, upper,
                    spec.n_stories if hi_story >= spec.n_stories else hi_story):
                warnings.append(
                    f"LADDER LADDER_NO_VISUAL_DESTINATION: '{lid}' upper "
                    f"surface '{upper}' has no onward route -- the dismount "
                    f"is valid but leads nowhere useful (s15.2).")

        # Rule 8 -- climbing volume clear of fixed geometry
        blockers = _volumes_in_climb(spec, ld, rect, z0, z1)
        if blockers:
            errors.append(
                f"LADDER LADDER_CLIMB_VOLUME_BLOCKED: '{lid}' climb envelope "
                f"is intruded by {', '.join(blockers)} -- the climbing volume "
                f"is reserved space (Rule 8).")

        # Rule 9 -- door/window conflict in the climb zone
        for kind, story, px, py in _openings_in_climb(spec, ld, rect, served):
            if kind == "door" or kind == "garage" or kind == "breach":
                # a fire-escape ladder MAY align with a tagged escape window
                if role in ESCAPE_ROLES and getattr(ld, "fire_escape_id", None):
                    continue
                errors.append(
                    f"LADDER LADDER_DOOR_CONFLICT: '{lid}' climb/mount zone "
                    f"contains a {kind} at story {story} ({px:.1f}, {py:.1f}) "
                    f"-- a door swing into the ladder traps the climber "
                    f"(Rule 9).")
            elif kind == "window":
                if role in ESCAPE_ROLES and getattr(ld, "fire_escape_id", None):
                    continue     # intentional fire-escape window relationship
                warnings.append(
                    f"LADDER LADDER_WINDOW_CONFLICT: '{lid}' climb zone "
                    f"crosses a window at story {story} -- ladders over "
                    f"windows read as accidental unless it's a tagged fire "
                    f"escape (Rule 9 / anti-pattern 'window ladder').")

        # Rule 5/6 -- top transition explicitly resolved
        tt = d["transition"]["type"]
        if tt not in TRANSITIONS:
            warnings.append(
                f"LADDER: '{lid}' transition '{tt}' is not one of the "
                f"resolved types ({', '.join(sorted(TRANSITIONS))}); the top "
                f"step-off may be undefined (Rule 5).")
        if hi_story >= spec.n_stories and getattr(spec, "parapets", None) \
                and any(p.story >= spec.n_stories - 1 for p in spec.parapets) \
                and tt not in ("parapet_cut_through", "parapet_crossover_platform",
                               "parapet_inside_ladder", "roof_hatch_exit"):
            emit_gate = role in ESCAPE_ROLES
            msg = (f"'{lid}' reaches a roof with a parapet but its transition "
                   f"'{tt}' has no crossover -- the climber lands outside the "
                   f"parapet with no way over (Rule 6 / PARAPET_CROSSOVER_"
                   f"MISSING).")
            (errors if emit_gate else warnings).append(
                f"LADDER PARAPET_CROSSOVER_MISSING: {msg}")

        # Rule 11 -- long climb needs a fall-protection profile
        h = z1 - z0
        if h > FALL_PROTECTION_TRIGGER_M \
                and (getattr(ld, "fall_protection", None) in (None, "none")):
            errors.append(
                f"LADDER LADDER_LONG_CLIMB_UNPROTECTED: '{lid}' climbs "
                f"{h:.1f} m (> {FALL_PROTECTION_TRIGGER_M} m) with no "
                f"fall_protection -- add safety_rail, cage, rest_platform, or "
                f"offset (Rule 11).")

        # s2 invariant -- never ordinary egress; escape only via escape role
        if getattr(ld, "counts_as_secondary_escape", False) \
                and role not in ESCAPE_ROLES:
            errors.append(
                f"LADDER LADDER_INVALID_EGRESS: '{lid}' sets "
                f"counts_as_secondary_escape but role '{role}' is not an "
                f"escape role -- a ladder is not ordinary egress (spec s2); "
                f"only legacy_secondary_escape / fire_escape_termination may "
                f"opt in.")
        if d["counts_as_secondary_escape"]:
            counts["escape"] += 1
            warnings.append(
                f"LADDER LEGACY_FIRE_ESCAPE_PROFILE: '{lid}' counts as "
                f"secondary escape -- this depends on an existing-building "
                f"exception; confirm the profile allows it (s15.2).")

        # Rule 14 -- fire-escape ladder must belong to a platform system
        if role == "fire_escape_termination" \
                and not getattr(ld, "fire_escape_id", None):
            errors.append(
                f"LADDER FIRE_ESCAPE_LADDER_ORPHANED: '{lid}' is a "
                f"fire-escape termination with no fire_escape_id -- an "
                f"isolated ladder on a window is not a fire escape (Rule 14).")

        # Rule 13 -- restricted role publicly reachable (intel)
        if role in ("roof_access", "maintenance_access", "service_access") \
                and getattr(ld, "access_class", "") == "public" \
                and getattr(ld, "access_control", None) in (None, "none"):
            warnings.append(
                f"LADDER LADDER_SECURITY_EXPOSURE: '{lid}' is a restricted "
                f"'{role}' ladder but is publicly accessible with no access "
                f"control (Rule 13).")

        # s10 -- geometry sanity (intel)
        if not (RUNG_SPACING_MIN <= ld.rung_spacing <= RUNG_SPACING_MAX):
            warnings.append(
                f"LADDER: '{lid}' rung_spacing {ld.rung_spacing:.2f} m is "
                f"outside the plausible {RUNG_SPACING_MIN}-{RUNG_SPACING_MAX} "
                f"m range (s10).")
        if ld.width < GAMEPLAY_LOW_CLEAR:
            warnings.append(
                f"LADDER LADDER_LOW_GAMEPLAY_CLEARANCE: '{lid}' clear width "
                f"{ld.width:.2f} m meets the technical minimum but may feel "
                f"cramped for first-person traversal (s10.4).")

        # excessive climb for the context (intel)
        if h > 3 * spec.story_height:
            warnings.append(
                f"LADDER LADDER_EXCESSIVE_HEIGHT: '{lid}' climbs {h:.1f} m "
                f"({h / spec.story_height:.1f} stories) -- unusually long; "
                f"consider offset sections with rest platforms (s15.2).")

    summary = {
        "ladders": counts["total"],
        "secondary_escape": counts["escape"],
        "errors": len(errors),
        "warnings": len(warnings),
        "route_analysis": "room-graph" if have_rooms else "skipped (no rooms)",
    }
    return errors, warnings, summary


def format_summary(spec_name, summary):
    return (f"  ladder systems for {spec_name}:\n"
            f"    ladders: {summary['ladders']}   secondary-escape: "
            f"{summary['secondary_escape']}   routes: "
            f"{summary['route_analysis']}   "
            f"(a ladder is never ordinary egress; this is room-graph intel)")
