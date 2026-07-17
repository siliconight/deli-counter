"""
pvp_heist.py  --  gating validation profile for attacker-vs-defender heist play
===============================================================================
The `pvp_heist` mode is the production profile for PvP heist missions: one team
attacks a defended objective, the other holds it. Unlike the PvE `heist` mode
(crew vs. AI), both sides are players, so the *balance-critical* findings that
combat_audit/sightlines report as advisory intel become hard gates here.

What this module gates (spec references are to the Production Package, §10/§13):

  PVP-SPAWN-A       at least one valid attacker spawn marker
  PVP-SPAWN-D       at least one valid defender spawn marker
  PVP-SPAWN-BOUNDS  spawn markers inside the playable envelope
  PVP-OBJ           an objective exists and sits in a resolvable room
  PVP-ROUTES        >= 2 room-disjoint attacker routes to the objective
  PVP-EXTRACT       objective can reach the extraction (zone/marker) or an
                    extraction-facing exit (entry room)
  PVP-SPAWN-LOS     no direct opposing-spawn sightline (same story, clear ray)
  PVP-ROTATE        at least one protected defender rotation (a route to the
                    objective avoiding attacker entry rooms)
  PVP-FLANK         at least one flanking opportunity (entries on more than one
                    face, or a vertical/breach alternate approach)
  PVP-BREACH        every breach opening connects two resolvable spaces
  PVP-VERT          declared vertical routes resolve (counts stairs/ladders;
                    hard stair/ladder integrity lives in stairwell.py/ladder.py)

All findings carry their code so downstream evidence files and failing-fixture
tests can assert the *reason*, not just the failure.

Usage:
    import pvp_heist
    errors, warnings, summary = pvp_heist.check(spec)   # gate on errors

Network-agnostic by design: this validates markers and metadata only. It never
prescribes how doors/breaches/objectives replicate at runtime.
"""

from collections import deque

ATTACKER_TYPES = ("attacker_spawn", "crew_spawn")
DEFENDER_TYPES = ("defender_spawn",)

# A spawn may legitimately sit in declared outdoor rooms beyond the footprint,
# or on the street apron just outside it (attacker approach staging) — Lot owns
# true site-level placement. Beyond footprint+margin AND beyond all declared
# room bounds = out of the playable envelope.
SPAWN_MARGIN = 8.0
ROOM_MARGIN = 0.5


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _marker_story(spec, m):
    try:
        import floorplan as fp
        return fp._marker_story(spec, m)
    except Exception:
        sh = getattr(spec, "story_height", 3.5) or 3.5
        return int(round((m.z or 0.0) / sh))


def _room_of_point(spec, story, x, y):
    from tactical import _room_at
    return _room_at(spec, story, x, y)


def _marker_room(spec, m):
    """Room id a marker belongs to: declared room wins, else locate by point."""
    if getattr(m, "room", None):
        return m.room
    return _room_of_point(spec, _marker_story(spec, m), m.x, m.y)


def _in_envelope(spec, m):
    """Inside footprint (+margin) or inside any declared room's bounds."""
    hx = spec.footprint_x / 2 + SPAWN_MARGIN
    hy = spec.footprint_y / 2 + SPAWN_MARGIN
    if -hx <= m.x <= hx and -hy <= m.y <= hy:
        return True
    for r in getattr(spec, "rooms", []) or []:
        x0, y0, x1, y1 = r.bounds
        if (x0 - ROOM_MARGIN <= m.x <= x1 + ROOM_MARGIN
                and y0 - ROOM_MARGIN <= m.y <= y1 + ROOM_MARGIN):
            return True
    return False


def _bfs_path(adj, starts, goals, blocked=()):
    """Shortest path (list of nodes) from any start to any goal, or None.
    Nodes in `blocked` are not traversed (starts/goals exempt themselves)."""
    starts = [s for s in starts if s in adj]
    goals = set(g for g in goals if g in adj)
    if not starts or not goals:
        return None
    blocked = set(blocked)
    prev = {s: None for s in starts}
    q = deque(starts)
    while q:
        n = q.popleft()
        if n in goals:
            path = []
            while n is not None:
                path.append(n)
                n = prev[n]
            return list(reversed(path))
        for nb in adj.get(n, ()):
            if nb in prev:
                continue
            if nb in blocked and nb not in goals:
                continue
            prev[nb] = n
            q.append(nb)
    return None


