"""0.133.0 -- the `strip_club` preset, and a club that stays a club when
somebody else names it.

Cold run 9055 was refused at graybox: "brief archetype 'strip_club' matches
no DC preset". A mission's own building is GENERATED from a preset
(`presets.make`); the lot anchors on the library family of the same name
(`strip_club_a01`..`a03`), and there was no recipe. On 0.132.1 every test
here fails at `presets.make("strip_club")`.

The second half is the name. 0.132.0 reads the club kind off the building's
id, and Level Factory names the level it generates `lf_<mission>_<seed>` --
so a club it built would have been a shop floor with a vending machine
(0.131.0's defect, one layer up). The recipe stamps `preset: "strip_club"`
and `level_design.club_building_id` reads it beside the name.

Measured on a scratch build through `new_level.py --preset strip_club --name
lf_club_block_001_7 --mode heist --seed 7` (the adapter's own arguments;
Blender and the Godot nav gate, not run here): 595 navmesh polys, 2/2
interior markers reachable from the spawn, navigable: yes; 30 light anchors,
3 club rooms lit as a club.
"""
import collections
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import layout_lint      # noqa: E402
import level_design     # noqa: E402
import navigability     # noqa: E402
import presets          # noqa: E402
import prop_species     # noqa: E402
import tactical         # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402

CLUB_ROOMS = ("main_floor", "back_bar", "vip_lounge")
OTHER_KINDS = {"dressing_room": "locker", "cash_office": "vault",
               "stockroom": "storage", "kitchen": "kitchen"}
CLUB_SPECIES = {"club_stage", "bar_stool", "counter", "booth_seat", "neon_sign",
                "crt_tv", "cocktail_table", "club_chair", "vending_machine"}
_TAGGED = re.compile(r"_r[0-9a-f]{8}_")
#: What Level Factory calls the level it builds for the 9055 brief.
LF_NAME = "lf_club_block_001_7"
#: Seeds swept where a claim must hold for every building, not one.
SEEDS = range(12)


def _make(name="strip_club_preset", **kw):
    return presets.make("strip_club", name=name, **kw)


def _species(spec, room):
    tag = level_design._room_tag(room)
    mine = [v for v in spec["volumes"] if f"_{tag}_" in v["name"]]
    return collections.Counter(prop_species.species_for_name(v["name"]) for v in mine)


def test_the_preset_exists_and_is_one_windowless_storey():
    s = _make()
    assert s["preset"] == "strip_club" and s["name"] == "strip_club_preset"
    assert s["n_stories"] == 1 and not s["has_basement"]
    assert not s["stairs"] and not s["ladders"]
    assert 30.0 <= s["footprint_x"] <= 36.0 and 22.0 <= s["footprint_y"] <= 24.0
    kinds = [o["kind"] for w in s["ext_walls"] for o in w["openings"]]
    assert "window" not in kinds, kinds
    doors = {w["wall"] for w in s["ext_walls"] for o in w["openings"] if o["kind"] == "door"}
    assert doors == {"S", "N"}, doors
    assert "breach" in kinds
    assert s["default_material"] == "paint_block"
    assert all(w["material"] == "paint_block" for w in s["ext_walls"])
    assert [r["id"] for r in s["rooms"]] == list(CLUB_ROOMS[:2]) + [
        "vip_lounge", "dressing_room", "cash_office", "stockroom", "kitchen"]
    assert presets.REGISTRY["strip_club"] is presets.strip_club


def test_the_club_rooms_are_claimed_under_either_name():
    for name in ("strip_club_preset", LF_NAME):
        s = _make(name)
        bid = level_design.club_building_id(s)
        assert "strip_club" in bid, (name, bid)
        for r in s["rooms"]:
            kind = level_design._room_kind(r, bid)
            if r["id"] in CLUB_ROOMS:
                assert kind == "strip_club", (name, r["id"], kind)
                assert r.get("floor_material") == "carpet_club", (name, r["id"])
            else:
                assert kind == OTHER_KINDS[r["id"]], (name, r["id"], kind)
                assert not r.get("floor_material"), (name, r["id"])
        # the wall between the main floor and the back bar, and the long wall
        # with club rooms on both faces, wear the club's paper; the office's
        # walls do not
        mats = {(p["axis"], p["pos"]): p["material"] for p in s["partitions"]}
        assert mats[("Y", 5.0)] == "wallpaper_club" and mats[("X", 2.0)] == "wallpaper_club"
        assert mats[("Y", 0.0)] == "concrete" and mats[("Y", 6.0)] == "concrete"
    # and the loaded spec carries the recipe's name for the builder
    sp = spec_from_dict(_make(LF_NAME))
    assert sp.preset == "strip_club"
    assert "strip_club" in level_design.club_building_id(sp)


