"""An Empty's walls close every storey line (0.175.2).

0.175.0 left an Empty only its roof slab, and `_cap_thick` kept stopping each
wall 0.3 m short of the storey line for a slab that was gone: a slot through
every Empty at every storey line, seen as a dark band in cold run 9147's
frames. These read the wall extents the builder derives, storey by storey.

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


def _gaps(dc, facade):
    """Uncovered height between one storey's wall top and the next's base,
    or under the roof slab's underside, per storey line -- metres."""
    spec = spec_from_dict(dict(presets.empty_rowhome(floors=3), facade=facade))
    b = dc._Builder(spec)
    base, top = b._story_range()
    H = spec.story_height
    roof_under = top * H - (spec.roof_thick or spec.floor_thick)
    out = []
    for s in range(base, top):
        wall_top = s * H + H - b._cap_thick(s, top)
        above = roof_under if s + 1 == top else (s + 1) * H
        out.append(round(above - wall_top, 6))
    return out


def test_an_empty_s_walls_leave_no_slot_at_any_storey_line(dc):
    """FAILS ON 0.175.1: 0.3 m open at the two storey lines of a three-storey
    house; the roof line meets its slab."""
    assert _gaps(dc, True) == [0.0, 0.0, 0.0]


def test_an_enterable_building_still_stops_under_each_floor(dc):
    """The control: a building keeps its floor slabs, so its walls stop under
    them -- the z-fight `_cap_thick` exists to prevent. The 0.3 m is the slab
    itself, filled, not a slot."""
    spec = spec_from_dict(dict(presets.empty_rowhome(floors=3), facade=False))
    b = dc._Builder(spec)
    _base, top = b._story_range()
    assert [b._cap_thick(s, top) for s in range(top)] == [spec.floor_thick] * 2 + [
        spec.roof_thick or spec.floor_thick]
