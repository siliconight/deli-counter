"""
floorplan.py  --  top-down annotated floorplan SVG (offline, bpy-free)
======================================================================
Deli Counter computes rich spatial intel and then discards it as printed
numbers. This renders a readable top-down floorplan per story so a designer can
judge the *space*, not a table. Pure-Python SVG strings — no Pillow/cairo/
matplotlib — so it stays offline, deterministic, dependency-free, and runs
without Blender.

First pass (clean): rooms as labelled boxes, exterior + partition walls with
gaps at doorways/openings, and gameplay markers as icons. Tactical overlays
(graph edges, chokepoints, single-route flags) layer on in a later pass.

Stair overlay (v0.76): every stair serving the story draws its reserved
footprint, its ascent ARROW (entry -> exit, so a stair facing a wall is
visible at a glance), its facing label, and -- on the stories where they
apply -- the entry/exit landing rects the review reserves. Green landing =
lower approach, blue = upper departure.

World convention: meters, origin at footprint center, +X east, +Y north, +Z up.
SVG convention: +x right, +y DOWN — so we flip Y (north renders up). A story is
selected by z: markers whose z falls in [story*sh, story*sh+sh) belong to it.

Entry points:
    svg = render_story(spec, story)        # one SVG string
    paths = write_floorplans(spec, outdir) # one file per story -> list of paths
"""

PADDING = 40          # px around the building
PX_PER_M = 12         # scale: pixels per meter
WALL_W = 3            # wall stroke width

# marker icon styling by type family
MARKER_STYLE = {
    "attacker_spawn": ("#2e7d32", "▲"),
    "defender_spawn": ("#c62828", "▼"),
    "survivor_spawn": ("#2e7d32", "◆"),
    "horde_spawn":    ("#6a1b9a", "✸"),
    "objective":      ("#ef6c00", "★"),
    "loot":           ("#f9a825", "$"),
    "extraction":     ("#00838f", "⤢"),
    "rescue":         ("#00838f", "✚"),
    "cover_low":      ("#607d8b", "▢"),
    "cover_high":     ("#455a64", "▣"),
    "camera_socket":  ("#9e9e9e", "◉"),
    "patrol_point":   ("#795548", "•"),
}
DEFAULT_MARKER = ("#888888", "•")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


class _Tx:
    """World-meters -> SVG-pixels transform, with Y flip. Canvas is padded
    enough to show markers placed just outside the footprint (e.g. attacker
    spawns breaching from outside)."""
    def __init__(self, spec):
        self.hx = spec.footprint_x / 2
        self.hy = spec.footprint_y / 2
        # extend the drawable area if any marker sits outside the footprint
        ox = oy = 0.0
        for m in getattr(spec, "markers", []) or []:
            ox = max(ox, abs(getattr(m, "x", 0.0)) - self.hx)
            oy = max(oy, abs(getattr(m, "y", 0.0)) - self.hy)
        for st in getattr(spec, "stairs", []) or []:
            # exterior towers stand off the facade; keep them on the canvas
            ox = max(ox, abs(getattr(st, "x", 0.0)) - self.hx)
            oy = max(oy, abs(getattr(st, "y", 0.0)) - self.hy)
        self.ox = max(0.0, ox) + 1.0 if ox > 0 else 0.0
        self.oy = max(0.0, oy) + 1.0 if oy > 0 else 0.0
        self.w = (spec.footprint_x + 2 * self.ox) * PX_PER_M + 2 * PADDING
        self.h = (spec.footprint_y + 2 * self.oy) * PX_PER_M + 2 * PADDING

    def x(self, wx):
        return PADDING + (wx + self.hx + self.ox) * PX_PER_M

    def y(self, wy):
        # flip: world +Y (north) -> screen up
        return PADDING + (self.hy + self.oy - wy) * PX_PER_M


def _story_height(spec):
    return getattr(spec, "story_height", 3.0) or 3.0


def _marker_story(spec, m):
    z = getattr(m, "z", 0.0) or 0.0
    sh = _story_height(spec)
    # round to nearest story; basement (negative z) -> -1 etc.
    import math
    return int(math.floor((z + 0.01) / sh)) if z >= 0 else int(math.floor(z / sh))


