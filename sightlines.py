"""
sightlines.py  --  tactical sightline / cover / exposure intel (offline, bpy-free)

WHY: tactical.py validates reachability and room access from the graph, but it
notes up top that real *sightline* analysis needs geometry. This is that pass.
It reads the SAME wall/partition/opening/volume geometry the floorplan draws,
casts rays in 2D at eye height, and reports the handful of metrics that catch
the gross gameplay problems in a greybox BEFORE you build and walk it:

  - death lane      : the longest unobstructed sightline on a floor (the angle
                      that dominates every fight near it).
  - exposed run     : the longest stretch of the spawn->objective approach with
                      no cover marker within reach (where you get caught out).
  - weak cover      : cover markers with clear line of sight from the attack
                      direction (cover that isn't actually cover).
  - intent mismatch : a room's authored combat_range vs the sightlines its
                      geometry actually produces (a "close" room that plays long).
  - objective entries: independent ways into the objective room (1 = a funnel).

This is INTEL, never a gate: it never fails a build. It prints a report and can
annotate the floorplan SVGs so you read the tactical shape and nudge the spec.
It is a GUIDE to authoring better buildings, not a pass/fail.

Greybox assumptions (deliberately conservative): every opening is see-through
(worst-case LOS through doors/windows); a volume blocks standing sight only if
it is tall enough to cross eye height; cover markers are the authored intent for
where cover will exist after the art pass.
"""

import math

import floorplan as fp

# ---- tunables (meters) ----------------------------------------------------
EYE = 1.6            # standing eye height (volume must cross this to block)
SIGHT_BLOCK_H = 1.6  # a volume taller than this blocks standing sight
COVER_R = 2.5        # a cover marker covers points within this radius
CLOSE_M = 8.0        # <= close-quarters; > LONG_M = long-range
LONG_M = 20.0
GRID = 1.5           # reachable-sample spacing
MAX_PTS = 240        # per-story sample cap (keeps the O(n^2) pass quick)
ROUTE_STEP = 0.5     # exposed-run march step


# ---- geometry -------------------------------------------------------------
def _seg_int(p, q, a, b):
    """True if open segments p-q and a-b properly cross (shared endpoints and
    collinear grazes do NOT count as blocking)."""
    def o(u, v, w):
        return (v[0] - u[0]) * (w[1] - u[1]) - (v[1] - u[1]) * (w[0] - u[0])
    d1, d2 = o(a, b, p), o(a, b, q)
    d3, d4 = o(p, q, a), o(p, q, b)
    eps = 1e-9
    if ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
       ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps)):
        return True
    return False


def _occluders(spec, story):
    """Sight-blocking segments on a story: exterior walls + partitions (each
    minus its openings) + tall volumes' footprints."""
    segs = []
    hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
    auto = getattr(spec, "auto_exterior", True)
    sides = {"N": ((-hx, hy), (hx, hy), "x"), "S": ((-hx, -hy), (hx, -hy), "x"),
             "E": ((hx, -hy), (hx, hy), "y"), "W": ((-hx, -hy), (-hx, hy), "y")}
    by_side = {}
    for w in getattr(spec, "ext_walls", []) or []:
        if w.story == story:
            by_side.setdefault(w.wall, []).append(w)
    for side, (p0, p1, axis) in sides.items():
        wlist = by_side.get(side, [])
        if wlist:
            lo = p0[0] if axis == "x" else p0[1]
            hi = p1[0] if axis == "x" else p1[1]
            gaps = []
            for w in wlist:
                gaps += fp._opening_gaps(w.openings, lo, hi)
            segs += fp._wall_segments_with_gaps(p0, p1, gaps, axis)
        elif auto:
            segs.append((p0, p1))
    for p in getattr(spec, "partitions", []) or []:
        if p.story != story:
            continue
        if p.axis == "X":
            p0, p1, axis = (p.start, p.pos), (p.end, p.pos), "x"
        else:
            p0, p1, axis = (p.pos, p.start), (p.pos, p.end), "y"
        lo = p0[0] if axis == "x" else p0[1]
        hi = p1[0] if axis == "x" else p1[1]
        gaps = fp._opening_gaps(p.openings, lo, hi)
        segs += fp._wall_segments_with_gaps(p0, p1, gaps, axis)
    for r in _tall_vol_rects(spec, story):
        (x0, y0, x1, y1) = r
        c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for i in range(4):
            segs.append((c[i], c[(i + 1) % 4]))
    return segs


