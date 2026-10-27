"""A selling room keeps a shop's lamp density however big it is (0.274.0) -- pure, no bpy.

The walker, 2026-10-26, in seed 9205's supermarket: "far too dark in teh super market", and the comps after it --
"shiny floor, bright lights, isles, glowing freezer section" (the factory's docs/reference/GROCERY_STORE_COMPS.md).
Every room was held to twelve lamps whatever its size, so the supermarkets' sales floors were lit at 88 to 92 m2 a
lamp against the delis' 25 (the factory's docs/findings/selling_hall_lights/census.py). A room whose id sells takes its
cap from its area, one lamp a `lights._SELLING_M2_PER_LAMP`; every other room keeps the library's caps.

FAILS ON 0.273.0: `room_caps` does not exist, and supermarket_a01's sales floor lays 12 lamps.

Run:  python -m pytest tests/test_selling_room_lamps.py
"""
import os

import lights
import spec_loader

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP, SH, WALL = 0.3, 4.5, 0.3


def _lamps(room):
    anchors = lights.derive_light_anchors([room], [], SH, cap_thick=CAP, wall_thick=WALL)
    return sum(a["row"]["count"] for a in anchors if a["type"] == "fluorescent" and a["room"] == room["id"])


def _room(rid, w, d, role="public_entry"):
    return {"id": rid, "story": 0, "bounds": [0.0, 0.0, w, d], "role": role, "center": [w / 2, d / 2, 0.0]}


def test_a_selling_rooms_cap_is_its_area_at_a_shops_density():
    assert lights.room_caps(_room("sales_floor", 44.0, 24.0), [0.0, 0.0, 44.0, 24.0]) == (42, 42, 42)
    # never fewer than the library's twelve
    assert lights.room_caps(_room("sales_floor", 10.0, 10.0), [0.0, 0.0, 10.0, 10.0]) == (12, 12, 12)
    # a room that does not sell keeps the library's caps, however big
    caps = (lights._MAX_ROWS, lights._MAX_FIXTURES, lights._MAX_LAMPS_ROOM)
    assert lights.room_caps(_room("concourse", 44.0, 24.0), [0.0, 0.0, 44.0, 24.0]) == caps
    assert lights.room_caps(_room("stockroom", 44.0, 24.0), [0.0, 0.0, 44.0, 24.0]) == caps


def test_a_supermarkets_sales_floor_is_lit_like_a_shop():
    """WOOD's rule decides how many it asks for; the cap only bounds it. supermarket_a01's 44 x 24 m floor under a
    4.1 m ceiling asks five rows of nine at 4.65 m and gets five of eight -- 40 lamps, 26.4 m2 a lamp."""
    spec = spec_loader.load_spec(os.path.join(HERE, "specs", "supermarket_a01.json"))
    room = next(r for r in spec.rooms if r.id == "sales_floor")
    b = list(room.bounds)
    n = _lamps(_room("sales_floor", b[2] - b[0], b[3] - b[1]))
    area = (b[2] - b[0]) * (b[3] - b[1])
    assert n == 40, n
    assert area / n <= lights._SELLING_M2_PER_LAMP * 1.1, area / n


def test_a_hall_that_does_not_sell_keeps_twelve():
    assert _lamps(_room("concourse", 44.0, 24.0)) == lights._MAX_LAMPS_ROOM
