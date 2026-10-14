"""A walk-up's fire escape (0.220.0, factory roadmaps 156 and 241): Zoo's `fire_escape` (>= 1.110.0) on the front of
every mid-rise Empty of six storeys or fewer that is no corner block, a storey a slot.

The walker's photo of a brick walk-up: "this is something i'd like to see in our toolset, fireescape stairs brick".
`fire_escape_stack.plan` says where each storey stands, `_fire_escape_stack` writes them as `prop` slots, and
`presets.empty_midrise` asks for one where the block is a walk-up. FAILS ON 0.219.0: there is no `fire_escape_stack`
module.

Runs without Blender. The last check reads the built slots and is skipped where there is no build/.
"""
import importlib
import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")

import fire_escape_stack as FE   # noqa: E402
import presets                   # noqa: E402
import themed_tscn               # noqa: E402
from spec_loader import spec_from_dict  # noqa: E402

ROWS = dict(presets.EMPTY_MIDRISES, **presets.EMPTY_MIDRISE_NARROW, **presets.EMPTY_CORNERS)
IN = 0.0254


def _zoo(module):
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module(module)


def _spec(name, **over):
    return spec_from_dict(presets.empty_midrise(name=name, **dict(ROWS[name], **over)))


def _walkups():
    return sorted(n for n, a in ROWS.items() if a["floors"] <= FE.WALKUP_STOREYS and not a.get("shop"))


def test_zoo_s_numbers_are_zoo_s():
    assert (FE.ZOO_DECK, FE.ZOO_GUARD, FE.ZOO_BAND) == (round(2 * IN, 4), round(36 * IN, 4), round(22 * IN, 4))
    F = _zoo("zoo_keeper.core.fire_escape_forms")
    assert (FE.ZOO_DECK, FE.ZOO_GUARD, FE.ZOO_PROUD, FE.ZOO_BAND, FE.ZOO_HATCH) == (
        F.FRAME, F.GUARD_H, F.POST_PROUD, F.FLIGHT_W, F.HATCH)


def test_the_walk_ups_and_only_they_stand_one():
    assert _walkups() == ["gs_midrise_a", "gs_midrise_b", "gs_midrise_g", "gs_midrise_h", "gs_midrise_i"]
    for name, a in ROWS.items():
        s = presets.empty_midrise(name=name, **a)
        assert (s.get("fire_escape_stack") == "front") == (name in _walkups()), name
        assert ("metal_painted" in {m["id"] for m in s["materials"]}) == (name in _walkups()), name


def test_a_five_storey_walk_up_stands_three_flights_a_top_and_a_drop():
    s = _spec("gs_midrise_a")
    parts = FE.plan(s)
    assert [p["form"] for p in parts] == ["flight_a", "flight_b", "flight_a", "top_b", "drop"]
    assert [p["slot_id"] for p in parts][:4] == ["fire_escape_1", "fire_escape_2", "fire_escape_3",
                                                 "fire_escape_4"]
    h, ft = s.story_height, s.floor_thick
    face = -(s.footprint_y + s.wall_thick) / 2.0
    for p in parts[:4]:
        (x, y, z), (w, d, hh) = p["centre"], p["size"]
        st = int(p["slot_id"].rsplit("_", 1)[1])
        # its deck's top on the storey's walking surface, its back SINK inside the wall's face
        assert math.isclose(z - hh / 2.0 + FE.ZOO_DECK, st * h + ft / 2.0, abs_tol=1e-9), p
        assert math.isclose(y + d / 2.0, face + FE.SINK, abs_tol=1e-9), p
        assert d == FE.DEPTH and w <= FE.WIDTH_MAX
    # a flight's box ends where the next landing's begins
    for a, b in zip(parts[:3], parts[1:4]):
        assert math.isclose(a["centre"][2] + a["size"][2] / 2.0, b["centre"][2] - b["size"][2] / 2.0,
                            abs_tol=1e-9)
    assert math.isclose(parts[3]["size"][2], FE.ZOO_DECK + FE.ZOO_GUARD + FE.ZOO_PROUD, abs_tol=1e-4)


def test_it_stands_on_the_end_bay_away_from_the_door_inside_the_bay():
    for name in _walkups():
        s = _spec(name)
        x, spacing = FE.bay(s)
        door = [op.pos for wl in s.ext_walls if wl.wall == "S" and wl.story == 0 for op in wl.openings
                if op.tag == "front_door"][0] * s.footprint_x
        cols = sorted({op.pos for wl in s.ext_walls if wl.wall == "S" and wl.story == 1 for op in wl.openings})
        assert x in (cols[0] * s.footprint_x, cols[-1] * s.footprint_x), name
        assert abs(x - door) >= abs((cols[0] + cols[-1]) * s.footprint_x - x - door) - 1e-9, name
        for p in FE.plan(s)[:-1]:
            assert p["size"][0] <= spacing - 2 * FE.MARGIN + 1e-9 and abs(p["centre"][0] - x) < 1e-9, name


