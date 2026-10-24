"""The arrangement census reads a room the way a player does (0.264.0).

`arrangement.py` gives every standing piece the first visible reason it has to stand where it stands -- wall, seat,
aligned, centred, grouped -- or calls it loose. These are its controls: rooms built so the right answer is known, so
an instrument that cannot tell a row from a scatter fails here rather than reporting a number nobody can trust.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import arrangement  # noqa: E402


def _room(**kw):
    s = {"name": "t", "story_height": 3.0, "rooms": [{"id": "office", "story": 0, "bounds": [0.0, 0.0, 12.0, 8.0]}],
         "volumes": []}
    s.update(kw)
    return s


def _v(name, x, y, sx=1.0, sy=0.6, h=0.75):
    return {"name": name, "x": x, "y": y, "z": h / 2.0, "size_x": sx, "size_y": sy, "size_z": h,
            "collision": "convex"}


def _why(spec):
    room = spec["rooms"][0]
    return {v["name"]: why for v, why in arrangement.reasons(room, arrangement.standing(spec)["office"])}


def test_each_reason_is_read_as_built():
    s = _room(volumes=[
        _v("shelf_run_r00000001_1", 6.0, 0.4, 2.6, 0.6, 1.7),                 # against the south wall
        _v("desk_r00000001_2", 3.0, 3.0), _v("desk_r00000001_3", 6.0, 3.0), _v("desk_r00000001_4", 9.0, 3.0),
        _v("chair_set_r00000001_2_1", 3.0, 2.2, 0.5, 0.5, 0.9),                # at its desk
        _v("crate_stack_office_0", 6.0, 4.0, 1.1, 1.1, 0.95),                  # on the room's centre line x = 6
        _v("cartons_r00000001_5", 2.0, 6.0, 0.6, 0.6, 0.5), _v("cartons_r00000001_6", 2.9, 6.25, 0.5, 0.5, 0.4),
        _v("planter_box_office_1", 8.7, 5.9, 1.4, 0.7, 0.9),                   # nothing
    ])
    got = _why(s)
    assert got["shelf_run_r00000001_1"] == "wall"
    assert {got["desk_r00000001_%d" % k] for k in (2, 3, 4)} == {"aligned"}
    assert got["chair_set_r00000001_2_1"] == "seat"
    assert got["crate_stack_office_0"] == "centred"
    assert got["cartons_r00000001_5"] == got["cartons_r00000001_6"] == "grouped"
    assert got["planter_box_office_1"] == "loose"


def test_a_scatter_reads_loose_and_its_row_does_not():
    """The same three desks, scattered and turned, then in a row: the census tells them apart."""
    scatter = _room(volumes=[_v("desk_r00000001_1", 3.0, 3.1), _v("desk_r00000001_2", 6.4, 5.2, 0.6, 1.0),
                             _v("desk_r00000001_3", 9.2, 3.7)])
    row = _room(volumes=[_v("desk_r00000001_1", 3.0, 3.1), _v("desk_r00000001_2", 6.4, 3.1),
                         _v("desk_r00000001_3", 9.2, 3.1)])
    assert set(_why(scatter).values()) == {"loose"}
    assert set(_why(row).values()) == {"aligned"}


def test_two_aligned_pieces_turned_differently_are_not_a_row():
    s = _room(volumes=[_v("table_work_r00000001_1", 3.0, 3.1, 1.2, 0.7), _v("table_work_r00000001_2", 3.0, 5.4, 0.7,
                                                                              1.2)])
    assert set(_why(s).values()) == {"loose"}


def test_hung_and_tiny_pieces_are_not_furniture():
    sign = dict(_v("sign_r00000001_1", 4.0, 4.0, 1.0, 0.1, 0.5), collision="none", z=2.5)
    s = _room(volumes=[sign, _v("bottle_r00000001_2", 4.0, 4.0, 0.1, 0.1, 0.2)])
    assert arrangement.standing(s) == {}


def test_the_producers_are_told_apart():
    room = {"id": "office", "bounds": [0, 0, 12, 8]}
    assert arrangement.producer({"name": "desk_r0badf00d_3"}, room) == "furnish"
    assert arrangement.producer({"name": "crate_stack_office_2"}, room) == "seed"
    assert arrangement.producer({"name": "kitchen_prep_table"}, room) == "authored"
