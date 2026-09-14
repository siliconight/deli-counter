"""Rooms get FURNITURE, and it is a different question from cover.

The walker, 2026-09-13: great progress outside the buildings, what about the
props inside. Measured over the 130 built shells before this: 819 prop slots
in all, 6.3 per building, 29 buildings with none. A bank tower's whole
interior was three teller lines and a funeral home had nothing.

`seed_cover` could not be the answer and must not be made into one. It fires
only when a room is BARE or has no SHELTER, caps at four pieces, and its
docstring argues the case: "props that give cover AND life without overkill".
That thesis is about COVER -- a mid-floor blocker changes how a room plays --
so furniture is a separate pass written to leave the cover balance alone.
These tests are what "leave it alone" means, stated so it cannot drift.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design   # noqa: E402
import prop_species   # noqa: E402


def _spec(w=12.0, d=10.0, role="office", **kw):
    # The footprint is deliberately LARGER than the room: wall furniture
    # stands against interior walls only, because `_seed_clear` knows about
    # partitions and nothing here knows where the openings in an outside
    # wall are. A probe room that WAS the whole building would have four
    # exterior walls and no shelf would ever be placed.
    s = {"name": "furnish_probe", "seed": 1997, "story_height": 3.0,
         "footprint_x": w + 4.0, "footprint_y": d + 4.0, "n_stories": 1,
         "rooms": [{"id": "r0", "story": 0, "role": role,
                    "bounds": [-w / 2, -d / 2, w / 2, d / 2],
                    "combat_range": "medium"}],
         "volumes": [], "partitions": [], "stairs": []}
    s.update(kw)
    return s


def _hosts(volumes):
    """Every placed piece but a host's chairs, which belong to the host and
    never counted toward the target (0.123.0)."""
    return [v for v in volumes if not v["name"].startswith("chair_set_")]


def test_a_bare_room_is_furnished_to_a_density_derived_from_its_area():
    """0.131.0: an office's desks bring a chair each, so the pieces counted
    against the density are the hosts, as they always were for tables."""
    s = _spec(12.0, 10.0)                       # 120 m2
    n = level_design.furnish(s)
    assert len(_hosts(s["volumes"])) == round(120.0 / level_design._FURNISH_PER_AREA)
    assert len(s["volumes"]) == n


def test_it_is_idempotent_because_what_is_there_counts():
    s = _spec(12.0, 10.0)
    first = level_design.furnish(s)
    assert first > 0
    assert level_design.furnish(s) == 0
    assert len(s["volumes"]) == first


def test_an_authored_room_is_topped_up_rather_than_doubled():
    s = _spec(12.0, 10.0)
    want = round(120.0 / level_design._FURNISH_PER_AREA)
    s["volumes"] = [{"name": f"authored_{i}", "x": -5.0 + i * 0.9, "y": -4.0,
                     "z": 0.45, "size_x": 0.6, "size_y": 0.6, "size_z": 0.9,
                     "collision": "convex"} for i in range(want - 1)]
    level_design.furnish(s)
    assert len(_hosts(s["volumes"])) == want


def test_nothing_it_puts_mid_floor_reaches_shelter_height():
    """The whole reason this is a separate pass, stated as the invariant it
    actually is.

    REFUTED FIRST DRAFT, kept above the result that replaced it. This
    asserted that nothing mid-floor reached `_COVER_MIN_Z` (0.60 m) and it
    failed on its first run: a desk is 0.75 and a floor safe is 1.00. That
    assertion was wrong, not the furniture -- a desk IS low cover, in this
    engine and in a real office, and pretending otherwise would have meant
    furnishing rooms with nothing but chairs.

    What `seed_cover`'s over-cover thesis actually protects is SHELTER: a
    body can fight from something only at `cover_break_height`, and one
    shelter piece per room is the rule that module enforces. So the
    invariant here is that this pass never creates one. Anything that tall
    goes flush against a wall, where it is a bookcase and not a redoubt.
    """
    shelter_z = level_design.shelter_height()
    tall_mid_floor = []
    for role in ("office", "storage", "bay", "vault", "utility", "lobby",
                 "something_unmatched"):
        s = _spec(20.0, 16.0, role=role)
        level_design.furnish(s)
        x0, y0, x1, y1 = s["rooms"][0]["bounds"]
        for v in s["volumes"]:
            if v["size_z"] < shelter_z:
                continue
            edge = min(abs(v["x"] - x0), abs(x1 - v["x"]),
                       abs(v["y"] - y0), abs(y1 - v["y"]))
            half = max(v["size_x"], v["size_y"]) / 2.0
            if edge > half + 0.5:
                tall_mid_floor.append((role, v["name"], round(edge, 2)))
    assert not tall_mid_floor, tall_mid_floor


def test_every_name_it_writes_routes_to_a_species_zoo_builds():
    """A volume whose name matches nothing is a grey box, which is the
    defect this pass exists to reduce. Cover pieces may be boxes by nature;
    furniture may not."""
    unrouted = set()
    for role in ("office", "storage", "bay", "vault", "utility", "lobby",
                 "something_unmatched"):
        s = _spec(20.0, 16.0, role=role)
        level_design.furnish(s)
        for v in s["volumes"]:
            if prop_species.species_for_name(v["name"]) is None:
                unrouted.add(v["name"].rsplit("_", 2)[0])
    assert not unrouted, sorted(unrouted)


def test_a_cupboard_is_left_alone():
    s = _spec(2.5, 2.5)                         # 6.25 m2
    assert level_design.furnish(s) == 0


def test_the_same_seed_and_room_furnish_the_same_way():
    a, b = _spec(14.0, 12.0), _spec(14.0, 12.0)
    level_design.furnish(a)
    level_design.furnish(b)
    assert [(v["name"], v["x"], v["y"]) for v in a["volumes"]] == \
           [(v["name"], v["x"], v["y"]) for v in b["volumes"]]


def test_wall_furniture_stands_on_outside_walls_but_never_in_an_opening():
    """SUPERSEDED, kept above the result that replaced it. 0.122.0 asserted
    furniture stayed OFF exterior walls: a shelf run had stood across the door
    of `office`'s exec suite, because `_seed_clear` guards partitions and knew
    nothing about exterior openings. The ban emptied every hall whose long
    walls are exterior, which cold run 9044's brewery frame showed. The rule
    now is the real one: exterior walls are allowed, and no piece may overlap
    an opening plus its clearance."""
    s = _spec(12.0, 10.0, role="storage")
    s["footprint_x"], s["footprint_y"] = 12.0, 10.0      # the room IS the shell
    s["ext_walls"] = [
        {"wall": "S", "story": 0, "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2}]},
        {"wall": "E", "story": 0, "openings": [
            {"kind": "window", "pos": 0.1, "width": 1.0, "sill": 1.0}]}]
    level_design.furnish(s)
    clear = level_design._FURNISH_OPENING_CLEAR
    on_ext = 0
    for v in s["volumes"]:
        if abs(v["y"] + 5.0) < 1.0:                        # against S
            on_ext += 1
            assert abs(v["x"] - 0.0) >= v["size_x"] / 2 + 0.6 + clear - 1e-6, v
        if abs(v["x"] - 6.0) < 1.0:                        # against E
            on_ext += 1
            assert abs(v["y"] - 1.0) >= v["size_y"] / 2 + 0.5 + clear - 1e-6, v
    assert on_ext > 0, "no wall piece stood on an exterior wall at all"


def test_a_setback_storey_keeps_its_outside_walls_bare():
    """The one place the exclusion survives: with a setback the storey's
    extent is not the footprint, and the opening positions are not re-derived
    here, so guessing them would be the defect this replaced."""
    s = _spec(12.0, 10.0, role="storage")
    s["footprint_x"], s["footprint_y"] = 12.0, 10.0
    s["setbacks"] = [{"story": 1, "n": 1.0}]
    level_design.furnish(s)
    for v in s["volumes"]:
        if v["size_z"] >= level_design.shelter_height():
            edge = min(6.0 - abs(v["x"]), 5.0 - abs(v["y"]))
            assert edge > level_design._FURNISH_EXT_KEEPOUT + 0.2, v


def test_a_hall_is_furnished_sparser_than_an_office_but_not_capped_at_ten():
    """Cold run 9044's brewery hall, about 1,000 m2: 63 pieces at office
    density, 10 under the old cap, 25 now."""
    assert level_design._furnish_target(120.0) == 8
    assert level_design._furnish_target(160.0) == 10
    assert level_design._furnish_target(1000.0) == 25
    assert level_design._furnish_target(5000.0) == level_design._FURNISH_HALL_MAX


def test_a_table_brings_its_chairs_and_the_set_is_still_idempotent():
    """0.131.0: 0-4 chairs a table, from the seed, so the bound is four."""
    s = _spec(20.0, 16.0, role="lobby")
    s["rooms"][0]["id"] = "dining_room"
    first = level_design.furnish(s)
    chairs = [v for v in s["volumes"] if v["name"].startswith("chair_set_")]
    tables = [v for v in s["volumes"] if v["name"].startswith("table_")]
    assert tables and chairs, [v["name"] for v in s["volumes"]]
    assert len(chairs) <= 4 * len(tables)
    assert all(prop_species.species_for_name(c["name"]) == "chair" for c in chairs)
    assert level_design.furnish(s) == 0
    assert len(s["volumes"]) == first


#: Zoo's genome ranges for every species furnish routes to, as of Zoo 0.84.0,
#: ``species: (width, depth, height)`` as (min, max). Duplicated rather than
#: imported because Zoo is a separate repo -- the same reason
#: `material_kind.SKIN_KINDS` is a literal. A slot outside its species' range
#: is built as a plain box, so this is what "routes to a species" has to mean.
#: `test_the_ranges_are_zoo_s` below pins the literal to the genomes whenever
#: Zoo is beside this repo.
_ZOO_RANGES = {
    "desk": ((1.0, 12.0), (0.5, 6.0), (0.65, 1.3)),
    "chair": ((0.38, 12.0), (0.38, 2.0), (0.5, 1.1)),
    "table": ((0.6, 8.0), (0.6, 2.0), (0.4, 0.95)),
    "counter": ((0.8, 12.0), (0.5, 2.0), (0.85, 1.2)),
    "shelving": ((0.6, 20.0), (0.3, 1.4), (0.9, 4.5)),
    "filing_cabinet": ((0.35, 4.0), (0.5, 0.9), (0.7, 2.1)),
    "drop_safe": ((0.4, 1.2), (0.4, 1.0), (0.4, 1.5)),
    "water_tank": ((1.2, 3.0), (1.2, 3.0), (1.8, 4.5)),
    "carton_stack": ((0.4, 1.6), (0.3, 1.2), (0.3, 1.8)),
    "furnace": ((0.5, 1.4), (0.5, 1.4), (1.4, 4.0)),
    "dust_sheet": ((0.4, 3.2), (0.4, 1.6), (0.4, 2.2)),
    "pool_table": ((1.8, 2.8), (1.0, 1.6), (0.74, 0.86)),
    "booth_seat": ((0.9, 4.0), (0.55, 1.6), (0.7, 1.4)),
    "water_barrel": ((0.406, 0.87), (0.406, 0.87), (0.616, 1.32)),
    "pallet_stack": ((0.84, 1.8), (0.7, 1.5), (0.665, 1.425)),
    "litter_bin": ((0.48, 0.78), (0.48, 0.78), (0.8, 1.3)),
    "flat_top_grill": ((0.9, 1.6), (0.7, 1.0), (0.98, 1.15)),
    "queue_stanchion": ((0.28, 0.42), (0.28, 0.42), (0.9, 1.1)),
    "payphone": ((0.525, 1.05), (0.35, 0.7), (1.61, 3.22)),
    "vending_machine": ((0.7, 1.05), (0.6, 0.9), (1.6, 2.0)),
    "atm": ((0.5, 0.75), (0.4, 0.7), (1.2, 1.65)),
    # the club (Zoo 0.88.0)
    "club_stage": ((2.0, 14.0), (2.0, 8.0), (0.45, 5.0)),
    "cocktail_table": ((0.6, 0.9), (0.6, 0.9), (0.5, 1.1)),
    "club_chair": ((0.6, 0.95), (0.6, 0.9), (0.65, 0.95)),
    "bar_stool": ((0.36, 0.5), (0.36, 0.5), (0.6, 0.85)),
    "neon_sign": ((1.0, 3.0), (0.06, 0.25), (0.45, 1.2)),
    "crt_tv": ((0.35, 0.9), (0.35, 0.62), (0.3, 0.7)),
}
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zoo")


def _zoo_core():
    import pytest
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    import importlib
    return importlib.import_module("zoo_keeper.core.kit")


def test_every_piece_is_a_size_its_species_builds():
    """The name test above passed while every chair this pass wrote was a
    box: `chair` routes to the species by NAME, and at 0.45 m it was below
    the species' 0.5 m minimum, so Zoo built the fallback. Cold run 9045's
    hall frame showed a table between two wooden cubes. Routing by name and
    building as the species are two different claims; this is the second.

    0.131.0: over every size of every piece in `_PIECES` (a to-the-ceiling
    height is checked at the shortest and tallest storey the library has,
    3.0 and 6.5 m), where 0.123.1 read the six rows of `_FURNITURE`."""
    bad = []
    rows = []
    for name, p in level_design._PIECES.items():
        for w, d, h in p["sizes"]:
            if h is None:
                for sh in (3.0, 6.5):
                    spec = {"story_height": sh}
                    rows.append((name, w, d, min(level_design._clear_height(spec),
                                                 level_design._TO_CEILING_MAX)))
            else:
                rows.append((name, w, d, h))
    rows.append(("chair_set", 0.5, 0.5, level_design._CHAIR_H))
    for name, w, d, h in rows:
        sp = prop_species.species_for_name(name + "_room_1")
        rng = _ZOO_RANGES.get(sp)
        assert rng is not None, (name, sp)
        for label, v, (lo, hi) in zip(("width", "depth", "height"),
                                      (max(w, d), min(w, d), h), rng):
            if not lo - 1e-9 <= v <= hi + 1e-9:
                bad.append(f"{name} -> {sp}: {label} {v} outside {lo}-{hi}")
    assert not bad, bad


def test_the_ranges_are_zoo_s():
    """The literal above against the genomes it was copied from."""
    _zoo_core()
    import json as _json
    gdir = os.path.join(ZOO, "zoo_keeper", "genome", "species")
    for sp, rng in _ZOO_RANGES.items():
        g = _json.load(open(os.path.join(gdir, sp + ".json"), encoding="utf-8"))
        dims = g["dimensions"]
        got = tuple((dims[k]["min"], dims[k]["max"])
                    for k in ("width", "depth", "height"))
        assert got == rng, (sp, got, rng)


def test_a_room_id_cannot_hijack_its_furniture_into_another_species():
    """`prop_species` matches keywords anywhere in a name, in table order. In
    a room called `teller_line`, `chair_set_teller_line_1_1` routed to
    `teller_line` before `chair` was tried, and Zoo built the fallback box --
    17 of them on cold run 9046. Furniture names carry a crc32 tag of the
    room id instead, and a tag is `r` plus hex digits."""
    for rid in ("teller_line", "safe_room", "counter_area", "tank_room",
                "desk_pool", "station_1", "bar_back", "col_bay"):
        s = _spec(20.0, 16.0, role="lobby")
        s["rooms"][0]["id"] = rid
        level_design.furnish(s)
        for v in s["volumes"]:
            want = v["name"].split("_r")[0]
            got = prop_species.species_for_name(v["name"])
            assert got == prop_species.species_for_name(want + "_x_1"), \
                (rid, v["name"], got)
    # and no species keyword can occur inside a tag at ANY alignment. The tag
    # is `_r` then eight hex digits then `_`; a set-of-letters check was the
    # first spelling of this and wrongly flagged `bar_`, whose `r` would have
    # to be followed by `_` where a tag's `r` is followed by a hex digit.
    template = ["_", "r"] + [None] * 8 + ["_"]      # None: any hex digit
    hexd = set("0123456789abcdef")

    def fits(word, at):
        for i, ch in enumerate(word):
            slot = template[at + i]
            if (slot is None and ch not in hexd) or                     (slot is not None and ch != slot):
                return False
        return True
    for words, _sp in prop_species.PROP_SPECIES:
        for w in words:
            assert not any(fits(w, at) for at in range(len(template) - len(w) + 1)), w


def test_a_set_chair_faces_its_table_by_the_compass_convention():
    """Slot rotation is a compass bearing (N 0, E 90, S 180, W 270) turning a
    module's +Y onto it, and a chair's front is its -Y, so its front bearing
    is rot_z + 180. The walker, cold run 9046: chairs should face the table."""
    import math as _m
    s = _spec(20.0, 16.0, role="lobby")
    s["rooms"][0]["id"] = "dining_room"
    level_design.furnish(s)
    # a dining room's chairs belong to its tables and its bar's stools to the
    # bar; each faces its own host either way
    tables = {"_".join(v["name"].split("_")[-2:]): v for v in s["volumes"]
              if not v["name"].startswith("chair_set_")}
    checked = 0
    for c in s["volumes"]:
        if not c["name"].startswith("chair_set_"):
            continue
        # chair_set_<tag>_<host seq>_<j>: the host is <stem>_<tag>_<host seq>
        key = "_".join(c["name"].split("_")[2:4])
        t = tables.get(key)
        assert t is not None, (c["name"], sorted(tables))
        # 0.131.0 turns some chairs 10-20 degrees off square; the front
        # still points at the table.
        front = (c["rot_z"] + 180.0) % 360.0
        fx, fy = _m.sin(_m.radians(front)), _m.cos(_m.radians(front))
        tx, ty = t["x"] - c["x"], t["y"] - c["y"]
        assert fx * tx + fy * ty > 0, (c["name"], c["rot_z"], (tx, ty))
        checked += 1
    assert checked, "no set chairs were placed"


def test_nothing_it_places_wears_the_building_default():
    """The walker, cold run 9048: chairs wearing the floor-and-wall skin were
    nearly invisible, "making it easy to stumble into things". Every piece
    furnish and seed_cover place names its own material."""
    for role in ("office", "storage", "bay", "vault", "utility", "lobby",
                 "something_unmatched"):
        s = _spec(20.0, 16.0, role=role)
        s["default_material"] = "concrete"
        level_design.seed_cover(s)
        level_design.furnish(s)
        bare = [v["name"] for v in s["volumes"] if not v.get("material")]
        assert not bare, (role, bare)
        assert all(v["material"] != "concrete" for v in s["volumes"]), role
        declared = {m["id"] for m in s.get("materials", [])} | {"wood"}
        assert {v["material"] for v in s["volumes"]} <= declared, role


def test_wall_pieces_face_into_the_room():
    """ "Chairs shouldnt face walls like this where humans couldnt sit in
    them." A wall piece's front (its module's -Y) must point away from the
    wall it stands against. Front bearing = long-axis turn + rot_z + 180,
    compass convention; the long-axis turn is 90 when the piece is long in y."""
    import math as _m
    s = _spec(20.0, 16.0, role="lobby")
    level_design.furnish(s)
    x0, y0, x1, y1 = s["rooms"][0]["bounds"]
    checked = 0
    for v in s["volumes"]:
        if not v["name"].startswith(("chair_waiting", "counter_service")):
            continue
        long_turn = 90.0 if v["size_y"] > v["size_x"] else 0.0
        front = (long_turn + v.get("rot_z", 0.0) + 180.0) % 360.0
        fx, fy = _m.sin(_m.radians(front)), _m.cos(_m.radians(front))
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        assert fx * (cx - v["x"]) + fy * (cy - v["y"]) > 0, (v["name"], front)
        checked += 1
    assert checked, "no wall seating placed"


def test_a_wall_piece_stands_off_the_wall_face_not_inside_it():
    """Cold run 9052: waiting-chair backs coplanar with the wall's inner face,
    because the offset from a room bound (the wall's centreline) was a flat
    0.12 m against a 0.30 m wall. Every wall slot now clears the face."""
    import random
    import level_design as LD
    spec = {"footprint_x": 20.0, "footprint_y": 14.0, "wall_thick": 0.3,
            "partitions": [], "ext_walls": [], "stairs": [], "volumes": [],
            "markers": [], "ladders": []}
    room = {"id": "r", "story": 0, "bounds": [-10.0, -7.0, 0.0, 7.0]}
    slots = LD._wall_slots(spec, room, 2.0, 0.5, random.Random(1))
    assert slots
    face = spec["wall_thick"] / 2.0
    x0, y0, x1, y1 = room["bounds"]
    for (px, py, sx, sy, _rot) in slots:
        gaps = (px - sx / 2.0 - x0, x1 - (px + sx / 2.0),
                py - sy / 2.0 - y0, y1 - (py + sy / 2.0))
        assert min(gaps) >= face + 0.005 - 1e-9, (px, py, sx, sy, gaps)


# ---------------------------------------------------------------------------
# 0.131.0 -- a recipe per room kind. The walker, cold run 9052, in
# country_club_a01's wine cellar: "need a lot more species for this room, its
# just a bunch of chairs and tables with nothing on it, boring".
# ---------------------------------------------------------------------------

import json      # noqa: E402
import math      # noqa: E402
import re        # noqa: E402
import zlib      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

#: Pieces whose species has a face a body uses. Literal, not read from
#: `_PIECES`, so the rule can be asked of a library furnished before it.
#: A desk is not here: its front is its SITTER's side, which faces away.
_FRONTED = ("safe_floor", "cabinet_", "shelf_run", "rack_wine", "furnace",
            "water_heater", "vending", "atm", "payphone", "counter_",
            "workbench", "grill", "chair_waiting", "booth", "sofa")
_GEN = re.compile(r"^(?P<stem>[a-z_]+?)_(?P<tag>r[0-9a-f]{8})_\d+$")


def _front_bearing(v):
    """The compass bearing a volume's module front points at, by the rule
    `deli_counter` records the slot with: long side first, +90 when that
    side is y (`prop_species.long_axis_first`), then `rot_z`; the front is
    the module's -Y, so bearing + 180."""
    turned = (prop_species.species_for_name(v["name"]) is not None
              and v["size_y"] > v["size_x"] + 1e-9)
    return ((90.0 if turned else 0.0) + float(v.get("rot_z", 0.0)) + 180.0) % 360.0


def _faces_room(v, room):
    x0, y0, x1, y1 = room["bounds"]
    f = math.radians(_front_bearing(v))
    fx, fy = math.sin(f), math.cos(f)
    return fx * ((x0 + x1) / 2 - v["x"]) + fy * ((y0 + y1) / 2 - v["y"]) > 0


def _library(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def test_rooms_are_read_on_whole_tokens_id_first_then_role():
    """Substring matching sent `cellar_hall` to lobby counters ("hall") and
    `food_service` to workbenches ("service"); `store` matched nothing."""
    k = level_design._room_kind
    assert k({"id": "wine_cellar", "role": "objective_room", "story": -1}) == "wine_cellar"
    assert k({"id": "cellar_hall", "story": -1}) == "basement"
    assert k({"id": "under_hall", "story": -1}) == "basement"
    assert k({"id": "food_service"}) == "kitchen"
    assert k({"id": "back_store"}) == "storage"
    assert k({"id": "manager_office"}) == "office"
    assert k({"id": "count_room"}) == "vault"
    assert k({"id": "stairwell_north"}) == "corridor"
    # below grade and named nothing: a basement, ahead of the role
    assert k({"id": "north_wing", "role": "public_entry", "story": -1}) == "basement"
    # above grade and named nothing: the role's own tokens
    assert k({"id": "front_left_0", "role": "public_entry"}) == "lobby"
    assert k({"id": "teller_staff", "role": "staff_only"}) == "locker"
    # the level grammar's roles say nothing about furniture
    assert k({"id": "north_wing", "role": "open_floor"}) == "fallback"
    assert k({"id": "r0", "role": "connector"}) == "fallback"


def test_the_country_club_wine_cellar_is_not_tables_and_chairs():
    """The walker's room, off the library spec: 27 pieces of 2 species
    (chair 20, table 7) on 0.130.0."""
    d = _library("country_club_a01")
    room = next(r for r in d["rooms"] if r["id"] == "wine_cellar")
    tag = level_design._room_tag(room)
    mine = [v for v in d["volumes"] if f"_{tag}_" in v["name"]]
    species = [prop_species.species_for_name(v["name"]) for v in mine]
    assert None not in species, [v["name"] for v in mine]
    kinds = set(species)
    assert len(kinds) >= 5, sorted(kinds)
    seats_and_tables = sum(1 for s in species if s in ("chair", "table"))
    assert seats_and_tables * 2 < len(species), (seats_and_tables, len(species))


def test_a_piece_with_a_front_faces_into_its_room():
    """Safes, cabinets, furnaces, shelving and counters face the room, never
    a wall or the approach. bank_branch_a02's basement had a floor safe
    beside the new vault door showing its blank back to the approach: floor
    safes were written with no rotation, and a square piece on an east or
    west wall faced along it (`_front_turn`)."""
    wrong = []
    for rid, role, story in (("vault_west", "loot_room", -1),
                             ("utility_room", "utility", -1),
                             ("stock_room", "connector", 0),
                             ("lobby", "public_entry", 0),
                             ("kitchen", "connector", 0),
                             ("club_bar", "connector", 0),
                             ("mech_plant", "connector", 0),
                             ("wine_cellar", "objective_room", -1)):
        for w, d in ((20.0, 16.0), (9.0, 14.0), (30.0, 12.0)):
            s = _spec(w, d, role=role)
            s["rooms"][0].update(id=rid, story=story)
            level_design.furnish(s)
            room = s["rooms"][0]
            for v in s["volumes"]:
                if v["name"].startswith(_FRONTED) and not _faces_room(v, room):
                    wrong.append((rid, v["name"], v.get("rot_z"),
                                  v["size_x"], v["size_y"]))
    for name in ("bank_branch_a02", "bank_branch_a03", "bank_job",
                 "country_club_a01"):
        d = _library(name)
        rooms = {level_design._room_tag(r): r for r in d["rooms"]}
        for v in d["volumes"]:
            m = _GEN.match(v["name"])
            if m and m.group("tag") in rooms and v["name"].startswith(_FRONTED):
                if not _faces_room(v, rooms[m.group("tag")]):
                    wrong.append((name, v["name"], v.get("rot_z")))
    assert not wrong, wrong


def test_stock_follows_the_room_and_the_variant_is_the_name_s_crc32():
    """Zoo 0.84.0's contract: desks `office`, bar counters `bar`, kitchen
    counters `kitchen`, vault and count work tables `vault`, supply cabinets
    `storage`; `variant` = crc32(name) % 4, and only where the species has
    variants to give -- Zoo drops all three fields when one is not honoured."""
    want_stock = {"desk": "office", "counter_bar": "bar",
                  "counter_kitchen": "kitchen", "table_count": "vault",
                  "cabinet_supply": "storage"}
    seen = set()
    for rid in ("office", "club_bar", "kitchen", "count_room", "stock_room"):
        s = _spec(24.0, 16.0, role="connector")
        s["rooms"][0]["id"] = rid
        level_design.furnish(s)
        for v in s["volumes"]:
            m = re.match(r"^([a-z_]+?)_r[0-9a-f]{8}_", v["name"])
            stem = m.group(1)
            p = level_design._PIECES.get(stem)
            if p is None:
                assert stem == "chair_set" and not (set(v) & {"stock", "variant", "form"}), v
                continue
            assert v.get("stock") == want_stock.get(stem), v
            n = (zlib.crc32(v["name"].encode("utf-8")) & 0xFFFFFFFF) % 4
            assert v.get("variant", 0) == (n if p["variants"] else 0), v
            if v.get("stock"):
                seen.add(stem)
    assert seen == set(want_stock), seen


def test_zoo_honours_every_dressing_furnish_writes():
    """All or nothing is Zoo's rule (`kit.honour_dressing`): one field the
    species cannot take drops the other two with it, so a form, stock or
    variant written where it cannot be honoured is not merely ignored."""
    kit = _zoo_core()
    dropped = []
    for name, p in level_design._PIECES.items():
        if not (p["stock"] or p["form"] or p["variants"]):
            continue
        sp = prop_species.species_for_name(name + "_r00000000_1")
        for n in range(4 if p["variants"] else 1):
            slot = {"stock": p["stock"], "form": p["form"], "variant": n}
            _dress, why = kit.honour_dressing(slot, sp)
            if why:
                dropped.append((name, sp, slot, why))
    assert not dropped, dropped


def test_no_more_than_four_of_one_piece_and_size_and_three_sizes_a_building():
    import collections
    per_room = collections.Counter()
    sizes = collections.defaultdict(set)
    s = {"name": "palette", "seed": 7, "story_height": 3.6, "footprint_x": 90.0,
         "footprint_y": 60.0, "rooms": [], "volumes": [], "partitions": [],
         "stairs": []}
    for i, rid in enumerate(("stock_room", "back_store", "office", "kitchen",
                             "basement", "upper_hall")):
        x = -42.0 + i * 14.0
        s["rooms"].append({"id": rid, "story": 0, "role": "connector",
                           "bounds": [x, -28.0, x + 13.0, 28.0]})
    level_design.furnish(s)
    for v in s["volumes"]:
        m = _GEN.match(v["name"])
        if not m or m.group("stem") == "chair_set":
            continue
        dims = (max(v["size_x"], v["size_y"]), min(v["size_x"], v["size_y"]),
                v["size_z"])
        per_room[(m.group("tag"), m.group("stem"), dims)] += 1
        sizes[m.group("stem")].add(dims)
    assert per_room and max(per_room.values()) <= level_design._SAME_PIECE_MAX, \
        per_room.most_common(3)
    assert max(len(x) for x in sizes.values()) <= level_design._PALETTE, sizes


def test_clusters_pack_small_pieces_a_hand_apart():
    """2-4 pieces 0.3-0.8 m apart: every cluster piece but a lone litter bin
    has a neighbour within 0.8 m, edge to edge, and none stands taller than
    `_CLUSTER_MAX_H` in the middle of the floor."""
    s = _spec(30.0, 24.0, role="connector")
    s["rooms"][0].update(id="storage_basement", story=-1)
    level_design.furnish(s)
    cl = [v for v in s["volumes"]
          if level_design._PIECES.get(re.match(r"^([a-z_]+?)_r[0-9a-f]{8}_", v["name"]).group(1),
                                      {}).get("where") == "cluster"]
    assert len(cl) >= 4, [v["name"] for v in s["volumes"]]

    def gap(a, b):
        gx = abs(a["x"] - b["x"]) - (a["size_x"] + b["size_x"]) / 2
        gy = abs(a["y"] - b["y"]) - (a["size_y"] + b["size_y"]) / 2
        return max(gx, gy)
    lonely = []
    for a in cl:
        if a["name"].startswith("litter_bin"):
            continue
        near = sorted(gap(a, b) for b in cl if b is not a)
        if not near or near[0] > 0.8 + 0.02 or near[0] < -0.02:
            lonely.append((a["name"], [round(g, 2) for g in near[:2]]))
    assert not lonely, lonely
    for v in cl:
        assert v["size_z"] <= level_design._CLUSTER_MAX_H


def test_a_table_seats_none_to_four_and_a_turned_chair_turns_a_little():
    import collections
    per_table = collections.Counter()
    turns = []
    tables = 0
    for seed in range(12):
        s = _spec(24.0, 18.0, role="connector", seed=seed)
        s["rooms"][0]["id"] = "dining_room"
        level_design.furnish(s)
        tables += sum(1 for v in s["volumes"] if v["name"].startswith("table_dining"))
        for v in s["volumes"]:
            if v["name"].startswith("chair_set_"):
                per_table[(seed,) + tuple(v["name"].split("_")[2:4])] += 1
                off = v["rot_z"] % 90.0
                turns.append(min(off, 90.0 - off))
    assert tables and max(per_table.values()) <= 4
    assert all(t == 0.0 or 10.0 - 1e-6 <= t <= 20.0 + 1e-6 for t in turns), turns
    assert any(t > 0 for t in turns) and any(t == 0 for t in turns)


def test_a_to_the_ceiling_piece_stops_short_of_the_ceiling():
    """Zoo's furnace and water heater run their flue to the slot's top; the
    slot reaches the ceiling less `_CEILING_AIR`, never through it."""
    for sh, roof in ((3.0, None), (3.8, 0.5), (6.5, None)):
        s = _spec(20.0, 16.0, role="utility", story_height=sh)
        s["rooms"][0].update(id="boiler_room", story=-1)
        if roof:
            s["roof_thick"] = roof
        level_design.furnish(s)
        tall = [v for v in s["volumes"] if v.get("form") in ("furnace", "water_heater")]
        assert tall, [v["name"] for v in s["volumes"]]
        ceiling = -1 * sh + sh - max(0.3, roof or 0.0)
        for v in tall:
            top = v["z"] + v["size_z"] / 2
            assert top <= ceiling - level_design._CEILING_AIR + 1e-6, (sh, v)
            assert v["size_z"] <= level_design._TO_CEILING_MAX


def test_every_furnished_piece_in_the_library_routes_to_a_species():
    """Over the committed library: a generated piece that routes to nothing
    is a grey box, which is the defect furnishing exists to reduce."""
    import glob
    unrouted = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
        for v in d.get("volumes", []):
            m = re.match(r"^(.+)_(r[0-9a-f]{8})_\d+(_\d+)?$", v["name"])
            if m and m.group(2) in tags and prop_species.species_for_name(v["name"]) is None:
                unrouted.append((os.path.basename(p), v["name"]))
    assert not unrouted, unrouted[:10]


def test_the_migration_takes_back_only_what_furnish_wrote_and_is_idempotent():
    import copy
    import migrate_furnish_recipes as mig
    d = _library("bank_branch_a02")
    tags = {level_design._room_tag(r) for r in d["rooms"]}
    authored = [v["name"] for v in d["volumes"]
                if not mig.furnished_by_this_pass(v, tags)]
    once = copy.deepcopy(d)
    mig.migrate(once)
    twice = copy.deepcopy(once)
    mig.migrate(twice)
    assert json.dumps(once, sort_keys=True) == json.dumps(twice, sort_keys=True)
    assert [v["name"] for v in once["volumes"]][:len(authored)] == authored
    # an authored name that merely looks tagged, with no such room, is kept
    fake = {"name": "desk_r00000000_1", "x": 0, "y": 0, "z": 0.4,
            "size_x": 1.6, "size_y": 0.8, "size_z": 0.75}
    assert not mig.furnished_by_this_pass(fake, tags)


def test_a_room_does_not_furnish_the_room_inside_it():
    """0.130.0's vault room stands inside `vault_west`; the outer room's
    pieces keep off its floor, which the vault room furnishes itself."""
    d = _library("bank_branch_a02")
    rooms = {level_design._room_tag(r): r for r in d["rooms"]}
    vault = next(r for r in d["rooms"] if r["id"] == "vault")
    vx0, vy0, vx1, vy1 = vault["bounds"]
    trespass = []
    for v in d["volumes"]:
        m = _GEN.match(v["name"]) or re.match(r"^(chair_set)_(r[0-9a-f]{8})_\d+_\d+$", v["name"])
        if not m or rooms.get(m.group(2)) in (None, vault):
            continue
        if rooms[m.group(2)].get("story", 0) != vault.get("story", 0):
            continue
        if (v["x"] + v["size_x"] / 2 > vx0 and v["x"] - v["size_x"] / 2 < vx1
                and v["y"] + v["size_y"] / 2 > vy0 and v["y"] - v["size_y"] / 2 < vy1):
            trespass.append(v["name"])
    assert not trespass, trespass

