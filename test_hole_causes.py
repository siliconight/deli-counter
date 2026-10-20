"""Every hole in a floor has a cause, and what stands round it says so (hole_causes.py, 0.236.0; the factory's roadmap 265).

The walker asked why the levels have holes in their floors and chose to keep the drops and give each a reason to
exist -- "clear to the player that they are there, but also some reason other than a perfectly cut square". A drop's
cause is its link's own `cause`, a hatch link's kind, or a row of `hole_causes.RULES` by the rooms above and below;
`cut` and `broken` stand a Zoo `hole_edge` round the cut and a `hole_spoil` where the drop lands (and, for `cut`, the
crew's `hole_kit` beside it), `hatch` a `roof_hatch` in its `floor` form with the `hatch` interactive; layout_lint L28
names a hole no cause covers.

FAIL ON 0.235.0: there is no `hole_causes` module, so this file does not collect; and with the module alone beside
0.235.0's tree, `VerticalLink` takes no `cause`, the schema refuses one, there is no L28 and the hole species do not own
their collision.
"""
import glob
import json
import os
import sys
import zlib

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hole_causes as HC             # noqa: E402
import layout_lint                   # noqa: E402
import prop_species                  # noqa: E402
import spec_loader                   # noqa: E402
import themed_tscn                   # noqa: E402

SH = 3.2


def _house(above="apartment_hideout", below="kitchen", link=None, volumes=(), partitions=(), up=None, dn=None,
           n_stories=3):
    """A 20 x 16 m house of three 3.2 m storeys, 0.3 m slabs and walls: on storeys 0 and 1 a west room (x -10..0)
    and an east one; a 2.2 m drop in storey 1's floor at (-5, 0), from `above` onto `below` (`up` and `dn` add
    to those two rooms)."""
    west = [-10.0, -8.0, 0.0, 8.0]
    east = [0.0, -8.0, 10.0, 8.0]
    return {"name": "t", "footprint_x": 20.0, "footprint_y": 16.0, "n_stories": n_stories, "story_height": SH,
            "wall_thick": 0.3, "floor_thick": 0.3, "grid": 0.5,
            "rooms": [dict({"id": below, "story": 0, "bounds": west}, **(dn or {})),
                      {"id": "shop", "story": 0, "bounds": east},
                      dict({"id": above, "story": 1, "bounds": west}, **(up or {})),
                      {"id": "hall", "story": 1, "bounds": east}],
            "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -8.0, "end": 8.0},
                           {"story": 1, "axis": "Y", "pos": 0.0, "start": -8.0, "end": 8.0}] + list(partitions),
            "vertical_links": [link or {"kind": "floor_hole", "story": 1, "x": -5.0, "y": 0.0,
                                        "size_x": 2.2, "size_y": 2.2}],
            "volumes": list(volumes)}


def _crate(x, y, story, size=1.0):
    return {"name": "crate_%g_%g" % (x, y), "x": x, "y": y, "z": story * SH + size / 2.0,
            "size_x": size, "size_y": size, "size_z": size}


def _slots(spec):
    slots, notes = HC.hole_slots(spec, lambda material: 1)
    return {s["species"]: (s, e, c, size) for s, e, c, size in slots}, notes


