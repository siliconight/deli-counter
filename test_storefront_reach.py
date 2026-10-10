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


def _all_rows(rooms, storefronts):
    """Every ceiling row of each room, in order (0.206.0 lays more than one)."""
    out = {}
    for a in lights.derive_light_anchors(rooms, [], 4.2, cap_thick=_cap, wall_thick=0.3,
                                         storefronts=storefronts):
        if a["type"] in ("fluorescent", "pendant"):
            out.setdefault(a["room"], []).append(a)
    return out


def test_a_row_parallel_to_its_storefront_reaches_across_the_room():
    # 0.206.0 lays the 12 m deep sales floor in three rows over its counters, at y -9.0,
    # -4.8 and -1.2 (the tile grid); each reaches the glass at -11 from its own line
    rows = _all_rows([SALES], SOUTH_GLASS)["sales_floor"]
    assert [a["type"] for a in rows] == ["fluorescent"] * 3
    assert [a["reach"] for a in rows] == [2.0, 6.2, 9.8]


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
    # two rows across the 9 m room since 0.206.0, at x 9.0 and 13.8: both reach the south
    # glass from their lamp at y -9, and the east glass at x 16 from their own line
    assert [a["reach"] for a in _all_rows([food], south)["food_service"]] == [2.0, 2.0]
    # the largest of the glass lines each faces
    assert [a["reach"] for a in _all_rows([food], south + east)["food_service"]] == [7.0, 2.2]


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
    # since 0.207.0 the built sales floor is laid to its gondolas and the cap's trade
    # (the pure case above has no shelves and keeps its three rows), so the shape is
    # asserted: every row reaches the glass from its own line, the nearer the shorter,
    # and the first row keeps the original id
    a = {x["id"]: x for x in _lights("gas_station_a02")}
    rows = sorted((x["pos"][1], x["reach"]) for x in a.values()
                  if x["type"] == "fluorescent" and x.get("room") == "sales_floor")
    assert len(rows) >= 2 and "sales_floor_ceiling" in a
    assert all(r > 0.0 for _y, r in rows)
    assert [r for _y, r in rows] == sorted(r for _y, r in rows)


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
            # a spill (0.156.0) carries the reach of the row it comes from
            assert a["type"] in ("fluorescent", "storefront_spill") and a["reach"] > 0.0,                 (d["building_id"], a)
    # and every storefront building has at least one row that reaches
    for bid in sorted(fronts):
        assert any("reach" in a for a in _lights(bid)), bid
