#!/usr/bin/env python3
r"""layout_lint.py -- real-architecture guard rails (LAYOUT_RULES.md, executable half).

Checks a spec against egress, secure-chain, readability, and combat-space
rules derived from IBC egress logic, bank/casino planning practice, and FPS
level-design canon. Offline, spec-level, complements validate.py.

    python layout_lint.py specs\bank_tower_a01.json
    python layout_lint.py --all          # every spec with mode pvp_heist

Findings are LINT-WARN (advisory) or LINT-FAIL (hard rule). Exit 1 on FAIL.
"""
import glob
import json
import math
import os
import sys

from partition_bounds import partition_overshoot

HERE = os.path.dirname(os.path.abspath(__file__))

# rule constants (meters) -- see LAYOUT_RULES.md for sources
COMMON_PATH_MAX = 7.0        # room depth beyond which 2 exits are expected (A1)
TRAVEL_MAX = 60.0            # room-graph travel to an exterior exit (A3)
DEAD_END_MAX = 6.0           # single-opening connector depth (A4)
HALL_MIN_SH = 4.2            # civic/venue public halls read tall (C1)
COVER_REPEAT_MAX = 3         # identical cover volumes in a row (D2)

VENUE_FAMILIES = ("stadium", "arena", "casino", "market_hall", "airport_terminal",
                  "bank_tower", "landmark_hall", "museum", "courthouse",
                  "rail_station", "supermarket", "large_warehouse")

PROGRAM = {  # C2 signature program per family prefix -> required room-id fragments
    "bank_tower": ["teller", "vault|safe"],
    "bank_branch": ["teller|counter", "vault"],
    "casino": ["cage|count", "gaming|floor"],
    "market_hall": ["stall|market", "cold|cage|deposit"],
    "airport_terminal": ["checkin|concourse", "bond|customs|ops"],
    "rail_station": ["fare|hall", "money|dispatch"],
    "train_yard": ["shed|dispatch", "store|signal"],
}


def _load(path):
    return json.load(open(path))


def _rooms_by_story(spec):
    out = {}
    for r in spec.get("rooms", []):
        out.setdefault(r.get("story", 0), []).append(r)
    return out


def _room_at(rooms, x, y):
    best = None
    best_area = 1e18
    for r in rooms:
        x0, y0, x1, y1 = r["bounds"]
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            area = (x1 - x0) * (y1 - y0)
            if area < best_area:      # innermost wins (room-in-room cages)
                best, best_area = r, area
    return best


def _opening_xy(spec, wall_or_part, opening, is_ext):
    hx, hy = spec["footprint_x"] / 2, spec["footprint_y"] / 2
    pos = opening.get("pos", 0.0)
    if is_ext:
        w = wall_or_part["wall"]
        if w in ("N", "S"):
            return pos * spec["footprint_x"], (hy if w == "N" else -hy)
        return (hx if w == "E" else -hx), pos * spec["footprint_y"]
    ax = wall_or_part["axis"]
    p = wall_or_part["pos"]
    s, e = wall_or_part.get("start"), wall_or_part.get("end")
    lo = -hx if ax == "X" else -hy
    hi = hx if ax == "X" else hy
    s = lo if s is None else s
    e = hi if e is None else e
    along = (s + e) / 2 + pos * (e - s)
    if ax == "X":     # partition runs along X at y=p
        return along, p
    return p, along   # runs along Y at x=p


