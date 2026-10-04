"""A parapet is a wall the art pass dresses (0.177.0).

No pass skinned a parapet: cold run 9148's package carried 324 parapet
surfaces in `gb_wall` (2,744.7 m2), 260 on the Empties -- where the parapet
is the cornice, a grey band along every roofline -- and 64 on the bank tower
and the freight terminal. A parapet is the wall below it carried past the
roof, so it is recorded as that wall's slot: one per visual tile, named as
the tile, in the material of the top storey's wall on its side.

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


def _parapets(dc, spec_dict):
    spec = spec_from_dict(spec_dict)
    b = dc._Builder(spec)
    b.slots = []
    # what `build` sets before any wall is recorded, on both paths
    import skin_style
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    visuals = []
    b._box = lambda name, *a, _v=visuals, **k: _v.append(name)
    b._col_box = lambda *a, **k: None
    b._parapets()
    return b.slots, visuals


def test_every_parapet_tile_is_a_wall_slot_in_the_wall_below_s_material(dc):
    """FAILS ON 0.176.0: no parapet slot at all. The front's top storey is
    siding over a brick house, so the front parapet is siding and the sides
    are brick -- the material is read off the wall below, not the default."""
    s = presets.empty_rowhome(floors=3, wall="brick")
    for w in s["ext_walls"]:
        if w["wall"] == "S" and w["story"] == 2:
            w["material"] = "siding"
    slots, visuals = _parapets(dc, dict(s, modular=True))
    assert visuals and sorted(sl["slot_id"] for sl in slots) == sorted(visuals)
    assert {sl["role"] for sl in slots} == {"wall"}
    by_side = {}
    for sl in slots:
        by_side.setdefault(sl["facing"], set()).add(sl["material"])
    assert by_side["S"] == {"siding"}
    assert by_side["N"] == by_side["E"] == by_side["W"] == {"brick"}
    # the parapet's own size, module-local: (run, thickness, height)
    assert all(abs(sl["fit"]["dims"][2] - 0.8) < 1e-9 and abs(sl["fit"]["dims"][1] - 0.3) < 1e-9
               for sl in slots)


def test_a_build_that_is_not_modular_records_none(dc):
    """The control: walls are recorded only for a modular build, and so are
    parapets -- a greybox-only build keeps its greybox parapet."""
    slots, visuals = _parapets(dc, dict(presets.empty_rowhome(), modular=False))
    assert visuals and slots == []