def _opening_gaps(opening_list, wall_lo, wall_hi):
    """Given openings (pos in -0.5..0.5 fraction) along a wall spanning
    [wall_lo, wall_hi] in world units, return list of (gap_lo, gap_hi) world
    intervals to leave open. Doors/garages/breaches are floor-level gaps;
    windows are drawn as thinner marks (still a visual gap here)."""
    gaps = []
    span = wall_hi - wall_lo
    mid = (wall_hi + wall_lo) / 2
    for op in opening_list:
        r = op.resolved()
        width = r.get("width") or 1.0
        center = mid + op.pos * span
        gaps.append((center - width / 2, center + width / 2, op.kind))
    return gaps


def _wall_segments_with_gaps(p0, p1, gaps, axis):
    """Split a wall line from p0 to p1 (along `axis`) into drawn segments,
    skipping the gap intervals. axis 'x' means the wall runs along world X
    (varying x), 'y' means along world Y."""
    # gaps are (lo, hi, kind) along the varying coordinate
    cuts = sorted([g for g in gaps], key=lambda g: g[0])
    segs = []
    if axis == "x":
        lo, hi = p0[0], p1[0]
        fixed = p0[1]
    else:
        lo, hi = p0[1], p1[1]
        fixed = p0[0]
    cur = lo
    for glo, ghi, _kind in cuts:
        glo = max(glo, lo)
        ghi = min(ghi, hi)
        if ghi <= cur:
            continue
        if glo > cur:
            segs.append((cur, glo))
        cur = max(cur, ghi)
    if cur < hi:
        segs.append((cur, hi))
    # map back to point pairs
    out = []
    for a, b in segs:
        if axis == "x":
            out.append(((a, fixed), (b, fixed)))
        else:
            out.append(((fixed, a), (fixed, b)))
    return out


STAIR_COLOR = "#7b1fa2"       # stair footprint + ascent arrow
LAND_LOWER_COLOR = "#2e7d32"  # entry landing (approach)
LAND_UPPER_COLOR = "#1565c0"  # exit landing (departure)


def _rect_svg(tx, rect, fill, stroke, width=1.5, dash=None, opacity=0.25):
    x0, y0, x1, y1 = rect
    sx, sy = tx.x(x0), tx.y(y1)
    w, h = (x1 - x0) * PX_PER_M, (y1 - y0) * PX_PER_M
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>')


def _draw_stairs(parts, tx, spec, story):
    """Reserved footprint, ascent arrow, facing label, and landing rects for
    every stair serving this story. The ascent arrow runs lower entry ->
    upper exit, so a stair pointed into a wall is visible immediately."""
    try:
        import stairwell
    except ImportError:
        return
    for i, st in enumerate(getattr(spec, "stairs", []) or []):
        served = stairwell.floors_served(spec, st)
        if story not in served:
            continue
        sid = stairwell.stair_ident(st, i)
        rect = stairwell.footprint_rect(st)
        parts.append(_rect_svg(tx, rect, STAIR_COLOR, STAIR_COLOR,
                               width=1.5, dash="4 3", opacity=0.15))
        cx, cy = tx.x((rect[0] + rect[2]) / 2), tx.y((rect[1] + rect[3]) / 2)
        facing = getattr(st, "facing", "N") or "N"
        role = getattr(st, "role", None)
        label = f"{sid} ↑{facing}" + (f" [{role}]" if role else "")
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="9" '
            f'fill="{STAIR_COLOR}" text-anchor="middle" font-weight="bold">'
            f'{_esc(label)}</text>')

        eps = stairwell.stair_endpoints(st)
        lows = [e for e in eps if e["end"] == "lower"]
        ups = [e for e in eps if e["end"] == "upper"]
        lo_story, hi_story = min(served), max(served)
        # landing rects on the stories where they physically apply
        if story == lo_story:
            for e in lows:
                parts.append(_rect_svg(tx, e["rect"], LAND_LOWER_COLOR,
                                       LAND_LOWER_COLOR, width=1.2,
                                       opacity=0.30))
        if story == hi_story:
            for e in ups:
                parts.append(_rect_svg(tx, e["rect"], LAND_UPPER_COLOR,
                                       LAND_UPPER_COLOR, width=1.2,
                                       opacity=0.30))
        # ascent arrow: entry point -> exit point (every served story, so a
        # mid-story plan still shows which way the shaft climbs)
        if lows and ups:
            (ax, ay), (bx, by) = lows[0]["point"], ups[0]["point"]
            x1p, y1p, x2p, y2p = tx.x(ax), tx.y(ay), tx.x(bx), tx.y(by)
            parts.append(
                f'<line x1="{x1p:.1f}" y1="{y1p:.1f}" x2="{x2p:.1f}" '
                f'y2="{y2p:.1f}" stroke="{STAIR_COLOR}" stroke-width="2"/>')
            # arrowhead at the exit end
            import math
            ang = math.atan2(y2p - y1p, x2p - x1p)
            for da in (2.6, -2.6):
                hx2 = x2p + 8 * math.cos(ang + da)
                hy2 = y2p + 8 * math.sin(ang + da)
                parts.append(
                    f'<line x1="{x2p:.1f}" y1="{y2p:.1f}" x2="{hx2:.1f}" '
                    f'y2="{hy2:.1f}" stroke="{STAIR_COLOR}" '
                    f'stroke-width="2"/>')
        elif getattr(st, "style", "") == "spiral":
            r = st.width * PX_PER_M
            parts.append(
                f'<circle cx="{tx.x(st.x):.1f}" cy="{tx.y(st.y):.1f}" '
                f'r="{r:.1f}" fill="none" stroke="{STAIR_COLOR}" '
                f'stroke-width="1.5" stroke-dasharray="4 3"/>')


