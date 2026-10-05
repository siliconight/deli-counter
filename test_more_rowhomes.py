"""Twelve rowhome Empties, not six (0.184.0).

Cold run 9159's terrace placed 26 Empties from six variants -- one of them
seven times -- and `level_factory`'s `empties.terrace` picks a variant per
house at random, never the same as its neighbour. Every house the family adds
halves the repeats. The comp's rule (the factory root's
`docs/reference/EMPTIES_COMPS.md`): a terrace reads as HOUSES because each
one differs.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets   # noqa: E402

FAMILY = presets.EMPTY_ROWHOMES


def test_the_family_is_twelve_houses():
    """FAILS ON 0.183.0: six."""
    assert len(FAMILY) == 12
    assert len({a["seed"] for a in FAMILY.values()}) == 12


def test_no_two_houses_wear_the_same_wall_and_door():
    looks = [(a["wall"], a.get("door_finish")) for a in FAMILY.values()]
    assert len(set(looks)) == len(looks), looks


def test_no_wall_and_no_door_finish_more_than_twice():
    for key in ("wall", "door_finish"):
        counts = collections.Counter(a.get(key) for a in FAMILY.values())
        assert max(counts.values()) <= 2, (key, counts)


def test_the_row_still_has_one_vacant_house_and_a_few_iron_doors():
    assert sum(1 for a in FAMILY.values() if a.get("vacant")) == 1
    assert 2 <= sum(1 for a in FAMILY.values() if a.get("security_door")) <= 4


def test_widths_storeys_and_door_sides_vary():
    assert len({a["width"] for a in FAMILY.values()}) >= 6
    assert {a["floors"] for a in FAMILY.values()} == {2, 3}
    assert {a["door_side"] for a in FAMILY.values()} == {"W", "E"}
