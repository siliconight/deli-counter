"""Ceiling voids vs light rows -- a fixture must be mounted to SOMETHING.

A stairwell punched through a slab is a hole in the room below's ceiling.
The fluorescent row is laid across the whole room and never subtracted the
hole, so on `art_probe_001` seed 5017 one of twenty fixtures hung at
(-10.50, 6.50, 3.20), inside the `ceiling_manager_office` void spanning
x -13.0..-9.0, y 4.2..9.3 -- a light floating in a stairwell.

These tests are in their own file rather than appended to `test_lights.py`
so they can be read as one argument end to end.

Run:  python -m pytest test_lights_voids.py
"""
import lights


CAP = 0.3
SH = 3.5

# The room from the measured case: 24 m wide on story 0, row along x.
OFFICE = {"id": "manager_office", "story": 0, "bounds": [-15.0, 4.0, 0.0, 9.0],
          "center": [-7.5, 6.5, 0.0]}
# A room on the same storey with no hole in its ceiling.
LOBBY = {"id": "lobby", "story": 0, "bounds": [-15.0, -9.0, 15.0, 0.0],
         "center": [0.0, -4.5, 0.0]}
# The stairwell, as `derive_light_anchors` takes it: a world XY rect tagged
# with the storey whose CEILING it holes.
STAIRWELL = {"story": 0, "x0": -13.0, "y0": 4.2, "x1": -9.0, "y1": 9.3}


def _derive(rooms, voids):
    return lights.derive_light_anchors(rooms, [], SH, cap_thick=CAP,
                                       ceiling_voids=voids)


def _fluoro(anchors):
    return [a for a in anchors if a["type"] == "fluorescent"]


def _in(rect, pos):
    x0, y0, x1, y1 = rect
    return x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1


# --- the defect itself -------------------------------------------------

def test_without_the_void_a_fixture_lands_inside_the_hole():
    """The pre-fix behaviour, asserted so the fix has something to beat.

    If this ever stops holding, the row layout changed and the rest of this
    file is testing a case that no longer exists -- which is worth failing
    for, because a green suite over a vanished case is how a rule quietly
    stops being enforced."""
    a = _fluoro(_derive([OFFICE], None))
    assert len(a) == 1
    row = a[0]
    assert row["row"]["count"] > 1
    pts = _row_points(row)
    inside = [p for p in pts if _in((-13.0, 4.2, -9.0, 9.3), p)]
    assert inside, "expected the unsplit row to cross the stairwell"


def test_no_fixture_sits_over_a_ceiling_void():
    for row in _fluoro(_derive([OFFICE], [STAIRWELL])):
        for p in _row_points(row):
            assert not _in((-13.0, 4.2, -9.0, 9.3), p), \
                "fixture at %r is over the stairwell" % (p,)


# --- split, do not drop ------------------------------------------------

def test_the_row_splits_rather_than_disappearing():
    """A hole in the middle of a room must not go dark on BOTH sides of it.

    Dropping the row is the cheap fix and the wrong one: the part of the
    ceiling that still exists still needs a light."""
    a = _fluoro(_derive([OFFICE], [STAIRWELL]))
    assert len(a) == 2
    before, after = sorted(a, key=lambda x: x["pos"][0])
    assert before["pos"][0] < -13.0
    assert after["pos"][0] > -9.0
    assert before["row"]["count"] + after["row"]["count"] > 0


def test_total_fixture_count_only_loses_the_ones_over_the_hole():
    whole = _fluoro(_derive([OFFICE], None))[0]["row"]["count"]
    split = sum(a["row"]["count"] for a in _fluoro(_derive([OFFICE], [STAIRWELL])))
    assert 0 < split < whole


def test_a_room_swallowed_entirely_by_a_void_gets_no_fixture():
    """The one case where dropping IS right -- there is no ceiling left."""
    everything = {"story": 0, "x0": -100.0, "y0": -100.0,
                  "x1": 100.0, "y1": 100.0}
    assert _fluoro(_derive([OFFICE], [everything])) == []


# --- ids ---------------------------------------------------------------

def test_an_unsplit_room_keeps_its_original_anchor_id():
    """Ids are how authored overrides bind. Renaming every room's anchor the
    day voids were wired would have silently unbound every override in every
    spec -- splitting is the exception and only the exception renames."""
    a = _fluoro(_derive([OFFICE, LOBBY], [STAIRWELL]))
    ids = {x["id"] for x in a}
    assert "lobby_ceiling" in ids
    assert "manager_office_ceiling" not in ids
    assert {"manager_office_ceiling_0", "manager_office_ceiling_1"} <= ids


def test_a_void_on_another_storey_does_not_touch_this_one():
    """`slab_holes` is keyed by the slab it cuts; two flights of the same
    stair hole two different slabs at almost the same XY. Tagging by storey
    is what keeps the basement's hole out of the ground floor's row."""
    basement = dict(STAIRWELL, story=-1)
    a = _fluoro(_derive([OFFICE], [basement]))
    assert len(a) == 1
    assert a[0]["id"] == "manager_office_ceiling"


