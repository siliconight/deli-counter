"""A store tapes a pair of sale posters in its window (0.170.0).

The walker, 2026-09-29, choosing where posters go: "store windows and walls".
The walls were 0.163.0; this is the window, by the window sign's rule: inside
the sales floor's glass, beside an entrance, facing the street, clear of
every opening and of the sign, at the eye. And it costs the sales floor no
furniture: paper on a wall stands on no floor.
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent_contract  # noqa: E402
import level_design  # noqa: E402
import migrate_slush_machine  # noqa: E402
import migrate_window_poster as M  # noqa: E402
import migrate_window_sign as SIGN  # noqa: E402
import prop_species  # noqa: E402
import test_window_sign  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STORES = test_window_sign.STORES


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _poster(spec):
    (v,) = [v for v in spec["volumes"] if v["name"] == M.NAME]
    return v


def test_the_name_routes_to_the_poster_wall_on_paper():
    assert prop_species.species_for_name(M.NAME) == "poster_wall"
    assert level_design._prop_material({"materials": []}, M.NAME) == "paper"
    # and the runs on the walls still route as they did
    assert prop_species.species_for_name("poster_wall_store_r0123abcd_4") == "poster_wall"


def test_every_store_tapes_one_and_the_migration_is_done():
    for name in STORES:
        spec = _spec(name)
        v = _poster(spec)
        assert v["form"] == "store" and v["collision"] == "none" and v["material"] == "paper"
        assert 0 <= v["variant"] < M.VARIANTS
        assert any(m.get("id") == "paper" for m in spec["materials"]), name
        assert M.migrate(copy.deepcopy(spec)) == (False, None), name


def test_it_is_on_the_sales_floors_glass_at_the_eye_facing_out_clear_of_the_sign():
    for name in STORES:
        spec = _spec(name)
        v = _poster(spec)
        room = next(r for r in spec["rooms"] if r["id"] == SIGN.ROOM)
        x0, y0, x1, y1 = room["bounds"]
        assert x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1, name
        assert v["z"] == agent_contract.eye_height(), name
        wt = float(spec.get("wall_thick") or 0.3)
        hx, hy = spec["footprint_x"] / 2.0, spec["footprint_y"] / 2.0
        fx, fy = migrate_slush_machine._front(v)
        # its front points out through the wall it is taped inside, and that
        # wall is storefront glass
        if fx:
            wall = "E" if fx > 0 else "W"
            gap = hx - abs(v["x"])
        else:
            wall = "N" if fy > 0 else "S"
            gap = hy - abs(v["y"])
        assert (v["x"] * fx > 0) or (v["y"] * fy > 0), (name, v)
        assert abs(gap - (wt / 2.0 + M.INSET + M.SIZE[1] / 2.0)) < 1e-6, (name, gap)
        mats = {w["wall"]: w.get("material") for w in spec["ext_walls"] if not w.get("story")}
        assert mats[wall] == SIGN.STOREFRONT, (name, wall)
        # clear of the window sign along the wall
        sign = next(s for s in spec["volumes"] if s["name"] == SIGN.NAME)
        u, su = (v["x"], sign["x"]) if fy else (v["y"], sign["y"])
        assert abs(u - su) >= (M.SIZE[0] + SIGN.SIZE[0]) / 2.0 + M.GAP - 1e-6, (name, u, su)


def test_paper_on_a_wall_takes_no_share_of_the_rooms_furniture():
    spec = _spec("gas_station_a02")
    room = next(r for r in spec["rooms"] if r["id"] == SIGN.ROOM)
    with_it = level_design._room_volume_count(spec, room)
    bare = copy.deepcopy(spec)
    bare["volumes"] = [v for v in bare["volumes"] if v["name"] != M.NAME]
    assert level_design._room_volume_count(bare, room) == with_it
    # the control: a solid thing in the same place does count
    solid = copy.deepcopy(spec)
    _poster(solid).update(collision="convex", material="metal_painted")
    assert level_design._room_volume_count(solid, room) == with_it + 1
