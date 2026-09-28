"""0.148.0 -- a walk-in cooler has its reach-in doors.

`migrate_cooler_wall.py` puts Zoo 1.12.0's `cooler_run` on the walk-in's
customer side of every store spec that has a walk-in and no cooler wall:
clear of the partition's doors, with an aisle in front, facing the room.
"""
import json
import os

import migrate_cooler_wall as M

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def test_every_store_with_a_walk_in_has_its_cooler_wall():
    assert M.main(["--check"]) == 0, "run: python migrate_cooler_wall.py"
    for name in ("gas_station_a02", "fuel_stop_heist"):
        runs = [v for v in _load(name)["volumes"] if v["name"] == M.NAME]
        assert len(runs) == 1, name


def test_a02s_cooler_wall_faces_food_service_clear_of_the_door_and_the_aisle():
    d = _load("gas_station_a02")
    v = next(x for x in d["volumes"] if x["name"] == M.NAME)
    x0, x1 = v["x"] - v["size_x"] / 2, v["x"] + v["size_x"] / 2
    y0, y1 = v["y"] - v["size_y"] / 2, v["y"] + v["size_y"] / 2
    # its back 0.17 m off the partition at y = 1, standing in food service
    assert abs(y1 - (1.0 - M.WALL_BACK)) < 1e-6 and abs((y1 - y0) - M.DEPTH) < 1e-6
    food = next(r["bounds"] for r in d["rooms"] if r["id"] == "food_service")
    assert food[0] <= x0 and x1 <= food[2]
    # clear of cooler_door_1 (x 9.6, 1.25 wide) and its clearance
    assert x0 >= 9.6 + 1.25 / 2 + M.DOOR_CLEAR - 1e-6
    # nothing stands in the aisle in front of it
    for w in d["volumes"]:
        if w is v or w["size_x"] * w["size_y"] > 400:
            continue
        wx0, wx1 = w["x"] - w["size_x"] / 2, w["x"] + w["size_x"] / 2
        wy0, wy1 = w["y"] - w["size_y"] / 2, w["y"] + w["size_y"] / 2
        overlaps_x = wx1 > x0 and wx0 < x1
        overlaps_aisle = wy1 > y0 - M.AISLE and wy0 < y1
        assert not (overlaps_x and overlaps_aisle), w["name"]
    # long in x and the room on its -y side: unturned, no rot_z (its doors
    # face -y, measured on cold run 9096's shipped transforms)
    assert v["size_x"] > v["size_y"] and "rot_z" not in v
    assert v["size_x"] >= M.MIN_RUN


def test_the_migration_is_idempotent_and_leaves_existing_coolers(tmp_path):
    for name in ("gas_station_a02", "gas_station"):
        d = _load(name)
        d["volumes"] = [v for v in d["volumes"] if v["name"] != M.NAME] if name == "gas_station_a02" else d["volumes"]
        (tmp_path / (name + ".json")).write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    before_preset = (tmp_path / "gas_station.json").read_bytes()
    assert M.main(["--check", "--dir", str(tmp_path)]) == 1
    assert M.main(["--dir", str(tmp_path)]) == 0
    first = (tmp_path / "gas_station_a02.json").read_bytes()
    assert M.main(["--dir", str(tmp_path)]) == 0
    assert (tmp_path / "gas_station_a02.json").read_bytes() == first
    assert (tmp_path / "gas_station.json").read_bytes() == before_preset


def test_a_side_with_no_room_is_refused_not_forced():
    d = _load("gas_station_a02")
    d["volumes"] = [v for v in d["volumes"] if v["name"] != M.NAME]
    d["volumes"].append({"name": "crate_wall", "x": 11.5, "y": -0.5, "size_x": 9.0, "size_y": 1.0,
                         "size_z": 1.0})
    vol, why = M.plan_cooler(d)
    assert vol is None and "clear" in why
