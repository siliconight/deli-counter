"""0.136.0 -- a strip club has a dartboard, and a bar, a lobby and a hall a
cigarette machine.

The walker, 2026-09-15: "we also need dart boards in the strip clubs. The
kind where you use chalk to keep your score", and "we need retro
cigarettes' machines in the strip club. (Maybe we'll put em in other
buildings too, it was the 1990s where smoking in public was still legal in
PA)". Zoo 0.91.0 builds both: `dartboard`, a wall cabinet whose slot is the
open footprint with the bull at its centre height, and `cigarette_machine`.

Here: the pieces route to the species; a club room's board hangs its bull at
1.73 m with the oche and a standing body clear in front of it, the lane
clear of doors and stairs; no board outside a strip club's club rooms; a
cigarette machine in the kinds that take one and nowhere else; the library
carries both (`migrate_club_fixtures.py`) and is still a fixed point of
`furnish`. Every test here fails on 0.135.1.
"""
import collections
import copy
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design   # noqa: E402
import prop_species   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BULL_M = 1.73
OCHE_M = 2.37
BODY_R = 0.35


def _club(w=20.0, d=12.0, rid="main_floor", name="strip_club_probe", **kw):
    s = {"name": name, "seed": 1997, "story_height": 3.6, "wall_thick": 0.3,
         "footprint_x": w + 4.0, "footprint_y": d + 4.0, "n_stories": 1,
         "default_material": "concrete",
         "materials": [{"id": "concrete"}, {"id": "drywall"}, {"id": "wood"}],
         "rooms": [{"id": rid, "story": 0, "role": "public_entry",
                    "bounds": [-w / 2, -d / 2, w / 2, d / 2], "combat_range": "medium"}],
         "volumes": [], "partitions": [], "ext_walls": [], "stairs": []}
    s.update(kw)
    return s


def _library_specs():
    return [p for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
            if not os.path.basename(p).startswith("lf_")]


def _mine(spec, room, stem):
    tag = level_design._room_tag(room)
    return [v for v in spec["volumes"] if v["name"].startswith(stem + "_") and f"_{tag}_" in v["name"]]


def _independent_lane(spec, room, v):
    """The lane recomputed here from the room and the volume alone -- not
    from `dart_lane` -- so the check does not grade its own homework: the
    board's back is on the NEAREST room bound, the lane runs away from it."""
    x0, y0, x1, y1 = room["bounds"]
    sx, sy = v["size_x"], v["size_y"]
    gaps = {"W": v["x"] - x0, "E": x1 - v["x"], "S": v["y"] - y0, "N": y1 - v["y"]}
    wall = min(gaps, key=gaps.get)
    depth, along = min(sx, sy), max(sx, sy)
    length = depth + OCHE_M + 2 * BODY_R
    half = along / 2 + BODY_R
    if wall in ("W", "E"):
        assert sx < sy, (v["name"], wall)
        back = v["x"] - depth / 2 if wall == "W" else v["x"] + depth / 2
        a, b = (back, back + length) if wall == "W" else (back - length, back)
        return (a, v["y"] - half, b, v["y"] + half), wall
    assert sy < sx, (v["name"], wall)
    back = v["y"] - depth / 2 if wall == "S" else v["y"] + depth / 2
    a, b = (back, back + length) if wall == "S" else (back - length, back)
    return (v["x"] - half, a, v["x"] + half, b), wall


def _assert_board(spec, room, v):
    story = room.get("story", 0)
    sh = float(spec.get("story_height", 3.6))
    assert prop_species.species_for_name(v["name"]) == "dartboard", v["name"]
    # the bull is the slot's centre (Zoo), so the slot's centre IS the bull
    assert v["z"] - story * sh == BULL_M, v
    assert v["collision"] == "none" and v["material"] == "wood_stained", v
    lane, wall = _independent_lane(spec, room, v)
    assert lane == tuple(level_design.dart_lane(v)) or all(
        abs(p - q) < 0.02 for p, q in zip(lane, level_design.dart_lane(v))), (lane, level_design.dart_lane(v))
    x0, y0, x1, y1 = room["bounds"]
    assert x0 < lane[0] and y0 < lane[1] and lane[2] < x1 and lane[3] < y1, (v["name"], lane)
    floor = story * sh
    for o in spec["volumes"]:
        if o is v:
            continue
        oz, oh = o["z"], o["size_z"]
        if not (oz + oh / 2 > floor + 0.05 and oz - oh / 2 < floor + sh - 0.05):
            continue
        if o.get("collision") == "none" and oz - oh / 2 - floor >= 1.8:
            continue
        hx, hy = o["size_x"] / 2, o["size_y"] / 2
        if abs(o.get("rot_z", 0.0)) % 90 > 1e-6:
            hx = hy = math.hypot(hx, hy)
        hit = o["x"] - hx < lane[2] and o["x"] + hx > lane[0] and o["y"] - hy < lane[3] and o["y"] + hy > lane[1]
        assert not hit, ("in the lane", v["name"], o["name"])
    assert level_design.dart_lane_blockers(spec, room, level_design.dart_lane(v), skip=(v["name"],)) == []
    return lane


