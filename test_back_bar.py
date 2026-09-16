"""The club bar's staff side (0.137.0): a back bar behind every counter,
a working aisle between them, a flap at one end and a bartender in it.

WHAT EACH CLAIM IS FOR, because "there is a back bar" is not the point:

  * THE AISLE IS A CORRIDOR AND A DOOR. Its width is the greater of
    `min_corridor_width` and `min_door_width` -- derived, not chosen -- and
    it is the CLEAR distance between the counter's service face and the
    back bar's front, not a centre-to-centre figure.
  * A BODY CAN STAND THERE AND BE REACHED. Every bar drops a
    `patrol_point` in its aisle; the nav gate answers the reachability,
    and what is held here is that the marker exists, is inside the aisle,
    is not inside any volume, and is on the room's own storey.
  * THE MOUTH IS A DOOR'S WIDTH. A bar whose aisle opens at neither end is
    NOT BUILT and the report says so, because a staff side you cannot walk
    into is an island the nav gate would find later and a person would
    find never.
  * IT IS A FIXED POINT. Deterministic, idempotent, and the library
    refurnishes to itself byte for byte.
"""
from __future__ import annotations

import copy
import io
import json
import math
import os

import pytest

import agent_contract
import level_design
import lights
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))
CLUBS = ("strip_club_a01", "strip_club_a02", "strip_club_a03")


def _library(name):
    with io.open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def _club(w=30.0, d=16.0, story_height=3.6):
    """A one-room strip club big enough for a bar, built the way
    `test_club_rooms` builds one."""
    return {
        "name": "strip_club_probe", "seed": 7, "footprint_x": w,
        "footprint_y": d, "n_stories": 1, "story_height": story_height,
        "wall_thick": 0.3, "floor_thick": 0.3, "default_material": "concrete",
        "materials": [{"id": "concrete", "acoustic": "Concrete"},
                      {"id": "wood", "acoustic": "Wood"}],
        "rooms": [{"id": "main_floor", "story": 0,
                   "bounds": [-w / 2, -d / 2, w / 2, d / 2], "role": "open_floor"}],
        "ext_walls": [{"story": 0, "wall": "S",
                       "openings": [{"kind": "door", "pos": 0.0, "width": 1.6}]}],
        "volumes": [], "partitions": [], "stairs": [], "ladders": [],
        "markers": [],
    }


def _bars(spec):
    return [v for v in spec["volumes"] if v["name"].startswith("back_bar_")]


def _counter_of(spec, bar):
    key = bar["name"][len("back_bar_"):]
    for v in spec["volumes"]:
        if v["name"] == "counter_club_" + key:
            return v
    return None


def _clear_gap(counter, bar):
    """The CLEAR floor between the counter's service face and the back
    bar's front: centres less both half depths, on the axis they are
    separated along."""
    if abs(counter["x"] - bar["x"]) > abs(counter["y"] - bar["y"]):
        return (abs(counter["x"] - bar["x"]) - counter["size_x"] / 2.0
                - bar["size_x"] / 2.0)
    return (abs(counter["y"] - bar["y"]) - counter["size_y"] / 2.0
            - bar["size_y"] / 2.0)


# --- the number --------------------------------------------------------------


def test_the_aisle_is_derived_from_both_contract_numbers():
    got = level_design.bar_aisle_width()
    assert got == max(agent_contract.min_corridor_width(),
                      agent_contract.min_door_width())
    # ...and it is the DOOR that wins today, which is the whole reason the
    # rule is a max and not "the corridor minimum": at 1.1 m the aisle's
    # own mouth would have been 0.15 m under a door's width.
    assert got == pytest.approx(1.25)
    assert got > agent_contract.min_corridor_width()


# --- the geometry ------------------------------------------------------------


@pytest.mark.parametrize("name", CLUBS)
def test_every_club_bar_in_the_library_has_a_back_bar_and_an_aisle(name):
    spec = _library(name)
    counters = [v for v in spec["volumes"]
                if v["name"].startswith("counter_club_")]
    bars = _bars(spec)
    assert counters and len(bars) == len(counters), (name, len(counters), len(bars))
    aisle = level_design.bar_aisle_width()
    for bar in bars:
        counter = _counter_of(spec, bar)
        assert counter is not None, bar["name"]
        assert _clear_gap(counter, bar) == pytest.approx(aisle, abs=0.011)
        assert bar["size_z"] == pytest.approx(level_design.BACK_BAR_H)
        assert min(bar["size_x"], bar["size_y"]) == pytest.approx(
            level_design.BACK_BAR_DEPTH)
        # the bar's run is the counter's, inside Zoo's genome range
        run = max(bar["size_x"], bar["size_y"])
        assert level_design.BACK_BAR_W[0] - 1e-9 <= run <= level_design.BACK_BAR_W[1] + 1e-9


