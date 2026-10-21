"""
axonometric.py  --  an exploded axonometric of a building, with architectural cutaways (offline, bpy-free)
==========================================================================================================
The plan (`floorplan.py`) shows one storey at a time, and nothing showed how a building's storeys stack: where a
stair lands, what an atrium opens onto, which rooms stand over which (the factory's roadmap 293; the walker's guide
`docs/reference/Floor_Plan_to_3D_Layout_and_Automap_Guide.md`, its section 6). This draws every storey as a slab
seen from above and to the south-west, each raised by a DISPLAY OFFSET over its true floor so the storeys come
apart, its walls cut at the plan-cut height so its rooms read from above, roofs and ceilings left off.

THE OFFSET IS THE DRAWING'S ALONE. A storey's group carries `data-elevation`, its true floor (`story *
story_height`, as the builder raises it), beside `data-offset`, what the drawing adds; elevations, collision and
navigation never see the second, and the spec is read, never written.

ONE LAYOUT, TWO DRAWINGS. Walls come from `floorplan.storey_walls` -- the exterior on `setbacks.storey_extent`, a
partition in the pieces `partition_bounds` builds it in, each opening remapped -- so the plan and this agree about
where a wall stands and where its doors are. Slab holes come from `stairwell.slab_openings` (authored holes and the
cut each stair makes) and the floor holes and hatches of `vertical_links`; stairs from `stairwell`.

Deterministic SVG strings: no Pillow, no Blender, no generative model.

Entry points:
    svg = render_axonometric(spec)
    path = write_axonometric(spec, outdir)      # <outdir>/<name>.axo.svg
"""
import math

import floorplan as FP

#: The camera stands south-west of the building, so the south and west faces of everything face it.
AZIMUTH_DEG = 45.0
#: True isometric: the three axes foreshortened alike.
ELEVATION_DEG = math.degrees(math.atan(1.0 / math.sqrt(2.0)))
#: THE PLAN CUT, a drawing convention: a plan is a section taken about 1.2 m over the floor, so a wall stands to
#: this height, its cut face dark, and every room behind it is seen. Above this an opening is wall.
PLAN_CUT_M = 1.2
#: The least clear air the drawing leaves between one storey's slab and the next, on top of what keeps them apart.
MIN_GAP_M = 2.0
PX_PER_M = 12
PADDING = 40
#: A door's threshold is drawn as a line this far into the floor, so a gap in a wall reads as a way through.
THRESHOLD_M = 0.12

SLAB_TOP = "#f7f8fa"
SLAB_SIDE = "#aeb9c4"
WALL_FACE = {"south": "#d9dfe5", "west": "#c4ccd5"}
FURN_TOP, FURN_FACE = "#eef1f4", {"south": "#d9dee4", "west": "#cbd2d9"}
GLASS = "#cfe3f3"
CONNECT = FP.STAIR_COLOR


class _Proj:
    """World metres (x east, y north, z up) to screen metres (right, UP), and a depth that grows away from the
    camera."""

    def __init__(self, azimuth=AZIMUTH_DEG, elevation=ELEVATION_DEG):
        a, e = math.radians(azimuth), math.radians(elevation)
        self.sa, self.ca = math.sin(a), math.cos(a)
        self.se, self.ce = math.sin(e), math.cos(e)

    def plan_depth(self, x, y):
        return x * self.sa + y * self.ca

    def xy(self, x, y, z):
        return (x * self.ca - y * self.sa, self.plan_depth(x, y) * self.se + z * self.ce)

    def depth(self, x, y, z):
        return self.plan_depth(x, y) * self.ce - z * self.se

    def faces_camera(self, nx, ny):
        """A vertical face whose outward normal is (nx, ny) is seen."""
        return nx * self.sa + ny * self.ca < -1e-9


