"""A wall remainder stands ALONG its wall whichever way the wall runs.

`wallEnd` is the one module Deli Counter scales: a unit cube whose slot
carries `scale = [length, thickness, height]` in the module's own frame
(`_volumes`). From 0.81.0 to 0.119.0 `themed_tscn._fit_rotation` fitted the
unscaled cube -- which has the same extents at every angle, so it tied and
answered 0 -- and the remainder on any wall that runs along Y stood with
its length across the wall: 237 of 777 wallEnd nodes on cold runs
9001-9012. 0.120.0 gave the fit the scale AND rewrote `godot_basis` on the
belief that its nine numbers were axes; they are Godot's ROWS, the old
numbers were right, and cold run 9013 shipped the pieces across the other
way (the engine's census: 6 across; the gate, summing columns: 165/165).
These pin the fit, the rows, and the extent sum -- against the engine's
reading, not the writer's.
"""
import math

import themed_tscn
from tscn_export import godot_basis, placed_extent


def _placed(basis, ext):
    return placed_extent(basis, ext)


def test_scale_is_applied_in_the_module_frame_then_turned():
    """A 1.875 x 0.3 x 3.3 remainder turned 90 degrees puts its LENGTH along
    Godot Z (DC Y): the rows of Ry(-90) x diag(1.875, 3.3, 0.3)."""
    b = godot_basis(90, [1.875, 0.3, 3.3])
    assert [round(v, 6) for v in b] == [0.0, 0.0, -0.3, 0.0, 3.3, 0.0, 1.875, 0.0, 0.0]
    px, py, pz = _placed(b, [1.0, 1.0, 1.0])
    assert math.isclose(px, 0.3, abs_tol=1e-9)
    assert math.isclose(py, 3.3, abs_tol=1e-9)
    assert math.isclose(pz, 1.875, abs_tol=1e-9)


def test_the_extent_sum_reads_rows_not_columns():
    """The transpose's answer is the footprint swapped: the gate said 165 of
    165 on cold run 9013's bank while the engine measured 6 across."""
    b = godot_basis(90, [1.7, 0.3, 4.3])
    assert [round(v, 3) for v in placed_extent(b, [1.0, 1.0, 1.0])] == [0.3, 4.3, 1.7]
    cols = [abs(b[i]) + abs(b[3 + i]) + abs(b[6 + i]) for i in range(3)]
    assert [round(v, 3) for v in cols] == [1.7, 4.3, 0.3]


def test_at_zero_degrees_the_two_orders_agree():
    b = godot_basis(0, [0.25, 0.3, 3.3])
    assert [round(v, 6) for v in _placed(b, [1.0, 1.0, 1.0])] == [0.25, 3.3, 0.3]


def test_unit_scale_is_the_plain_rotation():
    """Exact-fit modules (scale 1) are untouched by the change."""
    b = godot_basis(90, [1.0, 1.0, 1.0])
    assert [round(v, 6) for v in b] == [0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0]


def test_the_fit_sees_the_scaled_cube_not_the_unit_cube():
    """Greybox extent of `int_0_1_seg1` (bank_branch_a03): 0.3 along X,
    1.875 along Z. The unscaled unit cube ties at every angle and the fit
    answers 0 -- the first angle tried, NOT the fallback, which only stands
    when no angle scores at all; the scaled one fits at 90."""
    ge = [0.3, 3.3, 1.875]
    assert themed_tscn._fit_rotation([1.0, 1.0, 1.0], ge, fallback=90) == 0
    assert themed_tscn._fit_rotation([1.0, 1.0, 1.0], ge, fallback=0) == 0
    assert themed_tscn._fit_rotation([1.0, 1.0, 1.0], ge, fallback=0,
                                     scale=[1.875, 0.3, 3.3]) in (90, 270)
    assert themed_tscn._fit_rotation([1.0, 1.0, 1.0], [1.875, 3.3, 0.3],
                                     fallback=90, scale=[1.875, 0.3, 3.3]) in (0, 180)


def test_fit_and_basis_together_reproduce_the_greybox_footprint():
    for ge, scale in (([0.3, 3.3, 1.875], [1.875, 0.3, 3.3]),
                      ([1.35, 3.3, 0.3], [1.35, 0.3, 3.3]),
                      ([0.3, 3.3, 0.25], [0.25, 0.3, 3.3])):
        rot = themed_tscn._fit_rotation([1.0, 1.0, 1.0], ge, scale=scale)
        px, _py, pz = _placed(godot_basis(rot, scale), [1.0, 1.0, 1.0])
        assert math.isclose(px, ge[0], abs_tol=1e-9)
        assert math.isclose(pz, ge[2], abs_tol=1e-9)
