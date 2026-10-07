"""No piece passes through a wall (0.199.0, layout_lint L25).

Measured first across the 146 non-LF specs (the factory's
`docs/findings/pieces_through_walls/`): 19 pieces in 15 shells reach past both
faces of a wall the builder stands.
- THROUGH, 7: the piece's centre stands off the wall and its end comes out the
  far side. Every deli's case runs 0.825 m out of the deli counter into the
  market aisles -- `presets.corner_deli` authors it 7.0 m long from x -14.0
  and its own partition stands at x -8.0 -- and `warehouse`'s 16 m shelving
  run 3.85 m into the room past x 8.0.
- ALONG, 12: the piece is centred on the wall's line and the wall runs inside
  it: racks and forklift bays on y -3.0, two vomitory covers and a rollgate, a
  vault door, four columns.

A generated building is trimmed by the rule at `presets.make` (the corner
deli's case and the hospital's waiting seats); the library by
`migrate_wall_crossing`; the twelve along a wall are frozen in
`wall_crossing_baseline.json` until each is looked at.
"""
import glob
import inspect
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402
import level_design                  # noqa: E402
import presets                       # noqa: E402

BASELINE = os.path.join(HERE, "wall_crossing_baseline.json")


def _spec(**kw):
    """A 20 x 14 m one-storey building, walls 0.3 m, a partition along y at
    x = 0 with its door well clear of where these tests stand pieces."""
    s = {"name": "t", "footprint_x": 20.0, "footprint_y": 14.0, "story_height": 3.0,
         "n_stories": 1, "has_basement": False, "wall_thick": 0.3, "grid": 0.5,
         "auto_exterior": True, "ext_walls": [], "stairs": [], "slab_holes": [],
         "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -7.0, "end": 7.0,
                         "openings": [{"kind": "door", "pos": 0.3, "width": 1.2}]}],
         "rooms": [{"id": "west", "story": 0, "bounds": [-10.0, -7.0, 0.0, 7.0],
                    "role": "connector"},
                   {"id": "east", "story": 0, "bounds": [0.0, -7.0, 10.0, 7.0],
                    "role": "connector"}],
         "volumes": [], "markers": []}
    s.update(kw)
    return s


def _vol(name, x, y, sx=1.0, sy=1.0, sz=1.0, story=0, **kw):
    v = {"name": name, "x": x, "y": y, "z": story * 3.0 + sz / 2.0,
         "size_x": sx, "size_y": sy, "size_z": sz, "collision": "convex",
         "material": "wood"}
    v.update(kw)
    return v


def _rows(s):
    return [(r["name"], r["wall"], r["story"], r["shape"], r["footprint"])
            for r in layout_lint.wall_crossings(s)]


# --------------------------------------------------------------- the rule (L25)

def test_a_piece_through_a_wall_is_found():
    s = _spec(volumes=[_vol("case", -2.0, -3.0, sx=5.0)])
    got = layout_lint.wall_crossings(s)
    assert _rows(s) == [("case", "int_0_0", 0, "through", "box")], got
    # -4.5 .. 0.5 against a band -0.15 .. 0.15: 0.35 m out of the far face
    assert abs(got[0]["past"] - 0.35) < 1e-9, got
    assert any(w.startswith("L25 ") and "'case'" in w
               for w in layout_lint.wall_crossing_findings(s))
    _n, _fails, warns = layout_lint.lint_spec(s, "t")
    assert any(w.startswith("L25 ") and "'case'" in w for w in warns), warns


def test_a_piece_against_a_wall_or_into_it_is_not_through_it():
    """A face on a face, and an end inside the band, are not matter on both
    sides: a shelf backed into a wall is not a shelf through it."""
    against = _vol("against", -2.65, -3.0, sx=5.0)      # -5.15 .. -0.15
    into = _vol("into", -2.5, 3.0, sx=5.0)              # -5.0 .. 0.0
    assert _rows(_spec(volumes=[against, into])) == []


def test_a_piece_centred_on_a_wall_stands_along_it():
    s = _spec(volumes=[_vol("column", 0.0, -3.0, sx=0.5, sy=0.5)])
    got = layout_lint.wall_crossings(s)
    assert _rows(s) == [("column", "int_0_0", 0, "along", "box")]
    assert abs(got[0]["past"] - 0.1) < 1e-9, got           # 0.25 - 0.15 a side


