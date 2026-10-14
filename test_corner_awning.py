"""The corner blocks' awning (0.219.0, factory roadmap 241): Zoo's `shop_awning` (>= 1.108.0) over each corner
block's storefront, in its shop's colour.

The comps: "Corners carry the life. The corner building has the shop at grade (lit, awning), homes above."
Deli Counter 0.218.0 built the shop; `shop_awning.plan` says where the awning hangs, `_awning` writes it as a
`prop` slot, and the corner presets name each one's colour. FAILS ON 0.218.0: there is no `shop_awning` module.

Runs without Blender. The last check reads the built slots and is skipped where there is no build/.
"""
import importlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")

import presets       # noqa: E402
import shop_awning   # noqa: E402
import themed_tscn   # noqa: E402
from spec_loader import spec_from_dict  # noqa: E402

CORNERS = presets.EMPTY_CORNERS


def _zoo(module):
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module(module)


def _spec(name, **over):
    return spec_from_dict(presets.empty_midrise(name=name, **dict(CORNERS[name], **over)))


def test_the_forms_are_zoo_s_in_its_order():
    assert shop_awning.FORMS == _zoo("zoo_keeper.core.shop_awning_forms").FORMS


def test_every_corner_hangs_an_awning_in_its_shop_s_colour():
    by_shop = {a["shop"]: a["awning"] for a in CORNERS.values()}
    assert by_shop == {"shop_deli": "shed_red", "shop_grocery": "shed_green",
                       "shop_laundry": "shed_navy", "shop_bar": "shed_black"}


def test_the_awning_hangs_over_the_storefront_and_under_the_homes():
    for name in CORNERS:
        s = _spec(name)
        p = shop_awning.plan(s)
        (cx, cy, cz), (w, d, h) = p["centre"], p["size"]
        assert p["form"] == CORNERS[name]["awning"]
        assert cx == 0.0 and abs(w - (s.footprint_x - 2 * shop_awning.MARGIN)) < 1e-9
        # its back SINK inside the front wall's outer face, its front DEPTH out, inside the terrace's 2.0 m
        face = -(s.footprint_y + s.wall_thick) / 2.0
        assert abs((cy + d / 2.0) - (face + shop_awning.SINK)) < 1e-9
        assert d < 2.0
        # its valance CLEAR over the storefront's head: the door's and the shop windows' one line, 2.4 m up
        assert abs((cz - h / 2.0) - (s.floor_thick / 2.0 + 2.4 + shop_awning.CLEAR)) < 1e-9
        # its top more than 0.3 m under the first floor's front sills
        sills = [s.story_height + s.floor_thick / 2.0 + op.resolved()["sill"]
                 for wall in s.ext_walls if wall.wall == "S" and wall.story == 1 for op in wall.openings]
        assert cz + h / 2.0 < min(sills) - 0.3, (name, cz + h / 2.0, min(sills))


def test_a_mid_rise_hangs_none():
    """The control: `awning` defaults off, and no other Empty carries one."""
    for table in (presets.EMPTY_MIDRISES, presets.EMPTY_MIDRISE_NARROW):
        for name, a in table.items():
            assert shop_awning.plan(spec_from_dict(presets.empty_midrise(name=name, **a))) is None, name


def test_an_unknown_colour_is_refused():
    with pytest.raises(ValueError):
        shop_awning.plan(_spec("gs_cornershop_a", awning="shed_purple"))


def test_every_corner_spec_passes_the_schema():
    """0.218.0's lesson: a spec field the schema does not carry fails the build's own gate."""
    pytest.importorskip("jsonschema")
    import validate
    for name in CORNERS:
        with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
            assert validate._schema_check(json.load(fh)) == [], name


def test_the_awning_s_name_is_zoo_s_name():
    """NEITHER SIDE PARSES A STEM: Zoo's planner and this mirror must name the awning alike. Canvas is the
    awning's own kind, so Zoo's name carries no `_mcanvas`; only Zoo's genome says so, and the resolver tries the
    slot's material and none (`themed_tscn`'s "the resolver tries both"), so Zoo's name is one of the two."""
    kit = _zoo("zoo_keeper.core.kit")
    slot = {"slot_id": "shop_awning", "role": "prop", "size_mod": "full", "style": 1, "material": "canvas",
            "species": "shop_awning", "stock": None, "variant": 0, "form": "shed_red",
            "fit": {"dims": [14.4, 1.2, 0.85], "pivot": "center", "openings": [], "collision": "none"}}
    zoo_stem = kit.plan_kit({"building_id": "t", "slots": [slot]}, theme="delco_1997", style=1)["modules"][0]["stem"]
    ours = [themed_tscn.resolve_themed_stem(slot, "delco_1997", 1, material=m)[0]
            for m in (themed_tscn.stem_material(slot), None)]
    assert "_fshed_red" in zoo_stem and zoo_stem in ours, (zoo_stem, ours)


@pytest.mark.skipif(not os.path.isdir(os.path.join(HERE, "build")), reason="no build/")
def test_every_built_corner_carries_its_awning_slot():
    for name, a in CORNERS.items():
        path = os.path.join(HERE, "build", name + ".slots.json")
        if not os.path.exists(path):
            pytest.skip("%s is not built" % name)
        with open(path, encoding="utf-8") as fh:
            slots = [s for s in json.load(fh)["slots"] if s.get("species") == "shop_awning"]
        assert len(slots) == 1, name
        (s,) = slots
        want = shop_awning.plan(_spec(name))
        assert s["role"] == "prop" and s["form"] == a["awning"] and s["material"] == "canvas", name
        assert s["fit"]["dims"] == [round(v, 4) for v in want["size"]], name
        assert s["transform"]["translation"] == [round(v, 4) for v in want["centre"]], name
        assert s["fit"]["collision"] == "none", name
