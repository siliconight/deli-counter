"""Regression tests for the interior-partition footprint clamp + lint (L13).

The bug: a Y-axis partition authored with the X half-width (22) as its end
overshoots the 32 m depth (Y half 16) and ships as an interior wall poking
through the exterior shell. These lock both halves of the fix -- the shared
clamp used by the 3D builder, and the L13 spec invariant -- and run without
Blender (partition_bounds and layout_lint are bpy-free)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from partition_bounds import clamp_partition_span, partition_overshoot
import layout_lint

FX, FY = 44.0, 32.0   # footprint: X half = 22, Y half = 16


# ---- the shared clamp (used by deli_counter._partitions) --------------------

def test_y_wall_clamps_to_y_half_not_x_half():
    # the exact bug: int_0_1 = axis Y, start 8, end 22 -> must clamp to 16.
    assert clamp_partition_span(8, 22, "Y", FX, FY) == (8, 16)
    # full-depth basement wall authored -22..22 -> -16..16
    assert clamp_partition_span(-22, 22, "Y", FX, FY) == (-16, 16)


def test_x_wall_uses_x_half():
    # a genuine full-width X-wall must stay full width (22), unclamped.
    assert clamp_partition_span(-22, 22, "X", FX, FY) == (-22, 22)


def test_in_bounds_span_is_unchanged():
    assert clamp_partition_span(-10, 10, "Y", FX, FY) == (-10, 10)
    assert clamp_partition_span(0, 12, "X", FX, FY) == (0, 12)


def test_reversed_span_is_normalised():
    assert clamp_partition_span(22, 8, "Y", FX, FY) == (8, 16)


def test_overshoot_metres():
    assert partition_overshoot(8, 22, "Y", FX, FY) == 6.0     # 22 - 16
    assert partition_overshoot(-22, 22, "Y", FX, FY) == 6.0
    assert partition_overshoot(-22, 22, "X", FX, FY) == 0.0
    assert partition_overshoot(-10, 10, "Y", FX, FY) == 0.0


# ---- the L13 spec invariant (layout_lint) -----------------------------------

def _spec(parts):
    return {"footprint_x": FX, "footprint_y": FY, "rooms": [], "partitions": parts}


def test_lint_fails_out_of_bounds_partition():
    fails = layout_lint.bounds_findings(_spec(
        [{"axis": "Y", "pos": 10, "start": 8, "end": 22, "story": 0, "openings": []}]))
    assert any(f.startswith("L13") for f in fails), fails


def test_lint_passes_in_bounds_partition():
    assert layout_lint.bounds_findings(_spec(
        [{"axis": "Y", "pos": 10, "start": 8, "end": 16, "story": 0, "openings": []}])) == []


def test_lint_passes_full_width_x_wall():
    assert layout_lint.bounds_findings(_spec(
        [{"axis": "X", "pos": 8, "start": -22, "end": 22, "story": 0, "openings": []}])) == []


def test_clamp_and_lint_agree():
    """The builder's clamp and the L13 lint must never disagree: a span is
    'out of bounds' to the lint iff the clamp actually trims it."""
    for s, e, ax in [(8, 22, "Y"), (-22, 22, "Y"), (-22, 22, "X"),
                     (-10, 10, "Y"), (0, 12, "X"), (22, 8, "Y")]:
        over = partition_overshoot(s, e, ax, FX, FY)
        lo, hi = clamp_partition_span(s, e, ax, FX, FY)
        trimmed = (lo != min(s, e)) or (hi != max(s, e))
        assert (over > 0.0) == trimmed, (s, e, ax, over, lo, hi)
