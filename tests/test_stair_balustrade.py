"""A stair hole's rail is a balustrade (0.268.0): Zoo's `stoop_railing`, its level form, painted iron where the palette
has it, the rail's own collider kept. The walker, walking cold run 9386, of the office stair's solid wood guard boxes:
"the walling/railing doesn't loook natural yet". FAILS ON 0.267.0 (no species, wood)."""
import importlib
import json
import os
import sys
import types

import pytest

import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_a_stairs_rail_names_the_balustrade_and_nothing_else_does():
    for name in ("stair_guard_rail_0", "stair_guard_rail_11"):
        assert prop_species.species_for_name(name) == "stoop_railing", name
    for name in ("stair_guard_side_0", "stair_guard_back_10"):
        assert prop_species.species_for_name(name) is None, name
    assert not prop_species.owns_collision("stoop_railing")


@pytest.fixture
def dc(monkeypatch):
    """deli_counter against stub bpy/bmesh, as test_depth_long does."""
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def test_the_offices_rails_are_iron_balustrades_and_keep_their_colliders(dc):
    import skin_style
    from spec_loader import spec_from_dict
    spec = spec_from_dict(json.load(open(os.path.join(HERE, "specs", "office.json"), encoding="utf-8")))
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    cols = []
    b._box = lambda *a, **k: None
    b._col_box = lambda name, *a, **k: cols.append(name)
    b._record_surface = lambda *a, **k: None
    b._stair_guards()
    b._volumes()
    rails = [s for s in b.slots if s["slot_id"].startswith("stair_guard_rail_")]
    assert len(rails) == 6, [s["slot_id"] for s in rails]
    for s in rails:
        assert (s["species"], s["form"], s["material"]) == ("stoop_railing", "level", "metal_painted"), s
        assert s["slot_id"] + "_col" in cols, s["slot_id"]
    walls = [s for s in b.slots if s["slot_id"].startswith(("stair_guard_side_", "stair_guard_back_"))]
    assert walls and all(s["species"] is None and s["form"] is None for s in walls)
