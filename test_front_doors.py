"""An Empty's front door: a painted finish per house, and on some a black iron
security door (0.182.0).

The walker's photographs (the factory root's `docs/reference/EMPTIES_COMPS.md`,
"Window comps"): the South Philly row's doors are painted house by house, and
one carries "a black iron security door with a grille". Every Empty door
rendered the same brown wood until now. AUTHORED per house, like `vacant`: a
seeded draw over the six rowhomes gave three finishes, two of them twice, and
no iron door at all. Zoo (>= 1.72.0) paints the leaf and builds the security
door Patina (>= 0.28.0) orders; the back door keeps the stained wood.

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
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")

import empty_panes   # noqa: E402
import presets       # noqa: E402
import themed_tscn   # noqa: E402


def test_only_the_front_door_carries_the_house_s_door():
    """FAILS ON 0.181.0: nothing carried a door."""
    assert empty_panes.door("front_door", "navy", True) == {"door": "navy", "security_door": True}
    assert empty_panes.door("back_door", "navy", True) == {}
    assert empty_panes.door(None, "navy", True) == {}
    assert empty_panes.door("front_door", None, False) == {}


def test_an_unknown_finish_is_refused_not_dropped():
    with pytest.raises(ValueError):
        empty_panes.door("front_door", "purple")


def _zoo(module):
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module(module)


def test_the_finishes_are_zoo_s():
    assert empty_panes.DOOR_FINISHES == tuple(_zoo("zoo_keeper.core.doors").FINISHES)


def test_the_name_is_zoo_s_name():
    """NEITHER SIDE PARSES A STEM: Zoo's planner and this mirror must build
    the same one from the same slot."""
    kit = _zoo("zoo_keeper.core.kit")
    slot = {"slot_id": "d", "role": "doorway", "size_mod": "full", "style": 1,
            "material": "brick", "glazing": "facade", "door": "navy",
            "fit": {"dims": [1.0, 0.3, 3.1], "pivot": "center", "collision": "convex",
                    "openings": [{"kind": "door", "width": 1.0, "height": 2.3, "sill": 0.0}]}}
    zoo_stem = kit.plan_kit({"building_id": "t", "slots": [slot]},
                            theme="delco_1997", style=1)["modules"][0]["stem"]
    ours = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1,
                                           material=themed_tscn.stem_material(slot))[0]
    assert "_enavy" in ours and ours == zoo_stem


def test_the_family_authors_a_different_door_on_every_house_and_two_iron():
    doors = [a.get("door_finish") for a in presets.EMPTY_ROWHOMES.values()]
    assert None not in doors and len(set(doors)) == len(doors) == 6
    assert set(doors) <= set(empty_panes.DOOR_FINISHES)
    assert sum(1 for a in presets.EMPTY_ROWHOMES.values() if a.get("security_door")) == 2


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


def _doors(dc, d):
    from spec_loader import spec_from_dict
    import skin_style
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    H, wt = spec.story_height, spec.wall_thick
    for w in spec.ext_walls:
        if w.story != 0:
            continue
        y = -spec.footprint_y / 2 if w.wall == "S" else spec.footprint_y / 2
        name = f"ext_0_{w.wall}"
        for j, op in enumerate(w.openings):
            h = b._opening_to_hole(op, spec.footprint_x, name, 0)
            b._record_opening_slot(f"{name}_open{j}", (0.0, y, H / 2), (spec.footprint_x, wt, H), 0, h)
    return [s for s in b.slots if s["role"] == "doorway"]


def test_the_front_door_slot_carries_the_finish_and_the_back_door_s_does_not(dc):
    s = presets.empty_rowhome(floors=3, door_finish="oxblood", security_door=True)
    doors = _doors(dc, s)
    assert len(doors) == 2
    front = [d for d in doors if "door" in d]
    assert len(front) == 1 and front[0]["door"] == "oxblood" and front[0]["security_door"] is True
    # the control: the same house made enterable carries neither
    assert not [d for d in _doors(dc, dict(s, facade=False)) if "door" in d or "security_door" in d]


@pytest.mark.skipif(not glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.slots.json")),
                    reason="no built Empties")
def test_every_built_rowhome_s_front_door_is_its_authored_one():
    for name, args in presets.EMPTY_ROWHOMES.items():
        with open(os.path.join(HERE, "build", f"{name}.slots.json"), encoding="utf-8") as fh:
            doors = [s for s in json.load(fh)["slots"] if s["role"] == "doorway" and "door" in s]
        assert [d["door"] for d in doors] == [args["door_finish"]], name
        assert bool(doors[0].get("security_door")) == bool(args.get("security_door")), name
