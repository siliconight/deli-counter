"""The 90s below-grade rule: basements and objective rooms get bare bulbs.

Roadmap 57's palette, first entry. A cellar or a count room with an office
fluorescent row reads like an office; the moody version is sparse warm
pendants -- one pool per ~25 m^2, hanging on a cord below the slab -- and
the anchor type `pendant` is what Lux keys the incandescent tuning on.
"""
import lights


def _cap(_story):
    return 0.3


def _room(**kw):
    d = {"id": "r", "story": 0, "center": [0.0, 0.0, 0.0],
         "bounds": [-5.0, -2.5, 5.0, 2.5], "objective": False}
    d.update(kw)
    return d


def test_a_basement_gets_bulbs_not_a_ceiling_row():
    rooms = [_room(id="cellar", story=-1, center=[0.0, 0.0, -3.7])]
    anchors = lights.derive_light_anchors(rooms, [], 3.7, cap_thick=_cap)
    assert {a["type"] for a in anchors} == {"pendant"}
    a = anchors[0]
    assert a["row"]["count"] == 2          # 10 x 5 = 50 m^2 -> two pools
    assert a["id"] == "cellar_bulbs"
    # the drop still reaches the CELLAR's own floor
    assert abs((a["pos"][2] - a["drop"]) - (-3.7)) < 1e-6


def test_an_objective_room_is_moody_at_any_storey():
    rooms = [_room(id="vault", objective=True)]
    anchors = lights.derive_light_anchors(rooms, [], 3.7, cap_thick=_cap)
    assert anchors and anchors[0]["type"] == "pendant"


def test_the_bulb_hangs_on_its_cord_below_the_row_mount():
    moody = lights.derive_light_anchors(
        [_room(id="a", objective=True)], [], 3.7, cap_thick=_cap)[0]
    office = lights.derive_light_anchors(
        [_room(id="b")], [], 3.7, cap_thick=_cap)[0]
    assert office["type"] == "fluorescent"
    assert abs((office["pos"][2] - moody["pos"][2]) - 0.6) < 1e-6


def test_a_small_room_gets_exactly_one_bulb():
    rooms = [_room(id="cell", story=-1, center=[0.0, 0.0, -3.7],
                   bounds=[-2.0, -2.0, 2.0, 2.0])]
    a = lights.derive_light_anchors(rooms, [], 3.7, cap_thick=_cap)[0]
    assert a["row"]["count"] == 1


def test_ordinary_rooms_keep_the_fluorescent_row():
    a = lights.derive_light_anchors([_room()], [], 3.7, cap_thick=_cap)[0]
    assert a["type"] == "fluorescent"
    assert a["id"] == "r_ceiling"


def test_a_stairwell_still_splits_the_bulb_line():
    rooms = [_room(id="cellar", story=-1, center=[0.0, 0.0, -3.7],
                   bounds=[-8.0, -2.0, 8.0, 2.0])]
    voids = [{"story": -1, "x0": -1.0, "y0": -1.0, "x1": 1.0, "y1": 1.0}]
    anchors = lights.derive_light_anchors(rooms, [], 3.7, cap_thick=_cap,
                                          ceiling_voids=voids)
    flu = [a for a in anchors if a["type"] == "pendant"]
    assert len(flu) >= 2                    # split into runs around the hole
    assert {a["drop"] for a in flu} == {flu[0]["drop"]}
