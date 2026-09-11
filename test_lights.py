"""Tests for the light-anchor derivation (pure -- no Blender).

Run:  python -m pytest test_lights.py    (or: python test_lights.py)
"""
import lights


#: The slab capping a storey. The ceiling of a room is its UNDERSIDE, so a
#: fixture hangs at floor + story_height - SLAB - gap. Chosen to match the
#: shipped buildings measured on 2026-08-02, where the slab is 0.30 m.
SLAB = 0.3

#: The exterior wall. An opening's (x, y) is this wall's CENTRELINE, so a
#: facade emitter placed "proud of the wall" has to clear half of this first.
#: 0.30 is the thickness 18,469 of the shipped wall slots carry (2026-09-11);
#: 0.35 and 0.25 exist too, which is why it is a parameter and not a constant.
WALL = 0.3

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
    a = lights.derive_light_anchors(ROOMS, [], story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    fluoro = [x for x in a if x["type"] == "fluorescent"]
    assert len(fluoro) == 2
    office = next(x for x in fluoro if x["room"] == "office")
    # ceiling PLANE = floor(0.0) + story_height(3.5) - slab(0.3) = 3.2,
    # and the fixture hangs gap(0.1) below it.
    assert office["pos"][2] == 3.1
    assert office["reacts_to_alarm"] is True
    assert office["source"] == "derived"


def test_row_runs_along_the_longer_axis():
    a = lights.derive_light_anchors(ROOMS, [], story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    office = next(x for x in a if x.get("room") == "office")  # x is longer
    hall = next(x for x in a if x.get("room") == "hall")      # y is longer
    assert office["rot_y"] == 0.0
    assert hall["rot_y"] == 90.0
    # a 12 m room gets several fixtures; a small room would get one
    assert office["row"]["count"] >= 2


def test_only_windows_become_area_lights_facing_inward():
    a = lights.derive_light_anchors([], OPENINGS, story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
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
    m = lights.build_light_manifest("bld", ROOMS, [], 3.5, cap_thick=SLAB, wall_thick=WALL,
                                    authored=authored)
    office = [x for x in m["anchors"] if x["id"] == "office_ceiling"]
    assert len(office) == 1                     # replaced, not duplicated
    assert office[0]["source"] == "authored"
    assert office[0]["pos"] == [6, 2, 3.0]


def test_manifest_header():
    m = lights.build_light_manifest("gs_auto_shop", ROOMS, OPENINGS, 3.5, cap_thick=SLAB, wall_thick=WALL,
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
    a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    packs = [x for x in a if x["type"] == "wall_pack"]
    walls = sorted(p["wall"] for p in packs)
    # S door carries the sign; N door + E garage get packs; interior ignored
    assert walls == ["ext_0_N", "ext_1_E"]
    assert all(p["reacts_to_alarm"] is True for p in packs)


def test_wall_pack_sits_proud_above_the_door_head():
    a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    n = next(x for x in a if x["type"] == "wall_pack"
             and x["wall"] == "ext_0_N")
    # door top = sill 0 + height 2.2; emitter 0.25 above it
    assert n["pos"][2] == 2.45
    # N wall: outward is +Y (inward 270 -> outward 90)
    assert n["rot_y"] == 90.0
    # y is the wall's centreline; the face is half a wall out, and the
    # emitter 0.15 beyond THAT. 12.15 -- the value this test pinned until
    # 2026-09-11 -- is the face itself, with half the pack inside the wall.
    assert n["pos"][1] == 12.3           # y + 0.15 (half wall) + 0.15 (proud)
    assert n["pos"][0] == 6.0


def test_storefront_sign_on_the_windowed_facade():
    a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    signs = [x for x in a if x["type"] == "sign"]
    assert len(signs) == 1
    s = signs[0]
    assert s["wall"] == "ext_0_S"
    # S wall: outward is -Y (inward 90 -> outward 270); face plane 0.2 proud
    # of the wall FACE, which is itself half a wall out from y.
    assert s["rot_y"] == 270.0
    assert s["pos"][1] == -0.35
    assert s["pos"][2] == 2.55           # door top + rise
    assert s["size"] == [2.0, 0.6]       # door 1.2 + pad 0.8
    assert s["reacts_to_alarm"] is True


def test_no_windows_means_no_derived_sign():
    ops = [o for o in FACADE_OPENINGS if o["kind"] != "window"]
    a = lights.derive_light_anchors([], ops, story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    assert not [x for x in a if x["type"] == "sign"]
    # every exterior door gets a pack instead
    assert len([x for x in a if x["type"] == "wall_pack"]) == 3


def test_manifest_version_bumped_additively():
    m = lights.build_light_manifest("bld", ROOMS, FACADE_OPENINGS, 3.5, cap_thick=SLAB, wall_thick=WALL)
    assert m["light_manifest_version"] == "1.1.0"
    types = {x["type"] for x in m["anchors"]}
    assert {"fluorescent", "window", "sign", "wall_pack"} <= types


def test_a_ceiling_fixture_hangs_below_the_slab_it_is_under():
    """The regression this parameter exists for.

    Measured 2026-08-02: every fluorescent anchor in a shipped building sat
    0.10 m below the floor ABOVE it, which is 0.20 m INSIDE a 0.30 m slab --
    invisible from either room and lighting a void. 28 of 28. The fixture must
    end up under the slab's underside, not under the next storey's floor.
    """
    a = lights.derive_light_anchors(ROOMS, [], story_height=3.5, cap_thick=SLAB, wall_thick=WALL)
    for f in [x for x in a if x["type"] == "fluorescent"]:
        room = next(r for r in ROOMS if r["id"] == f["room"])
        storey_top = room["center"][2] + 3.5
        ceiling = storey_top - SLAB
        assert f["pos"][2] < ceiling, (
            f'{f["id"]} at {f["pos"][2]} is not below the ceiling {ceiling}')
        assert f["pos"][2] < storey_top - SLAB, "inside the slab"


def test_cap_thick_may_vary_by_storey():
    """A top storey is capped by a roof, which need not match a floor.

    `Building._cap_thick` returns roof_thick for the top storey and floor_thick
    below it, so this takes a callable and uses the storey each room declares.
    """
    def cap(story):
        return 0.5 if story == 1 else 0.3
    a = lights.derive_light_anchors(ROOMS, [], story_height=3.5, cap_thick=cap,
                                    wall_thick=WALL)
    office = next(x for x in a if x.get("room") == "office")   # story 0
    hall = next(x for x in a if x.get("room") == "hall")       # story 1
    assert office["pos"][2] == 3.1          # 0.0 + 3.5 - 0.3 - 0.1
    assert hall["pos"][2] == 6.4            # 3.5 + 3.5 - 0.5 - 0.1


def test_cap_thick_is_required():
    """No default, because a default of zero reproduces the defect silently."""
    try:
        lights.derive_light_anchors(ROOMS, [], story_height=3.5, wall_thick=WALL)
    except TypeError:
        return
    raise AssertionError("cap_thick must be required")


# --- roadmap 85: the facade hardware is outside the wall it hangs on --------

def _facade_clearance(anchor, wall_thick):
    """How far an anchor sits beyond its wall's FACE, along the outward
    normal. The opening is on the centreline (measured: 425 of 425 exterior
    doors in the shipped library), so the face is half a wall out from it."""
    door = next(o for o in FACADE_OPENINGS if o["wall"] == anchor["wall"]
                and o["kind"] in ("door", "garage"))
    dx = anchor["pos"][0] - door["x"]
    dy = anchor["pos"][1] - door["y"]
    return round(abs(dx) + abs(dy) - wall_thick * 0.5, 3)


def test_wall_pack_clears_the_face_by_the_constant_whatever_the_wall():
    """The regression this parameter exists for.

    Measured 2026-09-11 over the shipped library with
    `tools/anchor_wall_probe.py`: 334 wall packs at a median clearance of
    0.000 to the nearest wall (min -0.025 in a 0.35 m wall), 91 signs at
    0.050. The offsets were applied to the centreline coordinate, so the
    emitter sat on the face and Zoo's 0.22 m pack body -- centred on it --
    was half inside the wall. That is the half-buried light roadmap 85 was
    raised on.
    """
    for wall in (0.25, 0.3, 0.35):
        a = lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5,
                                        cap_thick=SLAB, wall_thick=wall)
        for p in [x for x in a if x["type"] == "wall_pack"]:
            assert _facade_clearance(p, wall) == lights._WALL_PACK_OUT, (p, wall)
            # Zoo's wall_pack body is up to 0.30 m deep and centred on the
            # anchor; the arm reaches _WALL_PACK_OUT back to the wall plane.
            assert lights._WALL_PACK_OUT >= 0.30 * 0.5, "body inside the wall"
        for s in [x for x in a if x["type"] == "sign"]:
            assert _facade_clearance(s, wall) == lights._SIGN_OUT, (s, wall)
            # Zoo's sign cabinet (<= 0.30 m) hangs entirely behind the face.
            assert lights._SIGN_OUT >= 0.30 * 0.5 + 0.02, "cabinet inside the wall"


def test_wall_thick_is_required():
    """Same rule as cap_thick: a default reproduces the defect silently."""
    try:
        lights.derive_light_anchors([], FACADE_OPENINGS, story_height=3.5,
                                    cap_thick=SLAB)
    except TypeError:
        return
    raise AssertionError("wall_thick must be required")