def test_the_drop_hangs_under_the_lowest_hatch_its_foot_out_of_reach():
    s = _spec("gs_midrise_a")
    parts = FE.plan(s)
    low, drop = parts[0], parts[-1]
    (lx, ly, lz), (lw, ld, lh) = low["centre"], low["size"]
    (dx, dy, dz), (dw, dd, dh) = drop["centre"], drop["size"]
    assert drop["form"] == "drop" and dh > 0.5
    # `flight_a`'s hatch is at -x: the drop hangs between the landing's end and its hatch's inner edge
    assert lx - lw / 2.0 < dx - dw / 2.0 and dx + dw / 2.0 < lx - lw / 2.0 + FE.ZOO_HATCH
    # in the stair band, behind the deck's front bar
    assert ly - ld / 2.0 + FE.ZOO_DECK < dy - dd / 2.0 and dy + dd / 2.0 < ly - ld / 2.0 + FE.ZOO_DECK + FE.ZOO_BAND
    # its top SINK into the lowest deck's frame, its foot DROP_FOOT over the ground floor
    assert math.isclose(dz + dh / 2.0, lz - lh / 2.0 + FE.SINK, abs_tol=1e-4)
    assert math.isclose(dz - dh / 2.0, s.floor_thick / 2.0 + FE.DROP_FOOT, abs_tol=1e-4)


@pytest.mark.parametrize("name,forms", [
    ("gs_midrise_i", ["flight_a", "flight_b", "top_a"]),                         # 4 storeys
    ("gs_midrise_a", ["flight_a", "flight_b", "flight_a", "top_b"]),             # 5
    ("gs_midrise_b", ["flight_a", "flight_b", "flight_a", "flight_b", "top_a"]),  # 6
])
def test_the_last_flight_comes_up_into_the_top_landing_s_hatch(name, forms):
    assert [p["form"] for p in FE.plan(_spec(name))][:-1] == forms


def test_a_side_it_does_not_know_and_a_building_with_no_landing_are_refused():
    s = _spec("gs_midrise_a")
    s.fire_escape_stack = "back"
    with pytest.raises(ValueError):
        FE.plan(s)
    s = _spec("gs_midrise_a")
    s.n_stories = 1
    with pytest.raises(ValueError):
        FE.plan(s)
    assert FE.plan(_spec("gs_midrise_c")) == []                                  # 7 storeys: no walk-up


def test_every_walk_up_spec_passes_the_schema():
    """0.218.0's lesson: a spec field the schema does not carry fails the build's own gate."""
    pytest.importorskip("jsonschema")
    import validate
    for name in _walkups():
        with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
            assert validate._schema_check(json.load(fh)) == [], name


def test_the_fire_escape_s_names_are_zoo_s():
    """NEITHER SIDE PARSES A STEM: Zoo's planner and this mirror must name each storey alike."""
    kit = _zoo("zoo_keeper.core.kit")
    for form, dims in (("flight_a", [2.6, 1.2, 3.1]), ("top_b", [2.6, 1.2, 0.9712]), ("drop", [0.45, 0.05, 0.853])):
        slot = {"slot_id": "fire_escape_1", "role": "prop", "size_mod": "full", "style": 1,
                "material": "metal_painted", "species": "fire_escape", "stock": None, "variant": 0, "form": form,
                "fit": {"dims": dims, "pivot": "center", "openings": [], "collision": "none"}}
        zoo_stem = kit.plan_kit({"building_id": "t", "slots": [slot]}, theme="delco_1997",
                                style=1)["modules"][0]["stem"]
        ours = [themed_tscn.resolve_themed_stem(slot, "delco_1997", 1, material=m)[0]
                for m in (themed_tscn.stem_material(slot), None)]
        assert "_f" + form in zoo_stem and zoo_stem in ours, (zoo_stem, ours)


@pytest.mark.skipif(not os.path.isdir(os.path.join(HERE, "build")), reason="no build/")
def test_every_built_walk_up_carries_its_stack():
    for name in _walkups():
        path = os.path.join(HERE, "build", name + ".slots.json")
        if not os.path.exists(path):
            pytest.skip("%s is not built" % name)
        with open(path, encoding="utf-8") as fh:
            slots = [s for s in json.load(fh)["slots"] if s.get("species") == "fire_escape"]
        want = FE.plan(_spec(name))
        assert [s["slot_id"] for s in slots] == [p["slot_id"] for p in want], name
        for s, p in zip(slots, want):
            assert s["role"] == "prop" and s["form"] == p["form"] and s["material"] == "metal_painted", name
            assert s["fit"]["dims"] == [round(v, 4) for v in p["size"]], name
            assert s["transform"]["translation"] == [round(v, 4) for v in p["centre"]], name
            assert s["fit"]["collision"] == "none", name
