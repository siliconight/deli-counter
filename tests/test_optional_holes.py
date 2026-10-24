"""A hole in a floor is an optional route, left out when asked (0.237.0; the factory's roadmap 269).

The walker, 2026-10-20: "stairs and ladders should be the primary way to get between floors in this game...with the
holes in floors being somewhat rare...but still at our disposal to use if needed/desired to add some more ways to
navigate levels". Measured before this (the factory's `docs/findings/hole_frequency/`): every corner-deli level carried
the deli's cut drop -- both of the deli family's themeable variants had one -- and every single-building deli and
county-hospital level carried its preset's.

`hole_causes.without_holes` leaves out every drop a player would see -- a floor hole, a hatch below the roof -- and the
authored slab holes under it, and keeps a drop that opens into a stair's own well (nothing of it shows). `presets.make`
takes `holes=False` to build without them, which Level Factory asks for on the levels its rate leaves without one;
`holes=None` (and True) builds what the recipe authored, as always. And the deli family keeps a variant without the
drop (`migrate_hole_free_variants.py`: deli_a01), so a lot can be drawn without one.

FAIL ON 0.236.1: there is no `without_holes`, `presets.make` refuses `holes`, and deli_a01 carries the cut drop.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import hole_causes as HC             # noqa: E402
import presets                       # noqa: E402

#: The presets that author a drop a player would see, each with the role it gives it.
DROP_PRESETS = {"police_station": None, "corner_deli": "vertical_attack_angle",
                "compound": "atrium_vertical_sightline", "hospital": "elevator_shaft_horde_channel",
                "casino_tower": "count_room_skylight"}


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _seen(spec):
    """The drops a player would see: `is_drop`, cause not `stair`."""
    return [v for v in HC.drop_links(spec) if HC.cause_for(spec, v) != HC.STAIR]


def _under(spec, links):
    """The authored slab holes whose plan overlaps any of `links`' holes, on any storey."""
    rects = [HC._rect(v) for v in links]
    return [h for h in spec.get("slab_holes") or [] if any(HC._overlaps(HC._rect(h), r) for r in rects)]


def test_without_holes_leaves_out_the_drop_and_the_slab_hole_under_it():
    spec = {"name": "t", "n_stories": 3, "story_height": 3.2, "footprint_x": 20.0, "footprint_y": 16.0,
            "vertical_links": [{"kind": "stair", "from_story": 0, "to_story": 2},
                               {"kind": "floor_hole", "story": 1, "x": -5.0, "y": 0.0, "size_x": 2.2, "size_y": 2.2},
                               {"kind": "hatch", "story": 3, "x": 4.0, "y": 4.0}],
            "slab_holes": [{"story": 1, "x": -5.0, "y": 0.0, "size_x": 2.2, "size_y": 2.2},
                           {"story": 2, "x": -5.0, "y": 0.0, "size_x": 1.0, "size_y": 1.0},
                           {"story": 1, "x": 6.0, "y": -6.0, "size_x": 1.0, "size_y": 1.0}]}
    links, holes = HC.without_holes(spec)
    assert [v["kind"] for v in links] == ["floor_hole"]
    # the slab holes over the drop go with it, on every storey (an atrium, a shaft); another stays
    assert holes == [{"story": 1, "x": -5.0, "y": 0.0, "size_x": 2.2, "size_y": 2.2},
                     {"story": 2, "x": -5.0, "y": 0.0, "size_x": 1.0, "size_y": 1.0}]
    assert spec["slab_holes"] == [{"story": 1, "x": 6.0, "y": -6.0, "size_x": 1.0, "size_y": 1.0}]
    # the stair and the roof hatch are not holes in a floor
    assert [v["kind"] for v in spec["vertical_links"]] == ["stair", "hatch"]
    assert HC.without_holes(spec) == ([], [])


def test_a_drop_into_a_stairs_own_well_stays():
    """deli_a03's hatch opens into its stair's well: nothing of it shows, so it is not a hole to leave out."""
    spec = _spec("deli_a03")
    well = [v for v in HC.drop_links(spec) if HC.cause_for(spec, v) == HC.STAIR]
    assert len(well) == 1
    links, _holes = HC.without_holes(spec)
    assert [v.get("role") for v in links] == ["vertical_attack_angle"]
    assert well[0] in spec["vertical_links"]


@pytest.mark.parametrize("preset", sorted(DROP_PRESETS))
def test_a_preset_builds_without_its_holes_when_asked(preset):
    authored = presets.make(preset)
    seen = _seen(authored)
    assert seen and DROP_PRESETS[preset] in [v.get("role") for v in seen]
    assert presets.make(preset, holes=True) == authored          # True is what the recipe authored
    left = presets.make(preset, holes=False)
    assert _seen(left) == []
    assert _under(left, seen) == []                               # no slab hole left where a drop was
    # nothing else moved out of the vertical links
    assert [v for v in left["vertical_links"] if v not in seen] == left["vertical_links"]


def test_a_preset_without_a_hole_is_unchanged_by_the_flag():
    assert presets.make("bank", holes=False) == presets.make("bank")


def test_the_deli_family_keeps_a_variant_without_the_drop():
    """deli_a01 and deli_a03 are the two delis a themed lot can draw; one of them now has no hole to see."""
    assert _seen(_spec("deli_a01")) == []
    assert _under(_spec("deli_a01"), [{"x": 8.5, "y": -4.0, "size_x": 2.2, "size_y": 2.2}]) == []
    assert [v.get("role") for v in _seen(_spec("deli_a03"))] == ["vertical_attack_angle"]


def test_the_migration_is_done_and_idempotent():
    import migrate_hole_free_variants as M
    assert M.HOLE_FREE == ("deli_a01",)
    assert M.main(["--check"]) == 0