def graph(spec):
    """room-id graph with EXT node; edges carry (kind, distance-capable)."""
    by_story = _rooms_by_story(spec)
    edges = {}          # id -> set of (neighbor, kind)
    def add(a, b, kind):
        edges.setdefault(a, set()).add((b, kind))
        edges.setdefault(b, set()).add((a, kind))

    for part in spec.get("partitions", []):
        story = part.get("story", 0)
        rooms = by_story.get(story, [])
        for op in part.get("openings", []):
            kind = op.get("kind", "door")
            if kind == "window" and not op.get("vaultable", True):
                continue
            x, y = _opening_xy(spec, part, op, False)
            eps = 0.4
            pairs = []
            if part["axis"] == "X":
                pairs.append((_room_at(rooms, x, y - eps), _room_at(rooms, x, y + eps)))
                pairs.append((_room_at(rooms, y, x - eps), _room_at(rooms, y, x + eps)))
            else:
                pairs.append((_room_at(rooms, x - eps, y), _room_at(rooms, x + eps, y)))
                pairs.append((_room_at(rooms, y - eps, x), _room_at(rooms, y + eps, x)))
            for a, b in pairs:                 # both axis conventions; lint is
                if a and b and a["id"] != b["id"]:   # advisory, engine gates are truth
                    add(a["id"], b["id"], kind if kind != "window" else "vault")
                    if op.get("reinforceable"):
                        add(a["id"], b["id"], "reinforced_door")

    ext_faces = {}
    for wall in spec.get("ext_walls", []):
        if wall.get("story", 0) != 0:
            continue
        rooms = by_story.get(0, [])
        for op in wall.get("openings", []):
            if op.get("kind") not in ("door", "garage", "breach"):
                continue
            x, y = _opening_xy(spec, wall, op, True)
            w = wall["wall"]
            dx = {"E": -0.4, "W": 0.4}.get(w, 0.0)
            dy = {"N": -0.4, "S": 0.4}.get(w, 0.0)
            r = _room_at(rooms, x + dx, y + dy)
            if r:
                add(r["id"], "EXT", op.get("kind", "door"))
                if op.get("kind") in ("door", "garage"):
                    ext_faces.setdefault(w, 0)
                    ext_faces[w] += 1

    for st in list(spec.get("stairs", [])) + list(spec.get("ladders", [])):
        rooms_lo = by_story.get(st["from_story"], [])
        rooms_hi = by_story.get(st["to_story"], [])
        a = _room_at(rooms_lo, st["x"], st["y"])
        b = _room_at(rooms_hi, st["x"], st["y"])
        if a and b:
            add(a["id"], b["id"], "stair")
        elif a and st.get("upper_surface") == "roof":
            add(a["id"], "ROOF", "ladder")
    return edges, ext_faces


def _dims(r):
    x0, y0, x1, y1 = r["bounds"]
    return x1 - x0, y1 - y0


def _center(r):
    x0, y0, x1, y1 = r["bounds"]
    return (x0 + x1) / 2, (y0 + y1) / 2


def bounds_findings(spec):
    """L13 (advisory WARN): an interior partition should stay within the
    footprint on its RUNNING axis. A Y-wall authored to the X half-width (or
    vice-versa) overshoots the envelope. This is a WARN, not a FAIL: the geometry
    builder now CLAMPS such walls at build time (deli_counter._partitions), so
    the shipped geometry is already correct -- the warning just surfaces the
    authoring debt so presets get fixed at the source over time (see 0.83.2).
    Runs on the spec (pre-clamp), geometry-only, for every story."""
    fails = []
    fx, fy = spec.get("footprint_x"), spec.get("footprint_y")
    if not fx or not fy:
        return fails
    for part in spec.get("partitions", []):
        ax = part.get("axis")
        s, e = part.get("start"), part.get("end")
        if s is None or e is None:
            continue
        over = partition_overshoot(s, e, ax, fx, fy)
        if over > 0.05:
            b = (fy / 2) if str(ax).upper() == "Y" else (fx / 2)
            fails.append(
                f"L13 partition out of bounds: story {part.get('story', 0)} "
                f"{ax}-wall at pos={part.get('pos')} spans [{s:.1f},{e:.1f}] past "
                f"the {ax}-half {b:.1f} (overshoots {over:.1f} m -- interior wall "
                f"pokes through the exterior shell)")
    return fails


