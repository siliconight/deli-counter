"""A lit store throws its light out through its storefront (0.156.0).

The walker, 2026-09-29: "do the outward spill next". A room whose ceiling row
reaches its storefront glass (0.155.0) gets `storefront_spill` anchors along
that glass, outside it, at its head, facing out; Lux (>= 0.57.0) throws each
out and down onto the pavement at a level solved from the room's own lit
floor. Nothing else gets one.
"""
import glob
import json
import os

import lights

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")


def _cap(_story):
    return 0.3


# gas_station_a02's sales floor: 23 x 12, the storefront along its south edge
SALES = {"id": "sales_floor", "story": 0, "center": [-4.5, -5.0, 0.0],
         "bounds": [-16.0, -11.0, 7.0, 1.0], "role": "public_entry"}
# nine 2 m storefront modules, x -11.5 .. 6.5 along y = -11
SOUTH = [{"story": 0, "facing": "S", "x": -10.5 + 2.0 * i, "y": -11.0, "w": 2.0} for i in range(9)]


def _anchors(rooms, fronts, story_height=4.2):
    return lights.derive_light_anchors(rooms, [], story_height, cap_thick=_cap,
                                       wall_thick=0.3, storefronts=fronts)


def _spills(anchors):
    return [a for a in anchors if a["type"] == "storefront_spill"]


def test_a_storefront_row_spills_along_its_glass_outside_it():
    a = _anchors([SALES], SOUTH)
    sp = _spills(a)
    # 18 m of glass (-11.5 .. 6.5), one lamp per 2 x 3.0 m head -> 3
    assert len(sp) == 3
    row = next(x for x in a if x["id"] == "sales_floor_ceiling")
    for s in sp:
        assert s["rot_y"] == 270.0                     # the S wall's outward
        assert s["pos"][1] == -11.0 - (0.15 + 0.20)    # off the wall's face
        assert s["pos"][2] == 3.0                      # the glass's head
        assert s["head"] == 3.0
        assert s["drop"] == row["drop"] and s["reach"] == row["reach"]
        assert s["reacts_to_alarm"] is True and s["room"] == "sales_floor"
    xs = [s["pos"][0] for s in sp]
    assert xs == sorted(xs) and xs[0] == -11.5 + 3.0 and xs[-1] == 6.5 - 3.0


def test_spills_come_last_and_the_rest_is_as_before():
    walled = _anchors([SALES], SOUTH)
    plain = _anchors([SALES], None)
    assert not _spills(plain)
    n = len(walled) - len(_spills(walled))
    assert all(a["type"] == "storefront_spill" for a in walled[n:])
    # without the spills and the row's reach, the same anchors in order
    head = [dict(a) for a in walled[:n]]
    for a in head:
        a.pop("reach", None)
    assert head == plain


def test_a_low_storey_lowers_the_head_with_the_glass():
    sp = _spills(_anchors([SALES], SOUTH, story_height=3.2))
    assert sp and all(s["head"] == 2.8 and s["pos"][2] == 2.8 for s in sp)


def test_a_short_run_still_gets_one_and_each_facing_its_own():
    food = {"id": "food_service", "story": 0, "center": [11.5, -5.0, 0.0],
            "bounds": [7.0, -11.0, 16.0, 1.0]}
    fronts = [{"story": 0, "facing": "S", "x": 8.0, "y": -11.0, "w": 2.0},
              {"story": 0, "facing": "E", "x": 16.0, "y": -9.0, "w": 2.0},
              {"story": 0, "facing": "E", "x": 16.0, "y": -7.0, "w": 2.0}]
    sp = _spills(_anchors([food], fronts))
    by = {}
    for s in sp:
        by.setdefault(s["wall"], []).append(s)
    assert len(by["S"]) == 1 and len(by["E"]) == 1
    assert by["E"][0]["rot_y"] == 0.0 and by["E"][0]["pos"][0] == 16.0 + 0.35


def test_no_reach_no_spill():
    vault = dict(SALES, id="vault", role="objective_room", objective=True)   # bulbs
    upstairs = [dict(f, story=1) for f in SOUTH]
    for rooms, fronts in (([vault], SOUTH), ([SALES], upstairs), ([SALES], [])):
        assert not _spills(_anchors(rooms, fronts)), rooms[0]["id"]


# --------------------------------------------------------------------------- #
# The shipped library (build.py --all)
# --------------------------------------------------------------------------- #

def _manifest(bid):
    with open(os.path.join(BUILD, bid + ".lights.json"), encoding="utf-8") as f:
        return json.load(f)["anchors"]


def test_the_gas_stations_sales_floor_spills_onto_its_forecourt():
    sp = [a for a in _manifest("gas_station_a02") if a["type"] == "storefront_spill"
          and a["room"] == "sales_floor"]
    assert len(sp) == 3 and all(a["rot_y"] == 270.0 for a in sp)


def test_only_a_room_that_reaches_its_glass_spills():
    for p in glob.glob(os.path.join(BUILD, "*.lights.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        reaching = {a["room"] for a in d["anchors"] if "reach" in a}
        spilling = {a["room"] for a in d["anchors"] if a["type"] == "storefront_spill"}
        assert spilling == reaching, (d["building_id"], sorted(spilling ^ reaching))
