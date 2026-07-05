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
    assert m["light_manifest_version"] == "1.0.0"
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
