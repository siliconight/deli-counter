"""The poster walls (0.163.0): Zoo's `poster_wall` runs hung as fixtures.

The walker, 2026-09-29, choosing where posters go: strip club interiors, bar
interiors, exterior alley walls and poles, store windows and walls. This is
the three interior kinds. What is held here, on the library as the specs
carry it and on the rules that put them there:

  * every strip club room hangs club posters, and only the rooms whose id
    says bar or sell hang the bar's and the store's (the `club` and
    `shop_floor` kinds are wider than that, and the gate is measured);
  * a run is Zoo's: its species, its paper, its band height, its family as
    the form, collision none, centred on the gameplay camera's eye;
  * a store's runs are off the storefront glass;
  * no room shows the same run twice (the poster baseline's "identical pairs
    side by side": 5 rooms of 48 before `_distinct_variant`).
"""
import collections
import glob
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent_contract  # noqa: E402
import level_design  # noqa: E402
import prop_species  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PIECES = {"poster_wall_club": "club", "poster_wall_bar": "bar", "poster_wall_store": "store"}
#: Zoo's `poster_wall_forms.band_height(family)` at 1.32.0: the sheet plus the
#: family's wander. `test_the_band_is_zoo_s` pins it when Zoo is beside this repo.
BAND = {"club": 0.64, "bar": 0.5, "store": 0.6}
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")


def _library():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("rooms"):
            yield d


def _runs(d):
    return [v for v in d.get("volumes") or [] if str(v.get("name", "")).startswith("poster_wall_")]


def _room_of(d, v):
    tags = {level_design._room_tag(r): r for r in d["rooms"]}
    return next(r for t, r in tags.items() if f"_{t}_" in v["name"])


def _tokens(room):
    return set(str(room.get("id", "")).lower().replace("-", "_").split("_"))


def _stem(v):
    return "_".join(v["name"].split("_")[:3])


# --- the pieces ------------------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(PIECES))
def test_a_piece_is_zoo_s_poster_wall_on_paper(key):
    p = level_design._PIECES[key]
    assert prop_species.species_for_name(f"{key}_r0123abcd_4") == "poster_wall"
    assert level_design._prop_material({"materials": []}, key) == "paper"
    assert p["form"] == PIECES[key] and p["collision"] == "none" and p["where"] == "wall"
    assert p["lift"] == agent_contract.eye_height()
    # 0.170.0: a run hangs a step off the eye, never more than 0.25 m, and
    # level is one of the steps
    assert p["lift_steps"] and 0.0 in p["lift_steps"]
    assert all(abs(s) <= 0.25 for s in p["lift_steps"])
    assert all(h == BAND[PIECES[key]] for _w, _d, h in p["sizes"])
    # four, so the variant is the NAME's and not the building's (`_make_volume`)
    assert level_design.variant_count(p) == 4 and p["distinct"]


def test_the_card_shop_poster_still_routes_as_it_did():
    """`poster_wall`'s rows go ABOVE the `poster` rows; `poster` must keep
    its own."""
    assert prop_species.species_for_name("poster_r0123abcd_2") == "poster"
    assert level_design._prop_material({"materials": []}, "poster") == "metal_bare"


def test_the_band_is_zoo_s():
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    from zoo_keeper.core import poster_wall_forms as F
    for fam, h in BAND.items():
        assert F.band_height(fam) == h, fam


# --- the library -------------------------------------------------------------------------


def test_every_strip_club_room_hangs_club_posters():
    seen = 0
    for d in _library():
        if not level_design._strip_club_building(level_design.club_building_id(d)):
            continue
        for r in d["rooms"]:
            if not level_design.is_strip_club_room(r, d["name"]):
                continue
            seen += 1
            mine = [v for v in _runs(d) if _room_of(d, v) is r]
            assert mine and all(_stem(v) == "poster_wall_club" for v in mine), (d["name"], r["id"])
    assert seen >= 5


def test_a_run_hangs_where_its_family_belongs():
    """The bar's in a bar, the store's where something is sold -- the gate,
    over every run in the library."""
    for d in _library():
        for v in _runs(d):
            room = _room_of(d, v)
            only = level_design._PIECES[_stem(v)]["rooms"]
            if only:
                assert _tokens(room) & only, (d["name"], room["id"], v["name"])


def test_the_gate_is_what_keeps_them_out():
    """A control: the kinds are wider than the gate. Without it, measured when
    this was written, sale posters went on 158 walls including warehouse,
    foundry, arena, office and self-storage floors; with it, 95. And a country
    club's lounge is the `club` kind -- it gets a cigarette machine -- and no
    gig bill."""
    kinds = collections.Counter()
    for d in _library():
        building = level_design.club_building_id(d)
        for r in d["rooms"]:
            kind = level_design._room_kind(r, building)
            for key in ("poster_wall_store", "poster_wall_bar"):
                if key in (level_design._RECIPES[kind].get("fixtures") or ()) \
                        and not (_tokens(r) & level_design._PIECES[key]["rooms"]):
                    kinds[key] += 1
                    assert not any(_room_of(d, v) is r for v in _runs(d)), (d["name"], r["id"])
    assert kinds["poster_wall_store"] and kinds["poster_wall_bar"], kinds


