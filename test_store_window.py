"""A store generated from the preset dresses its window and says what it is
(0.188.0).

The walker, 2026-10-06: the detail put into the Flappahs store must live in
the logic a level runs when it calls for a gas station or a convenience store,
not only in the library's specs. Every library store carried the window beer
sign and the sale posters (migrated in); 0 of 6 store specs generated from
`presets.gas_station` did. And the preset wrote no `preset`, so a generated
store's door sign read its kind off the mission id.

Run:  python -m pytest test_store_window.py -q
"""
import pytest

import level_design
import migrate_window_poster
import migrate_window_sign


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_a_generated_store_hangs_its_beer_sign_and_tapes_its_posters(mode):
    import presets
    spec = presets.gas_station(mode=mode)
    names = [v.get("name") for v in spec["volumes"]]
    assert names.count(migrate_window_sign.NAME) == 1
    assert names.count(migrate_window_poster.NAME) == 1


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_the_window_is_where_the_library_rule_puts_it(mode):
    """The preset calls the migrations' own rule, so running the migration
    over its spec changes nothing."""
    import presets
    spec = presets.gas_station(mode=mode)
    assert migrate_window_sign.migrate(spec) == (False, None)
    assert migrate_window_poster.migrate(spec) == (False, None)


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_a_generated_store_says_what_it_is_whatever_the_level_is_called(mode):
    import presets
    spec = presets.gas_station(name="lf_restaurant_row_001_9104", mode=mode)
    assert spec["preset"] == "gas_station"
    assert "gas_station" in level_design.club_building_id(spec)
