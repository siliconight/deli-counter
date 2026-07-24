"""
floorplan.py  --  top-down annotated floorplan SVG (offline, bpy-free)
======================================================================
Deli Counter computes rich spatial intel and then discards it as printed
numbers. This renders a readable top-down floorplan per story so a designer can
judge the *space*, not a table. Pure-Python SVG strings — no Pillow/cairo/
matplotlib — so it stays offline, deterministic, dependency-free, and runs
without Blender.

Rendering (v0.90):
  * rooms as labelled boxes; ROOM LABELS are drawn LAST, on top, with a white
    halo, so walls / fixtures / stairs never cover a room name.
  * exterior + partition walls, with partition extents CLAMPED to the footprint
    (some specs over-extend start/end past the shell).
  * TYPED openings: doors draw a leaf + swing arc, windows a glazed double
    line, breaches a dashed soft/reinforceable panel, garages a roll-door comb.
  * stairs: reserved footprint, ascent arrow, facing + DESTINATION label.
  * ladders, furniture volumes, and open-to-below (slab holes / floor holes)
    are drawn (previously omitted).
  * scale bar + overall dimensions + north arrow.
  * every layer is a named <g id="..."> and features carry data-* ids, so the
    SVG is toggleable and traceable back to spec objects.

World convention: meters, origin at footprint center, +X east, +Y north, +Z up.
SVG convention: +x right, +y DOWN — so we flip Y (north renders up). A story is
selected by z: markers whose z falls in [story*sh, story*sh+sh) belong to it.

Entry points:
    svg = render_story(spec, story)        # one SVG string
    paths = write_floorplans(spec, outdir) # one file per story -> list of paths
"""

PADDING = 40          # px around the building
PX_PER_M = 12         # scale: pixels per meter
WALL_W = 3            # (legacy) exterior wall stroke width
PART_W = 2            # (legacy) partition stroke width
PART_T = 0.15         # interior partition thickness (m) for poché fill
INK = "#1f2933"       # poché wall fill
LEGEND_H = 58         # extra px below the footprint for scale bar + legend

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

# opening symbol colors
OPEN_COLOR = {"door": "#3e4c59", "window": "#2f80c8",
              "breach": "#d1701f", "garage": "#5b6b7b"}
STAIR_COLOR = "#7b1fa2"       # stair footprint + ascent arrow
LAND_LOWER_COLOR = "#2e7d32"  # entry landing (approach)
LAND_UPPER_COLOR = "#1565c0"  # exit landing (departure)
LADDER_COLOR = "#00838f"
VOID_COLOR = "#b0392f"        # open-to-below hatch


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
        ox = oy = 0.0
        for m in getattr(spec, "markers", []) or []:
            ox = max(ox, abs(getattr(m, "x", 0.0)) - self.hx)
            oy = max(oy, abs(getattr(m, "y", 0.0)) - self.hy)
        for st in getattr(spec, "stairs", []) or []:
            ox = max(ox, abs(getattr(st, "x", 0.0)) - self.hx)
            oy = max(oy, abs(getattr(st, "y", 0.0)) - self.hy)
        self.ox = max(0.0, ox) + 1.0 if ox > 0 else 0.0
        self.oy = max(0.0, oy) + 1.0 if oy > 0 else 0.0
        self.w = (spec.footprint_x + 2 * self.ox) * PX_PER_M + 2 * PADDING
        self.h = (spec.footprint_y + 2 * self.oy) * PX_PER_M + 2 * PADDING

    def x(self, wx):
        return PADDING + (wx + self.hx + self.ox) * PX_PER_M

    def y(self, wy):
        return PADDING + (self.hy + self.oy - wy) * PX_PER_M


def _story_height(spec):
    return getattr(spec, "story_height", 3.0) or 3.0


def _marker_story(spec, m):
    import math
    z = getattr(m, "z", 0.0) or 0.0
    sh = _story_height(spec)
    return int(math.floor((z + 0.01) / sh)) if z >= 0 else int(math.floor(z / sh))


