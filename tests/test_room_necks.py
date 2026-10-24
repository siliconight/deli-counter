"""A room's necks: the widest way between every two of its route endpoints (0.256.0, the factory's roadmap 284).

`room_necks` asks the factory's census of what furnishing costs a route (`docs/findings/furnish_route_cost/
route_cost.py` at the factory root) its own question of one room: the largest clearance c joining two endpoints, a
body passing where c reaches its radius, two abreast where 2c reaches `two_abreast_width()`. Furnish asks it of a host
the rescue moves (`_move`), which may take no width from a pair it leaves under two abreast (`_narrows`). Read against
the census before it shipped: 187 pairs in 64 rooms of twelve specs the change leaves alone, every neck the same to the
millimetre (the factory's patches/dc_desk_move/).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_contract  # noqa: E402
import level_design as L  # noqa: E402

CELL = float(agent_contract.contract()["nav_bake"]["cell_size_m"])


def _room(gap=None):
    """A 10 m square storey, one room, a door in the south wall and one in the north; with `gap`, a box across the
    room between them leaving `gap` metres to the east wall's inner face."""
    spec = {
        "name": "neck_probe", "seed": 7, "footprint_x": 10, "footprint_y": 10, "n_stories": 1, "story_height": 3.0,
        "wall_thick": 0.3, "floor_thick": 0.3, "default_material": "concrete",
        "materials": [{"id": "concrete", "acoustic": "Concrete"}],
        "rooms": [{"id": "hall", "story": 0, "bounds": [-5, -5, 5, 5], "role": "open_floor"}],
        "ext_walls": [{"story": 0, "wall": "S", "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]},
                      {"story": 0, "wall": "N", "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}],
        "volumes": [], "partitions": [], "stairs": [], "ladders": [], "markers": [],
    }
    if gap is not None:
        inner = 5 - 0.15
        x1 = inner - gap
        spec["volumes"].append({"name": "probe_box", "x": (-inner + x1) / 2.0, "y": 0.0, "z": 0.5,
                                "size_x": x1 + inner, "size_y": 1.0, "size_z": 1.0, "collision": "convex",
                                "material": "concrete"})
    return spec, spec["rooms"][0]


def test_a_rooms_neck_is_half_the_narrowest_gap_a_body_must_pass():
    """The open room: its two doors joined at the clearance just past a door's open approach disc -- the wall the door
    stands in, `_ROUTE_DOOR_IN` plus `_NECK_DOOR_ZONE` off it and a cell on (the first draft of this test asked for the
    cap, and read 1.598). A box across the room leaving 1.2 m at the east wall: half that, to a cell. The box to the
    wall: the doors parted, the pair absent."""
    spec, room = _room()
    assert [k for k, _l, _x, _y in L.room_route_endpoints(spec, room)] == ["door", "door"]
    necks = L.room_necks(spec, room)
    assert list(necks) == [(0, 1)]
    assert abs(necks[(0, 1)] - (L._ROUTE_DOOR_IN + L._NECK_DOOR_ZONE + CELL / 2.0)) <= CELL, necks
    spec, room = _room(gap=1.2)
    neck = L.room_necks(spec, room)[(0, 1)]
    assert abs(neck - 0.6) <= CELL, neck
    spec, room = _room(gap=0.0)
    assert L.room_necks(spec, room) == {}


def test_a_neck_narrowed_counts_only_under_two_abreast():
    """`_narrows`: a pair left two abreast (a 2.4 m gap, a 1.2 m neck) is not narrowed, however much it lost; one left
    single file (1.2 m) is; one parted is."""
    open_ = L.room_necks(*_room())
    assert not L._narrows(open_, L.room_necks(*_room(gap=2.4)))
    assert L._narrows(open_, L.room_necks(*_room(gap=1.2)))
    assert L._narrows(open_, L.room_necks(*_room(gap=0.0)))
    assert not L._narrows(open_, open_)
