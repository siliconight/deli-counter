"""A family's street face upstairs stands on its row (0.296.0; the factory's roadmap 79, and the walker of the slice).

The slice's card shop, card_shop_a01, stood two 1.4 m windows on its 20 m street face over an apartment, beside a bank
whose upper storey stands on 3.0 m bays (0.295.0). The walker: "yes to window rhythm". `facade_plan.FRONT_ROWS` names
the families whose street face is composed on every upper storey people reach; `compose_front` lays it as
`compose_unreached` lays a storey nobody reaches, and the windows stay clear glass onto the rooms behind them.

FAIL ON 0.295.1: there is no `compose_front` or `FRONT_ROWS`, and the card shop's spec still carries two windows on its
street face upstairs. The spec tests read the spec alone, so they fail for that reason and not for an import.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import spec_loader   # noqa: E402


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _cut(d, story):
    """{side: openings of `side` on `story` in metres from the wall's centre, as the builder cuts them}."""
    s = spec_loader.spec_from_dict(d)
    out = {}
    for w in s.ext_walls:
        if w.story == story:
            run = s.footprint_x if w.wall in ("N", "S") else s.footprint_y
            out[w.wall] = sorted(round(round(o.pos * run / s.grid) * s.grid, 3) for o in w.openings)
    return out


def test_the_card_shops_street_face_upstairs_stands_on_three_metre_bays():
    cut = _cut(_spec("card_shop_a01"), 1)
    assert cut["S"] == [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]
    # its other faces upstairs, and its ground floor, are as the preset authored them
    assert cut["N"] == [0.0] and cut["W"] == [0.0] and cut["E"] == [0.0]
    assert _cut(_spec("card_shop_a01"), 0)["S"] == [-7.0, -3.0, 4.0]


def test_the_windows_are_clear_glass_onto_rooms_people_reach():
    """Not a facade: the storey has its apartment and its stair, so the emitter keeps the panes clear and lit."""
    import facade_plan
    d = _spec("card_shop_a01")
    assert facade_plan.unreached_storeys(spec_loader.spec_from_dict(d)) == []
    front = [w for w in d["ext_walls"] if w["wall"] == "S" and w["story"] == 1][0]["openings"]
    assert all(o["kind"] == "window" and o.get("material") == "glass" and "pane" not in o for o in front)
    assert {(o["width"], o["sill"]) for o in front} == {(1.4, 1.0)}


def test_the_furniture_was_laid_round_the_windows_that_are_built():
    """Composing again moves nothing, and so refurnishing moves nothing: every piece stands where `furnish` puts it
    with these windows in the wall."""
    import facade_plan
    import migrate_furnish_recipes
    d = _spec("card_shop_a01")
    before = json.dumps(d, sort_keys=True)
    assert all(b == a for _w, _s, b, a in facade_plan.compose_front(d))
    migrate_furnish_recipes.migrate(d)
    assert json.dumps(d, sort_keys=True) == before


def test_the_preset_builds_the_same_face():
    import presets
    spec = presets.make("card_shop", enrich=False)
    assert _cut(spec, 1)["S"] == [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]


def test_only_a_named_family_and_never_a_held_face():
    """A family `FRONT_ROWS` does not name is untouched, and so is a face whose window a drape hangs over -- it was
    hung for the windows that are there."""
    import facade_plan
    pawn = _spec("pawn_shop_a01")
    before = json.dumps(pawn, sort_keys=True)
    assert facade_plan.compose_front(pawn) == [] and json.dumps(pawn, sort_keys=True) == before

    d = copy.deepcopy(_spec("card_shop_a01"))
    front = [w for w in d["ext_walls"] if w["wall"] == "S" and w["story"] == 1][0]
    front["openings"] = front["openings"][:2]
    x = front["openings"][0]["pos"] * float(d["footprint_x"])
    z = float(d["story_height"]) + 1.0 + 0.7
    d["volumes"].append({"name": "window_drape_test", "x": x, "y": -float(d["footprint_y"]) / 2.0 + 0.2, "z": z,
                         "size_x": 1.6, "size_y": 0.1, "size_z": 1.6})
    held = json.dumps(d, sort_keys=True)
    facade_plan.compose_front(d)
    assert json.dumps(d, sort_keys=True) == held
