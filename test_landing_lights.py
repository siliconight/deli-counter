"""Every opening's landing is lit to read from above, even in a moody room (0.261.0).

The walker, walking cold run 9383, of a stair opening onto deli_a03's basement: "this shouldn't look pitch black", and
the rule: "you should be able to see into holes to know you can go forward into them". A room below grade keeps its
bare bulbs and its dark corners; the place an opening comes down into it -- a stair's foot, the floor under a hole, a
ladder's base -- gets a fluorescent over it (the factory's `docs/findings/walk_2026-10-23_deli/`).

THE TEST THAT MATTERS IS `test_the_basement_stairs_foot_is_lit_and_nothing_else_moves`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lights  # noqa: E402
import spec_loader  # noqa: E402


def _deli():
    return spec_loader.load_spec(os.path.join(HERE, "specs", "deli_a03.json"))


def _room(rid, story, bounds, objective=False, role="connector"):
    x0, y0, x1, y1 = bounds
    return {"id": rid, "story": story, "bounds": list(bounds), "objective": objective, "role": role,
            "center": [(x0 + x1) / 2.0, (y0 + y1) / 2.0, story * 3.3]}


def test_every_opening_lands_somewhere_once():
    """deli_a03: both stairs' feet, the floor under its broken-floor hole, both ladders' bases -- the hole named
    twice in its spec (authored and as its link) one landing, and its hatch, which stands inside the up-stair's own
    footprint, that stair's opening and not a second one."""
    got = [(g["story"], g["kind"]) for g in lights.opening_landings(_deli())]
    assert sorted(got) == sorted([(-1, "stair"), (0, "stair"), (0, "hole"), (0, "ladder"), (-1, "ladder")]), got


def test_a_built_spec_counts_no_opening_twice():
    """The build cuts every ladder's through-hole and every stair's run into the slabs (`Builder`), and the lights
    are derived from that built spec: read off it, deli_a03's basement corridor took two lamps at one point, one for
    its ladder and one for the ladder's own hole, and cold storage one for its stair and one for the stair's cut.
    A spec cut the way the builder cuts it lands exactly as the library spec does."""
    import copy
    import ladder_geom
    import stairwell
    from spec_types import SlabHole
    spec = _deli()
    built = copy.deepcopy(spec)
    for ld in built.ladders:
        lo, hi = sorted((ld.from_story, ld.to_story))
        for s in range(lo, hi):
            hx, hy, sx, sy = ladder_geom.through_hole(ld.x, ld.y, ld.width, ld.facing)
            built.slab_holes.append(SlabHole(story=s + 1, x=hx, y=hy, size_x=sx, size_y=sy))
    for st in built.stairs:
        f = stairwell.footprint_rect(st)
        built.slab_holes.append(SlabHole(story=max(st.from_story, st.to_story), x=(f[0] + f[2]) / 2,
                                         y=(f[1] + f[3]) / 2, size_x=f[2] - f[0], size_y=f[3] - f[1]))
    assert lights.opening_landings(built) == lights.opening_landings(spec)


def test_the_basement_stairs_foot_is_lit_and_nothing_else_moves():
    """deli_a03's basement is moody by rule. With its landings, cold storage gets a fluorescent at the stair's foot
    and the corridor one at the ladder's base; the rooms above, lit by rows, get none; and every anchor the
    derivation made before is the same, in the same order, the landings after them."""
    spec = _deli()
    g = json.load(open(os.path.join(HERE, "build", "deli_a03.gameplay.json"), encoding="utf-8")) \
        if os.path.isfile(os.path.join(HERE, "build", "deli_a03.gameplay.json")) else None
    rooms = g["rooms"] if g else [
        _room("cold_storage", -1, (-19.0, 1.0, 1.0, 14.0)), _room("basement_corridor", -1, (-19.0, -14.0, 1.0, 1.0)),
        _room("stairwell", 0, (-19.0, 6.0, -8.0, 14.0)), _room("kitchen", 0, (7.0, -14.0, 19.0, 6.0))]
    kw = dict(cap_thick=0.3, wall_thick=spec.wall_thick)
    before = lights.derive_light_anchors(rooms, [], spec.story_height, **kw)
    rep = {}
    after = lights.derive_light_anchors(rooms, [], spec.story_height, report=rep,
                                        landings=lights.opening_landings(spec), **kw)
    landing = [a for a in after if a.get("landing")]
    assert [a for a in after if not a.get("landing")] == before
    by_room = {a["room"]: a for a in landing}
    assert set(by_room) == {"cold_storage", "basement_corridor"}, sorted(by_room)
    assert by_room["cold_storage"]["landing"] == "stair" and by_room["basement_corridor"]["landing"] == "ladder"
    assert all(a["type"] == "fluorescent" for a in landing)
    assert by_room["cold_storage"]["pos"][:2] == [-15.8, 11.6]
    assert rep["landing_lights"] == 2


def test_a_landing_under_a_hole_hangs_its_lamp_beside_the_hole():
    """A hole's landing is under the hole: a lamp there would hang in air. It hangs past the hole's edge, on the
    side nearest the room's middle, inside the room."""
    room = _room("cellar", -1, (0.0, 0.0, 10.0, 10.0))
    hole = {"story": -1, "x0": 1.0, "y0": 4.0, "x1": 3.0, "y1": 6.0}
    got = lights.derive_light_anchors([room], [], 3.3, cap_thick=0.3, wall_thick=0.3, ceiling_voids=[hole],
                                      landings=[{"story": -1, "x": 2.0, "y": 5.0, "kind": "hole"}])
    (lamp,) = [a for a in got if a.get("landing")]
    x, y = lamp["pos"][:2]
    assert not (1.0 <= x <= 3.0 and 4.0 <= y <= 6.0), lamp["pos"]
    assert abs(x - (3.0 + lights._LANDING_OFF_HOLE)) < 1e-6 and abs(y - 5.0) < 1e-6, lamp["pos"]
