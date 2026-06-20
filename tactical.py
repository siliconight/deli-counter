"""
tactical.py  --  graph-based tactical validation + scorecard (no Blender)
=========================================================================
Analyzes a LevelSpec's tactical structure without launching Blender. Builds
a room/connectivity graph from rooms + openings + vertical links and checks
the production-readiness rules, then produces a scorecard.

This only runs meaningful checks when a spec opts into the tactical grammar
(rooms / markers). A plain building spec (no rooms) is reported as
"non-tactical" and skipped, so back-compat holds.

Rules implemented here (geometry-graph level; no engine needed):
  - >= 2 attacker entry routes (exterior openings tagged/あ usable)
  - every floor has stair/vertical access
  - every objective room has >= 2 access paths
  - no room unreachable from an attacker entry
  - hallway / opening minimum width
  - every breach opening has breach metadata (class/material)
  - spawns present if objectives present (warn)

Sightline analysis and "door opens into collision" need real geometry
raycasts and are intentionally deferred to the Godot side (Phase 2).
"""

from dataclasses import dataclass, field

MIN_OPENING_WIDTH = 0.8   # m; below this a passage is too tight


def _rooms_by_id(spec):
    return {r.id: r for r in spec.rooms}


def _room_at(spec, story, x, y):
    """Return the room id whose bounds contain (x,y) on this story, or None."""
    for r in spec.rooms:
        if r.story != story:
            continue
        minx, miny, maxx, maxy = r.bounds
        if minx <= x <= maxx and miny <= y <= maxy:
            return r.id
    return None


def build_graph(spec):
    """Nodes = room ids. Edges from interior openings (same story, between two
    rooms) and vertical links (between stories). Returns (adjacency, info)."""
    adj = {r.id: set() for r in spec.rooms}

    # interior openings connect two rooms on the same story
    # (we approximate: an opening connects the rooms on either side of the
    #  partition by sampling points just off the opening center)
    # Here we use the recorded gameplay openings if present; else partitions.
    # Since validation runs pre-build, derive from partitions directly.
    for p in spec.partitions:
        if not p.openings:
            continue
        eps = 0.6
        length = abs(p.end - p.start)
        lo = min(p.start, p.end)
        # sample at each opening's actual position along the run, not the
        # partition midpoint — a long wall can border different rooms along
        # its length, and each doorway connects whatever rooms flank it.
        for op in p.openings:
            along = lo + (op.pos + 0.5) * length
            if p.axis == "Y":      # wall runs along Y at x=pos; opening along Y
                a = _room_at(spec, p.story, p.pos - eps, along)
                b = _room_at(spec, p.story, p.pos + eps, along)
            else:                  # wall runs along X at y=pos; opening along X
                a = _room_at(spec, p.story, along, p.pos - eps)
                b = _room_at(spec, p.story, along, p.pos + eps)
            if a and b and a != b:
                adj[a].add(b)
                adj[b].add(a)

    # vertical links connect rooms across stories at (x,y)
    def _connect_stair_column(lo, hi):
        for s in range(lo, hi):
            for ra in [r for r in spec.rooms if r.story == s]:
                for rb in [r for r in spec.rooms if r.story == s + 1]:
                    if _overlap(ra.bounds, rb.bounds):
                        adj[ra.id].add(rb.id)
                        adj[rb.id].add(ra.id)

    # actual stairwells (geometry section) connect the stories they span
    for st in spec.stairs:
        lo, hi = sorted([st.from_story, st.to_story])
        _connect_stair_column(lo, hi)

    # ladders and ramps connect the rooms at their (x,y) across stories
    for ld in spec.ladders:
        lo, hi = sorted([ld.from_story, ld.to_story])
        for s in range(lo, hi):
            a = _room_at(spec, s, ld.x, ld.y)
            b = _room_at(spec, s + 1, ld.x, ld.y)
            if a and b:
                adj[a].add(b)
                adj[b].add(a)
    for rp in spec.ramps:
        lo, hi = sorted([rp.from_story, rp.to_story])
        for s in range(lo, hi):
            a = _room_at(spec, s, rp.x, rp.y)
            b = _room_at(spec, s + 1, rp.x, rp.y)
            if a and b:
                adj[a].add(b)
                adj[b].add(a)

    for v in spec.vertical_links:
        if v.kind == "stair" and v.from_story is not None:
            lo, hi = sorted([v.from_story, v.to_story])
            _connect_stair_column(lo, hi)
        elif v.kind in ("floor_hole", "hatch") and v.story is not None \
                and v.x is not None:
            a = _room_at(spec, v.story, v.x, v.y)
            b = _room_at(spec, v.story - 1, v.x, v.y)
            if a and b:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def _overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _entry_rooms(spec):
    """Rooms reachable directly from an exterior opening (an entry route)."""
    entries = set()
    base = -1 if spec.has_basement else 0
    for w in spec.ext_walls:
        for op in w.openings:
            if op.kind not in ("door", "garage", "breach"):
                continue
            # the room just inside this exterior wall
            hx = spec.footprint_x / 2
            hy = spec.footprint_y / 2
            run = spec.footprint_x if w.wall in ("N", "S") else spec.footprint_y
            u = op.pos * run
            eps = 0.8
            if w.wall == "N":
                rid = _room_at(spec, w.story, u, hy - eps)
            elif w.wall == "S":
                rid = _room_at(spec, w.story, u, -hy + eps)
            elif w.wall == "E":
                rid = _room_at(spec, w.story, hx - eps, u)
            else:
                rid = _room_at(spec, w.story, -hx + eps, u)
            if rid:
                entries.add(rid)
    return entries


