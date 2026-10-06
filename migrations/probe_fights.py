"""Print every remaining z-fight in a build with both boxes' actual extents.

WHY THIS EXISTS. The previous pass reported the 45 remaining fights as name
pairs and a count. A name pair says WHICH solids meet; it does not say HOW, and
the fix for a junction depends entirely on how. Two boxes sharing a corner
column want one of them shortened. Two boxes sharing a whole face want one of
them moved. Two boxes at identical extents are a duplicate emission and want one
of them deleted. All three read as "a <-> b" in a name list.

WHAT IT MEASURES, and nothing else. For each finding zfight_gate.visible_fights
returns, the two world AABBs that produced it, the overlap region between them,
and which face pair matched. It classifies the overlap by SHAPE only -- how many
axes the two boxes are flush on, and how deep the interpenetration runs -- and
prints that classification as a word, because "corner", "buried_end" and
"duplicate" are descriptions of an overlap, not diagnoses of a cause. The cause
belongs in the reply where it can be argued with.

It also prints, per fight, whether the shared face plane has a third solid
sitting against its OUTWARD side. That is not the gate's entombment test, which
requires matter on BOTH sides and is deliberately conservative. It is a separate
column, reported next to the gate's verdict rather than instead of it, because
the two answer different questions: the gate asks "could this ever flicker",
this asks "is anything currently in front of it". Where they disagree, that
disagreement is the finding.

    cd deli_counter
    python probe_fights.py build\\cr_deli.glb
    python probe_fights.py build\\cr_deli.glb --all      # include entombed

Reads a .glb and prints. Writes nothing.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import zfight_gate as zg  # noqa: E402

AXIS = "XYZ"


def _shape(alo, ahi, blo, bhi, tol):
    """Describe the overlap by how the two boxes sit, not by what caused it."""
    flush_max = [k for k in range(3) if abs(ahi[k] - bhi[k]) < tol]
    flush_min = [k for k in range(3) if abs(alo[k] - blo[k]) < tol]
    both = [k for k in range(3) if k in flush_max and k in flush_min]
    if len(both) == 3:
        return "duplicate"          # identical boxes; one of them is redundant
    contained = (all(blo[k] <= alo[k] + tol and bhi[k] >= ahi[k] - tol
                     for k in range(3))
                 or all(alo[k] <= blo[k] + tol and ahi[k] >= bhi[k] - tol
                        for k in range(3)))
    if contained:
        return "contained"          # one box wholly inside the other
    if len(both) == 2:
        return "crossing"           # equal on two axes, meeting on the third
    if len(both) == 1:
        return "corner"             # equal on one axis: two runs sharing a column
    return "partial"


def _outward_cover(boxes, i, j, ax, side, plane, rlo, rhi, tol, margin):
    """Names of solids covering the OUTWARD side of the shared plane over the
    whole shared rect. Outward is +ax for a max-face pair, -ax for a min-face
    pair -- the direction a camera would have to look from to see the fight."""
    o = [k for k in range(3) if k != ax]
    out = []
    for k, (nm, (slo, shi)) in enumerate(boxes):
        if k in (i, j):
            continue
        if side == "max":
            if not (slo[ax] <= plane + tol and shi[ax] >= plane + margin):
                continue
        else:
            if not (shi[ax] >= plane - tol and slo[ax] <= plane - margin):
                continue
        if all(slo[q] <= rlo[q] + tol and shi[q] >= rhi[q] - tol for q in o):
            out.append(nm)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("glb")
    ap.add_argument("--all", action="store_true",
                    help="include pairs the gate suppressed as entombed")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N fights (0 = every one)")
    args = ap.parse_args()

    path = pathlib.Path(args.glb)
    if not path.is_file():
        raise SystemExit(f"no such file: {path}")

    boxes = zg._node_world_boxes(str(path))
    index = {nm: k for k, (nm, _) in enumerate(boxes)}
    visible, buried = zg.visible_fights(boxes)
    rows = [("VISIBLE", f) for f in visible]
    if args.all:
        rows += [("entombed", f) for f in buried]

    print(f"{path.name}: {len(boxes)} visual solids, {len(visible)} visible "
          f"fights, {len(buried)} entombed")
    print(f"  gate constants  TOL={zg.TOL}  AREA_MIN={zg.AREA_MIN}  "
          f"PEN_MIN={zg.PEN_MIN}  OCCLUDE_MARGIN={zg.OCCLUDE_MARGIN}")
    print()

    shown = 0
    for verdict, f in rows:
        na, nb = f["a"], f["b"]
        ia, ib = index[na], index[nb]
        alo, ahi = boxes[ia][1]
        blo, bhi = boxes[ib][1]
        ax, side, plane = f["axis"], f["side"], f["plane"]
        rlo = [max(alo[k], blo[k]) for k in range(3)]
        rhi = [min(ahi[k], bhi[k]) for k in range(3)]
        pen = [round(rhi[k] - rlo[k], 4) for k in range(3)]
        shape = _shape(alo, ahi, blo, bhi, zg.TOL)
        cover = _outward_cover(boxes, ia, ib, ax, side, plane, rlo, rhi,
                               zg.TOL, zg.OCCLUDE_MARGIN)

        print(f"[{verdict}] {shape:<9} {na}  <->  {nb}")
        print(f"    face      {AXIS[ax]} {side} @ {plane}   "
              f"shared {f['area']} m^2")
        print(f"    A         "
              + "  ".join(f"{AXIS[k]} {alo[k]:9.4f}..{ahi[k]:<9.4f}"
                          for k in range(3)))
        print(f"    B         "
              + "  ".join(f"{AXIS[k]} {blo[k]:9.4f}..{bhi[k]:<9.4f}"
                          for k in range(3)))
        print(f"    overlap   "
              + "  ".join(f"{AXIS[k]} {rlo[k]:9.4f}..{rhi[k]:<9.4f}"
                          for k in range(3))
              + f"   depth {pen}")
        if cover:
            head = ", ".join(cover[:3])
            more = f" (+{len(cover) - 3} more)" if len(cover) > 3 else ""
            print(f"    outward   covered by {head}{more}")
        else:
            print(f"    outward   nothing in front of it")
        print()
        shown += 1
        if args.limit and shown >= args.limit:
            print(f"  ... stopped at --limit {args.limit}")
            break

    counts = {}
    for verdict, f in rows:
        ia, ib = index[f["a"]], index[f["b"]]
        counts[_shape(*boxes[ia][1], *boxes[ib][1], zg.TOL)] = \
            counts.get(_shape(*boxes[ia][1], *boxes[ib][1], zg.TOL), 0) + 1
    print("by overlap shape:")
    for k in sorted(counts, key=lambda x: -counts[x]):
        print(f"  {counts[k]:4d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
