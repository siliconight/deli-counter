"""A parapet stands on the wall below it (0.292.0).

`_exterior` centres every storey wall on the slab's extent, and the parapet
ring took that extent as its OUTER face -- so it stood half a wall behind the
facade it was meant to carry up, with the roof slab's edge in a recess under
it, because the wall stops under that slab (`_cap_thick`). Measured on
`bank_branch_a02` (the factory's docs/findings/parapet_coping/): the storey
walls' face at y 11.15 and their top at 6.9, the parapet's and the slab's face
at 11.0. The ring now stands on the walls' outer faces and each tile starts at
the wall's top; its top is where it was.

Runs without Blender: bpy and bmesh are stubbed when absent, as in
`test_parapet_slots.py`.
"""
import importlib
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def _ring(dc, spec_dict):
    """Every parapet visual's (name, centre, size), and the spec."""
    spec = spec_from_dict(spec_dict)
    b = dc._Builder(spec)
    b.slots = []
    import skin_style
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    boxes = []
    b._box = lambda name, c, size, *a, **k: boxes.append((name, c, size))
    b._col_box = lambda *a, **k: None
    b._parapets()
    return boxes, spec


def _bounds(boxes):
    lo = [min(c[i] - s[i] / 2 for _n, c, s in boxes) for i in range(3)]
    hi = [max(c[i] + s[i] / 2 for _n, c, s in boxes) for i in range(3)]
    return lo, hi


@pytest.mark.parametrize("spec_dict", [presets.empty_rowhome(floors=3, wall="brick"),
                                       dict(presets.empty_rowhome(floors=2), modular=True)])
def test_the_ring_stands_on_the_walls_outer_faces_from_the_walls_top(dc, spec_dict):
    """FAILS ON 0.291.0: the ring's outer faces were the walls' centrelines
    (+-footprint/2) and its bottom the slab's top."""
    boxes, spec = _ring(dc, spec_dict)
    assert boxes
    wt = spec.wall_thick
    lo, hi = _bounds(boxes)
    assert hi[0] == pytest.approx(spec.footprint_x / 2 + wt / 2)
    assert lo[0] == pytest.approx(-spec.footprint_x / 2 - wt / 2)
    assert hi[1] == pytest.approx(spec.footprint_y / 2 + wt / 2)
    assert lo[1] == pytest.approx(-spec.footprint_y / 2 - wt / 2)
    p = spec.parapets[0]
    z = p.story * spec.story_height
    cap = spec.roof_thick or spec.floor_thick
    # the top storey's wall stops at the roof slab's underside: the parapet
    # starts there, and its top is unchanged
    assert lo[2] == pytest.approx(z - cap)
    assert hi[2] == pytest.approx(z + p.height)


def test_the_corners_still_belong_to_n_and_s(dc):
    """The ring's rule is unchanged on the new extent: N and S span it, E and
    W stand between their inner faces, and no two runs overlap."""
    boxes, spec = _ring(dc, presets.empty_rowhome(floors=3, wall="brick"))
    t = spec.parapets[0].thick
    side = {k: _bounds([b for b in boxes if b[0].split("_")[1] == k]) for k in "NESW"}
    wt = spec.wall_thick
    (nlo, nhi), (elo, ehi) = side["N"], side["E"]
    assert nhi[0] - nlo[0] == pytest.approx(spec.footprint_x + wt)
    assert ehi[1] - elo[1] == pytest.approx(spec.footprint_y + wt - 2 * t)
    assert ehi[1] == pytest.approx(nlo[1])           # E ends at N's inner face
    assert ehi[0] == pytest.approx(nhi[0])           # and shares the outer face
