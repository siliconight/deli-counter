"""A den's windows are drawn shut (0.205.0).

The walker, 2026-10-09, walking club_block_014 (roadmap 219, note 2): "the
windows in any 'den of sin' building should have curtains or drapes or blinds
So people outside can't see in, and you keep the streetlight light out of the
club". What is held: every window of a strip club hangs a drape -- on the room
side, over the window the BUILDER cut, wider and longer than the glass, facing
the room -- and no other building does; the rule is idempotent; the name
reaches Zoo's species and the size falls in its genome; a draped window draws
no window light, and every other window keeps its light's id; the library's
two windowed clubs carry their drapes, and their built lights say so.
"""
from __future__ import annotations

import json
import os

import pytest

import level_design as LD
import lights
import migrate_den_drapes
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))


def _spec(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def _built(name, kind):
    with open(os.path.join(HERE, "build", "%s.%s.json" % (name, kind)), encoding="utf-8") as fh:
        return json.load(fh)


def _windows(name):
    return [o for o in _built(name, "gameplay")["openings"] if o.get("kind") == "window"]


@pytest.mark.parametrize("name", ["strip_club_a01", "strip_club_a03"])
def test_every_window_of_a_strip_club_hangs_a_drape_over_the_window_built(name):
    drapes = LD.plan_den_drapes(_spec(name))
    built = _windows(name)
    assert len(drapes) == len(built) > 0
    for o in built:
        mine = [v for v in drapes if lights._drapes_window(v, o)]
        assert len(mine) == 1, (o, drapes)
        v = mine[0]
        side = o["wall"].rsplit("_", 1)[-1]
        along, wide = ("x", v["size_x"]) if side in ("N", "S") else ("y", v["size_y"])
        # centred on the window the builder cut (snapped, not `pos * run`)
        assert v[along] == pytest.approx(o[along], abs=1e-6), (v, o)
        assert wide == pytest.approx(o["width"] + 2 * LD.DRAPE_SIDE)
        foot = v["z"] - v["size_z"] / 2.0
        top = v["z"] + v["size_z"] / 2.0
        floor = int(o.get("story", 0)) * LD._story_height(_spec(name))
        assert foot == pytest.approx(floor + o["sill"] - LD.DRAPE_BELOW, abs=1e-3)
        assert top > floor + o["sill"] + o["height"]                      # past the head
        assert top <= floor + LD._clear_height(_spec(name)) + 1e-6        # under the ceiling
        # on the room side of the wall, its front turned to the room
        across = "y" if side in ("N", "S") else "x"
        inward = 1.0 if side in ("S", "W") else -1.0
        assert (v[across] - o[across]) * inward > 0.15
        assert bool(v.get("rot_z")) == (side in ("S", "W"))
        assert v["collision"] == "none" and v["material"] == "velvet"


def test_no_other_building_is_draped():
    for name in ("deli_a01", "bank_branch_a01", "gs_empty_rowhome_a", "casino_a01"):
        path = os.path.join(HERE, "specs", name + ".json")
        if not os.path.isfile(path):
            continue
        assert LD.plan_den_drapes(_spec(name)) == [], name
        assert not [v for v in _spec(name).get("volumes") or []
                    if str(v.get("name", "")).startswith(LD.DRAPE_NAME)], name


def test_hanging_is_idempotent_and_declares_its_velvet_once():
    d = _spec("strip_club_a03")
    d["volumes"] = [v for v in d.get("volumes") or [] if not v["name"].startswith(LD.DRAPE_NAME)]
    d["materials"] = [m for m in d.get("materials") or [] if m.get("id") != "velvet"]
    assert LD.drape_den_windows(d) == 3
    assert LD.drape_den_windows(d) == 0
    assert [m["id"] for m in d["materials"]].count("velvet") == 1
    assert next(m for m in d["materials"] if m["id"] == "velvet")["acoustic"] == "Curtain"
    # a drape the rule no longer asks for goes
    d["volumes"].append(dict(d["volumes"][-1], name=LD.DRAPE_NAME + "_n9_1"))
    assert LD.drape_den_windows(d) == 1
    assert not [v for v in d["volumes"] if v["name"] == LD.DRAPE_NAME + "_n9_1"]


def test_furnish_never_sees_a_drape():
    """0.205.0's first suite run: a drape hangs from 1.3 to 1.7 m up, under the
    hung line, and was counted and cleared as a floor piece -- the clubs'
    rooms re-drew, and the library stopped being a fixed point of furnish
    (`test_back_bar`, `test_club_fixtures`, `test_wall_backing` hold that)."""
    for name in ("strip_club_a01", "strip_club_a03"):
        d = _spec(name)
        sh = LD._story_height(d)
        drapes = [v for v in d["volumes"] if v["name"].startswith(LD.DRAPE_NAME)]
        assert drapes
        for v in drapes:
            foot = v["z"] - v["size_z"] / 2.0
            floor = int(foot // sh) * sh
            assert foot - floor < LD._HUNG_MIN, (v["name"], foot - floor)   # under the hung line
            assert LD._is_drape(v) and LD._hung(v, floor), v["name"]        # and hung all the same
        bare = dict(d, volumes=[v for v in d["volumes"] if not LD._is_drape(v)])
        for room in d.get("rooms") or []:
            assert LD._room_volume_count(d, room) == LD._room_volume_count(bare, room), room["id"]


def test_a_drape_reaches_zoos_species_inside_its_genome():
    zoo = os.path.join(os.path.dirname(HERE), "zoo", "zoo_keeper", "genome", "species",
                       "window_drape.json")
    for name in ("strip_club_a01", "strip_club_a03"):
        for v in LD.plan_den_drapes(_spec(name)):
            assert prop_species.species_for_name(v["name"]) == "window_drape", v["name"]
            if not os.path.isfile(zoo):
                continue
            with open(zoo, encoding="utf-8") as fh:
                dims = json.load(fh)["dimensions"]
            (w, d, h), _rot = prop_species.long_axis_first((v["size_x"], v["size_y"], v["size_z"]))
            for k, val in (("width", w), ("depth", d), ("height", h)):
                assert dims[k]["min"] <= val <= dims[k]["max"], (v["name"], k, val)


def test_a_draped_window_lets_no_light_in_and_the_rest_keep_their_ids():
    win = {"wall": "ext_0_S", "kind": "window", "story": 0, "x": 2.0, "y": -12.0, "z": 2.5,
           "width": 1.2, "height": 1.4, "sill": 1.8}
    other = dict(win, x=8.0)
    drape = {"name": "window_drape_s0_1", "x": 2.0, "y": -11.74, "z": 2.475,
             "size_x": 1.5, "size_y": 0.16, "size_z": 1.55, "rot_z": 180.0}

    def windows(volumes):
        rep = {}
        got = lights.derive_light_anchors([], [win, other], 3.6, cap_thick=0.3, wall_thick=0.3,
                                          volumes=volumes, report=rep)
        return [a["id"] for a in got if a.get("type") == "window"], rep

    assert windows([])[0] == ["ext_0_S_window_1", "ext_0_S_window_2"]
    ids, rep = windows([drape])
    assert ids == ["ext_0_S_window_2"] and rep["draped_windows"] == 1
    assert LD.DRAPE_NAME == lights.DRAPE_NAME


def test_the_library_clubs_carry_their_drapes():
    assert migrate_den_drapes.main(["--check"]) == 0
    for name, n in (("strip_club_a01", 1), ("strip_club_a03", 3)):
        got = [v for v in _spec(name)["volumes"] if v["name"].startswith(LD.DRAPE_NAME)]
        assert got == LD.plan_den_drapes(_spec(name)) and len(got) == n


@pytest.mark.parametrize("name", ["strip_club_a01", "strip_club_a03"])
def test_the_built_clubs_draw_no_window_light(name):
    anchors = _built(name, "lights")["anchors"]
    assert not [a for a in anchors if a.get("type") == "window"], name
