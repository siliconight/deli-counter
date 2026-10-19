#!/usr/bin/env python3
"""
open_floor_rules.py  --  two rooms that meet with no wall between them: one floor, or two rooms
=============================================================================================
Deli Counter 0.234.0 (the factory's roadmap 260). layout_lint L26 (0.223.0) names every pair of rooms on one storey
whose shared edge no partition covers for `tactical.OPEN_FLOOR_M` and that no room's `open_to` names. The library had
49 such pairs in 26 specs (`open_floor_baseline.json`), frozen for the walker to sort one pair at a time. They are 20
pairs of room ids repeated through shared recipes, so they are sorted here once, by pair: a row says the floor is meant
(OPEN) or the two rooms are two rooms (WALL), and one row moves every building that has the pair.

THE WALKER'S CALLS, 2026-10-19 (the factory's docs/findings/walker_review_2026-10-19/). The rows below are the
defaults offered and approved in chat -- "go ahead with the 255 table, your defaults are good" -- after the review
page had answered "Wall it" for every pair while the walker was unsure whether a wall would shut a room nobody could
open: "we aren't making the doors in level factory because we are going to have networked doors added later". A wall
here shuts no room by itself: a door opening in it ships as a door socket like every other (Dispatch's
`interactives.json`), and layout_lint L12 fails a room nothing reaches. Three rows depart from what was offered,
each because a stair stands on the line, the factory's call until the walker asks otherwise: the office's lobby and
bullpen meet along y 0, where `office_stair_0` stands, and corner_deli_heist_01's stair well meets its two cold rooms
along edges the stair itself reaches or a door sits on (the rows say where). They are OPEN.

The gas stations' three forecourt rows never fire on today's library: those rooms meet along the footprint's own
edge, where the exterior wall stands, and since 0.234.0 the open-floor reading counts it (`tactical.exterior_parts`).
The rows stay as the walker's sort for a forecourt that meets a shop inside the footprint.

WHAT A ROW DOES (`apply`):
  OPEN  the second room's id goes into the first's `open_to`, the schema's word for "this floor is meant".
  WALL  each stretch of the meeting line no partition covers is closed. A partition on that line whose run ends at
        the stretch is extended over it, each of its openings kept where the builder stood it (`snap(pos * run)` from
        the run's middle); otherwise a partition is added for the stretch alone, in the material of the storey's
        partitions. An opening on a crossing wall that a new wall's end would split (layout_lint L18) slides along
        its own wall, whole grid cells away, until the end clears it -- L18's own prescription -- or the pair is
        refused. Then, under DOORWAY_POLICY, one door, as wide as the agent contract's, in the longest stretch
        closed: "keep_pair_joined" (the default) when nothing walkable joins the two rooms any more, so no way the
        open floor gave is lost; "only_if_sealed" only when L12 or L24 would otherwise newly name one of them. Never
        into an objective room (the walker, 2026-10-06: a room reachable only by breaching gets a door unless it is
        the objective). A WALL row that would leave the spec failing any lint rule it passed is taken back whole,
        and the pair is named as refused.
A pair with no row is left alone, and L26 keeps naming it. A spec already sorted is left alone: `apply` twice is
`apply` once. A partition is extended only when every opening it carries is built where it was: the grid places an
opening at `snap(pos * run)` from the run's middle, so a longer run can slide a door by half a cell (measured on
corner_deli_heist_01's `cold_w_access`, 0.125 m), and the stretch then gets a partition of its own.
"""
import copy

import layout_lint

OPEN = "open"
WALL = "wall"

