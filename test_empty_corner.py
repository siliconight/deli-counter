"""The corner blocks: a mid-rise Empty whose ground-floor front is a shop (0.218.0, factory roadmap 241).

The urban comps (the factory root's `docs/reference/URBAN_MIDRISE_COMPS.md`): "Corners carry the life. The corner
building has the shop at grade (lit, awning), homes above." `EMPTY_CORNERS` is four mid-rises whose ground floor's
front bays are shop windows, each authored in one shop's state (`empty_panes.SHOP_STATES`, which Zoo >= 1.107.0
paints from its shop atlas), and whose front door is the shop's. The homes above keep their door at the back. They
carry their own prefix, `gs_cornershop_`, so the urban street's deal (`gs_midrise_`) never draws one mid-block.

Runs without Blender: bpy and bmesh are stubbed when absent, as in `test_empty_panes.py`. FAILS ON 0.217.0: no
`EMPTY_CORNERS`, no `SHOP_STATES`, and an opening carrying `pane` does not load.
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

CORNERS = presets.EMPTY_CORNERS


def _zoo(module):
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module(module)


def _built(name):
    return presets.empty_midrise(name=name, **CORNERS[name])


def _load(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def _front(s, story):
    return next(w for w in s["ext_walls"] if w["wall"] == "S" and w["story"] == story)["openings"]


def test_the_shop_states_are_zoo_s_shop_atlas_in_its_order():
    assert empty_panes.SHOP_STATES == _zoo("zoo_keeper.core.shop_panes").STATES


def test_no_shop_state_is_a_window_state():
    assert not set(empty_panes.SHOP_STATES) & set(empty_panes.STATES)


def test_four_corners_four_shops_under_their_own_prefix():
    assert len(CORNERS) == 4
    assert len({a["shop"] for a in CORNERS.values()}) == 4
    assert all(a["shop"] in empty_panes.SHOP_STATES for a in CORNERS.values())
    for name in CORNERS:
        assert name.startswith("gs_cornershop_"), name
        assert not name.startswith(("gs_midrise_", "gs_empty_")), name
    # the prefix is theirs alone: `gs_corner_station` is an enterable gas station
    on_disk = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(HERE, "specs", "gs_cornershop_*.json")))
    assert on_disk == sorted(CORNERS), on_disk
    tables = [presets.EMPTY_MIDRISES, presets.EMPTY_MIDRISE_NARROW, CORNERS]
    seeds = [a["seed"] for t in tables for a in t.values()]
    assert len(seeds) == len(set(seeds)) == 13


def test_every_corner_is_the_preset_s_own_output():
    for name in CORNERS:
        assert _load(name) == json.loads(json.dumps(_built(name))), name


def test_the_ground_floor_front_is_the_shop_and_the_homes_are_above_it():
    for name, a in CORNERS.items():
        s = _built(name)
        assert s["facade"] is True and s["auto_exterior"] is True, name
        ground = _front(s, 0)
        doors = [o for o in ground if o["kind"] == "door"]
        assert [o["tag"] for o in doors] == ["front_door"], (name, doors)
        shop = [o for o in ground if o["kind"] == "window"]
        assert shop and all(o.get("pane") == a["shop"] for o in shop), name
        assert all((o["width"], o["height"], o["sill"]) == (presets.SHOP_WINDOW["width"],
                                                            presets.SHOP_WINDOW["height"],
                                                            presets.SHOP_WINDOW["sill"]) for o in shop), name
        # one head line: the door's top is the windows'
        assert doors[0]["height"] == presets.SHOP_WINDOW["sill"] + presets.SHOP_WINDOW["height"], name
        for st in range(1, a["floors"]):
            assert all("pane" not in o for o in _front(s, st)), (name, st)
        back = [(o["kind"], o.get("tag")) for w in s["ext_walls"] if w["wall"] == "N" and w["story"] == 0
                for o in w["openings"] if o["kind"] == "door"]
        assert back == [("door", "back_door")], (name, back)
        assert s.get("door_finish") == a["door_finish"], name
        assert bool(s.get("security_door")) == bool(a.get("security_door")), name


def test_a_shop_window_leaves_a_pier_either_side():
    """Bays about `MIDRISE_BAY` apart and a shop window `SHOP_WINDOW` wide leave masonry between them."""
    for name, a in CORNERS.items():
        ground = sorted(_front(_built(name), 0), key=lambda o: o["pos"])
        for o, n in zip(ground, ground[1:]):
            gap = (n["pos"] - o["pos"]) * a["width"] - (o["width"] + n["width"]) / 2.0
            assert gap >= 0.5, (name, o["pos"], n["pos"], round(gap, 3))


def test_every_corner_spec_passes_the_schema():
    """FOUND BY THE BUILD, NOT THE SUITE: before the schema took `pane`, the four specs loaded and built, and each
    validation manifest said "'pane' was unexpected" (`schema/level.schema.json`'s opening forbids additional
    properties)."""
    pytest.importorskip("jsonschema")
    import validate
    for name in CORNERS:
        assert validate._schema_check(_load(name)) == [], name


def test_the_rest_of_the_family_is_as_it_was():
    """The control: `shop` and `security_door` default off, so every mid-rise spec stands byte for byte."""
    for table in (presets.EMPTY_MIDRISES, presets.EMPTY_MIDRISE_NARROW):
        for name, a in table.items():
            assert _load(name) == json.loads(json.dumps(presets.empty_midrise(name=name, **a))), name


def test_an_authored_state_is_kept_and_an_unknown_one_refused():
    assert empty_panes.authored(None) is None
    assert empty_panes.authored("shop_bar") == "shop_bar"
    assert empty_panes.authored("lit_bars") == "lit_bars"
    with pytest.raises(ValueError):
        empty_panes.authored("shop_florist")


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


def _windows(dc, d, story):
    from spec_loader import spec_from_dict
    import skin_style
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    H, wt = spec.story_height, spec.wall_thick
    for w in spec.ext_walls:
        if w.wall != "S" or w.story != story:
            continue
        center = (0.0, -spec.footprint_y / 2, w.story * H + H / 2)
        name = f"ext_{w.story}_{w.wall}"
        for j, op in enumerate(w.openings):
            h = b._opening_to_hole(op, spec.footprint_x, name, w.story)
            b._record_opening_slot(f"{name}_open{j}", center, (spec.footprint_x, wt, H), 0, h)
    return [s for s in b.slots if s["role"] == "window"]


def test_a_shop_window_s_slot_carries_its_shop_and_nothing_hangs_in_it(dc):
    """FAILS ON 0.217.0: the pane was always drawn (`empty_panes.choose`), so a shop's window came out a home's."""
    for name, a in CORNERS.items():
        wins = _windows(dc, _built(name), 0)
        assert wins and all(w["pane"] == a["shop"] for w in wins), name
        assert not any(w.get("bars") or w.get("ac") for w in wins), name
        upper = _windows(dc, _built(name), 1)
        assert upper and all(w["pane"] in empty_panes.STATES for w in upper), name


def test_the_shop_window_s_name_is_zoo_s_name():
    """NEITHER SIDE PARSES A STEM: Zoo's planner (>= 1.107.0) and this mirror must name a shop window alike."""
    kit = _zoo("zoo_keeper.core.kit")
    slot = {"slot_id": "w", "role": "window", "size_mod": "full", "style": 1,
            "material": "brick", "glazing": "facade", "pane": "shop_deli",
            "fit": {"dims": [2.9, 0.3, 3.1], "pivot": "center", "collision": "convex",
                    "openings": [{"kind": "window", "width": 2.4, "height": 2.1, "sill": 0.3}]}}
    zoo_stem = kit.plan_kit({"building_id": "t", "slots": [slot]},
                            theme="delco_1997", style=1)["modules"][0]["stem"]
    ours = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1,
                                           material=themed_tscn.stem_material(slot))[0]
    assert "_pshop_deli" in ours and ours == zoo_stem
