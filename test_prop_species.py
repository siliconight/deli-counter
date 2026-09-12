"""The species hint a placement's name carries (prop_species.py) and the stem
that names it (themed_tscn.py). Roadmap 44."""

import os

import prop_species
import themed_tscn


def test_the_hospital_and_bank_names_route_where_they_say():
    f = prop_species.species_for_name
    assert f("teller_counter") == "counter"              # a waist-high counter, not the glass barrier
    assert f("tool_bench") == "counter"                  # a workbench, not a chair
    assert f("chair_row") == "chair"
    assert f("nurse_station_0") == "counter"
    assert f("lobby_reception") == "counter"
    assert f("counter_island_north_concourse") == "counter"
    assert f("desk_manager_office") == "desk"
    assert f("cabinet_manager_office") == "filing_cabinet"
    assert f("ARMORY_LOCKER") == "filing_cabinet"
    assert f("aisle_shelf") == "shelving"
    assert f("waiting_seats") == "chair"
    assert f("roof_unit_2") == "hvac_unit"


def test_boxes_by_nature_and_unknown_things_get_no_hint():
    f = prop_species.species_for_name
    assert f("crate_stack_security_room") is None
    assert f("col_0") is None
    assert f("supply_cart_0") is None
    assert f("pump_island") is None
    assert f("pump") == "pump"                        # minted 2026-09-12, zoo/tools/new_species.py
    assert f("VAULT") is None
    assert f("") is None
    assert f(None) is None


def test_every_species_in_the_table_is_a_real_zoo_species_name():
    """The table names Zoo genomes; a typo here is a silent box."""
    here = os.path.dirname(os.path.abspath(__file__))
    genomes = os.path.join(here, "..", "zoo", "zoo_keeper", "genome", "species")
    if not os.path.isdir(genomes):
        return
    known = {f[:-5] for f in os.listdir(genomes) if f.endswith(".json")}
    for _words, sp in prop_species.PROP_SPECIES:
        if sp is not None:
            assert sp in known, sp


def test_a_hinted_volume_is_recorded_long_side_first():
    """An aisle shelf authored 1.0 x 6.0 is a 6.0-wide run turned 90."""
    assert prop_species.long_axis_first((1.0, 6.0, 1.6)) == ([6.0, 1.0, 1.6], 90.0)
    assert prop_species.long_axis_first((6.0, 1.0, 1.6)) == ([6.0, 1.0, 1.6], 0.0)
    assert prop_species.long_axis_first((1.1, 1.1, 0.95)) == ([1.1, 1.1, 0.95], 0.0)


def _prop(dims, species):
    return {"slot_id": "x", "role": "prop", "size_mod": "full", "style": 2,
            "species": species, "fit": {"dims": list(dims), "pivot": "center"}}


def test_the_stem_carries_the_species_between_type_and_theme():
    assert themed_tscn.module_stem("prop", "delco", 2, 160, None, 80, None, None, 75,
                                   species="desk") == "prop_desk_delco_02_w160_d80_h75"
    assert themed_tscn.module_stem("prop", "delco", 2, 160, None, 80, None, None, 75) \
        == "prop_delco_02_w160_d80_h75"
    # a species equal to the type adds nothing
    assert themed_tscn.module_stem("prop", "delco", 2, 160, None, 80, None, None, 75,
                                   species="prop") == "prop_delco_02_w160_d80_h75"


def test_a_hinted_slot_resolves_to_the_species_stem():
    stem, scaled = themed_tscn.resolve_themed_stem(_prop((1.6, 0.8, 0.75), "desk"), "delco", 1)
    assert stem == "prop_desk_delco_02_w160_d80_h75" and not scaled
    stem, _ = themed_tscn.resolve_themed_stem(_prop((1.6, 0.8, 0.75), None), "delco", 1)
    assert stem == "prop_delco_02_w160_d80_h75"


def test_the_composer_falls_from_the_species_to_the_box(tmp_path):
    """Zoo builds the box when the species does not fit the slot; the
    composer must land on whichever module exists, never on greybox."""
    lib = str(tmp_path)
    slot = _prop((8.0, 0.8, 1.0), "teller_line")
    open(os.path.join(lib, "prop_delco_02_w800_d80_h100.glb"), "w").close()
    stem, _, fell = themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)
    assert stem == "prop_delco_02_w800_d80_h100" and not fell
    # the species module, once built, wins
    open(os.path.join(lib, "prop_teller_line_delco_02_w800_d80_h100.glb"), "w").close()
    stem, _, _ = themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)
    assert stem == "prop_teller_line_delco_02_w800_d80_h100"


def test_style_01_degrade_still_applies_to_each_in_turn(tmp_path):
    lib = str(tmp_path)
    slot = _prop((1.6, 0.8, 0.75), "desk")
    open(os.path.join(lib, "prop_delco_01_w160_d80_h75.glb"), "w").close()
    stem, _, fell = themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)
    assert stem == "prop_delco_01_w160_d80_h75" and fell
    open(os.path.join(lib, "prop_desk_delco_01_w160_d80_h75.glb"), "w").close()
    stem, _, fell = themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)
    assert stem == "prop_desk_delco_01_w160_d80_h75" and fell