def ladder_findings(spec):
    """L14/L15: every ladder must be TRAVERSABLE, not just present.
      L14 (FAIL): the through-hole a climbing body needs pokes past the slab
                  footprint -- the climb dead-ends into the exterior shell
                  (the ladder faces the wrong way for where it stands).
      L15 (WARN): a partition on the story the climb surfaces into crosses
                  the through-hole -- the climber tops out inside a wall.
    Hole geometry comes from ladder_geom -- the SAME module the builder cuts
    with (the partition_bounds pattern), so this linter can never disagree
    with the shipped geometry."""
    import ladder_geom
    from partition_bounds import clamp_partition_span
    fails, warns = [], []
    fx, fy = spec.get("footprint_x"), spec.get("footprint_y")
    if not fx or not fy:
        return fails, warns
    for i, ld in enumerate(spec.get("ladders", [])):
        if not ld.get("cut_slabs", True):
            continue
        # Through-hole semantics only apply where the climb passes a slab:
        # interior/shaft ladders. An exterior_wall or platform ladder climbs
        # the outside face and tops out at an edge, not through a cut.
        if (ld.get("placement_mode") or "interior") not in ("interior", "shaft"):
            continue
        x, y = ld.get("x", 0.0), ld.get("y", 0.0)
        w = ld.get("width", 0.5)
        facing = ld.get("facing", "S")
        over = ladder_geom.hole_overshoot(x, y, w, facing, fx, fy)
        if over > 0.05:
            fails.append(
                f"L14 ladder through-hole out of bounds: ladder #{i} at "
                f"({x:g},{y:g}) facing {facing} needs a climb hole that "
                f"overshoots the footprint by {over:.2f} m -- the climb "
                f"dead-ends into the exterior shell (flip the facing or move "
                f"the ladder off the wall)")
        for s in range(int(ld.get("from_story", 0)),
                       int(ld.get("to_story", 1))):
            top = s + 1
            for p in spec.get("partitions", []):
                if p.get("story") != top:
                    continue
                ps, pe = p.get("start"), p.get("end")
                if ps is None or pe is None:
                    continue
                lo, hi = clamp_partition_span(ps, pe, p.get("axis", "X"),
                                              fx, fy)
                if ladder_geom.partition_blocks_hole(
                        p.get("axis", "X"), p.get("pos", 0.0), lo, hi,
                        spec.get("wall_thick", 0.35), x, y, w, facing):
                    warns.append(
                        f"L15 ladder climb surfaces into a wall: ladder #{i} "
                        f"at ({x:g},{y:g}) tops out on story {top} where a "
                        f"{p.get('axis')}-partition at pos={p.get('pos')} "
                        f"crosses its through-hole")
    return fails, warns


def structural_findings(spec):
    """Coherence rules that apply to EVERY building (any mode):
      L10 dead opening  -- an interior door/garage/breach must connect two
                           DISTINCT rooms; same-room or into-void = FAIL.
      L11 orphan wall   -- an interior partition whose whole span borders no
                           two rooms (it bisects a room or floats in void) = WARN.
    Uses the same _room_at / _opening_xy the graph gate uses, so a coherence
    failure here can't disagree with the navigation graph."""
    fails, warns = [], []
    by = _rooms_by_story(spec)
    hx, hy = spec["footprint_x"] / 2, spec["footprint_y"] / 2
    EPS = 0.35
    for part in spec.get("partitions", []):
        story = part.get("story", 0)
        rooms = by.get(story, [])
        if not rooms:
            continue   # no room grammar on this story -> can't judge boundaries
                       # (legacy specs predating tactical rooms are not linted here)
        ax = part["axis"]
        p = part["pos"]
        s, e = part.get("start"), part.get("end")
        lo = (-hx if ax == "X" else -hy) if s is None else s
        hi = (hx if ax == "X" else hy) if e is None else e
        # sample the span: how much of it actually borders two distinct rooms
        N = 40
        step = (hi - lo) / N if hi > lo else 0.0
        real = orphan = 0.0
        for i in range(N):
            a = lo + (i + 0.5) * step
            if ax == "X":
                r1 = _room_at(rooms, a, p + EPS)
                r2 = _room_at(rooms, a, p - EPS)
            else:
                r1 = _room_at(rooms, p + EPS, a)
                r2 = _room_at(rooms, p - EPS, a)
            if r1 and r2 and r1["id"] != r2["id"]:
                real += step
            else:
                orphan += step
        if real < 0.5 and orphan > 0.5:
            fails.append(f"L11 orphan wall: story {story} {ax}-wall at pos={p} "
                         f"({orphan:.0f} m) borders no two rooms "
                         f"(bisects a room or floats in unassigned space)")
        # L10: every interior opening must connect two DISTINCT rooms; opening
        # into unassigned space (no room on a side) is a navigation dead-end.
        for op in part.get("openings", []):
            if op.get("kind") not in ("door", "garage", "breach"):
                continue
            x, y = _opening_xy(spec, part, op, False)
            if ax == "X":
                r1 = _room_at(rooms, x, y + EPS)
                r2 = _room_at(rooms, x, y - EPS)
            else:
                r1 = _room_at(rooms, x + EPS, y)
                r2 = _room_at(rooms, x - EPS, y)
            i1 = r1["id"] if r1 else None
            i2 = r2["id"] if r2 else None
            who = op.get("tag") or op.get("kind", "opening")
            if i1 and i2 and i1 == i2:
                fails.append(f"L10 dead opening: story {story} '{who}' connects "
                             f"'{i1}' to itself (separates no rooms)")
            elif i1 is None and i2 is None:
                fails.append(f"L10 dead opening: story {story} '{who}' opens into "
                             f"unassigned space on both sides")
            elif i1 is None or i2 is None:
                fails.append(f"L10 dead opening: story {story} '{who}' opens from "
                             f"'{i1 or i2}' into unassigned space (no room on the "
                             f"far side)")
    return fails, warns


