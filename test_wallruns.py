"""Wall runs split by their openings, and the sightline pass that depends on
them being ALIVE.

Two kinds of test here and they are testing different things:

  * the geometry contract of `wallruns` -- fractional opening positions, gap
    merging, clamping;
  * LIVENESS -- that `sightlines` actually produces occluders and findings on
    a real spec.

The second kind exists because of what happened on 2026-07-24: `floorplan.py`
was refactored, two private helpers `sightlines` had been reaching across for
vanished, and every sightline check raised into an `except Exception` for
twelve days. Nothing was red. A test that only asserts "does not raise" would
ALSO have stayed green through that, because the raising happened inside the
swallowing callers -- so these assert on non-empty output instead.

Run:  python -m pytest test_wallruns.py
"""
import json
import os

import pytest

import wallruns

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "specs", "pvp_station_ref.json")


class _Op(object):
    """Minimal stand-in for spec_types.Opening."""
    def __init__(self, pos, width, kind="door"):
        self.pos, self.width, self.kind = pos, width, kind

    def resolved(self):
        return {"width": self.width}


def _ref_spec():
    from spec_loader import spec_from_dict
    with open(REF, "r", encoding="utf-8") as f:
        return spec_from_dict(json.load(f))


# --- opening_gaps: the fractional position contract --------------------

def test_pos_is_a_fraction_of_the_run_not_a_world_coordinate():
    """`Opening.pos` is -0.5..0.5 of the wall's length. Reading it as world
    metres puts every opening near the origin, which on a wall centred there
    looks almost right and is wrong everywhere else."""
    gaps = wallruns.opening_gaps([_Op(0.25, 2.0)], -10.0, 10.0)
    assert gaps == [(4.0, 6.0, "door")]


def test_pos_zero_is_the_middle_of_the_run_wherever_the_run_is():
    gaps = wallruns.opening_gaps([_Op(0.0, 2.0)], 10.0, 30.0)
    assert gaps == [(19.0, 21.0, "door")]


def test_width_falls_back_rather_than_dropping_the_opening():
    """An opening that cannot resolve its width still occupies the wall.
    Dropping it would draw -- and occlude -- solid wall across a doorway."""
    class Broken(_Op):
        def resolved(self):
            raise ValueError("no")
    gaps = wallruns.opening_gaps([Broken(0.0, 3.0)], -5.0, 5.0)
    assert gaps == [(-1.5, 1.5, "door")]


def test_kind_is_carried_out():
    """No caller filters on it today -- sightlines documents every opening as
    see-through -- but the day that changes it must not need a git dig."""
    gaps = wallruns.opening_gaps([_Op(0.0, 1.0, "window")], -5.0, 5.0)
    assert gaps[0][2] == "window"


def test_no_openings_is_no_gaps():
    assert wallruns.opening_gaps([], -5.0, 5.0) == []
    assert wallruns.opening_gaps(None, -5.0, 5.0) == []


# --- segments_with_gaps: the split -------------------------------------

def test_a_solid_wall_is_one_segment():
    segs = wallruns.segments_with_gaps((-5.0, 2.0), (5.0, 2.0), [], "x")
    assert segs == [((-5.0, 2.0), (5.0, 2.0))]


def test_a_door_in_the_middle_leaves_two_stretches():
    segs = wallruns.segments_with_gaps((-5.0, 2.0), (5.0, 2.0),
                                       [(-1.0, 1.0, "door")], "x")
    assert segs == [((-5.0, 2.0), (-1.0, 2.0)), ((1.0, 2.0), (5.0, 2.0))]


def test_the_y_axis_holds_x_fixed():
    segs = wallruns.segments_with_gaps((3.0, -5.0), (3.0, 5.0),
                                       [(-1.0, 1.0, "door")], "y")
    assert segs == [((3.0, -5.0), (3.0, -1.0)), ((3.0, 1.0), (3.0, 5.0))]


def test_overlapping_openings_merge_into_one_hole():
    """A double door authored as two overlapping leaves must not emit a
    backwards segment between them."""
    segs = wallruns.segments_with_gaps(
        (-5.0, 0.0), (5.0, 0.0),
        [(-2.0, 0.5, "door"), (-0.5, 2.0, "door")], "x")
    assert segs == [((-5.0, 0.0), (-2.0, 0.0)), ((2.0, 0.0), (5.0, 0.0))]
    for (a, _), (b, _) in segs:
        assert b > a


def test_gaps_are_sorted_by_the_split_not_by_the_caller():
    unsorted_ = [(2.0, 3.0, "door"), (-3.0, -2.0, "door")]
    segs = wallruns.segments_with_gaps((-5.0, 0.0), (5.0, 0.0), unsorted_, "x")
    assert segs == [((-5.0, 0.0), (-3.0, 0.0)),
                    ((-2.0, 0.0), (2.0, 0.0)),
                    ((3.0, 0.0), (5.0, 0.0))]


def test_an_opening_wider_than_the_wall_leaves_nothing_solid():
    segs = wallruns.segments_with_gaps((-2.0, 0.0), (2.0, 0.0),
                                       [(-99.0, 99.0, "garage")], "x")
    assert segs == []


