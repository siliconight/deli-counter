"""A supermarket's ceiling rows bake to the next lamp along (0.279.0).

The walker, 2026-10-26: "far too dark in teh super market". The supermarket's lamps are baked statics whose range is
the drop rule, written for the realtime claim each lamp makes on every mesh it reaches; re-baked with the range x 1.6
the store's frame rose 38.5 -> 61.5 mean (the factory's docs/findings/black_gondola_ends/). Lux (>= 0.80.0) lends a
static lamp a longer range only while a lightmap bakes, derived from a row's `bake_reach`. A supermarket's selling
floor stamps its rows' spacing as that; no other room carries it.

FAILS ON 0.278.0: no row carries `bake_reach`, and `derive_light_anchors` takes no `bake_reach_rooms`.
"""
import json
import os

import pytest

import lights

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")


def _cap(_story):
    return 0.3


SALES = {"id": "sales_floor", "story": 0, "center": [0.0, -4.0, 0.0],
         "bounds": [-17.0, -15.0, 17.0, 7.0], "role": "public_entry"}
BACK = {"id": "stockroom", "story": 0, "center": [0.0, 10.0, 0.0],
        "bounds": [-17.0, 7.0, 17.0, 13.0]}


def _rows(rooms, **kw):
    out = {}
    for a in lights.derive_light_anchors(rooms, [], 4.4, cap_thick=_cap, wall_thick=0.3, **kw):
        if a["type"] in ("fluorescent", "pendant", "dome"):
            out.setdefault(a["room"], []).append(a)
    return out


def test_a_named_rooms_rows_carry_their_spacing_and_no_other_rooms_do():
    rows = _rows([SALES, BACK], bake_reach_rooms={"sales_floor"})
    assert rows["sales_floor"]
    for a in rows["sales_floor"]:
        assert a["type"] == "fluorescent"
        assert a["bake_reach"] == round(a["row"]["spacing"], 3) > 0.0, a
    for a in rows["stockroom"]:
        assert "bake_reach" not in a, a


def test_without_a_named_room_every_row_is_as_before():
    """The control: the same rooms with no `bake_reach_rooms` are 0.278.0's anchors exactly."""
    plain = _rows([SALES, BACK])
    named = _rows([SALES, BACK], bake_reach_rooms={"sales_floor"})
    for room, got in named.items():
        assert [{k: v for k, v in a.items() if k != "bake_reach"} for a in got] == plain[room]
    assert not any("bake_reach" in a for got in plain.values() for a in got)


def test_the_supermarket_floor_is_the_named_room():
    got = lights._bake_reach_rooms([SALES, BACK], "supermarket_a01")
    assert got == {"sales_floor"}
    assert lights._bake_reach_rooms([SALES, BACK], "convenience_store_a01") == set()
    assert lights._bake_reach_rooms([SALES, BACK], None) == set()


@pytest.mark.parametrize("name", ["supermarket_a01", "supermarket_a02", "supermarket_a03"])
def test_every_built_supermarkets_sales_floor_rows_carry_it(name):
    path = os.path.join(BUILD, name + ".lights.json")
    if not os.path.exists(path):
        pytest.skip("%s is not built" % name)
    with open(path, encoding="utf-8") as fh:
        anchors = json.load(fh)["anchors"]
    sales = [a for a in anchors if a.get("type") == "fluorescent" and a.get("room") == "sales_floor"]
    others = [a for a in anchors if a.get("type") == "fluorescent" and a.get("room") != "sales_floor"]
    assert sales, name
    assert all(a.get("bake_reach", 0.0) > 0.0 for a in sales), name
    assert not any("bake_reach" in a for a in others), name