def storey_offsets(spec, stories, proj, gap=None):
    """``({story: display offset in metres}, gap)``. The gap is DERIVED, not chosen: the rise that lifts one storey's
    slab clear of the next one's in the drawing, less the storey height that already separates them, plus
    `MIN_GAP_M` of clear air -- so no slab covers the one under it, at any footprint. Offsets count from the lowest
    storey drawn, so a basement stays where it is."""
    sh = FP._story_height(spec)
    hx, hy = spec.footprint_x / 2.0, spec.footprint_y / 2.0
    depths = [proj.plan_depth(x, y) for x in (-hx, hx) for y in (-hy, hy)]
    rise = (max(depths) - min(depths)) * proj.se / proj.ce
    g = max(MIN_GAP_M, rise - sh + MIN_GAP_M) if gap is None else float(gap)
    return {s: i * g for i, s in enumerate(sorted(stories))}, g


# ---------------------------------------------------------------------------
# solids
# ---------------------------------------------------------------------------

class _Box:
    """An axis-aligned solid in world metres, drawn as the faces the camera sees."""
    __slots__ = ("x0", "y0", "x1", "y1", "z0", "z1", "top", "faces", "data")

    def __init__(self, x0, y0, x1, y1, z0, z1, top, faces, data=""):
        self.x0, self.y0, self.x1, self.y1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
        self.z0, self.z1 = z0, z1
        self.top, self.faces, self.data = top, faces, data


def _behind(a, b):
    """True when ``a`` is drawn before ``b``: farther from a south-west camera. Two boxes that do not intersect are
    apart on some axis, and the first such axis decides; an intersecting pair falls back to its centres' depth."""
    eps = 1e-9
    if a.x0 >= b.x1 - eps:
        return True
    if b.x0 >= a.x1 - eps:
        return False
    if a.y0 >= b.y1 - eps:
        return True
    if b.y0 >= a.y1 - eps:
        return False
    if a.z1 <= b.z0 + eps:
        return True
    if b.z1 <= a.z0 + eps:
        return False
    return (a.x0 + a.x1 + a.y0 + a.y1) > (b.x0 + b.x1 + b.y0 + b.y1)


