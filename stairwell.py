"""
stairwell.py  --  semantic stair systems + offline egress review (no Blender)
=============================================================================
Implements Phases 1-2 of docs/stairwell_placement_spec.md: a stair stops being
an isolated mesh and becomes a SYSTEM -- role, vertical stack, per-floor
approach, and a ground-level discharge route -- reviewed offline at room-graph
resolution and emitted into shell.gameplay.json as `stair_systems`.

Like navigability, this is a PROXY, not the truth. It works on room rects and
the tactical adjacency graph, so it can say "this egress stair's only approach
is an objective room" or "no route from the stair to an exterior door exists",
but it cannot see enclosure walls, door swings, or signage. A pass here means
"nothing in the spec breaks the egress contract", not "code-compliant".

GATE THE DECLARED CONTRACT, WARN THE REST:
  - A stair that declares an EGRESS role (primary_egress / secondary_egress /
    exterior_egress) has opted into the egress contract: route findings on it
    are HARD ERRORS, and egress pairs must satisfy separation + independence.
  - An unclassified or non-egress stair gets the same findings as WARNINGS
    (intel). Every pre-0.65 spec therefore gates exactly as before.
  - A declared `stack_id` is a contract too: stairs sharing one must chain
    story ranges with overlapping footprints, or STAIR_NOT_STACKED errors.

Severity codes follow the placement spec (section 14) verbatim so a failure
reason maps straight back to the document.
"""

import math

import tactical

# ---------------------------------------------------------------------------
# Vocabulary (placement spec sections 3 and 5)
# ---------------------------------------------------------------------------

EGRESS_ROLES = {"primary_egress", "secondary_egress", "exterior_egress"}
STAIR_ROLES = EGRESS_ROLES | {
    "public_convenience", "service", "private_residential", "industrial_access",
}

# Room roles a required stair may not be approached through (Rule 3). Matched
# against Room.role; the repo's role vocabulary is free-form, so this covers
# both the spec's architectural names and the roles specs actually use.
PROHIBITED_APPROACH_ROLES = {
    "bathroom", "storage", "closet", "mechanical", "utility",
    "private_office", "kitchen", "bedroom", "objective_room",
}

# Room roles that read as circulation (a believable stair approach).
CIRCULATION_ROLES = {
    "connector", "corridor", "hall", "hallway", "lobby", "stairwell",
    "main_route", "route_node", "staging", "public_entry", "open_floor",
}

MIN_EGRESS_SEPARATION = 8.0     # m; Rule 6 game-friendly floor
DEFAULT_SEPARATION_FACTOR = 0.33  # sprinklered approximation (Rule 6)
DISCHARGE_MAX_CLEAN_HOPS = 3    # rooms between stair and exterior before warn
_TREAD_MARGIN = 0.6             # m shaved off each run end for the door test


# ---------------------------------------------------------------------------
# Geometry + graph helpers
# ---------------------------------------------------------------------------

def stair_ident(st, i):
    return getattr(st, "id", None) or f"stair_{i}"


def footprint_rect(st):
    """XY rect the stair reserves: both parallel switchback runs, or the single
    straight run. Matches the builder's _stairs() layout math."""
    x_off = 0.0 if st.style == "straight" else st.width / 2
    hx = st.width / 2 + x_off
    return (st.x - hx, st.y - st.run / 2, st.x + hx, st.y + st.run / 2)


def floors_served(spec, st):
    """Stories this stair gives access to, clamped to stories that exist.
    to_story past the top story is roof access; it is served but has no rooms."""
    base = -1 if spec.has_basement else 0
    lo, hi = sorted([st.from_story, st.to_story])
    return [s for s in range(lo, hi + 1) if base <= s <= spec.n_stories]


