"""A ceiling row walled by storefront glass says how far the glass is (0.155.0).

The walker, 2026-09-28: "yes, do the glass first then the troffer reach".
Lux derives a fluorescent's range to the floor UNDER it, and one row runs
down a room's middle, so in gas_station_a02's 12 m deep sales floor the floor
at the storefront -- what the street sees -- was 6 m off to the side and
outside every pool. A row whose room a storefront walls now carries `reach`,
and Lux (>= 0.56.0) derives the range to the floor at the glass. Nothing
else carries it.
"""
import glob
import json
import os

import lights

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")


def _cap(_story):
    return 0.3


# gas_station_a02's sales floor, from its gameplay manifest: 23 x 12, the
# storefront on its south edge
SALES = {"id": "sales_floor", "story": 0, "center": [-4.5, -5.0, 0.0],
         "bounds": [-16.0, -11.0, 7.0, 1.0], "role": "public_entry"}
SOUTH_GLASS = [{"story": 0, "facing": "S", "x": x, "y": -11.0} for x in (-10.5, -4.5, 1.5)]


def _rows(rooms, storefronts):
    return {a["room"]: a for a in lights.derive_light_anchors(
        rooms, [], 4.2, cap_thick=_cap, wall_thick=0.3, storefronts=storefronts)
        if a["type"] in ("fluorescent", "pendant")}


def test_a_row_parallel_to_its_storefront_reaches_across_the_room():
    row = _rows([SALES], SOUTH_GLASS)["sales_floor"]
    assert row["type"] == "fluorescent"
    assert row["reach"] == 6.0          # the row at y -5, the glass at -11


def test_no_storefront_no_reach_and_the_row_is_as_before():
    # the control: the same room without glass is 0.154.0's anchor exactly
    plain = _rows([SALES], None)["sales_floor"]
    assert "reach" not in plain
    walled = dict(_rows([SALES], SOUTH_GLASS)["sales_floor"])
    walled.pop("reach")
    assert walled == plain


def test_glass_on_another_room_or_storey_is_not_this_rooms():
    other_room = [{"story": 0, "facing": "S", "x": 12.0, "y": -11.0}]   # past x 7
    upstairs = [dict(g, story=1) for g in SOUTH_GLASS]
    inside = [{"story": 0, "facing": "S", "x": -4.5, "y": -8.0}]         # not on an edge
    for fronts in (other_room, upstairs, inside):
        assert "reach" not in _rows([SALES], fronts)["sales_floor"], fronts


def test_a_row_running_at_the_glass_reaches_from_its_nearest_lamp():
    # food_service: 9 x 12, its row along y (lamps at y -9, -5, -1), the
    # storefront south at -11 and east at x 16
    food = {"id": "food_service", "story": 0, "center": [11.5, -5.0, 0.0],
            "bounds": [7.0, -11.0, 16.0, 1.0]}
    south = [{"story": 0, "facing": "S", "x": 9.9, "y": -11.0}]
    east = [{"story": 0, "facing": "E", "x": 16.0, "y": -5.0}]
    assert _rows([food], south)["food_service"]["reach"] == 2.0
    # the largest of the glass lines it faces
    assert _rows([food], south + east)["food_service"]["reach"] == 4.5


def test_a_bare_bulb_does_not_reach():
    vault = dict(SALES, id="vault", role="objective_room", objective=True)
    row = _rows([vault], SOUTH_GLASS)["vault"]
    assert row["type"] == "pendant" and "reach" not in row


# --------------------------------------------------------------------------- #
# The shipped library (build.py --all)
# --------------------------------------------------------------------------- #

def _storefront_buildings():
    out = set()
    for p in glob.glob(os.path.join(BUILD, "*.slots.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if any(s.get("glazing") == "storefront" for s in d.get("slots", [])):
            out.add(d["building_id"])
    return out


def _lights(bid):
    with open(os.path.join(BUILD, bid + ".lights.json"), encoding="utf-8") as f:
        return json.load(f)["anchors"]


def test_the_gas_stations_sales_floor_reaches_its_glass():
    a = {x["id"]: x for x in _lights("gas_station_a02")}
    assert a["sales_floor_ceiling"]["reach"] == 6.0


def test_only_a_storefront_building_carries_a_reach_and_only_on_fluorescents():
    fronts = _storefront_buildings()
    assert fronts, "no building in build/ has storefront glass"
    for p in glob.glob(os.path.join(BUILD, "*.lights.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        reaching = [a for a in d["anchors"] if "reach" in a]
        if d["building_id"] not in fronts:
            assert not reaching, (d["building_id"], [a["id"] for a in reaching])
        for a in reaching:
            assert a["type"] == "fluorescent" and a["reach"] > 0.0, (d["building_id"], a)
    # and every storefront building has at least one row that reaches
    for bid in sorted(fronts):
        assert any("reach" in a for a in _lights(bid)), bid
