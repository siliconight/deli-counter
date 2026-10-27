"""A supermarket is furnished as one and stands a cooler wall (0.275.0) -- pure, no bpy.

The walker, 2026-10-26, walking seed 9205's supermarket: "far too dark in teh super market", and the comps after it --
"shiny floor, bright lights, isles, glowing freezer section, stacked high" (the factory's
docs/reference/GROCERY_STORE_COMPS.md). The library's three supermarkets stood no cooler, their sales floors took the
shop floor's recipe -- filing cabinets, vending, video poker -- and supermarket_a02 had no aisle at all.

FAILS ON 0.274.0: `is_supermarket_floor` does not exist, no supermarket stands a `cooler_run`, and supermarket_a02's
sales floor stands no gondola.

Run:  python -m pytest tests/test_supermarket_dress.py
"""
import json
import os
import re
import sys

import level_design as L

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "migrations"))
SHELLS = ("supermarket_a01", "supermarket_a02", "supermarket_a03")
#: What the shop floor's recipe stood on a supermarket's sales floor and the supermarket's does not.
NOT_A_SUPERMARKET = ("cabinet_file", "vending", "video_poker", "bar_stool", "counter_service", "poster_wall_store")


def _spec(stem):
    return json.load(open(os.path.join(HERE, "specs", stem + ".json"), encoding="utf-8"))


def _floor(d):
    return next(r for r in d["rooms"] if r["id"] == "sales_floor")


def _on(d, room):
    x0, y0, x1, y1 = room["bounds"]
    return [v for v in d["volumes"] if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1
            and -0.5 < v["z"] - v["size_z"] / 2.0 < 2.5]


def test_the_rule_names_a_supermarkets_selling_floor_only():
    assert L.is_supermarket_floor({"id": "sales_floor"}, "supermarket_a02")
    for rid in ("mezz_floor", "stockroom", "back_stock", "cash_office", "manager_suite", "receiving"):
        assert not L.is_supermarket_floor({"id": rid}, "supermarket_a02"), rid
    assert not L.is_supermarket_floor({"id": "sales_floor"}, "convenience_store_a01")
    assert L._room_kind({"id": "sales_floor", "story": 0}, "supermarket_a01") == "supermarket"
    assert L._room_kind({"id": "sales_floor", "story": 0}, "convenience_store_a01") == "shop_floor"


def test_every_supermarket_stands_a_cooler_wall_on_its_back_wall():
    """Opposite the storefront glass, facing into the sales floor, at least 16 m of it in two runs no longer than
    Zoo's `cooler_run` builds."""
    for stem in SHELLS:
        d = _spec(stem)
        room = _floor(d)
        coolers = [v for v in _on(d, room) if v["name"].startswith("cooler_run")]
        assert len(coolers) == 2, (stem, [v["name"] for v in coolers])
        assert sum(v["size_x"] for v in coolers) >= 16.0, stem
        for v in coolers:
            assert v["size_x"] <= 12.0 and v["size_y"] == 0.9, (stem, v)
            # the N wall, the room on its -y side: unturned, so its doors face -y, into the room
            assert abs(v["y"] + 0.45 - (room["bounds"][3] - 0.17)) < 1e-3 and "rot_z" not in v, (stem, v)


def test_a_supermarket_floor_is_shelving_not_an_office():
    for stem in SHELLS:
        d = _spec(stem)
        names = [v["name"] for v in _on(d, _floor(d))]
        assert not [n for n in names if n.startswith(NOT_A_SUPERMARKET)], (stem, names)
        assert sum(n.startswith("shelf_run") for n in names) >= 8, (stem, names)
        assert sum(n.startswith("gondola_") for n in names) >= 4, (stem, names)


def test_authored_aisles_take_no_rows_and_a_bare_floor_takes_long_runs():
    """supermarket_a01's five 14 m aisles are its rows; the first build of this recipe laid 3.6 m islands down the
    lanes between them. supermarket_a02 had none and lays runs of 7.2 m or more, below shelter."""
    d = _spec("supermarket_a01")
    assert not [v for v in _on(d, _floor(d)) if v["name"].startswith("gondola_run")]
    assert len(L.authored_aisles(d, _floor(d))) == 5
    d = _spec("supermarket_a02")
    runs = [v for v in _on(d, _floor(d)) if v["name"].startswith("gondola_run")]
    assert len(runs) >= 6, len(runs)
    for v in runs:
        assert max(v["size_x"], v["size_y"]) >= 7.2 and v["size_z"] < L.shelter_height(), v


def test_the_migration_is_done_and_idempotent(tmp_path):
    import migrate_supermarket_cooler as M
    for stem in SHELLS:
        (tmp_path / (stem + ".json")).write_text(json.dumps(_spec(stem)), encoding="utf-8")
    assert M.main(["--check", "--dir", str(tmp_path)]) == 0


def test_every_name_routes():
    import prop_species
    assert prop_species.species_for_name("gondola_run_r48016798_14") == "snack_gondola"
    assert prop_species.species_for_name("cooler_run_sales_0") == "cooler_run"
