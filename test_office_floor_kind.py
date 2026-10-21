"""An office building's open floor is an office, not a shop floor (0.248.0, the factory's roadmap 281).

`floor` is a shop-floor word, so the office preset's 816 m2 `floor_1` -- office's and office_stepped's open storey over
the bullpen -- was furnished with a service counter, vending machines, shelf runs and litter bins; cold run 9369's frame
of it showed the bins standing mid-floor among cartons. `level_design.is_office_floor` reads it on the card shop's
terms: a building whose id says `office`, a room the word table would make a shop floor by `floor` alone.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
#: The library's other rooms that are shop floors by `floor` alone, when 0.248.0 was written: a warehouse's, a depot's,
#: a foundry's, a brewery's, an arena's and a supermarket's mezzanine. They keep their kind.
OTHER_BARE_FLOORS = (
    ("arena_a01", "event_floor"), ("arena_a02", "event_floor"), ("arena_a03", "event_floor"),
    ("brewery_a01", "brew_floor"), ("depot_a02", "floor"), ("foundry_heist_vertical", "central_floor"),
    ("foundry_heist_vertical", "east_floor"), ("freight_terminal_a02", "south_floor"),
    ("large_warehouse_a02", "south_floor"), ("large_warehouse_a03", "main_floor"), ("setback_demo", "main_floor"),
    ("supermarket_a02", "mezz_floor"), ("warehouse_a02", "main_floor"),
)


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def test_an_office_building_s_floor_is_an_office():
    for b in ("office", "office_stepped", "lf_tower_007_3 office"):
        for rid in ("floor_1", "floor_2"):
            # the kind first, so 0.247.0 fails on the kind and not on a missing name
            assert L._room_kind({"id": rid, "story": 1}, b) == "office", (b, rid)
            assert L.is_office_floor({"id": rid}, b), (b, rid)


def test_every_other_bare_floor_keeps_its_kind():
    for b, rid in OTHER_BARE_FLOORS:
        assert L._room_kind({"id": rid, "story": 0}, b) == "shop_floor", (b, rid)
        assert not L.is_office_floor({"id": rid}, b), (b, rid)


def test_the_rule_asks_the_word_floor_alone():
    """A room that names a stronger kind keeps it, and `floor` beside a real shop word is a shop floor still; a
    building whose words only contain `office` is not one."""
    assert L._room_kind({"id": "ground_bullpen"}, "office") == "office"
    assert L._room_kind({"id": "lobby"}, "office") == "lobby"
    assert L._room_kind({"id": "sales_floor"}, "office") == "shop_floor"
    assert not L.is_office_floor({"id": "sales_floor"}, "office")
    assert not L.is_office_floor({"id": "floor_1"}, "post_officer")
    assert not L.is_office_floor({"id": "floor_1"}, None)


def test_the_library_office_floors_hold_desks_and_no_shop_stock():
    for name in ("office", "office_stepped"):
        d = _spec(name)
        (room,) = [r for r in d["rooms"] if r["id"] == "floor_1"]
        tag = "_%s_" % L._room_tag(room)
        stems = collections.Counter(v["name"].split("_" + L._room_tag(room))[0] for v in d["volumes"]
                                    if tag in v.get("name", ""))
        assert stems["desk"] >= 4, (name, dict(stems))
        assert not stems.keys() & {"litter_bin", "vending", "counter_service", "atm_store", "poster_wall_store"}, \
            (name, dict(stems))