def render_story(spec, story):
    """Return an SVG string for one story."""
    tx = _Tx(spec)
    sh = _story_height(spec)
    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tx.w}" '
        f'height="{tx.h}" viewBox="0 0 {tx.w} {tx.h}" '
        f'font-family="sans-serif">')
    parts.append(f'<rect width="{tx.w}" height="{tx.h}" fill="#fafafa"/>')

    # title
    label = ("basement" if story < 0 else
             "ground floor" if story == 0 else f"floor {story}")
    parts.append(
        f'<text x="{PADDING}" y="24" font-size="16" font-weight="bold" '
        f'fill="#333">{_esc(spec.name)} — {label}</text>')

    # rooms on this story
    for r in getattr(spec, "rooms", []) or []:
        if r.story != story:
            continue
        x0, y0, x1, y1 = r.bounds
        sx, sy = tx.x(x0), tx.y(y1)   # top-left in screen space (y1 is north)
        w = (x1 - x0) * PX_PER_M
        h = (y1 - y0) * PX_PER_M
        role = getattr(r, "role", "") or ""
        fill = "#fff3e0" if getattr(r, "objective", False) or "objective" in role \
            else "#e3f2fd" if "entry" in role \
            else "#f1f8e9" if "fortifiable" in role or "safe" in role \
            else "#f5f5f5"
        parts.append(
            f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="#bbb" stroke-width="1"/>')
        cx, cy = tx.x((x0 + x1) / 2), tx.y((y0 + y1) / 2)
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="10" fill="#555" '
            f'text-anchor="middle">{_esc(r.id)}</text>')

    # exterior walls (footprint outline) with door/window gaps for this story
    hx, hy = tx.hx, tx.hy
    # wall endpoints in world coords per side
    sides = {
        "S": ((-hx, -hy), (hx, -hy), "x"),
        "N": ((-hx, hy), (hx, hy), "x"),
        "W": ((-hx, -hy), (-hx, hy), "y"),
        "E": ((hx, -hy), (hx, hy), "y"),
    }
    walls_by_side = {}
    for w in getattr(spec, "ext_walls", []) or []:
        if w.story == story:
            walls_by_side.setdefault(w.wall, []).append(w)
    for side, (p0, p1, axis) in sides.items():
        wlist = walls_by_side.get(side, [])
        if wlist:
            lo = p0[0] if axis == "x" else p0[1]
            hi = p1[0] if axis == "x" else p1[1]
            gaps = []
            for w in wlist:
                gaps += _opening_gaps(w.openings, lo, hi)
            segs = _wall_segments_with_gaps(p0, p1, gaps, axis)
        else:
            segs = [(p0, p1)]
        for a, b in segs:
            parts.append(
                f'<line x1="{tx.x(a[0]):.1f}" y1="{tx.y(a[1]):.1f}" '
                f'x2="{tx.x(b[0]):.1f}" y2="{tx.y(b[1]):.1f}" '
                f'stroke="#333" stroke-width="{WALL_W}"/>')

    # partitions with gaps
    for p in getattr(spec, "partitions", []) or []:
        if p.story != story:
            continue
        if p.axis == "X":
            # wall runs along X at y=pos
            p0, p1, axis = (p.start, p.pos), (p.end, p.pos), "x"
        else:
            # wall runs along Y at x=pos
            p0, p1, axis = (p.pos, p.start), (p.pos, p.end), "y"
        lo = p0[0] if axis == "x" else p0[1]
        hi = p1[0] if axis == "x" else p1[1]
        gaps = _opening_gaps(p.openings, lo, hi)
        for a, b in _wall_segments_with_gaps(p0, p1, gaps, axis):
            parts.append(
                f'<line x1="{tx.x(a[0]):.1f}" y1="{tx.y(a[1]):.1f}" '
                f'x2="{tx.x(b[0]):.1f}" y2="{tx.y(b[1]):.1f}" '
                f'stroke="#666" stroke-width="2"/>')

    # stairs serving this story: reserved footprint + ascent arrow + landings
    _draw_stairs(parts, tx, spec, story)

    # markers on this story
    legend_used = {}
    for m in getattr(spec, "markers", []) or []:
        if _marker_story(spec, m) != story:
            continue
        mx = getattr(m, "x", 0.0)
        my = getattr(m, "y", 0.0)
        color, glyph = MARKER_STYLE.get(m.type, DEFAULT_MARKER)
        legend_used[m.type] = (color, glyph)
        parts.append(
            f'<text x="{tx.x(mx):.1f}" y="{tx.y(my) + 5:.1f}" font-size="14" '
            f'fill="{color}" text-anchor="middle" font-weight="bold">'
            f'{glyph}</text>')

    # legend
    ly = tx.h - PADDING + 8
    lx = PADDING
    for mtype, (color, glyph) in sorted(legend_used.items()):
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" fill="{color}" '
            f'font-weight="bold">{glyph}</text>')
        parts.append(
            f'<text x="{lx + 14:.1f}" y="{ly:.1f}" font-size="11" fill="#555">'
            f'{_esc(mtype)}</text>')
        lx += 16 + len(mtype) * 7 + 10
        if lx > tx.w - 120:
            lx = PADDING
            ly += 16

    # north arrow
    parts.append(
        f'<text x="{tx.w - 24}" y="{PADDING}" font-size="13" fill="#999" '
        f'text-anchor="middle">N↑</text>')

    parts.append('</svg>')
    return "\n".join(parts)