def _line(tx, a, b, stroke, w, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{tx.x(a[0]):.1f}" y1="{tx.y(a[1]):.1f}" '
            f'x2="{tx.x(b[0]):.1f}" y2="{tx.y(b[1]):.1f}" '
            f'stroke="{stroke}" stroke-width="{w}"{d}/>')


def _rect_svg(tx, rect, fill, stroke, width=1.5, dash=None, opacity=0.25,
              data=None):
    x0, y0, x1, y1 = rect
    sx, sy = tx.x(x0), tx.y(y1)
    w, h = (x1 - x0) * PX_PER_M, (y1 - y0) * PX_PER_M
    d = f' stroke-dasharray="{dash}"' if dash else ""
    dat = f' {data}' if data else ""
    return (f'<rect{dat} x="{sx:.1f}" y="{sy:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>')


# ---------------------------------------------------------------------------
# walls + typed openings
# ---------------------------------------------------------------------------

def _band_rect(tx, a, b, fixed, axis, t, fill=INK, stroke=None, sw=0):
    """A filled wall band: the wall runs a..b along `axis` at perpendicular
    coord `fixed`, with thickness t (m). Returns an SVG <rect>."""
    if axis == "x":
        x0, y0, x1, y1 = a, fixed - t / 2, b, fixed + t / 2
    else:
        x0, y0, x1, y1 = fixed - t / 2, a, fixed + t / 2, b
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (f'<rect x="{tx.x(x0):.1f}" y="{tx.y(y1):.1f}" '
            f'width="{(x1 - x0) * PX_PER_M:.1f}" '
            f'height="{(y1 - y0) * PX_PER_M:.1f}" fill="{fill}"{s}/>')


def _opening_symbol(tx, acc, op, aP, bP, nrm, w, t=0.0):
    """Draw a typed opening symbol into `acc` (a list). aP/bP are the two jamb
    points in world coords; nrm is the unit interior direction (perp to wall);
    t is the wall thickness (m) so windows fill the poché band."""
    kind = getattr(op, "kind", "door")
    kind_draw = "door" if kind in ("vault", "teller", "safe_deposit") else kind
    color = OPEN_COLOR.get(kind_draw, "#3e4c59")
    tag = _esc(getattr(op, "tag", None) or kind)
    ax, ay = aP
    bx, by = bP
    if kind_draw == "window":
        # glazed band filling the wall thickness + a center mullion line
        px, py = nrm
        corners = [(ax + px * t / 2, ay + py * t / 2),
                   (ax - px * t / 2, ay - py * t / 2),
                   (bx - px * t / 2, by - py * t / 2),
                   (bx + px * t / 2, by + py * t / 2)]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        rx0, rx1, ry0, ry1 = min(xs), max(xs), min(ys), max(ys)
        acc.append(
            f'<g data-opening="{tag}" data-kind="window">'
            f'<rect x="{tx.x(rx0):.1f}" y="{tx.y(ry1):.1f}" '
            f'width="{(rx1 - rx0) * PX_PER_M:.1f}" '
            f'height="{(ry1 - ry0) * PX_PER_M:.1f}" fill="#dfe8f0" '
            f'stroke="#8fb0cc" stroke-width="0.8"/>'
            + _line(tx, aP, bP, "#2f6ea5", 1.1) + '</g>')
    elif kind_draw == "breach":
        rein = getattr(op, "reinforceable", None) or \
            getattr(op, "breach_class", "") == "reinforceable"
        dash = "2 3" if rein else "5 3"
        acc.append(f'<g data-opening="{tag}" data-kind="breach">'
                   + _line(tx, aP, bP, color, 3, dash=dash) + '</g>')
    elif kind_draw == "garage":
        seg = [f'<g data-opening="{tag}" data-kind="garage">']
        n = 5
        for i in range(n + 1):
            t = i / n
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            qx, qy = px + nrm[0] * 0.9, py + nrm[1] * 0.9
            seg.append(_line(tx, (px, py), (qx, qy), color, 1.6))
        seg.append('</g>')
        acc.append("".join(seg))
    else:  # door — leaf + swing arc
        tx2, ty2 = ax + nrm[0] * w, ay + nrm[1] * w
        rpx = w * PX_PER_M
        sweep = 1 if (nrm[0] + nrm[1]) > 0 else 0
        acc.append(
            f'<g data-opening="{tag}" data-kind="door" stroke="{color}" '
            f'fill="none" stroke-width="1.4">'
            + _line(tx, (ax, ay), (tx2, ty2), color, 1.4)
            + f'<path d="M {tx.x(tx2):.1f} {tx.y(ty2):.1f} '
              f'A {rpx:.1f} {rpx:.1f} 0 0 {sweep} '
              f'{tx.x(bx):.1f} {tx.y(by):.1f}"/></g>')


