"""A piece placed before a stair changed is never asked again (0.192.0).

`seed_cover`, `furnish` and the presets each clear a piece against the stairs
when they PLACE it, and each is idempotent by name: a room already done is
skipped. So when a stair lengthens (0.124.0) or widens (0.190.0, twin_a01's
flights 0.9 -> 1.2 m), the pieces beside it stay where they were.
- deli_a01, a02 and a03 each stood a counter island 41% and 54% over the
  up-stair's hole, one of them across the flight's arrival, and a crate stack
  over the basement stair's.
- twin_a01's two wardrobes each overhung its widened hole by 0.12 m2. Under
  0.189.0's 0.9 m flights they stood clear: 0.190.0 put them there and its
  swept gate passed it, because walking is unaffected.

L23 asks of the spec as it stands. `reseat_piece` moves a piece to the
nearest place clear of every stair, and a seeded cover piece only where the
seeder itself would put one (`_seed_clear`). Measured across the library
first (`docs/findings/presentation_gates/stale_pieces.py` at the factory
root): 64 pieces in 18 shells.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402
import level_design                  # noqa: E402

BASELINE = os.path.join(HERE, "stale_pieces_baseline.json")


def _spec(**kw):
    """A 20 x 14 m building, one straight stair up the middle facing N."""
    s = {"name": "t", "footprint_x": 20.0, "footprint_y": 14.0, "story_height": 3.0,
         "stories": 2, "slab_holes": [],
         "stairs": [{"id": "s0", "x": 0.0, "y": 0.0, "from_story": 0, "to_story": 1,
                     "style": "straight", "facing": "N", "width": 1.2, "run": 4.0,
                     "cut_slabs": True}],
         "rooms": [{"id": "hall_up", "story": 1, "bounds": [-10.0, -7.0, 10.0, 7.0],
                    "role": "connector"},
                   {"id": "hall", "story": 0, "bounds": [-10.0, -7.0, 10.0, 7.0],
                    "role": "connector"}],
         "volumes": [], "partitions": [], "ext_walls": [], "markers": []}
    s.update(kw)
    return s


def _vol(name, x, y, story, sx=1.0, sy=1.0, sz=1.0, **kw):
    v = {"name": name, "x": x, "y": y, "z": story * 3.0 + sz / 2.0,
         "size_x": sx, "size_y": sy, "size_z": sz, "collision": "convex"}
    v.update(kw)
    return v


def test_a_piece_over_the_stairs_hole_is_found():
    s = _spec(volumes=[_vol("crate", 0.0, 1.0, 1)])
    got = layout_lint.stale_pieces(s)
    assert [p["name"] for p in got] == ["crate"] and got[0]["story"] == 1
    assert got[0]["hole"] > 0.9
    assert any(w.startswith("L23 ") for w in layout_lint.stale_piece_findings(s))


def test_a_piece_on_the_flight_below_is_found():
    """The flight's own storey: not over a hole, in its walk."""
    got = layout_lint.stale_pieces(_spec(volumes=[_vol("crate", 0.0, 0.0, 0)]))
    assert got and got[0]["story"] == 0 and got[0]["walk"] > 0.9


def test_a_piece_clear_of_the_stair_is_not():
    assert layout_lint.stale_pieces(_spec(volumes=[_vol("crate", 6.0, 4.0, 1)])) == []


def test_a_stairs_guard_and_a_hung_sign_are_not_pieces():
    # the sign's BASE 2.2 m over its floor (z is the centre; it is 1 m tall)
    s = _spec(volumes=[_vol("stair_guard_back_0", 0.0, 1.0, 1),
                       dict(_vol("sign", 0.0, 1.0, 1), z=3.0 + 2.2 + 0.5, collision="none")])
    assert layout_lint.stale_pieces(s) == []


def test_reseat_moves_a_piece_clear_and_keeps_it_in_its_room():
    s = _spec(volumes=[_vol("wardrobe", 1.0, 1.0, 1, sx=1.2, sy=0.6, sz=1.9)])
    moved = level_design.reseat_piece(s, "wardrobe")
    assert moved is not None and moved != (0.0, 0.0)
    assert layout_lint.stale_pieces(s) == []
    v = s["volumes"][0]
    assert -10.0 <= v["x"] - 0.6 and v["x"] + 0.6 <= 10.0


def test_reseat_leaves_a_clear_piece_alone():
    s = _spec(volumes=[_vol("crate", 6.0, 4.0, 1)])
    assert level_design.reseat_piece(s, "crate") == (0.0, 0.0)
    assert (s["volumes"][0]["x"], s["volumes"][0]["y"]) == (6.0, 4.0)


