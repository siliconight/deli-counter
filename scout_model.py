"""
scout_model.py  --  a building's scout model: what a player turns all the way round to scout it (offline, bpy-free)
====================================================================================================================
The walker, of the scout view (0.258.0): "its ok for now, but i want to make it look more polished and artistic so
it could ship to players....They can scout out the buildings and rotate the schemas in a 360 degree way" (the
factory's roadmap 295). This builds the scout view's signals as a model: each storey's slab with its holes cut
through, its walls standing to the plan cut with a dark cap on the cut, a window as glass from its sill to the cut, a
door as a strip across the floor -- the entry colour where it lets you in from outside -- every stair as the treads
the builder builds (`stairwell.ascent_surfaces`), every ladder as its rails and rungs. No furniture, rooms or
markers, as the scout view.

THE SCORE AND WHAT IS WORTH KNOWING (0.260.0). The walker: "buildings should show the 'score' location and key props
of interest". Each storey carries a second mesh, ``points``, apart from its structure so a viewer can light or pulse it
on its own: a beacon -- plinth, mast, a block on top -- at every `objective` marker (the score), and at every `loot`
marker, `camera_socket` marker, safe and ATM a lit block where it stands (`POINTS_OF_INTEREST`). The scene's
``extras.points`` lists every one -- kind, label, storey, and where it stands in the model's frame -- so a viewer can
name them. Spawns are not drawn: they are the gameplay layer's, and provisional.

ONE LAYOUT. Walls come from `floorplan.storey_walls` and `wall_split`, holes from `axonometric._slab_holes`, stairs
from `stairwell`, a storey's outline from `setbacks.storey_extent` -- the readers the plan, the axonometric and the
scout view use -- so the model and the drawings cannot disagree about where anything stands.

WHAT IT COSTS A CLIENT. One mesh a storey, so a viewer can lift the storeys apart, and one material: every colour is
in the vertex data (`COLOR_0`), never a material of its own -- the factory's draw-call rule -- so a building is one
draw a storey. deli_a03, three storeys, is 2,936 triangles. The style is a palette (`PALETTES`), the walker's to pick;
`DEFAULT_PALETTE` until then.

Deterministic GLB bytes: no Blender, no generative model. A storey's node stands at its true elevation
(`extras.elevation`); lifting storeys apart is the viewer's, never the model's.

Entry points:
    data = build_glb(spec, palette=DEFAULT_PALETTE)          # bytes
    stats = model_stats(spec)                                # {storey: triangles}
"""
import json
import struct

import axonometric as AX
import floorplan as FP
import stairwell as SW

#: Walls stand to the plan cut, as the drawings'; their top is capped dark, as a section's cut is.
CUT = AX.PLAN_CUT_M
CAP = 0.04
#: A door's strip across the floor, thick enough to read from any side.
THRESH = 0.08
#: A hole's rim, so an opening in a floor reads from below as well as above.
RIM = 0.06

