"""Pure tests for the stair ramp meeting its landing (no bpy) -- the head's
half of what `test_stair_ramp_foot.py` proves for the foot (0.190.0).

Measured 2026-10-06 (roadmap 189 at the factory root): every one of the
library's 174 ramps topped out 0.19 to 0.21 m over the floor it delivers to,
and a capsule of Laser Tag's size never started down deli_a03's stair. Going
UP the ledge is a drop; coming DOWN it is a riser.

THE HEAD IS TRIMMED, NOT SUNK. Sinking the ramp by the overshoot landed the
head and was built and reverted: the ramp ran a riser under the nosings, every
visual tread stood above it, and the nav bake -- which reads visual meshes --
failed stair traversal on 94 of 144 shells. So the property that matters as
much as the flush head is the one tested here as
`test_no_tread_stands_above_the_ramp`.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract                # noqa: E402
import stairwell as S                # noqa: E402

THICK = 0.25
# LEGAL STAIRS ONLY: risers 0.15 to 0.22 m, treads 0.22 to 0.32 m. The first
# draft of this grid also held 4.5 m in 8 risers -- 0.56 m a step -- and both
# properties below fail there, for the shipped ramp as much as the trimmed one.
FLIGHTS = [(rise, n * tread, n)
           for rise in (2.8, 2.9, 3.3, 3.4, 4.0, 4.5)
           for n in range(math.ceil(rise / 0.22), math.floor(rise / 0.15) + 1)
           for tread in (0.22, 0.25, 0.28, 0.32)]
CELL = 0.1    # agent_contract nav_bake.cell_size_m


def _ramp(rise, run, n, trimmed=True):
    """The ramp as deli_counter.py places it: centre height and plan position
    (from the run's start), and its length along the incline."""
    pitch = math.atan2(rise, run)
    step = rise / n
    extra, back, drop = S.ramp_foot_extension(pitch, step)
    trim, tback, tdrop = (S.ramp_head_trim(pitch, step) if trimmed
                          else (0.0, 0.0, 0.0))
    return {"pitch": pitch, "step": step,
            "c_h": rise / 2.0 + step / 2.0 - drop - tdrop,
            "c_u": run / 2.0 - back - tback,
            "length": math.hypot(run, rise) + extra - trim}


def _head_corner(r):
    """The top face's end corner: the highest point of the ramp."""
    mid_end = r["c_h"] + r["length"] / 2.0 * math.sin(r["pitch"])
    return mid_end + (THICK / 2.0) * math.cos(r["pitch"])


def _foot_surface(r):
    mid_foot = r["c_h"] - r["length"] / 2.0 * math.sin(r["pitch"])
    return mid_foot + (THICK / 2.0) / math.cos(r["pitch"])


def _surface_at(r, u):
    """Walkable surface at plan distance `u` from the run's start, measured
    vertically through the tilt, as test_stair_ramp_foot measures it."""
    mid = r["c_h"] + (u - r["c_u"]) * math.tan(r["pitch"])
    return mid + (THICK / 2.0) / math.cos(r["pitch"])


def test_untrimmed_the_head_stands_a_riser_proud():
    """What shipped, on deli_a03's up-stair: 0.1995 m, against the 0.2 the
    library census measured, and well over what a capsule walks up."""
    r = _ramp(3.3, 4.0, 16, trimmed=False)
    proud = _head_corner(r) - 3.3
    assert abs(proud - 0.1995) < 0.001, proud
    assert proud > agent_contract.contract()["clearances"]["unassisted_step_max_m"]


def test_the_trim_lands_the_head_on_the_landing():
    for rise, run, n in FLIGHTS:
        got = _head_corner(_ramp(rise, run, n))
        assert abs(got - rise) < 1e-9, (rise, run, n, got)


def test_the_trim_keeps_the_foot_on_the_floor():
    for rise, run, n in FLIGHTS:
        assert abs(_foot_surface(_ramp(rise, run, n))) < 1e-9, (rise, run, n)


def test_no_tread_stands_above_the_ramp():
    """At every nosing the ramp still covers, its surface is at or above the
    tread: the bake meets the ramp, not a riser. This is what sinking broke."""
    for rise, run, n in FLIGHTS:
        r = _ramp(rise, run, n)
        step_d = run / n
        u_head = r["c_u"] + r["length"] / 2.0 * math.cos(r["pitch"])
        for i in range(n):
            u = step_d * i
            if u > u_head:
                break
            assert _surface_at(r, u) >= r["step"] * (i + 1) - 1e-9, (rise, run, n, i)


def test_the_strip_left_is_the_top_tread_and_a_sliver_at_most():
    """What the trim leaves in plan is at most one tread and one bake cell. A
    final leg's discharge collider reaches back over all of it; a landing
    reaches back over the top tread, so on a shallow stair (under about 33
    degrees) a sliver under one cell can lie between -- narrower than anything
    the bake resolves or a capsule can drop into."""
    for rise, run, n in FLIGHTS:
        pitch = math.atan2(rise, run)
        trim = S.ramp_head_trim(pitch, rise / n)[0]
        assert trim * math.cos(pitch) < run / n + CELL, (rise, run, n)


def test_a_level_ramp_needs_no_trim():
    assert S.ramp_head_trim(0.0, 0.2) == (0.0, 0.0, 0.0)


def test_the_builder_trims_and_reaches_back():
    """deli_counter.py is Blender-bound, so it is read as source: the flight's
    ramp is trimmed (not a scissor's), and a final leg's discharge collider
    reaches back over the strip. The L-stair builder is untouched."""
    src = open(os.path.join(HERE, "deli_counter.py"), encoding="utf-8").read()
    assert "length3d + _ext - _trim" in src
    assert 'if st.style == "scissor" else' in src
    assert src.count("stairwell.ramp_head_trim(angle") == 2
    lsh = src[src.index("def _stair_l_shaped"):]
    lsh = lsh[:lsh.index("\n    def ", 1)]
    assert "ramp_head_trim" not in lsh