def _wall_and_openings(tx, walls_acc, opens_acc, p0, p1, axis, openings,
                       t_m, interior_sign):
    """Split a wall p0->p1 (axis 'x' varies x, 'y' varies y) into drawn
    segments skipping openings, appending poché band rects (thickness t_m, in
    metres) to walls_acc and typed opening symbols to opens_acc. Extent is
    CLAMPED to the footprint."""
    lo0 = p0[0] if axis == "x" else p0[1]
    hi0 = p1[0] if axis == "x" else p1[1]
    fixed = p0[1] if axis == "x" else p0[0]
    span = hi0 - lo0
    mid = (hi0 + lo0) / 2
    bound = tx.hx if axis == "x" else tx.hy
    lo, hi = max(lo0, -bound), min(hi0, bound)
    gaps = []
    for op in openings:
        try:
            width = op.resolved().get("width") or 1.0
        except Exception:
            width = getattr(op, "width", None) or 1.0
        c = mid + getattr(op, "pos", 0.0) * span
        gaps.append((c - width / 2, c + width / 2, op, c, width))
    gaps.sort(key=lambda t: t[0])
    segs = []
    cur = lo
    for glo, ghi, _op, _c, _w in gaps:
        glo, ghi = max(glo, lo), min(ghi, hi)
        if ghi <= cur:
            continue
        if glo > cur:
            segs.append((cur, glo))
        cur = max(cur, ghi)
    if cur < hi:
        segs.append((cur, hi))
    for a, b in segs:
        walls_acc.append(_band_rect(tx, a, b, fixed, axis, t_m))
    for glo, ghi, op, c, w in gaps:
        if c < lo or c > hi:
            continue
        if axis == "x":
            aP, bP, nrm = (glo, fixed), (ghi, fixed), (0.0, float(interior_sign))
        else:
            aP, bP, nrm = (fixed, glo), (fixed, ghi), (float(interior_sign), 0.0)
        _opening_symbol(tx, opens_acc, op, aP, bP, nrm, w, t_m)


# ---------------------------------------------------------------------------
# stairs / ladders / voids / volumes
# ---------------------------------------------------------------------------

def _story_tag(s):
    return "B" if s < 0 else ("G" if s == 0 else str(s))