def test_a_name_alone_is_not_enough_and_a_preset_alone_is():
    assert not level_design.is_strip_club_room({"id": "main_floor"}, "lf_club_block_001_7")
    assert level_design.is_strip_club_room(
        {"id": "main_floor"},
        level_design.club_building_id({"name": LF_NAME, "preset": "strip_club"}))
    assert level_design.club_building_id({"name": "deli_a01"}) == "deli_a01"


def _seeded():
    """The building under the name and seeds Level Factory gives it: the
    adapter always passes `--seed`, so one seed describes one building."""
    for seed in SEEDS:
        yield seed, _make(f"lf_club_block_001_{seed}", seed=seed)


def test_every_club_room_is_furnished_as_a_club_and_nothing_else():
    """What holds at EVERY seed. The wall run is shuffled and cut to the
    room's budget, so a sign, a TV, a sofa or a vending machine is not in
    every room at every seed -- measured over seeds 0-49 when this was
    written: no neon sign in `main_floor` at 5, in `vip_lounge` at 38, and
    none anywhere in the building at 3. That is the 0.132.0 recipe, not this
    preset, and it is not asserted here; the stage, its stools and the kind
    are."""
    for seed, s in _seeded():
        for r in s["rooms"]:
            sp = _species(s, r)
            if r["id"] not in CLUB_ROOMS:
                assert not (set(sp) & CLUB_SPECIES), (seed, r["id"], sp)
                continue
            assert set(sp) <= CLUB_SPECIES, (seed, r["id"], sp)
            assert sp["club_stage"] >= 1 and sp["bar_stool"] >= 3, (seed, r["id"], sp)
            # `seed_cover` left the room to the recipe: no kiosk, planter or
            # crate stack under the club's name (every recipe piece is tagged)
            x0, y0, x1, y1 = r["bounds"]
            seeded = [v["name"] for v in s["volumes"]
                      if not _TAGGED.search(v["name"])
                      and x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1]
            assert seeded == [], (seed, r["id"], seeded)
        # the main floor is over 300 m2: a bar stage in its middle, a second bar
        main = s["rooms"][0]
        assert _species(s, main)["counter"] == 1, seed
        stage = next(v for v in s["volumes"] if v["name"].startswith("stage_bar_")
                     and f"_{level_design._room_tag(main)}_" in v["name"])
        x0, y0, x1, y1 = main["bounds"]
        assert (stage["x"], stage["y"]) == ((x0 + x1) / 2, (y0 + y1) / 2), (seed, stage)


def test_every_room_has_shelter_at_every_seed():
    for seed, s in _seeded():
        for r in s["rooms"]:
            assert level_design._room_has_shelter(s, r), (seed, r["id"])


def test_lint_is_clean_under_either_name_and_every_seed():
    for name in ("strip_club_preset", LF_NAME):
        s = _make(name)
        _, fails, warns = layout_lint.lint_spec(s, name)
        assert fails == [], (name, fails)
        assert warns == [], (name, warns)
    for seed, s in _seeded():
        _, fails, _ = layout_lint.lint_spec(s, s["name"])
        assert fails == [], (seed, fails)


def test_the_objective_is_reachable_by_every_offline_instrument():
    for seed, s in _seeded():
        assert layout_lint.reachability_findings(s) == [], seed
        sp = spec_from_dict(s)
        errors, _warnings, card = tactical.analyze(sp)
        assert errors == [], (seed, errors)
        assert card["mode"] == "heist" and card["unreachable_objectives"] == 0, (seed, card)
        nerrors, _, _ = navigability.check(sp)
        assert nerrors == [], (seed, nerrors)
        # the objective, the extraction and the spawn stand in the rooms they name
        for m in s["markers"]:
            if m["type"] in ("objective", "extraction", "crew_spawn"):
                r = next(r for r in s["rooms"] if r["id"] == m["room"])
                x0, y0, x1, y1 = r["bounds"]
                assert x0 <= m["x"] <= x1 and y0 <= m["y"] <= y1, (seed, m)


def test_assault_mode_builds_too():
    s = _make(mode="assault")
    _, fails, _ = layout_lint.lint_spec(s, s["name"])
    assert fails == [], fails
    errors, _, _ = tactical.analyze(spec_from_dict(s))
    assert errors == [], errors
    types = collections.Counter(m["type"] for m in s["markers"])
    assert types["attacker_spawn"] == 2 and types["defender_spawn"] == 1


def test_enrich_is_idempotent_on_the_club():
    for seed, s in _seeded():
        again = copy.deepcopy(s)
        report = level_design.enrich(again)
        assert report["furnished"] == 0 and report["cover_seeded"] == 0, (seed, report)
        assert json.dumps(again, sort_keys=True) == json.dumps(s, sort_keys=True), seed


def test_the_recipe_is_deterministic():
    a, b = _make(), _make()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


if __name__ == "__main__":
    for k, fn in sorted(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            print(f"[ok] {k}")