def _reachable(adj, starts):
    seen = set(starts)
    stack = list(starts)
    while stack:
        n = stack.pop()
        for m in adj.get(n, ()):
            if m not in seen:
                seen.add(m)
                stack.append(m)
    return seen


def analyze(spec):
    """Return (errors, warnings, scorecard dict). errors are hard failures.
    Dispatches on spec.mode: 'assault' (default), 'heist', or 'survival'."""
    errors, warnings = [], []
    mode = getattr(spec, "mode", "assault")

    if not spec.rooms:
        # heist/survival levels can carry tactical meaning via zones/objectives/
        # markers even without rooms; only truly empty tactical specs are skipped.
        if mode == "heist" and (spec.objectives or spec.zones or spec.loot):
            return _analyze_heist(spec)
        if mode == "survival" and (spec.zones or
                any(m.type in ("survivor_spawn", "horde_spawn") for m in spec.markers)):
            return _analyze_survival(spec)
        return [], ["non-tactical spec (no rooms defined); tactical rules "
                    "skipped"], {"tactical": False}

    if mode == "heist":
        return _analyze_heist(spec)
    if mode == "survival":
        return _analyze_survival(spec)

    rooms = _rooms_by_id(spec)
    adj = build_graph(spec)
    entries = _entry_rooms(spec)
    objective_rooms = [r for r in spec.rooms
                       if r.objective or r.role == "objective_room"]

    # exterior entry routes
    ext_entries = 0
    for w in spec.ext_walls:
        for op in w.openings:
            if op.kind in ("door", "garage", "breach"):
                ext_entries += 1
    if ext_entries < 2:
        errors.append(f"only {ext_entries} attacker entry opening(s); need >= 2")

    # reachability from entries
    reachable = _reachable(adj, entries) if entries else set()
    unreachable = [r.id for r in spec.rooms if r.id not in reachable]
    if entries and unreachable:
        errors.append(f"rooms unreachable from any entry: {', '.join(unreachable)}")
    if not entries:
        warnings.append("no exterior opening maps into a defined room; "
                        "check room bounds vs wall positions")

    # objective rooms need >= 2 access paths (degree >= 2 in the graph)
    for r in objective_rooms:
        deg = len(adj.get(r.id, ()))
        if deg < 2:
            errors.append(f"objective room '{r.id}' has {deg} access path(s); "
                          "need >= 2")

    # every floor has vertical access (stair/link touching it)
    stories = sorted({r.story for r in spec.rooms})
    linked_stories = set()
    for v in spec.vertical_links:
        if v.from_story is not None:
            lo, hi = sorted([v.from_story, v.to_story])
            linked_stories.update(range(lo, hi + 1))
        if v.story is not None:
            linked_stories.update([v.story, v.story - 1])
    for st in spec.stairs:
        lo, hi = sorted([st.from_story, st.to_story])
        linked_stories.update(range(lo, hi + 1))
    for ld in spec.ladders:
        lo, hi = sorted([ld.from_story, ld.to_story])
        linked_stories.update(range(lo, hi + 1))
    for rp in spec.ramps:
        lo, hi = sorted([rp.from_story, rp.to_story])
        linked_stories.update(range(lo, hi + 1))
    for s in stories:
        if len(stories) > 1 and s not in linked_stories:
            errors.append(f"story {s} has no stair/vertical access")

    # steep ramp warning (too steep to walk -> should be stairs)
    import math as _m
    for ri, rp in enumerate(spec.ramps):
        dz = abs(rp.to_story - rp.from_story) * spec.story_height
        slope = _m.degrees(_m.atan2(dz, rp.run)) if rp.run else 90.0
        if slope > rp.max_slope_deg:
            warnings.append(f"ramp #{ri} slope {slope:.0f}deg exceeds walkable "
                            f"max {rp.max_slope_deg:.0f}deg (consider stairs or "
                            "a longer run)")

    # opening widths + breach metadata
    def _check_openings(openings, where):
        for op in openings:
            r = op.resolved()
            if op.kind in ("door", "garage", "breach") and r["width"] < MIN_OPENING_WIDTH:
                errors.append(f"{where}: {op.kind} width {r['width']}m below "
                              f"min {MIN_OPENING_WIDTH}m")
            if op.kind == "breach" and not (op.breach_class or op.material):
                warnings.append(f"{where}: breach opening lacks breach_class/"
                                "material metadata")
    for w in spec.ext_walls:
        _check_openings(w.openings, f"ext {w.wall}@{w.story}")
    for i, p in enumerate(spec.partitions):
        _check_openings(p.openings, f"partition #{i}@{p.story}")

    # spawns vs objectives
    marker_types = {m.type for m in spec.markers}
    if objective_rooms and "attacker_spawn" not in marker_types:
        warnings.append("objectives defined but no attacker_spawn marker")
    if objective_rooms and "defender_spawn" not in marker_types:
        warnings.append("objectives defined but no defender_spawn marker")

    scorecard = {
        "tactical": True,
        "floors": len(stories),
        "rooms": len(spec.rooms),
        "attacker_entries": ext_entries,
        "objective_rooms": len(objective_rooms),
        "breach_points": sum(1 for w in spec.ext_walls for o in w.openings
                             if o.kind == "breach")
                         + sum(1 for p in spec.partitions for o in p.openings
                               if o.kind == "breach"),
        "vertical_links": len(spec.vertical_links) + len(spec.stairs),
        "markers": len(spec.markers),
        "unreachable_rooms": len(unreachable),
        "errors": len(errors),
        "warnings": len(warnings),
        "mode": "assault",
    }
    return errors, warnings, scorecard