def _ordered(boxes, proj):
    """The boxes back to front: a topological order of `_behind` over every pair whose drawings overlap, ties broken
    by depth, so the order is the same on every run."""
    n = len(boxes)
    if n < 2:
        return list(boxes)
    rects = []
    for b in boxes:
        pts = [proj.xy(x, y, z) for x in (b.x0, b.x1) for y in (b.y0, b.y1) for z in (b.z0, b.z1)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        rects.append((min(xs), min(ys), max(xs), max(ys)))
    after = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        ri = rects[i]
        for j in range(i + 1, n):
            rj = rects[j]
            if ri[2] <= rj[0] or rj[2] <= ri[0] or ri[3] <= rj[1] or rj[3] <= ri[1]:
                continue
            if _behind(boxes[i], boxes[j]):
                after[i].append(j)
                indeg[j] += 1
            else:
                after[j].append(i)
                indeg[i] += 1
    key = [-proj.depth((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2, b.z0) for b in boxes]
    ready = sorted((k for k in range(n) if indeg[k] == 0), key=lambda k: (key[k], k))
    out, seen = [], [False] * n
    while len(out) < n:
        if not ready:                    # a cycle: release the farthest left
            k = min((k for k in range(n) if not seen[k]), key=lambda k: (key[k], k))
            indeg[k] = 0
            ready = [k]
        k = ready.pop(0)
        if seen[k]:
            continue
        seen[k] = True
        out.append(boxes[k])
        for m in after[k]:
            indeg[m] -= 1
            if indeg[m] == 0 and not seen[m]:
                ready.append(m)
        ready.sort(key=lambda k: (key[k], k))
    return out


# ---------------------------------------------------------------------------
# the drawing
# ---------------------------------------------------------------------------

class _Canvas:
    """Screen metres to SVG pixels, fitted to a bounding box of world points."""

    def __init__(self, proj, points):
        xy = [proj.xy(*p) for p in points]
        self.proj = proj
        self.x0 = min(p[0] for p in xy)
        self.y1 = max(p[1] for p in xy)
        self.w = (max(p[0] for p in xy) - self.x0) * PX_PER_M + 2 * PADDING
        self.h = (self.y1 - min(p[1] for p in xy)) * PX_PER_M + 2 * PADDING + 50 + 24

    def pt(self, x, y, z):
        sx, sy = self.proj.xy(x, y, z)
        return (PADDING + (sx - self.x0) * PX_PER_M, PADDING + 50 + (self.y1 - sy) * PX_PER_M)

    def poly(self, pts, fill, stroke="#7b8794", width=0.6, extra=""):
        s = " ".join("%.1f,%.1f" % self.pt(*p) for p in pts)
        return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s"%s/>' % (s, fill, stroke, width, extra)

    def line(self, a, b, stroke, width, dash=None, extra=""):
        (x1, y1), (x2, y2) = self.pt(*a), self.pt(*b)
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        return ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"%s%s/>'
                % (x1, y1, x2, y2, stroke, width, d, extra))


def _faces(cv, b):
    """The vertical faces of ``b`` the camera sees, as polygons."""
    p = cv.proj
    parts = []
    if p.faces_camera(0.0, -1.0):
        parts.append(cv.poly([(b.x0, b.y0, b.z0), (b.x1, b.y0, b.z0), (b.x1, b.y0, b.z1), (b.x0, b.y0, b.z1)],
                             b.faces["south"]))
    if p.faces_camera(0.0, 1.0):
        parts.append(cv.poly([(b.x0, b.y1, b.z0), (b.x1, b.y1, b.z0), (b.x1, b.y1, b.z1), (b.x0, b.y1, b.z1)],
                             b.faces["south"]))
    if p.faces_camera(-1.0, 0.0):
        parts.append(cv.poly([(b.x0, b.y0, b.z0), (b.x0, b.y1, b.z0), (b.x0, b.y1, b.z1), (b.x0, b.y0, b.z1)],
                             b.faces["west"]))
    if p.faces_camera(1.0, 0.0):
        parts.append(cv.poly([(b.x1, b.y0, b.z0), (b.x1, b.y1, b.z0), (b.x1, b.y1, b.z1), (b.x1, b.y0, b.z1)],
                             b.faces["west"]))
    return parts


def _box_svg(cv, b):
    """A box's seen faces, then its top. A wall's top is its CUT, drawn dark as a section's poche is."""
    top = cv.poly([(b.x0, b.y0, b.z1), (b.x1, b.y0, b.z1), (b.x1, b.y1, b.z1), (b.x0, b.y1, b.z1)], b.top)
    return '<g%s>%s</g>' % (b.data, "".join(_faces(cv, b) + [top]))


def _rect_pts(r, z):
    x0, y0, x1, y1 = r
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


def _slab_holes(spec):
    """``{story: [(rect, kind)]}``: every hole in the slab that is a storey's floor -- `stairwell.slab_openings`
    (authored holes and each stair's cut) and the floor holes and hatches of `vertical_links`."""
    out = {}
    try:
        import stairwell as _sw
        authored = {(round(h.x, 3), round(h.y, 3), int(h.story)) for h in getattr(spec, "slab_holes", []) or []}
        for story, rects in _sw.slab_openings(spec).items():
            for r in rects:
                c = (round((r[0] + r[2]) / 2, 3), round((r[1] + r[3]) / 2, 3), int(story))
                out.setdefault(int(story), []).append((r, "open to below" if c in authored else "stair"))
    except Exception:
        for h in getattr(spec, "slab_holes", []) or []:
            out.setdefault(int(h.story), []).append(
                ((h.x - h.size_x / 2, h.y - h.size_y / 2, h.x + h.size_x / 2, h.y + h.size_y / 2), "open to below"))
    for vl in getattr(spec, "vertical_links", []) or []:
        if getattr(vl, "kind", "") in ("floor_hole", "hatch") and vl.story is not None \
                and vl.x is not None and vl.size_x:
            out.setdefault(int(vl.story), []).append(
                ((vl.x - vl.size_x / 2, vl.y - vl.size_y / 2, vl.x + vl.size_x / 2, vl.y + vl.size_y / 2),
                 vl.kind.replace("_", " ")))
    return out


def _storey_title(s):
    return "Basement" if s < 0 else ("Ground floor" if s == 0 else "Floor %d" % s)


def render_axonometric(spec, azimuth=AZIMUTH_DEG, elevation=ELEVATION_DEG, cut=PLAN_CUT_M, gap=None):
    """One SVG string: every storey of ``spec``, exploded, cut and seen from the south-west."""
    import stairwell as _sw
    proj = _Proj(azimuth, elevation)
    sh = FP._story_height(spec)
    stories = FP.stories_in(spec)
    offsets, g = storey_offsets(spec, stories, proj, gap)
    drawn = {s: s * sh + offsets[s] for s in stories}
    floor_t = getattr(spec, "floor_thick", 0.3) or 0.3
    holes = _slab_holes(spec)
    try:
        import setbacks as _sb
        extent = {s: _sb.storey_extent(spec, s) for s in stories}
    except Exception:
        hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
        extent = {s: (-hx, -hy, hx, hy) for s in stories}

    pts = []
    for s in stories:
        x0, y0, x1, y1 = extent[s]
        pts += [(x, y, z) for x in (x0 - 1, x1 + 1) for y in (y0 - 1, y1 + 1)
                for z in (drawn[s] - floor_t, drawn[s] + cut)]
    for m in getattr(spec, "markers", []) or []:
        s = FP._marker_story(spec, m)
        if s in drawn:
            pts.append((getattr(m, "x", 0.0), getattr(m, "y", 0.0), drawn[s]))
    cv = _Canvas(proj, pts)
    W, H = cv.w, cv.h

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" viewBox="0 0 %.0f %.0f" '
           'font-family="Inter,Segoe UI,sans-serif" data-view="exploded-axonometric" data-azimuth="%g" '
           'data-elevation-angle="%.3f" data-cut="%g" data-gap="%.3f">' % (W, H, W, H, azimuth, elevation, cut, g),
           '<rect width="%.0f" height="%.0f" fill="#ffffff"/>' % (W, H)]
    defs = ["<defs>"]
    body = []
    labels_by_storey = {}
    for s in stories:
        z = drawn[s]
        x0, y0, x1, y1 = extent[s]
        tag = FP._story_tag(s)
        grp = ['<g id="storey_%s" data-storey="%d" data-elevation="%.3f" data-offset="%.3f">'
               % (tag, s, s * sh, offsets[s])]
        # ---- the slab: its seen edges, then its top through a mask that keeps every hole open ----
        slab = _Box(x0, y0, x1, y1, z - floor_t, z, SLAB_TOP, {"south": SLAB_SIDE, "west": SLAB_SIDE})
        grp.append('<g data-slab="%d">%s</g>' % (s, "".join(_faces(cv, slab))))
        mask_id = "voids_%s" % tag
        defs.append('<mask id="%s" maskUnits="userSpaceOnUse" x="0" y="0" width="%.0f" height="%.0f">'
                    '<rect width="%.0f" height="%.0f" fill="#ffffff"/>' % (mask_id, W, H, W, H))
        for r, kind in holes.get(s, []):
            defs.append(cv.poly(_rect_pts(r, z), "#000000", stroke="#000000", width=0.5,
                                extra=' data-void="%s"' % FP._esc(kind)))
        defs.append("</mask>")
        top = ['<g mask="url(#%s)">' % mask_id,
               cv.poly(_rect_pts((x0, y0, x1, y1), z), SLAB_TOP, stroke="#7b8794", width=0.8)]
        for r in getattr(spec, "rooms", []) or []:
            if r.story != s:
                continue
            role = getattr(r, "role", "") or ""
            fill = "#fdf0dd" if getattr(r, "objective", False) else {
                "public_entry": "#fbf6e7", "loot_room": "#f4eee0", "fortifiable": "#f2f3e4",
                "connector": "#faf8f2"}.get(role, "#f1f4f7")
            top.append(cv.poly(_rect_pts(r.bounds, z), fill, stroke="#d0d7de", width=0.6,
                               extra=' data-room="%s"' % FP._esc(r.id)))
            rx0, ry0, rx1, ry1 = r.bounds
            labels_by_storey.setdefault(s, []).append(((rx0 + rx1) / 2, (ry0 + ry1) / 2, r.id))
        top.append("</g>")
        grp += top
        # what opens the floor: the slab's thickness seen on a hole's far edges, then its outline
        for r, kind in holes.get(s, []):
            hx0, hy0, hx1, hy1 = r
            if proj.faces_camera(0.0, -1.0):       # the hole's north edge, its face turned south
                grp.append(cv.poly([(hx0, hy1, z - floor_t), (hx1, hy1, z - floor_t), (hx1, hy1, z), (hx0, hy1, z)],
                                   SLAB_SIDE, width=0.5))
            if proj.faces_camera(-1.0, 0.0):       # its east edge, turned west
                grp.append(cv.poly([(hx1, hy0, z - floor_t), (hx1, hy1, z - floor_t), (hx1, hy1, z), (hx1, hy0, z)],
                                   SLAB_SIDE, width=0.5))
            color = FP.VOID_COLOR if kind != "stair" else FP.STAIR_COLOR
            grp.append(cv.poly(_rect_pts(r, z), "none", stroke=color, width=1.0,
                               extra=' stroke-dasharray="3 2" data-void="%s"' % FP._esc(kind)))
        # stairs and ladders, outlined on every storey they serve
        for i, st in enumerate(getattr(spec, "stairs", []) or []):
            if s in _sw.floors_served(spec, st):
                grp.append(cv.poly(_rect_pts(_sw.footprint_rect(st), z + 0.01), "none", stroke=FP.STAIR_COLOR,
                                   width=1.0, extra=' stroke-dasharray="4 3" data-stair="%s"'
                                   % FP._esc(_sw.stair_ident(st, i))))
        # ---- the solids, back to front: walls to the cut, glass where a window's sill is under it, furniture ----
        boxes, thresholds = [], []
        bound = {"x": spec.footprint_x / 2, "y": spec.footprint_y / 2}
        for wall in FP.storey_walls(spec, s):
            t = wall["t"]
            ops = []
            low = []               # openings whose sill is under the cut: a window's sill wall and its glass
            for op in wall["openings"]:
                try:
                    res = op.resolved()
                except Exception:
                    res = {"sill": getattr(op, "sill", 0.0) or 0.0}
                sill = float(res.get("sill") or 0.0)
                if sill >= cut:
                    continue       # above the plan cut: here it is wall
                ops.append(op)
                if sill > 1e-6:
                    low.append(op)
            fixed, lo, hi, segs, gaps = FP.wall_split(wall["p0"], wall["p1"], wall["axis"], ops,
                                                      bound[wall["axis"]])
            name = FP._esc(wall["name"])

            def rect(a, b, axis=wall["axis"], fixed=fixed):
                return ((a, fixed - t / 2, b, fixed + t / 2) if axis == "x" else (fixed - t / 2, a, fixed + t / 2, b))
            for a, b in segs:
                r = rect(a, b)
                boxes.append(_Box(r[0], r[1], r[2], r[3], z, z + cut, FP.INK, WALL_FACE,
                                  ' data-wall="%s"' % name))
            for glo, ghi, op, c, w in gaps:
                if c < lo or c > hi:
                    continue
                glo, ghi = max(glo, lo), min(ghi, hi)
                kind = getattr(op, "kind", "door")
                otag = FP._esc(getattr(op, "tag", None) or kind)
                at = (c, fixed) if wall["axis"] == "x" else (fixed, c)
                if op in low:
                    sill = float(op.resolved().get("sill") or 0.0)
                    r = rect(glo, ghi)
                    boxes.append(_Box(r[0], r[1], r[2], r[3], z, z + sill, FP.INK, WALL_FACE,
                                      ' data-wall="%s"' % name))
                    boxes.append(_Box(r[0], r[1], r[2], r[3], z + sill, z + cut, GLASS,
                                      {"south": GLASS, "west": GLASS},
                                      ' data-opening="%s" data-kind="%s" data-at="%.3f,%.3f" fill-opacity="0.7"'
                                      % (otag, kind, at[0], at[1])))
                else:
                    if wall["axis"] == "x":
                        a3, b3 = (glo, fixed, z + 0.005), (ghi, fixed, z + 0.005)
                    else:
                        a3, b3 = (fixed, glo, z + 0.005), (fixed, ghi, z + 0.005)
                    color = FP.OPEN_COLOR.get("door" if kind in ("vault", "teller", "safe_deposit") else kind,
                                              "#3e4c59")
                    thresholds.append(cv.line(a3, b3, color, 2.2,
                                              extra=' data-opening="%s" data-kind="%s" data-at="%.3f,%.3f"'
                                              % (otag, kind, at[0], at[1])))
        for v in getattr(spec, "volumes", []) or []:
            if not getattr(v, "visual", True):
                continue
            vz = getattr(v, "z", 0.0) or 0.0
            base = vz - getattr(v, "size_z", 0.0) / 2
            if not (s * sh - 0.6 <= base < (s + 1) * sh - 0.6):
                continue
            z0 = z + max(0.0, base - s * sh)
            z1 = min(z0 + float(getattr(v, "size_z", 0.0) or 0.0), z + cut)
            if z1 <= z0 + 1e-6:
                continue
            boxes.append(_Box(v.x - v.size_x / 2, v.y - v.size_y / 2, v.x + v.size_x / 2, v.y + v.size_y / 2,
                              z0, z1, FURN_TOP, FURN_FACE, ' data-object="%s"' % FP._esc(v.name)))
        grp += thresholds
        grp += [_box_svg(cv, b) for b in _ordered(boxes, proj)]
        # ---- markers on their storey, riding its offset ----
        for m in getattr(spec, "markers", []) or []:
            if FP._marker_story(spec, m) != s:
                continue
            color, glyph = FP.MARKER_STYLE.get(m.type, FP.DEFAULT_MARKER)
            mz = getattr(m, "z", 0.0) or 0.0
            px, py = cv.pt(getattr(m, "x", 0.0), getattr(m, "y", 0.0), z + max(0.0, mz - s * sh))
            grp.append('<text x="%.1f" y="%.1f" font-size="13" fill="%s" text-anchor="middle" font-weight="bold" '
                       'data-marker="%s" data-at="%.3f,%.3f,%.3f">%s</text>'
                       % (px, py + 4, color, FP._esc(m.type), getattr(m, "x", 0.0), getattr(m, "y", 0.0), mz, glyph))
        # ---- labels: the rooms', then the storey's own at its west corner ----
        for lx, ly, rid in labels_by_storey.get(s, []):
            px, py = cv.pt(lx, ly, z + cut + 0.05)
            common = 'x="%.1f" y="%.1f" font-size="9" font-weight="700" text-anchor="middle"' % (px, py)
            grp.append('<text %s fill="none" stroke="#ffffff" stroke-width="3" stroke-linejoin="round">%s</text>'
                       % (common, FP._esc(rid)))
            grp.append('<text %s fill="#2b3742">%s</text>' % (common, FP._esc(rid)))
        px, py = cv.pt(x0, y0, z - floor_t)
        grp.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" fill="#1f2933" text-anchor="end">'
                   '%s</text>' % (px - 8, py + 4, _storey_title(s)))
        grp.append('<text x="%.1f" y="%.1f" font-size="9" fill="#7b8794" text-anchor="end">floor at %.2f m</text>'
                   % (px - 8, py + 16, s * sh))
        grp.append("</g>")
        body += grp

    # ---- what joins the storeys, over everything: stairs, ladders, the holes that open onto the floor below ----
    conn = ['<g id="connections">']
    for i, st in enumerate(getattr(spec, "stairs", []) or []):
        served = [s for s in _sw.floors_served(spec, st) if s in drawn]
        sid = FP._esc(_sw.stair_ident(st, i))
        eps = _sw.stair_endpoints(st)
        lows = [e for e in eps if e["end"] == "lower"]
        ups = [e for e in eps if e["end"] == "upper"]
        fr = _sw.footprint_rect(st)
        for a, b in zip(served, served[1:]):
            grp = ['<g data-stair="%s" data-from="%d" data-to="%d">' % (sid, a, b)]
            for cx, cy in ((fr[0], fr[1]), (fr[2], fr[1]), (fr[0], fr[3]), (fr[2], fr[3])):
                grp.append(cv.line((cx, cy, drawn[a]), (cx, cy, drawn[b]), CONNECT, 0.8, dash="3 3"))
            if lows and ups:
                (lx, ly), (ux, uy) = lows[0]["point"], ups[0]["point"]
                grp.append(cv.line((lx, ly, drawn[a]), (ux, uy, drawn[b]), CONNECT, 2.0))
                (x2, y2), (xa, ya) = cv.pt(ux, uy, drawn[b]), cv.pt(lx, ly, drawn[a])
                ang = math.atan2(y2 - ya, x2 - xa)
                for da in (2.6, -2.6):
                    grp.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>'
                               % (x2, y2, x2 + 8 * math.cos(ang + da), y2 + 8 * math.sin(ang + da), CONNECT))
            else:
                grp.append(cv.line((st.x, st.y, drawn[a]), (st.x, st.y, drawn[b]), CONNECT, 2.0))
            grp.append("</g>")
            conn += grp
    for ld in getattr(spec, "ladders", []) or []:
        a, b = sorted((ld.from_story, ld.to_story))
        if a in drawn and b in drawn:
            conn.append(cv.line((ld.x, ld.y, drawn[a]), (ld.x, ld.y, drawn[b]), FP.LADDER_COLOR, 1.8,
                                extra=' data-ladder="%s"' % FP._esc(getattr(ld, "id", None) or "")))
    for s, rects in sorted(holes.items()):
        if s not in drawn or (s - 1) not in drawn:
            continue
        for r, kind in rects:
            if kind == "stair":
                continue
            for cx, cy in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])):
                conn.append(cv.line((cx, cy, drawn[s]), (cx, cy, drawn[s - 1]), FP.VOID_COLOR, 0.8, dash="2 3"))
    conn.append("</g>")

    defs.append("</defs>")
    out += defs + body + conn
    out.append('<text x="%d" y="24" font-size="15" font-weight="700" fill="#1f2933">%s — exploded axonometric'
               '</text>' % (PADDING, FP._esc(spec.name)))
    out.append('<text x="%d" y="38" font-size="9.5" fill="#7b8794">each storey drawn %.1f m higher than the one '
               'below over its %.1f m floor to floor; the elevations are not moved</text>' % (PADDING, g, sh))
    out.append('<text x="%d" y="50" font-size="9.5" fill="#7b8794">walls cut at %.1f m · seen from the south-west · '
               'deterministic render, no generative model</text>' % (PADDING, cut))
    # the legend, along the foot
    lx, ly = PADDING, H - 14
    leg = ['<g id="legend">']
    for color, txt in ((FP.INK, "wall, cut"), ("#3e4c59", "door"), ("#2f80c8", "window"), (FP.STAIR_COLOR, "stair"),
                       (FP.LADDER_COLOR, "ladder"), (FP.VOID_COLOR, "open to below"), ("#c3ccd6", "furniture")):
        leg.append('<text x="%.0f" y="%.0f" font-size="10" fill="%s" font-weight="700">■</text>' % (lx, ly, color))
        leg.append('<text x="%.0f" y="%.0f" font-size="9.5" fill="#52606d">%s</text>' % (lx + 12, ly, txt))
        lx += 12 + len(txt) * 6.0 + 14
    leg.append("</g>")
    out += leg
    out.append("</svg>")
    return "\n".join(out)


def write_axonometric(spec, outdir):
    """Write ``<outdir>/<name>.axo.svg``; returns its path."""
    import os
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "%s.axo.svg" % spec.name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_axonometric(spec))
    return path


if __name__ == "__main__":
    import sys
    import spec_loader
    if len(sys.argv) < 2:
        print("usage: python axonometric.py <spec.json> [outdir]")
        raise SystemExit(2)
    print("wrote", write_axonometric(spec_loader.load_spec(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "."))
