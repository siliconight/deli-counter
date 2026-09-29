"""A storefront-lit room's floor and ceiling ask for light-budget tiles (0.157.0).

The walker, 2026-09-29: "yes, narrow it to the storefront rooms". Zoo 1.23.0
shipped every floor and ceiling's 8 m tiles as their own meshes; it restored
gas_station_a02's sales floor and cost the library +7% draws. The slot
manifest now tags `light_budget_tiles` on the floor and ceiling of the rooms
lit from outside through storefront glass -- the rooms the spills are derived
for -- and Zoo (>= 1.24.0) splits only those, under `_lbt`.
"""
import glob
import json
import os
import sys

import pytest

import lights
import themed_tscn

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
ZOO = os.path.join(HERE, "..", "zoo")

SALES = {"id": "sales_floor", "story": 0, "center": [-4.5, -5.0, 0.0],
         "bounds": [-16.0, -11.0, 7.0, 1.0], "role": "public_entry"}
STOCK = {"id": "stockroom", "story": 0, "center": [0.5, 6.0, 0.0],
         "bounds": [-6.0, 1.0, 7.0, 11.0], "role": "fortifiable"}
SOUTH = [{"story": 0, "facing": "S", "x": -10.5 + 2.0 * i, "y": -11.0, "w": 2.0} for i in range(9)]


def test_the_rooms_the_glass_walls_are_lit_and_no_others():
    assert lights.storefront_lit_rooms([SALES, STOCK], SOUTH, 0.3) == {"sales_floor"}
    assert lights.storefront_lit_rooms([SALES], [], 0.3) == set()
    vault = dict(SALES, id="vault", role="objective_room", objective=True)
    assert lights.storefront_lit_rooms([vault], SOUTH, 0.3) == set()          # bulbs
    assert lights.storefront_lit_rooms([SALES], SOUTH, 0.3, {"sales_floor"}) == set()  # club


def _slot(budget):
    s = {"slot_id": "floor_sales_floor", "role": "floor", "size_mod": "full", "style": 11,
         "material": "carpet", "room": "sales_floor",
         "fit": {"dims": [23.0, 12.0, 0.02], "pivot": "center", "voids": []}}
    if budget:
        s["light_budget_tiles"] = True
    return s


def test_the_name_carries_the_flag_on_a_plate_and_falls_back_without_it(tmp_path):
    lit, _ = themed_tscn.resolve_themed_stem(_slot(True), "delco_1997", 1)
    plain, _ = themed_tscn.resolve_themed_stem(_slot(False), "delco_1997", 1)
    assert themed_tscn.LIGHT_BUDGET_STEM in lit and themed_tscn.LIGHT_BUDGET_STEM not in plain
    assert lit.replace(themed_tscn.LIGHT_BUDGET_STEM, "") == plain
    wall = {"slot_id": "w", "role": "wall", "size_mod": "full", "style": 2, "light_budget_tiles": True,
            "fit": {"dims": [2.0, 0.3, 3.9], "pivot": "center", "openings": []}}
    assert themed_tscn.LIGHT_BUDGET_STEM not in themed_tscn.resolve_themed_stem(wall, "delco_1997", 1)[0]
    # a library with only the plain floor resolves the flagged slot to it
    (tmp_path / (plain + ".glb")).write_bytes(b"")
    got = themed_tscn.resolve_slot_choice(_slot(True), "delco_1997", 1, str(tmp_path))[0]
    assert got == plain
    (tmp_path / (lit + ".glb")).write_bytes(b"")
    assert themed_tscn.resolve_slot_choice(_slot(True), "delco_1997", 1, str(tmp_path))[0] == lit


def test_the_mirror_matches_zoo():
    if not os.path.isdir(ZOO):
        pytest.skip("zoo is not beside this checkout")
    sys.path.insert(0, ZOO)
    try:
        from zoo_keeper.core import kit
    finally:
        sys.path.remove(ZOO)
    assert themed_tscn.LIGHT_BUDGET_STEM == kit.LIGHT_BUDGET_STEM
    assert tuple(themed_tscn.LIGHT_BUDGET_ROLES) == tuple(kit.LIGHT_BUDGET_ROLES)
    for flag in (True, False):
        a = themed_tscn.module_stem("floor", "delco_1997", 11, 2300, None, 1200, material="carpet",
                                    budget_tiles=flag)
        b = kit.module_stem("floor", "delco_1997", 11, 2300, None, 1200, material="carpet",
                            budget_tiles=flag)
        assert a == b


# --------------------------------------------------------------------------- #
# The shipped library (build.py --all)
# --------------------------------------------------------------------------- #

def test_the_gas_stations_sales_floor_plates_are_flagged():
    with open(os.path.join(BUILD, "gas_station_a02.slots.json"), encoding="utf-8") as f:
        slots = json.load(f)["slots"]
    flagged = {s["slot_id"] for s in slots if s.get("light_budget_tiles")}
    assert {"floor_sales_floor", "ceiling_sales_floor"} <= flagged


def test_the_flagged_rooms_are_the_rooms_that_spill_and_only_plates_carry_it():
    for p in glob.glob(os.path.join(BUILD, "*.slots.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        lp = p.replace(".slots.json", ".lights.json")
        if not os.path.exists(lp):
            continue
        with open(lp, encoding="utf-8") as f:
            spill = {a["room"] for a in json.load(f)["anchors"] if a["type"] == "storefront_spill"}
        flagged = [s for s in d["slots"] if s.get("light_budget_tiles")]
        assert all(s["role"] in ("floor", "ceiling") for s in flagged), d["building_id"]
        assert {s["room"] for s in flagged} <= spill, (d["building_id"], sorted({s["room"] for s in flagged} - spill))
        plates = {s["room"] for s in d["slots"] if s["role"] in ("floor", "ceiling") and s.get("room") in spill}
        assert {s["room"] for s in flagged} == plates, (d["building_id"], sorted(plates ^ {s["room"] for s in flagged}))
