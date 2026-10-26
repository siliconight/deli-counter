"""A switchback's seam draws as a raking rail (0.269.0): its collider kept where it was, unseen; a visual-only
`stoop_railing` flight along the upper flight, its high end up the flight. The walker, walking cold run 9386, of the
block over the office switchback's upper flight: "the walling/railing doesn't loook natural yet". FAILS ON 0.268.0."""
import importlib
import json
import os
import sys
import types

import pytest

import stoop
import stairwell

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def _office(dc):
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
    return spec, b, cols


def test_the_seam_keeps_its_collider_unseen_and_gains_a_raking_rail(dc):
    spec, b, cols = _office(dc)
    seams = [(k, g) for k, g in enumerate(stairwell.stair_guards(spec)) if "z_lo" in g]
    assert len(seams) == 1, seams
    k, g = seams[0]
    side = "stair_guard_side_%d" % k
    assert side + "_col" in cols
    assert side not in {s["slot_id"] for s in b.slots}
    rake = [s for s in b.slots if s["slot_id"] == "stair_guard_rake_%d" % k]
    assert len(rake) == 1, [s["slot_id"] for s in b.slots if "rake" in s["slot_id"]]
    r = rake[0]
    assert (r["species"], r["form"], r["fit"]["collision"]) == ("stoop_railing", "flight", "none"), r
    along = round(g["hi"] - g["lo"], 4)
    assert r["fit"]["dims"] == [along, b.RAKE_THICK_M, round(spec.story_height + stoop.RAIL_H, 4)], r["fit"]
    want = 270.0 if g["rises_hi"] else 90.0
    if g["axis"] == "X":
        want = 0.0 if g["rises_hi"] else 180.0
    assert r["transform"]["rot_y"] == want, (r["transform"], g)
    assert "stair_guard_rake_%d_col" % k not in cols


def test_the_rake_draws_no_greybox_box(dc):
    """A greybox visual box is navigation data to Lot's walk bake; the rake has none."""
    import skin_style
    from spec_loader import spec_from_dict
    spec = spec_from_dict(json.load(open(os.path.join(HERE, "specs", "office.json"), encoding="utf-8")))
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    boxes = []
    b._box = lambda name, *a, **k: boxes.append(name)
    b._col_box = lambda *a, **k: None
    b._record_surface = lambda *a, **k: None
    b._stair_guards()
    b._volumes()
    assert not [n for n in boxes if "rake" in n], boxes