def test_clamp_is_off_unless_asked_for():
    """`bound` is the footprint clamp 1c344a8 was adding when these helpers
    were lost. A caller that has not asked for it gets the run as authored."""
    raw = wallruns.segments_with_gaps((-20.0, 0.0), (20.0, 0.0), [], "x")
    assert raw == [((-20.0, 0.0), (20.0, 0.0))]
    clamped = wallruns.segments_with_gaps((-20.0, 0.0), (20.0, 0.0), [], "x",
                                          bound=10.0)
    assert clamped == [((-10.0, 0.0), (10.0, 0.0))]


# --- LIVENESS: the pass must actually produce something ----------------

def test_occluders_are_not_empty_on_a_real_spec():
    """The regression that started all this: `_occluders` raised on every
    storey holding a partition. Asserting a NUMBER, not merely that no
    exception escaped -- the dead version escaped nothing either, its callers
    ate it."""
    import sightlines
    spec = _ref_spec()
    for story in (0, 1):
        occ = sightlines._occluders(spec, story)
        assert len(occ) > 5, (story, len(occ))


def test_sightlines_does_not_reach_into_floorplan_privates():
    """The actual root cause was a cross-module call to an underscore name,
    which has no declared callers and so breaks silently. Keep it gone."""
    import inspect
    import sightlines
    src = inspect.getsource(sightlines)
    # match the CALL (trailing paren) -- the module docstring names these
    # helpers in prose on purpose, to explain why they are gone.
    assert "fp._opening_gaps(" not in src
    assert "fp._wall_segments_with_gaps(" not in src


def test_analyze_reports_a_death_lane():
    import sightlines
    spec = _ref_spec()
    got = sightlines.analyze(spec)
    assert got, "analyze returned no stories"
    assert any(s["death_lane_m"] > 0 for s in got)


def test_spawn_los_gate_fires_on_stacked_opposing_spawns():
    """The end-to-end proof, duplicated from test_pvp_heist deliberately: if
    this file is green and that one is red, the difference is the gate's
    plumbing rather than its geometry."""
    import pvp_heist
    from spec_loader import spec_from_dict
    with open(REF, "r", encoding="utf-8") as f:
        d = json.load(f)
    atk = next(m for m in d["markers"] if m["type"] == "attacker_spawn")
    d["markers"].append({"type": "defender_spawn", "id": "LOS",
                         "x": atk["x"] + 1.0, "y": atk["y"],
                         "z": atk.get("z", 0)})
    errors, _, _ = pvp_heist.check(spec_from_dict(d))
    codes = {e.split(":", 1)[0] for e in errors}
    assert "PVP-SPAWN-LOS" in codes


def test_an_unavailable_gate_is_a_failure_not_a_pass(monkeypatch):
    """The rule this whole incident is about. If the sightline pass cannot
    run, PVP must report that it could not check -- never an empty findings
    list, which is indistinguishable from a clean level."""
    import pvp_heist
    import sightlines
    from spec_loader import spec_from_dict
    # `_spawn_los` only compares SAME-STOREY pairs, and the reference spec
    # has attackers on 0/2 and its defender on 1 -- so `_occluders` is never
    # reached on it. Put both sides on one storey first, or this test would
    # pass for the wrong reason (no call, no outage, no finding).
    with open(REF, "r", encoding="utf-8") as f:
        d = json.load(f)
    atk = next(m for m in d["markers"] if m["type"] == "attacker_spawn")
    d["markers"].append({"type": "defender_spawn", "id": "LOS",
                         "x": atk["x"] + 1.0, "y": atk["y"],
                         "z": atk.get("z", 0)})
    def boom(*a, **k):
        raise RuntimeError("simulated outage")
    monkeypatch.setattr(sightlines, "_occluders", boom)
    errors, _, _ = pvp_heist.check(spec_from_dict(d))
    codes = {e.split(":", 1)[0] for e in errors}
    assert "PVP-SPAWN-LOS-UNAVAILABLE" in codes


def test_sightlines_check_returns_a_tuple_not_a_mapping():
    """combat_audit called `sightlines.check(spec).get("warnings")`. `check`
    returns `(ok, lines)`, so that raised AttributeError on a tuple every
    time, into a bare `except: pass`. Pin the shape so the next caller reads
    it correctly -- or fails here rather than in silence."""
    import sightlines
    got = sightlines.check(_ref_spec())
    assert isinstance(got, tuple) and len(got) == 2
    ok, lines = got
    assert ok is True
    assert not hasattr(got, "get")


def test_analyze_exposes_intent_mismatch_as_structure():
    """The data combat_audit should have been reading all along: a per-room
    verdict, not a phrase to grep out of report() text."""
    import sightlines
    rooms = [r for s in sightlines.analyze(_ref_spec()) for r in s["rooms"]]
    assert rooms, "no rooms analysed"
    for r in rooms:
        assert {"id", "authored", "computed", "mismatch"} <= set(r)
    assert any(r["mismatch"] for r in rooms), \
        "the reference spec has known authored-vs-plays mismatches"