def reachability_findings(spec):
    """L12 -- every room must have a path from an exterior entrance. Catches
    SEALED spaces (a stair landing in a closed box, a room with no door): a
    *missing* connection, which the coherence rules (dead openings) cannot see.
    Runs for every mode. Uses the same graph as the nav check, but treats a
    stair/ladder as serving every floor it passes through (real stairwell
    behaviour), and counts ramps + floor-hole/hatch drops as connections."""
    rooms = spec.get("rooms", [])
    if not rooms:
        return []
    edges, _ = graph(spec)
    by = _rooms_by_story(spec)

    def link(a, b):
        edges.setdefault(a, set()).add((b, "vert"))
        edges.setdefault(b, set()).add((a, "vert"))

    # outdoor / site rooms (bounds extend beyond the building footprint -- a
    # forecourt, yard, dock, parking) are contiguous with the exterior, so they
    # are reachable from outside by definition.
    hx, hy = spec["footprint_x"] / 2, spec["footprint_y"] / 2
    tol = 0.5
    for r in rooms:
        x0, y0, x1, y1 = r["bounds"]
        if x0 < -hx - tol or x1 > hx + tol or y0 < -hy - tol or y1 > hy + tol:
            link(r["id"], "EXT")

    # stairs/ladders connect every floor they pass through, not just endpoints
    for st in list(spec.get("stairs", [])) + list(spec.get("ladders", [])):
        a, b = st.get("from_story"), st.get("to_story")
        if a is None or b is None:
            continue
        chain = []
        for fl in range(min(a, b), max(a, b) + 1):
            r = _room_at(by.get(fl, []), st.get("x", 0), st.get("y", 0))
            if r:
                chain.append(r["id"])
        for i in range(len(chain) - 1):
            link(chain[i], chain[i + 1])
    # ramps
    for rp in spec.get("ramps", []):
        a = _room_at(by.get(rp.get("from_story", 0), []), rp.get("x", 0), rp.get("y", 0))
        b = _room_at(by.get(rp.get("to_story", 0), []), rp.get("x", 0), rp.get("y", 0))
        if a and b:
            link(a["id"], b["id"])
    # floor holes / hatches (vertical drops) connect the two stacked rooms
    for vl in spec.get("vertical_links", []):
        if vl.get("kind") in ("floor_hole", "hatch") and vl.get("x") is not None:
            s = vl.get("story", 0)
            a = _room_at(by.get(s, []), vl["x"], vl["y"])
            b = _room_at(by.get(s - 1, []), vl["x"], vl["y"])
            if a and b:
                link(a["id"], b["id"])

    seen = {"EXT"}
    stk = ["EXT"]
    while stk:
        u = stk.pop()
        for v, k in edges.get(u, ()):
            if v not in seen:
                seen.add(v)
                stk.append(v)
    fails = []
    for r in rooms:
        if r["id"] not in seen:
            fails.append(f"L12 unreachable room: '{r['id']}' (story {r.get('story')}) "
                         f"has no path from an exterior entrance -- sealed space or "
                         f"missing door/stair connection")
    return fails


