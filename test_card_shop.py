"""The card shop: the preset, the room kind, the staff aisle and the caps.

Deli Counter 0.139.0, from the walker's nine photographs
(`docs/SET_DRESSING_REFERENCES.md`, "The walker's trading card shop
references (2026-09-15)"). Every test here fails on 0.138.0, where there is
no `card_shop` preset, no `card_shop` kind and none of the five species.

WHAT IS AND IS NOT ASSERTED HERE. These are Deli Counter's claims: which
rooms are card-shop rooms, what goes in them, how far the staff aisle is
from the wall and where that number comes from, and that the counts stay
inside the triangle arithmetic the release entry records. Whether the
GEOMETRY is right is Zoo's business and Zoo's tests
(`zoo/tests/test_card_shop.py`, 55 of them); what this file checks on that
side is only that every slot this pass emits falls inside the genome its
species declares, which is the one claim a slot can make on its own.
"""
import json
import math
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agent_contract            # noqa: E402
import level_design              # noqa: E402
import material_kind             # noqa: E402
import presets                   # noqa: E402
import prop_species              # noqa: E402

CARD_SPECIES = ("display_case", "pack_wall", "pennant_row", "folding_table",
                "folding_chair")


@pytest.fixture(scope="module")
def shop():
    """One enriched card shop, built the way `new_level.py` builds it."""
    return presets.make("card_shop", enrich=True)


def _room(spec, rid):
    return next(r for r in spec["rooms"] if r["id"] == rid)


def _named(spec, rid):
    tag = level_design._room_tag(_room(spec, rid))
    out = {}
    for stem, seq, v in level_design._room_names(spec, tag):
        out.setdefault(stem, []).append(v)
    return out


# --- the preset ------------------------------------------------------------

def test_the_preset_is_registered_and_carries_its_own_name():
    assert "card_shop" in presets.REGISTRY
    spec = presets.REGISTRY["card_shop"](enrich=False) if False else \
        presets.card_shop()
    # `preset` is what `club_building_id` reads when Level Factory renames
    # the level to `lf_<mission>_<seed>`
    assert spec["preset"] == "card_shop"
    assert level_design._card_shop_building(
        level_design.club_building_id(spec))


def test_floors_is_read_rather_than_accepted_and_ignored():
    """The pawn shop and the club both take `floors` and drop it. This one
    does not: one storey is the strip-mall unit, two is the shop with a
    flat over it."""
    one = presets.card_shop(floors=1)
    two = presets.card_shop(floors=2)
    assert one["n_stories"] == 1 and two["n_stories"] == 2
    assert one["stairs"] == [] and two["stairs"]
    assert not [r for r in one["rooms"] if r["story"] == 1]
    assert [r["id"] for r in two["rooms"] if r["story"] == 1] == [
        "apartment", "upper_storage"]
    # the parapet moves with the roof
    assert one["parapets"][0]["story"] == 1
    assert two["parapets"][0]["story"] == 2


def test_the_stair_pitch_is_inside_what_a_body_walks_up():
    """`CharacterBody3D.floor_max_angle` is 45 deg and nothing in this
    toolchain sets it otherwise; 20 of 38 shipped buildings emit stairs
    above it (CLAUDE.md, "Known contract tensions"). This one does not."""
    spec = presets.card_shop(floors=2)
    st = spec["stairs"][0]
    pitch = math.degrees(math.atan2(spec["story_height"], st["run"]))
    assert pitch < 45.0, pitch


# --- the room kind ---------------------------------------------------------

def test_the_selling_rooms_are_card_shop_rooms_and_the_back_rooms_are_not():
    spec = presets.card_shop()
    b = level_design.club_building_id(spec)
    kinds = {r["id"]: level_design._room_kind(r, b) for r in spec["rooms"]}
    assert kinds["sales_floor"] == "card_shop"
    assert kinds["play_area"] == "card_shop"
    # the stockroom is a stockroom and the flat is a flat: the club's cash
    # office keeps `vault` for the same reason
    assert kinds["stockroom"] == "storage"
    assert kinds["apartment"] == "apartment"
    assert kinds["upper_storage"] == "storage"


def test_the_kind_does_not_leak_into_a_building_that_is_not_a_card_shop():
    """`sales_floor` is a shop floor everywhere else, and must stay one --
    the club's `main_floor` defect (0.131.0) one building along."""
    room = {"id": "sales_floor", "story": 0}
    assert level_design._room_kind(room, "supermarket_a01") == "shop_floor"
    assert level_design._room_kind(room, "lf_card_shop_001_7") == "card_shop"


def test_the_play_area_anchors_on_tables_and_the_selling_floor_on_counters():
    spec = presets.card_shop()
    b = level_design.club_building_id(spec)
    play = level_design._card_shop_anchors(_room(spec, "play_area"), b)
    sell = level_design._card_shop_anchors(_room(spec, "sales_floor"), b)
    assert set(play) == {"folding_table"}
    assert 1 <= len(play) <= level_design._CARD_PLAY_TABLES_MAX
    assert set(sell) == {"display_case"}


def test_a_play_table_s_share_of_floor_is_derived_from_the_pieces():
    """Not a chosen number: the widest table by its depth plus, each side,
    a chair's depth and the body behind it."""
    tw, td = level_design._PIECES["folding_table"]["sizes"][1][0:2]
    _cw, cd, _ch = level_design._PIECES["folding_chair"]["sizes"][0]
    r = agent_contract.contract()["characters"]["player"]["radius_m"]
    assert level_design.card_play_table_floor() == pytest.approx(
        tw * (td + 2.0 * (cd + 2.0 * r)), abs=1e-4)