def _draw_stairs(parts, tx, spec, story, notes):
    """Draw each stair serving this story: reserved footprint, landings, and an
    ascent arrow, marked with a small NUMBERED badge + UP/DN only. The verbose
    id / facing / role / destination text is pushed to `notes` and rendered in
    the margin key, so nothing long is drawn over the (often cramped) stair."""
    try:
        import stairwell
    except ImportError:
        return
    import math
    for i, st in enumerate(getattr(spec, "stairs", []) or []):
        served = stairwell.floors_served(spec, st)
        if story not in served:
            continue
        sid = stairwell.stair_ident(st, i)
        rect = stairwell.footprint_rect(st)
        parts.append(_rect_svg(tx, rect, STAIR_COLOR, STAIR_COLOR, width=1.5,
                               dash="4 3", opacity=0.15,
                               data=f'data-stair="{_esc(sid)}"'))
        cx, cy = tx.x((rect[0] + rect[2]) / 2), tx.y((rect[1] + rect[3]) / 2)
        facing = getattr(st, "facing", "N") or "N"
        role = getattr(st, "role", None)
        eps = stairwell.stair_endpoints(st)
        lows = [e for e in eps if e["end"] == "lower"]
        ups = [e for e in eps if e["end"] == "upper"]
        lo_story, hi_story = min(served), max(served)
        if story == lo_story:
            for e in lows:
                parts.append(_rect_svg(tx, e["rect"], LAND_LOWER_COLOR,
                                       LAND_LOWER_COLOR, width=1.2, opacity=0.30))
        if story == hi_story:
            for e in ups:
                parts.append(_rect_svg(tx, e["rect"], LAND_UPPER_COLOR,
                                       LAND_UPPER_COLOR, width=1.2, opacity=0.30))
        if lows and ups:
            (ax, ay), (bx, by) = lows[0]["point"], ups[0]["point"]
            x1p, y1p, x2p, y2p = tx.x(ax), tx.y(ay), tx.x(bx), tx.y(by)
            parts.append(
                f'<line x1="{x1p:.1f}" y1="{y1p:.1f}" x2="{x2p:.1f}" '
                f'y2="{y2p:.1f}" stroke="{STAIR_COLOR}" stroke-width="2"/>')
            ang = math.atan2(y2p - y1p, x2p - x1p)
            for da in (2.6, -2.6):
                hx2 = x2p + 8 * math.cos(ang + da)
                hy2 = y2p + 8 * math.sin(ang + da)
                parts.append(
                    f'<line x1="{x2p:.1f}" y1="{y2p:.1f}" x2="{hx2:.1f}" '
                    f'y2="{hy2:.1f}" stroke="{STAIR_COLOR}" stroke-width="2"/>')
        elif getattr(st, "style", "") == "spiral":
            r = st.width * PX_PER_M
            parts.append(
                f'<circle cx="{tx.x(st.x):.1f}" cy="{tx.y(st.y):.1f}" '
                f'r="{r:.1f}" fill="none" stroke="{STAIR_COLOR}" '
                f'stroke-width="1.5" stroke-dasharray="4 3"/>')
        # direction from here
        others = sorted(s for s in served if s != story)
        up = [s for s in others if s > story]
        dn = [s for s in others if s < story]
        dirtxt = "UP" if up else ("DN" if dn else "")
        # small numbered badge only -> never overlaps neighbours or room names
        num = i + 1
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{STAIR_COLOR}" '
            f'stroke="#ffffff" stroke-width="1.5"/>')
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + 3.5:.1f}" font-size="9.5" fill="#ffffff" '
            f'text-anchor="middle" font-weight="700">{num}</text>')
        if dirtxt:
            parts.append(
                f'<text x="{cx:.1f}" y="{cy - 11:.1f}" font-size="8" '
                f'fill="{STAIR_COLOR}" text-anchor="middle" font-weight="700">'
                f'{dirtxt}</text>')
        # verbose text -> margin key (keeps id/facing/role out of the drawing)
        dest = []
        if up:
            dest.append("↑" + _story_tag(max(up)))
        if dn:
            dest.append("↓" + _story_tag(min(dn)))
        note = f'{num}. {sid} ↑{facing}' + (f' [{role}]' if role else '')
        if dest:
            note += '  ' + " ".join(dest)
        notes.append(note)


def _ladder_stories(ld):
    a, b = ld.from_story, ld.to_story
    return set(range(min(a, b), max(a, b) + 1))