def test_a_cut_hole_gets_its_edge_its_spoil_and_the_crews_kit():
    by, notes = _slots(_house())
    assert sorted(by) == ["hole_edge", "hole_kit", "hole_spoil"] and notes == []
    edge, _e, center, size = by["hole_edge"]
    assert edge["slot_id"] == "hole_edge_1_-50_0" and edge["role"] == "prop" and edge["form"] == "cut"
    # the hole and BAND a side; TOP + two skins + the slab + HANG tall, its top TOP above storey 1's visible floor
    assert edge["fit"]["dims"] == [2.8, 2.8, 0.652]
    assert edge["transform"]["translation"] == [-5.0, 0.0, round(SH + 0.02 + 0.012 - 0.652 / 2.0, 4)]
    assert edge["fit"]["collision"] == "none" and edge["material"] == "wood"
    spoil = by["hole_spoil"][0]
    # on the floor it lands on, the hole and SPILL a side, SKIRT down into the floor's skin
    assert spoil["fit"]["dims"] == [2.7, 2.7, 0.1] and spoil["stock"] == "none" and spoil["form"] == "cut"
    assert spoil["transform"]["translation"] == [-5.0, 0.0, round(0.02 - 0.004 + 0.05, 4)]
    kit, _e, kc, ksize = by["hole_kit"]
    # every side of this hole reaches as far into the room: the first by name, east, its +Y turned west to the hole
    assert kit["transform"]["translation"] == [round(-3.9 + 0.35 + 0.35, 4), 0.0, round(SH + 0.02 - 0.004 + 0.35, 4)]
    assert kit["transform"]["rot_y"] == 270.0
    assert kit["fit"]["dims"] == [1.4, 0.7, 0.7] and ksize == pytest.approx((0.7, 1.4, 0.7))
    assert kit["form"] == "cut" and kit["material"] == "plastic"


def test_a_form_names_the_slab_and_the_ceiling():
    # a concrete floor above is a slab (bars, not joists); a plaster ceiling below breaks as plaster and lath
    s = _house(up={"role": "staging"}, dn={"role": "utility"})
    by, _n = _slots(s)
    assert by["hole_edge"][0]["form"] == by["hole_spoil"][0]["form"] == "cut_slab_plaster"
    by, _n = _slots(_house(up={"floor_material": "concrete"}))
    assert by["hole_edge"][0]["form"] == "cut_slab"
    by, _n = _slots(_house(dn={"ceiling_material": "drywall"}))
    assert by["hole_edge"][0]["form"] == "cut_plaster"


def test_a_broken_floor_gets_an_edge_and_a_spoil_in_its_own_finish_and_no_kit():
    by, notes = _slots(_house(above="bedroom", up={"floor_material": "tile"}, dn={"ceiling_material": "plaster"}))
    assert sorted(by) == ["hole_edge", "hole_spoil"] and notes == []
    assert by["hole_edge"][0]["form"] == "broken_plaster"
    assert by["hole_spoil"][0]["stock"] == "tile"
    by, _n = _slots(_house(above="bedroom", up={"floor_material": "carpet"}))
    assert by["hole_spoil"][0]["stock"] == "carpet"


def test_a_hatch_below_the_roof_gets_a_floor_hatch_with_its_lid_by_the_nearest_wall():
    s = _house(link={"kind": "hatch", "story": 1, "x": -5.0, "y": 0.0})
    by, notes = _slots(s)
    assert sorted(by) == ["roof_hatch"] and notes == []
    slot, entry, center, size = by["roof_hatch"]
    assert slot["slot_id"] == "floor_hatch_1_-50_0" and slot["form"] == "floor" and slot["variant"] == 0
    assert slot["fit"]["dims"] == [1.66, 1.66, 0.03]              # the 1.5 m default hole + 0.08 a side
    assert slot["transform"]["translation"] == [-5.0, 0.0, round(SH + 0.02 - 0.004 + 0.015, 4)]
    # west and east walls 4.25 m off, the first by name: hinged east, so the slot's -Y is east
    assert slot["transform"]["rot_y"] == 270.0
    assert slot["interactive"]["kind"] == "hatch" and slot["interactive"]["default"] == "open"
    assert entry["slot_ref"] == slot["slot_id"] and entry["id"] == slot["interactive"]["id"]
    # a hole that is not square, by the west wall: hinged west, turned 90, its local footprint the world's turned
    s = _house(link={"kind": "hatch", "story": 1, "x": -9.0, "y": 0.0, "size_x": 1.0, "size_y": 1.4})
    slot, _e, _c, size = _slots(s)[0]["roof_hatch"]
    assert slot["transform"]["rot_y"] == 90.0
    assert slot["fit"]["dims"] == [1.56, 1.16, 0.03] and size == pytest.approx((1.16, 1.56, 0.03))


def test_a_floor_hole_the_rules_call_a_hatch_is_one():
    by, _n = _slots(_house(above="armory", below="garage"))
    assert sorted(by) == ["roof_hatch"]


