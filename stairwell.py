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
    """XY rect the stair reserves, style-aware and rotated by `facing`.
    Matches the builder's layout math: switchback/scissor hold two parallel
    runs, straight one, an L bounds both perpendicular legs + corner, and a
    spiral is a disc of radius `width`."""
    w, run = st.width, st.run
    style = st.style
    if style == "spiral":
        lx0, ly0, lx1, ly1 = -w, -w, w, w
    elif style == "l_shaped":
        lx0, ly0 = -w / 2, -run / 2
        lx1, ly1 = w / 2 + run, run / 2 + w
    elif style == "straight":
        lx0, ly0, lx1, ly1 = -w / 2, -run / 2, w / 2, run / 2
    else:                        # switchback, scissor: two parallel runs
        lx0, ly0, lx1, ly1 = -w, -run / 2, w, run / 2
    f = getattr(st, "facing", "N") or "N"
    if f == "S":
        lx0, ly0, lx1, ly1 = -lx1, -ly1, -lx0, -ly0
    elif f == "E":               # local (x, y) -> world (y, -x)
        lx0, ly0, lx1, ly1 = ly0, -lx1, ly1, -lx0
    elif f == "W":               # local (x, y) -> world (-y, x)
        lx0, ly0, lx1, ly1 = -ly1, lx0, -ly0, lx1
    return (st.x + lx0, st.y + ly0, st.x + lx1, st.y + ly1)


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


def _ext_openings(spec, story):
    """Yield (wall_name, opening, inside_room_id) for every grade-usable
    exterior opening (door/garage/breach) on `story`."""
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
            yield f"ext_{story}_{w.wall}", op, rid


def _exterior_rooms(spec, story):
    """Rooms on `story` that ARE a discharge destination: they hold a
    grade-usable exterior opening (door/garage/breach), or they are declared
    outdoor ground (a forecourt/yard rect essentially outside the footprint)."""
    dests = set()
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    for _, _, rid in _ext_openings(spec, story):
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
# Phase 4: door nodes + gameplay/network semantics (spec s9.3, s13)
# ---------------------------------------------------------------------------

_DOOR_KINDS = ("door", "garage", "breach", "vault")
_AI_COST_ENCLOSED = 1.15     # s13 example: enclosed stairs cost AI a little more
_AGENT_PASS_WIDTH = 0.7      # capsule pass band (docs/scale_guidelines.md)


def _door_nodes(spec, st, served):
    """The doors a body moves through to use this stair: every partition
    opening with the stair's approach room on one side (per served, roomed
    story), plus the approach room's exterior doors at grade (discharge).
    `interactive` carries the SAME stable id the builder bakes -- computed
    through interactives.derive_interactive on the same wall-name convention
    (int_{story}_{index} / ext_{story}_{wall}) -- so netcode, slots, and this
    egress contract all key on one id."""
    import interactives
    nodes = []
    if not spec.rooms:
        return nodes
    for s in served:
        if not any(r.story == s for r in spec.rooms):
            continue
        room = _approach_room(spec, s, st)
        if room is None:
            continue
        for i, p in enumerate(spec.partitions):
            if p.story != s or not p.openings:
                continue
            eps = 0.6
            lo = min(p.start, p.end)
            length = abs(p.end - p.start)
            for op in p.openings:
                if op.kind not in _DOOR_KINDS:
                    continue
                along = lo + (op.pos + 0.5) * length
                if p.axis == "Y":
                    a = tactical._room_at(spec, s, p.pos - eps, along)
                    b = tactical._room_at(spec, s, p.pos + eps, along)
                else:
                    a = tactical._room_at(spec, s, along, p.pos - eps)
                    b = tactical._room_at(spec, s, along, p.pos + eps)
                if room.id not in (a, b):
                    continue
                wall = f"int_{p.story}_{i}"
                m = interactives.derive_interactive(
                    spec.name, wall, s, op.kind, op.pos,
                    breakable=bool(op.breakable), override=op.interactive)
                nodes.append({
                    "floor": s, "kind": op.kind, "wall": wall, "pos": op.pos,
                    "interactive": m["id"] if m else None,
                    "default_state": (m or {}).get("default"),
                    "connects_from": (b if a == room.id else a),
                    "discharge_door": False,
                })
        if s == 0:
            for wall, op, rid in _ext_openings(spec, 0):
                if rid != room.id:
                    continue
                m = interactives.derive_interactive(
                    spec.name, wall, 0, op.kind, op.pos,
                    breakable=bool(op.breakable), override=op.interactive)
                nodes.append({
                    "floor": 0, "kind": op.kind, "wall": wall, "pos": op.pos,
                    "interactive": m["id"] if m else None,
                    "default_state": (m or {}).get("default"),
                    "connects_from": "exterior",
                    "discharge_door": True,
                })
    return nodes


