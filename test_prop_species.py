"""The species hint a placement's name carries (prop_species.py) and the stem
that names it (themed_tscn.py). Roadmap 44."""

import os

import prop_species
import themed_tscn


def test_the_hospital_and_bank_names_route_where_they_say():
    f = prop_species.species_for_name
    assert f("teller_counter") == "teller_line"          # the glass barrier over the counter; a low one falls to counter in Zoo
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
    # DC_ZOO_ROOT first, as `test_furnish` reads it: a worktree's `../zoo` is
    # whatever happens to sit beside it (0.136.0 read an unrelated copy)
    root = os.environ.get("DC_ZOO_ROOT") or os.path.join(here, "..", "zoo")
    genomes = os.path.join(root, "zoo_keeper", "genome", "species")
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


# ---------------------------------------------------------------------------
# 0.131.0 -- the interior species (Zoo 0.84.0) and the slot's dressing fields
# ---------------------------------------------------------------------------

import importlib  # noqa: E402
import sys        # noqa: E402
import types      # noqa: E402

import pytest     # noqa: E402


def test_the_interior_species_claim_their_names_ahead_of_the_rows_that_would():
    f = prop_species.species_for_name
    assert f("box_stack") == "carton_stack"               # not the box row's `stack`
    assert f("cartons_r1234abcd_2") == "carton_stack"     # not the box row's `cart`
    assert f("bankers_boxes") == "carton_stack"
    assert f("dust_sheet_r1234abcd_3") == "dust_sheet"    # not chair or table
    assert f("draped_table") == "dust_sheet"
    assert f("pool_table_r1234abcd_1") == "pool_table"    # not table
    assert f("booth_seating_a") == "booth_seat"           # not the chair row's `seat`
    assert f("apartment_sofa_cover") == "booth_seat"
    assert f("water_heater_r1234abcd_2") == "furnace"
    assert f("boiler_tank") == "furnace"                  # not `tank`
    assert f("loading_pallet_stack") == "pallet_stack"    # not the box row
    assert f("barrel_wine_r1234abcd_4") == "water_barrel"
    assert f("litter_bin_r1234abcd_5") == "litter_bin"
    assert f("grill_r1234abcd_1") == "flat_top_grill"
    assert f("stanchion_r1234abcd_7") == "queue_stanchion"
    assert f("payphone") == "payphone"


def test_the_new_rows_steal_nothing_they_should_not():
    """A row placed higher than it needs to be takes names from the rows it
    jumps: `booth` at the top of the table took `booth_desk` from `desk`."""
    f = prop_species.species_for_name
    assert f("booth_desk") == "desk"
    assert f("broadcast_booth_desk") == "desk"
    assert f("cabinet_supply_r1234abcd_2") == "filing_cabinet"   # `bin` is not a keyword
    assert f("tool_bench") == "counter"
    assert f("crate_stack_security_room") is None
    assert f("VAULT") is None


@pytest.fixture
def dc(monkeypatch):
    """deli_counter against stub bpy/bmesh, as test_facade_glazing does."""
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def test_every_prop_slot_carries_the_dressing_fields(dc):
    """Zoo 0.84.0's list, item 1: `stock`, `variant`, `form` on every prop
    slot, None / 0 / None when unset -- a slot that says it has none."""
    import skin_style
    from spec_loader import spec_from_dict
    d = {"name": "dress", "footprint_x": 20, "footprint_y": 20, "volumes": [
        {"name": "desk_r1234abcd_1", "x": 0, "y": 0, "z": 0.375, "size_x": 1.6,
         "size_y": 0.8, "size_z": 0.75, "stock": "office", "variant": 2},
        {"name": "water_heater_r1234abcd_2", "x": 4, "y": 0, "z": 1.2,
         "size_x": 0.6, "size_y": 0.6, "size_z": 2.4, "form": "water_heater"},
        {"name": "crate_stack", "x": -4, "y": 0, "z": 0.5, "size_x": 1.0,
         "size_y": 1.0, "size_z": 1.0}]}
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    b._box = lambda *a, **k: None
    b._col_box = lambda *a, **k: None
    b._record_surface = lambda *a, **k: None
    b._volumes()
    got = {s["slot_id"]: (s["stock"], s["variant"], s["form"]) for s in b.slots}
    assert got == {"desk_r1234abcd_1": ("office", 2, None),
                   "water_heater_r1234abcd_2": (None, 0, "water_heater"),
                   "crate_stack": (None, 0, None)}
    stem, _ = themed_tscn.resolve_themed_stem(b.slots[0], "delco_1997", 1)
    assert stem.endswith("_w160_d80_h75_soffice_n2"), stem