def test_the_links_own_cause_wins_and_a_wrong_one_is_refused():
    s = _house(above="bedroom")
    s["vertical_links"][0]["cause"] = "cut"
    assert "hole_kit" in _slots(s)[0]
    s["vertical_links"][0]["cause"] = "burnt"
    with pytest.raises(ValueError):
        HC.hole_slots(s, lambda material: 1)
    fails, warns = layout_lint.hole_cause_findings(s)
    assert len(fails) == 1 and fails[0].startswith("L28 ") and "'burnt'" in fails[0] and warns == []


def test_l28_names_a_hole_no_cause_covers_and_nothing_stands_round_it():
    s = _house(above="loft", below="shop")
    assert HC.hole_slots(s, lambda material: 1) == ([], [])
    fails, warns = layout_lint.hole_cause_findings(s)
    assert fails == [] and len(warns) == 1
    assert "no cause" in warns[0] and "loft over shop" in warns[0]
    assert warns[0] in layout_lint.lint_spec(s, "t")[2]


def test_a_hole_that_is_not_a_drop_gets_nothing():
    roof = _house(link={"kind": "hatch", "story": 3, "x": -5.0, "y": 0.0})        # roof_hatch.py's
    uncut = _house(link={"kind": "floor_hole", "story": 1, "x": -5.0, "y": 0.0, "cut_slab": False})
    stair = _house(link={"kind": "stair", "from_story": 0, "to_story": 1})
    for s in (roof, uncut, stair):
        assert HC.drop_links(s) == [] and HC.hole_slots(s, lambda material: 1) == ([], [])
        assert layout_lint.hole_cause_findings(s) == ([], [])


def test_the_kit_keeps_off_a_piece_a_door_and_says_when_no_side_has_room():
    by, _n = _slots(_house(volumes=[_crate(-2.5, 0.0, 1)]))
    assert by["hole_kit"][0]["transform"]["rot_y"] == 180.0          # east is taken: north, facing south
    door = {"story": 1, "axis": "Y", "pos": -2.0, "start": -8.0, "end": 8.0,
            "openings": [{"kind": "door", "pos": 0.0, "width": 1.0}]}
    assert layout_lint.DOOR_APPROACH_M > 0.9                         # reaches the east kit's box from x = -2
    by, _n = _slots(_house(partitions=[door]))
    assert by["hole_kit"][0]["transform"]["rot_y"] == 180.0
    boxed = [_crate(-2.5, 0.0, 1), _crate(-7.5, 0.0, 1), _crate(-5.0, 2.5, 1), _crate(-5.0, -2.5, 1)]
    by, notes = _slots(_house(volumes=boxed))
    assert "hole_kit" not in by and notes == ["hole_kit_1_-50_0: no kit -- no side of the hole has room for one"]


def test_the_spoil_keeps_off_the_furniture_below_and_says_when_none_fits():
    by, _n = _slots(_house(volumes=[_crate(-3.5, 0.0, 0)]))
    spoil = by["hole_spoil"][0]
    # cut back from the crate's west face less 2 cm: x -6.35..-4.02, the hole's centre kept under it
    assert spoil["fit"]["dims"] == [2.33, 2.7, 0.1]
    assert spoil["transform"]["translation"][0] == pytest.approx((-6.35 - 4.02) / 2.0)
    by, notes = _slots(_house(volumes=[_crate(-5.0, 0.0, 0, size=3.0)]))
    assert "hole_spoil" not in by
    assert notes == ["hole_spoil_1_-50_0: no spoil -- no floor under the hole clear of furniture for one"]