def _disjoint_route_count(adj, starts, goals, max_routes=8):
    """Number of interior-room-disjoint routes from any start to any goal:
    a proper Menger count via unit-node-capacity max-flow (node splitting,
    BFS augmenting paths). Start/goal rooms have unlimited capacity (two
    routes may share the spawn room and must share the objective room);
    every interior room can carry one route; each room-adjacency edge
    carries one route (parallel doorways between the same two rooms
    collapse — they are not meaningfully different at room resolution)."""
    starts = [s for s in starts if s in adj]
    goals = set(g for g in goals if g in adj)
    if not starts or not goals:
        return 0
    INF = 1 << 20
    cap = {}

    def add(u, v, c):
        cap[(u, v)] = cap.get((u, v), 0) + c
        cap.setdefault((v, u), 0)

    endpoints = set(starts) | goals
    for n in adj:
        add((n, "in"), (n, "out"), INF if n in endpoints else 1)
    for n, nbrs in adj.items():
        for m in nbrs:
            add((n, "out"), (m, "in"), 1)
    S, T = ("__S__", "src"), ("__T__", "snk")
    for s in set(starts):
        add(S, (s, "in"), INF)
    for g in goals:
        add((g, "out"), T, INF)

    flow = 0
    while flow < max_routes:
        # BFS for an augmenting path in the residual graph
        prev = {S: None}
        q = deque([S])
        while q and T not in prev:
            u = q.popleft()
            for (a, b), c in cap.items():
                if a == u and c > 0 and b not in prev:
                    prev[b] = u
                    q.append(b)
        if T not in prev:
            break
        # augment by 1 (all path-limiting capacities are 1)
        v = T
        while prev[v] is not None:
            u = prev[v]
            cap[(u, v)] -= 1
            cap[(v, u)] += 1
            v = u
        flow += 1
    return flow


def _entry_faces(spec):
    """Walls (N/S/E/W) that carry a ground-reachable entry opening."""
    faces = set()
    for w in getattr(spec, "ext_walls", []) or []:
        for op in w.openings:
            if op.kind in ("door", "garage", "breach"):
                faces.add(w.wall)
    return faces


# --------------------------------------------------------------------------
# the profile
# --------------------------------------------------------------------------