#: One row per pair of room ids, the order inside a pair immaterial. The walker's calls of 2026-10-19 (above).
RULES = {
    # the delis: the service counter divides the floor from the counter, not a wall; the kitchen is its own room
    ("customer_floor", "deli_counter"): OPEN,
    ("market_aisles", "kitchen"): WALL,
    # corner_deli_heist_01's walk-in cold rooms; the stair well between two of them opens onto both, the factory's
    # call where the walker's was WALL: `main_stack` reserves y 6.05..12.65, so a wall on the well's south edge
    # (y 6.25) runs inside the stair and the builder deletes it (L21), and the north edge (y 12.95) ends on the
    # x -13.2 wall at the centre of `cold_n_access` (L18) -- both edges are the stair's own way on and off
    ("cold_storage_w", "cold_storage_s"): WALL,
    ("main_stack_well_b", "cold_storage_n"): OPEN,
    ("main_stack_well_b", "cold_storage_s"): OPEN,
    # the gas stations (see the docstring: the exterior wall already stands there)
    ("forecourt", "sales_floor"): WALL,
    ("forecourt", "stockroom"): WALL,
    ("forecourt", "restroom"): WALL,
    # the upper floors of the auto shops and the pawn shops
    ("upper_office", "upper_storage"): WALL,
    ("apartment", "upper_storage"): WALL,
    # the rowhouse and the walk-up
    ("front_hall", "kitchen"): OPEN,
    ("front_hall", "garage_bay"): WALL,
    ("kitchen", "garage_bay"): WALL,
    ("office", "bedroom"): WALL,
    ("basement_vault", "basement_approach"): WALL,
    # a parking deck is one deck
    ("deck_0_south", "deck_0_main"): OPEN,
    ("deck_1", "deck_1_west"): OPEN,
    # the office: the anteroom opens off its lobby; the ground floor's stair stands on the lobby's edge
    ("exec_lobby", "exec_anteroom"): OPEN,
    ("lobby", "ground_bullpen"): OPEN,
    # the warehouse: the aisles run onto the dock
    ("north_aisles", "north_dock"): OPEN,
}

#: Where a WALL row puts a door. "keep_pair_joined": whenever nothing walkable joins the two rooms once the line is
#: closed. "only_if_sealed": only when layout_lint L12 or L24 would otherwise newly name one of them. A call made
#: 2026-10-19 and meant to be changed.
DOORWAY_POLICY = "keep_pair_joined"
POLICIES = ("keep_pair_joined", "only_if_sealed")

#: A partition counts as on the meeting line, or as ending at a stretch, within this: `tactical.open_edge`'s own
#: tolerance for a partition on the line.
LINE_TOL = 0.05


def rule(a, b):
    """The row for rooms `a` and `b` in either order, or None."""
    return RULES.get((a, b)) or RULES.get((b, a))


def _snap(v, grid):
    return round(v / grid) * grid


def _grid(spec):
    """The spec's grid, or `LevelSpec`'s default when the dict leaves it out: the builder snaps to that one."""
    return float(layout_lint._spec_value(spec, "grid"))


def _ends(spec, p):
    """``(start, end)`` of a partition's run as the builder reads it: the footprint on its axis when unset."""
    hx, hy = float(spec["footprint_x"]) / 2.0, float(spec["footprint_y"]) / 2.0
    lo, hi = (-hx, hx) if p["axis"] == "X" else (-hy, hy)
    s = lo if p.get("start") is None else float(p["start"])
    e = hi if p.get("end") is None else float(p["end"])
    return s, e


def _built_at(spec, p, o):
    """Where the builder stands opening `o` of partition `p` on its line: ``snap(pos * run)`` from the run's middle."""
    s, e = _ends(spec, p)
    return (s + e) / 2.0 + _snap(float(o.get("pos", 0.0)) * (e - s), _grid(spec))


def _stretches(spec, story, axis, line, lo, hi):
    """The stretches of [lo, hi] on the line that no same-axis partition on it covers, longest first."""
    cover = []
    for p in spec.get("partitions") or []:
        if int(p.get("story", 0) or 0) != story or p.get("axis") != axis or abs(float(p["pos"]) - line) >= LINE_TOL:
            continue
        s, e = sorted(_ends(spec, p))
        if min(e, hi) > max(s, lo):
            cover.append((max(s, lo), min(e, hi)))
    out, at = [], lo
    for s, e in sorted(cover):
        if s - at >= LINE_TOL:
            out.append((at, s))
        at = max(at, e)
    if hi - at >= LINE_TOL:
        out.append((at, hi))
    return sorted(out, key=lambda g: g[0] - g[1])


