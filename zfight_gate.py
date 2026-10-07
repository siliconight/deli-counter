#!/usr/bin/env python3
"""
zfight_gate.py  --  coplanar-surface (z-fight) gate for composed packages
=========================================================================
Two opaque faces on the same plane, facing the same way, overlapping in
area flicker ("z-fight") as the camera moves -- the depth buffer cannot
order them. Greybox-on-greybox coincidences are invisible (same material
both sides), but the moment the art pass puts a themed surface against a
greybox one the flicker is glaring. A composed package must ship with
ZERO such pairs; this gate proves it.

Box-level check (DC content is axis-aligned boxes at 90-degree turns).
A pair of solids z-fights iff ALL of:
  - real volume interpenetration (> PEN_MIN on every axis; mere contact
    is how geometry normally meets),
  - a face pair on the same plane (within TOL) on the SAME side of both
    boxes -- max-face vs max-face or min-face vs min-face (same-facing),
  - shared face area >= AREA_MIN (a sliver can't be seen flickering).
Abutting faces (max-vs-min: a wall top meeting the ceiling above) are
never flagged.

A pair can be seen only from the side its two faces FACE, so it is judged
there (0.198.0, `visible_fights`). When solid matter within OUTWARD_GAP of
the plane on that side covers the shared rectangle -- one solid, or several
together in 2-D -- no camera can reach either face, and the pair is reported
buried, not visible. Before 0.198.0 a pair was buried only inside a solid
with matter on BOTH sides of the plane, so a chair and the floor module it
stands in, both bottoms on the slab and facing down into it, read as
flicker: cold run 9189's deli_a01, office and rail_station_a02 reported 198,
121 and 117 pairs, and judged by what their faces face, 2, 2 and 1.

Pure geometry; pygltflib only for reading node boxes. No bpy. Run
standalone on a composed package:

    python zfight_gate.py <package_dir>          # exit 1 on findings

or from the composer: build_package() records check_package() in the
portable manifest and the LF compose driver fails the job on findings.
"""
import json
import os
import re
import sys

TOL = 0.0015        # same-plane tolerance (m)
AREA_MIN = 0.05     # smallest shared face area worth flagging (m^2)
PEN_MIN = 0.0005    # minimum interpenetration on every axis (m)
OCCLUDE_MARGIN = 0.003   # how far past the plane a covering solid must reach
# The composer sinks wall-family modules this far (themed_tscn.SLAB_CAP_SINK,
# mirrored here so this gate stays free of the scene exporter; a test pins the
# two together), which leaves their caps 4 mm under the slab above them.
SLAB_CAP_SINK = 0.004
# How close to the plane, on the side the faces face, matter must start to
# shut them (0.198.0): the composer's own sink plus this gate's tolerance. A
# slot that thin holds no camera. Nothing in cold run 9189's buildings needed
# more, and a 5 cm gap read the same.
OUTWARD_GAP = SLAB_CAP_SINK + TOL


# ---------------------------------------------------------------------------
# Core: pure box geometry (unit-tested without any file I/O)
# ---------------------------------------------------------------------------

def coplanar_fights(named_boxes, tol=TOL, area_min=AREA_MIN, pen_min=PEN_MIN):
    """named_boxes: [(name, (lo3, hi3)), ...] world AABBs of opaque solids.
    Returns findings: [{a, b, axis, side, plane, area}] -- every same-facing
    coplanar overlapping face pair. Empty list = no z-fights."""
    out = []
    n = len(named_boxes)
    for i in range(n):
        na, (alo, ahi) = named_boxes[i]
        for j in range(i + 1, n):
            nb, (blo, bhi) = named_boxes[j]
            d = [min(ahi[k], bhi[k]) - max(alo[k], blo[k]) for k in range(3)]
            if any(dk <= pen_min for dk in d):
                continue                      # contact or apart: never a fight
            rlo = [max(alo[k], blo[k]) for k in range(3)]
            rhi = [min(ahi[k], bhi[k]) for k in range(3)]
            for ax in range(3):
                o = [k for k in range(3) if k != ax]
                area = d[o[0]] * d[o[1]]
                if area < area_min:
                    continue
                if abs(ahi[ax] - bhi[ax]) < tol:
                    out.append({"a": na, "b": nb, "axis": ax, "side": "max",
                                "plane": round(ahi[ax], 4),
                                "area": round(area, 3),
                                "_rect": (ax, min(ahi[ax], bhi[ax]),
                                          tuple(rlo), tuple(rhi)), "_ij": (i, j)})
                if abs(alo[ax] - blo[ax]) < tol:
                    out.append({"a": na, "b": nb, "axis": ax, "side": "min",
                                "plane": round(alo[ax], 4),
                                "area": round(area, 3),
                                "_rect": (ax, max(alo[ax], blo[ax]),
                                          tuple(rlo), tuple(rhi)), "_ij": (i, j)})
    return out


