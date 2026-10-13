"""Mid-rise Empties (0.213.0, factory roadmap 241): a brick block of five to twelve storeys with regular
windows and a parapet, non-enterable, kept out of today's streets until a brief asks for it.

The walker, 2026-10-11, chose a NEW URBAN LEVEL TYPE: mid-rise Empties standing at the sidewalk line in
continuous street walls, the enterable buildings among them, and the Delco strip levels left as they are
(the factory root's `docs/reference/URBAN_MIDRISE_COMPS.md`). This is the family's first cut; its penthouse,
corner shop and bay windows each need a capability this builder does not have yet.

Runs without Blender: bpy and bmesh are stubbed when absent, as in `test_empties.py`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets        # noqa: E402
import roofs          # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402

FAMILY = presets.EMPTY_MIDRISES


def _load(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def _built(name):
    return presets.empty_midrise(name=name, **FAMILY[name])


def test_the_family_spans_five_to_twelve_storeys():
    """FAILS ON 0.212.0: there is no family."""
    floors = sorted(a["floors"] for a in FAMILY.values())
    assert floors[0] == 5 and floors[-1] == 12, floors
    assert len(set(floors)) == len(floors), "two blocks the same height"
    assert len({a["seed"] for a in FAMILY.values()}) == len(FAMILY)
    assert len({a["width"] for a in FAMILY.values()}) == len(FAMILY)


def test_every_block_is_the_preset_s_own_output():
    for name in FAMILY:
        assert _load(name) == json.loads(json.dumps(_built(name))), name


def test_the_family_is_named_out_of_today_s_terraces():
    """Level Factory hands every `gs_empty_*` in the library to a brief that stands a terrace
    (`building_library.empty_rows`), so a mid-rise under that prefix would stand in a Delco street."""
    for name in FAMILY:
        assert name.startswith("gs_midrise_") and not name.startswith("gs_empty_"), name
        assert _built(name)["name"] == name


def test_a_mid_rise_is_an_empty():
    """`facade` true is what makes a shell non-enterable in this builder: shut doors, painted windows,
    only its roof slab -- keyed on the flag, never on the name."""
    for name in FAMILY:
        s = _built(name)
        assert s["facade"] is True and s["auto_exterior"] is True and s["has_basement"] is False, name
        assert s["roof_material"] == "tar", name


def test_its_windows_stand_in_regular_bays_on_every_storey_front_and_back():
    for name, a in FAMILY.items():
        s = _built(name)
        walls = {(w["wall"], w["story"]): w for w in s["ext_walls"]}
        assert set(walls) == {(f, st) for f in ("S", "N") for st in range(a["floors"])}, name
        bays = len(walls[("S", 0)]["openings"])
        spacing = a["width"] / bays
        assert 2.8 <= spacing <= 3.4, (name, spacing)
        for (face, st), w in walls.items():
            pos = [o["pos"] for o in w["openings"]]
            assert len(pos) == bays, (name, face, st)
            # the positions are written to four decimals, so equal gaps can differ in the fourth
            gaps = [b - c for b, c in zip(pos[1:], pos)]
            assert max(gaps) - min(gaps) < 2e-4, (name, face, st, gaps)


def test_one_door_a_face_at_grade_and_windows_everywhere_else():
    for name in FAMILY:
        s = _built(name)
        doors = [(w["wall"], w["story"], o.get("tag")) for w in s["ext_walls"] for o in w["openings"]
                 if o["kind"] == "door"]
        assert sorted(doors) == [("N", 0, "back_door"), ("S", 0, "front_door")], (name, doors)
        others = {o["kind"] for w in s["ext_walls"] for o in w["openings"] if o["kind"] != "door"}
        assert others == {"window"}, (name, others)


def test_its_sides_are_party_walls():
    """The street wall touches: the sides are left unlisted, and `auto_exterior` seals them."""
    for name in FAMILY:
        assert {w["wall"] for w in _built(name)["ext_walls"]} == {"S", "N"}, name


def test_every_block_loads_and_fronts_the_street():
    for name in FAMILY:
        spec = spec_from_dict(_built(name))
        assert spec.n_stories == FAMILY[name]["floors"], name
        assert roofs.front_facing(spec) == "S", name
