"""0.273.0 -- a ramp's cut begins where a body clears the slab, and nothing stands in it (the factory's roadmap 270).

The walker, on seed 9205's parking garage, 2026-10-26: "i can't use this wide ramp to go up or down?". Every library
ramp's cut began at its middle, where the gap between the ramp and the slab above was 1.04 to 1.55 m against the
agent contract's 2.0. FAILS ON 0.272.0.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "migrations"))

import agent_contract  # noqa: E402
import migrate_ramp_cut as M  # noqa: E402
import stairwell  # noqa: E402


def _ramped():
    for p in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("ramps"):
            yield name, d


def _gap_at(d, r, t):
    """The gap between the ramp's top at `t` along its ascent and the underside of the slab it climbs to."""
    rise = float(d["story_height"]) * (r["to_story"] - r["from_story"])
    t_low = stairwell._ramp_ascent(r)[0]
    return rise - float(d.get("floor_thick", 0.0)) - rise * (t - t_low) / float(r.get("run", 8.0))


def test_every_library_ramp_cut_begins_where_a_body_clears_the_slab():
    hr = agent_contract.min_headroom()
    ramps = 0
    for name, d in _ramped():
        for r in d["ramps"]:
            if not r.get("cut_slabs", True) or r["to_story"] <= r["from_story"]:
                continue
            ramps += 1
            start = stairwell.ramp_cut_span(r, d)[0]
            assert _gap_at(d, r, start) >= hr - 1e-6, (name, round(_gap_at(d, r, start), 3))
            assert start <= stairwell.ramp_cut_span(r)[0] + 1e-9, name      # never later than the middle
    assert ramps == 9          # the nine library ramps roadmap 270 measured


def test_the_garage_the_walker_tried_opens_two_thirds_further_down():
    d = json.load(open(os.path.join(ROOT, "specs", "parking_garage.json"), encoding="utf-8"))
    r = d["ramps"][0]
    t_low = stairwell._ramp_ascent(r)[0]
    assert round(stairwell.ramp_cut_span(r)[0] - t_low, 3) == 5.0                    # where it began
    assert round(stairwell.ramp_cut_span(r, d)[0] - t_low, 3) == round(10.0 * 0.7 / 3.0, 3)  # 2.333 m up the ramp
    hole = stairwell.ramp_hole(r, d)
    assert hole[3 if r["axis"] == "Y" else 2] > stairwell.ramp_hole(r)[3 if r["axis"] == "Y" else 2]


def test_nothing_stands_in_a_ramps_cut_and_furnish_keeps_off_it():
    assert M.main(["--check"]) == 0, "run: python migrations/migrate_ramp_cut.py"
    for name, d in _ramped():
        assert M.in_cuts(d) == [], name


def test_the_authored_pieces_moved_by_the_least_distance():
    d = json.load(open(os.path.join(ROOT, "specs", "foundry_heist_vertical.json"), encoding="utf-8"))
    at = {v["name"]: v for v in d["volumes"]}
    assert at["forklift_cover"]["x"] == 10.6 and at["loading_crate_stack_a"]["x"] == 17.6
