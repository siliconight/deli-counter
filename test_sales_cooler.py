"""Every store sells its cold drinks where a shopper stands (0.161.0).

The walker, 2026-09-29: "there should be fridges of cold sodas, beer, milk,
etc, with glowing lights too". Four of the nine stores had no cooler on the
sales floor -- gas_station_a02 and fuel_stop_heist only the walk-in's short
side in the food-service room, gas_station_a03 and stop_n_go none at all.
`migrate_cooler_wall.plan_sales_cooler` gives each its wall.
"""
import copy
import json
import os

import migrate_cooler_wall as M
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
STORES = ("cr_gas", "fuel_stop_heist", "gas_station", "gas_station_a01", "gas_station_a02",
          "gas_station_a03", "gas_street", "gs_corner_station", "stop_n_go")


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _coolers(spec):
    return [v for v in spec["volumes"] if str(v["name"]).startswith(M.NAME)]


def test_every_store_has_a_cooler_on_its_sales_floor():
    for name in STORES:
        spec = _spec(name)
        assert any(M._on_sales_floor(spec, v) for v in _coolers(spec)), name


def test_the_sales_cooler_routes_to_the_cooler_species():
    assert prop_species.species_for_name(M.SALES_NAME) == "cooler_run"


def test_the_sales_cooler_is_never_on_the_storefront_or_a_glazed_wall():
    for name in STORES:
        spec = _spec(name)
        for v in _coolers(spec):
            if v["name"] != M.SALES_NAME:
                continue
            glazed = {w["wall"] for w in spec["ext_walls"] if int(w.get("story", 0) or 0) == 0
                      and (w.get("material") == "storefront_glass"
                           or any(o.get("kind") == "window" for o in w.get("openings") or []))}
            room = next(r for r in spec["rooms"] if r["id"] == M.SALES_ROOM)
            for axis, line, lo, hi, sign, ops, ext in M._edge_walls(spec, room["bounds"]):
                on_it = (abs(v["y"] - (line + sign * (M.WALL_BACK + M.DEPTH / 2.0))) < 1e-3 if axis == "X"
                         else abs(v["x"] - (line + sign * (M.WALL_BACK + M.DEPTH / 2.0))) < 1e-3)
                if on_it:
                    assert ext not in glazed, (name, ext)
            assert max(v["size_x"], v["size_y"]) <= M.SALES_RUN + 1e-9


def test_the_migration_is_done_and_places_nothing_twice():
    for name in STORES:
        spec = _spec(name)
        coolers = _coolers(spec)
        assert len([v for v in coolers if v["name"] == M.SALES_NAME]) <= 1, name


def test_a_store_without_a_sales_cooler_gets_one_and_its_doors_stay_clear():
    spec = _spec("gas_station_a02")
    bare = copy.deepcopy(spec)
    bare["volumes"] = [v for v in bare["volumes"] if v["name"] != M.SALES_NAME]
    vol, why = M.plan_sales_cooler(bare)
    assert vol is not None, why
    assert vol == next(v for v in spec["volumes"] if v["name"] == M.SALES_NAME)
    # a02's back partition has doors at x = -11.0 and 0.0 inside the sales floor
    a, b = vol["x"] - vol["size_x"] / 2.0, vol["x"] + vol["size_x"] / 2.0
    for c, w in ((-11.0, 1.25), (0.0, 1.4)):
        assert b <= c - w / 2.0 - M.DOOR_CLEAR + 1e-6 or a >= c + w / 2.0 + M.DOOR_CLEAR - 1e-6


def test_every_built_store_carries_its_sales_cooler_as_a_cooler_slot():
    for name in ("fuel_stop_heist", "gas_station_a02", "gas_station_a03", "stop_n_go"):
        slots = json.load(open(os.path.join(BUILD, name + ".slots.json"), encoding="utf-8"))["slots"]
        got = [s for s in slots if s.get("species") == "cooler_run" and "sales" in s["slot_id"]]
        assert len(got) == 1, (name, len(got))
