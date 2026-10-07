"""A wall piece needs a wall behind it (0.202.0).

`_wall_slots` offered a wall piece every edge of its room. It checked an
exterior edge's openings and glazing; an interior edge it assumed was a wall,
and never asked whether a partition stood on it. Where two rooms meet across
open floor, a shelf, a cabinet, an ATM or a paper poster was stood with its
back against nothing: 155 of the library's 4,086 furnished wall pieces, in 18
shells (the factory's docs/findings/wall_pieces_without_walls/), deli_a01's
ATM and two lottery boards in front of its deli case among them.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402
import level_design as L             # noqa: E402
import migrate_furnish_recipes as MF  # noqa: E402
import presets                       # noqa: E402

#: As the finding's census asks it: a wall on the piece's storey within this
#: of the edge it was slotted against, holding half its run
TOL, COVER = 0.10, 0.5


def _spec(partitions=()):
    """A 20 x 14 m one-storey building, two rooms meeting at x = 0."""
    return {"name": "t", "footprint_x": 20.0, "footprint_y": 14.0, "story_height": 3.0,
            "n_stories": 1, "has_basement": False, "wall_thick": 0.3, "grid": 0.5,
            "auto_exterior": True, "ext_walls": [], "stairs": [], "slab_holes": [],
            "partitions": list(partitions),
            "rooms": [{"id": "west", "story": 0, "bounds": [-10.0, -7.0, 0.0, 7.0],
                       "role": "connector"},
                      {"id": "east", "story": 0, "bounds": [0.0, -7.0, 10.0, 7.0],
                       "role": "connector"}],
            "volumes": [], "markers": []}


def _on_edge(slots, x_edge, long_side, short_side, back):
    """The slots whose back stands against the edge at x = ``x_edge``."""
    cx = x_edge - (short_side / 2.0 + back)
    return [s for s in slots if abs(s[0] - cx) < 1e-6]


def _back(spec):
    return float(spec["wall_thick"]) / 2.0 + L._WALL_PIECE_AIR


def _slots(spec, room_id, w=1.2, d=0.5, seed=1):
    room = next(r for r in spec["rooms"] if r["id"] == room_id)
    out = []
    for k in range(8):
        out += L._wall_slots(spec, room, w, d, random.Random(seed + k), with_front=True)
    return out


def test_an_edge_with_no_wall_offers_no_slot():
    s = _spec()
    assert _on_edge(_slots(s, "west"), 0.0, 1.2, 0.5, _back(s)) == []


def test_an_edge_with_a_wall_offers_slots():
    """A guard: the same edge with a partition on it is a wall to stand on."""
    s = _spec([{"story": 0, "axis": "Y", "pos": 0.0, "start": -7.0, "end": 7.0}])
    assert _on_edge(_slots(s, "west"), 0.0, 1.2, 0.5, _back(s))


def test_a_part_wall_backs_only_the_pieces_it_holds_whole():
    s = _spec([{"story": 0, "axis": "Y", "pos": 0.0, "start": -7.0, "end": 0.0}])
    got = _on_edge(_slots(s, "west"), 0.0, 1.2, 0.5, _back(s))
    assert got, "the wall's half of the edge offers no slot"
    for x, y, sx, sy, _r, _f in got:
        assert y - sy / 2.0 >= -7.0 - 1e-6 and y + sy / 2.0 <= 0.0 + 1e-6, (y, sy)


def test_an_exterior_edge_is_still_a_wall():
    """A guard: the building's own walls stand on every side. A slot's back
    is `short / 2 + back` off its edge: x -10 + 0.25 + back on the W wall,
    y -7 + 0.25 + back on the S."""
    s = _spec()
    slots = _slots(s, "west")
    off = 0.25 + _back(s)
    assert [q for q in slots if abs(q[0] - (-10.0 + off)) < 1e-6], "no slot on the W wall"
    assert [q for q in slots if abs(q[1] - (-7.0 + off)) < 1e-6], "no slot on the S wall"


def _unbacked(spec):
    """Furnished wall pieces with no built wall behind them, as the finding's
    census counts them."""
    stems = {k for k, p in L._PIECES.items() if p.get("where") == "wall"}
    rooms = {L._room_tag(r): r for r in spec.get("rooms") or []}
    walls = layout_lint.built_walls(spec)
    out = []
    for v in spec.get("volumes") or []:
        if not MF.furnished_by_this_pass(v, set(rooms)):
            continue
        m = MF._GENERATED.match(str(v.get("name")))
        if m.group("stem") not in stems:
            continue
        room = rooms[m.group("tag")]
        story = int(room.get("story", 0) or 0)
        x0, y0, x1, y1 = room["bounds"]
        vx0, vx1 = v["x"] - v["size_x"] / 2.0, v["x"] + v["size_x"] / 2.0
        vy0, vy1 = v["y"] - v["size_y"] / 2.0, v["y"] + v["size_y"] / 2.0
        edges = [(1, y0, vy0 - y0, (vx0, vx1)), (1, y1, y1 - vy1, (vx0, vx1)),
                 (0, x0, vx0 - x0, (vy0, vy1)), (0, x1, x1 - vx1, (vy0, vy1))]
        n, line, _gap, (a0, a1) = min(edges, key=lambda e: abs(e[2]))
        run = max(1e-9, a1 - a0)
        cover = max([sum(max(0.0, min(a1, s1) - max(a0, s0)) for s0, s1 in spans) / run
                     for _l, ws, wn, plane, _h, spans in walls
                     if ws == story and wn == n and abs(plane - line) <= TOL] or [0.0])
        if cover < COVER:
            out.append(v["name"])
    return out


def _library():
    for m in sorted(os.listdir(os.path.join(HERE, "build"))):
        if not m.endswith(".manifest.json") or m.startswith("lf_"):
            continue
        p = os.path.join(HERE, "specs", m[:-len(".manifest.json")] + ".json")
        if os.path.exists(p):
            yield os.path.basename(p)[:-5], json.load(open(p, encoding="utf-8"))


def test_no_library_wall_piece_stands_without_a_wall():
    got = {n: u for n, s in _library() for u in [_unbacked(s)] if u}
    assert not got, {n: len(u) for n, u in got.items()}


def test_the_delis_open_edge_carries_nothing():
    """deli_a01's customer floor meets its deli counter room across open floor
    at y -3.0: its ATM and two lottery boards stood there, in front of the
    case's service front."""
    s = json.load(open(os.path.join(HERE, "specs", "deli_a01.json"), encoding="utf-8"))
    room = next(r for r in s["rooms"] if r["id"] == "customer_floor")
    tag = L._room_tag(room)
    on_edge = [v["name"] for v in s["volumes"] if tag in v["name"]
               and v["y"] + v["size_y"] / 2.0 > room["bounds"][3] - 0.5]
    assert on_edge == [], on_edge


def test_a_generated_deli_furnishes_against_walls_only():
    for mode in ("heist", "assault"):
        s = presets.make("corner_deli", name="corner_deli_t", mode=mode)
        assert _unbacked(s) == [], (mode, _unbacked(s))


def test_the_library_is_a_fixed_point_of_furnish():
    """`migrate_furnish_recipes.main`'s own walk: a spec with no rooms -- an
    Empty, a facade, a demo -- is never furnished, and `migrate` on one only
    adds an empty `volumes` key (this test's first draft called it on all 16
    and read that as a moved library)."""
    for name, s in _library():
        if not s.get("rooms"):
            continue
        before = json.dumps(s, sort_keys=True)
        MF.migrate(s)
        assert json.dumps(s, sort_keys=True) == before, name