def _point_in_zone(zone, x, y):
    b = zone.bounds
    return b and b[0] <= x <= b[2] and b[1] <= y <= b[3]


def _analyze_heist(spec):
    """Heist mode: PvE crew objectives + loot + extraction. Independent
    objectives (any order). Rules differ from assault — no defender/breach
    requirements; instead validate the heist loop is completable."""
    errors, warnings = [], []

    objectives = spec.objectives
    loot = spec.loot
    extraction = [z for z in spec.zones if z.kind == "extraction"]
    secure = [z for z in spec.zones if z.kind in ("secure", "drop")]

    # core heist requirements
    if not objectives:
        warnings.append("heist level has no objectives defined")
    if not extraction:
        errors.append("heist level has no extraction zone")

    # at least one entry into the building (crew has to get in)
    ext_entries = sum(1 for w in spec.ext_walls for op in w.openings
                      if op.kind in ("door", "garage", "breach"))
    if ext_entries < 1:
        errors.append("no exterior entry opening for the crew")

    # required objectives need to exist if any objective is marked required
    required = [o for o in objectives if o.required]
    if objectives and not required:
        warnings.append("no objective marked required; extraction would be "
                        "valid immediately")

    # loot economy sanity
    if loot:
        total_value = sum(l.value for l in loot)
        total_bags = sum(l.bags for l in loot)
        if total_bags == 0:
            warnings.append("loot defined but yields 0 carriable bags")
        if not secure and not extraction:
            warnings.append("loot defined but no secure/drop/extraction zone "
                            "to deliver it to")
    else:
        total_value, total_bags = 0, 0

    # reachability (only if rooms are defined; heist levels may be open-plan)
    unreachable_objs = []
    if spec.rooms:
        adj = build_graph(spec)
        entries = _entry_rooms(spec)
        reachable_rooms = _reachable(adj, entries) if entries else set()

        def _obj_room(o):
            return o.room or _room_at(spec, _story_of_z(spec, o.z), o.x, o.y)
        for o in objectives:
            rr = _obj_room(o)
            if rr and entries and rr not in reachable_rooms:
                unreachable_objs.append(o.id)
        if unreachable_objs:
            errors.append("objectives in unreachable rooms: "
                          + ", ".join(unreachable_objs))

    # phase tags on spawns (informational)
    phases = set()
    for m in spec.markers:
        if m.meta and "phase" in m.meta:
            phases.add(m.meta["phase"])

    scorecard = {
        "tactical": True,
        "mode": "heist",
        "objectives": len(objectives),
        "required_objectives": len(required),
        "loot_spawns": len(loot),
        "loot_value": total_value,
        "loot_bags": total_bags,
        "extraction_zones": len(extraction),
        "secure_zones": len(secure),
        "entries": ext_entries,
        "phases": sorted(phases),
        "markers": len(spec.markers),
        "unreachable_objectives": len(unreachable_objs),
        "errors": len(errors),
        "warnings": len(warnings),
    }
    return errors, warnings, scorecard


