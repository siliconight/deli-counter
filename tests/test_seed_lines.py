"""A room's seeded pieces stand in one line, or in rows where one line cannot (0.264.0).

The walker, walking cold run 9383, of deli_a03's stair landing: "layout of these tables doesn't seem to have a rhyme
or reason" (the factory's `docs/findings/walk_2026-10-23_deli/`, finding 3; roadmap 300). `seed_cover` stood a room's
pieces where a shuffled, jittered grid's first fits fell, each turned by a coin flip. `_line_up` stands the same
pieces evenly along one straight line, long sides along it; a room no line fits keeps them where they were.

THE TEST THAT MATTERS IS `test_the_library_s_seeded_rooms_stand_in_lines`.
"""
import copy
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import agent_contract        # noqa: E402
import level_design          # noqa: E402
import migrate_seed_lines    # noqa: E402
import migrate_seed_corridor  # noqa: E402

#: Library rooms storing seeded pieces that stand in no lattice, kept where they stood (0.264.0's migration, the
#: factory's `patches/dc_seed_lines/migrate.out.txt`): the two safe rooms too tight for one clear of the room's own
#: route -- night_pawn's, beside the tall crate the shelter pass stood there, and pawn_shop_a01's, whose crates stood
#: on that route at 0.263.0 already.
KEPT = {("night_pawn", "safe_room"), ("pawn_shop_a01", "safe_room")}
LINED = 35


def _spec():
    """A bare 20 x 10 m combat room with nothing in it."""
    return {"name": "t", "footprint_x": 20.0, "footprint_y": 10.0, "story_height": 3.0, "stories": 1,
            "wall_thick": 0.3, "slab_holes": [], "stairs": [], "seed": 7,
            "rooms": [{"id": "lobby", "story": 0, "bounds": [-10.0, -5.0, 10.0, 5.0],
                       "role": "public_entry", "combat_range": "medium"}],
            "volumes": [], "partitions": [], "ext_walls": [], "markers": []}


def _in_a_lattice(pieces):
    """Rows along one axis, the rows evenly spaced, every piece's long side along its row, and every row on the
    longest row's stations (a short row centred under them): one line is a lattice of one row, pieces abreast a
    lattice of one column (0.264.0)."""
    for along, across, key, lon in (("x", "y", "size_x", "size_y"), ("y", "x", "size_y", "size_x")):
        if not all(v[key] >= v[lon] for v in pieces):
            continue
        rows = {}
        for v in pieces:
            rows.setdefault(round(v[across], 2), []).append(round(v[along], 2))
        cs = sorted(rows)
        pitches = [b - a for a, b in zip(cs, cs[1:])]
        if pitches and max(pitches) - min(pitches) > 0.02:
            continue
        full = sorted(max(rows.values(), key=len))
        step = (full[-1] - full[0]) / (len(full) - 1) if len(full) > 1 else 0.0
        if len(full) > 2 and max(abs(b - a - step) for a, b in zip(full, full[1:])) > 0.02:
            continue
        ok = True
        for row in rows.values():
            want = [full[0] + (j + (len(full) - len(row)) / 2.0) * step for j in range(len(row))]
            if len(row) == 1 and len(full) > 1 and len(rows) > 1:
                want = [(full[0] + full[-1]) / 2.0]
            if any(abs(a - b) > 0.02 for a, b in zip(sorted(row), want)):
                ok = False
        if ok:
            return True
    return False


def _in_a_line(pieces):
    return _in_a_lattice(pieces) and (len({round(v["x"], 2) for v in pieces}) == 1 or
                                      len({round(v["y"], 2) for v in pieces}) == 1)


def test_a_bare_room_s_pieces_are_seeded_in_a_line():
    s = _spec()
    assert level_design.seed_cover(s) >= 2
    room = s["rooms"][0]
    mine = [v for v in s["volumes"] if level_design._seeded_cover(v, room)]
    assert len(mine) >= 2 and _in_a_line(mine), [(v["name"], v["x"], v["y"]) for v in mine]


