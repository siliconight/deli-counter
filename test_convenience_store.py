"""The Flappahs store as a family and a recipe of its own (0.188.0).

The walker, 2026-10-06: "a03 as convenience store; Flappahs store always
Flappahs". `gas_station_a03` stood no fuel and sat in the gas-station family,
so a gas-station brief drew a store without pumps on about half its candidates;
`convenience_store` had no recipe and was built as the forecourt station.

Run:  python -m pytest test_convenience_store.py -q
"""
import json
import os

import pytest

import migrate_slush_machine
import migrate_window_poster
import migrate_window_sign
import presets

HERE = os.path.dirname(os.path.abspath(__file__))
FORECOURT = ("forecourt_", "canopy_", "pump_island_", "pump_")


def _names(spec):
    return [str(v.get("name", "")) for v in spec["volumes"]]


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_a_convenience_store_is_the_shop_without_the_fuel(mode):
    spec = presets.convenience_store(mode=mode)
    names = _names(spec)
    assert not [n for n in names if n.startswith(FORECOURT)]
    assert "forecourt" not in {r["id"] for r in spec["rooms"]}
    assert migrate_slush_machine.is_store(spec)
    for want in ("cooler_run", "coffee_island", migrate_window_sign.NAME,
                 migrate_window_poster.NAME):
        assert want in names, want
    assert spec["preset"] == "convenience_store"


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_the_gas_station_keeps_its_forecourt(mode):
    names = _names(presets.gas_station(mode=mode))
    assert sum(1 for n in names if n.startswith("pump_") and not n.startswith("pump_island_")) == 6
    assert "canopy_roof" in names and "forecourt_pad" in names


def test_the_recipe_is_registered_and_builds_through_make():
    assert presets.REGISTRY["convenience_store"] is presets.convenience_store
    spec = presets.make("convenience_store")
    assert spec["preset"] == "convenience_store"
    assert not [n for n in _names(spec) if n.startswith(FORECOURT)]


def test_the_library_flappahs_store_is_its_own_family():
    """`gas_station_a03` until 0.188.0: the family is the id less its
    variant, so the name is the family."""
    path = os.path.join(HERE, "specs", "convenience_store_a01.json")
    with open(path, encoding="utf-8") as f:
        assert json.load(f)["name"] == "convenience_store_a01"
    assert not os.path.exists(os.path.join(HERE, "specs", "gas_station_a03.json"))