def _tower_wall(spec, st):
    """The facade an exterior tower stands against: the nearest wall plane."""
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    d = {"N": abs(st.y - hy), "S": abs(st.y + hy),
         "E": abs(st.x - hx), "W": abs(st.x + hx)}
    return min(d, key=lambda k: d[k])


def _tower_door_nodes(spec, st, served):
    """Facade doors within lateral reach of an exterior tower, per served
    story (spec s8.4: corridor -> door -> tower -> grade). These ARE the
    tower's approach; grade needs no door because the tower discharges onto
    the site itself."""
    import interactives
    wall = _tower_wall(spec, st)
    rect = footprint_rect(st)
    reach = max(rect[2] - rect[0], rect[3] - rect[1]) / 2 + 2.0
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    nodes = []
    for s in served:
        for w in spec.ext_walls:
            if w.story != s or w.wall != wall:
                continue
            run = spec.footprint_x if wall in ("N", "S") else spec.footprint_y
            for op in w.openings:
                if op.kind not in _DOOR_KINDS:
                    continue
                u = op.pos * run
                lateral = abs(u - (st.x if wall in ("N", "S") else st.y))
                if lateral > reach:
                    continue
                eps = 0.8
                if wall == "N":
                    rid = tactical._room_at(spec, s, u, hy - eps)
                elif wall == "S":
                    rid = tactical._room_at(spec, s, u, -hy + eps)
                elif wall == "E":
                    rid = tactical._room_at(spec, s, hx - eps, u)
                else:
                    rid = tactical._room_at(spec, s, -hx + eps, u)
                m = interactives.derive_interactive(
                    spec.name, f"ext_{s}_{wall}", s, op.kind, op.pos,
                    breakable=bool(op.breakable), override=op.interactive)
                nodes.append({
                    "floor": s, "kind": op.kind, "wall": f"ext_{s}_{wall}",
                    "pos": op.pos,
                    "interactive": m["id"] if m else None,
                    "default_state": (m or {}).get("default"),
                    "connects_from": rid,
                    "discharge_door": s == 0,
                })
    return nodes


