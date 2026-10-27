"""A bank's walls are finished inside, and it hangs CCTV cameras, keeps potted plants and a wall clock (0.282.0, the
factory's roadmap 321).

The walker's bank comps (the factory's docs/reference/BANK_INTERIOR_COMPS.md) paint every public room's walls; a bank
built of concrete showed raw concrete in its lobby and offices (docs/findings/bank_interior/, frames 01-06). And the
walker asked "were there cctv cameras in the 90s?": yes, since the Bank Protection Act of 1968 -- Zoo's
`security_camera`, which no building placed.

The comps keep plants in planters by the windows and counters and a clock over the line (Zoo 1.136.0's `planter` and
`wall_clock`); a `potted_plant`, because `planter` is the library's long planter boxes, which stay boxes.

FAILS ON 0.281.0: a bank's concrete walls carry no `material_in`, and no bank hangs a camera, a plant or a clock.
"""
import json
import math
import os

import pytest

import level_design
import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
BANKS = ("bank_branch_a02", "bank_branch_a03", "bank_branch_a04", "bank_job", "bank_tower_a01", "bank_tower_a02",
         "bank_tower_a03")


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _in(v, room):
    x0, y0, x1, y1 = room["bounds"]
    return x0 <= v.get("x", 1e9) <= x1 and y0 <= v.get("y", 1e9) <= y1


def _story(d, v):
    """The storey a hung piece is in, by its CENTRE: `level_design._volume_story` guesses from a volume's base and
    rounds, so a camera under a basement's ceiling (base -0.8 m at a 3.6 m storey) reads as the ground floor -- the
    first reading of this test's counts was that misreading, not the placement."""
    return int(math.floor(float(v["z"]) / float(d.get("story_height") or 3.6)))


def test_the_camera_routes_to_zoos_species_long_in_depth():
    assert prop_species.species_for_name("security_camera_rcce455f7_7") == "security_camera"
    assert "security_camera" in prop_species.DEPTH_LONG
    p = level_design._PIECES["security_camera"]
    assert p["where"] == "wall" and p["collision"] == "none" and p["under"]
    assert "security_camera" in level_design._RECIPES["bank_lobby"]["fixtures"]
    assert "security_camera" in level_design._RECIPES["bank_vault"]["fixtures"]
    assert "security_camera" not in (level_design._RECIPES["lobby"].get("fixtures") or ())


def test_every_bank_hangs_cameras_in_its_lobby_and_vaults():
    for name in BANKS:
        d = _spec(name)
        b = level_design.club_building_id(d)
        cams = [v for v in d["volumes"] if v["name"].startswith("security_camera")]
        lobbies = [r for r in d["rooms"] if level_design._room_kind(r, b) == "bank_lobby"]
        assert lobbies, name
        for r in lobbies:
            story = int(r.get("story", 0) or 0)
            here = [v for v in cams if _in(v, r) and _story(d, v) == story]
            assert len(here) >= 2, (name, r["id"], len(here))
        vaults = [r for r in d["rooms"] if level_design._room_kind(r, b) == "bank_vault"]
        assert vaults, name
        for r in vaults:
            story = int(r.get("story", 0) or 0)
            assert [v for v in cams if _in(v, r) and _story(d, v) == story], (name, r["id"])
        # every camera hangs above a head and below its own storey's ceiling
        sh = float(d.get("story_height") or 3.6)
        for v in cams:
            s = _story(d, v)
            top = float(v["z"]) + float(v["size_z"]) / 2.0 - s * sh
            assert 2.0 < top <= sh, (name, v["name"], top)


def test_no_other_building_hangs_one():
    import glob
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        n = os.path.basename(p)[:-5]
        if n.startswith("lf_") or n in BANKS:
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        assert not any(str(v.get("name", "")).startswith("security_camera") for v in d.get("volumes") or []), n


@pytest.mark.parametrize("name", BANKS)
def test_a_banks_concrete_walls_are_plaster_inside_above_grade_and_concrete_below(name):
    path = os.path.join(BUILD, name + ".slots.json")
    if not os.path.exists(path):
        pytest.skip("%s is not built" % name)
    slots = json.load(open(path, encoding="utf-8"))["slots"]
    above = below = 0
    for s in slots:
        parts = str(s.get("wall") or "").split("_")
        if not (len(parts) >= 3 and parts[0] == "ext" and s.get("material") == "concrete"
                and s.get("role") in ("wall", "window", "doorway", "breach") and not s.get("glazing")):
            continue
        if int(parts[1]) >= 0:
            above += 1
            assert s.get("material_in") == "plaster", (name, s["slot_id"])
        else:
            below += 1
            assert "material_in" not in s, (name, s["slot_id"])
    assert above, name


def test_the_plant_and_the_clock_route_to_zoos_species_and_the_planter_boxes_stay_boxes():
    assert prop_species.species_for_name("potted_plant_rcce455f7_8") == "planter"
    assert prop_species.species_for_name("wall_clock_rcce455f7_9") == "wall_clock"
    assert prop_species.species_for_name("planter_r1234abcd_2") is None
    r = level_design._RECIPES["bank_lobby"]
    assert "potted_plant" in r["wall"] and "wall_clock" in r["fixtures"]


def test_every_banks_lobby_keeps_plants_and_a_clock():
    for name in BANKS:
        d = _spec(name)
        b = level_design.club_building_id(d)
        for r in [r for r in d["rooms"] if level_design._room_kind(r, b) == "bank_lobby"]:
            story = int(r.get("story", 0) or 0)
            mine = [v["name"] for v in d["volumes"] if _in(v, r) and _story(d, v) == story]
            assert sum(n.startswith("potted_plant") for n in mine) >= 1, (name, r["id"])
            assert sum(n.startswith("wall_clock") for n in mine) == 1, (name, r["id"])
