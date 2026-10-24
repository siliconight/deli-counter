"""Two video poker cabinets a store, and a filler's wall when none is free (0.228.0, the factory's roadmap 196).

0.202.0 dropped every fixture no held wall could take, and the six delis lost 18 of their 20 cabinets: in
deli_a01 both selling rooms are offered held wall slots and `_seed_clear` refuses every one, because the walls are
already stood. Now a cabinet takes a file cabinet's slot, then a vending machine's, in its own room, and a building
holds two. These run `place_fixtures` on copies of library specs as they were before the migration
(`tests_fixtures/store_cabinets/`, kept so the test does not change when the library does).

Run: python -m pytest -q tests/test_store_cabinets.py
"""
import copy
import json
from pathlib import Path

import level_design as L

HERE = Path(__file__).resolve().parent.parent
FIX = HERE / "tests_fixtures" / "store_cabinets"
KEY = "video_poker_store"


def _spec(name):
    return json.loads((FIX / (name + ".json")).read_text(encoding="utf-8"))


def _count(spec, stem):
    return sum(1 for v in spec.get("volumes") or [] if str(v.get("name", "")).startswith(stem + "_r"))


def test_deli_a01_reaches_two_by_taking_fillers(monkeypatch):
    # the displacement path, asked with the partition dial off: since 0.231.0 this cabinet may back onto a
    # partition, and deli_a01 then needs fewer fillers (test_cabinet_partitions.py)
    monkeypatch.setitem(L._PIECES[KEY], "backs_on_partitions", False)
    spec = _spec("deli_a01")
    assert _count(spec, KEY) == 0
    fillers = _count(spec, "cabinet_file") + _count(spec, "vending")
    L.place_fixtures(spec, keys={KEY})
    assert _count(spec, KEY) == 2
    assert _count(spec, "cabinet_file") + _count(spec, "vending") == fillers - 2
    # each cabinet brings its stool, named `bar_stool_<room tag>_<seq>_1` beside the cabinet's `<key>_<tag>_<seq>`
    names = {str(v["name"]) for v in spec["volumes"]}
    for v in spec["volumes"]:
        n = str(v["name"])
        if n.startswith(KEY + "_r"):
            assert L._SEAT_PIECES["stool"] + n[len(KEY):] + "_1" in names, n


def test_deli_a02_stops_at_two():
    spec = _spec("deli_a02")
    assert _count(spec, KEY) == 1
    L.place_fixtures(spec, keys={KEY})
    assert _count(spec, KEY) == 2


def test_a_store_already_at_two_is_untouched():
    spec = _spec("deli_a02")
    L.place_fixtures(spec, keys={KEY})
    again = copy.deepcopy(spec)
    L.place_fixtures(again, keys={KEY})
    assert again == spec


def test_keys_limits_the_pass_to_its_pieces():
    spec = _spec("deli_a01")
    before = {v["name"] for v in spec["volumes"]}
    L.place_fixtures(spec, keys={KEY})
    new = {v["name"] for v in spec["volumes"]} - before
    # the cabinets and the stools they bring, and nothing else
    stool = L._SEAT_PIECES["stool"] + "_r"
    assert any(n.startswith(KEY + "_r") for n in new), new
    assert all(n.startswith(KEY + "_r") or n.startswith(stool) for n in new), new


def test_the_dials_are_recorded():
    p = L._PIECES[KEY]
    assert p["displaces"] == ("cabinet_file", "vending") and p["most_building"] == 2
    assert L._PIECES["video_poker_bar"]["displaces"] == () and L._PIECES["video_poker_bar"]["most_building"] is None