def visible_fights(named_boxes, tol=TOL, area_min=AREA_MIN, pen_min=PEN_MIN,
                   margin=OCCLUDE_MARGIN, gap=OUTWARD_GAP):
    """coplanar_fights minus pairs whose shared face region is SHUT on the side
    the two faces face: solid matter starting within `gap` of the plane on
    that side and reaching at least `margin` past it, covering the region
    alone or together. A face no camera can reach cannot flicker -- end-faces
    of a wall run buried in the perpendicular wall's band, co-sunk junction
    caps under a slab, the bottoms of a piece and the floor module it stands
    in, pressed on the slab -- geometry meeting the way DC intends.

    THE FACING SIDE, not both sides (0.198.0). A min face looks down its axis
    and a max face up it, and both faces of a pair look the same way. Until
    0.198.0 a cover needed matter on BOTH sides of the plane, which buried a
    face inside a wall band and nothing pressed against a slab: on cold run
    9189's deli_a01, 198 visible pairs, of which 2 have an open side.
    Matter on both sides is matter on the facing side, so every pair the old
    rule buried, this one buries too.

    Returns (visible, suppressed) -- both lists of finding dicts."""
    raw = coplanar_fights(named_boxes, tol, area_min, pen_min)
    visible, suppressed = [], []
    for f in raw:
        ax, plane, rlo, rhi = f.pop("_rect")
        i, j = f.pop("_ij")
        o = [k for k in range(3) if k != ax]
        # covers: solids (other than the pair) on the side the faces face,
        # from within `gap` of the plane to at least `margin` past it. One may
        # shut the region alone, or several TOGETHER -- adjacent wall segments
        # split exactly where a partition lands, slab tiles meet under a desk
        # in a 2 x 2 corner -- so joint coverage is the common case.
        cands = []
        for k, (nm, (slo, shi)) in enumerate(named_boxes):
            if k in (i, j):
                continue
            if f["side"] == "min":
                if slo[ax] <= plane - margin and shi[ax] >= plane - gap:
                    cands.append((nm, slo, shi))
            elif shi[ax] >= plane + margin and slo[ax] <= plane + gap:
                cands.append((nm, slo, shi))
        buried_in = None
        for nm, slo, shi in cands:
            if all(slo[q] <= rlo[q] + tol and shi[q] >= rhi[q] - tol
                   for q in o):
                buried_in = nm
                break
        if buried_in is None and _rect_covered(
                [(slo, shi) for _nm, slo, shi in cands], rlo, rhi, o, tol):
            buried_in = "(joint cover)"
        if buried_in is not None:
            f["buried_in"] = buried_in
            suppressed.append(f)
        else:
            visible.append(f)
    return visible, suppressed


def _rect_covered(boxes, rlo, rhi, o, tol):
    """True if the union of `boxes` covers the rectangle rlo..rhi on the two
    axes `o`, to `tol`. The rectangle is cut on every box edge inside it, and
    every cell's centre must lie in some box.

    2-D, not 1-D (0.198.0). The 1-D union it replaces needed one box to span
    the whole rectangle across, so four slab tiles meeting in a corner under
    a desk covered it and read as uncovered. And `tol` is not optional: 9189's
    slab tiles meet at -9.333000183 and -9.332999944, a float32 seam of
    2.4e-7 m, and a first version without it called every seam a hole."""
    cuts = []
    for q in o:
        c = {rlo[q], rhi[q]}
        for lo, hi in boxes:
            for v in (lo[q], hi[q]):
                if rlo[q] < v < rhi[q]:
                    c.add(v)
        cuts.append(sorted(c))
    for a0, a1 in zip(cuts[0], cuts[0][1:]):
        for b0, b1 in zip(cuts[1], cuts[1][1:]):
            ma, mb = (a0 + a1) / 2.0, (b0 + b1) / 2.0
            if not any(lo[o[0]] - tol <= ma <= hi[o[0]] + tol
                       and lo[o[1]] - tol <= mb <= hi[o[1]] + tol
                       for lo, hi in boxes):
                return False
    return True


# ---------------------------------------------------------------------------
# Package reader: world boxes for the greybox base + every placed module
# ---------------------------------------------------------------------------

def _node_world_boxes(glb_path):
    """[(node_name, (lo, hi))] for visual (non-collision) meshed nodes, with
    the node's full TRS applied to its local POSITION accessor bounds."""
    from pygltflib import GLTF2
    g = GLTF2().load(glb_path)
    out = []
    for nd in g.nodes:
        if nd.mesh is None:
            continue
        nm = nd.name or ""
        if "colonly" in nm.lower():
            continue
        lo = [1e18] * 3
        hi = [-1e18] * 3
        ok = False
        for p in g.meshes[nd.mesh].primitives:
            acc = g.accessors[p.attributes.POSITION]
            if acc.min and acc.max:
                ok = True
                for i in range(3):
                    lo[i] = min(lo[i], acc.min[i])
                    hi[i] = max(hi[i], acc.max[i])
        if not ok:
            continue
        m = _trs_matrix(nd)
        pts = [_apply(m, (x, y, z))
               for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
               for z in (lo[2], hi[2])]
        out.append((nm, ([min(p[i] for p in pts) for i in range(3)],
                         [max(p[i] for p in pts) for i in range(3)])))
    return out