def check(spec):
    """Return (errors, warnings, summary). Errors gate approval."""
    from tactical import build_graph, _entry_rooms

    errors, warnings = [], []
    summary = {
        "profile": "pvp_heist",
        "attacker_spawns": 0, "defender_spawns": 0,
        "objective_rooms": [], "disjoint_routes": 0,
        "extraction": None, "protected_rotation": False,
        "flank": None, "spawn_los_pairs": [],
        "breach_openings": 0, "stairs": len(getattr(spec, "stairs", []) or []),
        "ladders": len(getattr(spec, "ladders", []) or []),
    }

    markers = getattr(spec, "markers", []) or []
    attackers = [m for m in markers if m.type in ATTACKER_TYPES]
    defenders = [m for m in markers if m.type in DEFENDER_TYPES]
    summary["attacker_spawns"] = len(attackers)
    summary["defender_spawns"] = len(defenders)

    if any(m.type == "crew_spawn" for m in attackers):
        warnings.append("PVP-SPAWN-A: crew_spawn markers accepted as attacker "
                        "spawns; prefer attacker_spawn for pvp_heist specs")

    # --- spawn presence -----------------------------------------------------
    if not attackers:
        errors.append("PVP-SPAWN-A: no attacker_spawn marker; pvp_heist "
                      "requires at least one valid attacker spawn")
    if not defenders:
        errors.append("PVP-SPAWN-D: no defender_spawn marker; pvp_heist "
                      "requires at least one valid defender spawn")

    # --- spawn bounds -------------------------------------------------------
    for m in attackers + defenders:
        if not _in_envelope(spec, m):
            errors.append(
                f"PVP-SPAWN-BOUNDS: {m.type} '{m.id or '?'}' at "
                f"({m.x:.1f},{m.y:.1f}) is outside the footprint and every "
                f"declared room — out of the playable envelope")

    # --- objective ----------------------------------------------------------
    obj_points = []          # (x, y, story, label)
    for o in getattr(spec, "objectives", []) or []:
        st = int(round((o.z or 0.0) / (spec.story_height or 3.5)))
        if getattr(o, "room", None):
            room = o.room
        else:
            room = _room_of_point(spec, st, o.x, o.y)
        obj_points.append((o.x, o.y, st, room, f"objective '{o.id}'"))
    for m in markers:
        if m.type == "objective":
            obj_points.append((m.x, m.y, _marker_story(spec, m),
                               _marker_room(spec, m),
                               f"objective marker '{m.id or '?'}'"))

    if not obj_points:
        errors.append("PVP-OBJ: no objective (spec.objectives or objective "
                      "marker); pvp_heist requires a defended objective")

    obj_rooms = sorted({p[3] for p in obj_points if p[3]})
    summary["objective_rooms"] = obj_rooms
    if obj_points and not obj_rooms and getattr(spec, "rooms", None):
        errors.append("PVP-OBJ: no objective resolves to a declared room; the "
                      "objective floats outside the room graph")

    # room-graph analyses need rooms; without them the profile can only do
    # marker-level checks (bounds + LOS) and must say so.
    if not getattr(spec, "rooms", None):
        warnings.append("PVP: spec declares no rooms; route/rotation/flank "
                        "gates skipped (marker-level checks only). Production "
                        "pvp_heist specs must declare rooms.")
        errors_r, sight = _spawn_los(spec, attackers, defenders)
        errors.extend(errors_r)
        summary["spawn_los_pairs"] = sight
        return errors, warnings, summary

    adj = build_graph(spec)
    entries = _entry_rooms(spec)

    # attacker start rooms: rooms holding attacker spawns; fall back to entry
    # rooms when the spawns stand outside every declared room.
    a_rooms = sorted({r for r in (_marker_room(spec, m) for m in attackers) if r})
    if attackers and not a_rooms:
        warnings.append("PVP-SPAWN-A: attacker spawns are outside all declared "
                        "rooms; using entry rooms as attack origins")
        a_rooms = sorted(entries)
    d_rooms = sorted({r for r in (_marker_room(spec, m) for m in defenders) if r})
    if defenders and not d_rooms:
        errors.append("PVP-SPAWN-D: defender spawn(s) resolve to no declared "
                      "room — defenders would spawn outside the room graph")

    # --- >= 2 disjoint attacker routes -------------------------------------
    if a_rooms and obj_rooms:
        n = _disjoint_route_count(adj, a_rooms, obj_rooms)
        summary["disjoint_routes"] = n
        if n == 0:
            errors.append("PVP-ROUTES: objective unreachable from attacker "
                          "spawns — no route at all")
        elif n < 2:
            errors.append(
                "PVP-ROUTES: only one room-disjoint attacker route to the "
                "objective; pvp_heist requires at least two meaningfully "
                "different routes (add an entrance, breach, or vertical route)")

    # --- objective -> extraction -------------------------------------------
    extract_rooms = set()
    how = None
    for z in getattr(spec, "zones", []) or []:
        if z.kind == "extraction" and z.bounds:
            cx = (z.bounds[0] + z.bounds[2]) / 2
            cy = (z.bounds[1] + z.bounds[3]) / 2
            r = _room_of_point(spec, z.story, cx, cy)
            if r:
                extract_rooms.add(r)
                how = "extraction zone"
    for m in markers:
        if m.type == "extraction":
            r = _marker_room(spec, m)
            if r:
                extract_rooms.add(r)
                how = how or "extraction marker"
    if not extract_rooms:
        extract_rooms = set(entries)
        how = "extraction-facing exit (entry rooms)"
    summary["extraction"] = how
    if obj_rooms:
        if not _bfs_path(adj, obj_rooms, extract_rooms):
            errors.append(
                f"PVP-EXTRACT: objective cannot reach the {how}; the win "
                f"condition is not completable")

    # --- opposing-spawn sightlines -----------------------------------------
    errors_r, sight = _spawn_los(spec, attackers, defenders)
    errors.extend(errors_r)
    summary["spawn_los_pairs"] = sight

    # --- protected defender rotation ---------------------------------------
    if d_rooms and obj_rooms:
        avoid = entries - set(d_rooms) - set(obj_rooms)
        path = _bfs_path(adj, d_rooms, obj_rooms, blocked=avoid)
        summary["protected_rotation"] = path is not None
        if path is None:
            errors.append(
                "PVP-ROTATE: no protected defender rotation — every "
                "defender route to the objective passes through an attacker "
                "entry room (defenders are exposed the moment they move)")

    # --- flanking opportunity ----------------------------------------------
    faces = _entry_faces(spec)
    vertical = bool(getattr(spec, "ladders", None)) or bool(
        getattr(spec, "stairs", None) and len(spec.stairs) > 1)
    if len(faces) >= 2:
        summary["flank"] = f"entries on faces {sorted(faces)}"
    elif vertical:
        summary["flank"] = "vertical alternate route"
        warnings.append("PVP-FLANK: single entry face; flanking relies "
                        "entirely on the vertical route")
    else:
        errors.append(
            "PVP-FLANK: all entries on one face and no vertical alternate — "
            "no flanking opportunity exists (attackers are fully predictable)")

    # --- breach metadata ----------------------------------------------------
    n_breach, breach_errs = _check_breaches(spec)
    summary["breach_openings"] = n_breach
    errors.extend(breach_errs)

    return errors, warnings, summary


