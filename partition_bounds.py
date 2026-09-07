"""Partition span clamping -- the single source of truth shared by the 3D
geometry builder (deli_counter._partitions), the spec linter (layout_lint L13),
and mirrored by the 2D floorplan, so a wall's built extent, its drawing, and the
lint can never disagree.

An interior wall runs along ONE axis and its extent must stay within the
footprint half-extent on THAT axis: a Y-wall is bounded by footprint_y/2, an
X-wall by footprint_x/2. Authoring a Y-wall's end from the X half-width is the
classic bug that ships interior partitions poking through the exterior shell.
"""
from __future__ import annotations


def axis_bound(axis, footprint_x, footprint_y):
    """Footprint half-extent on a partition's RUNNING axis."""
    return (footprint_y / 2.0) if str(axis).upper() == "Y" else (footprint_x / 2.0)


def clamp_partition_span(start, end, axis, footprint_x, footprint_y,
                         extent=None):
    """Clamp [start, end] to the footprint on the wall's running axis.

    Returns (lo, hi) with lo <= hi; ``hi - lo <= 0`` means the wall lies
    entirely outside the envelope and should not be built.

    `extent` is the storey's own ``(x0, y0, x1, y1)`` from `setbacks.py`, and
    it exists because a SETBACK CAN BE ASYMMETRIC (roadmap 116). The
    half-extent form below cannot express that: a storey inset 4 m from the
    north face alone runs -7..3, not +/-5, and clamping such a wall to a
    symmetric bound would both let it poke out of the stepped facade and cut
    it short at the face that did not move. When `extent` is None the
    behaviour is exactly as before, which is every spec that sets no setback.
    """
    if extent is not None:
        x0, y0, x1, y1 = extent
        blo, bhi = ((y0, y1) if str(axis).upper() == "Y" else (x0, x1))
    else:
        b = axis_bound(axis, footprint_x, footprint_y)
        blo, bhi = -b, b
    lo = max(min(start, end), blo)
    hi = min(max(start, end), bhi)
    return lo, hi


def hole_cuts(axis, pos, hole_rects, eps=1e-6):
    """Intervals on a wall's RUNNING axis that slab holes take away.

    `hole_rects` are world `(x0, y0, x1, y1)` for the holes in the slab the
    wall STANDS ON -- `stairwell.slab_openings(spec)[p.story]`, whose key is
    the storey whose FLOOR the hole opens. A wall over one of those has no
    floor under it; where the hole is a stairwell it is also a ceiling one
    storey height above the flight climbing through it, which is how this was
    found (roadmap 114).

    THE CENTRELINE DECIDES, not the wall's thickness band, and the choice is
    load-bearing rather than incidental. A stair's hole is deliberately
    oversized -- `width + 0.8` across and 0.8 m past the top landing -- so a
    band test would delete an enclosure wall seated flush against the shaft it
    encloses. The centreline is the minimum claim that can be made: the wall's
    own line is over void. It leaves up to a half-thickness of overhang, which
    is 0.125 m of soffit on the library's widest partition.
    """
    out = []
    for x0, y0, x1, y1 in hole_rects:
        if str(axis).upper() == "Y":
            across, cut = (x0, x1), (y0, y1)
        else:
            across, cut = (y0, y1), (x0, x1)
        if not (across[0] < pos < across[1]):
            continue
        if cut[1] - cut[0] > eps:
            out.append((cut[0], cut[1]))
    return sorted(out)


def subtract(lo, hi, cuts, min_span=0.0, eps=1e-6):
    """`[lo, hi]` minus every interval in `cuts`, left to right.

    Pieces shorter than `min_span` are dropped -- a wall shorter than its own
    thickness is a post, not a wall, and `night_pawn` leaves exactly one:
    0.10 m of drywall stranded between a stairwell and the shell.

    Returns `[(lo, hi), ...]`, possibly empty. WITH NO CUTS IT RETURNS THE
    INPUT UNCHANGED and untouched by the threshold, so a wall that meets no
    hole builds byte-identically to before this function existed -- including
    a legitimately short one that `min_span` would otherwise delete.
    """
    spans = [(lo, hi)]
    for c0, c1 in sorted(cuts):
        nxt = []
        for s0, s1 in spans:
            if c1 <= s0 + eps or c0 >= s1 - eps:
                nxt.append((s0, s1))
                continue
            if c0 - s0 > eps:
                nxt.append((s0, c0))
            if s1 - c1 > eps:
                nxt.append((c1, s1))
        spans = nxt
    if len(spans) == 1 and spans[0] == (lo, hi):
        return spans
    return [s for s in spans if s[1] - s[0] > max(min_span, eps)]


def partition_spans(start, end, axis, pos, footprint_x, footprint_y,
                    hole_rects=(), min_span=0.0, extent=None):
    """Every piece of one authored partition that actually gets built.

    Clamped to the footprint on its running axis (`clamp_partition_span`),
    then split around any slab hole it stands over. An empty list means the
    wall builds nothing at all.
    """
    lo, hi = clamp_partition_span(start, end, axis, footprint_x, footprint_y,
                                  extent=extent)
    if hi - lo <= 1e-6:
        return []
    return subtract(lo, hi, hole_cuts(axis, pos, hole_rects), min_span)


def piece_name(base, k):
    """The name of piece `k` of a split partition.

    PIECE 0 KEEPS THE AUTHORED NAME, so an unsplit wall -- every partition in
    115 of the library's 129 specs -- keeps the slot ids, interactive ids and
    surface names it has always had.

    It lives here because three passes have to agree on it and they run in
    different processes: `_partitions` bakes the object, `floorplan` draws it,
    and `stairwell._door_nodes` derives the interactive id a body opens. A
    fourth spelling of "p1" is exactly the kind of drift that makes an egress
    contract point at a node that is not there.
    """
    return base if k == 0 else "%sp%d" % (base, k)


def remap_opening(op_pos, raw_lo, raw_hi, lo, hi, eps=1e-6):
    """An opening's position in one piece's own frame, or None if it is not in
    that piece.

    `op_pos` is a fraction of the AUTHORED run measured from its centre, and
    the opening's WORLD position is what is preserved: a doorway does not
    slide because the wall it sits in got shorter at the other end. An opening
    whose centre falls in a removed part returns None -- there is no wall left
    to hang it on -- and the caller is expected to say so rather than drop it
    in silence.
    """
    raw_len = raw_hi - raw_lo
    world = (raw_lo + raw_hi) / 2.0 + op_pos * raw_len
    length = hi - lo
    if length <= eps:
        return None
    npos = (world - (lo + hi) / 2.0) / length
    return npos if abs(npos) <= 0.5 + eps else None


def partition_overshoot(start, end, axis, footprint_x, footprint_y):
    """Metres by which [start, end] exceeds the footprint on its axis (0.0 when
    in bounds). Positive means the wall pokes past the exterior shell."""
    b = axis_bound(axis, footprint_x, footprint_y)
    return max(0.0, max(start, end) - b, -b - min(start, end))