def test_the_shop_is_furnished_as_a_card_shop(shop):
    sell = _named(shop, "sales_floor")
    play = _named(shop, "play_area")
    assert len(sell["display_case"]) == 2, "the reference's L of counters"
    # one behind each counter, PLUS whatever the wall run draws now that the
    # cap is 4 rather than 2 -- "the reference's one long aisle of it", which
    # 0.139.0's `reserved_by` share had left at exactly nothing
    assert len(sell["pack_wall"]) >= 2, "one behind each counter"
    assert len(sell["pack_wall"]) > 2, "and a run along a free wall"
    assert len(sell["wall_tv"]) == 2, "the CRT on a shelf behind"
    assert len(sell["pack_wall_island"]) >= 2, "product in the open floor"
    assert sell["pennant_row"], "a row of pennants along the top of the wall"
    assert play["folding_table"] and play["folding_chair"]
    # the stockroom is dressed as storage, which is what it is
    assert "shelf_run" in _named(shop, "stockroom")


# --- the staff aisle -------------------------------------------------------

def test_the_staff_aisle_is_the_contract_s_and_not_a_number():
    """Derived, and derived the same way for both counters that have one:
    a corridor a body walks the length of AND a doorway at its end."""
    want = max(agent_contract.min_corridor_width(),
               agent_contract.min_door_width())
    assert level_design.staff_aisle_width() == pytest.approx(want)
    # the club's spelling is the same function, not a second body
    assert level_design.bar_aisle_width is level_design.staff_aisle_width


def test_every_counter_gets_its_aisle_and_the_gate_can_see_it(shop):
    report = [r for r in level_design.card_shop_counters(shop)
              if r.get("counter")]
    assert report, "no showcase counter was found to back"
    assert all(r["built"] for r in report), report
    aisle = level_design.staff_aisle_width()
    marks = {m["id"]: m for m in shop["markers"]
             if m.get("meta", {}).get("role") == "shopkeeper"}
    assert len(marks) == len(report)
    for m in marks.values():
        assert m["type"] == "patrol_point"
        assert m["meta"]["aisle_m"] == pytest.approx(aisle)
        assert m["room"] == "sales_floor"


def test_the_counter_stands_its_aisle_off_the_wall_before_anything_moves():
    """`piece_back_off`: the counter is SLOTTED at its final depth, so the
    staff band is protected by its own clearance for every piece that comes
    after it. Placed flush and shoved forward later, both counters of
    `card_shop_a01` were refused -- one by a shelter piece, one by a play
    chair."""
    p = level_design._PIECES["display_case"]
    assert p["backed_by"] == "pack_wall"
    assert level_design.piece_back_off(p) == pytest.approx(
        level_design.PACK_WALL_DEPTH + level_design.staff_aisle_width()
        - level_design._WALL_PIECE_AIR)
    assert level_design.piece_back_off(
        level_design._PIECES["pack_wall"]) == 0.0


def test_the_counter_does_not_take_the_shop_window(shop):
    """`off_glass`: the pack wall that follows the counter would board up
    the storefront from the inside."""
    assert level_design._PIECES["display_case"]["off_glass"]
    glazed = level_design._glazed_walls(shop, 0)
    assert glazed == {"S"}, glazed
    hy = shop["footprint_y"] / 2.0
    for v in _named(shop, "sales_floor").get("pack_wall", []):
        assert v["y"] - v["size_y"] / 2.0 > -hy + 1.0, v["name"]


def test_the_play_area_answers_the_nav_gate_for_itself(shop):
    """A room the gate is given no point in is a room it says nothing
    about, and a play area is furniture in the middle of a floor."""
    pts = [m for m in shop["markers"]
           if m.get("meta", {}).get("role") == "playfloor"]
    assert len(pts) == 1, pts
    x0, y0, x1, y1 = _room(shop, "play_area")["bounds"]
    assert x0 < pts[0]["x"] < x1 and y0 < pts[0]["y"] < y1


def test_the_marker_roles_are_declared_where_the_migration_reads_them():
    import migrate_furnish_recipes
    for role in level_design.STAFF_MARKER_ROLES:
        assert migrate_furnish_recipes._GENERATED_MARKER.match(
            "%s_r0123abcd_1" % role), role


def test_a_refurnished_card_shop_is_a_fixed_point():
    """Strip the furnishing and run it again: the same JSON, marker ORDER
    included. The first version of this moved every staff patrol point to
    the end of the list -- and so did a freshly generated strip_club, which
    the shipped `strip_club_a01..a03` hid because 0.137.0's migration had
    already appended theirs."""
    import copy
    import migrate_furnish_recipes
    for preset in ("card_shop", "strip_club"):
        spec = presets.make(preset, enrich=True)
        again = copy.deepcopy(spec)
        migrate_furnish_recipes.migrate(again)
        assert json.dumps(again, sort_keys=True) == \
            json.dumps(spec, sort_keys=True), preset


# --- what a hung piece answers to ------------------------------------------

def test_the_over_opening_exemption_reaches_no_older_piece():
    """`hangs_over_openings` loosens three of `_seed_clear`'s rules for a
    piece hung above every doorway and window. It must reach nothing that
    shipped before 0.139.0, at any storey height the library has."""
    spec = {"story_height": 3.0, "floor_thick": 0.3,
            "ext_walls": [{"wall": "S", "story": 0,
                           "openings": [{"kind": "door", "pos": 0.0}]}],
            "partitions": []}
    assert level_design.opening_head(spec, 0) == pytest.approx(2.2)
    for name in ("neon_sign", "wall_tv", "dartboard"):
        p = level_design._PIECES[name]
        for _w, _d, h in p["sizes"]:
            for sh in (3.0, 3.4, 3.6, 4.2, 5.0, 6.5):
                s = dict(spec, story_height=sh)
                assert not level_design._over_openings(s, 0, p, h), (name, sh)
    # ...and reaches the pennant row at every storey the library has
    p = level_design._PIECES["pennant_row"]
    for _w, _d, h in p["sizes"]:
        for sh in (3.0, 3.4, 3.6, 4.2, 5.0, 6.5):
            s = dict(spec, story_height=sh)
            assert level_design._over_openings(s, 0, p, h), (h, sh)