# --- the cubicle bank (0.138.0 / Zoo 0.93.0) ---------------------------------

def test_a_cubicle_is_a_cubicle_bank_and_a_desk_is_still_a_desk():
    """The desk row held `cubicle` and the desk genome is wide enough and deep
    enough that an 8.0 x 6.0 x 1.2 m farm FIT it -- so it built as desk
    geometry at that size rather than falling back to a box. The walker, cold
    run 9060: "these desks are too close to each other?"."""
    f = prop_species.species_for_name
    assert f("cubicles_w_0") == "cubicle_bank"
    assert f("cubicles_e_2") == "cubicle_bank"
    assert f("workstation_bank_3") == "cubicle_bank"
    assert f("desk_manager_office") == "desk"
    assert f("desk_r1234abcd_1") == "desk"
    assert f("reception_desk") == "counter"       # the counter row still wins
    # the jump over the counter row takes nothing from it
    assert f("nurse_station_0") == "counter"
    assert f("counter_island_north_concourse") == "counter"
    assert f("tool_bench") == "counter"


def test_the_ten_library_cubicles_are_the_whole_re_route():
    """Every volume in the library whose name reaches the new row, measured --
    so the next reader knows what this table move touched and what it did not."""
    import glob
    import json
    here = os.path.dirname(os.path.abspath(__file__))
    hits = []
    for path in sorted(glob.glob(os.path.join(here, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        for v in spec.get("volumes") or []:
            if prop_species.species_for_name(v.get("name") or "") \
                    == "cubicle_bank":
                hits.append((os.path.basename(path)[:-5], v["name"],
                             v["size_x"], v["size_y"], v["size_z"],
                             v.get("material")))
    assert len(hits) == 10, hits
    assert {h[0] for h in hits} == {"office", "office_stepped"}, hits
    assert {(h[2], h[3], h[4]) for h in hits} == {(8.0, 6.0, 1.2)}, hits
    assert {h[5] for h in hits} == {"drywall"}, hits


def test_a_species_that_owns_its_collision_gets_no_greybox_box(dc):
    """The composer keeps the greybox COLLIDER and drops its visual, so for a
    volume that is mostly aisle the box is the only thing a body meets.
    Measured in cold run 9060's composed `office_stepped`:
    `cubicles_w_0_col-convcolonly` is one solid 8.00 x 6.00 x 1.20 box."""
    import skin_style
    from spec_loader import spec_from_dict
    assert prop_species.owns_collision("cubicle_bank")
    assert not prop_species.owns_collision("desk")
    assert not prop_species.owns_collision(None)
    d = {"name": "t", "footprint_x": 30, "footprint_y": 24, "n_stories": 1,
         "volumes": [
             {"name": "cubicles_w_0", "x": 0, "y": 0, "z": 0.6,
              "size_x": 8.0, "size_y": 6.0, "size_z": 1.2,
              "material": "drywall"},
             {"name": "desk_r1234abcd_1", "x": 8, "y": 0, "z": 0.375,
              "size_x": 1.6, "size_y": 0.8, "size_z": 0.75}]}
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    cols = []
    b._box = lambda *a, **k: None
    b._col_box = lambda name, *a, **k: cols.append(name)
    b._record_surface = lambda *a, **k: None
    b._volumes()
    assert cols == ["desk_r1234abcd_1_col"], cols
    fits = {s["slot_id"]: s["fit"]["collision"] for s in b.slots}
    assert fits == {"cubicles_w_0": "none",
                    "desk_r1234abcd_1": "convex"}, fits
