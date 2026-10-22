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

#: Colours as they show on screen (sRGB 0-1). The walker picks one (2026-10-22, three put to them). Every role a
#: player reads by colour has its own: the first draft gave a hole's rim the entry's red, so an opening in a floor
#: read as a way in (`test_every_role_a_player_reads_has_its_own_colour`).
ROLES_READ = ("glass", "door", "entry", "tread", "ladder", "hole_rim")
PALETTES = {
    "blueprint": {"slab": (0.10, 0.20, 0.38), "slab_side": (0.07, 0.14, 0.28), "wall": (0.62, 0.82, 0.95),
                  "cap": (0.95, 0.98, 1.00), "glass": (0.35, 0.95, 0.95), "door": (0.85, 0.92, 1.00),
                  "entry": (1.00, 0.45, 0.25), "tread": (1.00, 0.75, 0.25), "ladder": (0.40, 1.00, 0.70),
                  "hole_rim": (1.00, 0.30, 0.65), "background": (0.03, 0.06, 0.12)},
    "model": {"slab": (0.70, 0.68, 0.64), "slab_side": (0.50, 0.48, 0.45), "wall": (0.95, 0.94, 0.91),
              "cap": (0.16, 0.17, 0.19), "glass": (0.55, 0.74, 0.86), "door": (0.30, 0.33, 0.37),
              "entry": (0.80, 0.22, 0.18), "tread": (0.78, 0.60, 0.30), "ladder": (0.15, 0.55, 0.55),
              "hole_rim": (0.55, 0.25, 0.60), "background": (0.13, 0.14, 0.16)},
    "dossier": {"slab": (0.90, 0.87, 0.78), "slab_side": (0.70, 0.66, 0.56), "wall": (0.30, 0.29, 0.27),
                "cap": (0.12, 0.11, 0.10), "glass": (0.60, 0.66, 0.66), "door": (0.45, 0.42, 0.38),
                "entry": (0.75, 0.10, 0.10), "tread": (0.55, 0.50, 0.42), "ladder": (0.25, 0.45, 0.30),
                "hole_rim": (0.20, 0.30, 0.55), "background": (0.82, 0.79, 0.70)},
}
DEFAULT_PALETTE = "blueprint"


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


def model_stats(spec, palette=DEFAULT_PALETTE):
    """{storey: triangles}."""
    return {s: len(m.idx) // 3 for s, m in _storeys(spec, PALETTES[palette]).items()}


def build_glb(spec, palette=DEFAULT_PALETTE):
    """The scout model as GLB bytes: a node and a mesh a storey (``storey_<n>``, at its true elevation, with
    ``extras.storey`` and ``extras.elevation``), one material, colour as normalised bytes in ``COLOR_0``."""
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

    for s, m in sorted(_storeys(spec, pal).items()):
        if not m.idx:
            continue
        p = add(b"".join(struct.pack("<3f", *v) for v in m.pos), 34962, 5126, "VEC3", len(m.pos),
                {"min": [min(v[i] for v in m.pos) for i in range(3)],
                 "max": [max(v[i] for v in m.pos) for i in range(3)]})
        n = add(b"".join(struct.pack("<3f", *v) for v in m.nrm), 34962, 5126, "VEC3", len(m.nrm))
        c = add(b"".join(struct.pack("<4B", *v) for v in m.col), 34962, 5121, "VEC4", len(m.col),
                {"normalized": True})
        i = add(b"".join(struct.pack("<I", v) for v in m.idx), 34963, 5125, "SCALAR", len(m.idx))
        meshes.append({"name": "storey_%d" % s, "primitives": [
            {"attributes": {"POSITION": p, "NORMAL": n, "COLOR_0": c}, "indices": i, "material": 0}]})
        nodes.append({"name": "storey_%d" % s, "mesh": len(meshes) - 1,
                      "translation": [0.0, round(s * sh, 6), 0.0],
                      "extras": {"storey": s, "elevation": round(s * sh, 6)}})
    gltf = {"asset": {"version": "2.0", "generator": "deli_counter scout_model"},
            "scene": 0, "scenes": [{"name": spec.name, "nodes": list(range(len(nodes))),
                                    "extras": {"palette": palette,
                                               "background": list(pal["background"])}}],
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