def gate(spec):
    """evidence.py entry point: (errors, warnings, summary). Runs the full lint
    (structural coherence for all modes + pvp_heist guard rails)."""
    name, fails, warns = lint_spec(spec, spec.get("name", "?"))
    return fails, warns, {"fails": len(fails), "warnings": len(warns)}


def lint_spec(spec, name):
    fails, warns = [], []
    sf, sw = structural_findings(spec)      # coherence rules run for ALL modes
    fails += sf
    warns += sw
    warns += bounds_findings(spec)          # L13 partition-in-footprint (advisory)
    lf14, lw15 = ladder_findings(spec)      # L14 hole-in-footprint / L15 blocked
    fails += lf14
    warns += lw15
    fails += reachability_findings(spec)    # L12 sealed/unreachable rooms (all modes)
    if spec.get("mode") != "pvp_heist":
        return name, fails, warns
    edges, ext_faces = graph(spec)
    rooms = spec.get("rooms", [])
    by_id = {r["id"]: r for r in rooms}

    # L1 (A1): big rooms need >= 2 openings
    for r in rooms:
        w, d = _dims(r)
        deg = len(edges.get(r["id"], ()))
        if max(w, d) > COMMON_PATH_MAX and deg < 2:
            warns.append(f"L1 room '{r['id']}' is {max(w,d):.0f}m deep with "
                         f"{deg} opening(s); expect 2 ways out (common-path rule)")

    # L2 (A2): >=2 exterior exits on >=2 faces
    n_ext = sum(ext_faces.values())
    if n_ext < 2 or len(ext_faces) < 2:
        fails.append(f"L2 exterior exits: {n_ext} on faces {sorted(ext_faces)}; "
                     f"need >=2 exits on >=2 faces")

    # L3 (A3): travel distance to EXT (BFS with centroid distances)
    import heapq
    dist = {"EXT": 0.0}
    pq = [(0.0, "EXT")]
    while pq:
        d0, u = heapq.heappop(pq)
        if d0 > dist.get(u, 1e18):
            continue
        for v, kind in edges.get(u, ()):
            if v == "EXT":
                continue
            step = 3.0
            if u != "EXT" and u in by_id and v in by_id:
                ax, ay = _center(by_id[u]); bx, by_ = _center(by_id[v])
                step = math.hypot(ax - bx, ay - by_)
            elif v in by_id:
                w, dd = _dims(by_id[v]); step = (w + dd) / 4
            nd = d0 + step
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    for r in rooms:
        d = dist.get(r["id"])
        if d is None:
            fails.append(f"L3 room '{r['id']}' has no path to an exterior exit")
        elif d > TRAVEL_MAX:
            warns.append(f"L3 room '{r['id']}' travel ~{d:.0f}m to exit "
                         f"(> {TRAVEL_MAX:.0f}m)")

    # L4 (A4): deep single-opening connectors
    for r in rooms:
        if r.get("role") in ("connector", "corridor") :
            w, d = _dims(r)
            if len(edges.get(r["id"], ())) <= 1 and max(w, d) > DEAD_END_MAX:
                warns.append(f"L4 dead-end connector '{r['id']}' ({max(w,d):.0f}m)")

    # L5 (B1): a PLAIN door from public straight into the objective breaks the
    # secure chain; a reinforceable ("staff only" steel) door or a breach is fine.
    for r in rooms:
        if not (r.get("objective") or r.get("role") == "objective_room"):
            continue
        nbrs = edges.get(r["id"], ())
        for v, kind in nbrs:
            if (v in by_id and by_id[v].get("role") == "public_entry"
                    and kind == "door" and (v, "reinforced_door") not in nbrs):
                fails.append(f"L5 objective '{r['id']}' has a PLAIN door straight "
                             f"from public room '{v}' (make it reinforceable, or "
                             f"route through the staff band)")

    # L6 (B2): objective must not touch the main-entry face wall
    entry_faces = set()
    for wall in spec.get("ext_walls", []):
        if wall.get("story", 0) == 0:
            for op in wall.get("openings", []):
                if op.get("kind") == "door" and (op.get("width", 0) >= 2.0
                                                 or str(op.get("tag", "")).startswith("entry")):
                    entry_faces.add(wall["wall"])
    hx, hy = spec["footprint_x"] / 2, spec["footprint_y"] / 2
    for r in rooms:
        if not (r.get("objective") or r.get("role") == "objective_room"):
            continue
        x0, y0, x1, y1 = r["bounds"]
        touch = {"W": abs(x0 + hx) < 0.3, "E": abs(x1 - hx) < 0.3,
                 "S": abs(y0 + hy) < 0.3, "N": abs(y1 - hy) < 0.3}
        for f in entry_faces:
            if touch.get(f):
                warns.append(f"L6 objective '{r['id']}' touches main-entry face {f}")

    # L7 (C1): venue public halls read tall
    fam = name.rsplit("_a", 1)[0]
    if fam in VENUE_FAMILIES:
        sh = spec.get("story_height", 3.0)
        if any(r.get("role") == "public_entry" for r in rooms) and sh < HALL_MIN_SH:
            warns.append(f"L7 venue public hall at sh {sh}m (< {HALL_MIN_SH}m reads flat)")

    # L8 (C2): family signature program present
    req = PROGRAM.get(fam)
    if req:
        ids = " ".join(r["id"] for r in rooms).lower()
        for group in req:
            if not any(tok in ids for tok in group.split("|")):
                warns.append(f"L8 '{fam}' spec has no room matching '{group}' "
                             f"(signature program)")

    # L9 (D2): repeated identical cover volumes ("cover boxes" anti-pattern)
    seen = {}
    for v in spec.get("volumes", []):
        key = (round(v.get("size_x", 0), 2), round(v.get("size_y", 0), 2),
               round(v.get("size_z", 0), 2))
        seen[key] = seen.get(key, 0) + 1
    for key, n in seen.items():
        if n > COVER_REPEAT_MAX:
            warns.append(f"L9 {n}x identical cover volumes {key} -- vary "
                         f"dims/height (cover-box anti-pattern)")

    return name, fails, warns


