"""0.153.0 -- a storefront is see-through glass.

A `storefront_glass` wall's full wall and door slots, on a building with an
interior, carry `glazing: "storefront"`, which Zoo 1.18.0 builds as
see-through glass in an aluminium frame; the name mirror carries it as
`_gstorefront` and a storefront door's open state is its own art. Nothing
else moves: remainders, windows, facade shells and every `glass` curtain wall
are untagged. Pinned against Zoo's own kit when the zoo repo is beside this.
"""
import json
import os
import sys

import pytest

import migrate_storefront_glass as M
import themed_tscn

HERE = os.path.dirname(os.path.abspath(__file__))
STORES = ("cr_gas", "fuel_stop_heist", "gas_station", "gas_station_a01", "gas_station_a02",
          "gas_station_a03", "gas_street", "gs_corner_station", "stop_n_go")
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")
#: CLOSED in 0.158.0, kept above what replaced it: fuel_stop_heist and
#: stop_n_go built NON-modular (`modular` unset, mode not `pvp_heist`), so
#: `_exterior` cut each wall as one box with holes and their manifests carried
#: prop slots only -- 51 and 17, every one a prop -- and a storefront tag had
#: no wall slot to ride on. `migrate_modular_storefront` makes every
#: storefront spec build modular; no store is excepted any more.
SHELL_WALLED = ()


def _slots(name):
    return json.load(open(os.path.join(HERE, "build", name + ".slots.json"), encoding="utf-8"))["slots"]


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def test_every_store_calls_its_shop_front_a_storefront():
    assert M.main(["--check"]) == 0, "run: python migrate_storefront_glass.py"
    for name in STORES:
        mats = {w["material"] for w in _spec(name)["ext_walls"] if w.get("story", 0) == 0}
        assert "storefront_glass" in mats and "glass" not in mats, (name, mats)


def test_every_storefront_spec_builds_modular():
    import migrate_modular_storefront as MM
    assert MM.main(["--check"]) == 0, "run: python migrate_modular_storefront.py"
    # deli_counter imports bpy, so its constant is read from the source
    import ast
    tree = ast.parse(open(os.path.join(HERE, "deli_counter.py"), encoding="utf-8").read())
    (dc,) = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
             and any(getattr(t, "id", None) == "STOREFRONT_MATERIALS" for t in n.targets)]
    assert tuple(MM.STOREFRONT_MATERIALS) == tuple(dc)


def test_the_once_shell_walled_stores_have_storefront_slots():
    # 0.158.0: the gap SHELL_WALLED named is closed
    for name in ("fuel_stop_heist", "stop_n_go"):
        tagged = [s for s in _slots(name) if s.get("glazing") == "storefront"]
        assert tagged and {s["role"] for s in tagged} <= {"wall", "doorway"}, name


@pytest.mark.parametrize("name", [n for n in STORES if n not in SHELL_WALLED])
def test_only_the_storefronts_full_walls_and_doors_are_tagged(name):
    spec = _spec(name)
    walls = {"ext_0_" + w["wall"] for w in spec["ext_walls"]
             if w.get("story", 0) == 0 and w["material"] == "storefront_glass"}
    tagged = [s for s in _slots(name) if s.get("glazing") == "storefront"]
    assert tagged, name
    for s in tagged:
        assert s["wall"] in walls and s["role"] in ("wall", "doorway") and s["size_mod"] == "full", s["slot_id"]
    # and every full wall and door on those walls IS tagged
    for s in _slots(name):
        if s.get("wall") in walls and s["role"] in ("wall", "doorway") and s.get("size_mod") == "full":
            assert s.get("glazing") == "storefront", s["slot_id"]


def test_a_curtain_wall_and_a_facade_shell_are_not_storefronts():
    """`glass` is every bank's and tower's opaque curtain wall."""
    import glob
    for p in sorted(glob.glob(os.path.join(HERE, "build", "*.slots.json"))):
        b = os.path.basename(p)[: -len(".slots.json")]
        if b in STORES or b == "card_shop_a01":
            continue
        slots = json.load(open(p, encoding="utf-8"))["slots"]
        assert not [s for s in slots if s.get("glazing") == "storefront"], b


def test_the_storefront_stem_and_its_fallback():
    s = {"slot_id": "s", "role": "wall", "size_mod": "full", "style": 2, "material": "glass_facade",
         "glazing": "storefront", "fit": {"dims": [2.0, 0.3, 3.9], "pivot": "center", "openings": []}}
    stem, _ = themed_tscn.resolve_themed_stem(s, "delco_1997", 2, material="glass_facade")
    assert stem == "wall_delco_1997_02_w200_mglass_facade_gstorefront"
    # a library without it falls back to the plain opaque wall
    got = themed_tscn.resolve_slot_choice(s, "delco_1997", 2, None)
    assert got[0].endswith("_gstorefront")


def _zoo_kit():
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    import importlib
    return importlib.import_module("zoo_keeper.core.kit")


def test_the_mirror_names_what_zoo_plans_for_a_storefront():
    kit = _zoo_kit()
    assert tuple(kit.STEM_GLAZINGS) == tuple(themed_tscn.STEM_GLAZINGS)
    slots = [s for s in _slots("gas_station_a02") if s.get("glazing") == "storefront"]
    plan = kit.plan_kit({"building_id": "t", "slots": slots}, theme="delco_1997", style=1)
    planned = {m["stem"] for m in plan["modules"]}
    for s in slots:
        mat = themed_tscn.stem_material(s)
        stem, _ = themed_tscn.resolve_themed_stem(s, "delco_1997", 1, material=mat)
        assert stem in planned, (stem, sorted(planned))
    # a storefront door's open state: Zoo builds it, the composer places it
    door = next(s for s in slots if s["role"] == "doorway")
    variants = themed_tscn.state_variant_stems(door, "delco_1997", 1, None)
    assert [v[0] for v in variants] == ["open"] and variants[0][1] in planned, variants