def test_a_pennant_row_hangs_from_the_ceiling_and_not_from_a_number(shop):
    """`under`, not `lift`: a fixed height would be right at one storey and
    inside the slab at the next."""
    p = level_design._PIECES["pennant_row"]
    assert p["lift"] is None and p["under"] == level_design._CEILING_AIR
    for sh in (3.0, 3.4, 4.2):
        s = {"story_height": sh, "floor_thick": 0.25}
        h = p["sizes"][0][2]
        top = level_design._piece_lift(s, p, h) + h / 2.0
        assert top == pytest.approx(level_design._clear_height(s)
                                    - level_design._CEILING_AIR)
    for v in _named(shop, "sales_floor")["pennant_row"]:
        assert v["z"] - v["size_z"] / 2.0 > 2.0, "over a body's head"
        assert v["collision"] == "none"


# --- the caps, which are the triangle budget -------------------------------

def test_the_variant_count_is_the_species_own_and_asked_once():
    """`variants=True` means four; a species with its own count says so.
    The folding pieces are 2, and a 4 written there would have asked Zoo to
    honour a variant it refuses -- which drops the `cards` stock with it."""
    assert level_design.variant_count(
        level_design._PIECES["folding_table"]) == 2
    assert level_design.variant_count(
        level_design._PIECES["folding_chair"]) == 2
    assert level_design.variant_count(
        level_design._PIECES["display_case"]) == 4
    assert level_design.variant_count(
        level_design._PIECES["neon_sign"]) == 24
    assert level_design.variant_count(level_design._PIECES["desk"]) == 4
    assert level_design.variant_count(level_design._PIECES["shelf_run"]) == 0


def test_a_later_pass_keeps_its_share_of_a_piece_s_cap(shop):
    """`reserved_by`: `card_shop_counters` stands one pack wall per
    showcase counter AFTER the wall run has spent the cap, so without it a
    two-counter selling floor draws `most` plus two. The mechanism is what
    is asserted here; `most` itself is the budget test's."""
    p = level_design._PIECES["pack_wall"]
    assert p["reserved_by"] == "display_case"
    sell = _named(shop, "sales_floor")
    assert len(sell["pack_wall"]) <= p["most"]
    assert len(sell["display_case"]) >= 1


def test_no_card_shop_room_carries_more_than_its_caps(shop):
    caps = {"display_case": 2, "pack_wall": 4, "pennant_row": 4,
            "pack_wall_island": 2 * 2,
            "folding_table": level_design._CARD_PLAY_TABLES_MAX}
    b = level_design.club_building_id(shop)
    for room in shop["rooms"]:
        if not level_design.is_card_shop_room(room, b):
            continue
        got = _named(shop, room["id"])
        for stem, cap in caps.items():
            assert len(got.get(stem, [])) <= cap, (room["id"], stem)


# --- density: the height and the floor (0.140.0) ---------------------------
#
# The walker walked cold run 9061's `card_shop_a01` and photographed the
# sales floor: "the card shop should feel saturated with posters, ads,
# playmats, content, fantasy, ect ect." `docs/SET_DRESSING_REFERENCES.md`
# splits that into five properties; these are the two Deli Counter owns --
# product goes to the ceiling, and the middle of the floor is occupied.
#
# Every test below FAILS on 0.139.0: the pack walls were 2.2 m in a room
# with 3.10 m of clear height, the `floor` run was empty and there was no
# `island` placement at all.

#: WHAT ONE MODULE COSTS AT THE WORST CORNER OF ITS PALETTE, in triangles.
#:
#: MEASURED 2026-09-16 by planning each palette size through Zoo 0.95.0's
#: own planners at every variant and keeping the largest --
#: `pack_wall_forms.plan`, `display_case_forms.plan`, `pennant_forms.plan`,
#: `folding_forms.plan_table` / `plan_chair` -- and read off `facts["tris"]`,
#: which for four of the five species IS the built number (0.139.0's release
#: entry checks it against the kit's `meta.json`).
#:
#: Pinned here rather than computed, so this test says the same thing on a
#: machine with no Zoo checkout. `test_the_measured_module_costs_are_still
#: _zoo_s` is what stops it drifting from the planner it was read off.
_WORST_TRIS = {
    "display_case": 1148,        # 3.6 x 0.6 x 1.05
    "display_case_end": 760,     # 1.25 x 0.6 x 1.0
    "pack_wall": 2112,           # 3.6 wide, 3 bays -- HEIGHT DOES NOT MOVE IT
    "pack_wall_island": 1416,    # 2.4 wide, 2 bays, and an island is TWO
    "pennant_row": 892,          # its budget, whatever its length
    "wall_tv": 404,
    "folding_table": 384,        # with the `cards` stock
    "folding_chair": 192,
    # THE FLAT ART (Zoo 0.98.0), measured the same way at THIS file's
    # palette corners. Every one of the four reproduces the per-species
    # figure Zoo's own 0.98.0 entry publishes, which is why the table can
    # be believed: poster 78 (framed), banner 62, hanger 52, sign 88.
    "poster": 78,
    "hanging_banner": 62,
    "ceiling_hanger": 52,
    "aisle_sign": 88,
}


