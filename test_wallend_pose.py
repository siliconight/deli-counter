"""A wall remainder stands ALONG its wall whichever way the wall runs.

`wallEnd` is the one module Deli Counter scales: a unit cube whose slot
carries `scale = [length, thickness, height]` in the module's own frame
(`_volumes`). Two things had to agree for it to land, and from 0.81.0 to
0.119.0 neither did: `tscn_export.godot_basis` applied the scale in WORLD
axes after the rotation, and `themed_tscn._fit_rotation` fitted the unscaled
cube -- which has the same extents at every angle, so it tied and answered
0. At 0 the two errors cancel; on a wall that runs along Y they stack, and
the remainder stood with its length across the wall. Measured on cold runs
9001-9012: 237 of 777 wallEnd nodes. These pin the fix at both seams.
"""
import math

import themed_tscn
from tscn_export import godot_basis


def _placed(basis, ext):
    """Horizontal/vertical extents of a box of local extents `ext` placed by
    `basis` (9 floats, column-major) -- the same sum the placement gate uses."""
    return [abs(basis[i]) * ext[0] + abs(basis[3 + i]) * ext[1]
            + abs(basis[6 + i]) * ext[2] for i in range(3)]


def test_scale_is_applied_in_the_module_frame_then_turned():
    """A 1.875 x 0.3 x 3.3 remainder turned 90 degrees puts its LENGTH along
    Godot Z (DC Y). The old basis put 0.3 there."""
    b = godot_basis(90, [1.875, 0.3, 3.3])
    px, py, pz = _placed(b, [1.0, 1.0, 1.0])
    assert math.isclose(px, 0.3, abs_tol=1e-9)
    assert math.isclose(py, 3.3, abs_tol=1e-9)
    assert math.isclose(pz, 1.875, abs_tol=1e-9)


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
