"""What hangs in an Empty's window: bars, an air conditioner (0.181.0).

The walker's window photographs (the factory root's
`docs/reference/EMPTIES_COMPS.md`, "Window comps"): "window air conditioners
in nearly every photograph", standing out of the wall, so GEOMETRY; bars proud
of the frame on bolted straps. Bars were painted into the pane until now.
This chooses, per window, what Patina (>= 0.26.0) orders and Zoo (>= 1.69.0)
builds, and writes it on the slot beside the pane.

Runs without Blender: bpy and bmesh are stubbed when absent, as in
`test_empty_panes.py`.
"""
import glob
import importlib
import json
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import empty_panes   # noqa: E402
import presets       # noqa: E402


def test_a_barred_pane_carries_bars():
    """FAILS ON 0.180.0: nothing chose what hangs in a window."""
    for pane in empty_panes.BAR_STATES:
        assert empty_panes.fixtures(pane, "b", 1, "s", 0) == {"bars": True}
    assert set(empty_panes.BAR_STATES) == {s for s in empty_panes.STATES if s.endswith("_bars")}


def test_no_unit_where_one_cannot_sit():
    """Behind flat bars (3.5 cm off the wall, against a unit 30 cm out), in
    a boarded window, or in the box fan's window."""
    for pane in ("boarded", "dark_fan") + empty_panes.BAR_STATES:
        for i in range(400):
            assert "ac" not in empty_panes.fixtures(pane, "b", 1, "s%d" % i, i % 3)


def test_units_mostly_upstairs():
    eligible = [s for s in empty_panes.STATES if s not in empty_panes.NO_AC]
    up = [empty_panes.fixtures(eligible[i % len(eligible)], "b", 1, "s%d" % i, 2) for i in range(4000)]
    gr = [empty_panes.fixtures(eligible[i % len(eligible)], "b", 1, "s%d" % i, 0) for i in range(4000)]
    share = lambda xs: sum(1 for x in xs if x.get("ac")) / len(xs)   # noqa: E731
    assert abs(share(up) - empty_panes.AC_UPPER / 100.0) < 0.03
    assert abs(share(gr) - empty_panes.AC_GROUND / 100.0) < 0.03


def test_the_unit_is_drawn_on_its_own_key():
    """Which windows hold a unit does not depend on which glow, so the
    lit pattern of a street does not move when units are added or retuned."""
    a = [empty_panes.fixtures("dark", "b", 1, "s%d" % i, 1) for i in range(300)]
    b = [empty_panes.fixtures("lit_amber", "b", 1, "s%d" % i, 1) for i in range(300)]
    assert a == b
    assert a == [empty_panes.fixtures("dark", "b", 1, "s%d" % i, 1) for i in range(300)]


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


def _windows(dc, d):
    from spec_loader import spec_from_dict
    import skin_style
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    H, wt = spec.story_height, spec.wall_thick
    for w in spec.ext_walls:
        if w.wall != "S":       # the front, as `test_empty_panes._windows` reads it
            continue
        center = (0.0, -spec.footprint_y / 2, w.story * H + H / 2)
        name = f"ext_{w.story}_{w.wall}"
        for j, op in enumerate(w.openings):
            h = b._opening_to_hole(op, spec.footprint_x, name, w.story)
            b._record_opening_slot(f"{name}_open{j}", center, (spec.footprint_x, wt, H), 0, h)
    return [s for s in b.slots if s["role"] == "window"]


def test_an_empty_s_window_carries_what_hangs_in_it_and_an_enterable_one_does_not(dc):
    s = presets.empty_rowhome(floors=3)
    wins = _windows(dc, s)
    assert wins
    for w in wins:
        assert w.get("bars", False) == (w["pane"] in empty_panes.BAR_STATES), w
        assert not (w.get("ac") and w["pane"] in empty_panes.NO_AC), w
    real = _windows(dc, dict(s, facade=False))
    assert real and not [w for w in real if "bars" in w or "ac" in w]


@pytest.mark.skipif(not glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.slots.json")),
                    reason="no built Empties")
def test_the_built_family_has_both():
    """On the built rowhomes: the fields agree with the panes, and the street
    sees at least one barred window and one air conditioner."""
    bars = ac = 0
    for f in sorted(glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.slots.json"))):
        with open(f, encoding="utf-8") as fh:
            wins = [s for s in json.load(fh)["slots"] if s["role"] == "window"]
        for w in wins:
            assert w.get("bars", False) == (w.get("pane") in empty_panes.BAR_STATES), (f, w["slot_id"])
            assert not (w.get("ac") and w.get("pane") in empty_panes.NO_AC), (f, w["slot_id"])
            bars += bool(w.get("bars"))
            ac += bool(w.get("ac"))
    assert bars >= 1 and ac >= 1, (bars, ac)
