"""Ceiling rows step off partitions (lights.py, roadmap 143) -- pure, no bpy.

The shapes are cold run 9005's county hospital, where the walk found "light
inside the wall": a 40 x 15 lobby whose five-lamp row lands two lamps on the
ward partitions at x = +-8, and a roof room whose bulb row lies along the
y = 0 spine partition.
"""

import lights

SLAB = 0.3
WALL = 0.3

#: the hospital lobby: x longer, row along x at y = -7.5, count 5, spacing 8
LOBBY = {"id": "lobby", "story": 0, "bounds": [-20.0, -15.0, 20.0, 0.0],
         "role": "safe_room", "center": [0.0, -7.5, 0.0]}
#: the two ward partitions crossing it, as the spec authors them
WARD_WALLS = [
    {"story": 0, "axis": "Y", "pos": -8.0, "start": -15.0, "end": 15.0},
    {"story": 0, "axis": "Y", "pos": 8.0, "start": -15.0, "end": 15.0},
]
#: the roof: a room spanning the floor, a spine partition along its row
ROOF = {"id": "roof_helipad", "story": 2, "bounds": [-20.0, -15.0, 20.0, 15.0],
        "role": "objective_room", "objective": True, "center": [0.0, 0.0, 7.4]}
SPINE = [{"story": 2, "axis": "X", "pos": 0.0, "start": -20.0, "end": 20.0}]


def _lamps(anchors, room):
    """Every lamp point of a room's rows, expanded the way Zoo and Lux do."""
    pts = []
    for a in anchors:
        if a.get("room") != room:
            continue
        n, sp = a["row"]["count"], a["row"]["spacing"]
        dx, dy = (1.0, 0.0) if abs(a["rot_y"]) < 45.0 else (0.0, 1.0)
        start = -(n - 1) * 0.5 * sp
        pts += [(a["pos"][0] + (start + i * sp) * dx,
                 a["pos"][1] + (start + i * sp) * dy) for i in range(n)]
    return sorted(pts)


def test_the_clearance_is_derived_from_the_wall_and_the_troffer():
    # half the wall + half a 0.3 m troffer + the ceiling air gap
    assert lights.wall_clearance(0.3) == 0.4
    assert lights.wall_clearance(0.5) == 0.5


def test_partition_rects_are_the_wall_band_in_world_xy():
    r = lights.partition_rects(WARD_WALLS, 0.3)
    assert r[0] == {"story": 0, "x0": -8.15, "y0": -15.0, "x1": -7.85, "y1": 15.0}
    # the builder's trimmed pieces win over the authored span
    r = lights.partition_rects(SPINE, 0.3, pieces={0: [(-20.0, -3.0), (3.0, 20.0)]})
    assert [(w["x0"], w["x1"]) for w in r] == [(-20.0, -3.0), (3.0, 20.0)]
    assert r[0]["y0"] == -0.15 and r[0]["y1"] == 0.15


def test_without_partitions_the_row_lands_on_the_wall_as_before():
    """The measured defect, reproduced: lamps 2 and 4 at x = +-8.0."""
    a = lights.derive_light_anchors([LOBBY], [], 3.7, cap_thick=SLAB, wall_thick=WALL)
    assert [p[0] for p in _lamps(a, "lobby")] == [-16.0, -8.0, 0.0, 8.0, 16.0]


def test_a_lamp_on_a_crossing_partition_is_nudged_off_it():
    rep = {}
    a = lights.derive_light_anchors(
        [LOBBY], [], 3.7, cap_thick=SLAB, wall_thick=WALL,
        partitions=lights.partition_rects(WARD_WALLS, WALL), report=rep)
    xs = [p[0] for p in _lamps(a, "lobby")]
    # five lamps still; the two on the walls stand 0.4 m off the centreline
    assert len(xs) == 5
    assert -8.4 in xs or -7.6 in xs
    assert 8.4 in xs or 7.6 in xs
    for x in xs:
        assert abs(abs(x) - 8.0) >= 0.4 - 1e-9
    assert rep == {"rows_shifted": 0, "nudged": 2, "dropped": 0}
    # a nudged lamp is its own run, so the row is published as several anchors
    ids = sorted(x["id"] for x in a if x.get("room") == "lobby")
    assert ids == ["lobby_ceiling_%d" % i for i in range(5)]
    assert all(x["row"]["count"] == 1 for x in a if x.get("room") == "lobby")


def test_a_row_lying_along_a_partition_moves_to_the_larger_side():
    rep = {}
    a = lights.derive_light_anchors(
        [ROOF], [], 3.7, cap_thick=SLAB, wall_thick=WALL,
        partitions=lights.partition_rects(SPINE, WALL), report=rep)
    pts = _lamps(a, "roof_helipad")
    assert pts, "the roof row must not vanish"
    # equal halves: the positive side, at its centre
    assert all(y == 7.5 for _, y in pts)
    assert rep["rows_shifted"] == 1 and rep["dropped"] == 0
    # bulbs, not troffers, on the objective room -- unchanged by the shift
    assert all(x["type"] == "pendant" for x in a if x.get("room") == "roof_helipad")


def test_a_lamp_with_nowhere_to_go_is_dropped_and_counted():
    """A partition band wider than half a spacing: no landing inside the
    room, so the lamp goes rather than staying in the wall."""
    wide = [{"story": 0, "axis": "Y", "pos": 8.0, "start": -15.0, "end": 15.0}]
    rep = {}
    a = lights.derive_light_anchors(
        [LOBBY], [], 3.7, cap_thick=SLAB, wall_thick=8.0,   # a 8 m "wall"
        partitions=lights.partition_rects(wide, 8.0), report=rep)
    xs = [p[0] for p in _lamps(a, "lobby")]
    assert 8.0 not in xs and rep["dropped"] >= 1


def test_partitions_on_another_storey_do_not_touch_the_row():
    other = [{"story": 1, "axis": "Y", "pos": 8.0, "start": -15.0, "end": 15.0}]
    a = lights.derive_light_anchors(
        [LOBBY], [], 3.7, cap_thick=SLAB, wall_thick=WALL,
        partitions=lights.partition_rects(other, WALL))
    assert [p[0] for p in _lamps(a, "lobby")] == [-16.0, -8.0, 0.0, 8.0, 16.0]


def test_deterministic():
    kw = dict(cap_thick=SLAB, wall_thick=WALL,
              partitions=lights.partition_rects(WARD_WALLS + SPINE, WALL))
    assert (lights.derive_light_anchors([LOBBY, ROOF], [], 3.7, **kw)
            == lights.derive_light_anchors([LOBBY, ROOF], [], 3.7, **kw))