def test_a_piece_past_the_end_of_a_wall_is_not_through_it():
    short = {"story": 0, "axis": "Y", "pos": 0.0, "start": -7.0, "end": 0.0}
    s = _spec(partitions=[short], volumes=[_vol("case", -2.0, 3.0, sx=5.0)])
    assert _rows(s) == []


def test_a_piece_on_another_storey_is_not_through_this_ones_wall():
    s = _spec(n_stories=2, volumes=[_vol("case", -2.0, -3.0, sx=5.0, story=1)])
    assert _rows(s) == []


def test_an_exterior_wall_is_a_wall():
    """Every storey, every side, under `auto_exterior`, as `Builder._exterior`
    builds them -- not only the sides `ext_walls` lists."""
    s = _spec(volumes=[_vol("bench", 5.0, -6.5, sy=2.0)])   # y -7.5 .. -5.5
    got = layout_lint.wall_crossings(s)
    assert _rows(s) == [("bench", "ext_0_S", 0, "through", "box")], got
    assert abs(got[0]["past"] - 0.35) < 1e-9, got


def test_a_turned_piece_is_measured_turned():
    """The greybox and its collider are the authored box, axis-aligned; the
    art is that box turned by `rot_z`. A long piece turned across a wall is
    through it even when its box is not."""
    s = _spec(volumes=[_vol("bench", -1.0, -3.0, sx=0.5, sy=3.0, rot_z=90.0)])
    got = layout_lint.wall_crossings(s)
    assert _rows(s) == [("bench", "int_0_0", 0, "through", "art")], got
    assert abs(got[0]["past"] - 0.35) < 1e-6, got


# --------------------------------------------------------------- the trim

def test_trim_pulls_the_far_end_back_to_the_walls_face():
    import migrate_wall_crossing
    s = _spec(volumes=[_vol("case", -2.0, -3.0, sx=5.0)])
    trimmed, refused = migrate_wall_crossing.trim(s)
    assert refused == [] and [t["name"] for t in trimmed] == ["case"], (trimmed, refused)
    v = s["volumes"][0]
    x0, x1 = v["x"] - v["size_x"] / 2.0, v["x"] + v["size_x"] / 2.0
    assert abs(x0 - -4.5) < 1e-6                                 # the near end stays
    assert abs(x1 - (-0.15 - level_design._WALL_PIECE_AIR)) < 1e-6, (x0, x1)
    assert layout_lint.wall_crossings(s) == []


def test_trim_leaves_a_piece_along_a_wall_and_says_why():
    import migrate_wall_crossing
    s = _spec(volumes=[_vol("column", 0.0, -3.0, sx=0.5, sy=0.5)])
    before = json.dumps(s, sort_keys=True)
    trimmed, refused = migrate_wall_crossing.trim(s)
    assert trimmed == [] and [r[0] for r in refused] == ["column"], refused
    assert "along" in refused[0][2]
    assert json.dumps(s, sort_keys=True) == before


def test_trim_leaves_a_turned_piece_and_says_why():
    import migrate_wall_crossing
    s = _spec(volumes=[_vol("bench", -1.0, -3.0, sx=0.5, sy=3.0, rot_z=90.0)])
    trimmed, refused = migrate_wall_crossing.trim(s)
    assert trimmed == [] and [r[0] for r in refused] == ["bench"], refused


def test_trim_will_not_cut_from_under_a_marker():
    import migrate_wall_crossing
    s = _spec(volumes=[_vol("case", -2.0, -3.0, sx=5.0)],
              markers=[{"type": "cover_low", "id": "C1", "x": 0.4, "y": -3.0, "z": 0.0,
                        "room": "east"}])
    trimmed, refused = migrate_wall_crossing.trim(s)
    assert trimmed == [] and "C1" in refused[0][2], refused