def test_the_room_budget_is_zoo_s_only_real_one_and_the_caps_fit_under_it():
    """THE FIGURE 0.139.0 CAPPED AGAINST WAS NOT A BUDGET, and this is the
    test that says so rather than the release note.

    10,664 is Zoo 0.95.0's MEASUREMENT of one card-shop room at its worst
    genome corners, published under the heading "THE ROOM-LEVEL NUMBER,
    because a species budget is not a room" and followed immediately by
    "For scale, one `cubicle_bank` is budgeted 24,000". 0.139.0 read the
    measurement as a ceiling and capped the shipped room BELOW the
    reference furnishing it was citing -- two pack walls where that
    reference has four, two pennant rows where it has four.

    The budget is one `cubicle_bank`, which is the only room-scale figure
    in this toolchain that is a budget at all, and the caps are set so the
    worst case the palette can produce lands under it. A cap that is not
    the thing holding the number is a comment (Zoo's own words, one layer
    down), so this multiplies them out.
    """
    P = level_design._PIECES

    def cap(key):
        """A piece's ceiling in ONE room: its `most_big` allowance where it
        has one, since a selling floor is 220 m2 and reaches every one."""
        p = P[key]
        return p["most_big"][1] if p["most_big"] else p["most"]

    solid = (
        2 * _WORST_TRIS["display_case"] +         # both counters
        2 * _WORST_TRIS["display_case_end"] +     # both returns
        cap("pack_wall") * _WORST_TRIS["pack_wall"] +
        cap("pennant_row") * _WORST_TRIS["pennant_row"] +
        2 * _WORST_TRIS["wall_tv"] +              # one CRT a counter
        cap("pack_wall_island") * 2 * _WORST_TRIS["pack_wall_island"]
    )
    # THE FLAT ART IS THE CHEAP HALF AND THE ARITHMETIC SAYS SO (0.141.0).
    # Zoo 0.98.0: "geometry is not where flat art costs anything and the
    # caps on these four genomes are not what will hold the room back."
    art = sum(cap(k) * _WORST_TRIS[k] for k in
              ("poster", "hanging_banner", "ceiling_hanger", "aisle_sign"))
    assert solid == 22304, solid
    assert art == 1064, art
    worst = solid + art
    assert worst == 23368, worst
    assert worst <= level_design._CARD_SHOP_ROOM_TRIS
    # ...and the cap is load-bearing: one more island is over it, which is
    # why `most` is 2 and not 3.
    assert worst + 2 * _WORST_TRIS["pack_wall_island"] > \
        level_design._CARD_SHOP_ROOM_TRIS
    # the art is 4.6 % of the room and would not be what broke it
    assert art < solid * 0.06


def test_the_measured_module_costs_are_still_zoo_s():
    """`_WORST_TRIS` is a reading of Zoo's planners, so it can go stale
    silently. Where Zoo is reachable, it is re-read."""
    from test_furnish import ZOO
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    import importlib
    PW = importlib.import_module("zoo_keeper.core.pack_wall_forms")
    DCF = importlib.import_module("zoo_keeper.core.display_case_forms")
    PN = importlib.import_module("zoo_keeper.core.pennant_forms")

    def worst(plan, sizes):
        return max(plan(w, d, h, variant=v)["facts"]["tris"]
                   for (w, d, h) in sizes for v in range(4))

    spec = presets.card_shop()
    clear = level_design._clear_height(spec)
    tall = level_design.to_ceiling_height(
        spec, level_design._PIECES["pack_wall"], clear)
    for key, plan in (("pack_wall", PW.plan), ("pack_wall_island", PW.plan)):
        sizes = [(w, d, tall) for w, d, _h in
                 level_design._PIECES[key]["sizes"]]
        assert worst(plan, sizes) == _WORST_TRIS[key], key
    assert worst(DCF.plan, level_design._PIECES["display_case"]["sizes"]) == \
        _WORST_TRIS["display_case"]
    assert worst(DCF.plan,
                 level_design._PIECES["display_case_end"]["sizes"]) == \
        _WORST_TRIS["display_case_end"]
    assert worst(PN.plan, level_design._PIECES["pennant_row"]["sizes"]) == \
        _WORST_TRIS["pennant_row"]


def test_the_pack_wall_ceiling_is_the_genome_s_and_not_a_number():
    """`PACK_WALL_CEILING` is copied out of Zoo's genome. A copy drifts."""
    from test_furnish import ZOO
    path = os.path.join(ZOO, "zoo_keeper", "genome", "species",
                        "pack_wall.json")
    if not os.path.isfile(path):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    with open(path, encoding="utf-8") as fh:
        genome = json.load(fh)
    assert level_design.PACK_WALL_CEILING == \
        genome["dimensions"]["height"]["max"]


def test_product_goes_to_the_ceiling_and_stops_under_the_pennants(shop):
    """REFERENCE PROPERTY 1. "A wall that stops at 2.2 m in a 3.4 m room
    reads as a partition; a wall filled to the ceiling reads as a shop."

    The three numbers are derived and each is asked of the room it is in:
    the clear height, the band the hung fixtures own, and the product
    ceiling under it. At the card shop's 3.4 m storey that is 3.10 / 2.75 /
    2.70, and 0.139.0's pack walls were 2.2 -- 0.55 m short of what the
    room allows and a metre short of its ceiling.
    """
    clear = level_design._clear_height(shop)
    band = level_design.hung_band_bottom(shop)
    top = level_design.to_ceiling_height(
        shop, level_design._PIECES["pack_wall"], clear)
    assert band < clear                       # something hangs
    assert top == round(band - level_design._CEILING_AIR, 4)
    assert top > 2.2                          # the number this replaces
    assert top <= level_design.PACK_WALL_CEILING
    walls = [v for v in shop["volumes"] if v["name"].startswith("pack_wall")]
    assert walls
    for v in walls:
        # every one of them reaches the product ceiling, or the counter's
        # own derivation of it, and NONE of them is still at 2.2
        assert v["size_z"] > 2.2, v["name"]
        assert v["z"] + v["size_z"] / 2.0 <= clear + 1e-9, v["name"]
    # ...and nothing standing on the floor reaches into the hung band
    for v in walls:
        assert v["z"] + v["size_z"] / 2.0 <= band, v["name"]


