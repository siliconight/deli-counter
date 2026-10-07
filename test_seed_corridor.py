"""A seeded piece leaves a body's width on every side (0.195.0).

`seed_cover` cleared each piece of walls, stairs and other pieces by margins
that are each a fraction of a body: 0.3 m off a stair's reserve, 0.9 m off a
volume, 1.0 m from a partition's LINE to the piece's centre, and nothing at
all off an exterior wall. deli_a01's stairwell held two crate stacks that
between them cut its up-stair's foot off from the stairwell's only door:
0.79 m and 0.54 m passages round one, 0.40 m and 0.23 m round the other,
where a bake that erodes 0.4 m a side needs 0.8. Its whole upper storey was
an island the street could not reach in cold runs 9187 and 9188
(`docs/findings/deli_a01_upper_storey_9188/` at the factory root). One crate
was stale -- today's rule refused where it stood -- and the other passed it.

Measured across the library first: 69 seeded pieces in 128 shells; 23
stale, 35 leaving a gap under `min_corridor_width` (1.1 m) to a wall, a stair
reserve or another piece, 40 either.
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract                # noqa: E402
import layout_lint                   # noqa: E402
import level_design                  # noqa: E402

CW = agent_contract.min_corridor_width()
HALF = 0.55                          # a 1.1 m crate stack


def _spec(**kw):
    """A 20 x 14 m building, 0.3 m walls, one straight stair facing N at the centre."""
    s = {"name": "t", "footprint_x": 20.0, "footprint_y": 14.0, "story_height": 3.0,
         "stories": 2, "wall_thick": 0.3, "slab_holes": [],
         "stairs": [{"id": "s0", "x": 0.0, "y": 0.0, "from_story": 0, "to_story": 1,
                     "style": "straight", "facing": "N", "width": 1.2, "run": 4.0,
                     "cut_slabs": True}],
         "rooms": [{"id": "hall", "story": 0, "bounds": [-10.0, -7.0, 10.0, 7.0],
                    "role": "connector", "combat_range": "medium"}],
         "volumes": [], "partitions": [], "ext_walls": [], "markers": []}
    s.update(kw)
    return s


def _crate(name, x, y):
    return {"name": name, "x": x, "y": y, "z": 0.475, "size_x": 1.1, "size_y": 1.1,
            "size_z": 0.95, "collision": "convex"}


def _clear(s, x, y, corridor):
    return level_design._seed_clear(s, s["rooms"][0], x, y, [], half=HALF,
                                    corridor=corridor)


def test_off_an_exterior_wall_a_body_must_pass():
    s = _spec(stairs=[])
    face = -10.0 + 0.15                      # the west wall's inner face
    tight = face + 0.40 + HALF               # 0.40 m: deli_a01's crate
    assert _clear(s, tight, 0.0, False)      # the old rules let it stand
    assert not _clear(s, tight, 0.0, True)
    assert _clear(s, face + CW + 0.05 + HALF, 0.0, True)


def test_off_a_partitions_face_not_its_line():
    s = _spec(stairs=[], partitions=[{"story": 0, "axis": "Y", "pos": 0.0,
                                      "start": -7.0, "end": 7.0, "openings": []}])
    x = 0.15 + 0.50 + HALF                   # centre 1.2 m off the line, 0.5 m gap
    assert _clear(s, x, 0.0, False)
    assert not _clear(s, x, 0.0, True)
    assert _clear(s, 0.15 + CW + 0.05 + HALF, 0.0, True)


def test_off_a_stairs_reserve():
    s = _spec(footprint_y=20.0, rooms=[{"id": "hall", "story": 0,
                                        "bounds": [-10.0, -10.0, 10.0, 10.0],
                                        "role": "connector", "combat_range": "medium"}])
    top = max(r[3] for r in level_design._stair_reserved_rects(s))
    y = top + 0.65 + HALF                    # 0.65 m off the reserve: over the old 0.3
    assert math.hypot(0.0, y) > 2.6 + HALF   # clear of the stair-radius rule
    assert 10.0 - 0.15 - (y + HALF) > CW     # and of the north wall
    assert _clear(s, 0.0, y, False)
    assert not _clear(s, 0.0, y, True)


def test_off_another_piece():
    s = _spec(stairs=[], volumes=[_crate("desk", 5.0, 0.0)])
    x = 5.0 + 0.55 + 1.0 + HALF              # 1.0 m gap: over the old 0.9
    assert _clear(s, x, 0.0, False)
    assert not _clear(s, x, 0.0, True)


def test_a_hung_piece_is_not_asked():
    """The corridor is about bodies on the floor; `above` is a hung piece."""
    s = _spec(stairs=[])
    x = -10.0 + 0.15 + 0.40 + HALF
    assert level_design._seed_clear(s, s["rooms"][0], x, 0.0, [], half=HALF,
                                    above=2.2, corridor=True)


def test_seed_cover_keeps_the_corridor():
    """A 6 m deep building, where the old margins stood crates 0.5 m off a
    wall: candidates span y -1.8..1.56, the walls' faces stand at +-2.85.
    (In the 20 x 14 m room above, this seed happened to land every piece a
    body off every wall, and the test passed without the rule: no proof.)"""
    s = _spec(stairs=[], footprint_y=6.0,
              rooms=[{"id": "hall", "story": 0, "bounds": [-10.0, -3.0, 10.0, 3.0],
                      "role": "connector", "combat_range": "medium"}])
    assert level_design.seed_cover(s) > 0
    hx, hy, t = 10.0 - 0.15, 3.0 - 0.15, 0.15
    vols = s["volumes"]
    for v in vols:
        x0, y0 = v["x"] - v["size_x"] / 2, v["y"] - v["size_y"] / 2
        x1, y1 = v["x"] + v["size_x"] / 2, v["y"] + v["size_y"] / 2
        assert min(x0 + hx, hx - x1, y0 + hy, hy - y1) >= CW - 1e-9, v
        for o in vols:
            if o is v:
                continue
            dx = max(o["x"] - o["size_x"] / 2 - x1, x0 - (o["x"] + o["size_x"] / 2), 0.0)
            dy = max(o["y"] - o["size_y"] / 2 - y1, y0 - (o["y"] + o["size_y"] / 2), 0.0)
            assert math.hypot(dx, dy) >= CW - 1e-9, (v["name"], o["name"])


def test_reseat_moves_a_seeded_piece_off_a_wall():
    s = _spec(stairs=[])
    face = -10.0 + 0.15
    s["volumes"] = [_crate("crate_stack_hall_0", face + 0.40 + HALF, 0.0)]
    assert level_design.reseat_piece(s, "crate_stack_hall_0") == (0.0, 0.0)  # L23: nothing
    moved = level_design.reseat_piece(s, "crate_stack_hall_0", corridor=True)
    assert moved is not None and moved != (0.0, 0.0)
    assert s["volumes"][0]["x"] - HALF - face >= CW - 1e-9


def test_reseat_leaves_furniture_to_furnish():
    """The corridor is the seeder's rule; a furnished piece is not moved by it."""
    s = _spec(stairs=[])
    s["volumes"] = [_crate("shelf_r1a2b3c4_0", -10.0 + 0.15 + 0.40 + HALF, 0.0)]
    assert level_design.reseat_piece(s, "shelf_r1a2b3c4_0", corridor=True) == (0.0, 0.0)


