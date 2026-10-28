"""The IP-name guard holds Deli Counter's own strings, not a designer's level name (0.287.1).

The factory's authoring panel names a level what the designer types; Level Factory writes its per-run spec as
`lf_<mission>_<seed>`, git-ignored and never shipped. A level named "Delco Ave" made `lf_delco_ave_001_9003`, and the
guard refused all three of its candidates. FAILS ON 0.287.0, which had no tests here at all.
"""
from types import SimpleNamespace

import guards


def _spec(name, room_id="office"):
    return SimpleNamespace(name=name, rooms=[SimpleNamespace(id=room_id, role="office")], markers=[], zones=[],
                           objectives=[], loot=[], ext_walls=[], partitions=[])


def test_a_designers_level_name_is_not_refused():
    for name in ("lf_delco_ave_001_9003", "lf_gabagool_heist_001_9104"):
        errors, _w = guards.check_ip_names(_spec(name))
        assert errors == [], (name, errors)


def test_a_library_specs_name_is_still_refused():
    errors, _w = guards.check_ip_names(_spec("delco_deli"))
    assert len(errors) == 1 and "'delco'" in errors[0]


def test_a_per_run_spec_is_held_to_the_guard_everywhere_but_its_name():
    errors, _w = guards.check_ip_names(_spec("lf_delco_ave_001_9003", room_id="gabagool_vault"))
    assert len(errors) == 1 and "room.id" in errors[0] and "'gabagool'" in errors[0]


def test_the_guard_still_matches_on_word_edges_only():
    assert guards.check_ip_names(_spec("delcourt_office"))[0] == []        # inside a longer word: not a brand use
    assert guards.check_ip_names(_spec("payday-vault"))[0]                  # bounded by a hyphen: a brand use
