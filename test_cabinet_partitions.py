"""A store's video poker cabinet may stand against the partition it backs onto (0.231.0, the factory's roadmap 196).

`_seed_clear` keeps every piece's centre a metre off every partition's line, which refused every slot a held
partition wall offers -- a cabinet backed against one stands its centre about half a metre off it -- and left four
stores short of the walker's two. The cabinet's `backs_on_partitions` dial exempts the one partition behind it;
every other partition and every other rule still apply. These run `place_fixtures` on copies of library specs as
they were before the change (`tests_fixtures/cabinet_partitions/`), and read the library as it is after.

Run: python -m pytest -q test_cabinet_partitions.py
"""
import glob
import json
import math
from pathlib import Path

import level_design as L

HERE = Path(__file__).resolve().parent
FIX = HERE / "tests_fixtures" / "cabinet_partitions"
KEY = "video_poker_store"


def _spec(name):
    return json.loads((FIX / (name + ".json")).read_text(encoding="utf-8"))


def _cabinets(spec):
    return [v for v in spec.get("volumes") or [] if str(v.get("name", "")).startswith(KEY + "_r")]


def _partition_distance(p, x, y):
    if p["axis"] == "Y":
        return math.hypot(x - p["pos"], y - max(p["start"], min(y, p["end"])))
    return math.hypot(x - max(p["start"], min(x, p["end"])), y - p["pos"])


def _story_of(spec, v):
    return int(round((float(v["z"]) - float(v["size_z"]) / 2.0) / float(spec["story_height"])))


def _near_partitions(spec, v):
    story = _story_of(spec, v)
    return [p for p in spec.get("partitions") or []
            if p.get("story", 0) == story and _partition_distance(p, v["x"], v["y"]) < 1.0]


def test_pharmacy_reaches_two_against_a_partition():
    spec = _spec("pharmacy_a01")
    before = {v["name"] for v in _cabinets(spec)}
    assert len(before) == 1
    L.place_fixtures(spec, keys={KEY})
    new = [v for v in _cabinets(spec) if v["name"] not in before]
    assert len(new) == 1
    # it stands where the metre refused it: within a metre of exactly one partition, the one behind it
    near = _near_partitions(spec, new[0])
    assert len(near) == 1, near
    assert _partition_distance(near[0], new[0]["x"], new[0]["y"]) < 0.7


def test_the_fuel_stop_reaches_two():
    spec = _spec("fuel_stop_heist")
    assert len(_cabinets(spec)) == 0
    L.place_fixtures(spec, keys={KEY})
    assert len(_cabinets(spec)) == 2


def test_no_cabinet_in_the_library_stands_near_a_partition_it_does_not_back_onto():
    for path in sorted(glob.glob(str(HERE / "specs" / "*.json"))):
        if Path(path).name.startswith("lf_"):
            continue
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
        for v in _cabinets(spec):
            near = _near_partitions(spec, v)
            assert len(near) <= 1, (Path(path).name, v["name"], near)
            if near:
                assert _partition_distance(near[0], v["x"], v["y"]) < 0.7, (Path(path).name, v["name"])


def test_the_dial_is_the_cabinets_alone():
    assert L._PIECES[KEY]["backs_on_partitions"] is True
    others = [k for k, p in L._PIECES.items() if k != KEY and p["backs_on_partitions"]]
    assert others == []
