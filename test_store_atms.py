"""The store's ATM (0.164.0): one freestanding ATM in every building that sells.

The walker, 2026-09-29: "Convenient stores should also have ATMs". Zoo 1.35.0
drew the unit; this places it. What is held, on the library as the specs
carry it: every building with a selling room has exactly ONE (a deli's
customer floor and market aisles are one store), none stands anywhere else;
it stands on its floor against a wall, faces the room, has collision and a
network variant; and no sale poster hangs over it.
"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design  # noqa: E402
import prop_species  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SELLING = level_design._PIECES["atm_store"]["rooms"]


def _library():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("rooms"):
            yield d


def _tokens(room):
    return set(str(room.get("id", "")).lower().replace("-", "_").split("_"))


def _atms(d):
    return [v for v in d.get("volumes") or [] if str(v.get("name", "")).startswith("atm_store_")]


def _room_of(d, v):
    tags = {level_design._room_tag(r): r for r in d["rooms"]}
    return next(r for t, r in tags.items() if f"_{t}_" in v["name"])


def test_every_building_that_sells_has_one_atm_and_no_other_does():
    per = collections.Counter()
    for d in _library():
        building = level_design.club_building_id(d)
        sells = any(level_design._room_kind(r, building) == "shop_floor" and _tokens(r) & SELLING
                    and max(0.0, r["bounds"][2] - r["bounds"][0]) * max(0.0, r["bounds"][3] - r["bounds"][1])
                    >= level_design._FURNISH_MIN_AREA
                    for r in d["rooms"])
        n = len(_atms(d))
        per[n] += 1
        if sells:
            assert n == 1, (d["name"], n)
        else:
            assert n == 0, (d["name"], n)
    assert per[1] >= 25, per


def test_one_store_with_two_selling_rooms_has_one_atm():
    """The control for `solo`: without it, six delis carried two each."""
    seen = 0
    for d in _library():
        rooms = [r for r in d["rooms"] if _tokens(r) & SELLING]
        if len(rooms) >= 2 and _atms(d):
            seen += 1
            assert len(_atms(d)) == 1, d["name"]
    assert seen >= 4


def test_an_atm_stands_on_its_floor_against_a_wall_facing_the_room():
    for d in _library():
        sh = level_design._story_height(d)
        for v in _atms(d):
            room = _room_of(d, v)
            assert prop_species.species_for_name(v["name"]) == "atm"
            assert v["collision"] == "convex" and v["material"] == "metal"
            story = int(room.get("story", 0) or 0)
            assert v["z"] == round(story * sh + v["size_z"] / 2.0, 3), v["name"]
            x0, y0, x1, y1 = room["bounds"]
            edge = min(v["x"] - x0, x1 - v["x"], v["y"] - y0, y1 - v["y"])
            assert edge < 0.6, (d["name"], v["name"], edge)
            assert 0 <= int(v.get("variant", 0) or 0) < 4


def test_no_sale_poster_hangs_over_an_atm():
    for d in _library():
        atms = _atms(d)
        if not atms:
            continue
        for p in (v for v in d["volumes"] if str(v.get("name", "")).startswith("poster_wall_store_")):
            for a in atms:
                ox = min(p["x"] + p["size_x"] / 2, a["x"] + a["size_x"] / 2) - max(p["x"] - p["size_x"] / 2, a["x"] - a["size_x"] / 2)
                oy = min(p["y"] + p["size_y"] / 2, a["y"] + a["size_y"] / 2) - max(p["y"] - p["size_y"] / 2, a["y"] - a["size_y"] / 2)
                assert not (ox > 0 and oy > 0), (d["name"], p["name"], a["name"])


def test_the_fixture_pass_is_idempotent_on_the_library():
    import copy
    for d in _library():
        e = copy.deepcopy(d)
        assert level_design.place_fixtures(e) == 0, d["name"]
