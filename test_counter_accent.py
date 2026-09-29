"""A warm bulb over the register counter (0.160.0).

The walker, 2026-09-29: "add the warm counter accent and the window sign
next", from their 1990s lighting reference on the convenience store at
night -- cooler light on the aisles, a warmer accent at the counter. One
`counter_accent` anchor over the centre of each volume whose name carries
`register_counter`, in a room lit by a fluorescent row; Lux (>= 0.59.0)
lights it warm and Zoo (>= 1.27.0) hangs a pendant for it. Nothing else
moves.
"""
import glob
import json
import os

import lights

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")


def _cap(_story):
    return 0.3


# gas_station_a02's sales floor and its register counter (specs, 2026-09-29)
SALES = {"id": "sales_floor", "story": 0, "center": [-4.5, -5.0, 0.0],
         "bounds": [-16.0, -11.0, 7.0, 1.0], "role": "public_entry"}
COUNTER = {"name": "register_counter", "x": 0.0, "y": -8.5, "z": 0.55,
           "size_x": 6.0, "size_y": 1.0, "size_z": 1.1}
DELI_COUNTER = dict(COUNTER, name="front_register_counter", x=-3.0)


def _anchors(rooms, volumes, story_height=4.2, report=None, **kw):
    return lights.derive_light_anchors(rooms, [], story_height, cap_thick=_cap,
                                       wall_thick=0.3, volumes=volumes, report=report, **kw)


def _accents(anchors):
    return [a for a in anchors if a["type"] == "counter_accent"]


def test_one_bulb_hangs_over_the_register_counter():
    rep = {}
    a = _anchors([SALES], [COUNTER], report=rep)
    (acc,) = _accents(a)
    row = next(x for x in a if x["id"] == "sales_floor_ceiling")
    assert acc["id"] == "sales_floor_counter_accent"
    assert acc["pos"][:2] == [0.0, -8.5]
    # on the pendant's cord below the ceiling, drop measured from the bulb
    assert acc["pos"][2] == round(row["pos"][2] - lights._PENDANT_CORD, 3)
    assert acc["drop"] == round(acc["pos"][2] - SALES["center"][2], 3)
    assert acc["room"] == "sales_floor" and acc["reacts_to_alarm"] is True
    assert rep["counter_accents"] == 1


def test_a_delis_front_register_counter_gets_one_too():
    assert [x["pos"][0] for x in _accents(_anchors([SALES], [DELI_COUNTER]))] == [-3.0]


def test_accents_come_last_and_the_rest_is_as_before():
    lit = _anchors([SALES], [COUNTER])
    plain = _anchors([SALES], [])
    assert not _accents(plain)
    assert lit[:-1] == plain and lit[-1]["type"] == "counter_accent"


def test_no_counter_no_bulb_and_other_volumes_do_not_count():
    shelf = dict(COUNTER, name="gondola_aisle_1")
    assert not _accents(_anchors([SALES], [shelf]))


def test_a_moody_room_keeps_its_bare_bulbs_and_gets_no_accent():
    cellar = dict(SALES, id="cellar", story=-1, center=[-4.5, -5.0, -4.2])
    low = dict(COUNTER, z=-4.2 + 0.55)
    got = _anchors([cellar], [low])
    assert not _accents(got)
    vault = dict(SALES, id="vault", objective=True, role="vault")
    assert not _accents(_anchors([vault], [COUNTER]))


def test_a_club_room_gets_its_club_set_and_no_accent():
    got = _anchors([dict(SALES, id="main_floor")], [COUNTER], club_rooms=["main_floor"])
    assert not _accents(got)


def test_two_counters_two_bulbs_the_first_keeps_the_plain_id():
    second = dict(COUNTER, x=-10.0)
    ids = sorted(x["id"] for x in _accents(_anchors([SALES], [COUNTER, second])))
    assert ids == ["sales_floor_counter_accent", "sales_floor_counter_accent_1"]


# --- what the build shipped ---------------------------------------------------

STORES = ("cr_gas", "fuel_stop_heist", "gas_station", "gas_station_a01", "gas_station_a02",
          "gas_station_a03", "gas_street", "gs_corner_station", "stop_n_go")


def test_every_built_store_hangs_its_accent_over_its_counter():
    for name in STORES:
        spec = json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))
        counters = [v for v in spec["volumes"] if "register_counter" in v["name"]]
        man = json.load(open(os.path.join(BUILD, name + ".lights.json"), encoding="utf-8"))
        acc = _accents(man["anchors"])
        assert len(acc) == len(counters) >= 1, name
        for a, v in zip(sorted(acc, key=lambda a: a["pos"][0]), sorted(counters, key=lambda v: v["x"])):
            assert a["pos"][:2] == [round(v["x"], 3), round(v["y"], 3)], name


def test_no_building_without_a_register_counter_got_one():
    for p in glob.glob(os.path.join(BUILD, "*.lights.json")):
        name = os.path.basename(p)[:-len(".lights.json")]
        sp = os.path.join(HERE, "specs", name + ".json")
        if not os.path.isfile(sp):
            continue
        spec = json.load(open(sp, encoding="utf-8"))
        if any("register_counter" in v.get("name", "") for v in spec.get("volumes") or []):
            continue
        man = json.load(open(p, encoding="utf-8"))
        assert not _accents(man.get("anchors") or []), name