def _overlap_area(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy


def _rects_overlap(a, b):
    return _overlap_area(a, b) > 1e-9


def _approach_room(spec, story, st):
    """The room a body stands in to use this stair on `story`: the room
    containing the stair center, else the max-overlap room with the footprint."""
    rect = footprint_rect(st)
    best, best_area = None, 0.0
    for r in spec.rooms:
        if r.story != story:
            continue
        x0, y0, x1, y1 = r.bounds
        if x0 <= st.x <= x1 and y0 <= st.y <= y1:
            return r
        area = _overlap_area(rect, r.bounds)
        if area > best_area:
            best, best_area = r, area
    return best if best_area > 0.5 else None


def _same_story_edges(spec, adj):
    """Adjacency filtered to edges whose endpoints share a story (the graph
    from tactical.build_graph also carries vertical stair-column edges)."""
    story_of = {r.id: r.story for r in spec.rooms}
    out = {rid: set() for rid in adj}
    for a, nbrs in adj.items():
        for b in nbrs:
            if story_of.get(a) == story_of.get(b):
                out[a].add(b)
    return out


def _exterior_rooms(spec, story):
    """Rooms on `story` that ARE a discharge destination: they hold a
    grade-usable exterior opening (door/garage/breach), or they are declared
    outdoor ground (a forecourt/yard rect essentially outside the footprint)."""
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
    for r in spec.rooms:                      # outdoor ground rooms
        if r.story != story:
            continue
        x0, y0, x1, y1 = r.bounds
        ix = max(0.0, min(x1, hx) - max(x0, -hx))
        iy = max(0.0, min(y1, hy) - max(y0, -hy))
        area = max(1e-9, (x1 - x0) * (y1 - y0))
        if (ix * iy) / area < 0.1:
            dests.add(r.id)
    return dests


def _bfs_path(adj, start, dests):
    """Shortest path (list of room ids, start..dest) to any dest, or None."""
    if start in dests:
        return [start]
    prev, seen, queue = {}, {start}, [start]
    while queue:
        n = queue.pop(0)
        for m in adj.get(n, ()):
            if m in seen:
                continue
            seen.add(m)
            prev[m] = n
            if m in dests:
                path = [m]
                while path[-1] != start:
                    path.append(prev[path[-1]])
                return list(reversed(path))
            queue.append(m)
    return None


# ---------------------------------------------------------------------------
# Derivation: LevelSpec -> stair_systems (gameplay.json section 13 subset)
# ---------------------------------------------------------------------------

def derive(spec):
    """One semantic dict per Stairwell: identity, role, stack, floors served,
    reserved footprint, per-floor approach, and the ground discharge route.
    Pure and offline-derivable; the builder serializes this verbatim."""
    systems = []
    have_rooms = bool(spec.rooms)
    adj = tactical.build_graph(spec) if have_rooms else {}
    flat = _same_story_edges(spec, adj) if have_rooms else {}

    for i, st in enumerate(spec.stairs):
        rect = footprint_rect(st)
        served = floors_served(spec, st)
        role = getattr(st, "role", None)
        sysd = {
            "id": stair_ident(st, i),
            "stack_id": getattr(st, "stack_id", None),
            "role": role,
            "shape": st.style,
            "floors_served": served,
            "footprint_polygon": [[rect[0], rect[1]], [rect[2], rect[1]],
                                  [rect[2], rect[3]], [rect[0], rect[3]]],
            "clear_width_m": st.width,
            "approach": [],
            "discharge": None,
            "egress": {"counts_as_exit": role in EGRESS_ROLES},
        }
        if have_rooms:
            for s in served:
                if not any(r.story == s for r in spec.rooms):
                    continue                      # roof / unroomed story
                room = _approach_room(spec, s, st)
                sysd["approach"].append({
                    "floor": s,
                    "room": room.id if room else None,
                    "room_role": room.role if room else None,
                })
            if 0 in served and any(r.story == 0 for r in spec.rooms):
                room = _approach_room(spec, 0, st)
                if room:
                    dests = _exterior_rooms(spec, 0)
                    path = _bfs_path(flat, room.id, dests)
                    if path:
                        hops = len(path) - 1
                        if hops == 0:
                            dtype = "direct_exterior"
                        else:
                            roles = {r.id: r.role for r in spec.rooms}
                            circ = all((roles.get(rid) or "") in CIRCULATION_ROLES
                                       for rid in path[1:-1])
                            dtype = ("exit_passage"
                                     if hops <= 2 and circ else "lobby")
                        sysd["discharge"] = {
                            "floor": 0, "type": dtype, "room": room.id,
                            "via": path[1:-1], "destination": path[-1],
                            "route_hops": hops,
                        }
                    else:
                        sysd["discharge"] = {"floor": 0, "type": "none",
                                             "room": room.id, "via": [],
                                             "destination": None,
                                             "route_hops": None}
        systems.append(sysd)
    return systems


# ---------------------------------------------------------------------------
# Review: the analyzer contract  check(spec) -> (errors, warnings, summary)
# ---------------------------------------------------------------------------

def check(spec):
    errors, warnings = [], []
    systems = derive(spec)
    have_rooms = bool(spec.rooms)
    counts = {"egress": 0, "classified": 0}

    def emit(gate, code, msg):
        (errors if gate else warnings).append(f"STAIRWELL {code}: {msg}")

    same_story = {}
    if have_rooms:
        same_story = _same_story_edges(spec, tactical.build_graph(spec))
    room_by_id = {r.id: r for r in spec.rooms}

    for sysd, st in zip(systems, spec.stairs):
        sid, role = sysd["id"], sysd["role"]
        gate = role in EGRESS_ROLES
        if role:
            counts["classified"] += 1
            if role in EGRESS_ROLES:
                counts["egress"] += 1
            if role not in STAIR_ROLES:
                warnings.append(
                    f"STAIRWELL: '{sid}' has unknown role '{role}' (known: "
                    f"{', '.join(sorted(STAIR_ROLES))}); treated as unclassified.")
                gate = False

        # Rule 3 -- believable approach on every served, roomed floor
        for ap in sysd["approach"]:
            s, rid, rrole = ap["floor"], ap["room"], ap["room_role"]
            if rid is None:
                emit(gate, "STAIR_NO_CORRIDOR_CONNECTION",
                     f"'{sid}' serves story {s} but no room covers its "
                     f"footprint there -- the stair floats in unrouted space.")
                continue
            if rrole in PROHIBITED_APPROACH_ROLES:
                emit(gate, "STAIR_ACCESS_THROUGH_PROHIBITED_ROOM",
                     f"'{sid}' on story {s} is approached through "
                     f"'{rid}' (role '{rrole}') -- prohibited for a required "
                     f"stair (Rule 3).")
            elif rrole == "stairwell":
                nbrs = same_story.get(rid, set())
                if not nbrs:
                    emit(gate, "STAIR_NO_CORRIDOR_CONNECTION",
                         f"'{sid}' enclosure '{rid}' has no same-story "
                         f"connection on story {s} -- no way to reach the stair.")
                elif all((room_by_id[n].role or "") in PROHIBITED_APPROACH_ROLES
                         for n in nbrs):
                    emit(gate, "STAIR_ACCESS_THROUGH_PROHIBITED_ROOM",
                         f"'{sid}' enclosure '{rid}' on story {s} connects "
                         f"only to prohibited rooms "
                         f"({', '.join(sorted(nbrs))}).")

        # Rule 5 -- ground discharge
        d = sysd["discharge"]
        if have_rooms and 0 in sysd["floors_served"] \
                and any(r.story == 0 for r in spec.rooms):
            if d is None or d["type"] == "none":
                emit(gate, "STAIR_NO_GROUND_DISCHARGE",
                     f"'{sid}' reaches grade but no route exists from its "
                     f"ground room to any exterior door or outdoor ground.")
            elif d["route_hops"] and d["route_hops"] > DISCHARGE_MAX_CLEAN_HOPS:
                warnings.append(
                    f"STAIRWELL STAIR_DISCHARGE_ROUTE_HAS_MULTIPLE_TURNS: "
                    f"'{sid}' discharge crosses {d['route_hops']} rooms "
                    f"({' -> '.join([d['room']] + d['via'] + [d['destination']])}); "
                    f"keep it short and legible (Rule 5).")
        elif gate and have_rooms and 0 not in sysd["floors_served"] \
                and not sysd["stack_id"]:
            emit(gate, "STAIR_NO_GROUND_DISCHARGE",
                 f"egress stair '{sid}' never reaches grade (serves "
                 f"{sysd['floors_served']}) and declares no stack_id chaining "
                 f"it to a stair that does.")

        # Rule 8 -- basement continuation past the discharge floor
        if gate and sysd["floors_served"] and min(sysd["floors_served"]) < 0 \
                and 0 in sysd["floors_served"]:
            warnings.append(
                f"STAIRWELL BASEMENT_CONTINUATION_NOT_INTERRUPTED: egress "
                f"stair '{sid}' runs through grade into the basement in one "
                f"shaft; offline review can't see a barrier -- make sure the "
                f"grade landing interrupts descent (Rule 8).")

        # Rule 4 / 9 -- a door landing on the treads (footprint approximation)
        tread = footprint_rect(st)
        tread = (tread[0], tread[1] + _TREAD_MARGIN,
                 tread[2], tread[3] - _TREAD_MARGIN)
        for p in spec.partitions:
            if p.story not in sysd["floors_served"]:
                continue
            lo = min(p.start, p.end)
            length = abs(p.end - p.start)
            for op in p.openings:
                if op.kind not in ("door", "breach", "garage"):
                    continue
                along = lo + (op.pos + 0.5) * length
                px, py = ((p.pos, along) if p.axis == "Y" else (along, p.pos))
                if tread[0] <= px <= tread[2] and tread[1] <= py <= tread[3]:
                    warnings.append(
                        f"STAIRWELL STAIR_DOOR_OPENS_ONTO_TREAD: a {op.kind} "
                        f"in partition @story {p.story} sits over '{sid}' "
                        f"mid-run at ({px:.1f}, {py:.1f}) -- doors belong on "
                        f"landings, never treads (Rule 4).")

    # Rule 2 -- declared stacks must actually stack
    stacks = {}
    for sysd, st in zip(systems, spec.stairs):
        if sysd["stack_id"]:
            stacks.setdefault(sysd["stack_id"], []).append((sysd, st))
    for stack_id, members in stacks.items():
        members.sort(key=lambda m: min(m[1].from_story, m[1].to_story))
        for (sa, a), (sb, b) in zip(members, members[1:]):
            a_hi = max(a.from_story, a.to_story)
            b_lo = min(b.from_story, b.to_story)
            if b_lo > a_hi:
                errors.append(
                    f"STAIRWELL STAIR_NOT_STACKED: stack '{stack_id}' has a "
                    f"story gap between '{sa['id']}' (top {a_hi}) and "
                    f"'{sb['id']}' (bottom {b_lo}).")
            if not _rects_overlap(footprint_rect(a), footprint_rect(b)):
                errors.append(
                    f"STAIRWELL STAIR_NOT_STACKED: stack '{stack_id}' members "
                    f"'{sa['id']}' and '{sb['id']}' have disjoint footprints "
                    f"-- the stair teleports laterally between floors (Rule 2).")
    # Rules 6-7 -- egress pairs: separation + route independence
    egress = [(sysd, st) for sysd, st in zip(systems, spec.stairs)
              if sysd["role"] in EGRESS_ROLES]
    factor = getattr(spec, "separation_factor", DEFAULT_SEPARATION_FACTOR)
    diag = math.hypot(spec.footprint_x, spec.footprint_y)
    required = max(MIN_EGRESS_SEPARATION, diag * factor)
    for i, (sa, a) in enumerate(egress):
        for sb, b in egress[i + 1:]:
            dist = math.hypot(a.x - b.x, a.y - b.y)
            if dist < required:
                errors.append(
                    f"STAIRWELL REQUIRED_STAIRS_TOO_CLOSE: egress stairs "
                    f"'{sa['id']}' and '{sb['id']}' are {dist:.1f} m apart; "
                    f"required >= {required:.1f} m "
                    f"(max(8.0, {diag:.1f} m diagonal x {factor}), Rule 6).")
            if have_rooms and sa["discharge"] and sb["discharge"] \
                    and sa["discharge"]["type"] != "none" \
                    and sb["discharge"]["type"] != "none":
                ra, rb = sa["discharge"]["room"], sb["discharge"]["room"]
                if ra == rb:
                    errors.append(
                        f"STAIRWELL REQUIRED_ROUTES_SHARE_SINGLE_CHOKEPOINT: "
                        f"egress stairs '{sa['id']}' and '{sb['id']}' are both "
                        f"entered from '{ra}' at grade -- one blocked room "
                        f"kills both routes (Rule 7).")
                else:
                    choke = _shared_chokepoint(spec, same_story, ra, rb)
                    if choke:
                        errors.append(
                            f"STAIRWELL REQUIRED_ROUTES_SHARE_SINGLE_CHOKEPOINT: "
                            f"removing room '{choke}' severs BOTH egress "
                            f"discharge routes ('{sa['id']}' and '{sb['id']}') "
                            f"-- routes must stay independently usable (Rule 7).")

    summary = {
        "systems": len(systems),
        "egress": counts["egress"],
        "classified": counts["classified"],
        "errors": len(errors),
        "warnings": len(warnings),
        "route_analysis": "room-graph" if have_rooms else "skipped (no rooms)",
    }
    return errors, warnings, summary


def _shared_chokepoint(spec, same_story, room_a, room_b):
    """A single grade-story room (not either stair room, not a destination)
    whose removal disconnects BOTH stair rooms from every exterior destination.
    Returns the room id, or None."""
    dests = _exterior_rooms(spec, 0)
    grade = [r.id for r in spec.rooms if r.story == 0]
    for cand in grade:
        if cand in (room_a, room_b) or cand in dests:
            continue
        adj = {k: {m for m in v if m != cand}
               for k, v in same_story.items() if k != cand}
        if _bfs_path(adj, room_a, dests) is None \
                and _bfs_path(adj, room_b, dests) is None:
            return cand
    return None


def format_summary(spec_name, summary):
    return (f"  stairwell systems for {spec_name}:\n"
            f"    systems: {summary['systems']}   egress-role: "
            f"{summary['egress']}   classified: {summary['classified']}   "
            f"routes: {summary['route_analysis']}   "
            f"(authoritative check = walk it; this is room-graph intel)")