#: Colours as they show on screen (sRGB 0-1). The walker's direction (2026-10-22): "roughly be in the style of a
#: 1990s palm pilot...but with a little more backlight and color" -- `palm`, the default since 0.260.0; the three
#: before it were put to them first. Every role a
#: player reads by colour has its own: the first draft gave a hole's rim the entry's red, so an opening in a floor
#: read as a way in (`test_every_role_a_player_reads_has_its_own_colour`).
ROLES_READ = ("glass", "door", "entry", "tread", "ladder", "hole_rim", "score", "poi")
PALETTES = {
    # a 1990s handheld's LCD, backlit: grey-green floors, ink walls, a few lit accents for what a player hunts for
    "palm": {"slab": (0.47, 0.58, 0.45), "slab_side": (0.30, 0.38, 0.29), "wall": (0.16, 0.21, 0.16),
             "cap": (0.06, 0.09, 0.06), "glass": (0.45, 0.85, 0.95), "door": (0.30, 0.40, 0.29),
             "entry": (1.00, 0.55, 0.20), "tread": (1.00, 0.85, 0.35), "ladder": (0.55, 1.00, 0.75),
             "hole_rim": (1.00, 0.40, 0.70), "score": (1.00, 0.22, 0.22), "poi": (0.80, 0.55, 1.00),
             "background": (0.56, 0.68, 0.53)},
    "blueprint": {"slab": (0.10, 0.20, 0.38), "slab_side": (0.07, 0.14, 0.28), "wall": (0.62, 0.82, 0.95),
                  "cap": (0.95, 0.98, 1.00), "glass": (0.35, 0.95, 0.95), "door": (0.85, 0.92, 1.00),
                  "entry": (1.00, 0.45, 0.25), "tread": (1.00, 0.75, 0.25), "ladder": (0.40, 1.00, 0.70),
                  "hole_rim": (1.00, 0.30, 0.65), "score": (1.00, 0.20, 0.30), "poi": (0.75, 0.55, 1.00),
                  "background": (0.03, 0.06, 0.12)},
    "model": {"slab": (0.70, 0.68, 0.64), "slab_side": (0.50, 0.48, 0.45), "wall": (0.95, 0.94, 0.91),
              "cap": (0.16, 0.17, 0.19), "glass": (0.55, 0.74, 0.86), "door": (0.30, 0.33, 0.37),
              "entry": (0.80, 0.22, 0.18), "tread": (0.78, 0.60, 0.30), "ladder": (0.15, 0.55, 0.55),
              "hole_rim": (0.55, 0.25, 0.60), "score": (0.85, 0.10, 0.45), "poi": (0.20, 0.45, 0.80),
              "background": (0.13, 0.14, 0.16)},
    "dossier": {"slab": (0.90, 0.87, 0.78), "slab_side": (0.70, 0.66, 0.56), "wall": (0.30, 0.29, 0.27),
                "cap": (0.12, 0.11, 0.10), "glass": (0.60, 0.66, 0.66), "door": (0.45, 0.42, 0.38),
                "entry": (0.75, 0.10, 0.10), "tread": (0.55, 0.50, 0.42), "ladder": (0.25, 0.45, 0.30),
                "hole_rim": (0.20, 0.30, 0.55), "score": (0.95, 0.35, 0.05), "poi": (0.45, 0.20, 0.55),
                "background": (0.82, 0.79, 0.70)},
}
DEFAULT_PALETTE = "palm"


