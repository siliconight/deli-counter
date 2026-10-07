"""The nav gate asks whether an entrance reaches each stair (0.196.0).

A stair whose two ends join is a stair, not a route. deli_a01's up-stair
passed the gate in every build -- both ends on one island, navigable "yes" --
while two crate stacks cut its foot off from the stairwell's door and its
whole upper storey with it (cold runs 9187 and 9188; Deli Counter 0.195.0;
`docs/findings/deli_a01_upper_storey_9188/` at the factory root).

The gate now snaps each storey-0 exterior door and garage ENTRY_IN m inside
its wall and reports, per stair, whether either end is on an island an
entrance is on. Run on the shipped deli_a01 it reads "stairs an entrance
reaches: 1/2 -- no entrance reaches stair deli_stair_up"; on 0.195.0's, 2/2.
Reported, not gated: the stair verdict and the exit code are unchanged, and
test_navgate_population freezes the library's set.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nav_gate                      # noqa: E402

GD = os.path.join(HERE, "godot", "addon", "deli_counter", "nav_gate.gd")


def _src():
    with open(GD, encoding="utf-8") as fh:
        return fh.read()


def test_the_gate_snaps_each_storey0_door_a_step_inside():
    src = _src()
    assert "const ENTRY_IN := 1.0" in src
    assert "func _entry_points(gp: Variant) -> Array:" in src
    assert 'wall.begins_with("ext_0_")' in src
    assert 'kind in ["door", "garage"]' in src


def test_each_stair_reports_from_entry_and_the_result_carries_the_set():
    src = _src()
    assert 'rep["from_entry"]' in src
    assert '"stairs_unreached": unreached' in src
    # reported, not gated: nothing about entrances touches `failures`
    block = src[src.index("var judged := 0"):src.index("# -- markers: the documented F5 check")]
    assert "failures" not in block and "_exit_code" not in block


def _result(**kw):
    r = {"exit_code": 0, "stairs_ok": True, "navmesh_polys": 10,
         "stairs": [{"id": "up", "status": "ok", "detail": "", "from_entry": False},
                    {"id": "down", "status": "ok", "detail": "", "from_entry": True}],
         "entries": {"points": [{"tag": "front", "island": 0},
                                {"tag": "alley", "island": 0}],
                     "snapped": 2, "stairs_judged": 2, "stairs_unreached": ["up"]},
         "markers": {}, "navigable": True}
    r.update(kw)
    return r


def test_the_verdict_names_a_stair_no_entrance_reaches():
    ok, lines = nav_gate.verdict(_result())
    assert ok                                   # the stair verdict is unchanged
    assert any("stairs an entrance reaches: 1/2" in ln for ln in lines), lines
    assert any("no entrance reaches stair up" in ln for ln in lines), lines


def test_a_result_from_before_the_check_says_so():
    r = _result()
    del r["entries"]
    ok, lines = nav_gate.verdict(r)
    assert ok
    assert any(ln.startswith("entrances: UNJUDGED") for ln in lines), lines
