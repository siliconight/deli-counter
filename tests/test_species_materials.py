"""A placed piece asks Zoo for a material its species is made of (0.284.0).

Zoo builds any known kind a slot names, and delco_1997's `metal` is street rust: the bank level's ATM was built in
rust, its cash cart, cameras, clock and planters in wood. FAILS ON 0.283.0, which has no `SPECIES_MATERIALS`.
"""
import json
import os

import pytest

import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")


def _zoo():
    from test_furnish import ZOO
    return ZOO


def test_every_routed_species_is_mirrored():
    routed = {sp for _w, sp in prop_species.PROP_SPECIES if sp}
    assert routed <= set(prop_species.SPECIES_MATERIALS), sorted(routed - set(prop_species.SPECIES_MATERIALS))


def test_the_mirror_is_zoos_genomes():
    zoo = _zoo()
    gdir = os.path.join(zoo, "zoo_keeper", "genome", "species")
    if not os.path.isdir(gdir):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % zoo)
    for sp, (default, options) in prop_species.SPECIES_MATERIALS.items():
        g = json.load(open(os.path.join(gdir, sp + ".json"), encoding="utf-8"))["materials"]
        assert (g["default"], tuple(g["options"])) == (default, tuple(options)), sp


def test_a_kind_the_species_offers_is_kept_and_any_other_is_its_own():
    assert prop_species.material_for("atm", "metal") == "metal_painted"
    assert prop_species.material_for("atm", "plastic") == "plastic"
    assert prop_species.material_for("security_camera", "wood") == "plastic"
    assert prop_species.material_for("teller_line", "wood") == "wood"
    # a box keeps what it asked for
    assert prop_species.material_for(None, "concrete") == "concrete"


def test_no_built_slot_asks_a_species_for_what_it_is_not_made_of():
    seen = 0
    for f in sorted(os.listdir(BUILD)):
        if not f.endswith(".slots.json"):
            continue
        d = json.load(open(os.path.join(BUILD, f), encoding="utf-8"))
        slots = d.get("slots", d) if isinstance(d, dict) else d
        for s in slots:
            row = prop_species.SPECIES_MATERIALS.get(s.get("species"))
            if s.get("role") != "prop" or row is None:
                continue
            assert s["material"] in row[1], (f, s["slot_id"], s["species"], s["material"])
            seen += 1
    assert seen > 1000, seen


def test_the_bank_level_bank_asks_for_its_pieces_own_kinds():
    path = os.path.join(BUILD, "bank_branch_a02.slots.json")
    if not os.path.isfile(path):
        pytest.skip("bank_branch_a02 is not built")
    d = json.load(open(path, encoding="utf-8"))
    slots = d.get("slots", d) if isinstance(d, dict) else d
    by = {}
    for s in slots:
        if s.get("species"):
            by.setdefault(s["species"], set()).add(s["material"])
    assert by["atm"] == {"metal_painted"}
    assert by["security_camera"] == {"plastic"}
    assert by["litter_bin"] == {"metal_painted"}
    assert by["teller_line"] == {"wood"}
