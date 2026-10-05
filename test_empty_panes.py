"""An Empty's windows carry a painted state (0.179.0).

The walker's Bloodlines comp, read off in the factory root's
`docs/reference/EMPTIES_COMPS.md` ("LIT WINDOWS AT NIGHT"): mixed per
building, most dark, some lit, bars at street level, a vacant house boarded.
Zoo (>= 1.64.0) paints the states; this chooses them, and names the module
the same way Zoo does.

Runs without Blender: bpy and bmesh are stubbed when absent, as in
`test_facade_glazing.py`.
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
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")

import empty_panes   # noqa: E402
import presets       # noqa: E402
import themed_tscn   # noqa: E402


def _zoo(module):
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module(module)


def test_the_states_are_zoo_s_atlas_in_its_order():
    assert empty_panes.STATES == _zoo("zoo_keeper.core.window_panes").STATES


def test_most_windows_are_dark_and_only_the_street_has_bars():
    ground = [empty_panes.choose("b", 1, "s%d" % i, 0) for i in range(2000)]
    upper = [empty_panes.choose("b", 1, "s%d" % i, 2) for i in range(2000)]
    lit = lambda xs: sum(x.startswith("lit") for x in xs) / len(xs)   # noqa: E731
    assert 0.2 < lit(ground) < 0.36 and 0.3 < lit(upper) < 0.46
    assert not any(x.endswith("_bars") for x in upper)
    assert sum(x.endswith("_bars") for x in ground) > 600
    assert empty_panes.choose("b", 1, "s1", 0) == empty_panes.choose("b", 1, "s1", 0)


def test_a_vacant_house_is_boarded_and_the_family_has_one():
    assert {empty_panes.choose("b", 1, "s%d" % i, i % 3, vacant=True) for i in range(20)} == {"boarded"}
    vacant = [n for n, a in presets.EMPTY_ROWHOMES.items() if a.get("vacant")]
    assert len(vacant) == 1, vacant


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
        if w.wall != "S":
            continue
        center = (0.0, -spec.footprint_y / 2, w.story * H + H / 2)
        name = f"ext_{w.story}_{w.wall}"
        for j, op in enumerate(w.openings):
            h = b._opening_to_hole(op, spec.footprint_x, name, w.story)
            b._record_opening_slot(f"{name}_open{j}", center, (spec.footprint_x, wt, H), 0, h)
    return [s for s in b.slots if s["role"] == "window"]


def test_an_empty_s_window_carries_its_state_and_an_enterable_one_does_not(dc):
    """FAILS ON 0.178.0: no state on any window. The control is the same
    house made enterable: see-through glass is never painted."""
    s = presets.empty_rowhome(floors=3)
    empty = _windows(dc, s)
    assert empty and all(w.get("pane") in empty_panes.STATES for w in empty)
    assert all("pane" not in w for w in _windows(dc, dict(s, facade=False)))
    boarded = _windows(dc, presets.empty_rowhome(floors=3, vacant=True))
    assert {w["pane"] for w in boarded} == {"boarded"}


def test_the_name_is_zoo_s_name():
    """NEITHER SIDE PARSES A STEM: Zoo's planner and this mirror must build
    the same one from the same slot, or the composer misses the module."""
    kit = _zoo("zoo_keeper.core.kit")
    slot = {"slot_id": "w", "role": "window", "size_mod": "full", "style": 1,
            "material": "brick", "glazing": "facade", "pane": "lit_bars",
            "fit": {"dims": [0.95, 0.3, 3.1], "pivot": "center", "collision": "convex",
                    "openings": [{"kind": "window", "width": 0.95, "height": 1.6, "sill": 0.85}]}}
    zoo_stem = kit.plan_kit({"building_id": "t", "slots": [slot]},
                            theme="delco_1997", style=1)["modules"][0]["stem"]
    ours = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1,
                                           material=themed_tscn.stem_material(slot))[0]
    assert "_plit_bars" in ours and ours == zoo_stem


@pytest.mark.skipif(not os.path.isdir(os.path.join(HERE, "build")), reason="no build/")
def test_every_built_empty_window_has_a_state():
    for f in sorted(glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.slots.json"))):
        with open(f, encoding="utf-8") as fh:
            wins = [s for s in json.load(fh)["slots"] if s["role"] == "window"]
        assert wins and all(w.get("pane") in empty_panes.STATES for w in wins), f