def _tall_vol_rects(spec, story):
    sh = fp._story_height(spec)
    eye = story * sh + EYE
    rects = []
    for v in getattr(spec, "volumes", []) or []:
        z = getattr(v, "z", 0.0)
        szz = getattr(v, "size_z", 0.0)
        if szz < SIGHT_BLOCK_H:
            continue
        if z - szz / 2 <= eye <= z + szz / 2:
            sx, sy = v.size_x / 2, v.size_y / 2
            rects.append((v.x - sx, v.y - sy, v.x + sx, v.y + sy))
    return rects


def _clear(p, q, occ):
    for a, b in occ:
        if _seg_int(p, q, a, b):
            return False
    return True


def _in_rect(x, y, r):
    return r[0] <= x <= r[2] and r[1] <= y <= r[3]


def _reachable(spec, story):
    """Grid of standing positions inside the story's rooms, minus tall-volume
    footprints. Returns list of (x, y, room_id)."""
    rooms = [r for r in (getattr(spec, "rooms", []) or []) if r.story == story]
    vol = _tall_vol_rects(spec, story)
    pts = []
    for r in rooms:
        x0, y0, x1, y1 = r.bounds
        x = x0 + GRID / 2
        while x < x1:
            y = y0 + GRID / 2
            while y < y1:
                if not any(_in_rect(x, y, vr) for vr in vol):
                    pts.append((x, y, r.id))
                y += GRID
            x += GRID
    if len(pts) > MAX_PTS:
        step = math.ceil(len(pts) / MAX_PTS)
        pts = pts[::step]
    return pts


def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def _markers(spec, story, *types):
    out = []
    for m in getattr(spec, "markers", []) or []:
        if fp._marker_story(spec, m) == story and m.type in types:
            out.append(m)
    return out


# ---- metrics --------------------------------------------------------------
def analyze_story(spec, story):
    occ = _occluders(spec, story)
    pts = _reachable(spec, story)
    res = {"story": story, "n_samples": len(pts)}

    # 1) death lane: longest clear sightline among sampled positions
    best = (0.0, None, None)
    for i in range(len(pts)):
        pi = (pts[i][0], pts[i][1])
        for j in range(i + 1, len(pts)):
            pj = (pts[j][0], pts[j][1])
            d = _dist(pi, pj)
            if d <= best[0]:
                continue
            if _clear(pi, pj, occ):
                best = (d, pi, pj)
    res["death_lane_m"] = round(best[0], 1)
    res["death_lane"] = (best[1], best[2])

    # 2) intent mismatch: per-room max in-room sightline vs authored combat_range
    res["rooms"] = []
    by_room = {}
    for (x, y, rid) in pts:
        by_room.setdefault(rid, []).append((x, y))
    for r in [r for r in (getattr(spec, "rooms", []) or []) if r.story == story]:
        rp = by_room.get(r.id, [])
        mx = 0.0
        for i in range(len(rp)):
            for j in range(i + 1, len(rp)):
                d = _dist(rp[i], rp[j])
                if d > mx and _clear(rp[i], rp[j], occ):
                    mx = d
        got = "close" if mx <= CLOSE_M else "long" if mx > LONG_M else "medium"
        authored = getattr(r, "combat_range", None)
        res["rooms"].append({"id": r.id, "max_sightline_m": round(mx, 1),
                             "computed": got, "authored": authored,
                             "mismatch": bool(authored and authored != got)})

    # 3) exposed run on each attacker_spawn -> objective approach
    covers = _markers(spec, story, "cover_high", "cover_low")
    cover_xy = [(c.x, c.y) for c in covers]
    spawns = _markers(spec, story, "attacker_spawn")
    objs = _markers(spec, story, "objective")
    worst = {"len_m": 0.0, "seg": None}
    for s in spawns:
        for ob in objs:
            run = _exposed_run((s.x, s.y), (ob.x, ob.y), cover_xy)
            if run["len_m"] > worst["len_m"]:
                worst = run
    res["exposed_run_m"] = round(worst["len_m"], 1)
    res["exposed_seg"] = worst["seg"]

    # 4) weak cover: cover markers with clear LOS from an attacker spawn
    weak = []
    for c in covers:
        seen = sum(1 for s in spawns
                   if _clear((s.x, s.y), (c.x, c.y), occ))
        if spawns and seen:
            weak.append({"id": c.id, "seen_from": seen, "of": len(spawns)})
    res["weak_cover"] = weak
    res["n_cover"] = len(covers)

    # 5) objective entries (funnel check): openings on the objective room edges
    res["objective_entries"] = _objective_entries(spec, story)
    return res