# --- the pieces ------------------------------------------------------------------------

def test_the_pieces_route_to_zoos_species_and_nothing_else_moved():
    assert prop_species.species_for_name("dartboard_r00000000_1") == "dartboard"
    assert prop_species.species_for_name("cigarettes_r00000000_1") == "cigarette_machine"
    assert prop_species.species_for_name("scoreboard_control_rack") == "shelving"
    assert prop_species.species_for_name("vending_r00000000_1") == "vending_machine"
    assert "dartboard" in level_design._PIECES and "cigarettes" in level_design._PIECES
    # a cigarette machine is not auto-cover, as the vending machine is not
    assert not level_design._looks_like_cover({"name": "cigarettes_r00000000_1", "size_x": 0.88,
                                              "size_y": 0.45, "size_z": 1.5})


def test_zoo_hangs_the_bull_at_the_slots_centre_so_the_lift_is_the_bull():
    import test_furnish
    test_furnish._zoo_core()
    from zoo_keeper.core import dartboard_forms as DF
    assert tuple(level_design._PIECES["dartboard"]["sizes"]) == tuple(DF.DC_SIZES)
    for w, d, h in DF.DC_SIZES:
        for v in range(4):
            got = DF.plan(w, d, h, "open", v)
            assert abs(got["bull"][2] - h / 2) < 1e-6 and abs(got["bull"][0]) < 1e-6
    assert level_design._PIECES["dartboard"]["lift"] == BULL_M
    from zoo_keeper.core import cigarette_forms as CF
    assert tuple(level_design._PIECES["cigarettes"]["sizes"]) == tuple(CF.DC_SIZES)


# --- the dartboard -----------------------------------------------------------------------

def test_a_club_room_hangs_a_board_at_regulation_height_with_a_clear_lane():
    for w, d in ((20.0, 12.0), (18.0, 10.0), (24.0, 11.0)):
        s = _club(w, d)
        level_design.furnish(s)
        room = s["rooms"][0]
        boards = _mine(s, room, "dartboard")
        assert 1 <= len(boards) <= level_design.fixture_limit("dartboard", w * d), (w, d, boards)
        for v in boards:
            _assert_board(s, room, v)


def test_the_lane_keeps_off_doors_stairs_and_the_next_board():
    s = _club(30.0, 12.0)                   # 360 m2: may take two
    s["footprint_x"], s["footprint_y"] = 30.0, 12.0
    s["ext_walls"] = [{"wall": "S", "story": 0, "material": "concrete",
                       "openings": [{"kind": "door", "pos": 0.1, "width": 1.6}]},
                      {"wall": "N", "story": 0, "material": "concrete",
                       "openings": [{"kind": "door", "pos": -0.3, "width": 1.25}]}]
    s["stairs"] = [{"x": 11.0, "y": 0.0, "from_story": 0, "to_story": 1, "style": "straight",
                    "facing": "N", "run": 4.7, "id": "st"}]
    s["n_stories"] = 2
    level_design.furnish(s)
    room = s["rooms"][0]
    boards = _mine(s, room, "dartboard")
    assert len(boards) == 2, [v["name"] for v in s["volumes"]]
    lanes = [_assert_board(s, room, v) for v in boards]
    doors = [(0.1 * 30.0, -6.0), (-0.3 * 30.0, 6.0)]
    for lane in lanes:
        for ox, oy in doors:
            dx = max(lane[0] - ox, 0.0, ox - lane[2])
            dy = max(lane[1] - oy, 0.0, oy - lane[3])
            assert math.hypot(dx, dy) >= 1.5, (lane, (ox, oy))
        for r in level_design._stair_reserved_rects(s):
            assert not (lane[0] < r[2] + 0.3 and lane[2] > r[0] - 0.3 and
                        lane[1] < r[3] + 0.3 and lane[3] > r[1] - 0.3), (lane, r)
    a, b = lanes
    gap = 2 * BODY_R
    assert not (a[0] < b[2] + gap and a[2] > b[0] - gap and a[1] < b[3] + gap and a[3] > b[1] - gap)
    # idempotent, deterministic
    assert level_design.furnish(s) == 0


def test_no_board_outside_a_strip_clubs_club_rooms():
    # the control: the same room in a strip club takes one (without it this
    # test passed on 0.135.1, where nothing took a board)
    control = _club(20.0, 12.0)
    level_design.furnish(control)
    assert [v for v in control["volumes"] if v["name"].startswith("dartboard_")]
    probes = [_club(20.0, 12.0, rid="cash_office"), _club(20.0, 12.0, rid="main_floor", name="deli_a09"),
              _club(20.0, 12.0, rid="club_bar", name="country_club_a09"),
              _club(20.0, 12.0, rid="lobby", name="bank_a09"), _club(20.0, 12.0, rid="upper_hall", name="hall_a09")]
    for s in probes:
        level_design.furnish(s)
        assert not [v for v in s["volumes"] if v["name"].startswith("dartboard_")], (s["name"], s["rooms"][0]["id"])


