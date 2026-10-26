"""0.272.0 -- a supermarket's aisles are gondolas too (the factory's docs/findings/walk_2026-10-26_panel/, L4, L3).

The walker read seed 9205's supermarket as "far too dark" and "doesn't look finished": its sales floor was five 14 m
dark boxes. They fit Zoo's `snack_gondola`, so they are routed to it. FAILS ON 0.271.0.
"""
import json
import os

import migrate_supermarket_gondolas as M
import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_supermarket_aisle_is_a_gondola():
    assert M.main(["--check"]) == 0, "run: python migrations/migrate_supermarket_gondolas.py"
    for name, n in (("supermarket_a01", 5), ("supermarket_a03", 4)):
        d = json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))
        names = [v["name"] for v in d["volumes"]]
        assert not [x for x in names if M._AISLE.fullmatch(x)], name
        gondolas = [x for x in names if prop_species.species_for_name(x) == "snack_gondola"]
        assert len(gondolas) == n, (name, gondolas)


def test_they_fit_the_species():
    zoo = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")
    path = os.path.join(zoo, "zoo_keeper", "genome", "species", "snack_gondola.json")
    if not os.path.isfile(path):
        import pytest
        pytest.skip("zoo is not beside this checkout (set DC_ZOO_ROOT)")
    dims = json.load(open(path, encoding="utf-8"))["dimensions"]
    checked = 0
    for name in ("supermarket_a01", "supermarket_a03"):
        d = json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))
        for v in d["volumes"]:
            if prop_species.species_for_name(v["name"]) != "snack_gondola":
                continue
            width, depth = max(v["size_x"], v["size_y"]), min(v["size_x"], v["size_y"])
            assert dims["width"]["min"] <= width <= dims["width"]["max"], (name, v["name"], width)
            assert dims["depth"]["min"] <= depth <= dims["depth"]["max"], (name, v["name"], depth)
            assert dims["height"]["min"] <= v["size_z"] <= dims["height"]["max"], (name, v["name"])
            checked += 1
    assert checked == 9          # every aisle, so this cannot pass by finding none