def test_one_pack_wall_height_a_room_and_not_two_spellings_of_it(shop):
    """The counter pass and the wall run each used to name their own
    height -- `PACK_WALL_H` here, the palette's sizes there -- and they
    agreed by coincidence at 2.2. Raising one moved the run's gondolas to
    2.70 and left the two behind the counters, which are the most visible
    in the shop, at 2.2. One declaration, two readers."""
    assert not hasattr(level_design, "PACK_WALL_H")
    counter_h = level_design.counter_pack_wall_height(shop)
    run_h = level_design.to_ceiling_height(
        shop, level_design._PIECES["pack_wall"],
        level_design._clear_height(shop))
    # the counter's is the run's less the CRT's own band, and no more
    crt_h = level_design._PIECES["wall_tv"]["sizes"][0][2]
    assert counter_h <= run_h
    assert run_h - counter_h <= crt_h + level_design._CRT_OVER_PACK + 1e-9


def test_the_crt_still_has_its_shelf_over_the_taller_gondola(shop):
    """What filling the height nearly cost, and the term that keeps it. At
    the full 2.70 product ceiling a 0.50 m CRT has nowhere to hang and
    `card_shop_counters` reports `crt: false` -- the reference's "small CRT
    on a shelf behind" quietly gone. `counter_pack_wall_height` takes the
    CRT's band off first."""
    tvs = [v for v in shop["volumes"] if v["name"].startswith("wall_tv")]
    cases = [v for v in shop["volumes"]
             if v["name"].startswith("display_case_r")]
    # ONE CRT A COUNTER, which is the claim -- not one per pack wall, since
    # the wall run stands its own now and those carry no CRT
    assert tvs and len(tvs) == len(cases)
    clear = level_design._clear_height(shop)
    for v in tvs:
        assert v["z"] + v["size_z"] / 2.0 <= clear + 1e-9, v["name"]
        # and each one hangs over a gondola rather than in mid-air
        under = [w for w in shop["volumes"]
                 if w["name"].startswith("pack_wall_")
                 and abs(w["x"] - v["x"]) < 0.3 and abs(w["y"] - v["y"]) < 0.3]
        assert under, v["name"]
        top = max(w["z"] + w["size_z"] / 2.0 for w in under)
        assert v["z"] - v["size_z"] / 2.0 >= top - 1e-9, v["name"]


def test_the_middle_of_the_selling_floor_is_occupied(shop):
    """REFERENCE PROPERTY 2. "The current recipe treats the floor as
    circulation and puts everything against a wall. That is what makes the
    frame read as a hall: there is nothing between the camera and the far
    wall."

    An island is a piece whose every side is open floor. 0.139.0's selling
    floor had none: `floor` was `()` and every `where` in the recipe was
    `wall`.
    """
    room = _room(shop, "sales_floor")
    x0, y0, x1, y1 = room["bounds"]
    islands = [v for v in shop["volumes"]
               if v["name"].startswith("pack_wall_island")]
    assert islands, "nothing stands in the open floor"
    aisle = level_design.island_aisle_width()
    for v in islands:
        for lo, hi, c, s in ((x0, x1, v["x"], v["size_x"]),
                             (y0, y1, v["y"], v["size_y"])):
            assert c - s / 2.0 - lo >= aisle - 1e-6, (v["name"], "lo")
            assert hi - (c + s / 2.0) >= aisle - 1e-6, (v["name"], "hi")


def test_an_island_is_two_faces_and_never_one_blank_back(shop):
    """A `pack_wall`'s back panel owns +Y and carries no product, so a
    single one mid-floor is a blank slatwall sheet seen from half the room.
    `twin` writes the other face; they share a spine and face opposite
    ways."""
    assert level_design._PIECES["pack_wall_island"]["twin"]
    islands = [v for v in shop["volumes"]
               if v["name"].startswith("pack_wall_island")]
    assert islands and len(islands) % 2 == 0
    by_pos = {}
    for v in islands:
        by_pos.setdefault((round(v["size_x"], 2), round(v["size_y"], 2)),
                          []).append(v)
    for group in by_pos.values():
        assert len(group) % 2 == 0, [v["name"] for v in group]
    # each unit's back is against its partner's, and the two look opposite
    # ways: their rotations differ by 180
    rots = sorted({round(float(v.get("rot_z", 0.0)) % 360.0) for v in islands})
    assert len(rots) == 2 and abs(rots[1] - rots[0]) == 180, rots
    # ...AND THE TWO BACKS ARE NOT COPLANAR. Two slatwall sheets meeting on
    # exactly one plane is the shape Zoo measured as 3.09 m2 of flicker on
    # cold run 9052's lobby; `island_depth` puts `_WALL_PIECE_AIR` between
    # them, and the gap is checked here rather than trusted to the writer.
    for v in islands:
        near = [o for o in islands
                if o is not v
                and abs(o["size_x"] - v["size_x"]) < 1e-6
                and abs(o["size_y"] - v["size_y"]) < 1e-6
                and math.hypot(o["x"] - v["x"], o["y"] - v["y"]) < 2.0]
        assert near, v["name"]
        gap = min(math.hypot(o["x"] - v["x"], o["y"] - v["y"]) for o in near)
        depth = min(v["size_x"], v["size_y"])
        assert gap > depth + 1e-9, (v["name"], gap, depth)
        assert gap <= depth + level_design._WALL_PIECE_AIR + 1e-6, \
            (v["name"], gap, depth)