# --- the cigarette machine ------------------------------------------------------------------

def test_a_cigarette_machine_stands_in_a_club_a_bar_a_lobby_and_a_hall_and_nowhere_else():
    kinds = {("strip_club_x", "main_floor"): 1, ("country_club_x", "club_bar"): 1,
             ("bank_x", "lobby"): 1, ("museum_x", "upper_hall"): 1,
             ("office_x", "office"): 0, ("warehouse_x", "stock_room"): 0,
             ("deli_x", "kitchen"): 0, ("shop_x", "sales_floor"): 0}
    for (name, rid), want in kinds.items():
        s = _club(20.0, 12.0, rid=rid, name=name)
        level_design.furnish(s)
        room = s["rooms"][0]
        got = _mine(s, room, "cigarettes")
        assert len(got) == want, (name, rid, len(got))
        lanes = [level_design.dart_lane(v) for v in _mine(s, room, "dartboard")]
        for v in got:
            assert prop_species.species_for_name(v["name"]) == "cigarette_machine"
            assert v["collision"] == "convex" and v["material"] == "metal_painted"
            assert v["z"] == round(v["size_z"] / 2.0, 3)
            # against a wall, its front to the room
            x0, y0, x1, y1 = room["bounds"]
            edge = min(v["x"] - x0, x1 - v["x"], v["y"] - y0, y1 - v["y"])
            assert edge < 0.5, v
            for L in lanes:
                hx, hy = v["size_x"] / 2, v["size_y"] / 2
                assert not (v["x"] - hx < L[2] and v["x"] + hx > L[0]
                            and v["y"] - hy < L[3] and v["y"] + hy > L[1]), ("in a lane", v["name"])


def test_a_fixture_moves_nothing_the_room_was_furnished_with():
    """The pass runs after the whole room loop, from the spec alone: the rest
    of a room is what 0.135.1 furnished, piece for piece."""
    s = _club(20.0, 12.0)
    t = copy.deepcopy(s)
    level_design.furnish(s)
    saved = level_design.place_fixtures
    try:
        level_design.place_fixtures = lambda spec: 0
        level_design.furnish(t)
    finally:
        level_design.place_fixtures = saved
    fixtures = [v for v in s["volumes"] if v["name"].startswith(("dartboard_", "cigarettes_"))]
    assert fixtures
    assert [v for v in s["volumes"] if v not in fixtures] == t["volumes"]


# --- the library -------------------------------------------------------------------------------

def test_the_library_clubs_carry_their_boards_and_every_lane_is_clear():
    boards = 0
    for name in ("strip_club_a01", "strip_club_a02", "strip_club_a03"):
        with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as f:
            d = json.load(f)
        for r in d["rooms"]:
            mine = _mine(d, r, "dartboard")
            if not level_design.is_strip_club_room(r, d["name"]):
                assert not mine, (name, r["id"])
                continue
            b = r["bounds"]
            assert 1 <= len(mine) <= level_design.fixture_limit("dartboard", (b[2] - b[0]) * (b[3] - b[1])), (name, r["id"])
            for v in mine:
                _assert_board(d, r, v)
            boards += len(mine)
            assert len(_mine(d, r, "cigarettes")) == 1, (name, r["id"])
    assert boards == 11


def test_the_library_carries_the_fixture_pass_and_is_still_a_fixed_point_of_furnish():
    import migrate_club_fixtures
    import migrate_club_rooms
    import migrate_furnish_recipes
    counts = collections.Counter()
    for path in _library_specs():
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if not d.get("rooms"):
            continue
        once = copy.deepcopy(d)
        assert not migrate_club_fixtures.migrate(once), os.path.basename(path)
        assert once == d
        full = copy.deepcopy(d)
        name = os.path.basename(path)
        (migrate_club_rooms.migrate if name.startswith("strip_club_") else migrate_furnish_recipes.migrate)(full)
        assert json.dumps(full, sort_keys=True) == json.dumps(d, sort_keys=True), name
        for v in d["volumes"]:
            if v["name"].startswith(("dartboard_", "cigarettes_")):
                counts[v["name"].split("_r")[0]] += 1
    assert counts == {"dartboard": 11, "cigarettes": 121}, counts


def test_the_strip_club_preset_hangs_a_board():
    import presets
    for seed in range(4):
        s = presets.make("strip_club", name="strip_club_preset_%d" % seed, seed=seed)
        d = s if isinstance(s, dict) else s.to_dict()
        building = level_design.club_building_id(d)
        rooms = [r for r in d["rooms"] if level_design.is_strip_club_room(r, building)]
        got = [v for r in rooms for v in _mine(d, r, "dartboard")]
        assert got, seed
        for r in rooms:
            for v in _mine(d, r, "dartboard"):
                _assert_board(d, r, v)
