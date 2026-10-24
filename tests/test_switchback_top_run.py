"""A multi-storey switchback's top leg cuts only its own run, and its seam is guarded (0.225.0).

Cold run 9317's office, read by the drop-edge instrument (roadmap 173): the top leg arrives at storey 2 in the
west run; the east run holds leg 0, which tops out a storey below, and the cut at storey 2 spanned both runs --
a pit 6.67 m deep onto leg 0's foot, open on the plate's edge, the east rail's sideways opening and the seam
between the runs. Fails on 0.224.1 (the cut 4.0 m wide at storey 2; no seam guard).

Run: pytest -q test_switchback_top_run.py
"""
import stairwell as S
from spec_types import LevelSpec, Stairwell


def _switchback(to_story=2, facing="N", width=1.6):
    st = Stairwell(x=0.0, y=0.0, from_story=0, to_story=to_story, id="sb", width=width,
                   run=4.7, style="switchback", facing=facing)
    return LevelSpec(name="sb", n_stories=to_story + 1, story_height=3.6,
                     footprint_x=34, footprint_y=24, stairs=[st])


def _lateral(rect, facing):
    x0, y0, x1, y1 = rect
    return (x0, x1) if facing in ("N", "S") else (y0, y1)


def test_top_leg_cuts_only_its_run():
    sp = _switchback()
    st = sp.stairs[0]
    holes = S.slab_openings(sp)
    (r1,) = holes[1]
    assert abs(r1[0] + 2.0) < 1e-6 and abs(r1[2] - 2.0) < 1e-6      # storey 1: both runs and both margins
    (r2,) = holes[2]
    assert abs(r2[0] + 2.0) < 1e-6 and abs(r2[2] - 0.0) < 1e-6      # storey 2: the west run, its outer margin, the seam
    r_lo, r_hi = S.flight_run_lateral(st, 1)
    assert abs(r_hi - r2[2]) < 1e-6                                 # the rectangle meets the other run at the flight's edge
    assert abs(r2[3] - r2[1] - (4.7 + 0.3 + 0.8)) < 1e-6            # the travel extent is what it was


def test_three_legs_top_leg_in_the_east_run():
    sp = _switchback(to_story=3)
    holes = S.slab_openings(sp)
    (r3,) = holes[3]
    assert abs(r3[0] - 0.0) < 1e-6 and abs(r3[2] - 2.0) < 1e-6      # leg 2 climbs in the east run
    (r2,) = holes[2]
    assert abs(r2[0] + 2.0) < 1e-6 and abs(r2[2] - 2.0) < 1e-6      # an intermediate leg keeps both runs


def test_facing_east_turns_the_seam_with_the_stair():
    sp = _switchback(facing="E")
    (r2,) = S.slab_openings(sp)[2]
    lo, hi = _lateral(r2, "E")
    assert abs(hi - lo - 2.0) < 1e-6
    assert min(abs(lo), abs(hi)) < 1e-6                             # one lateral edge is the seam at the stair's own line


def test_seam_guards():
    sp = _switchback()
    st = sp.stairs[0]
    g = S.stair_guards(sp)
    seam_pos = S.SIDE_GAP + S.GUARD_THICK / 2.0
    sides = [p for p in g if p["kind"] == "side" and p["story"] == 1 and abs(p["pos"] - seam_pos) < 1e-6]
    assert len(sides) == 1, [p for p in g if p["story"] == 1]
    p = sides[0]
    assert "thick" not in p                                          # thin, like a narrow flight's guard
    land = S.flight_solid_end(st, sp.story_height, 0)[1]
    assert abs(p["lo"] + 3.15) < 1e-6                                # from the rectangle's far end
    assert abs(p["hi"] - (land - S.SIDE_GAP)) < 1e-6                 # to the turn landing: no sideways opening
    # ITS UNDERSIDE IS A BODY'S HEIGHT ABOVE THE FLOOR, so the flight below keeps its headroom under it
    import agent_contract
    H = sp.story_height
    assert abs(p["z_lo"] - (H + agent_contract.body_height())) < 1e-6
    assert p["z_lo"] < 2 * H                                           # and there is wall left under the slab
    rails = [p for p in g if p["kind"] == "rail" and p["story"] == 2 and abs(p["pos"] - seam_pos) < 1e-6]
    assert len(rails) == 1
    assert not [p for p in g if p["story"] == 2 and p["axis"] == "Y" and p["pos"] > 0.2]   # nothing over the other run
    end = [p for p in g if p["kind"] == "rail" and p["story"] == 2 and p["axis"] == "X"]
    assert len(end) == 1 and abs(end[0]["lo"] + 2.1) < 1e-6 and abs(end[0]["hi"] - 0.1) < 1e-6
    outer = [p for p in g if p["kind"] == "side" and p["story"] == 1 and p["pos"] < -1.0]
    assert len(outer) == 1 and abs(outer[0]["thick"] - (S.SIDE_MARGIN - S.SIDE_GAP)) < 1e-6   # the outer wall as before


def test_single_run_and_straight_unchanged():
    one = _switchback(to_story=1).stairs[0]
    assert S.hole_span(one, 0) == S.hole_span(one)
    straight = Stairwell(x=0.0, y=0.0, from_story=0, to_story=3, id="st", width=1.2, run=4.0, style="straight")
    for s in range(3):
        assert S.hole_span(straight, s) == S.hole_span(straight)
    g = S.stair_guards(_switchback(to_story=1))
    assert all(abs(abs(p["pos"]) - (S.SIDE_GAP + S.GUARD_THICK / 2.0)) > 1e-6 for p in g)   # no seam piece