def test_an_island_keeps_the_contract_s_aisle_from_everything(shop):
    """THE CONTRACT'S NUMBER, NOT THIS BRIEF'S. `_seed_clear` keeps a piece
    0.9 m off another volume's edge, which is under
    `clearances.min_corridor_width_m` (1.10) -- right for a chair beside a
    desk and wrong for a run a body walks down. An island asks
    `island_aisle_width`, which is `staff_aisle_width` (1.25) because an
    aisle is a corridor ENTERED AT ITS END and so a doorway too."""
    aisle = level_design.island_aisle_width()
    assert aisle == max(agent_contract.min_corridor_width(),
                        agent_contract.min_door_width())
    assert aisle >= agent_contract.min_corridor_width()
    islands = [v for v in shop["volumes"]
               if v["name"].startswith("pack_wall_island")]
    assert islands
    partners = {v["name"] for v in islands}
    for v in islands:
        rect = level_design._rect_of(v)
        for o in shop["volumes"]:
            if o["name"] in partners or o.get("collision") == "none":
                continue
            if abs(float(o.get("z", 0.0))) > level_design._story_height(shop):
                continue
            r = level_design._rect_of(o)
            gap_x = max(rect[0] - r[2], r[0] - rect[2])
            gap_y = max(rect[1] - r[3], r[1] - rect[3])
            assert max(gap_x, gap_y) >= aisle - 1e-6, (v["name"], o["name"])


def test_the_play_area_gets_no_islands(shop):
    """Its middle is already its tables; an island between two of them is a
    wall across a tournament. The two rooms share one `_RECIPES` entry, so
    the floor run is per-room the way the anchors are."""
    b = level_design.club_building_id(shop)
    play = _room(shop, "play_area")
    assert level_design._card_shop_floor(play, b) == ()
    assert level_design._card_shop_floor(_room(shop, "sales_floor"), b)
    tag = level_design._room_tag(play)
    for stem, _seq, _v in level_design._room_names(shop, tag):
        assert stem != "pack_wall_island"


def test_a_derived_height_is_never_rounded_up():
    """`round(x, 4)` moves a value UP by as much as 5e-5, and every caller
    asks a LIMIT of the result -- `_host` refuses `h > clear_h`, the CRT
    pass refuses one with no room above. One quantity, two spellings, a
    threshold between them: the `_wall_span` shape. `_floor4` is what stops
    it, so it is asked directly rather than only through its callers."""
    assert level_design._floor4(2.69999999) <= 2.69999999
    assert level_design._floor4(1.00005) <= 1.00005
    for storey in (3.0, 3.4, 3.6, 4.2, 5.0, 6.5):
        spec = presets.card_shop()
        spec["story_height"] = storey
        clear = level_design._clear_height(spec)
        for key in ("pack_wall", "pack_wall_island"):
            h = level_design.to_ceiling_height(
                spec, level_design._PIECES[key], clear)
            assert h <= clear, (storey, key)
            assert h <= level_design.PACK_WALL_CEILING, (storey, key)
        pw = level_design.counter_pack_wall_height(spec)
        crt_h = level_design._PIECES["wall_tv"]["sizes"][0][2]
        assert pw + level_design._CRT_OVER_PACK + crt_h <= clear + 1e-9, storey


# --- the flat art (0.141.0, Zoo 0.98.0) -----------------------------------
#
# Properties 3 and 4 of the references: things hang, and the wall above the
# shelving is where the posters live. Zoo ships four species whose whole
# cost is texture; Deli Counter's side is where they go and what a body can
# walk under.

_ART = ("poster", "hanging_banner", "ceiling_hanger", "aisle_sign")


def test_the_room_carries_every_flat_art_species(shop):
    """All four, not three. A species wired into the recipe and placed
    nowhere is the `pennant_row` defect of 0.139.0 -- an entry that could
    not fire -- and the only way to catch it is to count."""
    b = level_design.club_building_id(shop)
    got = {}
    for room in shop["rooms"]:
        if not level_design.is_card_shop_room(room, b):
            continue
        for stem, _seq, v in level_design._room_names(
                shop, level_design._room_tag(room)):
            if stem in _ART:
                got.setdefault(stem, []).append(v)
    assert set(got) == set(_ART), sorted(got)
    for stem in _ART:
        assert prop_species.species_for_name(got[stem][0]["name"]) == stem


def test_the_wall_art_hangs_under_the_pennant_strip(shop):
    """`_UNDER_PENNANTS`, derived from the strip's own height rather than
    written down. Both references put the art and the strip in one band and
    the strip is there first, so the art's top is the strip's bottom less
    `_CEILING_AIR`."""
    clear = level_design._clear_height(shop)
    band = level_design.hung_band_bottom(shop)
    top = clear - level_design._UNDER_PENNANTS
    assert abs(top - (band - level_design._CEILING_AIR)) < 1e-9
    for v in shop["volumes"]:
        if v["name"].split("_r")[0] not in ("poster", "hanging_banner"):
            continue
        assert abs((v["z"] + v["size_z"] / 2.0) - top) < 1e-6, v["name"]
        # ...and it is clear of the strip rather than through it
        assert v["z"] + v["size_z"] / 2.0 <= band - 1e-9, v["name"]