def test_trim_will_not_cut_away_most_of_a_piece():
    """Past half its length a cut is a different piece, not a trim. A centre
    off the band loses less than half plus the air, so this bites only where
    the centre hugs the face: here 5 mm off it, -1.155 .. 0.845, which keeps
    0.995 m of 2.0."""
    import migrate_wall_crossing
    s = _spec(volumes=[_vol("case", -0.155, -3.0, sx=2.0)])
    trimmed, refused = migrate_wall_crossing.trim(s)
    assert trimmed == [] and refused and "half" in refused[0][2], (trimmed, refused)


# --------------------------------------------------------------- the generator

def _generated():
    """Every recipe through `presets.make`, in each mode it takes."""
    out = {}
    for name in sorted(presets.REGISTRY):
        takes_mode = "mode" in inspect.signature(presets.REGISTRY[name]).parameters
        for mode in (("heist", "assault") if takes_mode else (None,)):
            kw = {"mode": mode} if mode else {}
            out[(name, mode)] = presets.make(name, name=name + "_t", **kw)
    return out


def test_no_generated_building_stands_a_piece_through_a_wall():
    got = {k: [r for r in layout_lint.wall_crossings(s) if r["shape"] == "through"]
           for k, s in _generated().items()}
    assert not {k: v for k, v in got.items() if v}, got


def test_the_pieces_generated_along_a_wall_are_the_known_ones():
    """Two recipes stand a piece on a wall's line: the casino's basement vault
    block, centred on the partition at x 0, and the garage's first column.
    Frozen here so a third fails; each needs a look, not a trim."""
    got = sorted({(k[0], r["name"]) for k, s in _generated().items()
                  for r in layout_lint.wall_crossings(s) if r["shape"] == "along"})
    assert got == [("casino_tower", "vault_block"), ("parking_garage", "col_0_00")], got


def test_the_corner_delis_case_stops_at_its_wall():
    s = presets.make("corner_deli", name="corner_deli_t")
    v = next(v for v in s["volumes"] if v["name"] == "deli_case_cover")
    x0, x1 = v["x"] - v["size_x"] / 2.0, v["x"] + v["size_x"] / 2.0
    face = -8.0 - float(s["wall_thick"]) / 2.0
    assert abs(x0 - -14.0) < 1e-6, x0
    assert abs(x1 - (face - level_design._WALL_PIECE_AIR)) < 1e-6, x1


# --------------------------------------------------------------- the library

def _library():
    out = {}
    for m in sorted(glob.glob(os.path.join(HERE, "build", "*.manifest.json"))):
        name = os.path.basename(m)[:-len(".manifest.json")]
        p = os.path.join(HERE, "specs", name + ".json")
        if name.startswith("lf_") or not os.path.exists(p):
            continue
        got = layout_lint.wall_crossings(json.load(open(p, encoding="utf-8")))
        if got:
            out[name] = sorted(r["name"] for r in got)
    return out


def _frozen():
    d = json.load(open(BASELINE, encoding="utf-8"))
    return {k: sorted(v) for k, v in d["wall_crossings"].items()}


def test_no_new_wall_crossing():
    frozen = _frozen()
    new = {k: [n for n in v if n not in frozen.get(k, [])] for k, v in _library().items()}
    assert not {k: v for k, v in new.items() if v}, new


def test_the_baseline_has_not_gone_stale():
    lib = _library()
    gone = {k: [n for n in v if n not in lib.get(k, [])] for k, v in _frozen().items()}
    assert not {k: v for k, v in gone.items() if v}, gone


def test_the_library_delis_cases_stop_at_their_wall():
    for name in ("deli_a01", "deli_a02", "deli_a03", "cr_deli", "night_deli",
                 "corner_deli_heist_01"):
        s = json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))
        v = next(v for v in s["volumes"] if v["name"] == "deli_case_cover")
        x0, x1 = v["x"] - v["size_x"] / 2.0, v["x"] + v["size_x"] / 2.0
        face = -8.0 - float(s["wall_thick"]) / 2.0
        assert abs(x0 - -14.0) < 1e-6 and abs(x1 - (face - level_design._WALL_PIECE_AIR)) < 1e-4, \
            (name, x0, x1)


def test_the_migration_is_a_fixed_point():
    import copy
    import migrate_wall_crossing
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        before = copy.deepcopy(d)
        changed, _why = migrate_wall_crossing.migrate(d)
        assert not changed and d == before, os.path.basename(p)
