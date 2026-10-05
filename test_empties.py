"""Empties (0.174.0): a non-enterable shell has openings that look real, keeps
its walls solid, carries no gameplay, and comes in houses that differ.

Roadmap 106. The walker, 2026-10-04, shown the two Empties this repo built
(sealed boxes, no openings) standing in a row: "that just looks like a
continuous concrete wall". The comps -- a Philadelphia rowhouse street and
four industrial lofts, 1990s -- are read off in the factory root's
`docs/reference/EMPTIES_COMPS.md`.

Runs without Blender: bpy and bmesh are stubbed when absent, as in
`test_facade_glazing.py`.
"""
import importlib
import json
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets        # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402

VARIANTS = ["gs_empty_rowhome_a", "gs_empty_rowhome_b", "gs_empty_rowhome_c",
            "gs_empty_rowhome_d", "gs_empty_rowhome_e", "gs_empty_rowhome_f"]


@pytest.fixture
def dc(monkeypatch):
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def _load(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_a_rowhome_empty_has_a_door_and_two_windows_a_storey_on_its_front():
    """The comp's rowhouse: two bays, three storeys, a door to one side and a
    window beside it at street level, two windows on every storey above."""
    s = presets.empty_rowhome(width=6.0, floors=3, wall="brick", door_side="W")
    assert s["facade"] is True and s["footprint_x"] == 6.0 and s["n_stories"] == 3
    front = {w["story"]: w["openings"] for w in s["ext_walls"] if w["wall"] == "S"}
    assert sorted(front) == [0, 1, 2]
    kinds0 = sorted(o["kind"] for o in front[0])
    assert kinds0 == ["door", "window"]
    door = next(o for o in front[0] if o["kind"] == "door")
    assert door["pos"] < 0 and door["tag"] == "front_door"      # the west bay
    for st in (1, 2):
        assert [o["kind"] for o in front[st]] == ["window", "window"]
    # the party walls are not listed, so `auto_exterior` seals them
    assert {w["wall"] for w in s["ext_walls"]} == {"S", "N"}


def test_an_empty_s_door_does_not_carve_its_wall(dc):
    """A door carves a walkable void in an enterable building; behind an
    Empty's door there is nothing, so the wall stays one solid box."""
    boxes = []
    for facade in (False, True):
        spec = spec_from_dict(dict(presets.empty_rowhome(), facade=facade))
        b = dc._Builder(spec)
        got = []
        b._col_box = lambda name, center, size, _g=got: _g.append((name, size))
        hole = {"kind": "door", "u": 0.0, "w": 1.0, "h": 2.2, "sill": 0.0}
        b._wall_collision("ext_0_S", (0.0, -6.0, 1.55), (6.0, 0.3, 3.1), 0, [hole])
        boxes.append(got)
    enterable, empty = boxes
    assert len(enterable) > 1                     # the control: a door carves
    assert len(empty) == 1 and empty[0][1] == (6.0, 0.3, 3.1)


def test_an_empty_records_no_gameplay_from_its_openings(dc):
    """The control is the same call on the same spec made enterable: its
    door is recorded. An Empty's is not."""
    got = {}
    for facade in (False, True):
        spec = spec_from_dict(dict(presets.empty_rowhome(), facade=facade))
        b = dc._Builder(spec)
        b.gameplay = {"openings": [], "markers": [], "interactives": []}
        b.rarity_info = None                      # what `build` sets before the walls
        b.MARKERS = None                          # the collection `_empty` would link into
        made = []
        b._empty = lambda *a, _m=made, **k: _m.append(a[0]) or {}
        front = next(w for w in spec.ext_walls if w.wall == "S" and w.story == 0)
        b._record_openings(front.openings, (0.0, -6.0, 1.55), 0, 6.0, "ext_0_S", 0)
        got[facade] = (len(b.gameplay["openings"]), len(made))
    assert got[False][0] > 0                      # the control: an enterable door is recorded
    assert got[True] == (0, 0)


def test_six_rowhomes_differ_house_to_house():
    """The comp's row reads as houses because each differs: width, storeys,
    wall, cornice and door side are not all alike across the family."""
    specs = [_load(n) for n in VARIANTS]
    assert all(s["facade"] is True for s in specs)
    for key in ("footprint_x", "n_stories", "default_material"):
        assert len({json.dumps(s[key]) for s in specs}) > 1, key
    assert len({s["parapets"][0]["height"] for s in specs}) > 2
    doors = {next(o["pos"] for w in s["ext_walls"] if w["wall"] == "S" and w["story"] == 0
                  for o in w["openings"] if o["kind"] == "door") > 0 for s in specs}
    assert doors == {True, False}
    import material_kind
    for s in specs:
        # three bricks since 0.183.0: the comp's row is brown, red and orange
        assert material_kind.kind_for(s["default_material"]) in (
            "brick", "brick_brown", "brick_orange", "siding", "stone", "paint_block")


def test_the_variants_are_the_preset_s_own_output():
    for n in VARIANTS:
        s = _load(n)
        args = presets.EMPTY_ROWHOMES[n]
        assert s == json.loads(json.dumps(presets.empty_rowhome(name=n, **args)))
