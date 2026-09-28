"""0.149.0 -- a store's aisles are Zoo 1.13.0's snack gondolas."""
import glob
import json
import os

import migrate_store_gondolas as M
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))


def _specs():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            yield os.path.basename(p), json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue


def test_every_store_aisle_is_a_snack_gondola():
    assert M.main(["--check"]) == 0, "run: python migrate_store_gondolas.py"
    stores = 0
    for name, d in _specs():
        names = [v.get("name", "") for v in d.get("volumes") or []]
        if "register_counter" not in names:
            continue
        stores += 1
        aisles = [n for n in names if prop_species.species_for_name(n) == "snack_gondola"]
        assert aisles, name
    assert stores == 9


def test_the_supermarkets_and_the_pharmacy_are_left_alone():
    for name in ("supermarket_a01", "supermarket_a03"):
        d = json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))
        assert any(v["name"].startswith("aisle_") for v in d["volumes"]), name
    assert prop_species.species_for_name("gondola_a") is None
    assert prop_species.species_for_name("aisle_1") is None


def test_milk_crates_route_to_their_species_not_a_box():
    assert prop_species.species_for_name("milk_crates_r6af9550a_4") == "milk_crate_stack"
    assert prop_species.species_for_name("crate_stack") is None
