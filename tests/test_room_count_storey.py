"""A room counts only what stands on its own storey (0.246.0, the factory's roadmap 148).

`level_design._room_volume_count` is what a room already holds, so furnish tops an authored room up rather than
doubling it. It asked `abs(z - (floor + size_z / 2)) < sh` -- a foot anywhere between the storey below's floor and the
storey above's, both ends open -- and a piece standing on either of those floors is EXACTLY `sh` from this one, so
whether it counted was float rounding: at sh 3.3 a 1.45 m piece one storey down is 3.2999999999999994 off and counted,
a 1.40 m one is 3.3 and did not. Measured over the library before the change: 740 volumes in 195 rooms of 55 specs
inside that window, each a piece the room it was counted in then went without. The look review of 2026-10-19 found
the rooms "Too sparse"; this is one of the reasons, and the rows that roadmap item asked for next were the first new
height to fall into the window (their 1.45 m gondolas cost deli_a03's apartment nine of its twelve pieces).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level_design  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = 3.3
#: Every height from a kerb to a tall shelf, in 5 cm steps: the window is float noise, so the test sweeps for it
#: rather than naming the one height that found it.
HEIGHTS = [round(0.30 + 0.05 * k, 2) for k in range(43)]


def _spec(volumes):
    return {"name": "count_probe", "story_height": SH, "floor_thick": 0.3, "footprint_x": 20, "footprint_y": 20,
            "rooms": [{"id": "below", "story": 0, "bounds": [-10.0, -10.0, 10.0, 10.0]},
                      {"id": "above", "story": 1, "bounds": [-10.0, -10.0, 10.0, 10.0]}],
            "volumes": volumes}


def _standing(story, h, i=0):
    """A piece `h` tall standing on `story`'s floor, z rounded to the millimetre as `_make_volume` writes it."""
    return {"name": "crate_%d" % i, "x": round(0.4 * i - 8.0, 2), "y": 0.0, "z": round(story * SH + h / 2.0, 3),
            "size_x": 0.3, "size_y": 0.3, "size_z": h, "collision": "convex", "material": "wood"}


def test_the_window_is_real_at_this_storey_height():
    """The control, so the next two tests are known to be able to fail: at SH 3.3 the old spelling put a 1.45 m piece
    standing one storey down inside a room upstairs, and a 1.40 m one outside it."""
    for h, inside in ((1.45, True), (1.40, False)):
        z = round(h / 2.0, 3)
        assert (abs(z - (SH + h / 2.0)) < SH) is inside, h


def test_a_piece_on_the_floor_below_is_not_counted_upstairs():
    spec = _spec([_standing(0, h, i) for i, h in enumerate(HEIGHTS)])
    below, above = spec["rooms"]
    assert level_design._room_volume_count(spec, below) == len(HEIGHTS)
    assert level_design._room_volume_count(spec, above) == 0


def test_a_piece_on_the_floor_above_is_not_counted_downstairs():
    spec = _spec([_standing(1, h, i) for i, h in enumerate(HEIGHTS)])
    below, above = spec["rooms"]
    assert level_design._room_volume_count(spec, above) == len(HEIGHTS)
    assert level_design._room_volume_count(spec, below) == 0


def test_a_slab_sunk_under_the_floor_is_not_furniture():
    """gas_station_a02's sales floor holds the centre of a 46 x 46 m `forecourt_pad` whose top is the floor: under
    the old spelling it was one of the room's pieces."""
    pad = {"name": "forecourt_pad", "x": 0.0, "y": 0.0, "z": -0.2, "size_x": 46.0, "size_y": 46.0, "size_z": 0.4,
           "collision": "convex", "material": "concrete"}
    spec = _spec([pad, _standing(0, 1.0)])
    below, above = spec["rooms"]
    assert level_design._room_volume_count(spec, below) == 1
    assert level_design._room_volume_count(spec, above) == 0


def test_a_raised_piece_counts_on_its_own_storey_only():
    """A piece with collision whose foot is above the floor -- on a plinth, on a bracket -- is its own storey's, and
    only its own: the old spelling counted a foot 1.2 m up in the room over it too, 2.1 m off. What is hung over a
    body's head with no collision stays out, as it was."""
    v = _standing(0, 0.5)
    v["z"] = 1.45                       # its foot at 1.2 m
    spec = _spec([v])
    below, above = spec["rooms"]
    assert level_design._room_volume_count(spec, below) == 1
    assert level_design._room_volume_count(spec, above) == 0


def test_the_library_is_a_fixed_point_of_furnish():
    """Every library spec with rooms comes back byte for byte from stripping what furnish wrote and furnishing again:
    the refurnish shipped with this rule is the one the rule makes."""
    import migrate_furnish_recipes
    moved = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if not d.get("rooms"):
            continue
        before = json.dumps(d, sort_keys=True)
        migrate_furnish_recipes.migrate(d)
        if json.dumps(d, sort_keys=True) != before:
            moved.append(os.path.basename(p))
    assert not moved, moved
