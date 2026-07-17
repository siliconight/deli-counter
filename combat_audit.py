#!/usr/bin/env python3
"""
combat_audit.py  --  structural FPS-combat audit for building specs
===================================================================
The existing checkers answer "is it buildable / reachable / sane?". This one
answers "will it FIGHT well?" -- 4-player PvE co-op FPS combat lives or dies
on structure the other gates don't measure:

  LOOPS      route-graph cycles. Zero loops = a tree = every fight is a
             one-corridor siege; players can never flank, AI can never
             surprise. Interior loops are the single biggest lever.
  CHOKES     articulation rooms (removing one disconnects the graph). A few
             are good drama; a graph that is ALL chokepoints is a slog.
  DEAD ENDS  degree-1 rooms. Fine for closets; bad for combat rooms; a
             dead-end OBJECTIVE room turns the climax into door-camping.
  FACES      which building faces carry entries. One-face entry = attackers
             and reinforcements all use the same funnel; no exterior flank.
  WIDTH      a 1.1-1.2 m door passes ONE agent. Co-op wants at least one
             wide (>=1.4 m) route toward the objective or fights stack up
             in frames.
  VERTICAL   an upper story with exactly one way up is a vertical dead end:
             the whole floor plays as one siege. Two+ links make it a level.
  COVER      combat-range rooms >35 m^2 with no waist-high volume and no
             cover markers = open kill boxes.
  CRAMP      rooms narrower than ~2.2 m that author a combat_range: four
             capsules + enemies do not fit.

USAGE
-----
    python combat_audit.py specs/bank.json          # one spec
    python combat_audit.py --preset gas_station     # one preset (fresh)
    python combat_audit.py --all-presets            # every gameplay preset
    python combat_audit.py --all                    # every spec in specs/

Severity: HIGH structural combat problems; MED costs fun but playable; INFO
context. This is a structural estimate, not a measure of fun -- walk it.
"""

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets as presets_mod                       # noqa: E402
import tactical                                     # noqa: E402
import sightlines                                   # noqa: E402
from spec_loader import spec_from_dict, load_spec   # noqa: E402

WIDE_DOOR = 1.4          # >= passes two agents / a loot carry comfortably
KIND_DEFAULT_W = {"door": 1.2, "window": 1.6, "garage": 3.5, "breach": 1.5,
                  "vault": 1.4, "teller": 2.0, "safe_deposit": 2.0}


def _op_width(op):
    w = getattr(op, "width", None)
    return w if w is not None else KIND_DEFAULT_W.get(op.kind, 1.2)
CRAMP_MIN_DIM = 2.2      # a combat room narrower than this can't hold a fight
KILLBOX_AREA = 35.0      # combat room bigger than this with no cover = flag
COVER_MIN_H = 0.6        # >= waist high; taller solids block sight = also cover
UTILITY_ROLES = {"utility", "restroom", "storage", "closet"}


# ---------------------------------------------------------------------------
# graph helpers
# ---------------------------------------------------------------------------
def _degrees(adj):
    return {n: len(adj.get(n, ())) for n in adj}


def _components(adj):
    seen, comps = set(), 0
    for n in adj:
        if n in seen:
            continue
        comps += 1
        stack = [n]
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            seen.add(c)
            stack.extend(adj.get(c, ()))
    return comps


def _articulation_points(adj):
    """Tarjan. Rooms whose removal disconnects the route graph."""
    disc, low, ap = {}, {}, set()
    t = [0]

    def dfs(u, parent):
        disc[u] = low[u] = t[0]
        t[0] += 1
        children = 0
        for v in adj.get(u, ()):
            if v == parent:
                continue
            if v in disc:
                low[u] = min(low[u], disc[v])
            else:
                children += 1
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if parent is not None and low[v] >= disc[u]:
                    ap.add(u)
        if parent is None and children > 1:
            ap.add(u)

    for n in list(adj):
        if n not in disc:
            dfs(n, None)
    return ap


def _bfs_dist(adj, srcs):
    dist = {s: 0 for s in srcs if s in adj}
    frontier = list(dist)
    while frontier:
        nxt = []
        for u in frontier:
            for v in adj.get(u, ()):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    nxt.append(v)
        frontier = nxt
    return dist


# ---------------------------------------------------------------------------
# spec helpers
# ---------------------------------------------------------------------------
def _room_by_id(spec):
    return {r.id: r for r in spec.rooms}


def _room_area(r):
    x0, y0, x1, y1 = r.bounds
    return max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))


def _room_min_dim(r):
    x0, y0, x1, y1 = r.bounds
    return min(x1 - x0, y1 - y0)


def _is_utility(r):
    if (r.role or "") in UTILITY_ROLES:
        return True
    return _room_area(r) < 8.0 and not getattr(r, "combat_range", None)