def stories_in(spec):
    """All stories that have rooms, markers, or stair service (a story a
    stair climbs through deserves a plan even if unroomed -- the ascent
    arrow and landings are the point)."""
    s = set(r.story for r in (getattr(spec, "rooms", []) or []))
    for m in getattr(spec, "markers", []) or []:
        s.add(_marker_story(spec, m))
    try:
        import stairwell
        for st in getattr(spec, "stairs", []) or []:
            for fs in stairwell.floors_served(spec, st):
                if fs < getattr(spec, "n_stories", 1):   # roof has no plan
                    s.add(fs)
    except ImportError:
        pass
    if not s:
        s = {0}
    return sorted(s)


def write_floorplans(spec, outdir):
    """Write one SVG per story. Returns list of file paths."""
    import os
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for st in stories_in(spec):
        suffix = ("B" if st < 0 else str(st))
        path = os.path.join(outdir, f"{spec.name}.floor{suffix}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_story(spec, st))
        paths.append(path)
    return paths


if __name__ == "__main__":
    import sys
    import spec_loader
    if len(sys.argv) < 2:
        print("usage: python floorplan.py <spec.json> [outdir]")
        raise SystemExit(2)
    spec = spec_loader.load_spec(sys.argv[1])
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    for p in write_floorplans(spec, outdir):
        print("wrote", p)