# --- authored overrides ------------------------------------------------

def test_authored_override_supersedes_the_split_runs():
    """An author placing `manager_office_ceiling` by hand gets ONE fixture,
    not their own plus the two derived halves."""
    m = lights.build_light_manifest(
        "b", [OFFICE], [], SH, cap_thick=CAP,
        ceiling_voids=[STAIRWELL],
        authored=[{"id": "manager_office_ceiling", "type": "fluorescent",
                   "pos": [-7.5, 6.5, 3.2], "rot_y": 0.0,
                   "row": {"count": 1, "spacing": 0.0}}])
    f = _fluoro(m["anchors"])
    assert [x["id"] for x in f] == ["manager_office_ceiling"]
    assert f[0]["source"] == "authored"


def test_an_override_does_not_eat_an_unrelated_anchor():
    """`_0` suffix stripping must not reach past its own base id, and must
    not touch anchors of another type or another source."""
    m = lights.build_light_manifest(
        "b", [OFFICE, LOBBY], [], SH, cap_thick=CAP,
        ceiling_voids=[STAIRWELL],
        authored=[{"id": "manager_office_ceiling", "type": "fluorescent",
                   "pos": [-7.5, 6.5, 3.2], "rot_y": 0.0}])
    ids = {a["id"] for a in m["anchors"]}
    assert "lobby_ceiling" in ids


# --- the storey shift, where it actually lives -------------------------

class _Hole(object):
    def __init__(self, story, x, y, sx, sy):
        self.story, self.x, self.y = story, x, y
        self.size_x, self.size_y = sx, sy


class _Spec(object):
    def __init__(self, holes):
        self.slab_holes = holes


def test_floors_tags_a_hole_with_the_storey_below_the_slab_it_cuts():
    """`slab_holes` is keyed by the slab; a slab's top face is the FLOOR of
    that storey, so the hole opens the CEILING of the one below. This is the
    off-by-one that would split rows around the wrong flight."""
    import floors
    v = floors.ceiling_voids(_Spec([_Hole(1, -11.0, 6.75, 4.0, 5.1)]))
    assert v == [{"story": 0, "x0": -13.0, "y0": 4.2,
                  "x1": -9.0, "y1": 9.3}]


def test_floors_agrees_with_the_rect_the_ceiling_skin_cuts():
    """Same hole through `room_voids` (skin, room-centred) and
    `ceiling_voids` (light, world) must land on the same rectangle -- the
    light must not split around a hole the skin did not cut."""
    import floors
    hole = _Hole(1, -11.0, 6.75, 4.0, 5.1)
    spec = _Spec([hole])
    cx, cy = -7.5, 6.5
    skin = floors.room_voids(spec, None, 1, cx, cy, 15.0, 10.0)
    light = floors.ceiling_voids(spec)
    assert len(skin) == 1 and len(light) == 1
    assert round(skin[0]["x0"] + cx, 4) == light[0]["x0"]
    assert round(skin[0]["y0"] + cy, 4) == light[0]["y0"]
    assert round(skin[0]["x1"] + cx, 4) == light[0]["x1"]
    assert round(skin[0]["y1"] + cy, 4) == light[0]["y1"]


def test_floors_dedupes_the_double_counted_hatch():
    """A spec-authored hatch is appended a second time by `_vertical_links`.
    The split does not care -- but the build line reports the count, and a
    number that is not the number of holes is a lie in the log."""
    import floors
    h = [_Hole(1, 0.0, 0.0, 2.0, 2.0), _Hole(1, 0.0, 0.0, 2.0, 2.0)]
    assert len(floors.ceiling_voids(_Spec(h))) == 1


def test_floors_returns_nothing_for_a_building_with_no_holes():
    import floors
    assert floors.ceiling_voids(_Spec([])) == []
    assert floors.ceiling_voids(_Spec(None)) == []


# --- helpers -----------------------------------------------------------

def _row_points(anchor):
    """Reconstruct the fixture positions a row anchor stands for. The
    manifest publishes a centre + count + spacing; the hole test is about
    the individual fixtures, so expand it the way Lux does."""
    n = int(anchor["row"]["count"])
    sp = float(anchor["row"]["spacing"])
    cx, cy = anchor["pos"][0], anchor["pos"][1]
    if n <= 1 or sp <= 0.0:
        return [(cx, cy)]
    dx, dy = (1.0, 0.0) if abs(anchor["rot_y"]) < 45.0 else (0.0, 1.0)
    start = -(n - 1) * 0.5 * sp
    return [(cx + (start + i * sp) * dx, cy + (start + i * sp) * dy)
            for i in range(n)]


if __name__ == "__main__":
    import sys
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok   %s" % name)
            except AssertionError as e:
                fails += 1
                print("FAIL %s: %s" % (name, e))
    sys.exit(1 if fails else 0)