def _trs_matrix(nd):
    t = nd.translation or [0.0, 0.0, 0.0]
    q = nd.rotation or [0.0, 0.0, 0.0, 1.0]
    s = nd.scale or [1.0, 1.0, 1.0]
    x, y, z, w = q
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[r[i][j] * s[j] for j in range(3)] + [t[i]] for i in range(3)]


def _apply(m, p):
    return tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3]
                 for i in range(3))


_EXT = re.compile(r'\[ext_resource type="PackedScene" path="res://([^"]+)" '
                  r'id="([^"]+)"\]')
_NODE = re.compile(r'\[node name="([^"]+)"[^\]]*instance=ExtResource\('
                   r'"([^"]+)"\)')
_XF = re.compile(r'transform = Transform3D\(([^)]+)\)')


def _scene_module_boxes(pkg_dir, tscn_name):
    """World AABB per placed module instance in the composed scene: the
    module glb's union visual box pushed through the instance transform."""
    text = open(os.path.join(pkg_dir, tscn_name), encoding="utf-8").read()
    paths = {rid: p for p, rid in _EXT.findall(text)}
    boxes = []
    cache = {}
    for block in re.split(r"\n(?=\[node )", text):
        mn = _NODE.match(block)
        if not mn:
            continue
        # Hidden nodes are interactive STATE VARIANTS (a window's `_broken`
        # remnant, a breach wall's `_breached` hole) parked at the same
        # transform as their visible default, deliberately coplanar with it.
        # A mesh that does not render cannot flicker, and the swap contract
        # (INTERACTIVES.md) is exclusive visibility -- the game shows one
        # sibling at a time. Gate what renders at rest, not the parked art.
        if re.search(r"^visible = false\b", block, re.M):
            continue
        ref = paths.get(mn.group(2), "")
        if not ref.startswith("art/zoo/") or not ref.endswith(".glb"):
            # base is handled per-node separately; content LAYERS (dressing /
            # fixtures) are prop clouds whose union AABB spans the building --
            # box-level coplanar checks are meaningless for them.
            continue
        glb = os.path.join(pkg_dir, ref)
        if not os.path.exists(glb):
            continue
        if ref not in cache:
            per = _node_world_boxes(glb)
            if not per:
                cache[ref] = None
            else:
                cache[ref] = ([min(b[0][i] for _, b in per) for i in range(3)],
                              [max(b[1][i] for _, b in per) for i in range(3)])
        local = cache[ref]
        if local is None:
            continue
        xf = _XF.search(block)
        f = ([float(v) for v in xf.group(1).split(",")] if xf
             else [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
        m = [[f[0], f[3], f[6], f[9]],
             [f[1], f[4], f[7], f[10]],
             [f[2], f[5], f[8], f[11]]]
        lo, hi = local
        pts = [_apply(m, (x, y, z))
               for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
               for z in (lo[2], hi[2])]
        boxes.append((mn.group(1), ([min(p[i] for p in pts) for i in range(3)],
                                    [max(p[i] for p in pts) for i in range(3)])))
    return boxes


def check_package(pkg_dir, scene_name=None):
    """Gate a composed package dir. Returns {ok, pairs, solids, findings}."""
    if scene_name is None:
        cands = [f for f in sorted(os.listdir(pkg_dir))
                 if f.endswith(".tscn") and not f.endswith("_main.tscn")
                 and not f.endswith("_walk.tscn") and "lux" not in f]
        if not cands:
            return {"ok": False, "error": "no scene .tscn in package"}
        scene_name = "site.tscn" if "site.tscn" in cands else cands[0]
    solids = []
    for f in sorted(os.listdir(pkg_dir)):
        if f.endswith("_base.glb"):
            solids += [(f"base:{nm}", b)
                       for nm, b in _node_world_boxes(os.path.join(pkg_dir, f))]
    solids += _scene_module_boxes(pkg_dir, scene_name)
    vis, buried = visible_fights(solids)
    # The gate judges what the COMPOSE added: module-vs-module and
    # module-vs-greybox pairs. Greybox-internal coincidences (stair treads
    # flush with a floor slab, etc.) are same-material-both-sides -- invisible
    # by construction and DC's own geometry, not a compose defect. They are
    # reported for intel, never gated on. Entombed pairs (visible_fights'
    # suppression) are likewise intel only.
    findings = [x for x in vis
                if not (x["a"].startswith("base:")
                        and x["b"].startswith("base:"))]
    return {"ok": not findings, "pairs": len(findings),
            "solids": len(solids), "scene": scene_name,
            "greybox_internal_pairs": len(vis) - len(findings),
            "buried_pairs": len(buried),
            "findings": findings[:50]}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = check_package(sys.argv[1])
    print(json.dumps({k: v for k, v in r.items() if k != "findings"},
                     indent=2))
    for f in r.get("findings", []):
        print(f"  FIGHT {f['a']}  ~  {f['b']}  "
              f"(axis {f['axis']} {f['side']} @ {f['plane']}, {f['area']} m^2)")
    sys.exit(0 if r.get("ok") else 1)


if __name__ == "__main__":
    main()