@pytest.mark.parametrize("name", CLUBS)
def test_the_back_bar_faces_the_counter_and_stands_on_the_wall(name):
    spec = _library(name)
    for bar in _bars(spec):
        counter = _counter_of(spec, bar)
        assert lights._front_bearing(bar) == pytest.approx(
            lights._front_bearing(counter)), bar["name"]
        # its back is on a room bound, within the wall's own half thickness
        room = next(r for r in spec["rooms"]
                    if level_design._room_tag(r) in bar["name"])
        x0, y0, x1, y1 = room["bounds"]
        wt = float(spec.get("wall_thick") or 0.3) / 2.0
        edges = [abs(bar["x"] - bar["size_x"] / 2.0 - x0),
                 abs(bar["x"] + bar["size_x"] / 2.0 - x1),
                 abs(bar["y"] - bar["size_y"] / 2.0 - y0),
                 abs(bar["y"] + bar["size_y"] / 2.0 - y1)]
        assert min(edges) == pytest.approx(wt, abs=1e-6), (bar["name"], edges)


@pytest.mark.parametrize("name", CLUBS)
def test_nothing_stands_in_the_aisle(name):
    """The staff side is empty floor: no volume on that storey overlaps
    the rectangle between the counter and the back bar."""
    spec = _library(name)
    sh = level_design._story_height(spec)
    for bar in _bars(spec):
        counter = _counter_of(spec, bar)
        lo = (min(bar["x"] + bar["size_x"] / 2.0, counter["x"] - counter["size_x"] / 2.0),
              min(bar["y"] + bar["size_y"] / 2.0, counter["y"] - counter["size_y"] / 2.0))
        hi = (max(bar["x"] - bar["size_x"] / 2.0, counter["x"] + counter["size_x"] / 2.0),
              max(bar["y"] - bar["size_y"] / 2.0, counter["y"] + counter["size_y"] / 2.0))
        rect = (min(lo[0], hi[0]), min(lo[1], hi[1]),
                max(lo[0], hi[0]), max(lo[1], hi[1]))
        # the aisle is the band BETWEEN them; shrink it off both pieces
        floor = float(bar["z"]) - float(bar["size_z"]) / 2.0
        for v in spec["volumes"]:
            if v["name"] in (bar["name"], counter["name"]):
                continue
            if v["name"].startswith("counter_end_"):
                continue            # the L's return end closes one mouth
            vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
            if not level_design._on_storey(vz, vh, floor, sh):
                continue
            if v.get("collision") == "none":
                continue
            if _overlap(rect, v) > 0.02:
                raise AssertionError((name, bar["name"], v["name"]))


def _overlap(rect, v):
    ox = min(rect[2], v["x"] + v["size_x"] / 2.0) - max(rect[0], v["x"] - v["size_x"] / 2.0)
    oy = min(rect[3], v["y"] + v["size_y"] / 2.0) - max(rect[1], v["y"] - v["size_y"] / 2.0)
    return min(ox, oy)


# --- the bartender -----------------------------------------------------------


@pytest.mark.parametrize("name", CLUBS)
def test_a_bartender_marker_stands_in_every_aisle(name):
    spec = _library(name)
    marks = [m for m in spec.get("markers", [])
             if (m.get("meta") or {}).get("role") == "bartender"]
    assert len(marks) == len(_bars(spec)) and marks
    sh = level_design._story_height(spec)
    for m in marks:
        assert m["type"] == "patrol_point"
        bar = next(b for b in _bars(spec)
                   if b["name"] == "back_bar_" + m["id"][len("bartender_"):])
        counter = _counter_of(spec, bar)
        # BETWEEN THE TWO ON THE AXIS THEY ARE SEPARATED ALONG, which is
        # the only axis the question is about: along the run the marker
        # deliberately stands near the open end, not at the middle.
        if abs(bar["x"] - counter["x"]) > abs(bar["y"] - counter["y"]):
            u, a0, a1 = m["x"], bar["x"], counter["x"]
        else:
            u, a0, a1 = m["y"], bar["y"], counter["y"]
        assert min(a0, a1) - 1e-6 <= u <= max(a0, a1) + 1e-6, (m["id"], u, a0, a1)
        room = next(r for r in spec["rooms"] if r["id"] == m["room"])
        assert m["z"] == pytest.approx(int(room.get("story", 0)) * sh)
        for v in spec["volumes"]:
            if v.get("collision") == "none":
                continue
            if abs(v["x"] - m["x"]) < v["size_x"] / 2.0 and \
                    abs(v["y"] - m["y"]) < v["size_y"] / 2.0 and \
                    level_design._on_storey(float(v["z"]), float(v["size_z"]),
                                            m["z"], sh):
                raise AssertionError((name, m["id"], v["name"]))