def _draw_ladders(parts, tx, spec, story):
    for ld in getattr(spec, "ladders", []) or []:
        if story not in _ladder_stories(ld):
            continue
        cx, cy = ld.x, ld.y
        w = getattr(ld, "width", 0.5) or 0.5
        rect = (cx - w / 2, cy - 0.6, cx + w / 2, cy + 0.6)
        parts.append(_rect_svg(tx, rect, "none", LADDER_COLOR, width=1.4,
                               opacity=0.0, data=f'data-ladder="{_esc(ld.id or "")}"'))
        x0, y0, x1, y1 = rect
        for i in range(1, 5):
            yy = y0 + (y1 - y0) * i / 5
            parts.append(_line(tx, (x0, yy), (x1, yy), LADDER_COLOR, 1))
        role = (getattr(ld, "role", None) or "ladder").replace("_", " ")
        parts.append(
            f'<text x="{tx.x(cx):.1f}" y="{tx.y(y0) + 11:.1f}" font-size="8" '
            f'fill="{LADDER_COLOR}" text-anchor="middle" font-weight="600">'
            f'{_esc(role)}</text>')


def _draw_voids(parts, tx, spec, story):
    """Open-to-below: slab holes + floor-hole/hatch vertical links on this
    story, drawn as a cross-hatched region with an 'OPEN TO BELOW' tag."""
    rects = []
    for h in getattr(spec, "slab_holes", []) or []:
        if h.story == story:
            rects.append((h.x, h.y, h.size_x, h.size_y, "open to below"))
    for vl in getattr(spec, "vertical_links", []) or []:
        if getattr(vl, "kind", "") in ("floor_hole", "hatch") \
                and vl.story == story and vl.x is not None and vl.size_x:
            rects.append((vl.x, vl.y, vl.size_x, vl.size_y,
                          vl.kind.replace("_", " ")))
    for x, y, sx, sy, lbl in rects:
        rect = (x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)
        parts.append(_rect_svg(tx, rect, VOID_COLOR, VOID_COLOR, width=1.4,
                               dash="3 3", opacity=0.10))
        x0, y0, x1, y1 = rect
        parts.append(_line(tx, (x0, y0), (x1, y1), VOID_COLOR, 1, dash="3 3"))
        parts.append(_line(tx, (x0, y1), (x1, y0), VOID_COLOR, 1, dash="3 3"))
        short = {"open to below": "OPEN ↓", "hatch": "HATCH ↓",
                 "floor hole": "HOLE ↓"}.get(lbl, lbl.upper())
        lyv = tx.y(y0) + 9   # just below the box, clear of any stair badge above
        common = (f'x="{tx.x(x):.1f}" y="{lyv:.1f}" font-size="7.5" '
                  f'text-anchor="middle" font-weight="700"')
        parts.append(f'<text {common} fill="none" stroke="#ffffff" '
                     f'stroke-width="2.6" stroke-linejoin="round">{short}</text>')
        parts.append(f'<text {common} fill="{VOID_COLOR}">{short}</text>')


def _draw_volumes(parts, tx, spec, story):
    """Furniture / fixtures: solid boxes whose base falls on this story."""
    sh = _story_height(spec)
    for v in getattr(spec, "volumes", []) or []:
        if not getattr(v, "visual", True):
            continue
        z = getattr(v, "z", 0.0) or 0.0
        base = z - getattr(v, "size_z", 0.0) / 2
        if not (story * sh - 0.6 <= base < (story + 1) * sh - 0.6):
            continue
        rect = (v.x - v.size_x / 2, v.y - v.size_y / 2,
                v.x + v.size_x / 2, v.y + v.size_y / 2)
        parts.append(_rect_svg(tx, rect, "#e9edf1", "#c3ccd6", width=1,
                               opacity=1.0, data=f'data-object="{_esc(v.name)}"'))


# ---------------------------------------------------------------------------
# main render
# ---------------------------------------------------------------------------