def _failing(spec):
    """Every seed_cover piece the seeder's rule, with the corridor, refuses
    where it stands -- asked as the seeder asks it, BEFORE furnish: cover is
    placed first and furniture after (`level_design.enrich`, "the order is
    load-bearing"), so what furnish then stands beside a piece is furnish's
    to keep clear, not the seeder's."""
    import migrate_furnish_recipes
    tags = {level_design._room_tag(r) for r in spec.get("rooms") or []}
    vols = [v for v in spec.get("volumes") or []
            if not migrate_furnish_recipes.furnished_by_this_pass(v, tags)]
    view = dict(spec, volumes=vols)
    bad = []
    for v in vols:
        story = layout_lint.piece_story(view, v)
        if story is None:
            continue
        room = level_design._room_for_point(view, float(v["x"]), float(v["y"]), story)
        if not level_design._seeded_cover(v, room):
            continue
        without = dict(view)
        without["volumes"] = [o for o in vols if o is not v]
        placed = [(float(o["x"]), float(o["y"])) for o in vols
                  if o is not v and level_design._seeded_cover(o, room)]
        half = max(float(v["size_x"]), float(v["size_y"])) / 2.0
        if not level_design._seed_clear(without, room, float(v["x"]), float(v["y"]),
                                        placed, half=half, corridor=True):
            bad.append(v["name"])
    return sorted(bad)


def test_every_seeded_piece_in_the_library_leaves_a_corridor():
    out = {}
    for m in sorted(glob.glob(os.path.join(HERE, "build", "*.manifest.json"))):
        name = os.path.basename(m)[:-len(".manifest.json")]
        p = os.path.join(HERE, "specs", name + ".json")
        if name.startswith("lf_") or not os.path.exists(p):
            continue
        bad = _failing(json.load(open(p, encoding="utf-8")))
        if bad:
            out[name] = bad
    assert out == {}, out


def test_deli_a01s_stairwell_mouth_is_open():
    """The two places the crates stood: the mouth of the corridor between the
    stairs, and the strip between the west wall and the down-stair's guard."""
    spec = json.load(open(os.path.join(HERE, "specs", "deli_a01.json"), encoding="utf-8"))
    for x0, y0, x1, y1 in ((-14.5, 11.3, -12.6, 12.4), (-18.825, 10.0, -17.1, 12.0)):
        for v in spec["volumes"]:
            if layout_lint.piece_story(spec, v) != 0:
                continue
            vx0, vx1 = v["x"] - v["size_x"] / 2, v["x"] + v["size_x"] / 2
            vy0, vy1 = v["y"] - v["size_y"] / 2, v["y"] + v["size_y"] / 2
            assert not (vx0 < x1 and vx1 > x0 and vy0 < y1 and vy1 > y0), v["name"]
