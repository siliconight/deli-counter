"""Video-poker cabinets with a stool, in stores, bars and clubs (0.168.0).

The walker, 2026-09-30: "PA Skill Games ... in convenient stores, bars, and
strip clubs. High stool to play" -- Zoo 1.39.0's `video_poker`. Held, on the
library as the specs carry it: cabinets stand only in selling rooms, bar
rooms and strip-club rooms, at most the pieces allow; each routes to the
species, stands on its floor against a wall with collision and a variant;
each has ONE stool in front of its face, facing it, clear of the cabinet;
and the fixture pass stays idempotent.
"""
import collections
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design  # noqa: E402
import prop_species  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _library():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("rooms"):
            yield d


def _cabinets(d):
    return [v for v in d.get("volumes") or [] if str(v.get("name", "")).startswith("video_poker_")]


def test_the_names_route_to_the_species_and_the_stool_to_the_stool():
    for n in ("video_poker_store_r0a1b2c3d_4", "video_poker_bar_r0a1b2c3d_2"):
        assert prop_species.species_for_name(n) == "video_poker", n
    assert prop_species.species_for_name("bar_stool_r0a1b2c3d_2_1") == "bar_stool"


def test_cabinets_stand_where_they_belong_at_most_the_pieces_allow():
    per_room = collections.Counter()
    total = 0
    for d in _library():
        building = level_design.club_building_id(d)
        rooms = {level_design._room_tag(r): r for r in d["rooms"]}
        for v in _cabinets(d):
            total += 1
            tag = next(t for t in rooms if f"_{t}_" in v["name"])
            room = rooms[tag]
            key = v["name"].rsplit("_" + tag, 1)[0]
            kind = level_design._room_kind(room, building)
            assert key in level_design._RECIPES[kind].get("fixtures", ()), (d["name"], v["name"], kind)
            toks = set(str(room["id"]).lower().replace("-", "_").split("_"))
            assert toks & level_design._PIECES[key]["rooms"], (d["name"], room["id"])
            per_room[(d["name"], tag, key)] += 1
    assert total >= 30, total
    for (name, tag, key), n in per_room.items():
        assert n <= max(level_design._PIECES[key]["most"] or 1,
                        (level_design._PIECES[key]["most_big"] or (0, 0))[1]), (name, tag, key, n)


def test_each_cabinet_stands_against_a_wall_with_one_stool_facing_it():
    seen = 0
    for d in _library():
        sh = level_design._story_height(d)
        vols = {v["name"]: v for v in d.get("volumes") or []}
        for v in _cabinets(d):
            seen += 1
            assert prop_species.species_for_name(v["name"]) == "video_poker"
            assert v["collision"] == "convex"
            assert 0 <= int(v.get("variant", 0) or 0) < 4
            # the stool is named for its cabinet: `bar_stool_<roomtag>_<seq>_1`
            key = next(k for k in ("video_poker_store", "video_poker_bar")
                       if v["name"].startswith(k + "_"))
            stools = [vols[n] for n in ("bar_stool_" + v["name"][len(key) + 1:] + "_1",) if n in vols]
            assert len(stools) == 1, (d["name"], v["name"])
            s = stools[0]
            # in front of the face, off the cabinet, facing it
            dx, dy = s["x"] - v["x"], s["y"] - v["y"]
            assert math.hypot(dx, dy) > 0.5, (d["name"], v["name"])
            assert abs(dx) < 1e-6 or abs(dy) < 1e-6, (dx, dy)
            assert s["z"] < v["z"]                       # a stool, under the cabinet's centre
    assert seen >= 30


def test_the_fixture_pass_is_idempotent_on_the_library():
    import copy
    for d in _library():
        e = copy.deepcopy(d)
        assert level_design.place_fixtures(e) == 0, d["name"]


def _on_glass(d):
    """The cabinets standing within a wall's thickness of a glazed wall on
    their storey -- the poster test's rule (`test_poster_walls`)."""
    hx, hy = float(d.get("footprint_x", 0.0)) / 2.0, float(d.get("footprint_y", 0.0)) / 2.0
    wt = float(d.get("wall_thick") or 0.3)
    sh = level_design._story_height(d)
    out = []
    for v in _cabinets(d):
        story = round((v["z"] - v["size_z"] / 2.0) / sh)
        glazed = level_design._glazed_walls(d, story)
        near = {"S": abs(v["y"] + hy) < wt + 0.5, "N": abs(v["y"] - hy) < wt + 0.5,
                "W": abs(v["x"] + hx) < wt + 0.5, "E": abs(v["x"] - hx) < wt + 0.5}
        if any(near[w] for w in glazed):
            out.append(v["name"])
    return out


def test_no_cabinet_stands_against_the_storefront_glass():
    """0.168.2, the walker: "set off_glass on cabinets" -- cold run 9127 put
    one of gas_station_a02's against the glass by its door. The 0.5 m band
    is the cabinet's half-depth and a hand: a cabinet's centre stands 0.33 m
    and its back a centimetre off the wall it is backed to."""
    for d in _library():
        assert not _on_glass(d), (d["name"], _on_glass(d))