def render_story(spec, story):
    """Return an SVG string for one story."""
    tx = _Tx(spec)
    sh = _story_height(spec)
    stair_notes = []
    # reserve margin height for the stair key (one line per stair on this story)
    nstair = 0
    try:
        import stairwell as _sw
        nstair = sum(1 for st in (getattr(spec, "stairs", []) or [])
                     if story in _sw.floors_served(spec, st))
    except Exception:
        nstair = 0
    notes_h = (20 + nstair * 13) if nstair else 0
    W, H = tx.w, tx.h + LEGEND_H + notes_h
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Inter,Segoe UI,sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>']

    # ---- grid ----
    grid = ['<g id="grid" stroke="#eef2f6" stroke-width="1">']
    step = 2.0
    nx = int(tx.hx // step)
    for i in range(-nx, nx + 1):
        grid.append(_line(tx, (i * step, -tx.hy), (i * step, tx.hy), "#eef2f6", 1))
    ny = int(tx.hy // step)
    for i in range(-ny, ny + 1):
        grid.append(_line(tx, (-tx.hx, i * step), (tx.hx, i * step), "#eef2f6", 1))
    grid.append('</g>')
    out += grid

    # ---- rooms (fills) + deferred labels ----
    ROOM_FILL = {"objective_room": "#fdf0dd", "public_entry": "#fbf6e7",
                 "loot_room": "#f4eee0", "fortifiable": "#f2f3e4",
                 "connector": "#faf8f2"}
    room_fills = ['<g id="rooms">']
    room_labels = []
    for r in getattr(spec, "rooms", []) or []:
        if r.story != story:
            continue
        x0, y0, x1, y1 = r.bounds
        role = getattr(r, "role", "") or ""
        fill = ROOM_FILL["objective_room"] if getattr(r, "objective", False) \
            else ROOM_FILL.get(role, "#f6f8fa")
        room_fills.append(
            f'<rect data-room="{_esc(r.id)}" x="{tx.x(x0):.1f}" y="{tx.y(y1):.1f}" '
            f'width="{(x1 - x0) * PX_PER_M:.1f}" height="{(y1 - y0) * PX_PER_M:.1f}" '
            f'fill="{fill}" stroke="#d7dee6" stroke-width="1"/>')
        cx = tx.x((x0 + x1) / 2)
        # if a stair/ladder sits in this room, keep the name at the top edge so
        # it never collides with the stair markers in the room centre
        occ = any(x0 <= getattr(v, "x", 1e9) <= x1 and y0 <= getattr(v, "y", 1e9) <= y1
                  for v in ((getattr(spec, "stairs", []) or [])
                            + (getattr(spec, "ladders", []) or [])))
        ly = tx.y(y1) + 22 if (occ or (y1 - y0) * PX_PER_M >= 90) \
            else tx.y((y0 + y1) / 2) - 3
        sub = f'{x1 - x0:.1f} × {y1 - y0:.1f} m'   # lead with size (human-first)
        if role:
            sub += f' · {role}'
        room_labels.append((cx, ly, r.id, sub))
    room_fills.append('</g>')
    out += room_fills

    # ---- furniture ----
    fur = ['<g id="furniture">']
    _draw_volumes(fur, tx, spec, story)
    fur.append('</g>')
    out += fur

    # ---- open-to-below ----
    voids = ['<g id="open_to_below">']
    _draw_voids(voids, tx, spec, story)
    voids.append('</g>')
    out += voids

    # ---- walls + openings ----
    walls, opens = [], []
    hx, hy = tx.hx, tx.hy
    sides = {"S": ((-hx, -hy), (hx, -hy), "x", +1),
             "N": ((-hx, hy), (hx, hy), "x", -1),
             "W": ((-hx, -hy), (-hx, hy), "y", +1),
             "E": ((hx, -hy), (hx, hy), "y", -1)}
    wall_t = getattr(spec, "wall_thick", 0.3) or 0.3
    ewalls = {}
    for w in getattr(spec, "ext_walls", []) or []:
        if w.story == story:
            ewalls.setdefault(w.wall, []).append(w)
    for side, (p0, p1, axis, isign) in sides.items():
        wlist = ewalls.get(side, [])
        ops = [o for w in wlist for o in w.openings]
        _wall_and_openings(tx, walls, opens, p0, p1, axis, ops, wall_t, isign)
    for p in getattr(spec, "partitions", []) or []:
        if p.story != story:
            continue
        if p.axis == "X":
            p0, p1, axis = (p.start, p.pos), (p.end, p.pos), "x"
        else:
            p0, p1, axis = (p.pos, p.start), (p.pos, p.end), "y"
        isign = -1 if (getattr(p, "pos", 0) or 0) > 0 else 1
        _wall_and_openings(tx, walls, opens, p0, p1, axis,
                           getattr(p, "openings", []), PART_T, isign)
    out += ['<g id="walls">'] + walls + ['</g>']
    out += ['<g id="openings">'] + opens + ['</g>']

    # ---- stairs / ladders ----
    st_parts = ['<g id="stairs">']
    _draw_stairs(st_parts, tx, spec, story, stair_notes)
    st_parts.append('</g>')
    out += st_parts
    ld_parts = ['<g id="ladders">']
    _draw_ladders(ld_parts, tx, spec, story)
    ld_parts.append('</g>')
    out += ld_parts

    # ---- markers ----
    legend_used = {}
    mk = ['<g id="markers">']
    for m in getattr(spec, "markers", []) or []:
        if _marker_story(spec, m) != story:
            continue
        color, glyph = MARKER_STYLE.get(m.type, DEFAULT_MARKER)
        legend_used[m.type] = (color, glyph)
        mk.append(
            f'<text x="{tx.x(getattr(m, "x", 0.0)):.1f}" '
            f'y="{tx.y(getattr(m, "y", 0.0)) + 5:.1f}" font-size="14" '
            f'fill="{color}" text-anchor="middle" font-weight="bold">{glyph}</text>')
    mk.append('</g>')
    out += mk

    # ---- ROOM LABELS (last, on top, portable two-pass halo) ----
    lab = ['<g id="room_labels">']
    for cx, ly, rid, sub in room_labels:
        for txt, size, weight, fill, dy in (
                (rid, 11, 700, "#2b3742", 0), (sub, 8.5, 600, "#7b8794", 13)):
            common = (f'x="{cx:.1f}" y="{ly + dy:.1f}" font-size="{size}" '
                      f'font-weight="{weight}" text-anchor="middle"')
            lab.append(f'<text {common} fill="none" stroke="#ffffff" '
                       f'stroke-width="3.2" stroke-linejoin="round">{_esc(txt)}</text>')
            lab.append(f'<text {common} fill="{fill}">{_esc(txt)}</text>')
    lab.append('</g>')
    out += lab

    # ---- annotations: title, dims, scale, north, legend ----
    ann = ['<g id="annotations">']
    title = ("Basement" if story < 0 else
             "Ground Floor" if story == 0 else f"Floor {story}")
    ann.append(
        f'<text x="{PADDING}" y="24" font-size="15" font-weight="700" '
        f'fill="#1f2933">{_esc(spec.name)} — {title}</text>')
    elev = story * sh
    ann.append(
        f'<text x="{PADDING}" y="37" font-size="10" fill="#7b8794">'
        f'elevation {elev:.2f} m · {sh:.1f} m clg · deterministic render, no generative model</text>')
    ann.append(
        f'<text x="{tx.x(0):.0f}" y="{PADDING - 6}" font-size="9" fill="#90a0ad" '
        f'text-anchor="middle">◄ {spec.footprint_x:.0f} m ►</text>')
    midy = tx.y(0)
    ann.append(
        f'<text x="{PADDING - 14}" y="{midy:.0f}" font-size="9" fill="#90a0ad" '
        f'text-anchor="middle" transform="rotate(-90 {PADDING - 14} {midy:.0f})">'
        f'◄ {spec.footprint_y:.0f} m ►</text>')
    nx2, ny2 = W - 30, 34
    ann.append(f'<line x1="{nx2}" y1="{ny2 + 15}" x2="{nx2}" y2="{ny2 - 9}" '
               f'stroke="#52606d" stroke-width="1.6"/>')
    ann.append(f'<path d="M {nx2} {ny2 - 12} l -4 8 l 8 0 z" fill="#52606d"/>')
    ann.append(f'<text x="{nx2}" y="{ny2 + 27}" font-size="10" fill="#52606d" '
               f'text-anchor="middle">N</text>')
    sbx, sby = PADDING, tx.h + 24
    ann.append(f'<line x1="{sbx}" y1="{sby}" x2="{sbx + 5 * PX_PER_M:.0f}" '
               f'y2="{sby}" stroke="#3e4c59" stroke-width="3"/>')
    for t in (0, 1):
        xx = sbx + t * 5 * PX_PER_M
        ann.append(f'<line x1="{xx:.0f}" y1="{sby - 4}" x2="{xx:.0f}" '
                   f'y2="{sby + 4}" stroke="#3e4c59" stroke-width="2"/>')
    ann.append(f'<text x="{sbx}" y="{sby + 15}" font-size="10" fill="#52606d">'
               f'0 ————— 5 m</text>')
    lx, ly2 = PADDING + 130, tx.h + 20
    arch = [("#3e4c59", "door"), ("#2f80c8", "window"), ("#d1701f", "breach"),
            ("#5b6b7b", "garage"), (STAIR_COLOR, "stair"),
            (LADDER_COLOR, "ladder"), ("#c3ccd6", "fixture"),
            (VOID_COLOR, "open-below")]
    for c, txt in arch:
        ann.append(f'<text x="{lx:.0f}" y="{ly2:.0f}" font-size="10" fill="{c}" '
                   f'font-weight="700">■</text>')
        ann.append(f'<text x="{lx + 12:.0f}" y="{ly2:.0f}" font-size="9.5" '
                   f'fill="#52606d">{txt}</text>')
        lx += 12 + len(txt) * 6.4 + 14
        if lx > W - 90:
            lx, ly2 = PADDING + 130, ly2 + 15
    for mtype, (color, glyph) in sorted(legend_used.items()):
        ann.append(f'<text x="{lx:.0f}" y="{ly2:.0f}" font-size="10.5" '
                   f'fill="{color}" font-weight="bold">{glyph}</text>')
        ann.append(f'<text x="{lx + 13:.0f}" y="{ly2:.0f}" font-size="9.5" '
                   f'fill="#52606d">{_esc(mtype)}</text>')
        lx += 13 + len(mtype) * 6.4 + 12
        if lx > W - 90:
            lx, ly2 = PADDING + 130, ly2 + 15
    ann.append('</g>')
    out += ann

    # ---- stair key (verbose stair text lives here, not on the drawing) ----
    if stair_notes:
        ny0 = tx.h + LEGEND_H + 6
        key = ['<g id="stair_key">',
               f'<text x="{PADDING}" y="{ny0:.0f}" font-size="9.5" '
               f'fill="{STAIR_COLOR}" font-weight="700">Stairs</text>']
        for k, note in enumerate(stair_notes):
            key.append(
                f'<text x="{PADDING}" y="{ny0 + 13 * (k + 1):.0f}" font-size="9" '
                f'fill="#52606d">{_esc(note)}</text>')
        key.append('</g>')
        out += key

    out.append('</svg>')
    return "\n".join(out)


def stories_in(spec):
    """All stories that have rooms, markers, or stair service."""
    s = set(r.story for r in (getattr(spec, "rooms", []) or []))
    for m in getattr(spec, "markers", []) or []:
        s.add(_marker_story(spec, m))
    try:
        import stairwell
        for st in getattr(spec, "stairs", []) or []:
            for fs in stairwell.floors_served(spec, st):
                if fs < getattr(spec, "n_stories", 1):
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