def _spawn_los(spec, attackers, defenders):
    """Direct opposing-spawn sightline check (same story, 2D clear ray against
    wall/tall-volume occluders — the same geometry sightlines.py uses)."""
    errors, pairs = [], []
    if not attackers or not defenders:
        return errors, pairs
    try:
        import sightlines
    except Exception:
        return errors, pairs
    by_story = {}
    for m in attackers + defenders:
        by_story.setdefault(_marker_story(spec, m), []).append(m)
    for story, ms in by_story.items():
        atk = [m for m in ms if m.type in ATTACKER_TYPES]
        dfd = [m for m in ms if m.type in DEFENDER_TYPES]
        if not atk or not dfd:
            continue
        try:
            occ = sightlines._occluders(spec, story)
        except Exception:
            continue
        for a in atk:
            for d in dfd:
                if sightlines._clear((a.x, a.y), (d.x, d.y), occ):
                    pairs.append([a.id or a.type, d.id or d.type, story])
                    errors.append(
                        f"PVP-SPAWN-LOS: attacker spawn '{a.id or '?'}' and "
                        f"defender spawn '{d.id or '?'}' (story {story}) have "
                        f"a direct clear sightline at spawn time")
    return errors, pairs


def _check_breaches(spec):
    """Every breach opening must connect two resolvable spaces (room<->room or
    room<->outdoors), never open into solid/void."""
    from tactical import _room_at
    errors = []
    n = 0
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    for w in getattr(spec, "ext_walls", []) or []:
        run = spec.footprint_x if w.wall in ("N", "S") else spec.footprint_y
        for op in w.openings:
            if op.kind != "breach":
                continue
            n += 1
            u = op.pos * run
            eps = 0.8
            if w.wall == "N":
                inside = _room_at(spec, w.story, u, hy - eps)
            elif w.wall == "S":
                inside = _room_at(spec, w.story, u, -hy + eps)
            elif w.wall == "E":
                inside = _room_at(spec, w.story, hx - eps, u)
            else:
                inside = _room_at(spec, w.story, -hx + eps, u)
            if getattr(spec, "rooms", None) and inside is None:
                errors.append(
                    f"PVP-BREACH: exterior breach on {w.wall}@{w.story} "
                    f"(pos {op.pos:.2f}) opens into no declared room — a "
                    f"breach into solid/void space")
    for i, p in enumerate(getattr(spec, "partitions", []) or []):
        length = abs(p.end - p.start)
        lo = min(p.start, p.end)
        for op in p.openings:
            if op.kind != "breach":
                continue
            n += 1
            along = lo + (op.pos + 0.5) * length
            eps = 0.6
            if p.axis == "Y":
                a = _room_at(spec, p.story, p.pos - eps, along)
                b = _room_at(spec, p.story, p.pos + eps, along)
            else:
                a = _room_at(spec, p.story, along, p.pos - eps)
                b = _room_at(spec, p.story, along, p.pos + eps)
            if getattr(spec, "rooms", None) and (a is None or b is None):
                errors.append(
                    f"PVP-BREACH: interior breach on partition #{i}@{p.story} "
                    f"does not connect two rooms (sides resolve to "
                    f"{a!r} / {b!r}) — breach into solid/void space")
    return n, errors


def format_summary(spec_name, summary):
    return (f"  pvp_heist profile for {spec_name}:\n"
            f"    attackers: {summary['attacker_spawns']}   "
            f"defenders: {summary['defender_spawns']}   "
            f"objective rooms: {', '.join(summary['objective_rooms']) or '—'}\n"
            f"    disjoint routes: {summary['disjoint_routes']}   "
            f"extraction via: {summary['extraction'] or '—'}   "
            f"protected rotation: {'yes' if summary['protected_rotation'] else 'NO'}\n"
            f"    flank: {summary['flank'] or 'NONE'}   "
            f"breaches: {summary['breach_openings']}   "
            f"stairs: {summary['stairs']}   ladders: {summary['ladders']}")
