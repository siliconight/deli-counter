"""0.149.0 -- a store's aisles are Zoo 1.13.0's snack gondolas."""
import glob
import json
import os

import migrate_store_gondolas as M
import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _specs():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            yield os.path.basename(p), json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue


def test_every_store_aisle_is_a_snack_gondola():
    """The nine stores, and since 0.247.0 the six delis, whose counter is a
    `front_register_counter`: not one `aisle_N` or `aisle_shelf_N` left."""
    assert M.main(["--check"]) == 0, "run: python migrations/migrate_store_gondolas.py"
    stores = delis = 0
    for name, d in _specs():
        names = [v.get("name", "") for v in d.get("volumes") or []]
        if not M.is_store(names):
            continue
        stores += 1
        delis += "front_register_counter" in names
        aisles = [n for n in names if prop_species.species_for_name(n) == "snack_gondola"]
        assert aisles, name
        assert not [n for n in names if M._AISLE.fullmatch(n)], name
    assert (stores, delis) == (15, 6)


def test_the_pharmacy_is_left_alone():
    # the supermarkets were left alone here until 0.272.0 (`test_supermarket_gondolas.py`)
    assert prop_species.species_for_name("gondola_a") is None
    assert prop_species.species_for_name("aisle_1") is None


def test_milk_crates_route_to_their_species_not_a_box():
    assert prop_species.species_for_name("milk_crates_r6af9550a_4") == "milk_crate_stack"
    assert prop_species.species_for_name("crate_stack") is None