def test_a_run_is_zoo_s_slot():
    for d in _library():
        sh = level_design._story_height(d)
        for v in _runs(d):
            fam = PIECES[_stem(v)]
            story = round((v["z"] - agent_contract.eye_height()) / sh)
            # 0.170.0: at the eye plus the run's OWN step -- its room's k-th
            # run of its kind, in the order the pass numbered them
            p = level_design._PIECES[_stem(v)]
            rtag, seq = v["name"][len(_stem(v)) + 1:].rsplit("_", 1)
            k = sorted(int(u["name"].rsplit("_", 1)[1]) for u in _runs(d)
                       if u["name"].startswith(f"{_stem(v)}_{rtag}_")).index(int(seq))
            want = agent_contract.eye_height() + level_design._lift_step(p, _stem(v), rtag, k)
            assert v["z"] == round(story * sh + round(want, 3), 3), v["name"]
            assert v["form"] == fam and v["collision"] == "none" and v["material"] == "paper"
            assert v["size_z"] == BAND[fam] and min(v["size_x"], v["size_y"]) == 0.01, v["name"]
            assert any(m.get("id") == "paper" for m in d.get("materials") or []), d["name"]


def test_the_runs_do_not_all_hang_at_one_height():
    """0.170.0, the placement guide: "identical spacing, height, rotation,
    or mounting pattern on every wall" is the tell. Across the library each
    family's runs take every one of its steps."""
    seen = {}
    for d in _library():
        sh = level_design._story_height(d)
        for v in _runs(d):
            story = round((v["z"] - agent_contract.eye_height()) / sh)
            seen.setdefault(_stem(v), set()).add(round(v["z"] - story * sh - agent_contract.eye_height(), 3))
    for key in PIECES:
        steps = set(level_design._PIECES[key]["lift_steps"])
        # more than one height, and none that is not a step (the library has
        # eight bar runs: too few to promise every step is drawn)
        assert seen[key] <= steps and len(seen[key]) >= 2, (key, seen[key])


def test_a_store_s_runs_are_off_the_glass():
    """A run hung inside a storefront faces the shop and shows the street its
    back; a window poster is a rule of its own."""
    for d in _library():
        hx, hy = float(d.get("footprint_x", 0.0)) / 2.0, float(d.get("footprint_y", 0.0)) / 2.0
        wt = float(d.get("wall_thick") or 0.3)
        sh = level_design._story_height(d)
        for v in _runs(d):
            if _stem(v) != "poster_wall_store":
                continue
            story = round((v["z"] - agent_contract.eye_height()) / sh)
            glazed = level_design._glazed_walls(d, story)
            near = {"S": abs(v["y"] + hy) < wt + 0.1, "N": abs(v["y"] - hy) < wt + 0.1,
                    "W": abs(v["x"] + hx) < wt + 0.1, "E": abs(v["x"] - hx) < wt + 0.1}
            assert not any(near[w] for w in glazed), (d["name"], v["name"], glazed)


def test_no_room_shows_the_same_run_twice():
    rooms = 0
    for d in _library():
        by_room = collections.defaultdict(list)
        for v in _runs(d):
            by_room[_room_of(d, v)["id"]].append((v["size_x"], v["size_y"], v.get("variant", 0)))
        for rid, runs in by_room.items():
            rooms += 1
            assert len(runs) == len(set(runs)), (d["name"], rid, runs)
    assert rooms >= 40


def test_a_distinct_variant_moves_off_a_taken_one_and_refuses_when_none_is_left():
    vol = {"name": "poster_wall_club_r0123abcd_5", "size_x": 2.4, "size_y": 0.01, "size_z": 0.64,
           "variant": 1}
    spec = {"volumes": [dict(vol, name="poster_wall_club_r0123abcd_2", variant=1),
                        dict(vol, name="poster_wall_club_r0123abcd_3", variant=2)]}
    v = dict(vol)
    assert level_design._distinct_variant(spec, "poster_wall_club", "r0123abcd", v, 4)
    assert v["variant"] == 3
    # another size is not a clash
    w = dict(vol, size_x=1.6)
    assert level_design._distinct_variant(spec, "poster_wall_club", "r0123abcd", w, 4)
    assert w["variant"] == 1
    # every variant taken at this size: refused, so the placer tries elsewhere
    spec["volumes"] += [dict(vol, name="poster_wall_club_r0123abcd_6"),
                        dict(vol, name="poster_wall_club_r0123abcd_7", variant=3)]
    spec["volumes"][-2].pop("variant")
    assert not level_design._distinct_variant(spec, "poster_wall_club", "r0123abcd", dict(vol), 4)


def test_the_fixture_pass_is_idempotent_on_the_library():
    import copy
    for d in _library():
        e = copy.deepcopy(d)
        assert level_design.place_fixtures(e) == 0, d["name"]
