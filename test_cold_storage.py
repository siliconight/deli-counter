"""0.149.0 -- a walk-in cooler is cold storage, not a kitchen.

`cooler` and `walkin` sat in `level_design._ROOM_KINDS`'s kitchen row, so
every walk-in in the library was furnished with a grill, kitchen counters
and work tables (measured in six specs). They now furnish as `cold_storage`:
backstock racks, cartons, milk crates, pallets.
"""
import glob
import json
import os

import level_design as L
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))
KITCHEN = ("grill", "counter_kitchen", "table_work")


def _specs():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            yield os.path.basename(p), json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue


def test_a_walk_in_is_cold_storage_and_its_recipe_has_no_kitchen():
    for rid in ("walk_in_cooler", "walkin_cooler", "freezer", "beer_cooler"):
        assert L._room_kind({"id": rid}) == "cold_storage", rid
    r = L._RECIPES["cold_storage"]
    pieces = set(r["anchors"]) | set(r["wall"]) | set(r["floor"]) | {p for c in r["clusters"] for p in c[0]}
    assert not pieces & set(KITCHEN), pieces
    assert "milk_crates" in pieces and "shelf_run" in pieces
    # the rooms that stay what they were
    assert L._room_kind({"id": "food_service"}) == "kitchen"
    assert L._room_kind({"id": "kitchen"}) == "kitchen"
    assert L._room_kind({"id": "cold_storage"}) == "storage"


def test_no_walk_in_in_the_library_holds_a_grill():
    """Fails on 0.148.0's library: six walk-ins carried kitchen pieces."""
    walk_ins = 0
    for name, d in _specs():
        for room in d.get("rooms") or []:
            if L._room_kind(room, d.get("name")) != "cold_storage":
                continue
            walk_ins += 1
            tag = L._room_tag(room) if hasattr(L, "_room_tag") else None
            mine = [v["name"] for v in d["volumes"] if tag and ("_" + tag + "_") in v["name"] + "_"]
            bad = [n for n in mine if n.startswith(KITCHEN)]
            assert not bad, (name, room["id"], bad)
    assert walk_ins == 6, walk_ins


def test_milk_crates_are_zoo_s_crate_stack_in_plastic():
    """Not a grey box: `test_furnish` refuses a furnished piece that routes
    to no species, so Zoo 1.14.0 grew `milk_crate_stack` for it."""
    assert prop_species.species_for_name("milk_crates_r1234abcd_1") == "milk_crate_stack"
    spec = {"materials": []}
    assert L._prop_material(spec, "milk_crates_r1234abcd_1") == "plastic"
