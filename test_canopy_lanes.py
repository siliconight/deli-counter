"""The canopy's washes hang over the lanes (0.167.0).

Cold run 9120, finding 4: under the canopy the pump stood in shadow beside a
lit patch. The washes were spread evenly along the deck and on
gas_station_a02 landed within 1.33 m of the islands; a pump's faces face its
lanes. Held: with islands under the deck, one wash a lane, over the lane's
centre and never over an island; the gaps too narrow to drive are not lanes;
the islands' long axis decides which way the lanes run; too many lanes are
capped; another forecourt's islands do not count; and with no islands the
even spread is unchanged.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lights  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = {"name": "canopy_roof", "x": 0.0, "y": -22.0, "z": 5.0, "size_x": 22.0, "size_y": 13.0,
        "size_z": 0.4}
COLS = [{"name": "canopy_col_%d" % i, "x": x, "y": y, "z": 2.5, "size_x": 0.5, "size_y": 0.5,
         "size_z": 5.0} for i, (x, y) in enumerate(((-8, -27), (0, -27), (8, -27), (-8, -17),
                                                    (0, -17), (8, -17)))]
ISLANDS = [{"name": "pump_island_%d" % i, "x": x, "y": -22.0, "z": 0.15, "size_x": 1.6,
            "size_y": 8.0, "size_z": 0.3} for i, x in enumerate((-6.0, 0.0, 6.0), 1)]


def _washes(vols):
    return [a for a in lights._canopy_anchors(vols) if a["type"] == "canopy_wash"]


def test_one_wash_a_lane_over_the_lane_and_never_over_an_island():
    w = _washes([DECK] + COLS + ISLANDS)
    xs = sorted(a["pos"][0] for a in w)
    assert xs == [-8.9, -3.0, 3.0, 8.9], xs
    for a in w:
        assert a["pos"][1] == -22.0
        for i in ISLANDS:                       # clear of every island
            assert abs(a["pos"][0] - i["x"]) >= i["size_x"] / 2.0 + lights._CANOPY_LANE_MIN / 2.0 - 1e-9
    assert {tuple(a["size"]) for a in w} == {(4.2, 13.0), (4.4, 13.0)}


def test_a_gap_too_narrow_to_drive_is_not_a_lane():
    tight = [dict(i, x=x) for i, x in zip(ISLANDS, (-2.0, 0.0, 6.0))]   # 0.4 m between two
    xs = sorted(a["pos"][0] for a in _washes([DECK] + COLS + tight))
    assert all(not (-1.2 < x < -0.8) for x in xs), xs


def test_islands_along_x_put_the_lanes_along_x():
    deck = dict(DECK, size_x=13.0, size_y=22.0, y=0.0)
    isl = [dict(i, x=0.0, y=y, size_x=8.0, size_y=1.6) for i, y in zip(ISLANDS, (-6.0, 0.0, 6.0))]
    w = _washes([deck] + isl)
    assert sorted(a["pos"][1] for a in w) == [-8.9, -3.0, 3.0, 8.9]
    assert {a["pos"][0] for a in w} == {0.0}


def test_too_many_lanes_are_capped():
    deck = dict(DECK, size_x=60.0)
    isl = [dict(ISLANDS[0], name="pump_island_%d" % k, x=x)
           for k, x in enumerate((-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0))]
    w = _washes([deck] + isl)
    assert len(w) == lights._CANOPY_WASH_MAX
    xs = sorted(a["pos"][0] for a in w)
    assert xs[0] < -24 and xs[-1] > 24            # the outermost lanes are kept


def test_another_forecourt_s_islands_do_not_count():
    far = [dict(i, x=i["x"] + 200.0) for i in ISLANDS]
    assert len(_washes([DECK] + COLS + far)) == len(_washes([DECK] + COLS))


def test_no_islands_keeps_the_even_spread():
    xs = sorted(a["pos"][0] for a in _washes([DECK] + COLS))
    n = len(xs)
    step = DECK["size_x"] / n
    assert xs == [round(-DECK["size_x"] / 2 + step * (k + 0.5), 3) for k in range(n)] or \
        all(abs(a - b) < 1e-6 for a, b in zip(xs, [-DECK["size_x"] / 2 + step * (k + 0.5)
                                                   for k in range(n)]))


def test_the_gas_station_s_washes_are_over_its_lanes():
    spec = json.load(open(os.path.join(HERE, "specs", "gas_station_a02.json"), encoding="utf-8"))
    vols = spec.get("volumes") or []
    w = _washes(vols)
    islands = [v for v in vols if str(v["name"]).startswith("pump_island")]
    assert len(w) == 4 and len(islands) == 3
    for a in w:
        for i in islands:
            assert abs(a["pos"][0] - i["x"]) > i["size_x"] / 2.0, (a["pos"], i["name"])
