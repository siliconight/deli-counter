"""A beer sign hung in the store's window (0.160.0).

The walker, 2026-09-29: "add the warm counter accent and the window sign
next". `migrate_window_sign` hangs one `window_sign` volume -- Zoo's
`neon_sign` in its `window` form (Zoo >= 1.27.0) -- inside every store's
storefront glass, beside the entrance, facing the street. Emissive only: no
light anchor derives from it.
"""
import copy
import json
import os

import lights
import migrate_window_sign as M
import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
STORES = ("cr_gas", "fuel_stop_heist", "gas_station", "gas_station_a01", "gas_station_a02",
          "gas_station_a03", "gas_street", "gs_corner_station", "stop_n_go")


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _sign(spec):
    (v,) = [v for v in spec["volumes"] if v["name"] == M.NAME]
    return v


def test_the_name_routes_to_the_neon_species():
    assert prop_species.species_for_name(M.NAME) == "neon_sign"
    # and it steals nothing: no existing volume name carries it
    for name in STORES:
        for v in _spec(name)["volumes"]:
            if v["name"] != M.NAME:
                assert M.NAME not in v["name"]


def test_every_store_hangs_one_and_the_migration_is_done():
    for name in STORES:
        spec = _spec(name)
        v = _sign(spec)
        assert v["form"] == "window" and v["collision"] == "none"
        assert 0 <= v["variant"] < M.NAMES
        assert M.migrate(copy.deepcopy(spec)) == (False, None), name


def test_it_hangs_inside_the_sales_floors_glass_beside_a_door_and_faces_out():
    for name in STORES:
        spec = _spec(name)
        bare = copy.deepcopy(spec)
        bare["volumes"] = [v for v in bare["volumes"] if v["name"] != M.NAME]
        want, why = M.plan(bare)
        assert why is None and want == _sign(spec), name
        v = want
        room = next(r for r in spec["rooms"] if r["id"] == M.ROOM)
        x0, y0, x1, y1 = room["bounds"]
        assert x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1, name
        # its top at the glass's head, where the chains hang
        top = min(M.GLASS_TOP, float(spec.get("story_height") or 3.6) - M.HEAD_MIN)
        assert abs(v["z"] + v["size_z"] / 2.0 - top) < 1e-6, name
        # long along its wall; the front faces out of the building
        wall = next(w for w in spec["ext_walls"] if w.get("material") == M.STOREFRONT
                    and int(w.get("story", 0) or 0) == 0
                    and abs(M._wall_geometry(spec, w["wall"])[1]
                            - (v["y"] if M._wall_geometry(spec, w["wall"])[0] == 0 else v["x"])) < 0.5)
        assert (v.get("rot_z", 0.0) == 180.0) == (wall["wall"] in ("N", "E")), name


def test_a_store_with_no_room_beside_its_door_is_refused_not_forced():
    spec = _spec("gas_station_a02")
    bare = copy.deepcopy(spec)
    bare["volumes"] = [v for v in bare["volumes"] if v["name"] != M.NAME]
    for w in bare["ext_walls"]:
        for o in w.get("openings") or []:
            o["width"] = 40.0          # a door wider than the building
    vol, why = M.plan(bare)
    assert vol is None and why


def test_no_light_derives_from_the_sign():
    sales = {"id": "sales_floor", "story": 0, "center": [-4.5, -5.0, 0.0],
             "bounds": [-16.0, -11.0, 7.0, 1.0], "role": "public_entry"}
    sign = _sign(_spec("gas_station_a02"))
    kw = dict(cap_thick=lambda s: 0.3, wall_thick=0.3)
    assert (lights.derive_light_anchors([sales], [], 4.2, volumes=[sign], **kw)
            == lights.derive_light_anchors([sales], [], 4.2, volumes=[], **kw))


def test_every_built_store_carries_it_as_a_window_neon_prop_slot():
    for name in STORES:
        slots = json.load(open(os.path.join(BUILD, name + ".slots.json"), encoding="utf-8"))["slots"]
        got = [s for s in slots if s.get("species") == "neon_sign" and s.get("form") == "window"]
        assert len(got) == 1, (name, len(got))


def test_a_hung_sign_is_not_furniture_in_the_rooms_count():
    """`furnish` tops a room up to a target less what is already there; a
    sign hung over a body's head takes no floor, so it must not count --
    it did, and a refurnish placed one piece fewer (gas_station_a02's
    `shelf_run_3`). The control: the same volume at a wall-fixture height
    (a dartboard's, 1.3 m) still counts."""
    import level_design
    spec = _spec("gas_station_a02")
    room = next(r for r in spec["rooms"] if r["id"] == M.ROOM)
    bare = copy.deepcopy(spec)
    bare["volumes"] = [v for v in bare["volumes"] if v["name"] != M.NAME]
    n = level_design._room_volume_count(bare, room)
    assert level_design._room_volume_count(spec, room) == n
    low = copy.deepcopy(bare)
    low["volumes"].append(dict(_sign(spec), z=1.3 + 0.3))
    assert level_design._room_volume_count(low, room) == n + 1


def test_the_sign_sits_before_the_pieces_furnish_wrote():
    import level_design
    import migrate_furnish_recipes
    for name in STORES:
        spec = _spec(name)
        tags = {level_design._room_tag(r) for r in spec["rooms"]}
        owned = [migrate_furnish_recipes.furnished_by_this_pass(v, tags) for v in spec["volumes"]]
        at = [i for i, v in enumerate(spec["volumes"]) if v["name"] == M.NAME][0]
        assert all(owned[at + 1:]), name


def test_every_store_defines_the_signs_material():
    """`validate` refuses a volume naming a material its spec does not
    define; none of the nine stores defined `metal_painted` until the
    migration added the library's own definition of it."""
    for name in STORES:
        spec = _spec(name)
        mats = {m["id"]: m for m in spec["materials"]}
        assert mats.get(_sign(spec)["material"]) == M.MATERIAL, name
