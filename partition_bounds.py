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


def clamp_partition_span(start, end, axis, footprint_x, footprint_y):
    """Clamp [start, end] to the footprint on the wall's running axis.

    Returns (lo, hi) with lo <= hi; ``hi - lo <= 0`` means the wall lies
    entirely outside the envelope and should not be built.
    """
    b = axis_bound(axis, footprint_x, footprint_y)
    lo = max(min(start, end), -b)
    hi = min(max(start, end), b)
    return lo, hi


def partition_overshoot(start, end, axis, footprint_x, footprint_y):
    """Metres by which [start, end] exceeds the footprint on its axis (0.0 when
    in bounds). Positive means the wall pokes past the exterior shell."""
    b = axis_bound(axis, footprint_x, footprint_y)
    return max(0.0, max(start, end) - b, -b - min(start, end))