def _extend(spec, p, g0, g1):
    """Extend partition `p`'s run over [g0, g1], keeping each opening where it is built. ``[what moved]``: an
    opening the grid cannot put back exactly where it stood, named with how far."""
    built = [_built_at(spec, p, o) for o in p.get("openings") or ()]
    s, e = _ends(spec, p)
    if abs(max(s, e) - g0) < LINE_TOL:
        if e >= s:
            e = g1
        else:
            s = g1
    else:
        if e >= s:
            s = g0
        else:
            e = g0
    p["start"], p["end"] = s, e
    moved = []
    for o, at in zip(p.get("openings") or (), built):
        o["pos"] = (at - (s + e) / 2.0) / (e - s)
        now = _built_at(spec, p, o)
        if abs(now - at) > 1e-6:
            moved.append("%s %s moved %+.3f m by the grid" % (o.get("kind"), o.get("tag", ""), now - at))
    return moved


def _material(spec, story, axis, line):
    """The material for a new partition: a partition's on the same line, else the storey's commonest, else drywall."""
    same, story_mats = [], {}
    for p in spec.get("partitions") or []:
        if int(p.get("story", 0) or 0) != story or not p.get("material"):
            continue
        story_mats[p["material"]] = story_mats.get(p["material"], 0) + 1
        if p.get("axis") == axis and abs(float(p["pos"]) - line) < LINE_TOL:
            same.append(p["material"])
    if same:
        return same[0]
    if story_mats:
        return sorted(story_mats.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return "drywall"


def _walk_joined(spec, a, b):
    """Is there a walkable opening (layout_lint.WALK_KINDS) straight between rooms `a` and `b`?"""
    edges, _ = layout_lint.graph(spec)
    return any(n == b and k in layout_lint.WALK_KINDS for n, k in edges.get(a, ()))


def _named(spec):
    """The room ids layout_lint L12 or L24 names in `spec`."""
    out = set()
    reach = layout_lint._reach_from_ext(spec)
    walk = layout_lint._reach_from_ext(spec, walk_only=True)
    for r in spec.get("rooms") or []:
        if r["id"] not in reach or r["id"] not in walk:
            out.add(r["id"])
    return out


def _objective(spec, room_id):
    for r in spec.get("rooms") or []:
        if r["id"] == room_id:
            return bool(r.get("objective")) or r.get("role") == "objective_room"
    return False


def _door(spec, p, g0, g1, a, b):
    """Put one door, the agent contract's width, in the middle of [g0, g1] on partition `p`, or say why not."""
    import agent_contract
    width = agent_contract.min_door_width()
    s, e = _ends(spec, p)
    mid = (s + e) / 2.0
    at = mid + _snap((g0 + g1) / 2.0 - mid, _grid(spec))
    if at - width / 2.0 < g0 - 1e-6 or at + width / 2.0 > g1 + 1e-6:
        return None, "no door: %.2f m of new wall cannot hold a %.2f m door clear of its ends" % (g1 - g0, width)
    p.setdefault("openings", []).append({"kind": "door", "pos": (at - mid) / (e - s), "width": width,
                                         "tag": "%s_to_%s" % (a, b)})
    return at, None


def _centre(spec, p, o):
    """Where layout_lint's L18 reads opening `o` of partition `p`: ``pos * run`` from the run's middle, unsnapped
    (`partition_bounds.host_openings`' convention)."""
    s, e = _ends(spec, p)
    return (s + e) / 2.0 + float(o.get("pos", 0.0)) * (e - s)


def _sides(spec, p, at):
    """The rooms either side of partition `p` at `at` along it, as layout_lint's graph reads a doorway."""
    rooms = layout_lint._rooms_by_story(spec).get(int(p.get("story", 0) or 0), [])
    line = float(p["pos"])
    if p["axis"] == "X":
        pts = ((at, line - 0.6), (at, line + 0.6))
    else:
        pts = ((line - 0.6, at), (line + 0.6, at))
    got = [layout_lint._room_at(rooms, x, y) for x, y in pts]
    return tuple(r["id"] if r else None for r in got)


def _clear_apertures(spec, term):
    """Slide each opening a new wall's end would split (layout_lint L18) along its own wall, whole grid cells away
    from the end, until the end clears it: L18's own prescription, "nudge the opening along its wall". It stays on its
    wall's run, clear of the wall's other openings and of every other wall ending on it, and between the same two
    rooms, or it does not move. ``[what slid]`` and ``[what could not]``."""
    import partition_bounds
    grid = _grid(spec)
    margin = layout_lint.LEAF_MARGIN
    meet = float(layout_lint._spec_value(spec, "wall_thick")) + 0.05
    fx, fy = float(spec["footprint_x"]), float(spec["footprint_y"])
    t_ax, t_pos = term["axis"], float(term["pos"])
    t_story = int(term.get("story", 0) or 0)
    lo, hi = partition_bounds.clamp_partition_span(*_ends(spec, term), t_ax, fx, fy)
    moved, stuck = [], []
    parts = spec.get("partitions") or []
    for end in (lo, hi):
        for host in parts:
            if host is term or host.get("axis") == t_ax or int(host.get("story", 0) or 0) != t_story:
                continue
            if abs(end - float(host["pos"])) > meet:
                continue
            h_lo, h_hi = sorted(_ends(spec, host))
            others = [q for q in parts if q is not host and q.get("axis") != host.get("axis")
                      and int(q.get("story", 0) or 0) == t_story
                      and any(abs(v - float(host["pos"])) <= meet
                              for v in partition_bounds.clamp_partition_span(*_ends(spec, q), q["axis"], fx, fy))]
            for o in host.get("openings") or []:
                w = float(o.get("width", 1.0))
                need = w / 2.0 + margin
                c = _centre(spec, host, o)
                if abs(t_pos - c) >= need:
                    continue
                s, e = _ends(spec, host)
                mid, run = (s + e) / 2.0, e - s
                built = _built_at(spec, host, o)
                rooms = _sides(spec, host, built)
                away = 1.0 if c > t_pos or (c == t_pos and mid > t_pos) else -1.0
                done = False
                for k in range(1, 7):                  # at most 3 m, on the builder's grid
                    at = built + away * k * grid
                    if abs(t_pos - at) < need:
                        continue
                    if at - w / 2.0 < h_lo + margin or at + w / 2.0 > h_hi - margin:
                        break                          # off its wall's run
                    if any(abs(at - _centre(spec, host, o2)) < (w + float(o2.get("width", 1.0))) / 2.0 + margin
                           for o2 in host.get("openings") or [] if o2 is not o):
                        continue                       # onto another opening
                    if any(abs(float(q["pos"]) - at) < need for q in others):
                        continue                       # onto another wall's end
                    if _sides(spec, host, at) != rooms:
                        break                          # between other rooms
                    o["pos"] = (at - mid) / run
                    moved.append("%s %s slid %+.2f m along its wall to clear the new wall's end (L18)"
                                 % (o.get("kind", "door"), o.get("tag", ""), at - built))
                    done = True
                    break
                if not done:
                    stuck.append("%s %s" % (o.get("kind", "door"), o.get("tag", "")))
    return moved, stuck


def _fail_codes(spec):
    """How many of each layout_lint FAIL `spec` carries, by rule: ``{"L18": 1, ...}``."""
    _name, fails, _warns = layout_lint.lint_spec(spec, spec.get("name", "?"))
    out = {}
    for f in fails:
        code = f.split(" ", 1)[0]
        out[code] = out.get(code, 0) + 1
    return out


def apply(spec, policy=None):
    """Sort `spec`'s open floors by `RULES`, in place. ``[what changed]``, empty when nothing did.

    A WALL row is applied to one pair at a time, and taken back whole when it would leave the spec failing a lint
    rule it passed -- a wall through a stair's reservation (L21), say, or a doorway it could not clear (L18) -- so the
    table never writes a wall the builder or the lint refuses; the pair is named as refused and L26 keeps naming it."""
    policy = policy or DOORWAY_POLICY
    if policy not in POLICIES:
        raise ValueError("doorway policy %r, not one of %s" % (policy, ", ".join(POLICIES)))
    said = []
    named_before = _named(spec) if policy == "only_if_sealed" else set()
    for f in layout_lint.open_floors(spec):
        a, b, st = f["a"], f["b"], f["story"]
        row = rule(a, b)
        if row is None:
            continue
        if row == OPEN:
            room = [r for r in spec["rooms"] if r["id"] == a and int(r.get("story", 0) or 0) == st][0]
            if b not in (room.get("open_to") or []):
                room["open_to"] = sorted(set(room.get("open_to") or []) | {b})
                said.append("%s|%s (story %d) open: %s.open_to += %s" % (a, b, st, a, b))
            continue
        if not _stretches(spec, st, f["axis"], f["pos"], f["lo"], f["hi"]):
            continue
        before, fails_before = copy.deepcopy(spec), _fail_codes(spec)
        lines = _close(spec, f, a, b, st, policy, named_before)
        fails_after = _fail_codes(spec)
        worse = sorted(k for k, n in fails_after.items() if n > fails_before.get(k, 0))
        if worse:
            spec.clear()
            spec.update(before)
            said.append("%s|%s (story %d): REFUSED -- closing it would fail %s; left open, and L26 names it"
                        % (a, b, st, ", ".join(worse)))
            continue
        said.extend(lines)
    return said


def _close(spec, f, a, b, st, policy, named_before):
    """Close one WALL pair's stretches, slide clear what the new walls would split, then the door. ``[what changed]``."""
    said = []
    axis, line = f["axis"], f["pos"]
    closed = []
    for g0, g1 in _stretches(spec, st, axis, line, f["lo"], f["hi"]):
        on_line = [p for p in spec.get("partitions") or []
                   if int(p.get("story", 0) or 0) == st and p.get("axis") == axis
                   and abs(float(p["pos"]) - line) < LINE_TOL]
        ends_here = [p for p in on_line
                     if abs(max(_ends(spec, p)) - g0) < LINE_TOL or abs(min(_ends(spec, p)) - g1) < LINE_TOL]
        moved = []
        if ends_here:
            # extended only when every opening it carries stays where it is built; else a piece of its own
            moved = _extend(spec, copy.deepcopy(ends_here[0]), g0, g1)
        if ends_here and not moved:
            p = ends_here[0]
            _extend(spec, p, g0, g1)
            said.append("%s|%s (story %d) wall: the %s-partition at %s %g extended over %g..%g"
                        % (a, b, st, axis, "y" if axis == "X" else "x", line, g0, g1))
        else:
            p = {"story": st, "axis": axis, "pos": line, "start": g0, "end": g1,
                 "material": ends_here[0].get("material") if ends_here and ends_here[0].get("material")
                 else _material(spec, st, axis, line), "openings": []}
            spec.setdefault("partitions", []).append(p)
            said.append("%s|%s (story %d) wall: a %s-partition added at %s %g, %g..%g%s"
                        % (a, b, st, axis, "y" if axis == "X" else "x", line, g0, g1,
                           (" -- extending the one beside it would have moved its " + "; ".join(moved))
                           if moved else ""))
        closed.append((g1 - g0, g0, g1, p))
    for _n, _g0, _g1, p in closed:
        slid, _stuck = _clear_apertures(spec, p)
        said.extend("%s|%s: %s" % (a, b, x) for x in slid)
    if not closed:
        return said
    if _objective(spec, a) or _objective(spec, b):
        if not _walk_joined(spec, a, b):
            said.append("%s|%s: no door -- %s is the objective, kept behind what it had"
                        % (a, b, a if _objective(spec, a) else b))
        return said
    if policy == "keep_pair_joined":
        want = not _walk_joined(spec, a, b)
    else:
        want = bool(({a, b} & _named(spec)) - named_before)
    if not want:
        return said
    _, g0, g1, p = max(closed, key=lambda c: (c[0], -c[1]))
    at, why = _door(spec, p, g0, g1, a, b)
    said.append("%s|%s: %s" % (a, b, why if why else "a door at %s %+.2f, tagged %s_to_%s"
                               % ("x" if axis == "X" else "y", at, a, b)))
    return said
