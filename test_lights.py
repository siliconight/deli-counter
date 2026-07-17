"""Tests for the light-anchor derivation (pure -- no Blender).

Run:  python -m pytest test_lights.py    (or: python test_lights.py)
"""
import lights


ROOMS = [
    # a wide room (x longer) on story 0
    {"id": "office", "story": 0, "bounds": [0, 0, 12, 4],
     "role": "backroom", "center": [6.0, 2.0, 0.0]},
    # a deep room (y longer) on story 1
    {"id": "hall", "story": 1, "bounds": [0, 0, 3, 20],
     "role": "corridor", "center": [1.5, 10.0, 3.5]},
]
OPENINGS = [
    {"kind": "window", "wall": "ext_0_S", "x": 6.0, "y": 0.0, "z": 1.85,
     "width": 1.4, "height": 1.2},
    {"kind": "door", "wall": "ext_0_N", "x": 6.0, "y": 4.0, "z": 1.0,
     "width": 1.1, "height": 2.2},   # not a window -> ignored
]


def test_one_fluorescent_per_room_on_the_ceiling():
    a = lights.derive_light_anchors(ROOMS, [], story_height=3.5)
    fluoro = [x for x in a if x["type"] == "fluorescent"]
    assert len(fluoro) == 2
    office = next(x for x in fluoro if x["room"] == "office")
    # ceiling = floor(0.0) + story_height(3.5) - gap(0.1)
    assert office["pos"][2] == 3.4
    assert office["reacts_to_alarm"] is True
    assert office["source"] == "derived"


def test_row_runs_along_the_longer_axis():
    a = lights.derive_light_anchors(ROOMS, [], story_height=3.5)
    office = next(x for x in a if x.get("room") == "office")  # x is longer
    hall = next(x for x in a if x.get("room") == "hall")      # y is longer
    assert office["rot_y"] == 0.0
    assert hall["rot_y"] == 90.0
    # a 12 m room gets several fixtures; a small room would get one
    assert office["row"]["count"] >= 2


def test_only_windows_become_area_lights_facing_inward():
    a = lights.derive_light_anchors([], OPENINGS, story_height=3.5)
    wins = [x for x in a if x["type"] == "window"]
    assert len(wins) == 1                      # the door is ignored
    w = wins[0]
    assert w["size"] == [1.4, 1.2]
    assert w["rot_y"] == 90.0                  # S wall -> faces inward (+Y)
    assert w["reacts_to_alarm"] is False


def test_authored_anchor_overrides_derived_by_id():
    authored = [{"id": "office_ceiling", "type": "fluorescent",
                 "pos": [6, 2, 3.0], "rot_y": 0, "room": "office",
                 "row": {"count": 1, "spacing": 0}, "reacts_to_alarm": True}]
    m = lights.build_light_manifest("bld", ROOMS, [], 3.5, authored=authored)
    office = [x for x in m["anchors"] if x["id"] == "office_ceiling"]
    assert len(office) == 1                     # replaced, not duplicated
    assert office[0]["source"] == "authored"
    assert office[0]["pos"] == [6, 2, 3.0]


def test_manifest_header():
    m = lights.build_light_manifest("gs_auto_shop", ROOMS, OPENINGS, 3.5,
                                    theme="delco")
    assert m["light_manifest_version"] == "1.1.0"
    assert m["building_id"] == "gs_auto_shop"
    assert m["rig_library"] == "lux"
    assert m["theme"] == "delco"


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"\n{len(fns)} passed")
    sys.exit(0)


# --- v1.1 facade lights (wall packs + storefront sign) ----------------------

FACADE_OPENINGS = [
    # storefront: two windows + the widest door on the same S wall
    {"kind": "window", "wall": "ext_0_S", "x": 3.0, "y": 0.0, "z": 1.85,
     "width": 1.4, "height": 1.2},
    {"kind": "window", "wall": "ext_0_S", "x": 9.0, "y": 0.0, "z": 1.85,
     "width": 1.4, "height": 1.2},
    {"kind": "door", "wall": "ext_0_S", "x": 6.0, "y": 0.0, "z": 1.25,
     "width": 1.2, "height": 2.2, "sill": 0.0},
    # a service door on the N wall and a rollup on the E wall
    {"kind": "door", "wall": "ext_0_N", "x": 6.0, "y": 12.0, "z": 1.25,
     "width": 1.1, "height": 2.2, "sill": 0.0},
    {"kind": "garage", "wall": "ext_1_E", "x": 12.0, "y": 6.0, "z": 1.65,
     "width": 4.0, "height": 3.0, "sill": 0.0},
    # an interior door: no facing suffix -> never gets facade hardware
    {"kind": "door", "wall": "int_office_hall", "x": 2.0, "y": 4.0, "z": 1.1,
     "width": 0.9, "height": 2.1, "sill": 0.0},
]


def test_wall_pack_over_every_exterior_door_but_the_sign_door():
    a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5)
    packs = [x for x in a if x["type"] == "wall_pack"]
    walls = sorted(p["wall"] for p in packs)
    # S door carries the sign; N door + E garage get packs; interior ignored
    assert walls == ["ext_0_N", "ext_1_E"]
    assert all(p["reacts_to_alarm"] is True for p in packs)


def test_wall_pack_sits_proud_above_the_door_head():
    a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5)
    n = next(x for x in a if x["type"] == "wall_pack"
             and x["wall"] == "ext_0_N")
    # door top = sill 0 + height 2.2; emitter 0.25 above it
    assert n["pos"][2] == 2.45
    # N wall: outward is +Y (inward 270 -> outward 90)
    assert n["rot_y"] == 90.0
    assert n["pos"][1] == 12.15          # y + 0.15 outward
    assert n["pos"][0] == 6.0


def test_storefront_sign_on_the_windowed_facade():
    a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5)
    signs = [x for x in a if x["type"] == "sign"]
    assert len(signs) == 1
    s = signs[0]
    assert s["wall"] == "ext_0_S"
    # S wall: outward is -Y (inward 90 -> outward 270); face 0.2 proud
    assert s["rot_y"] == 270.0
    assert s["pos"][1] == -0.2
    assert s["pos"][2] == 2.55           # door top + rise
    assert s["size"] == [2.0, 0.6]       # door 1.2 + pad 0.8
    assert s["reacts_to_alarm"] is True


def test_no_windows_means_no_derived_sign():
    ops = [o for o in FACADE_OPENINGS if o["kind"] != "window"]
    a = lights.derive_light_anchors([], ops, story_height=3.5)
    assert not [x for x in a if x["type"] == "sign"]
    # every exterior door gets a pack instead
    assert len([x for x in a if x["type"] == "wall_pack"]) == 3


def test_manifest_version_bumped_additively():
    m = lights.build_light_manifest("bld", ROOMS, FACADE_OPENINGS, 3.5)
    assert m["light_manifest_version"] == "1.1.0"
    types = {x["type"] for x in m["anchors"]}
    assert {"fluorescent", "window", "sign", "wall_pack"} <= types