def lint(path):
    spec = _load(path)
    return lint_spec(spec, spec.get("name", os.path.basename(path)))


def main():
    args = sys.argv[1:]
    paths = (sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
             if "--all" in args else [a for a in args if a.endswith(".json")])
    # LF pipeline artifacts (specs/lf_*.json) are transient build inputs written
    # into specs/ by Level Factory, not DC's authored library -- don't gate DC
    # commits on them. Lint them explicitly by path if ever needed.
    if "--all" in args:
        paths = [p for p in paths
                 if not os.path.basename(p).startswith("lf_")]
    total_f = total_w = checked = 0
    for p in paths:
        try:
            name, fails, warns = lint(p)
        except Exception as e:
            print(f"== {os.path.basename(p)} ==\n  LINT-ERROR: {e}")
            total_f += 1
            continue
        if not fails and not warns:
            continue
        checked += 1
        print(f"== {name} ==")
        for f in fails:
            print(f"  LINT-FAIL: {f}")
        for w in warns:
            print(f"  LINT-WARN: {w}")
        total_f += len(fails)
        total_w += len(warns)
    print(f"\n[layout-lint] {len(paths)} specs: {total_f} FAIL, {total_w} WARN "
          f"({checked} specs with findings)")
    sys.exit(1 if total_f else 0)


if __name__ == "__main__":
    main()