def test_a_stacked_shaft_lays_one_spoil_where_both_drops_land():
    s = _house()
    s["rooms"] += [{"id": "attic", "story": 2, "bounds": [-10.0, -8.0, 0.0, 8.0]}]
    s["vertical_links"].append({"kind": "floor_hole", "story": 2, "x": -5.0, "y": 0.0, "size_x": 2.2,
                                "size_y": 2.2, "cause": "cut"})
    slots, notes = HC.hole_slots(s, lambda material: 1)
    spoils = [x for x in slots if x[0]["species"] == "hole_spoil"]
    assert len(spoils) == 1 and spoils[0][0]["transform"]["translation"][2] == round(0.02 - 0.004 + 0.05, 4)
    assert notes == ["hole_spoil_2_-50_0: no spoil -- another drop's spoil lies there already"]
    assert sum(1 for x in slots if x[0]["species"] == "hole_edge") == 2


def test_a_hole_too_big_for_its_edge_or_hatch_gets_neither_and_l28_says_so():
    """Zoo builds a slot outside its species' sizes as the plain box at the slot's size, which over a
    hole would cover it: the slot is left out instead."""
    big = _house(link={"kind": "floor_hole", "story": 1, "x": -5.0, "y": 0.0, "size_x": 6.5, "size_y": 6.5})
    by, notes = _slots(big)
    assert sorted(by) == ["hole_kit", "hole_spoil"]                  # the edge would be 7.1 m, past 6.8
    assert by["hole_spoil"][0]["fit"]["dims"] == [7.0, 7.0, 0.1]      # the hole and SPILL a side: Zoo's 7.0
    assert notes == ["hole_edge_1_-50_0: no hole_edge -- 7.1 x 7.1 x 0.652 m is outside its sizes, "
                     "and Zoo would build a box over the hole"]
    (warn,) = layout_lint.hole_cause_findings(big)[1]
    assert "too big to dress" in warn and "hole_edge 7.1 x 7.1 x 0.652" in warn
    wide = _house(link={"kind": "hatch", "story": 1, "x": -5.0, "y": 0.0, "size_x": 2.4, "size_y": 2.4})
    assert _slots(wide) == ({}, ["floor_hatch_1_-50_0: no roof_hatch -- 2.56 x 2.56 x 0.03 m is outside its "
                                 "sizes, and Zoo would build a box over the hole"])
    (warn,) = layout_lint.hole_cause_findings(wide)[1]
    assert "roof_hatch 2.56 x 2.56 x 0.03" in warn
    for sp, dims in (("hole_edge", (2.8, 2.8, 0.652)), ("hole_spoil", (7.0, 0.8, 0.04)),
                     ("hole_kit", HC.KIT), ("roof_hatch", (2.4, 0.9, 0.03))):
        assert HC.fits(sp, dims)
    assert not HC.fits("hole_spoil", (7.01, 2.0, 0.1)) and not HC.fits("hole_edge", (2.8, 2.8, 1.41))


def test_a_slots_variant_is_its_names_and_its_stem_is_zoos():
    s = _house()
    by, _n = _slots(s)
    for sp in ("hole_edge", "hole_spoil", "hole_kit"):
        slot = by[sp][0]
        assert slot["variant"] == zlib.crc32(("t:" + slot["slot_id"]).encode("utf-8")) % 4
    assert _slots(_house()) == (by, [])
    # the rows Zoo's tests/test_hole_forms.py pins for its side of the name
    edge = dict(by["hole_edge"][0], form="cut_slab", variant=2)
    edge["fit"] = dict(edge["fit"], dims=[2.8, 2.8, 0.652])
    assert themed_tscn.resolve_themed_stem(edge, "delco_1997", 1)[0].endswith("_w280_d280_h65_fcut_slab_n2")
    spoil = dict(by["hole_spoil"][0], form="cut", stock="carpet", variant=2)
    spoil["fit"] = dict(spoil["fit"], dims=[2.7, 2.7, 0.1])
    assert themed_tscn.resolve_themed_stem(spoil, "delco_1997", 1)[0].endswith("_w270_d270_h10_fcut_scarpet_n2")
    assert themed_tscn.resolve_themed_stem(edge, "delco_1997", 1)[0].startswith("prop_hole_edge_delco_1997_01_")


