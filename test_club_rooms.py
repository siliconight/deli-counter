"""0.132.0 -- a strip club is furnished and lit as one.

The walker, with two frames of GTA IV's Triangle Club: "strip clubs should
have a dingy lived in feel, dark with colored lights, couches and bars". The
layout comp is a one-storey windowless neighbourhood club with two bar areas
whose pole stage stands inside the bar, stools round it, CRTs on brackets.
On 0.131.1 `strip_club_a01`'s main floor was a shop floor -- shelving, a
vending machine, cartons -- under five cool fluorescent lamps, with the
authored stage a grey box.
"""
import collections
import copy
import json
import math
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design   # noqa: E402
import lights         # noqa: E402
import prop_species   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CLUB_SPECIES = {"club_stage", "bar_stool", "counter", "booth_seat", "neon_sign",
                "crt_tv", "cocktail_table", "club_chair", "vending_machine"}
_GEN = re.compile(r"^(?P<stem>[a-z_]+?)_(?P<tag>r[0-9a-f]{8})_\d+(_\d+)?$")


def _club(w=20.0, d=12.0, rid="main_floor", name="strip_club_probe", **kw):
    """A strip club with one room; the footprint is larger than the room so
    its walls are interior (the furnish probe's reasoning)."""
    s = {"name": name, "seed": 1997, "story_height": 3.6, "wall_thick": 0.3,
         "footprint_x": w + 4.0, "footprint_y": d + 4.0, "n_stories": 1,
         "default_material": "concrete",
         "materials": [{"id": "concrete"}, {"id": "drywall"}, {"id": "wood"}],
         "rooms": [{"id": rid, "story": 0, "role": "public_entry",
                    "bounds": [-w / 2, -d / 2, w / 2, d / 2],
                    "combat_range": "medium"}],
         "volumes": [], "partitions": [], "ext_walls": [], "stairs": []}
    s.update(kw)
    return s


def _stem(v):
    m = _GEN.match(v["name"])
    return m.group("stem") if m else None


