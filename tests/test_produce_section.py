"""A supermarket stands a produce section (0.277.0) -- pure, no bpy.

The walker's grocery comps, 2026-10-26 (the factory's docs/reference/GROCERY_STORE_COMPS.md): "a retro produce section
... neatly arranged fruit and vegetables", produce on tables under a sign. Zoo 1.132.0's `produce_table` is the table;
the supermarket recipe stands two of them as islands, the first pieces its floor takes.

FAILS ON 0.276.0: there is no `produce_table` piece and no supermarket stands one.

Run:  python -m pytest tests/test_produce_section.py
"""
import json
import os

import level_design as L
import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHELLS = ("supermarket_a01", "supermarket_a02", "supermarket_a03")


def _spec(stem):
    return json.load(open(os.path.join(HERE, "specs", stem + ".json"), encoding="utf-8"))


def _tables(d):
    room = next(r for r in d["rooms"] if r["id"] == "sales_floor")
    x0, y0, x1, y1 = room["bounds"]
    return [v for v in d["volumes"] if str(v["name"]).startswith("produce_table_")
            and x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1]


def test_the_recipe_stands_two_tables_first():
    r = L._RECIPES["supermarket"]
    assert r["anchors"] == ("produce_table", "produce_table") and r["all_anchors"]
    p = L._PIECES["produce_table"]
    assert p["where"] == "island" and L.variant_count(p) == 4
    for w, d, h in p["sizes"]:
        # below cover height: a shopper's island, never a wall across the floor
        assert h < L.cover_break_height(), (w, d, h)


def test_every_supermarket_stands_a_produce_section():
    for stem in SHELLS:
        tables = _tables(_spec(stem))
        assert 1 <= len(tables) <= 2, (stem, [v["name"] for v in tables])
        for v in tables:
            assert 0 <= int(v.get("variant", 0)) < 4, (stem, v)
            assert v["material"] in {m["id"] for m in _spec(stem)["materials"]}, (stem, v["material"])


def test_two_tables_in_a_store_carry_different_heaps():
    """The first build drew both tables' variant from the building's id; at four it is each table's name."""
    for stem in SHELLS:
        tables = _tables(_spec(stem))
        if len(tables) == 2:
            assert len({int(v.get("variant", 0)) for v in tables}) == 2, (stem, tables)


def test_a_table_routes_to_zoos_species():
    assert prop_species.species_for_name("produce_table_r48016798_3") == "produce_table"
    zoo = os.environ.get("DC_ZOO_ROOT") or os.path.join(HERE, "..", "zoo")
    g = os.path.join(zoo, "zoo_keeper", "genome", "species", "produce_table.json")
    if os.path.isfile(g):
        genome = json.load(open(g, encoding="utf-8"))
        assert genome["module_variants"] >= L.variant_count(L._PIECES["produce_table"])
        dims = genome["dimensions"]
        for w, d, h in L._PIECES["produce_table"]["sizes"]:
            assert dims["width"]["min"] <= w <= dims["width"]["max"]
            assert dims["depth"]["min"] <= d <= dims["depth"]["max"]
            assert dims["height"]["min"] <= h <= dims["height"]["max"]