def test_a_poster_never_shortens_a_gondola(shop):
    """THE TWO HALVES OF THE DENSITY WORK WANT THE SAME BAND, and this is
    the rule that settles it.

    `hung_band_bottom` is what a floor-standing wall unit must stop under,
    and it is scoped by `wall_band` -- a flag only `pennant_row` sets.
    Measured while wiring this: unscoped it read every hung piece and the
    product ceiling fell 2.70 -> 2.40 on a `ceiling_hanger` over the middle
    of the floor; scoped to `where == "wall"` it fell to 1.45 on a poster.
    A poster does not shorten anything -- it goes where the product is not,
    which `_seed_clear` decides at placement.
    """
    banders = {n for n, p in level_design._PIECES.items() if p["wall_band"]}
    assert banders == {"pennant_row"}, banders
    assert level_design.to_ceiling_height(
        shop, level_design._PIECES["pack_wall"],
        level_design._clear_height(shop)) == 2.7


def test_a_hung_piece_is_cleared_of_what_shares_its_height_and_no_more(shop):
    """`below`, the other half of `above`, FOUND BY ATTRIBUTING A ZERO.

    `hanging_banner` placed nowhere at all: a probe over all 31 candidates
    named the blocker in each and `pennant_row` was in 22 of them -- the
    strip the reference hangs the banner under. A pennant is 2.75-3.05 and
    a banner 2.00-2.70 and they share no height.
    """
    import inspect
    assert "below" in inspect.signature(level_design._seed_clear).parameters
    room = _room(shop, "sales_floor")
    # a candidate under the strip is clear of the strip...
    strip = next(v for v in shop["volumes"]
                 if v["name"].startswith("pennant_row_"))
    x, y = strip["x"], strip["y"]
    assert level_design._seed_clear(
        shop, room, x, y, [], half=0.9,
        above=2.0, below=2.7, over_openings=False) is not None
    # ...and the same point WITHOUT the top term is refused by it
    assert not level_design._seed_clear(
        shop, room, x, y, [], half=0.9, above=2.0, over_openings=False)


def test_nothing_hangs_where_a_body_would_walk_into_it(shop):
    """THE HEADROOM IS DELI COUNTER'S, NOT THE GENOME'S. Zoo caps the two
    hanging species at 0.60 m and derives it from this contract assuming a
    0.3 m slab -- and says in its own genome note that it cannot see the
    slab. So the cap is a guess and this is the measurement."""
    head = agent_contract.min_headroom()
    for v in shop["volumes"]:
        if v["name"].split("_r")[0] not in ("ceiling_hanger", "aisle_sign"):
            continue
        assert v["z"] - v["size_z"] / 2.0 >= head - 1e-9, v["name"]
    # and the gate BITES where the genome's assumption fails: a thicker slab
    # at the shortest storey leaves less than the genome's 0.60
    thick = dict(shop, story_height=3.0, floor_thick=0.5)
    refused = [h for (_w, _d, h)
               in level_design._PIECES["ceiling_hanger"]["sizes"]
               if not level_design.hung_headroom_ok(
                   thick, level_design._PIECES["ceiling_hanger"], h)]
    assert refused, "the headroom gate cannot fail, so it proves nothing"


def test_a_hung_fixture_is_not_assumed_to_be_on_a_wall(shop):
    """`_place_fixture` used `_wall_slots` whatever the piece said, so a
    hanger over the middle of the floor could not exist. It asks the piece
    now, as `_host` does."""
    floor_art = {n for n in _ART if level_design._PIECES[n]["where"] == "floor"}
    assert floor_art == {"ceiling_hanger", "aisle_sign"}, floor_art
    room = _room(shop, "sales_floor")
    x0, y0, x1, y1 = room["bounds"]
    for v in shop["volumes"]:
        if v["name"].split("_r")[0] not in floor_art:
            continue
        if not (x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1):
            continue
        edge = min(v["x"] - x0, x1 - v["x"], v["y"] - y0, y1 - v["y"])
        assert edge >= 1.0 - 1e-6, (v["name"], edge)


def test_every_flat_art_material_is_one_its_species_offers():
    """A MATERIAL A SPECIES DOES NOT OFFER IS A SILENT SUBSTITUTION, which
    is the defect `_PROP_MATERIALS`' own card-shop note warns about one
    release earlier: "the pennants would have come out as timber and nothing
    would have said so".

    `_PROP_MATERIAL_DEFAULT` is `wood` and `hanging_banner`'s genome offers
    cloth, canvas, plastic and paper -- no wood. Left to the default it
    asked for timber, Zoo fell back, and no gate anywhere would have
    noticed. Checked against the genomes rather than against a copy of them.
    """
    from test_furnish import ZOO
    gdir = os.path.join(ZOO, "zoo_keeper", "genome", "species")
    if not os.path.isdir(gdir):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    bad = []
    for key in _ART:
        path = os.path.join(gdir, key + ".json")
        with open(path, encoding="utf-8") as fh:
            mats = json.load(fh)["materials"]
        want = level_design._prop_material({}, key)
        if want not in mats["options"]:
            bad.append((key, want, mats["options"]))
    assert not bad, bad


def test_the_play_tables_still_ask_for_the_printed_mat(shop):
    """Zoo 0.98.0 gave `_surface_stock` a textured path, so the `cards`
    flavour paints a playmat instead of colouring one. Deli Counter's side
    of that is one word it was already writing -- asserted so that dropping
    it is a failure rather than a quiet loss of the single most visible gap
    the references named."""
    assert level_design._PIECES["folding_table"]["stock"] == "cards"
    tables = [v for v in shop["volumes"]
              if v["name"].startswith("folding_table_")]
    assert tables
    for v in tables:
        assert v.get("stock") == "cards", v["name"]


