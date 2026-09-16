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
    assert len(sell["pack_wall"]) == 2, "one behind each counter"
    assert len(sell["wall_tv"]) == 2, "the CRT on a shelf behind"
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
    showcase counter AFTER the wall run has spent the cap, so a two-counter
    selling floor drew four. At the palette's widest that is 8,448
    triangles of pack wall alone."""
    p = level_design._PIECES["pack_wall"]
    assert p["most"] == 2 and p["reserved_by"] == "display_case"
    sell = _named(shop, "sales_floor")
    assert len(sell["pack_wall"]) <= p["most"]
    assert len(sell["pack_wall"]) == len(sell["display_case"])


def test_no_card_shop_room_carries_more_than_its_caps(shop):
    caps = {"display_case": 2, "pack_wall": 2, "pennant_row": 2,
            "folding_table": level_design._CARD_PLAY_TABLES_MAX}
    b = level_design.club_building_id(shop)
    for room in shop["rooms"]:
        if not level_design.is_card_shop_room(room, b):
            continue
        got = _named(shop, room["id"])
        for stem, cap in caps.items():
            assert len(got.get(stem, [])) <= cap, (room["id"], stem)


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