def _analyze_survival(spec):
    """Survival mode: co-op PvE horde defense. The level is a directional run —
    players move from a start safe-room, through the building, to a finale
    holdout where they survive a final wave (and optionally a rescue/escape).
    Rules differ from assault/heist: instead of breach rules or a loot loop,
    validate that (1) there's a start and a finale, (2) the finale is reachable
    from the start through the building, and (3) there are horde spawns to
    apply pressure along the way.

    Vocabulary (all reuse existing spec fields — no geometry changes):
      - zones: kind 'safe_room' (start) and 'finale' (holdout). Optionally an
        'extraction' zone for the rescue/escape point.
      - rooms: role 'safe_room', 'finale'/'holdout', 'route_node' read as hints.
      - markers: type 'survivor_spawn' (where the team starts), 'horde_spawn'
        (where AI pours in), 'rescue' (escape point). The AI director / wave
        state machine lives in your game code; the level just provides geometry.
    """
    errors, warnings = [], []

    zones = spec.zones
    safe_rooms = [z for z in zones if z.kind == "safe_room"]
    finales = [z for z in zones if z.kind == "finale"]
    rescues = [z for z in zones if z.kind == "extraction"]

    # core survival requirements: a start and a finale holdout
    if not safe_rooms:
        # fall back to a survivor_spawn marker if no safe_room zone
        if not any(m.type == "survivor_spawn" for m in spec.markers):
            errors.append("survival level has no safe_room zone or "
                          "survivor_spawn marker (nowhere for the team to start)")
    if not finales:
        errors.append("survival level has no finale zone (no holdout to reach)")

    # at least one exterior entry (the team has to be able to enter/exit the run)
    ext_entries = sum(1 for w in spec.ext_walls for op in w.openings
                      if op.kind in ("door", "garage", "breach"))
    if ext_entries < 1:
        warnings.append("no exterior entry opening; the run is fully interior")

    # horde spawns are what make it a survival level rather than a walk
    horde_spawns = [m for m in spec.markers if m.type == "horde_spawn"]
    if not horde_spawns:
        warnings.append("no horde_spawn markers; the route has no AI pressure")
    elif len(horde_spawns) < 3:
        warnings.append(f"only {len(horde_spawns)} horde_spawn marker(s); "
                        "survival runs usually want spawns spread along the route")

    # THE key check: is the finale reachable from the start through the building?
    # This is the survival analogue of heist's objective-reachability — the run
    # has to be traversable start -> finale or the level is unplayable.
    unreachable_finale = False
    route_reachable_rooms = set()
    if spec.rooms:
        adj = build_graph(spec)
        # start rooms = entry rooms + any room tagged safe_room + survivor spawns
        starts = set(_entry_rooms(spec))
        for r in spec.rooms:
            if r.role in ("safe_room", "start"):
                starts.add(r.id)
        for m in spec.markers:
            if m.type == "survivor_spawn":
                rr = m.room or _room_at(spec, _story_of_z(spec, m.z), m.x, m.y)
                if rr:
                    starts.add(rr)
        route_reachable_rooms = _reachable(adj, starts) if starts else set()

        # finale rooms: role-tagged, or the room containing a finale zone's center
        finale_rooms = set()
        for r in spec.rooms:
            if r.role in ("finale", "holdout"):
                finale_rooms.add(r.id)
        for z in finales:
            if z.bounds:
                cx = (z.bounds[0] + z.bounds[2]) / 2
                cy = (z.bounds[1] + z.bounds[3]) / 2
                rr = _room_at(spec, z.story, cx, cy)
                if rr:
                    finale_rooms.add(rr)

        if finale_rooms and starts:
            unreachable = [r for r in finale_rooms if r not in route_reachable_rooms]
            if unreachable:
                unreachable_finale = True
                errors.append("finale holdout not reachable from the start: "
                              + ", ".join(unreachable))

    scorecard = {
        "tactical": True,
        "mode": "survival",
        "safe_rooms": len(safe_rooms),
        "finales": len(finales),
        "rescue_zones": len(rescues),
        "horde_spawns": len(horde_spawns),
        "entries": ext_entries,
        "rooms": len(spec.rooms),
        "vertical_links": len(spec.vertical_links),
        "route_reachable_rooms": len(route_reachable_rooms),
        "finale_reachable": not unreachable_finale,
        "markers": len(spec.markers),
        "errors": len(errors),
        "warnings": len(warnings),
    }
    return errors, warnings, scorecard


