"""A supermarket hangs a numbered marker over each aisle (0.276.0) -- pure, no bpy.

The walker's grocery comps, 2026-10-26 (the factory's docs/reference/GROCERY_STORE_COMPS.md): a printed sign over the
head of every aisle, its number large and what is down it beside it. Zoo 1.131.0's `aisle_sign` form `grocery`
prints the number its variant gives; furnish hangs one over each lane between two lines of a supermarket's gondolas,
at the lane's storefront end (`level_design.aisle_markers`).

FAILS ON 0.275.0: `aisle_markers` does not exist and no supermarket hangs a marker.

Run:  python -m pytest tests/test_aisle_markers.py
"""
import json
import os

import agent_contract
import level_design as L

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHELLS = {"supermarket_a01": 4, "supermarket_a02": 3, "supermarket_a03": 3}


def _spec(stem):
    return json.load(open(os.path.join(HERE, "specs", stem + ".json"), encoding="utf-8"))


def _floor(d):
    return next(r for r in d["rooms"] if r["id"] == "sales_floor")


def _markers(d):
    return [v for v in d["volumes"] if str(v["name"]).startswith("aisle_sign_")]


def test_a01s_markers_hang_over_its_four_lanes_at_the_storefront_end():
    """Five 14 m aisles at x -14, -7, 0, 7, 14 (1.4 m deep) from y -11 to 3, the storefront glass on the south wall:
    four lanes, a marker over each at x -10.5, -3.5, 3.5, 10.5, 0.6 m in from the aisles' south end."""
    d = _spec("supermarket_a01")
    got = L.aisle_markers(d, _floor(d))
    assert [(round(x, 2), round(y, 2)) for x, y, _sx, _sy in got] == [(-10.5, -10.4), (-3.5, -10.4), (3.5, -10.4),
                                                                      (10.5, -10.4)]
    assert all((sx, sy) == (1.4, 0.06) for _x, _y, sx, sy in got)


def test_every_supermarket_hangs_its_markers_numbered_in_order():
    for stem, n in SHELLS.items():
        d = _spec(stem)
        ms = _markers(d)
        assert len(ms) == n, (stem, [v["name"] for v in ms])
        assert all(v.get("form") == "grocery" for v in ms), stem
        assert sorted(int(v.get("variant", 0)) for v in ms) == list(range(n)), stem


def test_a_marker_hangs_over_a_lane_with_a_bodys_headroom_under_it():
    sh_head = agent_contract.min_headroom()
    for stem in SHELLS:
        d = _spec(stem)
        room = _floor(d)
        floor = int(room.get("story", 0) or 0) * float(d.get("story_height", 3.5))
        gondolas = [v for v in d["volumes"] if str(v["name"]).startswith("gondola_")]
        for m in _markers(d):
            assert m["z"] - m["size_z"] / 2.0 - floor >= sh_head - 1e-6, (stem, m["name"], m["z"])
            for g in gondolas:
                inside = (abs(m["x"] - g["x"]) < g["size_x"] / 2.0 and abs(m["y"] - g["y"]) < g["size_y"] / 2.0)
                assert not inside, (stem, m["name"], g["name"])


def test_the_markers_reach_zoos_grocery_form():
    import prop_species
    assert prop_species.species_for_name("aisle_sign_r48016798_31") == "aisle_sign"
    zoo = os.environ.get("DC_ZOO_ROOT") or os.path.join(HERE, "..", "zoo")
    g = os.path.join(zoo, "zoo_keeper", "genome", "species", "aisle_sign.json")
    if os.path.isfile(g):
        genome = json.load(open(g, encoding="utf-8"))
        assert "grocery" in genome["params"]["form"] and genome["module_variants"] >= max(SHELLS.values())
