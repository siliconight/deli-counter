"""The stair underside toggle (the walker, 2026-09-13): "Stairs being solid
should be the new default, and for gameplay reasons having that be a toggle
we flip on and off if we want more sightlines would be interesting."

One resolver, `stairwell.stair_underside`, at three levels -- stair, building,
build -- defaulting to solid. The builder builds its answer and gameplay.json
reports it, so these tests are the contract for both.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stairwell   # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402


def _spec(**top):
    d = {"name": "u", "footprint_x": 20.0, "footprint_y": 14.0,
         "story_height": 3.0, "n_stories": 2,
         "stairs": [{"id": "s0", "x": 0.0, "y": 0.0, "from_story": 0,
                     "to_story": 1, "run": 4.0, "style": "straight"}]}
    d.update(top)
    return spec_from_dict(d)


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("DC_STAIR_UNDERSIDES", raising=False)


def test_solid_is_the_default():
    sp = _spec()
    assert sp.stairs[0].open_under is None
    assert stairwell.stair_underside(sp, sp.stairs[0]) == "solid"


def test_the_building_flips_every_stair_it_has():
    sp = _spec(stair_undersides="open")
    assert stairwell.stair_underside(sp, sp.stairs[0]) == "open"


def test_a_stair_overrides_its_building_both_ways():
    sp = _spec(stair_undersides="open")
    sp.stairs[0].open_under = False
    assert stairwell.stair_underside(sp, sp.stairs[0]) == "solid"
    sp = _spec(stair_undersides="solid")
    sp.stairs[0].open_under = True
    assert stairwell.stair_underside(sp, sp.stairs[0]) == "open"


def test_the_build_env_flips_a_library_but_not_a_spec_that_chose(monkeypatch):
    monkeypatch.setenv("DC_STAIR_UNDERSIDES", "open")
    sp = _spec()
    assert stairwell.stair_underside(sp, sp.stairs[0]) == "open"
    sp = _spec(stair_undersides="solid")
    assert stairwell.stair_underside(sp, sp.stairs[0]) == "solid"


def test_a_typo_is_refused_rather_than_read_as_the_default(monkeypatch):
    with pytest.raises(ValueError):
        sp = _spec(stair_undersides="hollow")
        stairwell.stair_underside(sp, sp.stairs[0])
    monkeypatch.setenv("DC_STAIR_UNDERSIDES", "opne")
    sp = _spec()
    with pytest.raises(ValueError):
        stairwell.stair_underside(sp, sp.stairs[0])


def test_gameplay_json_reports_what_was_built():
    sp = _spec(stair_undersides="open")
    (entry,) = stairwell.derive(sp)
    assert entry["underside"] == "open"
    (entry,) = stairwell.derive(_spec())
    assert entry["underside"] == "solid"
