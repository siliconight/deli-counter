"""Unit tests for the z-fight gate (zfight_gate.py) -- pure box geometry,
no bpy, no file I/O. These pin the rules that keep flickering packages from
ever shipping:

  - cohabitation (roof module in the slab's exact volume)      -> FLAGGED
  - same-facing cap in a shared plane (wall top vs slab top)   -> FLAGGED
  - the composer's 4mm sink on wall-family modules             -> clean
  - abutment (wall top meeting the ceiling above, max-vs-min)  -> clean
  - side-by-side tiles on one plane, no interpenetration       -> clean
  - sliver overlaps under the area threshold                   -> clean
"""
from zfight_gate import coplanar_fights, visible_fights, TOL, AREA_MIN


def _fights(boxes):
    """coplanar_fights stripped of internal bookkeeping keys."""
    return [{k: v for k, v in f.items() if not k.startswith("_")}
            for f in coplanar_fights(boxes)]


def _box(lo, hi):
    return (list(lo), list(hi))


def test_exact_cohabitation_is_flagged():
    # roof module occupying the top slab's volume: both min and max faces
    # shared on the vertical axis, full footprint -- the flickering ceiling.
    slab = ("slab_2", _box((-22, 7.7, -16), (22, 8.0, 16)))
    roof = ("roof_footprint", _box((-22, 7.7, -16), (22, 8.0, 16)))
    f = _fights([slab, roof])
    assert f, "cohabiting boxes must be flagged"
    vertical = [x for x in f if x["axis"] == 1]
    assert {x["side"] for x in vertical} == {"min", "max"}


def test_same_facing_cap_in_story_plane_is_flagged():
    # wall module runs through the slab band; its up-facing top cap shares
    # the story plane with the slab's up-facing top -> stripes on the floor.
    slab = ("slab_1", _box((-22, 3.7, -16), (22, 4.0, 16)))
    wall = ("wall_seg", _box((-1, 0.0, -0.175), (1, 4.0, 0.175)))
    f = _fights([slab, wall])
    assert any(x["axis"] == 1 and x["side"] == "max" for x in f)


def test_sunk_wall_cap_is_clean():
    # the composer sinks wall-family modules 4mm: top cap at 3.996 clears
    # the slab plane at 4.0 by more than the gate tolerance.
    slab = ("slab_1", _box((-22, 3.7, -16), (22, 4.0, 16)))
    wall = ("wall_seg", _box((-1, -0.004, -0.175), (1, 3.996, 0.175)))
    assert _fights([slab, wall]) == []
    assert 4.0 - 3.996 > TOL


def test_abutment_is_clean():
    # wall top meets ceiling bottom (max-vs-min): the normal way geometry
    # meets. Never a fight.
    wall = ("wall", _box((-1, 0.0, -0.175), (1, 3.7, 0.175)))
    slab = ("slab", _box((-22, 3.7, -16), (22, 4.0, 16)))
    assert _fights([wall, slab]) == []


def test_stacked_modules_abutting_are_clean():
    a = ("wall_s0", _box((-1, 0.0, -0.175), (1, 4.0, 0.175)))
    b = ("wall_s1", _box((-1, 4.0, -0.175), (1, 8.0, 0.175)))
    assert _fights([a, b]) == []


def test_side_by_side_same_plane_is_clean():
    # two floor tiles sharing the y=0.3 top plane but not interpenetrating.
    a = ("tile_a", _box((0, 0, 0), (2, 0.3, 2)))
    b = ("tile_b", _box((2, 0, 0), (4, 0.3, 2)))
    assert _fights([a, b]) == []


def test_sliver_under_area_threshold_is_clean():
    a = ("a", _box((0, 0, 0), (0.1, 1.0, 0.1)))
    b = ("b", _box((0.05, 0, 0.05), (0.15, 1.0, 0.15)))
    f = _fights([a, b])
    assert f == []
    assert 0.05 * 0.05 < AREA_MIN


def test_finding_reports_plane_and_area():
    slab = ("slab", _box((-22, 3.7, -16), (22, 4.0, 16)))
    wall = ("wall", _box((-1, 0.0, -0.35), (1, 4.0, 0.0)))
    f = _fights([slab, wall])
    top = [x for x in f if x["side"] == "max" and x["axis"] == 1][0]
    assert top["plane"] == 4.0
    assert abs(top["area"] - 2 * 0.35) < 1e-6


def test_buried_junction_caps_are_suppressed():
    # two co-sunk wall modules crossing inside the slab band: their coplanar
    # caps at 3.996 are entombed in the slab (3.7..4.0) -- suppressed.
    a = ("int_a", _box((-1, -0.004, -0.175), (1, 3.996, 0.175)))
    b = ("int_b", _box((-0.175, -0.004, -1), (0.175, 3.996, 1)))
    slab = ("slab", _box((-22, 3.7, -16), (22, 4.0, 16)))
    vis, buried = visible_fights([a, b, slab])
    caps = [f for f in buried if f["axis"] == 1 and f["side"] == "max"]
    assert caps and caps[0]["buried_in"] == "slab"
    assert not [f for f in vis if f["axis"] == 1 and f["side"] == "max"]


def test_exposed_cohabitation_is_not_suppressed():
    # the roof/slab sandwich has nothing covering it -- stays visible.
    slab = ("slab_2", _box((-22, 7.7, -16), (22, 8.0, 16)))
    roof = ("roof", _box((-22, 7.7, -16), (22, 8.0, 16)))
    vis, buried = visible_fights([slab, roof])
    assert vis and not buried


def test_partial_cover_does_not_suppress():
    # a third solid covering only half the shared region leaves it visible.
    slab = ("slab", _box((-22, 3.7, -16), (22, 4.0, 16)))
    wall = ("wall", _box((-1, 0.0, -0.35), (1, 4.0, 0.0)))
    half = ("cover", _box((-1, 3.9, -0.35), (0, 4.1, 0.0)))
    vis, buried = visible_fights([slab, wall, half])
    assert any(f["axis"] == 1 and f["side"] == "max" for f in vis)


def test_joint_cover_by_adjacent_segments_suppresses():
    # the burying wall is split into two segments exactly where the partition
    # lands -- together they entomb the end face; neither does alone.
    part = ("int_end", _box((-0.175, -4.0, 14.0), (0.175, 0.0, 16.0)))
    slab = ("slab_0", _box((-22, -0.3, -16), (22, 0.0, 16)))
    segA = ("ext_segA", _box((-2.0, -4.0, 15.825), (0.0, 0.0, 16.175)))
    segB = ("ext_segB", _box((0.0, -4.0, 15.825), (2.0, 0.0, 16.175)))
    vis, buried = visible_fights([part, slab, segA, segB])
    end = [f for f in buried if f["axis"] == 2]
    assert end, "jointly covered end face must be suppressed"
    assert not [f for f in vis if f["axis"] == 2]