def _story_of_z(spec, z):
    return int(round(z / spec.story_height))


def format_scorecard(spec_name, scorecard):
    if not scorecard.get("tactical"):
        return "  scorecard: (non-tactical spec — no rooms)"
    s = scorecard
    if s.get("mode") == "heist":
        return (
            f"  scorecard for {spec_name} [heist]:\n"
            f"    objectives: {s['objectives']} "
            f"({s['required_objectives']} required)   "
            f"entries: {s['entries']}   markers: {s['markers']}\n"
            f"    loot: {s['loot_spawns']} spawns, {s['loot_bags']} bags, "
            f"value {s['loot_value']:g}\n"
            f"    extraction zones: {s['extraction_zones']}   "
            f"secure/drop zones: {s['secure_zones']}   "
            f"unreachable objectives: {s['unreachable_objectives']}\n"
            f"    phases: {', '.join(s['phases']) if s['phases'] else '—'}\n"
            f"    errors: {s['errors']}   warnings: {s['warnings']}"
        )
    if s.get("mode") == "survival":
        return (
            f"  scorecard for {spec_name} [survival]:\n"
            f"    safe rooms: {s['safe_rooms']}   finales: {s['finales']}   "
            f"rescue zones: {s['rescue_zones']}\n"
            f"    horde spawns: {s['horde_spawns']}   entries: {s['entries']}   "
            f"markers: {s['markers']}\n"
            f"    rooms: {s['rooms']}   vertical links: {s['vertical_links']}   "
            f"finale reachable: {'yes' if s['finale_reachable'] else 'NO'}\n"
            f"    errors: {s['errors']}   warnings: {s['warnings']}"
        )
    return (
        f"  scorecard for {spec_name} [assault]:\n"
        f"    floors: {s['floors']}   rooms: {s['rooms']}   "
        f"markers: {s['markers']}\n"
        f"    attacker entries: {s['attacker_entries']}   "
        f"objective rooms: {s['objective_rooms']}   "
        f"breach points: {s['breach_points']}\n"
        f"    vertical links: {s['vertical_links']}   "
        f"unreachable rooms: {s['unreachable_rooms']}\n"
        f"    errors: {s['errors']}   warnings: {s['warnings']}"
    )
