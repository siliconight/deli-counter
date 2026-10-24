"""Pure tests for the stair ramp reaching the floor (no bpy).

deli_counter.py builds a flight's collision as one smooth incline set half a
step proud so its surface rides the step nosings. Correct along the run; at the
foot it means the surface starts above the floor it is supposed to meet, and
that gap is a riser. Measured on walkup_siege at 0.492 m against a capsule that
walks up 0.146 -- the walker parks against it with a horizontal contact normal
and the site fails its walktest.

Eight stair test modules existed and none of them mentioned the ramp collider,
which is why the defect shipped. Run: python3 test_stair_ramp_foot.py
"""
import math

import stairwell as S

THICK = 0.25


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _foot_height(pitch, rise, step_rise, length3d, extra, drop, thickness=THICK):
    """Top surface of the ramp at its lower end, relative to the flight base.

    Mirrors deli_counter.py's own placement: the slab's centre sits
    `rise/2 + step_rise/2 - drop` above the base plane, and its lower end is
    half the (extended) length downhill of that. The walkable surface is half
    the thickness above the mid-plane, measured VERTICALLY through the tilt.

    The `rise/2` term is not optional. Leaving it out cancels wrongly and the
    helper reports `-rise/2` for a ramp that lands perfectly -- which is what
    it did on first run, and is why this docstring names it."""
    centre = rise / 2.0 + step_rise / 2.0 - drop
    mid_at_foot = centre - (length3d + extra) / 2.0 * math.sin(pitch)
    return mid_at_foot + (thickness / 2.0) / math.cos(pitch)


# --- the defect, stated as the number it produced ----------------------------

def test_unextended_ramp_hovers_above_the_floor():
    """What shipped: no extension, and the surface starts a third of a metre up."""
    rise, run, n = 3.40, 4.16, 10
    pitch = math.atan2(rise, run)
    length3d = math.hypot(run, rise)
    hover = _foot_height(pitch, rise, rise / n, length3d, 0.0, 0.0)
    assert hover > 0.3, hover
    assert hover > 0.146, "this is the whole point: a capsule cannot walk it"


def test_extension_lands_the_surface_on_the_floor():
    rise, run, n = 3.40, 4.16, 10
    pitch = math.atan2(rise, run)
    length3d = math.hypot(run, rise)
    extra, back, drop = S.ramp_foot_extension(pitch, rise / n)
    assert abs(_foot_height(pitch, rise, rise / n, length3d, extra,
                              drop)) < 1e-9


def test_it_lands_across_every_plausible_flight():
    for rise in (2.8, 3.2, 3.4, 4.0):
        for run in (3.0, 4.16, 5.5):
            for n in (8, 10, 12, 16):
                pitch = math.atan2(rise, run)
                length3d = math.hypot(run, rise)
                extra, back, drop = S.ramp_foot_extension(pitch, rise / n)
                got = _foot_height(pitch, rise, rise / n, length3d,
                                   extra, drop)
                assert abs(got) < 1e-9, (rise, run, n, got)


# --- what must NOT move ------------------------------------------------------

def test_the_head_of_the_flight_does_not_move():
    """The top has to keep meeting the landing. Extending downhill and shifting
    the centre by half the extension leaves the upper end exactly where it was."""
    for rise, run, n in ((3.4, 4.16, 10), (2.8, 3.0, 8), (4.0, 5.5, 16)):
        pitch = math.atan2(rise, run)
        length3d = math.hypot(run, rise)
        extra, back, drop = S.ramp_foot_extension(pitch, rise / n)
        head_before = length3d / 2.0 * math.sin(pitch)
        head_after = -drop + (length3d + extra) / 2.0 * math.sin(pitch)
        assert abs(head_after - head_before) < 1e-9, (rise, run, n)


def test_the_plan_shift_matches_the_drop_at_the_pitch():
    pitch = math.atan2(3.4, 4.16)
    extra, back, drop = S.ramp_foot_extension(pitch, 0.34)
    assert abs(back - extra / 2.0 * math.cos(pitch)) < 1e-12
    assert abs(drop - extra / 2.0 * math.sin(pitch)) < 1e-12
    assert abs(math.hypot(back, drop) - extra / 2.0) < 1e-12


def test_a_steeper_flight_needs_less_extension():
    """Steeper means the surface loses height faster, so it reaches the floor
    sooner. A check that moved the other way would be measuring nothing."""
    shallow = S.ramp_foot_extension(math.radians(30), 0.34)[0]
    steep = S.ramp_foot_extension(math.radians(50), 0.34)[0]
    assert steep < shallow


def test_a_flat_flight_is_not_divided_by_zero():
    assert S.ramp_foot_extension(0.0, 0.34) == (0.0, 0.0, 0.0)


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for fn in ALL:
        _run(fn)
    print(f"\n{len(ALL)} ramp-foot tests passed.")
