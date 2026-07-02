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
KIND_DEFAULT_W = {"door": 1.2, "window": 1.6, "garage": 3.5, "breach": 1.5}


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
            rid = tactical._room_at(spec, 0, m.x, m.y) \
                or tactical._room_at(spec, getattr(m, "story", 0) or 0, m.x, m.y)
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
def audit(spec, name=None):
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
            res = audit(spec, name=f"preset:{ref}")
        else:
            spec = load_spec(ref)
            d = json.load(open(ref))
            if d.get("facade"):
                continue
            res = audit(spec, name=os.path.basename(ref))
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