def _library(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


# --- the kind ----------------------------------------------------------------

def test_the_kind_is_read_only_inside_a_strip_club_building():
    k = level_design._room_kind
    assert k({"id": "main_floor"}, "strip_club_a01") == "strip_club"
    assert k({"id": "main_floor"}, "deli_a01") == "shop_floor"
    assert k({"id": "vip_wing", "role": "connector"}, "strip_club_a01") == "strip_club"
    assert k({"id": "champagne_wing"}, "strip_club_a03") == "strip_club"
    assert k({"id": "champagne_wing"}, "country_club_a01") == "wine_cellar"
    assert k({"id": "back_bar"}, "strip_club_a03") == "strip_club"
    assert k({"id": "club_bar"}, "country_club_a02") == "club"
    assert k({"id": "go_go_lounge"}, "strip_club_x") == "strip_club"
    # the club's other rooms keep their kinds
    assert k({"id": "cash_office", "role": "objective_room"}, "strip_club_a01") == "vault"
    assert k({"id": "back_rooms", "role": "connector"}, "strip_club_a02") == "fallback"
    assert k({"id": "cellar_hall", "story": -1}, "strip_club_a02") == "basement"
    assert k({"id": "count_room", "story": -1}, "strip_club_a02") == "vault"
    # and the one rule is shared with the light manifest
    assert level_design.is_strip_club_room({"id": "main_floor"}, "strip_club_a02")
    assert not level_design.is_strip_club_room({"id": "main_floor"}, "casino_a01")


def test_the_library_rooms_the_kind_claims_are_exactly_these():
    claimed = []
    for name in ("strip_club_a01", "strip_club_a02", "strip_club_a03"):
        d = _library(name)
        claimed += [(name, r["id"]) for r in d["rooms"]
                    if level_design.is_strip_club_room(r, d["name"])]
    assert claimed == [("strip_club_a01", "main_floor"), ("strip_club_a01", "vip_wing"),
                       ("strip_club_a02", "main_floor"),
                       ("strip_club_a03", "main_floor"), ("strip_club_a03", "back_bar"),
                       ("strip_club_a03", "vip_mezz"), ("strip_club_a03", "champagne_wing")]


# --- the furniture ------------------------------------------------------------

def test_a_club_room_is_a_stage_a_bar_couches_a_name_in_neon_and_small_tables():
    s = _club(20.0, 12.0)                      # 240 m2, aspect 1.67: the bar stage
    level_design.furnish(s)
    species = collections.Counter(prop_species.species_for_name(v["name"])
                                  for v in s["volumes"])
    assert None not in species, [v["name"] for v in s["volumes"]
                                 if prop_species.species_for_name(v["name"]) is None]
    assert set(species) <= CLUB_SPECIES, species
    assert species["club_stage"] >= 1
    assert species["bar_stool"] >= 6
    assert species["cocktail_table"] >= 2
    assert species["club_chair"] >= 2 * species["cocktail_table"] - 2
    assert species["booth_seat"] >= 1
    assert species["neon_sign"] >= 1
    assert species["crt_tv"] >= 1
    stems = {_stem(v) for v in s["volumes"]}
    # nothing of the shop floor or the office: no shelving, desks, chair sets
    assert not stems & {"shelf_run", "desk", "cabinet_file", "chair_set", "cartons",
                        "table_dining", "chair_waiting", "counter_service"}, stems


def test_the_stage_is_authored_to_the_ceiling_over_an_invisible_platform_collider():
    s = _club(20.0, 12.0)
    level_design.furnish(s)
    stage = [v for v in s["volumes"] if v["name"].startswith("stage_bar_")]
    deck = [v for v in s["volumes"] if v["name"].startswith("stage_deck_")]
    assert len(stage) == 1 and len(deck) == 1
    st, dk = stage[0], deck[0]
    clear = level_design._clear_height(s)
    assert abs(st["size_z"] - min(clear, level_design._TO_CEILING_MAX)) < 1e-6
    assert st["collision"] == "none" and st["form"] == "bar_stage" and st["stock"] == "bar"
    assert st.get("visual", True) is True
    # the collider is the platform: same footprint, the deck's height, no slot
    assert dk["visual"] is False and dk["collision"] == "convex"
    assert (dk["x"], dk["y"], dk["size_x"], dk["size_y"]) == (st["x"], st["y"], st["size_x"], st["size_y"])
    assert dk["size_z"] == 1.18 and abs(dk["z"] - 0.59) < 1e-6
    # in the middle of the room, long side along the room's long axis
    assert (st["x"], st["y"]) == (0.0, 0.0)
    assert st["size_x"] > st["size_y"]


def test_a_long_room_gets_a_round_stage_and_a_bar_on_the_wall():
    s = _club(30.0, 10.0)                      # aspect 3
    level_design.furnish(s)
    stems = collections.Counter(_stem(v) for v in s["volumes"])
    assert stems["stage_round"] == 1 and stems["stage_bar"] == 0
    assert stems["counter_club"] >= 1
    deck = next(v for v in s["volumes"] if v["name"].startswith("stage_deck_"))
    assert deck["size_z"] == 0.8
    # stools line a counter's front, not the stage: each stool is its own
    # counter's (`bar_stool_<tag>_<counter seq>_<n>`), within its length
    counters = {v["name"].rsplit("_", 1)[1]: v for v in s["volumes"]
                if v["name"].startswith("counter_club_")}
    stools = [v for v in s["volumes"] if v["name"].startswith("bar_stool_")]
    assert stools and len(counters) == 2            # 300 m2: the second bar
    for v in stools:
        host = counters[v["name"].split("_")[3]]
        assert math.hypot(v["x"] - host["x"], v["y"] - host["y"]) < 3.5, (v["name"], host["name"])


def test_a_large_room_gets_a_second_bar():
    s = _club(24.0, 14.0)                      # 336 m2, aspect 1.7
    level_design.furnish(s)
    stems = collections.Counter(_stem(v) for v in s["volumes"])
    assert stems["stage_bar"] == 1 and stems["counter_club"] == 1


def test_stools_ring_the_bar_stage_and_face_it():
    s = _club(20.0, 12.0)
    level_design.furnish(s)
    st = next(v for v in s["volumes"] if v["name"].startswith("stage_bar_"))
    tag = _GEN.match(st["name"]).group("tag")
    stools = [v for v in s["volumes"] if v["name"].startswith("bar_stool_%s_1_" % tag)]
    assert 6 <= len(stools) <= 10, len(stools)
    hx, hy = st["size_x"] / 2.0, st["size_y"] / 2.0
    for v in stools:
        dx, dy = abs(v["x"] - st["x"]) - hx, abs(v["y"] - st["y"]) - hy
        # a stool's edge a hand off the bar's band, never inside it
        gap = max(dx, dy) - v["size_x"] / 2.0
        assert 0.10 <= gap <= 0.20, (v["name"], gap)
        # facing the bar: a seat's front is its module's -Y, bearing
        # rot_z + 180 (the chair convention), aimed at the bar's centre
        want = math.degrees(math.atan2(st["x"] - v["x"], st["y"] - v["y"])) % 360.0
        front = (v["rot_z"] + 180.0) % 360.0
        assert abs((front - want + 180.0) % 360.0 - 180.0) < 0.2, (v["rot_z"], want)
        assert v["material"] == "metal_bare"


def test_a_cocktail_table_brings_two_or_three_tub_chairs_facing_it():
    s = _club(20.0, 12.0)
    level_design.furnish(s)
    tables = [v for v in s["volumes"] if v["name"].startswith("table_cocktail_")]
    assert tables
    for t in tables:
        assert t["form"] == "cloth" and t["stock"] == "bar"
        m = _GEN.match(t["name"])
        seq = t["name"].rsplit("_", 1)[1]
        chairs = [v for v in s["volumes"]
                  if v["name"].startswith("club_chair_%s_%s_" % (m.group("tag"), seq))]
        assert len(chairs) <= 3
        for c in chairs:
            assert (c["size_x"], c["size_y"], c["size_z"]) == (0.78, 0.75, 0.78)
            assert math.hypot(c["x"] - t["x"], c["y"] - t["y"]) < 1.5
            f = math.radians((float(c.get("rot_z", 0.0)) + 180.0) % 360.0)
            assert math.sin(f) * (t["x"] - c["x"]) + math.cos(f) * (t["y"] - c["y"]) > 0
    assert sum(1 for v in s["volumes"] if v["name"].startswith("club_chair_")) >= 2


def test_hung_pieces_hang_in_free_air_over_the_furniture():
    """A neon sign and a bracket TV hang at 2.2 / 2.1 m with no collision: a
    body's head is 1.8 m and so is the nav bake's clearance. They take no
    share of the floor -- a couch may stand under one -- and clear the
    openings in an outside wall like any wall piece."""
    s = _club(20.0, 12.0)
    s["footprint_x"], s["footprint_y"] = 20.0, 12.0     # the room IS the building
    s["ext_walls"] = [{"wall": "S", "story": 0, "material": "concrete",
                       "openings": [{"kind": "door", "pos": 0.0, "width": 1.6}]},
                      {"wall": "N", "story": 0, "material": "concrete",
                       "openings": [{"kind": "door", "pos": -0.3, "width": 1.25}]}]
    level_design.furnish(s)
    hung = [v for v in s["volumes"] if v["name"].startswith(("neon_sign_", "wall_tv_"))]
    assert hung, [v["name"] for v in s["volumes"]]
    for v in hung:
        assert v["collision"] == "none"
        assert v["z"] - v["size_z"] / 2.0 >= level_design._HUNG_MIN
        assert v["z"] + v["size_z"] / 2.0 <= level_design._clear_height(s)
        assert v["z"] == (2.2 if v["name"].startswith("neon") else 2.1)
        assert v["material"] == "metal_painted"
        # against a wall (its thin side to it), facing in
        x0, y0, x1, y1 = s["rooms"][0]["bounds"]
        edge = min(v["x"] - x0, x1 - v["x"], v["y"] - y0, y1 - v["y"])
        assert edge < 0.6, (v["name"], edge)
        # clear of the doors: 0.9 m past the opening's edge
        for door_x, door_y, hw in ((0.0, -6.0, 0.8), (-6.0, 6.0, 0.625)):
            along = abs(v["x"] - door_x) if abs(v["y"] - door_y) < 0.6 else 99.0
            assert along >= hw + max(v["size_x"], v["size_y"]) / 2.0 + 0.9 - 1e-6, v
    # they hold no spread: a floor piece may stand within 2.2 m of one
    floor = [v for v in s["volumes"] if v not in hung and v.get("visual", True)]
    near = [(h["name"], f["name"]) for h in hung for f in floor
            if math.hypot(h["x"] - f["x"], h["y"] - f["y"]) < 2.2]
    assert near, "nothing stands near a hung piece; the spread is still held"


def test_the_neon_names_the_building_once():
    """`neon_sign`'s variant IS the name (Zoo 0.88.0: 24 of them); a club has
    one name, so every sign in a building draws crc32(building) % 24."""
    s = _club(30.0, 14.0)                      # big enough for two signs
    level_design.furnish(s)
    signs = [v for v in s["volumes"] if v["name"].startswith("neon_sign_")]
    assert signs
    want = (zlib.crc32(b"strip_club_probe") & 0xFFFFFFFF) % 24
    assert {v.get("variant", 0) for v in signs} == {want}
    other = _club(30.0, 14.0, name="strip_club_other")
    level_design.furnish(other)
    got = {v.get("variant", 0) for v in other["volumes"] if v["name"].startswith("neon_sign_")}
    assert got == {(zlib.crc32(b"strip_club_other") & 0xFFFFFFFF) % 24}


def test_the_only_mid_floor_shelter_is_the_stage():
    """The furnishing pass's standing rule -- nothing mid-floor reaches
    shelter height -- with the one deliberate exception: a stage is shelter
    (the walker's "shooting galleries": bars and cover), and its visual
    volume reaches the ceiling for the pole."""
    for w, d in ((20.0, 12.0), (30.0, 10.0), (24.0, 14.0)):
        s = _club(w, d)
        level_design.furnish(s)
        x0, y0, x1, y1 = s["rooms"][0]["bounds"]
        for v in s["volumes"]:
            if v["size_z"] < level_design._COVER_HIGH_Z:
                continue
            edge = min(v["x"] - x0, x1 - v["x"], v["y"] - y0, y1 - v["y"])
            if edge > max(v["size_x"], v["size_y"]) / 2.0 + 0.5:
                assert v["name"].startswith(("stage_bar_", "stage_round_", "stage_deck_")), v


def test_the_club_keeps_the_furnishing_invariants():
    """Stair reservations, the 2.2 m spread between hosts, the wall
    standoff, idempotence by mark and determinism -- as every other kind."""
    s = _club(24.0, 14.0, stairs=[{"x": -8.0, "y": 0.0, "from_story": 0, "to_story": 1,
                                   "style": "straight", "facing": "N", "run": 4.7,
                                   "id": "st"}])
    s["n_stories"] = 2
    n = level_design.furnish(s)
    assert n > 0
    assert level_design.furnish(s) == 0
    hosts = [v for v in s["volumes"] if v.get("visual", True)
             and not v["name"].startswith(("bar_stool_", "club_chair_", "neon_sign_", "wall_tv_"))]
    for i, a in enumerate(hosts):
        for b in hosts[i + 1:]:
            assert math.hypot(a["x"] - b["x"], a["y"] - b["y"]) >= 2.2 - 1e-6, (a["name"], b["name"])
    rects = level_design._stair_reserved_rects(s)
    assert rects
    for v in s["volumes"]:
        hx, hy = v["size_x"] / 2.0, v["size_y"] / 2.0
        for r in rects:
            assert not (v["x"] + hx > r[0] and v["x"] - hx < r[2]
                        and v["y"] + hy > r[1] and v["y"] - hy < r[3]), (v["name"], r)
    t = _club(24.0, 14.0, stairs=s["stairs"])
    t["n_stories"] = 2
    level_design.furnish(t)
    assert [(v["name"], v["x"], v["y"], v.get("rot_z")) for v in s["volumes"]] == \
           [(v["name"], v["x"], v["y"], v.get("rot_z")) for v in t["volumes"]]


# --- the surfaces --------------------------------------------------------------

def test_the_club_wears_its_own_surfaces_and_nothing_else_does():
    s = _club(20.0, 12.0)
    s["rooms"].append({"id": "cash_office", "story": 0, "role": "objective_room",
                       "bounds": [10.0, -6.0, 12.0, 6.0]})
    s["partitions"] = [{"story": 0, "axis": "Y", "pos": 10.0, "start": -6.0, "end": 6.0,
                        "material": "drywall", "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}]
    s["ext_walls"] = [{"wall": "S", "story": 0, "material": "concrete", "openings": []},
                      {"wall": "N", "story": 0, "openings": []}]
    level_design.furnish(s)
    room = s["rooms"][0]
    assert room["floor_material"] == "carpet_club"
    assert "floor_material" not in s["rooms"][1]
    # the partition has an office on its other face: not papered
    assert s["partitions"][0]["material"] == "drywall"
    assert all(w["material"] == "paint_block" for w in s["ext_walls"])
    assert s["default_material"] == "paint_block"
    declared = {m["id"]: m for m in s["materials"]}
    for mid in ("carpet_club", "paint_block", "leather", "metal_bare", "metal_painted"):
        assert mid in declared and declared[mid].get("acoustic"), mid
    assert "wallpaper_club" not in declared
    for v in s["volumes"]:
        assert v["material"] in declared, v
        if v["name"].startswith("sofa_club_"):
            assert v["material"] == "leather" and v["form"] == "sofa"
    # two club rooms either side of a partition: papered
    t = _club(20.0, 12.0)
    t["rooms"].append({"id": "vip_lounge", "story": 0, "role": "connector",
                       "bounds": [10.0, -6.0, 18.0, 6.0]})
    t["footprint_x"] = 30.0
    t["partitions"] = [{"story": 0, "axis": "Y", "pos": 10.0, "start": -6.0, "end": 6.0,
                        "material": "drywall", "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}]
    level_design.furnish(t)
    assert t["partitions"][0]["material"] == "wallpaper_club"
    # and a building that is not a strip club is left alone
    u = _club(20.0, 12.0, name="country_club_probe")
    u["ext_walls"] = [{"wall": "S", "story": 0, "material": "concrete", "openings": []}]
    level_design.furnish(u)
    assert "floor_material" not in u["rooms"][0]
    assert u["ext_walls"][0]["material"] == "concrete" and u["default_material"] == "concrete"


def test_every_booth_and_sofa_in_the_library_is_leather_now():
    """Zoo 0.88.0: a sofa slot's material is its upholstery, and every booth
    this pass wrote wore wood."""
    import glob
    wood = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
        for v in d.get("volumes", []):
            m = _GEN.match(v["name"])
            if m and m.group("tag") in tags and m.group("stem") in ("booth", "sofa", "sofa_club"):
                if v.get("material") != "leather":
                    wood.append((os.path.basename(p), v["name"], v.get("material")))
    assert not wood, wood[:10]


def test_a_vending_machine_has_a_brand_and_a_room_may_take_three():
    """Zoo 0.87.0's four branded variants; `most` was 1 and `variants` False,
    so every machine of one size in a building sold the same thing."""
    p = level_design._PIECES["vending"]
    assert p["variants"] is True and p["most"] == 3
    seen = collections.Counter()
    variants = set()
    for seed in range(6):
        s = {"name": "lobby_probe", "seed": seed, "story_height": 3.6,
             "footprint_x": 44.0, "footprint_y": 34.0, "n_stories": 1,
             "rooms": [{"id": "upper_hall", "story": 0, "role": "connector",
                        "bounds": [-20.0, -15.0, 20.0, 15.0]}],
             "volumes": [], "partitions": [], "stairs": []}
        level_design.furnish(s)
        vend = [v for v in s["volumes"] if v["name"].startswith("vending_")]
        seen[len(vend)] += 1
        for v in vend:
            n = (zlib.crc32(v["name"].encode("utf-8")) & 0xFFFFFFFF) % 4
            assert v.get("variant", 0) == n, v
            variants.add(n)
    assert max(seen) <= 3 and max(seen) >= 2, seen
    assert len(variants) >= 2, variants


# --- the light ------------------------------------------------------------------

def _lit(s):
    rooms = [dict(r, center=[(r["bounds"][0] + r["bounds"][2]) / 2.0,
                             (r["bounds"][1] + r["bounds"][3]) / 2.0,
                             r["story"] * s["story_height"]]) for r in s["rooms"]]
    club = {r["id"] for r in s["rooms"] if level_design.is_strip_club_room(r, s["name"])}
    rep = {}
    m = lights.build_light_manifest(s["name"], rooms, [], s["story_height"],
                                    cap_thick=0.3, wall_thick=0.3,
                                    volumes=s["volumes"], club_rooms=club, report=rep)
    return m, rep


def test_a_club_room_is_lit_by_the_club_set_and_no_fluorescent_row():
    s = _club(20.0, 12.0)
    s["rooms"].append({"id": "cash_office", "story": 0, "role": "objective_room",
                       "objective": True, "bounds": [10.0, -6.0, 12.0, 6.0]})
    level_design.furnish(s)
    m, rep = _lit(s)
    assert m["light_manifest_version"] == "1.2.0"
    assert rep["club_rooms"] == 1
    by_room = collections.defaultdict(collections.Counter)
    for a in m["anchors"]:
        by_room[a.get("room")][a["type"]] += 1
    club = by_room["main_floor"]
    assert club["fluorescent"] == 0 and club["pendant"] == 0
    assert 3 <= club["club_wash"] <= 5
    assert club["stage_light"] == 1
    signs = sum(1 for v in s["volumes"] if v["name"].startswith("neon_sign_"))
    tvs = sum(1 for v in s["volumes"] if v["name"].startswith("wall_tv_"))
    # each sign, the stage's rope light, and each TV's screen (0.135.0)
    assert club["neon"] == signs + 1 + tvs
    assert club["room_ambient"] == 1
    # the office keeps its pendants (an objective room) and gains its box
    assert by_room["cash_office"]["pendant"] >= 1
    assert by_room["cash_office"]["room_ambient"] == 1
    for a in m["anchors"]:
        if "color" in a and a["color"] is not None:
            assert a["color"] in lights.CLUB_COLOURS, a


def test_washes_vary_in_colour_and_take_the_partition_test():
    s = _club(30.0, 14.0)
    s["partitions"] = [{"story": 0, "axis": "Y", "pos": -7.5, "start": -7.0, "end": 7.0,
                        "material": "drywall", "openings": []}]
    level_design.furnish(s)
    m, _ = _lit(s)
    washes = [a for a in m["anchors"] if a["type"] == "club_wash"]
    assert len(washes) == 5
    assert len({a["color"] for a in washes}) >= 3
    clear = lights.wall_clearance(0.3)
    for a in washes:
        assert abs(a["pos"][0] - (-7.5)) >= clear - 1e-6, a
        assert a["pos"][2] == 3.2 and a["drop"] == 3.2
        assert 1.5 <= a["radius"] <= 6.0
    # deterministic, and two rooms are not lit alike
    t = _club(30.0, 14.0, rid="vip_lounge")
    level_design.furnish(t)
    n, _ = _lit(t)
    other = [a["color"] for a in n["anchors"] if a["type"] == "club_wash"]
    assert other != [a["color"] for a in washes]


def test_the_stage_light_aims_at_the_body_over_the_platform():
    for w, d, form, platform in ((20.0, 12.0, "bar_stage", 1.18), (30.0, 10.0, "round", 0.8)):
        s = _club(w, d)
        level_design.furnish(s)
        st = next(v for v in s["volumes"] if v["name"].startswith("stage_") and v.get("visual", True))
        assert st["form"] == form
        m, _ = _lit(s)
        spot = next(a for a in m["anchors"] if a["type"] == "stage_light")
        assert spot["target"] == [st["x"], st["y"], round(platform + 0.5, 3)]
        assert spot["pos"][2] == 3.2 and spot["row"] == {"count": 2, "spacing": 1.2}
        assert spot["cycle_s"] == 4.0 and spot["color"] in lights.CLUB_COLOURS
        # thrown from past the stage's edge, inside the room
        px, py = spot["pos"][:2]
        assert (abs(px - st["x"]) >= st["size_x"] / 2.0 + 1.5 - 1e-6
                or abs(py - st["y"]) >= st["size_y"] / 2.0 + 1.5 - 1e-6), spot
        x0, y0, x1, y1 = s["rooms"][0]["bounds"]
        assert x0 < px < x1 and y0 < py < y1
        rope = next(a for a in m["anchors"] if a["id"].endswith("_stage_lip"))
        assert rope["type"] == "neon" and rope["color"] == "amber"
        if form == "bar_stage":
            assert rope["pos"][2] == round(platform + 0.35, 3)
            assert abs(rope["pos"][0] - st["x"]) + abs(rope["pos"][1] - st["y"]) == 0.5
        else:
            assert rope["pos"][2] == 0.75
            assert not (abs(rope["pos"][0] - st["x"]) < st["size_x"] / 2.0
                        and abs(rope["pos"][1] - st["y"]) < st["size_y"] / 2.0)


def test_a_neon_spill_stands_proud_of_its_sign_in_free_air():
    s = _club(30.0, 14.0)
    level_design.furnish(s)
    m, _ = _lit(s)
    signs = [v for v in s["volumes"] if v["name"].startswith("neon_sign_")]
    neons = [a for a in m["anchors"] if a["type"] == "neon"
             and not a["id"].endswith(("_stage_lip", "_screen"))]
    assert len(signs) == len(neons) >= 1
    x0, y0, x1, y1 = s["rooms"][0]["bounds"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    for v, a in zip(signs, neons):
        depth = min(v["size_x"], v["size_y"])
        dist = math.hypot(a["pos"][0] - v["x"], a["pos"][1] - v["y"])
        assert abs(dist - (depth / 2.0 + 0.15)) < 1e-3, (v["name"], dist)
        # outside the cabinet, on the room side of it
        assert not (abs(a["pos"][0] - v["x"]) < v["size_x"] / 2.0
                    and abs(a["pos"][1] - v["y"]) < v["size_y"] / 2.0)
        assert math.hypot(a["pos"][0] - cx, a["pos"][1] - cy) < math.hypot(v["x"] - cx, v["y"] - cy)
        assert a["pos"][2] == v["z"]
        assert "color" not in a
        assert a["size"] == [max(v["size_x"], v["size_y"]), v["size_z"]]
        # rot_y is the sign's facing in this manifest's frame (0 == +X)
        r = math.radians(a["rot_y"])
        assert math.cos(r) * (cx - v["x"]) + math.sin(r) * (cy - v["y"]) > 0


def _lux_neon_range(a):
    """Lux 0.38.1's `neon` range: 0.5 x the longer side + 1.0 m, held to
    1.0-2.5 (`lux_light_loader.gd`, the `neon` branch of `_club_rig`)."""
    return min(2.5, max(1.0, 0.5 * max(a["size"]) + 1.0))


def test_a_tv_that_is_on_spills_its_screen_in_free_air():
    """Zoo 0.90.0 lights the bracket TV's screen; its spill is a `neon`
    `_TV_SCREEN_OUT` in front of the slot, cold, the screen's size."""
    s = _club(30.0, 14.0)
    level_design.furnish(s)
    tvs = [v for v in s["volumes"] if v["name"].startswith("wall_tv_")]
    assert tvs and all(v.get("form") == "bracket" for v in tvs)
    m, rep = _lit(s)
    screens = {a["id"]: a for a in m["anchors"] if a["id"].endswith("_screen")}
    assert rep["tv_screens"] == len(tvs) == len(screens)
    x0, y0, x1, y1 = s["rooms"][0]["bounds"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    for v in tvs:
        a = screens[v["name"] + "_screen"]
        assert a["type"] == "neon" and a["room"] == "main_floor"
        depth, width = min(v["size_x"], v["size_y"]), max(v["size_x"], v["size_y"])
        dist = math.hypot(a["pos"][0] - v["x"], a["pos"][1] - v["y"])
        assert abs(dist - (depth / 2.0 + 0.25)) < 1e-3, (v["name"], dist)
        # in free air in front of the set, on the room side of it
        assert not (abs(a["pos"][0] - v["x"]) < v["size_x"] / 2.0
                    and abs(a["pos"][1] - v["y"]) < v["size_y"] / 2.0)
        assert math.hypot(a["pos"][0] - cx, a["pos"][1] - cy) < math.hypot(v["x"] - cx, v["y"] - cy)
        assert a["pos"][2] == round(v["z"] + 0.036, 3) and a["drop"] == round(v["z"] + 0.036, 3)
        r = math.radians(a["rot_y"])
        assert math.cos(r) * (a["pos"][0] - v["x"]) + math.sin(r) * (a["pos"][1] - v["y"]) > 0
        assert a["color"] in ("cyan", "blue") and a["color"] in lights.CLUB_COLOURS
        assert a["size"] == lights.tv_screen_size(width, v["size_z"])
        assert 1.0 <= _lux_neon_range(a) <= 1.5, a
    n, _ = _lit(copy.deepcopy(s))
    assert [a for a in n["anchors"] if a["id"].endswith("_screen")] == list(screens.values())


def test_the_screen_size_is_zoos():
    """Zoo 0.90.0's fitted screen, measured off `crt_forms.plan_bracket` at
    the two sizes the recipe places (width x height of the lit face)."""
    for (w, h), zoo in (((0.6, 0.5), (0.3953, 0.2965)), ((0.7, 0.55), (0.4450, 0.3337))):
        got = lights.tv_screen_size(w, h)
        assert abs(got[0] - zoo[0]) <= 0.01 * zoo[0] and abs(got[1] - zoo[1]) <= 0.01 * zoo[1], (got, zoo)


def test_a_tv_outside_a_club_spills_and_a_set_that_is_off_does_not():
    t = _club(20.0, 12.0, name="office_probe", rid="bullpen")
    t["volumes"] = [
        {"name": "wall_tv_r00000001_1", "x": 0.0, "y": 5.7, "z": 2.1, "size_x": 0.6,
         "size_y": 0.55, "size_z": 0.5, "rot_z": 0.0, "form": "bracket", "collision": "none"},
        {"name": "bar_tv_r00000001_2", "x": 3.0, "y": 0.0, "z": 0.3, "size_x": 0.55,
         "size_y": 0.5, "size_z": 0.42, "rot_z": 0.0, "collision": "none"}]
    n, rep = _lit(t)
    assert rep["club_rooms"] == 0 and rep["tv_screens"] == 1
    types = collections.Counter(a["type"] for a in n["anchors"])
    assert types == {"fluorescent": 1, "neon": 1, "room_ambient": 1}, types
    ids = [a["id"] for a in n["anchors"]]
    # the room's ceiling light first and its box last, as every reader assumes
    assert ids == ["bullpen_ceiling", "wall_tv_r00000001_1_screen", "bullpen_ambient"], ids


def test_the_library_clubs_light_every_tv():
    for name in ("strip_club_a01", "strip_club_a02", "strip_club_a03"):
        spec = _library(name)
        with open(os.path.join(HERE, "build", name + ".lights.json"), encoding="utf-8") as f:
            m = json.load(f)
        tvs = sorted(v["name"] for v in spec["volumes"]
                     if prop_species.species_for_name(v["name"]) == "crt_tv" and v.get("form") == "bracket")
        got = sorted(a["id"][:-len("_screen")] for a in m["anchors"] if a["id"].endswith("_screen"))
        assert tvs and got == tvs, (name, tvs, got)


def test_every_room_carries_its_box_for_the_ambient_probe():
    s = _club(20.0, 12.0)
    s["rooms"].append({"id": "cash_office", "story": 0, "role": "objective_room",
                       "bounds": [10.0, -6.0, 12.0, 6.0]})
    s["rooms"].append({"id": "cellar", "story": -1, "role": "connector",
                       "bounds": [-10.0, -6.0, 10.0, 6.0]})
    m, _ = _lit(s)
    amb = {a["room"]: a for a in m["anchors"] if a["type"] == "room_ambient"}
    assert set(amb) == {"main_floor", "cash_office", "cellar"}
    for rid, a in amb.items():
        r = next(r for r in s["rooms"] if r["id"] == rid)
        x0, y0, x1, y1 = r["bounds"]
        floor = r["story"] * 3.6
        assert a["size"] == [x1 - x0, y1 - y0, 3.3]           # to the ceiling plane
        assert a["pos"] == [(x0 + x1) / 2.0, (y0 + y1) / 2.0, round(floor + 1.65, 3)]
        assert a["reacts_to_alarm"] is False
    assert amb["main_floor"]["color"] in lights.CLUB_COLOURS
    assert amb["cash_office"]["color"] is None and amb["cellar"]["color"] is None
    # an ordinary building: a box per room and nothing else new
    t = _club(20.0, 12.0, name="office_probe", rid="bullpen")
    n, rep = _lit(t)
    assert rep["club_rooms"] == 0
    types = collections.Counter(a["type"] for a in n["anchors"])
    assert types == {"fluorescent": 1, "room_ambient": 1}, types


# --- the library ------------------------------------------------------------------

def test_the_three_clubs_are_furnished_as_clubs():
    for name in ("strip_club_a01", "strip_club_a02", "strip_club_a03"):
        d = _library(name)
        assert d["default_material"] == "paint_block"
        assert all(w["material"] == "paint_block" for w in d["ext_walls"])
        assert not any(v["name"] in ("stage", "bar_run") for v in d["volumes"])
        for r in d["rooms"]:
            if not level_design.is_strip_club_room(r, d["name"]):
                continue
            assert r.get("floor_material") == "carpet_club", (name, r["id"])
            tag = level_design._room_tag(r)
            mine = [v for v in d["volumes"] if f"_{tag}_" in v["name"]]
            species = collections.Counter(prop_species.species_for_name(v["name"]) for v in mine)
            assert set(species) <= CLUB_SPECIES, (name, r["id"], species)
            assert species["club_stage"] >= 1 and species["bar_stool"] >= 3, (name, r["id"], species)
            assert species["cocktail_table"] >= 1 and species["booth_seat"] >= 1
            assert species["neon_sign"] >= 1, (name, r["id"], species)
            assert len(set(species)) >= 6, (name, r["id"], species)
    a01 = _library("strip_club_a01")
    assert next(p for p in a01["partitions"] if p["axis"] == "X")["material"] == "wallpaper_club"
    assert next(p for p in a01["partitions"] if p["axis"] == "Y")["material"] == "concrete"


def test_the_club_migration_is_idempotent():
    import migrate_club_rooms as mig
    d = _library("strip_club_a01")
    once = copy.deepcopy(d)
    mig.migrate(once)
    assert json.dumps(once, sort_keys=True) == json.dumps(d, sort_keys=True)
