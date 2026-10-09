"""An Empty's roof: a TV antenna, and the odd satellite dish (0.185.0).

Authored per house on the spec (`roof_antenna`, `roof_dish`), as its door
is. `roofs.roof_fixtures` puts them on the roof slot with `front`, the facing
of the wall that holds the front door, for Patina (>= 0.29.0) to order and
Zoo (>= 1.74.0) to build.
"""
import json
import os

import pytest

import presets
import roofs
from spec_types import ExtWall, LevelSpec, Opening

HERE = os.path.dirname(os.path.abspath(__file__))


def _spec(**kw):
    walls = [ExtWall(wall="S", story=0, openings=[Opening(kind="door", tag="front_door")]),
             ExtWall(wall="N", story=0, openings=[Opening(kind="door", tag="back_door")])]
    base = dict(name="t", footprint_x=6.0, footprint_y=12.0, roof_mode="footprint",
                facade=True, ext_walls=walls)
    base.update(kw)
    return LevelSpec(**base)


def _roof(sp):
    (s,) = roofs.roof_slots(sp, story=3, cz=9.15, ft=0.3)
    return s


def test_an_empty_s_roof_slot_carries_its_fixtures_and_its_front():
    """FAILS ON 0.184.0: the roof slot carried neither."""
    s = _roof(_spec(roof_antenna=True, roof_dish=True))
    assert (s.get("antenna"), s.get("dish"), s.get("front")) == (True, True, "S")


def test_the_front_is_the_wall_with_the_front_door_not_a_fixed_side():
    walls = [ExtWall(wall="E", story=0, openings=[Opening(kind="door", tag="front_door")])]
    assert _roof(_spec(roof_antenna=True, ext_walls=walls))["front"] == "E"


def test_a_roof_without_them_is_unchanged():
    assert not {"antenna", "dish", "front"} & set(_roof(_spec()))


def test_asked_for_with_no_front_door_or_on_a_real_building_refuses():
    """A fixture that quietly did not appear is a check that cannot fail."""
    with pytest.raises(ValueError):
        _roof(_spec(roof_antenna=True, ext_walls=[]))
    with pytest.raises(ValueError):
        _roof(_spec(roof_dish=True, facade=False))


def test_the_family_has_antennas_on_two_and_a_dish_on_one():
    """FAILS ON 0.204.0. The walker, 2026-10-09: "far too many Sattelite/Attena
    that makes the rowhomes look a little too uniform and computer generated.
    perhaps 30% as many?" 0.185.0's eight antennas and two dishes, cut to
    three (0.204.1)."""
    rows = list(presets.EMPTY_ROWHOMES.values())
    assert sum(1 for a in rows if a.get("antenna")) == 2
    assert sum(1 for a in rows if a.get("dish")) == 1
    assert sum(1 for a in rows if not (a.get("antenna") or a.get("dish"))) == 9


def test_every_built_rowhome_s_roof_carries_what_its_preset_asked_for():
    """The built half: fails until `build.py --all` has run on 0.185.0."""
    for name, args in presets.EMPTY_ROWHOMES.items():
        with open(os.path.join(HERE, "build", name + ".slots.json"), encoding="utf-8") as f:
            (roof,) = [s for s in json.load(f)["slots"] if s["role"] == "roof"]
        assert roof.get("antenna", False) == bool(args.get("antenna")), name
        assert roof.get("dish", False) == bool(args.get("dish")), name
        if args.get("antenna") or args.get("dish"):
            assert roof["front"] == "S", name