def _linear(c):
    """sRGB to linear: glTF's COLOR_0 is linear, and a palette is written as it shows."""
    return (c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


class _Mesh:
    """Flat-shaded boxes as one triangle list, in glTF's frame: spec x east, y north, z up -> x, y up, z south."""

    def __init__(self):
        self.pos, self.nrm, self.col, self.idx = [], [], [], []

    def quad(self, a, b, c, d, n, col):
        base = len(self.pos)
        rgba = tuple(int(round(_linear(v) * 255)) for v in col) + (255,)
        for p in (a, b, c, d):
            self.pos.append((p[0], p[2], -p[1]))
            self.nrm.append((float(n[0]), float(n[2]), float(-n[1])))
            self.col.append(rgba)
        self.idx += [base, base + 1, base + 2, base, base + 2, base + 3]

    def box(self, x0, y0, z0, x1, y1, z1, col, side=None, sides="snwe"):
        side = side or col
        q = self.quad
        q((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1), col)
        q((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0), (0, 0, -1), side)
        if "s" in sides:
            q((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0), side)
        if "n" in sides:
            q((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (0, 1, 0), side)
        if "w" in sides:
            q((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (-1, 0, 0), side)
        if "e" in sides:
            q((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0), side)


def _cells(rect, holes):
    """``rect`` less every hole: a grid on every hole edge, each cell kept unless a hole covers its centre."""
    x0, y0, x1, y1 = rect
    xs = sorted({x0, x1} | {min(max(h[i], x0), x1) for h in holes for i in (0, 2)})
    ys = sorted({y0, y1} | {min(max(h[i], y0), y1) for h in holes for i in (1, 3)})
    out = []
    for a, b in zip(xs, xs[1:]):
        for c, d in zip(ys, ys[1:]):
            if b - a < 1e-6 or d - c < 1e-6:
                continue
            mx, my = (a + b) / 2, (c + d) / 2
            if not any(h[0] <= mx <= h[2] and h[1] <= my <= h[3] for h in holes):
                out.append((a, c, b, d))
    return out


def _open_sides(r, cells):
    """The sides of cell ``r`` no other cell of its slab stands against: the slab's edge and its holes' edges. Cells
    of one grid meet whole edge to whole edge, so a neighbour is a cell sharing the edge exactly."""
    out = ""
    if not any(abs(c[3] - r[1]) < 1e-6 and abs(c[0] - r[0]) < 1e-6 and abs(c[2] - r[2]) < 1e-6 for c in cells):
        out += "s"
    if not any(abs(c[1] - r[3]) < 1e-6 and abs(c[0] - r[0]) < 1e-6 and abs(c[2] - r[2]) < 1e-6 for c in cells):
        out += "n"
    if not any(abs(c[2] - r[0]) < 1e-6 and abs(c[1] - r[1]) < 1e-6 and abs(c[3] - r[3]) < 1e-6 for c in cells):
        out += "w"
    if not any(abs(c[0] - r[2]) < 1e-6 and abs(c[1] - r[1]) < 1e-6 and abs(c[3] - r[3]) < 1e-6 for c in cells):
        out += "e"
    return out


def _storeys(spec, pal):
    """{storey: _Mesh}, each storey's floor at its local 0."""
    sh = FP._story_height(spec)
    t_floor = getattr(spec, "floor_thick", 0.3) or 0.3
    holes = AX._slab_holes(spec)
    stories = FP.stories_in(spec)
    try:
        import setbacks
        extent = {s: setbacks.storey_extent(spec, s) for s in stories}
    except Exception:
        hx, hy = spec.footprint_x / 2, spec.footprint_y / 2
        extent = {s: (-hx, -hy, hx, hy) for s in stories}
    bound = {"x": spec.footprint_x / 2, "y": spec.footprint_y / 2}
    out = {}
    for s in stories:
        m = _Mesh()
        cells = _cells(extent[s], [r for r, _k in holes.get(s, [])])
        for r in cells:
            m.box(r[0], r[1], -t_floor, r[2], r[3], 0.0, pal["slab"], side=pal["slab_side"],
                  sides=_open_sides(r, cells))
        for r, kind in holes.get(s, []):
            col = pal["tread"] if kind == "stair" else pal["hole_rim"]
            for rr in ((r[0], r[1] - RIM, r[2], r[1]), (r[0], r[3], r[2], r[3] + RIM),
                       (r[0] - RIM, r[1], r[0], r[3]), (r[2], r[1], r[2] + RIM, r[3])):
                m.box(rr[0], rr[1], 0.0, rr[2], rr[3], 0.02, col)
        for wall in FP.storey_walls(spec, s):
            t = wall["t"]
            ops, sills = [], {}
            for op in wall["openings"]:
                try:
                    res = op.resolved()
                except Exception:
                    res = {"sill": getattr(op, "sill", 0.0) or 0.0}
                sill = float(res.get("sill") or 0.0)
                if sill < CUT:           # above the cut an opening is wall, as in the drawings
                    ops.append(op)
                    sills[id(op)] = sill
            fixed, lo, hi, segs, gaps = FP.wall_split(wall["p0"], wall["p1"], wall["axis"], ops,
                                                      bound[wall["axis"]])
            exterior = str(wall["name"]).startswith("ext")

            def rect(a, b, axis=wall["axis"], fixed=fixed, t=t):
                return (a, fixed - t / 2, b, fixed + t / 2) if axis == "x" else (fixed - t / 2, a, fixed + t / 2, b)
            for a, b in segs:
                r = rect(a, b)
                m.box(r[0], r[1], 0.0, r[2], r[3], CUT - CAP, pal["wall"])
                m.box(r[0], r[1], CUT - CAP, r[2], r[3], CUT, pal["cap"])
            for glo, ghi, op, c, w in gaps:
                if c < lo or c > hi:
                    continue
                r = rect(max(glo, lo), min(ghi, hi))
                sill = sills.get(id(op), 0.0)
                if sill > 1e-6:
                    m.box(r[0], r[1], 0.0, r[2], r[3], sill, pal["wall"])
                    m.box(r[0], r[1], sill, r[2], r[3], CUT, pal["glass"])
                else:
                    m.box(r[0], r[1], 0.0, r[2], r[3], THRESH, pal["entry"] if exterior else pal["door"])
        for st in getattr(spec, "stairs", []) or []:
            surfaces = [u for u in SW.ascent_surfaces(spec, st) if u[0] == s]
            if not surfaces:
                continue
            riser = sh / SW._step_count(st, sh)
            solid = SW.flight_solid_under(spec, st, s)
            for (_s, tx, ty, ztop, ssx, ssy) in surfaces:
                z1 = ztop - s * sh
                z0 = 0.0 if solid else max(0.0, z1 - riser)
                m.box(tx - ssx / 2, ty - ssy / 2, z0, tx + ssx / 2, ty + ssy / 2, z1, pal["tread"])
        for ld in getattr(spec, "ladders", []) or []:
            a, b = sorted((ld.from_story, ld.to_story))
            if a <= s < b:               # its rails and rungs from this floor to the next
                for dx in (-0.22, 0.22):
                    m.box(ld.x + dx - 0.03, ld.y - 0.03, 0.0, ld.x + dx + 0.03, ld.y + 0.03, sh, pal["ladder"])
                k = 0.3
                while k < sh - 1e-6:
                    m.box(ld.x - 0.22, ld.y - 0.02, k, ld.x + 0.22, ld.y + 0.02, k + 0.03, pal["ladder"])
                    k += 0.3
        out[s] = m
    return out


#: What a scout is shown besides the structure: the score (an `objective` marker) and the props worth knowing
#: about. Markers by type, volumes by the kind their name begins with. Label is what a viewer names it.
POINTS_OF_INTEREST = {
    ("marker", "objective"): ("score", "SCORE"),
    ("marker", "loot"): ("poi", "LOOT"),
    ("marker", "camera_socket"): ("poi", "CAMERA"),
    ("volume", "safe"): ("poi", "SAFE"),
    ("volume", "atm"): ("poi", "ATM"),
}
#: A score beacon: plinth, mast and a block on top, standing over the floor so it reads from any side.
BEACON_H = 3.0


def points(spec):
    """Every point of interest, in spec metres: [{kind, label, storey, x, y, z (over its storey's floor), size}],
    markers first then volumes, each in spec order."""
    sh = FP._story_height(spec)
    stories = set(FP.stories_in(spec))
    out = []
    for m in getattr(spec, "markers", []) or []:
        hit = POINTS_OF_INTEREST.get(("marker", m.type))
        s = FP._marker_story(spec, m)
        if hit and s in stories:
            out.append({"kind": hit[0], "label": hit[1], "storey": s, "x": m.x, "y": m.y,
                        "z": max(0.0, (getattr(m, "z", 0.0) or 0.0) - s * sh), "size": None})
    for v in getattr(spec, "volumes", []) or []:
        hit = POINTS_OF_INTEREST.get(("volume", str(v.name).split("_")[0]))
        if not hit or not getattr(v, "visual", True):
            continue
        base = (getattr(v, "z", 0.0) or 0.0) - v.size_z / 2
        s = next((k for k in sorted(stories) if k * sh - 0.6 <= base < (k + 1) * sh - 0.6), None)
        if s is None:
            continue
        out.append({"kind": hit[0], "label": hit[1], "storey": s, "x": v.x, "y": v.y,
                    "z": max(0.0, base - s * sh), "size": (v.size_x, v.size_y, v.size_z)})
    return out


def _point_meshes(spec, pal):
    """{storey: _Mesh} of the points of interest on it."""
    out = {}
    for p in points(spec):
        m = out.setdefault(p["storey"], _Mesh())
        x, y, z = p["x"], p["y"], p["z"]
        col = pal[p["kind"]]
        if p["kind"] == "score":
            m.box(x - 0.45, y - 0.45, z, x + 0.45, y + 0.45, z + 0.10, col)
            m.box(x - 0.10, y - 0.10, z + 0.10, x + 0.10, y + 0.10, z + BEACON_H - 0.7, col)
            m.box(x - 0.40, y - 0.40, z + BEACON_H - 0.7, x + 0.40, y + 0.40, z + BEACON_H, col)
        elif p["size"]:
            sx, sy, sz = p["size"]
            m.box(x - sx / 2, y - sy / 2, z, x + sx / 2, y + sy / 2, z + min(sz, 1.6), col)
        else:
            m.box(x - 0.2, y - 0.2, z, x + 0.2, y + 0.2, z + 0.4, col)
    return out


def model_stats(spec, palette=DEFAULT_PALETTE):
    """{storey: triangles}."""
    return {s: len(m.idx) // 3 for s, m in _storeys(spec, PALETTES[palette]).items()}


def build_glb(spec, palette=DEFAULT_PALETTE):
    """The scout model as GLB bytes: a node and a mesh a storey (``storey_<n>``, at its true elevation, with
    ``extras.storey`` and ``extras.elevation``), and under it, where the storey has any, its points of interest
    (``storey_<n>_points``, a mesh of their own); one material, colour as normalised bytes in ``COLOR_0``; the
    scene's ``extras.points`` naming every point, its ``at`` in the model's frame (x, y up, z south)."""
    pal = PALETTES[palette]
    sh = FP._story_height(spec)
    bin_ = bytearray()
    views, accs, meshes, nodes = [], [], [], []

    def add(data, target, comp, typ, count, extra=None):
        while len(bin_) % 4:
            bin_.append(0)
        views.append({"buffer": 0, "byteOffset": len(bin_), "byteLength": len(data), "target": target})
        bin_.extend(data)
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": count, "type": typ}
        a.update(extra or {})
        accs.append(a)
        return len(accs) - 1

    def mesh(name, m):
        p = add(b"".join(struct.pack("<3f", *v) for v in m.pos), 34962, 5126, "VEC3", len(m.pos),
                {"min": [min(v[i] for v in m.pos) for i in range(3)],
                 "max": [max(v[i] for v in m.pos) for i in range(3)]})
        n = add(b"".join(struct.pack("<3f", *v) for v in m.nrm), 34962, 5126, "VEC3", len(m.nrm))
        c = add(b"".join(struct.pack("<4B", *v) for v in m.col), 34962, 5121, "VEC4", len(m.col),
                {"normalized": True})
        i = add(b"".join(struct.pack("<I", v) for v in m.idx), 34963, 5125, "SCALAR", len(m.idx))
        meshes.append({"name": name, "primitives": [
            {"attributes": {"POSITION": p, "NORMAL": n, "COLOR_0": c}, "indices": i, "material": 0}]})
        return len(meshes) - 1

    pts = _point_meshes(spec, pal)
    for s, m in sorted(_storeys(spec, pal).items()):
        if not m.idx:
            continue
        if s in pts:
            nodes.append({"name": "storey_%d_points" % s, "mesh": mesh("storey_%d_points" % s, pts[s]),
                          "extras": {"storey": s, "points": True}})
        node = {"name": "storey_%d" % s, "mesh": mesh("storey_%d" % s, m),
                "translation": [0.0, round(s * sh, 6), 0.0],
                "extras": {"storey": s, "elevation": round(s * sh, 6)}}
        if s in pts:
            node["children"] = [len(nodes) - 1]
        nodes.append(node)
    gltf = {"asset": {"version": "2.0", "generator": "deli_counter scout_model"},
            "scene": 0, "scenes": [{"name": spec.name,
                                    "nodes": [k for k, n in enumerate(nodes) if not n["extras"].get("points")],
                                    "extras": {"palette": palette,
                                               "background": list(pal["background"]),
                                               "points": [{"kind": p["kind"], "label": p["label"],
                                                           "storey": p["storey"],
                                                           "at": [round(p["x"], 3), round(p["storey"] * sh + p["z"], 3),
                                                                  round(-p["y"], 3)]}
                                                          for p in points(spec)]}}],
            "nodes": nodes, "meshes": meshes,
            "materials": [{"name": "scout", "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.85}}],
            "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": len(bin_)}]}
    js = json.dumps(gltf, separators=(",", ":"), sort_keys=True).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    while len(bin_) % 4:
        bin_.append(0)
    head = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
    return (head + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(bin_), 0x004E4942) + bytes(bin_))


if __name__ == "__main__":
    import sys
    import spec_loader
    spec = spec_loader.load_spec(sys.argv[1])
    data = build_glb(spec, sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PALETTE)
    with open(sys.argv[2], "wb") as f:
        f.write(data)
    print("%s: %d bytes, triangles %s" % (sys.argv[2], len(data), model_stats(spec)))
