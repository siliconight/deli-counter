"""A switchback's second flight stands on the floor under it (0.221.0), the walker's call of 2026-10-14.

The walker, at cold run 9310's office (the factory's `docs/findings/walk_2026-10-14/`, findings 7-9): "bottom of
this stair should come down all the way to the ground". `flight_solid_under` fills a switchback's first two legs
solid "to that storey's floor". With `cut_slabs`, leg 1's own storey floor is the slab its stair cut across both
runs, so its fill hung with a level bottom a storey over the floor below -- over the walkway 0.134.0 kept open
under it, whose north mouth was the gap the walker looked through. Asked, the walker chose: "fill the stairs to
the ground". Pure geometry over `stairwell`; no bpy. Frame: the building plan, metres. Run: python -m pytest
test_stair_fill_to_ground.py
"""
import glob
import os

import spec_loader
import stairwell as S
from spec_types import LevelSpec, SlabHole, Stairwell

HERE = os.path.dirname(os.path.abspath(__file__))


def _library_specs():
    """The library's specs, not Level Factory's per-candidate copies beside them (`specs/lf_*.json`)."""
    return [p for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
            if not os.path.basename(p).startswith("lf_")]


def _load(name):
    return spec_loader.load_spec(os.path.join(HERE, "specs", name + ".json"))


def _switchback(**kw):
    base = dict(x=0.0, y=0.0, from_story=0, to_story=2, width=1.6, run=4.7, style="switchback", id="a")
    base.update(kw)
    return Stairwell(**base)


def _shell(*stairs, **kw):
    base = dict(name="s", n_stories=3, footprint_x=30, footprint_y=24, stairs=list(stairs))
    base.update(kw)
    return LevelSpec(**base)


def test_the_walkers_second_flight_stands_on_the_ground_floor():
    sp = _load("office")
    st = sp.stairs[0]
    assert S.flight_solid_base(sp, st, 0) == 0
    assert S.flight_solid_base(sp, st, 1) == 0     # was storey 1's floor: the stair's own cut


def test_only_a_cut_multi_storey_switchbacks_second_leg_moves():
    sp = _shell(_switchback(to_story=1))                     # one storey: one leg
    assert S.flight_solid_base(sp, sp.stairs[0], 0) == 0
    sp = _shell(_switchback(cut_slabs=False))                # no cut: its storey floor is there
    assert S.flight_solid_base(sp, sp.stairs[0], 1) == 1
    sp = _shell(_switchback(open_under=True))                # an open underside fills nothing
    assert S.flight_solid_base(sp, sp.stairs[0], 1) == 1
    sp = _shell(_switchback(style="straight"))               # straight legs stack in one run
    assert S.flight_solid_base(sp, sp.stairs[0], 1) == 1
    sp = _shell(_switchback(to_story=3), n_stories=4)        # a third leg is not filled at all
    assert S.flight_solid_base(sp, sp.stairs[0], 2) == 2
    sp = _shell(_switchback(from_story=-1, to_story=1), has_basement=True)
    assert S.flight_solid_base(sp, sp.stairs[0], 0) == -1    # counted from the stair's own lowest storey


def test_a_floor_cut_under_the_second_run_keeps_its_own_storey():
    """If something else opens the lowest storey's floor under leg 1's run, the fill would stand on a hole
    again, so it keeps its own storey."""
    sp = _shell(_switchback())
    x0, y0, x1, y1 = S.flight_solid_rect(sp.stairs[0], sp.story_height, 1)
    sp.slab_holes.append(SlabHole(story=0, x=(x0 + x1) / 2.0, y=(y0 + y1) / 2.0, size_x=1.0, size_y=1.0))
    assert S.flight_solid_base(sp, sp.stairs[0], 1) == 1


def test_the_walkers_core_is_closed_to_the_north():
    """The walkway's north mouth, the gap the walker looked through (walker_75): the second run gets a back on
    the lowest storey from leg 1's foot to the rectangle's arrival edge, flush with the west side wall and with
    the first run's back, which is as 0.220.0 built it."""
    sp = _load("office")
    backs = sorted((p for p in S.stair_guards(sp) if p["kind"] == "back"), key=lambda p: p["lo"])
    assert [p["story"] for p in backs] == [0, 0], backs
    run_b, run_a = backs
    assert abs(run_a["lo"] - 0.0) < 1e-9 and abs(run_a["hi"] - 1.605) < 1e-9, run_a
    assert abs(run_a["pos"] - 2.622) < 1e-3 and abs(run_a["thick"] - 1.056) < 1e-3, run_a
    assert abs(run_b["lo"] - -1.605) < 1e-9 and abs(run_b["hi"] - 0.0) < 1e-9, run_b
    h = run_b["thick"] / 2.0
    assert abs(run_b["pos"] - h - (2.35 + S.SIDE_GAP)) < 1e-9, run_b
    assert abs(run_b["pos"] + h - 3.15) < 1e-9, run_b


def test_every_cut_second_flight_in_the_library_stands_on_its_stairs_lowest_floor():
    """17 legs in 14 specs, measured 2026-10-14 (the factory's `docs/findings/walk_2026-10-14/
    floating_flights.py`)."""
    legs, specs = 0, set()
    for path in _library_specs():
        sp = spec_loader.load_spec(path)
        for st in sp.stairs or ():
            if st.style != "switchback" or S.single_run(st) or not st.cut_slabs:
                continue
            lo = min(st.from_story, st.to_story)
            if not S.flight_solid_under(sp, st, lo + 1):
                continue
            assert S.flight_solid_base(sp, st, lo + 1) == lo, (path, st.id)
            legs += 1
            specs.add(os.path.basename(path))
    assert legs == 17 and len(specs) == 14, (legs, sorted(specs))