def _is_outdoor(spec, r):
    """Outside-the-footprint grade room (forecourt, yard): open ground, so a
    graph 'dead end' there is not a siege -- it's approachable from anywhere
    outside. Mirrors tactical's outdoor-entry rule."""
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    x0, y0, x1, y1 = r.bounds
    ix = max(0.0, min(x1, hx) - max(x0, -hx))
    iy = max(0.0, min(y1, hy) - max(y0, -hy))
    return (ix * iy) / max(1e-9, _room_area(r)) < 0.1


def _objective_rooms(spec):
    """Rooms holding an objective marker or authored as objective_room."""
    out = set()
    rooms = list(spec.rooms)
    for r in rooms:
        if (r.role or "") == "objective_room":
            out.add(r.id)
    for m in spec.markers:
        if getattr(m, "type", None) == "objective":
            # the marker's own room wins; else derive the story from z --
            # never guess story 0 (a count room above a kitchen would claim
            # the kitchen too)
            rid = getattr(m, "room", None)
            if not rid:
                st = int(round(getattr(m, "z", 0.0) // max(spec.story_height, 1)))
                rid = tactical._room_at(spec, st, m.x, m.y)
            if rid:
                out.add(rid)
    return out


def _entry_faces(spec):
    faces = set()
    for w in spec.ext_walls:
        for op in w.openings:
            if op.kind in ("door", "garage", "breach") or getattr(op, "vaultable", False):
                faces.add(w.wall)
    return faces


def _openings_into(spec, room_id):
    """(width, kind, where) of every opening bordering this room."""
    out = []
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    r = _room_by_id(spec)[room_id]
    eps = 0.8
    for p in spec.partitions:
        along_axis = p.axis
        for op in p.openings:
            run = abs(p.end - p.start)
            u = p.start + (op.pos + 0.5) * run if abs(op.pos) <= 0.5 else op.pos
            # tactical convention: pos is normalized along the partition span
            u = p.start + (op.pos + 0.5) * run
            if along_axis == "Y":
                a = tactical._room_at(spec, p.story, p.pos - eps, u)
                b = tactical._room_at(spec, p.story, p.pos + eps, u)
            else:
                a = tactical._room_at(spec, p.story, u, p.pos - eps)
                b = tactical._room_at(spec, p.story, u, p.pos + eps)
            if room_id in (a, b):
                out.append((_op_width(op), op.kind, "partition"))
    for w in spec.ext_walls:
        run = spec.footprint_x if w.wall in ("N", "S") else spec.footprint_y
        for op in w.openings:
            if op.kind not in ("door", "garage", "breach") and \
                    not getattr(op, "vaultable", False):
                continue
            u = op.pos * run
            if w.wall == "N":
                a = tactical._room_at(spec, w.story, u, hy - eps)
            elif w.wall == "S":
                a = tactical._room_at(spec, w.story, u, -hy + eps)
            elif w.wall == "E":
                a = tactical._room_at(spec, w.story, hx - eps, u)
            else:
                a = tactical._room_at(spec, w.story, -hx + eps, u)
            if a == room_id:
                out.append((_op_width(op), op.kind, f"ext {w.wall}"))
    return out


def _cover_in_room(spec, r):
    n = 0
    for v in spec.volumes:
        # anything solid and at least waist-high breaks sightlines: crates,
        # counters, machines, pillars, shelving, the vault box itself
        if v.size_z < COVER_MIN_H or min(v.size_x, v.size_y) < 0.3:
            continue
        x0, y0, x1, y1 = r.bounds
        if x0 <= v.x <= x1 and y0 <= v.y <= y1:
            base = getattr(v, "z", 0.0)
            if abs(base - r.story * spec.story_height) < spec.story_height:
                n += 1
    for m in spec.markers:
        if getattr(m, "type", "") in ("cover_low", "cover_high"):
            x0, y0, x1, y1 = r.bounds
            if x0 <= m.x <= x1 and y0 <= m.y <= y1:
                n += 1
    return n


def _vertical_links(spec):
    """story-pair -> number of independent vertical connections."""
    pairs = {}
    for s in spec.stairs:
        lo, hi = sorted((s.from_story, s.to_story))
        for st in range(lo, hi):
            pairs[(st, st + 1)] = pairs.get((st, st + 1), 0) + 1
    for l in getattr(spec, "ladders", []) or []:
        lo, hi = sorted((l.from_story, l.to_story))
        for st in range(lo, hi):
            pairs[(st, st + 1)] = pairs.get((st, st + 1), 0) + 1
    for rp in getattr(spec, "ramps", []) or []:
        lo, hi = sorted((rp.from_story, rp.to_story))
        for st in range(lo, hi):
            pairs[(st, st + 1)] = pairs.get((st, st + 1), 0) + 1
    return pairs


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------
# ===========================================================================
# genre rule packs -- PayDay 2 / Ready or Not / Left 4 Dead 2 grammars
# Enabled with --rules; "auto" picks packs by spec mode. Full rationale and
# authoring guidance in docs/DESIGN_RULES.md.
# ===========================================================================

def _opening_points(spec, room_id):
    """World-space points of every opening bordering room_id:
    (x, y, width, kind, other_room_or_None, is_ext)."""
    out = []
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    eps = 0.8
    for p in spec.partitions:
        run = abs(p.end - p.start)
        for op in p.openings:
            if op.kind not in ("door", "garage", "breach"):
                continue
            u = p.start + (op.pos + 0.5) * run
            if p.axis == "Y":
                a = tactical._room_at(spec, p.story, p.pos - eps, u)
                b = tactical._room_at(spec, p.story, p.pos + eps, u)
                pt = (p.pos, u)
            else:
                a = tactical._room_at(spec, p.story, u, p.pos - eps)
                b = tactical._room_at(spec, p.story, u, p.pos + eps)
                pt = (u, p.pos)
            if room_id in (a, b):
                other = b if a == room_id else a
                out.append((pt[0], pt[1], _op_width(op), op.kind, other, False))
    for w in spec.ext_walls:
        run = spec.footprint_x if w.wall in ("N", "S") else spec.footprint_y
        for op in w.openings:
            if op.kind not in ("door", "garage", "breach") and \
                    not getattr(op, "vaultable", False):
                continue
            u = op.pos * run
            x, y = {"N": (u, hy), "S": (u, -hy),
                    "E": (hx, u), "W": (-hx, u)}[w.wall]
            ex, ey = {"N": (u, hy - eps), "S": (u, -hy + eps),
                      "E": (hx - eps, u), "W": (-hx + eps, u)}[w.wall]
            if tactical._room_at(spec, w.story, ex, ey) == room_id:
                out.append((x, y, _op_width(op), op.kind, None, True))
    return out


def _seg_hits_rect(x1, y1, x2, y2, rx0, ry0, rx1, ry1):
    """Does segment (x1,y1)-(x2,y2) intersect axis-aligned rect?"""
    # trivial accept if either end inside
    if rx0 <= x1 <= rx1 and ry0 <= y1 <= ry1:
        return True
    if rx0 <= x2 <= rx1 and ry0 <= y2 <= ry1:
        return True
    def _cross(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    def _seg_seg(ax, ay, bx, by, cx, cy, dx, dy):
        d1 = _cross(cx, cy, dx, dy, ax, ay)
        d2 = _cross(cx, cy, dx, dy, bx, by)
        d3 = _cross(ax, ay, bx, by, cx, cy)
        d4 = _cross(ax, ay, bx, by, dx, dy)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))
    edges = (((rx0, ry0), (rx1, ry0)), ((rx1, ry0), (rx1, ry1)),
             ((rx1, ry1), (rx0, ry1)), ((rx0, ry1), (rx0, ry0)))
    return any(_seg_seg(x1, y1, x2, y2, a[0], a[1], b[0], b[1])
               for a, b in edges)


def _threshold_visibility(spec, room, door_pt):
    """Fraction of the room's floor visible from a point 0.5 m inside the
    threshold, occluded by solid volumes (>= 0.9 m tall) in the room.
    The Ready or Not 'first slice' number: how much of the room can be
    cleared from the doorway before committing."""
    x0, y0, x1, y1 = room.bounds
    cx = min(max(door_pt[0], x0 + 0.5), x1 - 0.5)
    cy = min(max(door_pt[1], y0 + 0.5), y1 - 0.5)
    blockers = []
    sh = spec.story_height
    for v in spec.volumes:
        if v.size_z < 0.9:
            continue
        base = getattr(v, "z", 0.0) - v.size_z / 2
        if abs(base - room.story * sh) > 1.0:
            continue
        if x0 <= v.x <= x1 and y0 <= v.y <= y1:
            blockers.append((v.x - v.size_x / 2, v.y - v.size_y / 2,
                             v.x + v.size_x / 2, v.y + v.size_y / 2))
    # nudge the vantage toward the room centroid (an entering player steps
    # in, not stands in the frame) and never count a blocker the vantage is
    # inside of -- that's the ray-caster blinding itself
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = mx - cx, my - cy
    d = max(0.001, (dx * dx + dy * dy) ** 0.5)
    cx, cy = cx + dx / d * 0.8, cy + dy / d * 0.8
    blockers = [b for b in blockers
                if not (b[0] <= cx <= b[2] and b[1] <= cy <= b[3])]
    n = vis = 0
    for i in range(8):
        for j in range(8):
            px = x0 + (i + 0.5) * (x1 - x0) / 8
            py = y0 + (j + 0.5) * (y1 - y0) / 8
            n += 1
            if not any(_seg_hits_rect(cx, cy, px, py, *b) for b in blockers):
                vis += 1
    return vis / max(1, n)


def _width_graph(spec, min_w):
    """Room adjacency using only openings >= min_w (open-plan edges count
    as infinitely wide). The loot-carry graph."""
    adj = {r.id: set() for r in spec.rooms}
    for r in spec.rooms:
        for (x, y, w, kind, other, is_ext) in _opening_points(spec, r.id):
            if other and w >= min_w:
                adj[r.id].add(other)
                adj[other].add(r.id)
    full = tactical.build_graph(spec)
    for a, ns in full.items():
        for b in ns:
            if a in adj and b in adj[a]:
                continue
            # keep edges that come from open-plan sharing or verticals only
            # if they aren't width-limited doors -- open plan is carry-wide;
            # verticals: stairs carry bags, ladders don't
            pass
    # open-plan edges: recompute cheaply via bounds sharing (mirrors tactical)
    rl = list(spec.rooms)
    for i, ra in enumerate(rl):
        for rb in rl[i + 1:]:
            if ra.story != rb.story:
                continue
            ax0, ay0, ax1, ay1 = ra.bounds
            bx0, by0, bx1, by1 = rb.bounds
            share = 0.0
            if abs(ax1 - bx0) < 0.05 or abs(bx1 - ax0) < 0.05:
                share = min(ay1, by1) - max(ay0, by0)
            if abs(ay1 - by0) < 0.05 or abs(by1 - ay0) < 0.05:
                share = max(share, min(ax1, bx1) - max(ax0, bx0))
            if share >= 1.2 and rb.id in tactical.build_graph(spec).get(ra.id, ()):
                adj[ra.id].add(rb.id)
                adj[rb.id].add(ra.id)
    # stairs carry bags
    for s in spec.stairs:
        lo, hi = sorted((s.from_story, s.to_story))
        for st in range(lo, hi):
            a = tactical._room_at(spec, st, s.x, s.y)
            b = tactical._room_at(spec, st + 1, s.x, s.y)
            if a and b and a in adj and b in adj:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def _disjoint_paths2(adj, srcs, dst):
    """Are there >= 2 interior-node-disjoint routes from any sources to dst?
    Greedy: find one BFS path, delete its interior, search again."""
    def bfs(block):
        prev = {}
        seen = set(s for s in srcs if s in adj and s not in block)
        q = list(seen)
        while q:
            u = q.pop(0)
            if u == dst:
                path = [u]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return path
            for v in adj.get(u, ()):
                if v in seen or v in block:
                    continue
                seen.add(v)
                prev[v] = u
                q.append(v)
        return None
    p1 = bfs(set())
    if not p1:
        return 0
    interior = set(p1) - set(srcs) - {dst}
    return 2 if bfs(interior) else 1


# --- PayDay 2: the heist grammar ------------------------------------------
def _pack_heist(spec, ctx, F):
    adj, entries, objectives, rooms = (ctx["adj"], ctx["entries"],
                                       ctx["objectives"], ctx["rooms"])
    for ob in sorted(objectives):
        if ob not in adj:
            continue
        n = _disjoint_paths2(adj, entries, ob)
        if n == 1 and len(adj) >= 4:
            F(("MED", "H_ONE_ROUTE",
               f"[heist] every route to objective '{ob}' funnels through the "
               f"same rooms: one crew plan, no split assault. A second "
               f"disjoint approach (breach wall, window vault, vertical) "
               f"makes plans differ."))
        # holdout: the drill-defense space -- objective room or a neighbor
        # with 2-3 coverable ways in and something to hide behind
        cands = [ob] + sorted(adj.get(ob, ()))
        best = None
        for c in cands:
            r = rooms.get(c)
            if not r:
                continue
            ops = _openings_into(spec, c)
            n_in = len(ops)
            if 2 <= n_in <= 3 and _room_area(r) >= 12 and \
                    (_cover_in_room(spec, r) > 0 or
                     (r.role or "") == "fortifiable"):
                best = c
                break
        if best is None:
            F(("MED", "H_NO_HOLDOUT",
               f"[heist] no defensible holdout at/next to objective '{ob}' "
               f"(want a room with 2-3 coverable entries, >= 12 m^2, and "
               f"cover): the drill/objective-wait phase has nowhere to "
               f"fight from."))
    # loot carry: from each objective, a >= 1.2 m route must reach a
    # >= 1.4 m exterior egress (bags don't fit through squeezes)
    wg = _width_graph(spec, 1.2)
    wide_exits = set()
    for r in spec.rooms:
        for (x, y, w, kind, other, is_ext) in _opening_points(spec, r.id):
            if is_ext and w >= 1.4:
                wide_exits.add(r.id)
    for ob in sorted(objectives):
        if ob not in wg:
            continue
        seen, q = {ob}, [ob]
        hit = ob in wide_exits
        while q and not hit:
            u = q.pop(0)
            for v in wg.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    q.append(v)
                    if v in wide_exits:
                        hit = True
                        break
        if not hit:
            F(("MED", "H_CARRY_PINCH",
               f"[heist] no bag-carry route from objective '{ob}' to a "
               f">= 1.4 m exterior egress using only >= 1.2 m openings: "
               f"the loot leaves single-file through a pinch."))
    if getattr(spec, "mode", None) == "heist":
        cams = sum(1 for m in spec.markers
                   if getattr(m, "type", "") == "camera_socket")
        pats = sum(1 for m in spec.markers
                   if getattr(m, "type", "") == "patrol_point")
        if cams == 0 and pats == 0:
            F(("INFO", "H_NO_STEALTH",
               "[heist] no camera_socket or patrol_point markers: the map "
               "has no stealth layer to beat -- loud-only by construction."))


# --- Ready or Not: the CQB grammar ----------------------------------------
def _pack_cqb(spec, ctx, F):
    rooms, objectives = ctx["rooms"], ctx["objectives"]
    hot = [r for r in spec.rooms
           if r.id in objectives or (r.role or "") == "fortifiable"]
    for r in hot:
        x0, y0, x1, y1 = r.bounds
        for (dx, dy, w, kind, other, is_ext) in _opening_points(spec, r.id):
            if kind not in ("door", "breach"):
                continue
            # feed type: distance from the door to the nearest corner along
            # its wall. Corner-fed doors give the entry team one hard angle;
            # center-fed doors expose them to both flanks at once.
            on_x_wall = min(abs(dy - y0), abs(dy - y1)) < 0.3
            along = dx if on_x_wall else dy
            lo, hi = (x0, x1) if on_x_wall else (y0, y1)
            corner_d = min(along - lo, hi - along)
            fed = "corner" if corner_d <= 1.5 else "center"
            # pie standoff: room to work the angle from outside the door
            if not is_ext and other in rooms:
                o = rooms[other]
                ox0, oy0, ox1, oy1 = o.bounds
                depth = min(dx - ox0, ox1 - dx) if not on_x_wall else \
                        min(dy - oy0, oy1 - dy)
                room_depth = min(ox1 - ox0, oy1 - oy0)
                if room_depth < 1.6:
                    F(("MED", "C_NO_PIE",
                       f"[cqb] the approach to '{r.id}' via '{other}' is "
                       f"{room_depth:.1f} m deep at the door: no room to pie "
                       f"the threshold -- the stack breaches blind."))
            # (threshold visibility judged per-room below, on the best door)
    # threshold visibility per room, judged on the BEST door: the entry
    # team picks its threshold, so a room is only blind if EVERY way in is
    # blind, and only naked if every way in sees everything.
    for r in hot:
        doors = [(dx, dy) for (dx, dy, w, k, o, e) in
                 _opening_points(spec, r.id) if k in ("door", "breach")]
        if not doors:
            continue
        vises = [_threshold_visibility(spec, r, d) for d in doors]
        best = max(vises)
        if best > 0.97 and _room_area(r) >= 25 and \
                _cover_in_room(spec, r) == 0:
            F(("MED", "C_NAKED_ROOM",
               f"[cqb] '{r.id}': every doorway sees "
               f"{best * 100:.0f}% of the room -- nothing to clear, nowhere "
               f"to hide. One or two hard corners or tall blockers give the "
               f"entry a decision."))
        elif best < 0.35:
            F(("MED", "C_BLIND_ROOM",
               f"[cqb] '{r.id}': the BEST doorway sees only "
               f"{best * 100:.0f}% of the room -- every entry commits blind "
               f"into hard corners, grenade-bait. Open the first slice from "
               f"at least one threshold to ~50-90%."))

    # census: all-center-fed maps play monotone
    feeds = {"corner": 0, "center": 0}
    for r in spec.rooms:
        x0, y0, x1, y1 = r.bounds
        for (dx, dy, w, kind, other, is_ext) in _opening_points(spec, r.id):
            if kind != "door" or is_ext:
                continue
            on_x_wall = min(abs(dy - y0), abs(dy - y1)) < 0.3
            along = dx if on_x_wall else dy
            lo, hi = (x0, x1) if on_x_wall else (y0, y1)
            fed = "corner" if min(along - lo, hi - along) <= 1.5 else "center"
            feeds[fed] += 1
    tot = feeds["corner"] + feeds["center"]
    if tot >= 6 and (feeds["corner"] == 0 or feeds["center"] == 0):
        only = "corner" if feeds["center"] == 0 else "center"
        F(("INFO", "C_FEED_MONOTONE",
           f"[cqb] all {tot} interior doors are {only}-fed: every room "
           f"clears the same way. Mixing feed types varies the entries."))


# --- Left 4 Dead 2: the flow grammar --------------------------------------
def _pack_flow(spec, ctx, F):
    adj, entries, objectives, rooms = (ctx["adj"], ctx["entries"],
                                       ctx["objectives"], ctx["rooms"])
    # golden path: entries -> primary objective (BFS)
    dst = next(iter(sorted(objectives)), None)
    path = None
    if dst and dst in adj:
        prev, seen = {}, set(s for s in entries if s in adj)
        q = list(seen)
        while q:
            u = q.pop(0)
            if u == dst:
                path = [u]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                path.reverse()
                break
            for v in adj.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    prev[v] = u
                    q.append(v)
    if path and len(path) >= 4:
        areas = [_room_area(rooms[r]) for r in path if r in rooms]
        import math as _m
        monotone = all(abs(_m.log(max(areas[i + 1], 1) / max(areas[i], 1)))
                       < 0.35 for i in range(len(areas) - 1))
        if monotone:
            F(("MED", "F_FLAT_RHYTHM",
               f"[flow] the entry->objective path "
               f"({' -> '.join(path)}) never changes scale: no "
               f"compression/release rhythm, the run reads as one long "
               f"corridor. Alternate tight connectors with open rooms."))
        for rid in path:
            if len(adj.get(rid, ())) >= 5:
                F(("INFO", "F_BRANCH_OVERLOAD",
                   f"[flow] '{rid}' on the main path has "
                   f"{len(adj[rid])} connections: heavy wayfinding load at "
                   f"one decision point."))
    # holdout arenas need horde ingress: >= 3 ways in, not all one face
    # horde-arena rules apply to horde contexts: finale rooms always, and
    # fortifiable/objective rooms only in survival/assault modes. A heist
    # drill room WANTS 2-3 coverable entries (the PayDay holdout rule);
    # demanding >= 3 ingress there would contradict the heist grammar.
    horde_mode = getattr(spec, "mode", "") in ("survival", "assault")
    arena_ids = set()
    for r in spec.rooms:
        if (r.role or "") == "finale" or \
                (horde_mode and ((r.role or "") == "fortifiable"
                                 or r.id in objectives)):
            arena_ids.add(r.id)
    for a in sorted(arena_ids):
        r = rooms.get(a)
        if not r:
            continue
        ops = _opening_points(spec, a)
        n_in = len(ops) + sum(1 for s in spec.stairs
                              if tactical._room_at(spec, s.to_story, s.x, s.y) == a
                              or tactical._room_at(spec, s.from_story, s.x, s.y) == a)
        if n_in < 3:
            F(("MED", "F_ARENA_STARVED",
               f"[flow] holdout room '{a}' has only {n_in} way(s) in: the "
               f"horde single-files and the holdout is a shooting gallery. "
               f"Arenas want >= 3 ingress vectors from >= 2 directions."))
    if getattr(spec, "mode", "") == "survival":
        hs = sum(1 for m in spec.markers
                 if getattr(m, "type", "") == "horde_spawn")
        if hs < 3:
            F(("INFO", "F_FEW_HORDE_SPAWNS",
               f"[flow] only {hs} horde_spawn marker(s): director has few "
               f"ingress choices; waves will feel same-y."))


RULE_PACKS = {"heist": _pack_heist, "cqb": _pack_cqb, "flow": _pack_flow}


def packs_for(spec, rules_arg):
    if rules_arg in (None, "", "none"):
        return []
    if rules_arg == "all":
        return list(RULE_PACKS)
    if rules_arg == "auto":
        mode = getattr(spec, "mode", None) or "heist"
        return (["heist", "cqb", "flow"] if mode in ("heist", "pvp_heist")
                else ["flow", "cqb"])
    return [r.strip() for r in rules_arg.split(",") if r.strip() in RULE_PACKS]


def audit(spec, name=None, rules=None):
    name = name or spec.name
    findings = []          # (severity, code, message)
    F = findings.append

    adj = tactical.build_graph(spec)
    info = {}
    rooms = _room_by_id(spec)
    entries = tactical._entry_rooms(spec)
    objectives = _objective_rooms(spec)

    # --- topology
    n_nodes = len(adj)
    n_edges = sum(len(v) for v in adj.values()) // 2
    comps = _components(adj)
    loops = n_edges - n_nodes + comps
    degs = _degrees(adj)
    dead = [r for r, d in degs.items() if d <= 1 and r in rooms
            and not _is_utility(rooms[r]) and not _is_outdoor(spec, rooms[r])]
    chokes = {a for a in _articulation_points(adj)
              if a in rooms and _room_area(rooms[a]) >= 4.0}

    if loops == 0 and n_nodes >= 4:
        F(("HIGH", "NO_LOOPS",
           "route graph is a pure tree (0 interior loops): every fight is a "
           "one-corridor siege; no flanking for players or AI. Add at least "
           "one second connection between wings (a door, a breach wall, a "
           "window vault)."))
    elif n_nodes >= 6 and loops == 1:
        F(("MED", "ONE_LOOP",
           f"only 1 interior loop across {n_nodes} rooms; combat will settle "
           f"into one circuit. A second loop (upper story or back-of-house) "
           f"adds real route choice."))
    for r in dead:
        sev = "HIGH" if r in objectives else "MED"
        why = ("objective room is a dead end: the climax becomes door-camping "
               "one threshold" if r in objectives else
               "combat-intent room is a dead end (one way in = one way out)")
        F((sev, "DEAD_END", f"'{r}': {why}."))
    if n_nodes >= 5 and len(chokes) >= max(2, n_nodes // 3):
        F(("MED", "CHOKE_HEAVY",
           f"{len(chokes)}/{n_nodes} rooms are articulation chokepoints "
           f"({', '.join(sorted(chokes))}): most of the building funnels "
           f"through single rooms."))

    # --- entries / faces
    faces = _entry_faces(spec)
    n_entries = info.get("entries") if isinstance(info, dict) else None
    if len(faces) <= 1 and spec.footprint_x >= 10 and spec.footprint_y >= 10:
        F(("HIGH", "ONE_FACE",
           f"all exterior entries sit on {sorted(faces) or 'no'} face(s): "
           f"no exterior flank pressure is possible; attackers and "
           f"reinforcements share one funnel. Add a rear/side door, breach "
           f"panel, or vault window on another face."))
    elif len(faces) == 2 and {"N", "S"} != faces and {"E", "W"} != faces:
        F(("INFO", "ADJACENT_FACES",
           f"entries on adjacent faces only ({sorted(faces)}); opposite-face "
           f"entries create the strongest flank geometry."))

    # --- width ladder toward objectives
    for ob in sorted(objectives):
        ops = _openings_into(spec, ob)
        if not ops:
            continue
        n_ops = len(ops)
        widest = max(w for w, _, _ in ops)
        if n_ops == 1:
            F(("HIGH", "OBJ_ONE_DOOR",
               f"objective room '{ob}' has a single opening "
               f"({ops[0][1]} {ops[0][0]:.1f} m): assault has exactly one "
               f"plan. Add a second opening or a breachable soft wall."))
        if widest < WIDE_DOOR:
            F(("MED", "OBJ_NARROW",
               f"objective room '{ob}': widest way in is {widest:.1f} m "
               f"(single-file). One >= {WIDE_DOOR:.1f} m opening lets the "
               f"squad enter as a unit and loot-carry out."))
        d = _bfs_dist(adj, entries)
        if ob in d and d[ob] == 0:
            F(("INFO", "OBJ_AT_DOOR",
               f"objective room '{ob}' has a direct exterior entry -- a "
               f"designed breach shortcut if intended; gate it in game code "
               f"or accept the speedrun line."))
        elif ob in d and d[ob] > 4:
            F(("INFO", "OBJ_DEEP",
               f"objective room '{ob}' is {d[ob]} rooms from the nearest "
               f"entry; long approach -- fine if the route fights well."))

    # --- vertical
    if spec.n_stories > 1 or spec.has_basement:
        links = _vertical_links(spec)
        base = -1 if spec.has_basement else 0
        for st in range(base, spec.n_stories - 1):
            n = links.get((st, st + 1), 0)
            if n == 0:
                continue   # navigability check owns unreachable stories
            if n == 1:
                F(("MED", "VERT_DEAD_END",
                   f"stories {st}->{st + 1} connect by exactly 1 vertical "
                   f"link: the upper floor plays as a single siege. A second "
                   f"link (ladder, second stair, roof hatch) turns it into a "
                   f"level."))

    # --- cover + cramp
    for r in spec.rooms:
        cr = getattr(r, "combat_range", None)
        if not cr:
            continue
        if _room_min_dim(r) < CRAMP_MIN_DIM:
            F(("MED", "CRAMPED",
               f"room '{r.id}' authors combat_range={cr} but is only "
               f"{_room_min_dim(r):.1f} m at its narrowest: four capsules + "
               f"enemies do not fit. Drop the combat intent or widen it."))
        area = _room_area(r)
        if area >= KILLBOX_AREA and _cover_in_room(spec, r) == 0:
            F(("MED", "KILLBOX",
               f"room '{r.id}' is {area:.0f} m^2 with combat intent and ZERO "
               f"waist-high volumes or cover markers: an open kill box. "
               f"Two or three 0.9-1.2 m volumes fix it."))

    # --- axis-swap lint: a partition whose doors all open within a single
    # room, but which would connect two distinct rooms with its axis flipped,
    # is almost certainly authored with X/Y swapped -- the built wall bisects
    # rooms and its doors are decorative. This exact bug shipped in five
    # presets before this check existed.
    class _Flip:
        def __init__(self, p):
            self.__dict__.update(p.__dict__)
            self.axis = "X" if p.axis == "Y" else "Y"

    def _door_pairs(part):
        pairs, eps = [], 0.8
        run = abs(part.end - part.start)
        for op in part.openings:
            if op.kind not in ("door", "garage", "breach"):
                continue
            u = part.start + (op.pos + 0.5) * run
            if part.axis == "Y":
                a = tactical._room_at(spec, part.story, part.pos - eps, u)
                b = tactical._room_at(spec, part.story, part.pos + eps, u)
            else:
                a = tactical._room_at(spec, part.story, u, part.pos - eps)
                b = tactical._room_at(spec, part.story, u, part.pos + eps)
            pairs.append((a, b))
        return pairs

    for part in spec.partitions:
        asis = _door_pairs(part)
        if not asis:
            continue
        if all(a == b or a is None or b is None for a, b in asis) and                 any(a != b and a and b for a, b in _door_pairs(_Flip(part))):
            F(("HIGH", "AXIS_SWAP",
               f"partition axis={part.axis} pos={part.pos} story={part.story}: "
               f"every door on it opens within a single room as authored, but "
               f"connects two rooms with the axis flipped -- X/Y are almost "
               f"certainly swapped (the built wall bisects rooms)."))

    # --- sightline intent (reuse the existing checker's mismatches)
    try:
        sl = sightlines.check(spec)
        for w in (sl.get("warnings") or []):
            if "intent mismatch" in w:
                F(("INFO", "SIGHT_INTENT", w.strip()))
    except Exception:
        pass

    # --- genre rule packs (--rules): PayDay 2 / Ready or Not / L4D2
    ctx = {"adj": adj, "entries": entries, "objectives": objectives,
           "rooms": rooms}
    for pk in packs_for(spec, rules):
        RULE_PACKS[pk](spec, ctx, F)

    # --- author-accepted findings: a spec can declare intended designs
    # ("audit_accept": [{"code","room","why"}]) -- a one-breach vault may be
    # the climax. Accepted findings downgrade to INFO with the reason, so
    # they stay visible without nagging.
    accepts = {(a.get("code"), a.get("room")): a.get("why", "accepted")
               for a in getattr(spec, "audit_accept", None)
               or (spec.raw.get("audit_accept", []) if hasattr(spec, "raw") else [])}
    if accepts:
        out = []
        for sev, code, msg in findings:
            key = next((k for k in accepts
                        if k[0] == code and
                        (k[1] is None or f"'{k[1]}'" in msg)), None)
            if key and sev != "INFO":
                out.append(("INFO", code,
                            msg + f" [ACCEPTED by author: {accepts[key]}]"))
            else:
                out.append((sev, code, msg))
        findings[:] = out


    return {"name": name, "rooms": n_nodes, "edges": n_edges, "loops": loops,
            "dead_ends": sorted(dead), "chokepoints": sorted(chokes),
            "entry_faces": sorted(faces), "objective_rooms": sorted(objectives),
            "findings": findings}


def format_report(res):
    lines = [f"== {res['name']} =="]
    lines.append(
        f"  rooms {res['rooms']}  edges {res['edges']}  loops {res['loops']}"
        f"  entry faces {'/'.join(res['entry_faces']) or '-'}"
        f"  objectives {', '.join(res['objective_rooms']) or '-'}")
    if res["chokepoints"]:
        lines.append(f"  chokepoints: {', '.join(res['chokepoints'])}")
    counts = {"HIGH": 0, "MED": 0, "INFO": 0}
    for sev, code, msg in res["findings"]:
        counts[sev] += 1
    lines.append(f"  flags: {counts['HIGH']} HIGH / {counts['MED']} MED / "
                 f"{counts['INFO']} INFO")
    for sev, code, msg in sorted(res["findings"],
                                 key=lambda f: ("HIGH MED INFO".split()
                                                .index(f[0]), f[1])):
        lines.append(f"    [{sev}] {code}: {msg}")
    return "\n".join(lines)


GAMEPLAY_PRESETS = None  # filled in main from the registry, minus facades


def main(argv=None):
    ap = argparse.ArgumentParser(description="FPS combat structural audit")
    ap.add_argument("spec", nargs="?", help="path to a spec json")
    ap.add_argument("--preset", help="audit a freshly generated preset")
    ap.add_argument("--all-presets", action="store_true")
    ap.add_argument("--all", action="store_true", help="every spec in specs/")
    ap.add_argument("--json", action="store_true", help="machine output")
    ap.add_argument("--rules", default=None,
                    help="genre rule packs: auto | all | heist,cqb,flow "
                         "(PayDay 2 / Ready or Not / L4D2 grammars)")
    ap.add_argument("--raw", action="store_true",
                    help="audit presets WITHOUT level_design enrichment "
                         "(default audits the shipping path, enrich=True)")
    a = ap.parse_args(argv)

    jobs = []
    if a.spec:
        jobs.append(("spec", a.spec))
    if a.preset:
        jobs.append(("preset", a.preset))
    if a.all_presets:
        for p in sorted(presets_mod.REGISTRY):
            d = presets_mod.make(p, enrich=False)
            if d.get("facade"):
                continue
            jobs.append(("preset", p))
    if a.all:
        for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
            jobs.append(("spec", p))
    if not jobs:
        ap.error("give a spec path, --preset, --all-presets, or --all")
    enrich = not a.raw

    results = []
    for kind, ref in jobs:
        if kind == "preset":
            spec = spec_from_dict(presets_mod.make(ref, enrich=enrich))
            res = audit(spec, name=f"preset:{ref}", rules=a.rules)
        else:
            spec = load_spec(ref)
            d = json.load(open(ref))
            if d.get("facade"):
                continue
            res = audit(spec, name=os.path.basename(ref), rules=a.rules)
        results.append(res)

    if a.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(format_report(r))
            print()
        high = sum(1 for r in results for f in r["findings"] if f[0] == "HIGH")
        med = sum(1 for r in results for f in r["findings"] if f[0] == "MED")
        print(f"== {len(results)} audited: {high} HIGH, {med} MED ==")
        print("(structural estimate, not a measure of fun -- walk it)")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:      # piping into head/grep is normal CLI use
        sys.exit(0)