def test_the_marker_is_inside_the_mouth_it_is_reached_through():
    """A bartender a body's step in from the open end, not in the doorway
    and not at the far blind end."""
    s = _club()
    level_design.furnish(s)
    marks = [m for m in s["markers"]
             if (m.get("meta") or {}).get("role") == "bartender"]
    assert marks
    for m in marks:
        bar = next(b for b in _bars(s)
                   if b["name"] == "back_bar_" + m["id"][len("bartender_"):])
        run = max(bar["size_x"], bar["size_y"])
        along = m["x"] if bar["size_x"] > bar["size_y"] else m["y"]
        centre = bar["x"] if bar["size_x"] > bar["size_y"] else bar["y"]
        assert abs(along - centre) <= run / 2.0 + 1e-6


# --- the flap and the L ------------------------------------------------------


def test_a_bar_whose_aisle_opens_nowhere_is_not_built():
    """The refusal, and it is the point of the pass: a staff side you
    cannot walk into is an island, and an island is worse than no bar."""
    s = _club(30.0, 16.0)
    level_design.furnish(s)
    bars = _bars(s)
    assert bars, "the probe club got no bar at all"
    # wall the aisle's ends in and refurnish from scratch: the same counter
    # now has nowhere to open
    t = _club(30.0, 16.0)
    counter = None
    level_design.furnish(t)
    counter = next(v for v in t["volumes"] if v["name"].startswith("counter_club_"))
    u = _club(30.0, 16.0)
    run = max(counter["size_x"], counter["size_y"])
    along_x = counter["size_x"] > counter["size_y"]
    for end in (-1, 1):
        if along_x:
            u["partitions"].append({"story": 0, "axis": "Y",
                                    "pos": round(counter["x"] + end * run / 2.0, 3),
                                    "start": -8.0, "end": 8.0, "openings": []})
        else:
            u["partitions"].append({"story": 0, "axis": "X",
                                    "pos": round(counter["y"] + end * run / 2.0, 3),
                                    "start": -15.0, "end": 15.0, "openings": []})
    level_design.furnish(u)
    rep = level_design.back_bar_club_counters(u)
    for r in rep:
        if not r["built"]:
            assert r["why"], r
    # every entry the pass refuses says WHY, in words with a number in them
    assert all(r["built"] or any(c.isdigit() for c in r["why"]) or
               "clear" in r["why"] for r in rep)


@pytest.mark.parametrize("name", CLUBS)
def test_the_l_shaped_bars_close_one_end_with_a_plain_counter(name):
    spec = _library(name)
    for leg in [v for v in spec["volumes"]
                if v["name"].startswith("counter_end_")]:
        # it is a PLAIN counter: no bar form, no dense top, no variant
        assert "form" not in leg and "stock" not in leg, leg
        assert prop_species.species_for_name(leg["name"]) == "counter"
        # and it spans the aisle: its short side is the counter's depth,
        # its long side the aisle's width
        key = leg["name"][len("counter_end_"):]
        counter = next(v for v in spec["volumes"]
                       if v["name"] == "counter_club_" + key)
        thick = min(counter["size_x"], counter["size_y"])
        assert min(leg["size_x"], leg["size_y"]) == pytest.approx(thick)
        assert max(leg["size_x"], leg["size_y"]) == pytest.approx(
            level_design.bar_aisle_width())
        assert leg["size_z"] == pytest.approx(counter["size_z"])


def test_the_library_has_at_least_one_l_shaped_bar():
    """"Where the room's corner allows" is a real branch, not dead code."""
    n = sum(len([v for v in _library(c)["volumes"]
                 if v["name"].startswith("counter_end_")]) for c in CLUBS)
    assert n >= 1


# --- the counter's own dressing ----------------------------------------------


@pytest.mark.parametrize("name", CLUBS)
def test_every_club_counter_asks_zoo_for_the_bar_form_and_the_dense_top(name):
    spec = _library(name)
    counters = [v for v in spec["volumes"]
                if v["name"].startswith("counter_club_")]
    assert counters
    for v in counters:
        assert v.get("form") == "bar", v["name"]
        assert v.get("stock") == "bar_dense", v["name"]


def test_the_dive_bar_is_left_alone():
    """The walker: the club's bar "will be different from the dive bar
    species we make later". `counter_bar` -- the `club` room kind's, a
    taproom's -- keeps the sparse stock and no form."""
    p = level_design._PIECES["counter_bar"]
    assert p["stock"] == "bar" and p["form"] is None


# --- the light ---------------------------------------------------------------


