"""Pure tests for the floorplan stair overlay (no bpy).
Run: python3 test_floorplan_stairs.py"""
import floorplan as F
import stairwell as S
from spec_types import LevelSpec, Stairwell, Room


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _spec():
    return LevelSpec(name="s", n_stories=2, footprint_x=24, footprint_y=18,
                     stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                       width=1.2, run=4.0, style="straight",
                                       facing="E", id="core",
                                       role="primary_egress")],
                     rooms=[Room(id="g", story=0, bounds=[-12, -9, 12, 9],
                                 role="connector"),
                            Room(id="u", story=1, bounds=[-12, -9, 12, 9],
                                 role="connector")])


def test_footprint_facing_label_and_arrow():
    svg = F.render_story(_spec(), 0)
    assert "core ↑E" in svg                      # id + facing label
    assert "[primary_egress]" in svg             # role label
    assert svg.count(F.STAIR_COLOR) >= 4         # rect + label + arrow lines


def test_landings_render_on_their_stories():
    sp = _spec()
    g0, g1 = F.render_story(sp, 0), F.render_story(sp, 1)
    assert F.LAND_LOWER_COLOR in g0 and F.LAND_UPPER_COLOR not in g0
    assert F.LAND_UPPER_COLOR in g1 and F.LAND_LOWER_COLOR not in g1


def test_arrow_points_along_facing():
    """Facing E: the exit point is east of the entry point, so the arrow's
    x2 must be greater than x1 (screen x grows east)."""
    sp = _spec()
    st = sp.stairs[0]
    eps = S.stair_endpoints(st)
    lo = [e for e in eps if e["end"] == "lower"][0]["point"]
    up = [e for e in eps if e["end"] == "upper"][0]["point"]
    assert up[0] > lo[0]
    svg = F.render_story(sp, 0)
    assert 'stroke="#7b1fa2" stroke-width="2"' in svg


def test_stair_only_story_still_gets_a_plan():
    sp = _spec()
    sp.rooms = []                                 # no rooms anywhere
    assert F.stories_in(sp) == [0, 1]             # stairs alone force plans


def test_spiral_draws_disc_not_arrow():
    sp = _spec()
    sp.stairs = [Stairwell(x=0, y=0, from_story=0, to_story=1,
                           width=1.5, style="spiral", id="twist")]
    svg = F.render_story(sp, 0)
    assert "<circle" in svg


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all floorplan stair tests passed")