def test_a_link_says_its_cause_in_the_schema_and_the_dataclass():
    import jsonschema
    schema = json.load(open(os.path.join(HERE, "schema", "level.schema.json"), encoding="utf-8"))
    link = {"kind": "floor_hole", "story": 1, "x": 0.0, "y": 0.0, "cause": "broken"}
    jsonschema.validate({"name": "t", "vertical_links": [link]}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"name": "t", "vertical_links": [dict(link, cause="burnt")]}, schema)
    assert spec_loader.spec_from_dict({"name": "t", "vertical_links": [link]}).vertical_links[0].cause == "broken"


def test_the_hole_species_own_their_collision():
    for sp in ("hole_edge", "hole_spoil", "hole_kit", "roof_hatch"):
        assert prop_species.owns_collision(sp)


def test_a_hole_in_a_stairs_well_is_the_stairs_and_nothing_stands_round_it():
    """deli_a03's `roof_drop_to_stair` hatch is cut wholly inside `deli_stair_up`'s well: a floor hatch built round it
    hung over the stair, and `circulation.check_shell` read its frame 0.03 m inside the stair's column. rowhouse_raid's
    hatch is 70 % in its stair's well and the rest a bare cut beside it, which L28 names."""
    deli = json.load(open(os.path.join(HERE, "specs", "deli_a03.json"), encoding="utf-8"))
    (hatch,) = [v for v in HC.drop_links(deli) if v["kind"] == "hatch"]
    assert HC.stair_share(deli, hatch) == pytest.approx(1.0)
    assert HC.cause_for(deli, hatch) == HC.STAIR
    assert [s["species"] for s, _e, _c, _z in HC.hole_slots(deli, lambda m: 1)[0]] == [
        "hole_edge", "hole_spoil", "hole_kit"]
    assert layout_lint.hole_cause_findings(deli) == ([], [])
    row = json.load(open(os.path.join(HERE, "specs", "rowhouse_raid.json"), encoding="utf-8"))
    (hatch,) = [v for v in HC.drop_links(row) if v["kind"] == "hatch"]
    assert HC.stair_share(row, hatch) == pytest.approx(0.70)
    (warn,) = layout_lint.hole_cause_findings(row)[1]
    assert "runs past a stair's well" in warn and "70% in the well" in warn
    hatch["cause"] = "hatch"                                         # the link's own cause still wins
    assert HC.cause_for(row, hatch) == "hatch"


def test_the_library_dresses_every_drop_but_foundrys_catwalk():
    """0.235.0's library: 21 drop links in 12 specs. The six delis' hideout floors (concrete) cut through to their
    kitchens; the two walk-ups' bedroom floors broken over their kitchens, on tile; eight hatches, and four holes in a
    stair's well with nothing round them (deli_a01-a03's drop to the stair, rowhouse_raid's hatch); foundry's 5 x 3 m
    catwalk drop onto its south machine floor caused by nothing, named by L28."""
    got = {}
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):        # a level's transients, not the library
            continue
        spec = json.load(open(p, encoding="utf-8"))
        slots, notes = HC.hole_slots(spec, lambda material: 1)
        assert notes == [], (p, notes)
        if slots:
            got[os.path.basename(p)[:-5]] = sorted((s["species"], s["form"], s["stock"]) for s, _e, _c, _z in slots)
    cut = [("hole_edge", "cut_slab", None), ("hole_kit", "cut", None), ("hole_spoil", "cut_slab", "none")]
    deli = cut + [("roof_hatch", "floor", None)]
    broken = [("hole_edge", "broken", None), ("hole_spoil", "broken", "tile")]
    hatch = [("roof_hatch", "floor", None)]
    assert got == {"corner_deli_heist_01": deli, "cr_deli": deli, "deli_a01": cut, "deli_a02": cut,
                   "deli_a03": cut, "night_deli": deli, "apartment_walkup_a01": broken + hatch,
                   "rowhouse_raid": broken, "07_police_station": hatch, "pvp_station_ref": hatch,
                   "warehouse_a02": hatch, "foundry_heist_vertical": hatch}
    spec = json.load(open(os.path.join(HERE, "specs", "foundry_heist_vertical.json"), encoding="utf-8"))
    (warn,) = layout_lint.hole_cause_findings(spec)[1]
    assert "catwalk_south over south_machine" in warn
