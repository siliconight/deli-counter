"""Fluorescent anchors carry their DROP to the floor (roadmap 54, lux >= 0.19).

A flat light range was wrong at both ends: 8.0 claimed per-mesh budget slots
two rooms away through walls, 4.5 left the arena's ~5.7 m hall with a lit
ceiling over a pitch-black floor (attenuation reaches hard zero at the range,
so no energy lights a floor the range does not reach). Only this kit knows a
room's height; the anchor carries it so the rig never guesses.
"""
import lights


def _cap(_story):
    return 0.3


def test_the_drop_reaches_the_rooms_own_floor():
    rooms = [{"id": "hall", "story": 0, "center": [0.0, 0.0, 0.0],
              "bounds": [-10.0, -8.0, 10.0, 8.0]}]
    anchors = lights.derive_light_anchors(rooms, [], 6.0, cap_thick=_cap)
    flu = [a for a in anchors if a["type"] == "fluorescent"]
    assert flu, "a room must derive a ceiling row"
    for a in flu:
        # pos z is the lamp; pos z minus drop is the FLOOR of story 0.
        assert abs((a["pos"][2] - a["drop"]) - 0.0) < 1e-6
        # and the lamp hangs below the storey top by cap + gap, so the drop
        # is storey height minus that hardware allowance -- never the full 6.
        assert 5.0 < a["drop"] < 6.0


def test_an_upper_storey_drop_is_storey_local_not_building_global():
    """A storey-2 lamp is ~7.3 m above the GROUND; its drop must still be the
    ~3.3 m to its own floor, or every upstairs room gets a ground-floor
    range."""
    rooms = [{"id": "up", "story": 1, "center": [0.0, 0.0, 3.7],
              "bounds": [-4.0, -4.0, 4.0, 4.0]}]
    anchors = lights.derive_light_anchors(rooms, [], 3.7, cap_thick=_cap)
    a = [x for x in anchors if x["type"] == "fluorescent"][0]
    assert abs((a["pos"][2] - a["drop"]) - 3.7) < 1e-6
    assert a["drop"] < 3.7


def test_split_runs_share_one_drop():
    """A stairwell splits a row into runs; both runs hang from one ceiling."""
    rooms = [{"id": "cut", "story": 0, "center": [0.0, 0.0, 0.0],
              "bounds": [-8.0, -2.0, 8.0, 2.0]}]
    voids = [{"story": 0, "x0": -1.0, "y0": -1.0, "x1": 1.0, "y1": 1.0}]
    anchors = lights.derive_light_anchors(rooms, [], 3.7, cap_thick=_cap,
                                          ceiling_voids=voids)
    flu = [a for a in anchors if a["type"] == "fluorescent"]
    assert len({a["drop"] for a in flu}) == 1


def test_only_ceiling_lamps_carry_a_drop():
    """Windows (and any future wall hardware) meter their own mounting; a
    drop on them would be a guess wearing a number."""
    rooms = [{"id": "r", "story": 0, "center": [0.0, 0.0, 0.0],
              "bounds": [-4.0, -4.0, 4.0, 4.0]}]
    openings = [{"kind": "window", "wall": "ext_0_N", "x": 0.0, "y": 4.0,
                 "z": 1.5, "width": 1.2, "height": 1.4}]
    anchors = lights.derive_light_anchors(rooms, openings, 3.7,
                                          cap_thick=_cap)
    for a in anchors:
        if a["type"] != "fluorescent":
            assert "drop" not in a, a["type"]