def _exposed_run(a, b, cover_xy):
    d = _dist(a, b)
    if d < 1e-6:
        return {"len_m": 0.0, "seg": None}
    ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
    n = int(d / ROUTE_STEP) + 1
    run = 0.0
    best = 0.0
    seg = cur_start = None
    for k in range(n + 1):
        x, y = a[0] + ux * ROUTE_STEP * k, a[1] + uy * ROUTE_STEP * k
        covered = any(math.hypot(x - cx, y - cy) <= COVER_R for cx, cy in cover_xy)
        if not covered:
            if cur_start is None:
                cur_start = (x, y)
            run += ROUTE_STEP
            if run > best:
                best, seg = run, (cur_start, (x, y))
        else:
            run = 0.0
            cur_start = None
    return {"len_m": best, "seg": seg}


def _objective_entries(spec, story):
    """Count openings bordering each objective room on this story (independent
    ways in). 1 = a funnel into the holdable point."""
    out = []
    rooms = [r for r in (getattr(spec, "rooms", []) or []) if r.story == story]
    for r in rooms:
        if not getattr(r, "objective", False):
            continue
        x0, y0, x1, y1 = r.bounds
        eps = 0.4
        n = 0
        for p in getattr(spec, "partitions", []) or []:
            if p.story != story:
                continue
            for op in p.openings:
                span = (p.end - p.start)
                along = p.start + (op.pos + 0.5) * span
                if p.axis == "Y":      # wall at x=pos, opening along Y
                    if abs(p.pos - x0) < eps or abs(p.pos - x1) < eps:
                        if y0 - eps <= along <= y1 + eps:
                            n += 1
                else:                  # wall at y=pos, opening along X
                    if abs(p.pos - y0) < eps or abs(p.pos - y1) < eps:
                        if x0 - eps <= along <= x1 + eps:
                            n += 1
        # exterior doors on the room's footprint edge
        hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
        for w in getattr(spec, "ext_walls", []) or []:
            if w.story != story:
                continue
            for op in w.openings:
                if op.kind not in ("door", "garage", "breach"):
                    continue
                if w.wall in ("N", "S"):
                    edge_y = hy if w.wall == "N" else -hy
                    cx = op.pos * spec.footprint_x
                    if abs(edge_y - y1) < eps or abs(edge_y - y0) < eps:
                        if x0 - eps <= cx <= x1 + eps:
                            n += 1
                else:
                    edge_x = hx if w.wall == "E" else -hx
                    cy = op.pos * spec.footprint_y
                    if abs(edge_x - x1) < eps or abs(edge_x - x0) < eps:
                        if y0 - eps <= cy <= y1 + eps:
                            n += 1
        out.append({"id": r.id, "entries": n})
    return out


def analyze(spec):
    return [analyze_story(spec, st) for st in fp.stories_in(spec)]


