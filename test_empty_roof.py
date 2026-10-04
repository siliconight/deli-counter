"""An Empty is exterior plus roof (0.175.0): no slab inside it, and a roof slot
so the art pass dresses the roof it does keep.

Cold run 9146, the first level to stand the rowhome Empties (0.174.0) across
a street, was refused at export by Level Factory's greybox-skin gate: 588
slab surfaces in `gb_floor`, every one an Empty's -- 26 placed, 18 or 24
slab tiles each. An Empty has no rooms, so it had no floor or roof slot,
Zoo built it no `floor_` or `roof_` module, and the worldskin's slab pass
had no material to dress them with. Three of every four of those slabs were
a ground floor and storeys nobody can see or reach, inside a sealed box.

Runs without Blender: bpy and bmesh are stubbed when absent, as in
`test_empties.py`.
"""
import importlib
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets        # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402


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


def _slab_levels(dc, facade):
    """The storey index of every slab `_slabs` emits, visual and collision."""
    spec = spec_from_dict(dict(presets.empty_rowhome(floors=3), facade=facade))
    b = dc._Builder(spec)
    vis, col = [], []
    b._box = lambda name, *a, _v=vis, **k: _v.append(name)
    b._col_box = lambda name, *a, _c=col, **k: _c.append(name)
    b._slabs()
    return ({int(n.split("_")[1]) for n in vis},
            {int(n.split("_")[2]) for n in col})


def test_an_empty_keeps_only_its_roof_slab(dc):
    """The control is the same three-storey house made enterable: a ground
    slab, two floors and a roof. An Empty keeps the roof -- visual, so a
    greybox level still has a top on it, and collision, so it stays sealed."""
    assert _slab_levels(dc, False) == ({0, 1, 2, 3}, {0, 1, 2, 3})
    assert _slab_levels(dc, True) == ({3}, {3})


def test_an_empty_records_one_roof_slot_in_its_roof_material(dc):
    spec = spec_from_dict(presets.empty_rowhome(floors=3, wall="brick"))
    b = dc._Builder(spec)
    b.slots = []
    b._record_roof_slots()
    assert [s["role"] for s in b.slots] == ["roof"]
    roof = b.slots[0]
    # the flat roof of a 1990s rowhouse is tar, silver-coated; never its brick
    assert roof["material"] == "concrete"
    assert abs(roof["fit"]["dims"][0] - 6.0) < 1e-9 and abs(roof["fit"]["dims"][1] - 12.0) < 1e-9


def test_the_facade_build_asks_for_its_roof_slot():
    """`build` cannot run here without Blender; this reads the facade branch
    it takes, and fails if the roof slot call leaves it."""
    src = open(os.path.join(HERE, "deli_counter.py"), encoding="utf-8").read()
    branch = src[src.index("# FACADE shell: exterior + roof + theme only."):]
    branch = branch[:branch.index("return\n")]
    assert "self._modular_on()" in branch and "self._record_roof_slots()" in branch