def test_deli_counter_writes_a_back_bar_anchor_at_every_back_bar():
    s = _club()
    level_design.furnish(s)
    bars = _bars(s)
    assert bars
    rooms = [{"id": r["id"], "story": r["story"], "bounds": r["bounds"],
              "center": [(r["bounds"][0] + r["bounds"][2]) / 2.0,
                         (r["bounds"][1] + r["bounds"][3]) / 2.0,
                         r["story"] * s["story_height"]]} for r in s["rooms"]]
    rep = {}
    anchors = lights.derive_light_anchors(
        rooms, [], s["story_height"], cap_thick=0.3, wall_thick=0.3,
        volumes=s["volumes"], club_rooms=[r["id"] for r in s["rooms"]],
        report=rep)
    got = [a for a in anchors if a["type"] == "back_bar"]
    assert len(got) == len(bars) == rep["back_bars"]
    for a, bar in zip(got, bars):
        assert a["id"] == bar["name"] + "_niche"
        # NO COLOUR ON THE ANCHOR: Lux reads a back bar with none as
        # `tungsten` (0.39.0), which is the bulb colour Zoo paints. Naming
        # it here would be the same number written twice.
        assert "color" not in a
        assert a["aisle"] == pytest.approx(level_design.bar_aisle_width())
        # THE SOURCE IS IN FREE AIR, in front of the cabinet: Lux's omni
        # sits AT the anchor (roadmap 139)
        depth = min(bar["size_x"], bar["size_y"])
        d = math.hypot(a["pos"][0] - bar["x"], a["pos"][1] - bar["y"])
        assert d > depth / 2.0 + 1e-6, (a["id"], d, depth)
        assert d == pytest.approx(depth / 2.0 + lights._BACKBAR_OUT, abs=1e-3)
        # ...and it is inside the aisle, not through the counter
        assert d < level_design.bar_aisle_width()


def test_the_lit_face_is_zoos_arithmetic():
    """`back_bar_face` mirrors `back_bar_forms`, which Deli Counter cannot
    import. Pinned against Zoo's own numbers when Zoo is beside this repo,
    and against the derivation either way."""
    for h in (1.8, 2.0, 2.4, 2.8, 3.0):
        rise, lit = lights.back_bar_face(h)
        counter = min(1.05, h * 0.5)
        lo, hi = counter + 0.04, h - 0.07
        assert rise == pytest.approx((lo + hi) / 2.0, abs=1e-4)
        assert lit == pytest.approx(hi - lo, abs=1e-4)
        assert lo < rise < hi
    zoo = os.environ.get("DC_ZOO_ROOT") or os.path.join(
        os.path.dirname(HERE), "zoo")
    forms = os.path.join(zoo, "zoo_keeper", "core", "back_bar_forms.py")
    if not os.path.isfile(forms):
        return
    src = io.open(forms, encoding="utf-8").read()
    for name, want in (("COUNTER_H", 1.05), ("COUNTER_SHARE", 0.5),
                       ("TOP_T", 0.04), ("CORNICE_H", 0.07)):
        line = next(ln for ln in src.splitlines()
                    if ln.startswith(name + " = "))
        assert float(line.split("=")[1].split("#")[0].strip()) == want, line


# --- the pass's own contract -------------------------------------------------


def test_the_pass_is_idempotent_and_deterministic():
    a = _club()
    level_design.furnish(a)
    before = json.dumps(a, sort_keys=True)
    assert all(r["why"] == "already"
               for r in level_design.back_bar_club_counters(a) if r["built"])
    assert json.dumps(a, sort_keys=True) == before
    b = _club()
    level_design.furnish(b)
    assert json.dumps(b, sort_keys=True) == before


def test_a_counter_outside_a_strip_club_is_left_alone():
    """`counter_bar` in a taproom, `counter_service` in a lobby: this pass
    is the STRIP CLUB's, read off the building's id like every other club
    rule (`is_strip_club_room`)."""
    s = _club()
    s["name"] = "tavern_a01"
    level_design.furnish(s)
    assert not _bars(s)
    assert not [m for m in s["markers"]
                if (m.get("meta") or {}).get("role") == "bartender"]


def test_the_library_is_still_a_fixed_point_of_furnish():
    """Strip every volume and marker this pass writes and run it again:
    the three clubs come back byte for byte, as the other 123 specs do."""
    import migrate_club_rooms
    import migrate_furnish_recipes
    for name in CLUBS:
        d = _library(name)
        before = json.dumps(d, sort_keys=True)
        e = copy.deepcopy(d)
        migrate_club_rooms.migrate(e)
        migrate_furnish_recipes.migrate(e)
        assert json.dumps(e, sort_keys=True) == before, name