# ---- report ---------------------------------------------------------------
def report(spec):
    lines = [f"sightlines: {spec.name}"]
    for s in analyze(spec):
        st = s["story"]
        label = ("basement" if st < 0 else "ground" if st == 0 else f"floor {st}")
        lines.append(f"  [{label}]  ({s['n_samples']} samples)")
        bucket = ("long" if s["death_lane_m"] > LONG_M else
                  "close" if s["death_lane_m"] <= CLOSE_M else "medium")
        lines.append(f"    death lane (longest clear sightline): "
                     f"{s['death_lane_m']} m  [{bucket}]")
        if s["exposed_run_m"]:
            lines.append(f"    longest exposed approach (no cover within "
                         f"{COVER_R} m): {s['exposed_run_m']} m")
        for oe in s["objective_entries"]:
            flag = "  <- FUNNEL (single entry)" if oe["entries"] <= 1 else ""
            lines.append(f"    objective room '{oe['id']}': "
                         f"{oe['entries']} entries{flag}")
        for w in s["weak_cover"]:
            lines.append(f"    weak cover '{w['id']}': in LOS of "
                         f"{w['seen_from']}/{w['of']} attacker spawns")
        for rm in s["rooms"]:
            if rm["mismatch"]:
                lines.append(f"    intent mismatch: room '{rm['id']}' authored "
                             f"'{rm['authored']}' but plays '{rm['computed']}' "
                             f"({rm['max_sightline_m']} m sightline)")
    return "\n".join(lines)


def check(spec):
    """INTEL entry for check.py: always ok=True; returns (ok, report_lines)."""
    return True, report(spec).splitlines()


# ---- SVG overlay (annotate the floorplan) ---------------------------------
def _overlay_svg(spec, story, s):
    tx = fp._Tx(spec)
    g = ['<g id="sightlines">']
    dl = s["death_lane"]
    if dl[0] and dl[1]:
        (p, q) = dl
        g.append(f'<line x1="{tx.x(p[0]):.1f}" y1="{tx.y(p[1]):.1f}" '
                 f'x2="{tx.x(q[0]):.1f}" y2="{tx.y(q[1]):.1f}" '
                 f'stroke="#e11" stroke-width="2" stroke-dasharray="6 4" '
                 f'opacity="0.8"/>')
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        g.append(f'<text x="{tx.x(mx):.1f}" y="{tx.y(my) - 4:.1f}" '
                 f'font-size="11" fill="#e11" text-anchor="middle">'
                 f'death lane {s["death_lane_m"]}m</text>')
    seg = s.get("exposed_seg")
    if seg:
        (p, q) = seg
        g.append(f'<line x1="{tx.x(p[0]):.1f}" y1="{tx.y(p[1]):.1f}" '
                 f'x2="{tx.x(q[0]):.1f}" y2="{tx.y(q[1]):.1f}" '
                 f'stroke="#f90" stroke-width="6" opacity="0.45"/>')
    for w in s["weak_cover"]:
        for m in _markers(spec, story, "cover_high", "cover_low"):
            if m.id == w["id"]:
                g.append(f'<circle cx="{tx.x(m.x):.1f}" cy="{tx.y(m.y):.1f}" '
                         f'r="7" fill="none" stroke="#e11" stroke-width="2"/>')
    g.append('</g>')
    return "\n".join(g)


def write_overlays(spec, outdir):
    import os
    os.makedirs(outdir, exist_ok=True)
    paths = []
    data = {s["story"]: s for s in analyze(spec)}
    for st in fp.stories_in(spec):
        base = fp.render_story(spec, st)
        s = data.get(st)
        if s:
            base = base.replace("</svg>", _overlay_svg(spec, st, s) + "\n</svg>")
        suffix = "B" if st < 0 else str(st)
        path = os.path.join(outdir, f"{spec.name}.sightlines{suffix}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(base)
        paths.append(path)
    return paths


if __name__ == "__main__":
    import sys
    import spec_loader
    if len(sys.argv) < 2:
        print("usage: python sightlines.py <spec.json> [outdir]")
        raise SystemExit(2)
    spec = spec_loader.load_spec(sys.argv[1])
    print(report(spec))
    if len(sys.argv) > 2:
        for p in write_overlays(spec, sys.argv[2]):
            print("wrote", p)
