"""0.152.0 -- a convenience store has its roller grill.

`migrate_roller_grill.py` puts Zoo 1.17.0's `roller_grill` in every
convenience store by the slush machine's rule, generalised: against a solid
wall of the sales floor, clear of openings, facing the room, nearest the
REGISTER'S QUEUE rather than its centre, out of the clerk's aisle behind it,
and allowed beside another piece on the same wall. These hold for every
store, the slush stations did not move, the preset carries both, and the
built slots carry the species.
"""
import glob
import json
import os

import pytest

import level_design
import migrate_roller_grill as R
import migrate_slush_machine as S
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))
STORES = ("cr_gas", "fuel_stop_heist", "gas_station", "gas_station_a01", "gas_station_a02",
          "gas_station_a03", "gas_street", "gs_corner_station", "stop_n_go")


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _box(v):
    return (v["x"] - v["size_x"] / 2, v["y"] - v["size_y"] / 2, v["x"] + v["size_x"] / 2, v["y"] + v["size_y"] / 2)


def test_every_store_has_one_grill_and_it_routes():
    assert R.main(["--check"]) == 0, "run: python migrate_roller_grill.py"
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        n = sum(1 for v in d.get("volumes") or [] if v.get("name") == R.NAME)
        assert n == (1 if name in STORES else 0), (name, n)
    assert prop_species.species_for_name("roller_grill") == "roller_grill"
    assert prop_species.species_for_name("grill_rae0246ea_1") == "flat_top_grill"


def test_the_grill_is_zoos_size():
    """Zoo's `roller_grill_forms.DC_SIZES[0]`, a literal copy."""
    assert (R.WIDTH, R.DEPTH, R.HEIGHT) == (1.0, 0.6, 1.4)


def test_no_grill_stands_in_the_clerks_aisle_or_behind_the_till():
    """MEASURED before the staff-side rule: gas_station_a03's and stop_n_go's
    grills stood 1.29 m behind the register on the back partition."""
    for name in STORES:
        d = _load(name)
        reg = next(v for v in d["volumes"] if v["name"] == "register_counter")
        g = next(v for v in d["volumes"] if v["name"] == R.NAME)
        fx, fy = S._front(reg)
        rx0, ry0, rx1, ry1 = _box(reg)
        gx0, gy0, gx1, gy1 = _box(g)
        if fy:      # the staff side is behind the counter, across its length
            behind = (gy0 >= ry1) if fy < 0 else (gy1 <= ry0)
            overlaps = gx1 > rx0 - level_design.island_aisle_width() and gx0 < rx1 + level_design.island_aisle_width()
        else:
            behind = (gx0 >= rx1) if fx < 0 else (gx1 <= rx0)
            overlaps = gy1 > ry0 - level_design.island_aisle_width() and gy0 < ry1 + level_design.island_aisle_width()
        assert not (behind and overlaps), (name, _box(g), _box(reg))


def test_a_grill_may_stand_beside_a_piece_on_the_same_wall():
    """a02: beside the slush station on the food-service partition, not 10 m
    up it (MEASURED before the same-wall rule)."""
    d = _load("gas_station_a02")
    g = next(v for v in d["volumes"] if v["name"] == R.NAME)
    s = next(v for v in d["volumes"] if v["name"] == S.NAME)
    assert abs(g["x"] + g["size_x"] / 2 - (s["x"] + s["size_x"] / 2)) < 1e-6      # the same wall
    assert abs(g["y"] - s["y"]) < 2.0


def test_the_generalised_rule_did_not_move_a_slush_station():
    for name in STORES:
        d = _load(name)
        lib = next(v for v in d["volumes"] if v["name"] == S.NAME)
        d["volumes"] = [v for v in d["volumes"] if v["name"] not in (S.NAME, R.NAME)]
        assert S.plan_station(d)[0] == lib, name


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_the_preset_carries_the_grill_where_the_library_does(mode):
    import presets
    spec = presets.gas_station(mode=mode)
    v = [x for x in spec["volumes"] if x["name"] == R.NAME]
    lib = next(x for x in _load("gas_station")["volumes"] if x["name"] == R.NAME)
    assert v == [lib], (v, lib)


def test_the_built_slots_carry_the_species():
    for name in STORES:
        doc = json.load(open(os.path.join(HERE, "build", name + ".slots.json"), encoding="utf-8"))
        got = [s for s in doc["slots"] if str(s.get("slot_id", "")).startswith(R.NAME)]
        assert len(got) == 1 and got[0].get("species") == "roller_grill", (name, got)
