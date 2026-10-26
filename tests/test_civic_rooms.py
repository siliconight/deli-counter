"""A chapel, a courtroom, an assembly hall and a gallery are furnished as what they are (0.270.0, the factory's
roadmap 308). These words were one `hall` kind with a dining hall's recipe, and a chapel stood a service counter,
vending and dining tables. FAILS ON 0.269.0: no such kinds, no front, no facing rows, no pew."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level_design   # noqa: E402
import prop_species   # noqa: E402


def _spec(rid, w=24.0, d=12.0, door_x=None, volumes=()):
    """One room the shell, a door in its west (low-x) wall unless `door_x` says where in the south one."""
    s = {"name": "civic_probe", "seed": 1997, "story_height": 4.0,
         "footprint_x": w, "footprint_y": d, "n_stories": 1,
         "rooms": [{"id": rid, "story": 0, "role": "public_entry",
                    "bounds": [-w / 2, -d / 2, w / 2, d / 2], "combat_range": "medium"}],
         "ext_walls": [{"wall": "W", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.8}]}]
         if door_x is None else
         [{"wall": "S", "story": 0, "openings": [{"kind": "door", "pos": door_x / w, "width": 1.8}]}],
         "volumes": list(volumes), "partitions": [], "stairs": []}
    return s


def test_the_civic_words_have_their_own_kinds():
    k = level_design._room_kind
    assert k({"id": "chapel"}) == "chapel"
    assert k({"id": "viewing_wing"}) == "chapel"
    assert k({"id": "main_courtroom"}) == "courtroom"
    assert k({"id": "courtrooms"}) == "courtroom"
    assert k({"id": "assembly_hall"}) == "assembly"
    assert k({"id": "north_galleries"}) == "gallery"
    assert k({"id": "artifact_wing"}) == "gallery"
    assert "hall" not in level_design._RECIPES
    assert prop_species.species_for_name("pew_row_a") == "pew"


def test_the_front_is_the_end_away_from_the_door():
    s = _spec("chapel")
    assert level_design.room_front(s, s["rooms"][0]) == (True, 1)


def test_an_authored_row_turns_the_axis():
    row = {"name": "pew_row_a", "x": 0.0, "y": 0.0, "z": 0.45, "size_x": 8.0, "size_y": 0.9, "size_z": 0.9,
           "collision": "convex", "material": "wood"}
    s = _spec("chapel", door_x=0.0, volumes=[row])
    along_x, _sign = level_design.room_front(s, s["rooms"][0])
    assert along_x is False


def test_a_chapel_is_an_altar_and_pews_all_facing_it():
    s = _spec("chapel")
    level_design.furnish(s)
    names = [v["name"] for v in s["volumes"]]
    pews = [v for v in s["volumes"] if v["name"].startswith("pew_")]
    assert len(pews) >= 4, names
    assert sum(n.startswith("table_work_") for n in names) == 1
    assert not any(n.startswith(("counter_service_", "vending_", "table_dining_", "chair_waiting_")) for n in names)
    assert len({v.get("rot_z") for v in pews}) == 1, "every pew faces one way"
    altar = next(v for v in s["volumes"] if v["name"].startswith("table_work_"))
    assert altar["x"] > max(v["x"] for v in pews), "the altar stands at the front, beyond the rows"
    # a centre aisle: no pew crosses the room's middle line across the rows
    assert not any(abs(v["y"]) < v["size_y"] / 2.0 for v in pews)


def test_a_courtroom_has_its_bench_and_a_well_before_the_public():
    s = _spec("courtroom", w=30.0, d=14.0)
    level_design.furnish(s)
    by = lambda stem: [v for v in s["volumes"] if v["name"].startswith(stem + "_")]
    bench, tables, pews = by("counter_service"), by("table_work"), by("pew")
    assert len(bench) == 1 and len(tables) == 2 and pews
    assert bench[0]["x"] > max(t["x"] for t in tables) > max(p["x"] for p in pews)


def test_a_gallery_keeps_its_floor_open():
    s = _spec("galleries", w=30.0, d=14.0)
    level_design.furnish(s)
    r = s["rooms"][0]
    assert level_design.room_floor_share(s, r) < 0.12
    assert not any(v["name"].startswith(("counter_service_", "vending_", "table_dining_")) for v in s["volumes"])
