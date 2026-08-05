"""
wallruns.py  --  a wall run split by its openings (pure geometry, bpy-free)
==========================================================================
One wall, one list of openings, out come the SOLID stretches between them.
Two consumers want this and want it to agree: `floorplan.py` draws the solid
stretches as poche bands, and `sightlines.py` treats them as occluders. A
wall you can see through where the drawing shows brick is a bug in whichever
one is wrong, and you cannot tell which without a shared answer.

WHY THIS MODULE EXISTS AT ALL
-----------------------------
It used to live in `floorplan.py` as `_opening_gaps` / `_wall_segments_with_gaps`,
and `sightlines.py` reached across the module boundary to call them by their
private, underscore-prefixed names. On 2026-07-24 commit `1c344a8` ("clamp
interior partitions to footprint") refactored `floorplan.py` and both helpers
went away. Nothing complained: an underscore name has no declared callers, so
the refactor looked local.

`sightlines._occluders` then raised `AttributeError` on every storey holding a
partition -- which is every real spec -- and its four callers
(`combat_audit`, `evidence`, `pvp_heist`, `validate`) each wrap it in
`except Exception`. So the entire sightline and cover pass returned nothing,
silently, for twelve days. The gate that should have caught two opposing
spawns one metre apart could not fire, and `test_pvp_heist.py` had been red
that whole time in a suite the commit hook did not run.

The lesson is not "be careful when refactoring". It is that a cross-module
call to a private name is an undeclared dependency, and undeclared
dependencies break quietly. These are public names in a module of their own,
so the next refactor has something to see.

Restored from `1c344a8^:floorplan.py` verbatim in behaviour. The one addition
is the optional footprint clamp, which is what `1c344a8` was actually adding
when the helpers were lost.
"""


def opening_gaps(openings, wall_lo, wall_hi):
    """Openings along a wall spanning ``[wall_lo, wall_hi]`` in world units,
    as ``(gap_lo, gap_hi, kind)`` world intervals.

    ``op.pos`` is a FRACTION in -0.5..0.5 of the wall's run, not a world
    coordinate (see `spec_types.Opening`), so the centre is
    ``mid + pos * span``. Getting that wrong puts every opening near the
    origin and is invisible on a wall centred there.

    ``kind`` is carried out and no caller currently reads it. That is
    deliberate: `sightlines` documents its greybox assumption as "every
    opening is see-through (worst-case LOS through doors/windows)", so a
    window occludes nothing today. Keeping the kind here means the day that
    assumption is revisited it is a filter on this tuple, not another dig
    through git history to find out what an opening was.
    """
    gaps = []
    span = wall_hi - wall_lo
    mid = (wall_hi + wall_lo) / 2
    for op in openings or ():
        try:
            width = op.resolved().get("width") or 1.0
        except Exception:
            # An opening that cannot resolve its own width still occupies the
            # wall. Falling back to the authored value (then the per-kind
            # default of 1.0) keeps the run split; skipping the opening would
            # draw and occlude solid wall across a doorway.
            width = getattr(op, "width", None) or 1.0
        center = mid + getattr(op, "pos", 0.0) * span
        gaps.append((center - width / 2, center + width / 2,
                     getattr(op, "kind", None)))
    return gaps


def segments_with_gaps(p0, p1, gaps, axis, bound=None):
    """The SOLID stretches of the wall ``p0 -> p1``, as point pairs.

    ``axis`` is 'x' when the wall runs along world X (x varies, y fixed) and
    'y' for the other. ``gaps`` are ``(lo, hi, kind)`` along the varying
    coordinate -- `opening_gaps` output, in any order.

    ``bound`` optionally clamps the run to +/- that half-extent, for a
    partition authored past the footprint edge. This is the clamp `1c344a8`
    added on the drawing side; it is off by default so a caller that has not
    asked for it gets the run exactly as authored.
    """
    if axis == "x":
        lo, hi = p0[0], p1[0]
        fixed = p0[1]
    else:
        lo, hi = p0[1], p1[1]
        fixed = p0[0]
    if bound is not None:
        lo, hi = max(lo, -bound), min(hi, bound)

    segs = []
    cur = lo
    # Sorted by gap start so `cur` only ever moves forward; overlapping
    # openings (a double door authored as two) merge into one stretch rather
    # than emitting a backwards segment.
    for glo, ghi, _kind in sorted(gaps or (), key=lambda g: g[0]):
        glo, ghi = max(glo, lo), min(ghi, hi)
        if ghi <= cur:
            continue
        if glo > cur:
            segs.append((cur, glo))
        cur = max(cur, ghi)
    if cur < hi:
        segs.append((cur, hi))

    out = []
    for a, b in segs:
        if axis == "x":
            out.append(((a, fixed), (b, fixed)))
        else:
            out.append(((fixed, a), (fixed, b)))
    return out