def _gameplay_block(role, enclosed, width):
    """s9.3 / s13 network-and-gameplay defaults, derived from the role.
    Egress-critical routes are server-owned and never randomly lockable; the
    authored escape hatch is Stairwell.meta["gameplay"] (merged over this)."""
    egress = role in EGRESS_ROLES
    return {
        "network_authority": "server",
        "replicate_door_state": True,
        "allow_random_lock": not egress,
        "egress_side_always_openable": egress,
        "fire_door": egress and enclosed,
        "self_closing": egress and enclosed,
        "ai_route_cost_multiplier": _AI_COST_ENCLOSED if enclosed else 1.0,
        "congestion": {
            "clear_width_m": width,
            "max_agents_abreast": max(1, int(width // _AGENT_PASS_WIDTH)),
            "two_way_passable": width >= 1.1,
        },
    }


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
        exterior = bool(getattr(st, "exterior", False))
        sysd = {
            "id": stair_ident(st, i),
            "stack_id": getattr(st, "stack_id", None),
            "role": role,
            "shape": st.style,
            "facing": getattr(st, "facing", "N") or "N",
            "exterior": exterior,
            "channels": 2 if st.style == "scissor" else 1,
            "roof_access": max(st.from_story, st.to_story) >= spec.n_stories,
            "transfer": bool(getattr(st, "transfer", False)),
            "floors_served": served,
            "footprint_polygon": [[rect[0], rect[1]], [rect[2], rect[1]],
                                  [rect[2], rect[3]], [rect[0], rect[3]]],
            "clear_width_m": st.width,
            "approach": [],
            "discharge": None,
            "egress": {"counts_as_exit": role in EGRESS_ROLES},
        }
        if have_rooms and not exterior:
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
                room = _approach_room(spec, 0, st)   # interior stairs only
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
        # exterior towers stand on the site: they always discharge at grade
        if exterior and min(served, default=0) <= 0:
            sysd["discharge"] = {"floor": 0, "type": "exterior_tower",
                                 "room": None, "via": [],
                                 "destination": "site", "route_hops": 0}
        # Phase 4: enclosure, door nodes, and network/gameplay semantics
        enclosed = any(ap["room_role"] == "stairwell"
                       for ap in sysd["approach"])
        sysd["enclosure"] = "protected" if enclosed else "open"
        sysd["door_nodes"] = (_tower_door_nodes(spec, st, served) if exterior
                              else _door_nodes(spec, st, served))
        gp = _gameplay_block(role, enclosed, st.width)
        meta = getattr(st, "meta", None)
        if meta:
            sysd["meta"] = meta
            gp.update(meta.get("gameplay", {}))   # the authored escape hatch
        sysd["gameplay"] = gp
        systems.append(sysd)

    # egress route identity: independence groups key on the grade discharge
    # destination (two stairs sharing one are NOT independent -- the review
    # prices that); paired_with closes the two-stair contract of s13.
    egress = [s for s in systems if s["role"] in EGRESS_ROLES]
    for s in egress:
        d = s["discharge"]
        dest = d["destination"] if d and d.get("destination") else None
        s["egress"]["independence_group"] = (f"route_{dest}" if dest
                                             else f"route_{s['id']}")
        s["egress"]["paired_with"] = (
            next(o["id"] for o in egress if o is not s)
            if len(egress) == 2 else None)

    # declared transfer floors: stack members that shift footprint at their
    # junction story (Rule 2 relaxation; check() verifies walkability)
    stacks = {}
    for sysd, st in zip(systems, spec.stairs):
        if sysd["stack_id"]:
            stacks.setdefault(sysd["stack_id"], []).append((sysd, st))
    for members in stacks.values():
        members.sort(key=lambda m: min(m[1].from_story, m[1].to_story))
        for (sa, a), (sb, b) in zip(members, members[1:]):
            a_hi = max(a.from_story, a.to_story)
            b_lo = min(b.from_story, b.to_story)
            if a_hi == b_lo \
                    and not _rects_overlap(footprint_rect(a),
                                           footprint_rect(b)) \
                    and (getattr(a, "transfer", False)
                         or getattr(b, "transfer", False)):
                sa["transfer_floor"] = a_hi
                sb["transfer_floor"] = a_hi
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

        # spec 6.5 -- a spiral is decorative/private/service, never egress
        if st.style == "spiral" and role in EGRESS_ROLES:
            errors.append(
                f"STAIRWELL STAIR_STYLE_NOT_EGRESS_CAPABLE: '{sid}' is a "
                f"spiral stair carrying role '{role}' -- spirals never serve "
                f"as a required egress stair (spec 6.5); use switchback, "
                f"straight, l_shaped, or scissor, or drop the role.")

        # anti-pattern: a run that ends against the slab above (roof access
        # needs the hole plus an authored bulkhead/hatch at the top landing)
        if not st.cut_slabs \
                and max(st.from_story, st.to_story) > min(st.from_story,
                                                          st.to_story):
            warnings.append(
                f"STAIRWELL STAIR_TERMINATES_INTO_SLAB: '{sid}' spans "
                f"stories with cut_slabs=false -- each run ends against the "
                f"slab above it; cut the holes or author the bulkhead.")

        # s8.4 -- exterior tower: every occupied floor it serves needs a
        # facade door within reach (corridor -> door -> tower -> grade)
        if sysd["exterior"] and spec.ext_walls:
            wall = _tower_wall(spec, st)
            with_doors = {dn["floor"] for dn in sysd["door_nodes"]}
            for s in sysd["floors_served"]:
                if s <= 0 or s >= spec.n_stories:
                    continue        # grade discharges to site; roof is open
                if any(w.story == s for w in spec.ext_walls) \
                        and s not in with_doors:
                    emit(gate, "EXTERIOR_TOWER_NO_DOOR",
                         f"'{sid}' exterior tower serves story {s} but the "
                         f"{wall} facade has no door within reach of the "
                         f"tower there -- the floor cannot use it (s8.4).")

        # Rule 10 / criterion 10 -- the stair volume is RESERVED. Props, cover,
        # objectives, and loot may not occupy the shaft or its landings.
        rect = footprint_rect(st)
        H = spec.story_height
        lo_z = min(sysd["floors_served"] or [0]) * H
        hi_z = (max(sysd["floors_served"] or [0]) + 1) * H
        invaders = []
        for v in spec.volumes:
            nm = v.name.lower()
            if any(k in nm for k in ("stair", "ramp", "land")):
                continue                     # the stair's own furniture
            vrect = (v.x - v.size_x / 2, v.y - v.size_y / 2,
                     v.x + v.size_x / 2, v.y + v.size_y / 2)
            if _rects_overlap(rect, vrect) and lo_z <= v.z <= hi_z:
                invaders.append(f"volume '{v.name}'")
        for o in getattr(spec, "objectives", []) or []:
            if rect[0] <= o.x <= rect[2] and rect[1] <= o.y <= rect[3] \
                    and lo_z <= o.z <= hi_z:
                invaders.append(f"objective '{o.id}'")
        for l in getattr(spec, "loot", []) or []:
            if rect[0] <= l.x <= rect[2] and rect[1] <= l.y <= rect[3] \
                    and lo_z <= l.z <= hi_z:
                invaders.append(f"loot '{l.id}'")
        for m in getattr(spec, "markers", []) or []:
            if m.type not in ("objective", "loot", "cover_low", "cover_high",
                              "extraction"):
                continue
            if rect[0] <= m.x <= rect[2] and rect[1] <= m.y <= rect[3] \
                    and lo_z <= m.z <= hi_z:
                invaders.append(f"{m.type} marker '{m.id or '?'}'")
        if invaders:
            emit(gate, "STAIR_VOLUME_INVADED",
                 f"'{sid}' reserved volume is occupied by "
                 f"{', '.join(invaders)} -- stair runs, landings, and "
                 f"discharge are reserved space, not leftover space (Rule 10).")

        # s9.3 -- locked egress roulette: a required stair door that defaults
        # to locked is only tolerable when another egress stair serves the
        # floor AND the scenario says so; alone, it deletes the route.
        if gate:
            for dn in sysd["door_nodes"]:
                if dn.get("default_state") != "locked":
                    continue
                backup = [o for o in systems if o is not sysd
                          and o["role"] in EGRESS_ROLES
                          and dn["floor"] in o["floors_served"]]
                if backup:
                    warnings.append(
                        f"STAIRWELL: egress stair '{sid}' door on floor "
                        f"{dn['floor']} defaults to locked "
                        f"({dn['interactive']}); route relies on "
                        f"'{backup[0]['id']}' staying available (s9.3).")
                else:
                    errors.append(
                        f"STAIRWELL LOCKED_EGRESS_DOOR: the only egress stair "
                        f"serving floor {dn['floor']} ('{sid}') has a door "
                        f"defaulting to locked ({dn['interactive']}) -- a "
                        f"required route may not ship locked with no "
                        f"alternate (s9.3).")

        # s14.2 -- archetype fit (intel; placement lives in stair_place.py)
        if getattr(spec, "archetype", None):
            import stair_place                      # lazy: avoids the cycle
            prof = stair_place.PROFILES.get(spec.archetype)
            if prof is None:
                warnings.append(
                    f"STAIRWELL: spec declares unknown archetype "
                    f"'{spec.archetype}' (known: "
                    f"{', '.join(sorted(stair_place.PROFILES))}).")
            else:
                fams = stair_place.zone_families_at(spec, prof, st.x, st.y)
                if not fams & (set(prof["primary_zones"])
                               | set(prof["secondary_zones"])):
                    warnings.append(
                        f"STAIRWELL STAIR_LOW_ARCHETYPE_FIT: '{sid}' at "
                        f"({st.x:g}, {st.y:g}) sits in none of "
                        f"'{spec.archetype}''s candidate zones "
                        f"({', '.join(prof['primary_zones'] + prof['secondary_zones'])}) "
                        f"-- see stair_place.py for a placement proposal.")

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
                junction = a_hi if a_hi == b_lo else None
                declared = getattr(a, "transfer", False) \
                    or getattr(b, "transfer", False)
                if declared and junction is not None:
                    # Rule 2 relaxation: a DECLARED transfer floor, provided
                    # a body can actually walk between the two stairs there
                    if have_rooms and any(r.story == junction
                                          for r in spec.rooms):
                        ra = _approach_room(spec, junction, a)
                        rb = _approach_room(spec, junction, b)
                        if ra and rb and (ra.id == rb.id
                                          or rb.id in same_story.get(ra.id,
                                                                     set())):
                            continue        # verified transfer
                        errors.append(
                            f"STAIRWELL STAIR_NOT_STACKED: stack "
                            f"'{stack_id}' declares a transfer at story "
                            f"{junction}, but '{sa['id']}' and '{sb['id']}' "
                            f"land in unconnected rooms there -- a transfer "
                            f"floor must be walkable (Rule 2).")
                        continue
                    warnings.append(
                        f"STAIRWELL: stack '{stack_id}' transfer at story "
                        f"{junction} accepted as declared -- no rooms there "
                        f"to verify the walk between '{sa['id']}' and "
                        f"'{sb['id']}'.")
                    continue
                errors.append(
                    f"STAIRWELL STAIR_NOT_STACKED: stack '{stack_id}' members "
                    f"'{sa['id']}' and '{sb['id']}' have disjoint footprints "
                    f"-- the stair teleports laterally between floors "
                    f"(Rule 2); declare `transfer: true` on a member if the "
                    f"shift is intentional and walkable.")
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
                    and sb["discharge"]["type"] != "none" \
                    and sa["discharge"].get("room") \
                    and sb["discharge"].get("room"):
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