def test_reseat_will_not_stand_a_piece_on_another():
    """The nearest clear spot is taken; the piece goes further."""
    s = _spec(volumes=[_vol("crate", 1.3, 1.0, 1),
                       _vol("desk", 2.6, 1.0, 1, sx=1.6, sy=0.8)])
    level_design.reseat_piece(s, "crate")
    c, d = s["volumes"]
    ox = min(c["x"] + 0.5, d["x"] + 0.8) - max(c["x"] - 0.5, d["x"] - 0.8)
    oy = min(c["y"] + 0.5, d["y"] + 0.4) - max(c["y"] - 0.5, d["y"] - 0.4)
    assert not (ox > 0 and oy > 0)
    assert layout_lint.stale_pieces(s) == []


def test_reseat_says_when_nothing_fits():
    tight = _spec(rooms=[{"id": "box", "story": 1, "bounds": [-0.8, -2.0, 0.8, 2.0],
                          "role": "connector"}],
                  volumes=[_vol("crate", 0.0, 1.0, 1)])
    assert level_design.reseat_piece(tight, "crate") is None


def test_twin_a01_wardrobes_are_clear_of_the_widened_stairs():
    """0.190.0's regression, pinned."""
    s = json.load(open(os.path.join(HERE, "specs", "twin_a01.json"), encoding="utf-8"))
    assert [p["name"] for p in layout_lint.stale_pieces(s)] == []


def _library():
    out = {}
    for m in sorted(glob.glob(os.path.join(HERE, "build", "*.manifest.json"))):
        name = os.path.basename(m)[:-len(".manifest.json")]
        p = os.path.join(HERE, "specs", name + ".json")
        if name.startswith("lf_") or not os.path.exists(p):
            continue
        got = layout_lint.stale_pieces(json.load(open(p, encoding="utf-8")))
        if got:
            out[name] = sorted(x["name"] for x in got)
    return out


def _frozen():
    d = json.load(open(BASELINE, encoding="utf-8"))
    return {k: sorted(v) for k, v in d["stale_pieces"].items()}


def test_no_new_stale_piece():
    frozen = _frozen()
    new = {k: [n for n in v if n not in frozen.get(k, [])] for k, v in _library().items()}
    assert not {k: v for k, v in new.items() if v}, new


def test_stale_baseline_has_not_gone_stale():
    lib = _library()
    gone = {k: [n for n in v if n not in lib.get(k, [])] for k, v in _frozen().items()}
    assert not {k: v for k, v in gone.items() if v}, gone


# ------------------------------------------- an authored hole (0.202.0)
# L23's second cause, "UNSEEN": furnish cleared the stairs and never an
# authored `slab_holes` opening. apartment_walkup_a01's dining set stood over
# its 2 x 2 m drop hole; cbp_town_finale's and final_stand's furnished pieces
# inside atrium holes nothing fills.

def _holed(story=1):
    """Two storeys, one 20 x 14 m room each, an authored 4 x 4 m hole in the
    floor of `story`'s room."""
    s = {"name": "holed", "seed": 7, "footprint_x": 20.0, "footprint_y": 14.0,
         "story_height": 3.0, "n_stories": 2, "wall_thick": 0.3, "stairs": [],
         "slab_holes": [{"story": story, "x": 0.0, "y": 0.0, "size_x": 4.0, "size_y": 4.0}],
         "rooms": [{"id": "lower_hall", "story": 0, "role": "connector",
                    "bounds": [-10.0, -7.0, 10.0, 7.0]},
                   {"id": "upper_hall", "story": 1, "role": "connector",
                    "bounds": [-10.0, -7.0, 10.0, 7.0]}],
         "volumes": [], "partitions": [], "ext_walls": [], "markers": []}
    return s


def _over(v, x0, y0, x1, y1):
    return (v["x"] + v["size_x"] / 2 > x0 and v["x"] - v["size_x"] / 2 < x1
            and v["y"] + v["size_y"] / 2 > y0 and v["y"] - v["size_y"] / 2 < y1)


def test_furnish_keeps_off_an_authored_hole_in_its_own_floor():
    for seed in range(8):
        s = _holed()
        s["seed"] = seed
        level_design.furnish(s)
        upper = [v for v in s["volumes"] if layout_lint.piece_story(s, v) == 1]
        assert upper, "nothing furnished upstairs (seed %d)" % seed
        assert layout_lint.stale_pieces(s) == [], (seed, layout_lint.stale_pieces(s))


def test_the_storey_below_a_hole_may_stand_under_it():
    """A guard: a hole in storey 1's floor is a ceiling over storey 0, not a
    floor; the room below is furnished as it was."""
    a, b = _holed(), _holed()
    b["slab_holes"] = []
    level_design.furnish(a)
    level_design.furnish(b)
    lower = lambda s: sorted((v["name"], v["x"], v["y"]) for v in s["volumes"]
                             if layout_lint.piece_story(s, v) == 0)
    assert lower(a) == lower(b)