def test_line_up_moves_the_same_pieces_and_nothing_else():
    s = _spec()
    room = s["rooms"][0]
    pieces = [{"name": "crate_stack_lobby_%d" % k, "x": -7.0 + 5 * k, "y": (-1) ** k * 2.0, "z": 0.475,
               "size_x": 1.1, "size_y": 1.1, "size_z": 0.95, "collision": "convex"} for k in range(3)]
    s["volumes"] = copy.deepcopy(pieces)
    assert level_design._line_up(s, room, s["volumes"])
    assert _in_a_line(s["volumes"])
    # a body passes between any two of them: the gap is the contract's corridor, not the centres' spread
    cw = agent_contract.min_corridor_width()
    for a, b in zip(s["volumes"], s["volumes"][1:]):
        gap = max(abs(a["x"] - b["x"]) - (a["size_x"] + b["size_x"]) / 2.0,
                  abs(a["y"] - b["y"]) - (a["size_y"] + b["size_y"]) / 2.0)
        assert gap >= cw - 1e-6, (a["name"], b["name"], gap)
    for a, b in zip(pieces, s["volumes"]):
        assert {k: a[k] for k in a if k not in ("x", "y", "size_x", "size_y")} == \
            {k: b[k] for k in b if k not in ("x", "y", "size_x", "size_y")}


def test_where_one_line_cannot_two_rows_do():
    """Four pieces that want 10.5 m in one line, in a room 9 m long: two rows of two, a body passing every side of
    each, every piece lying the same way (deli_a03's landing in small)."""
    s = _spec()
    s["rooms"][0]["bounds"] = [-4.5, -5.0, 4.5, 5.0]
    s["footprint_x"], s["footprint_y"] = 9.0, 10.0
    room = s["rooms"][0]
    s["volumes"] = [{"name": "%s_lobby_%d" % (stem, k), "x": -2.0 + k, "y": (-1) ** k * 1.5, "z": 0.5, "size_x": sx,
                     "size_y": sy, "size_z": 1.0, "collision": "convex"}
                    for k, (stem, sx, sy) in enumerate((("counter_island", 2.2, 0.8), ("planter_box", 1.4, 0.7),
                                                        ("counter_island", 0.8, 2.2), ("planter_box", 0.7, 1.4)))]
    assert level_design._line_up(s, room, s["volumes"])
    assert _in_a_lattice(s["volumes"]) and not _in_a_line(s["volumes"])
    import migrate_seed_corridor
    assert migrate_seed_corridor.failing(s) == []


def test_a_room_no_line_fits_keeps_its_pieces():
    s = _spec()
    s["rooms"][0]["bounds"] = [-2.0, -2.0, 2.0, 2.0]          # 4 x 4 m: no 2.2 m spread clear of its walls
    s["footprint_x"] = s["footprint_y"] = 4.0
    pieces = [{"name": "crate_stack_lobby_%d" % k, "x": 0.5 * k, "y": 0.0, "z": 0.475, "size_x": 1.1,
               "size_y": 1.1, "size_z": 0.95, "collision": "convex"} for k in range(2)]
    s["volumes"] = copy.deepcopy(pieces)
    assert not level_design._line_up(s, s["rooms"][0], s["volumes"])
    assert s["volumes"] == pieces


def test_the_library_s_seeded_rooms_stand_in_lines():
    """Every library room storing a seeded piece stands it on a lattice -- a lone one on the room's line, two or more
    in a line or rows -- but the one named in KEPT; and the library is a fixed point of the migration."""
    lined, kept = set(), set()
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if not d.get("rooms"):
            continue
        for room, pieces in migrate_seed_lines.rooms_seeded(migrate_seed_corridor._view(d)):
            (lined if _in_a_lattice(pieces) else kept).add((name, room["id"]))
        once = copy.deepcopy(d)
        moved, _kept = migrate_seed_lines.migrate(once)
        assert not moved and once == d, name
    assert kept == KEPT, sorted(kept ^ KEPT)
    assert len(lined) == LINED, sorted(lined)
