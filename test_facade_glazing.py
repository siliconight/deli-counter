"""A facade shell's windows carry glazing="facade"; an enterable building's do not.

0.80.0 (501c9db) tagged them so Zoo skins a hollow shell's panes with opaque
`glass_facade`. f54ebfe removed the tag eleven hours later by committing a
working copy that predated it, and nothing noticed: no shipped facade had a
window slot, and no test read `_record_opening_slot`, which lives in the one
module that imports bpy at the top.

Why it matters: Zoo's `plan_kit` keys window modules on `glazing` and
`dna.resolve_module_plan` turns "facade" into `glazing_kind="glass_facade"`;
without it the pane takes the `glass` fallback, and Pixelcoat (0.40.0) makes
every theme's `glass` blend -- so the player looks through the window of a
building with nothing inside it.

Runs without Blender: bpy and bmesh are stubbed only when they are absent, and
the slot emitter itself is pure dict-building.

    python -m pytest test_facade_glazing.py -q
"""
import importlib
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets        # noqa: E402
import skin_style     # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402


@pytest.fixture
def dc(monkeypatch):
    """deli_counter imported against stub bpy/bmesh, dropped again after so no
    later test sees the stubs or a module bound to them."""
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def _with_openings(spec):
    """A window and a door on the ground-floor north wall."""
    spec = dict(spec)
    spec["ext_walls"] = [{"wall": "N", "story": 0, "openings": [
        {"kind": "window", "pos": -0.25},
        {"kind": "door", "pos": 0.25},
    ]}]
    return spec


def _opening_slots(dc, d):
    """Drive `_record_opening_slot` exactly as `_opening_piece` does, for every
    opening on the spec's explicit exterior walls. Returns the slots."""
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    H, wt = spec.story_height, spec.wall_thick
    for w in spec.ext_walls:
        assert w.wall == "N", "fixture only places north walls"
        run = spec.footprint_x
        center = (0.0, spec.footprint_y / 2, w.story * H + H / 2)
        size = (run, wt, H)
        wall_name = f"ext_{w.story}_{w.wall}"
        for j, op in enumerate(w.openings):
            h = b._opening_to_hole(op, run, wall_name, w.story)
            b._record_opening_slot(f"{wall_name}_open{j}", center, size, 0, h)
    return b.slots


def _by_role(slots, role):
    out = [s for s in slots if s["role"] == role]
    assert out, f"no {role} slot emitted -- the fixture is not testing anything"
    return out


def test_the_facade_presets_are_facades():
    # The premise of the next test: the preset really sets the flag the
    # emitter reads. If a rename (roadmap 106: facade -> empty) moves the flag,
    # this fails first and says so.
    for make in (presets.facade_rowhome, presets.facade_storefront,
                 presets.facade_industrial):
        assert spec_from_dict(make()).facade is True


def test_a_facade_window_slot_carries_facade_glazing(dc):
    slots = _opening_slots(dc, _with_openings(presets.facade_storefront()))
    for s in _by_role(slots, "window"):
        assert s.get("glazing") == "facade", s["slot_id"]


def test_a_facade_door_carries_no_glazing(dc):
    slots = _opening_slots(dc, _with_openings(presets.facade_storefront()))
    for s in _by_role(slots, "doorway"):
        assert "glazing" not in s, s["slot_id"]


def test_an_enterable_buildings_window_carries_no_glazing(dc):
    # Same shell with the flag off: identical openings, see-through glass.
    d = _with_openings(presets.facade_storefront())
    d["facade"] = False
    slots = _opening_slots(dc, d)
    for s in _by_role(slots, "window") + _by_role(slots, "doorway"):
        assert "glazing" not in s, s["slot_id"]