def test_every_card_shop_slot_is_a_size_its_species_builds(shop):
    """A slot outside its genome is built as the fallback box, and a box is
    not a showcase counter. The ranges are `test_furnish._ZOO_RANGES`,
    which `test_the_ranges_are_zoo_s` pins to the genomes themselves."""
    from test_furnish import _ZOO_RANGES
    for v in shop["volumes"]:
        sp = prop_species.species_for_name(v["name"])
        if sp not in CARD_SPECIES:
            continue
        w, d = max(v["size_x"], v["size_y"]), min(v["size_x"], v["size_y"])
        for label, val, (lo, hi) in zip(("width", "depth", "height"),
                                        (w, d, v["size_z"]),
                                        _ZOO_RANGES[sp]):
            assert lo - 1e-9 <= val <= hi + 1e-9, (v["name"], sp, label, val)


# --- the surfaces ----------------------------------------------------------

def test_the_shop_wears_the_theme_s_own_kinds(shop):
    """The play area is `carpet` and NOT `carpet_tournament`: a pack is
    `<kind>_<theme>`, so the tournament loop is what the `card_shop` theme
    resolves `carpet` to. Inventing a kind would have left every other
    theme's card shop grey."""
    assert _room(shop, "play_area")["floor_material"] == "carpet"
    assert _room(shop, "sales_floor")["floor_material"] == "tile"
    assert "carpet_tournament" not in material_kind.SKIN_KINDS
    panelled = [p for p in shop["partitions"]
                if p.get("material") == "wood_panel"]
    assert panelled, "the lower walls are wood panelling"


def test_every_material_this_pass_writes_resolves_to_a_kind(shop):
    """An unmapped id is a flat grey surface that looks like a styling
    choice -- and a kind absent from the vocabulary is the defect Zoo
    0.95.0's second half is about."""
    ids = {m["id"] for m in shop["materials"]}
    ids |= {v.get("material") for v in shop["volumes"] if v.get("material")}
    ids |= {r.get("floor_material") for r in shop["rooms"]
            if r.get("floor_material")}
    ids |= {p.get("material") for p in shop["partitions"] if p.get("material")}
    assert not material_kind.unmapped(ids)
    for mid in ids:
        assert material_kind.kind_for(mid) in material_kind.SKIN_KINDS, mid


def test_the_two_new_kinds_are_in_the_vocabulary():
    assert "wood_panel" in material_kind.SKIN_KINDS
    assert "slatwall" in material_kind.SKIN_KINDS
    assert material_kind.kind_for("wood_panel") == "wood_panel"
    assert material_kind.kind_for("slatwall") == "slatwall"


def test_the_case_and_the_pack_wall_ask_for_a_material_that_changes_the_build(shop):
    """Zoo tags a stem `_m<kind>` only when the kind is not the species'
    own. `wood_panel` and `slatwall` are not; `cloth` and `plastic` are,
    and they are written for exactly that reason."""
    want = {"display_case": "wood_panel", "display_case_end": "wood_panel",
            "pack_wall": "slatwall", "pennant_row": "cloth",
            "folding_table": "plastic", "folding_chair": "plastic"}
    seen = set()
    for room in shop["rooms"]:
        tag = level_design._room_tag(room)
        for stem, _seq, v in level_design._room_names(shop, tag):
            if stem not in want:
                continue
            assert v["material"] == want[stem], v["name"]
            seen.add(stem)
    assert {"display_case", "pack_wall", "pennant_row",
            "folding_table", "folding_chair"} <= seen, seen


# --- routing ---------------------------------------------------------------

def test_every_card_shop_name_routes_to_its_species():
    for stem in CARD_SPECIES:
        assert prop_species.species_for_name(stem + "_r0123abcd_1") == stem
    # the return case is a display case, not a counter
    assert prop_species.species_for_name(
        "display_case_end_r0123abcd_1") == "display_case"
    # and a supermarket gondola is NOT a pack wall: its 1.0-1.2 m depth is
    # outside the genome's 0.35-0.60 and every match would fall back to the
    # box (see the note in `prop_species`)
    assert prop_species.species_for_name("gondola_aisle_3") != "pack_wall"


def test_no_brand_string_lives_in_deli_counter():
    """Every name a card shop paints comes from `zoo/core/card_brands.py`,
    which is invented and has its own denylist test. Deli Counter names
    species and sizes and nothing a player can read."""
    for path in ("level_design.py", "presets.py", "prop_species.py"):
        text = open(os.path.join(HERE, path), encoding="utf-8").read().lower()
        # UNAMBIGUOUS MARKS ONLY. The first draft of this list carried
        # "upper deck" and fired on a parking garage's "upper decks: open
        # bays", which is the defect Zoo's own denylist note warns about --
        # a guard that matches ordinary English is a guard that will be
        # deleted the first time it is wrong. Zoo holds the real list, in
        # the file that does the painting.
        for mark in ("pokemon", "yu-gi-oh", "yugioh", "topps", "fleer",
                     "donruss", "wizards of the coast"):
            assert mark not in text, (path, mark)


# --- the library spec ------------------------------------------------------

def test_the_library_carries_a_card_shop_and_it_validates():
    path = os.path.join(HERE, "specs", "card_shop_a01.json")
    assert os.path.isfile(path), "specs/card_shop_a01.json"
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    assert d["preset"] == "card_shop"
    rc = subprocess.run([sys.executable, "validate.py", path], cwd=HERE,
                        capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout + rc.stderr
