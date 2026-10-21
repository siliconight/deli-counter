"""A corner store's selling floor stands its aisle gondolas in ROWS (0.247.0, the factory's roadmap 148).

The look review of 2026-10-19 on deli_a03's market aisles, among six other rooms: "Too sparse". That room was 300 m2
with 5.7 % of its floor under anything standing -- two authored aisle shelves, a counter, a cabinet, cartons and a
bin. A corner store's selling floor (`level_design.is_corner_store_floor`) now lays rows of Zoo's `snack_gondola`
down its long axis -- or along its own aisles, at their depth and on their line, when it has them -- with an aisle
(`island_aisle_width`) round every gondola, until a quarter of the floor stands under furniture or nothing more clears.

The aisle checks here are re-derived from the geometry in this file -- rectangles and the gaps between them -- not
`_row_clear` asked a second time.
"""
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design as L  # noqa: E402
import migrate_store_gondolas  # noqa: E402
import prop_species  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
#: The selling floors that stand rows, measured when 0.247.0 was written: six delis' market aisles and eight stores'
#: sales floors. `gs_corner_station` names neither `gas` nor `fuel` and is not among them (`_CORNER_STORE_IDS`).
CORNER_FLOORS = {
    "corner_deli_heist_01": "market_aisles", "cr_deli": "market_aisles", "deli_a01": "market_aisles",
    "deli_a02": "market_aisles", "deli_a03": "market_aisles", "night_deli": "market_aisles",
    "convenience_store_a01": "sales_floor", "cr_gas": "sales_floor", "fuel_stop_heist": "sales_floor",
    "gas_station": "sales_floor", "gas_station_a01": "sales_floor", "gas_station_a02": "sales_floor",
    "gas_street": "sales_floor", "stop_n_go": "sales_floor",
}


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _room(spec, rid):
    (room,) = [r for r in spec["rooms"] if r["id"] == rid]
    return room


def _gondolas(spec, room):
    tag = "_%s_" % L._room_tag(room)
    return [v for v in spec["volumes"] if v["name"].startswith("gondola_aisle" + tag)]


def _rect(v):
    hx, hy = float(v["size_x"]) / 2.0, float(v["size_y"]) / 2.0
    return (float(v["x"]) - hx, float(v["y"]) - hy, float(v["x"]) + hx, float(v["y"]) + hy)


def _gap(a, b):
    """Clear plan distance between two rectangles, corner to corner the diagonal."""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def _walls(spec, story):
    """Every wall a body walks beside on `story`, as the rectangle the builder stands: the footprint's four exterior
    walls and the storey's partitions, `wall_thick` thick and centred on their lines."""
    hx, hy = spec.get("footprint_x", 20) / 2.0, spec.get("footprint_y", 20) / 2.0
    t = float(spec.get("wall_thick", 0.3))
    out = [(-hx, hy - t / 2, hx, hy + t / 2), (-hx, -hy - t / 2, hx, -hy + t / 2),
           (hx - t / 2, -hy, hx + t / 2, hy), (-hx - t / 2, -hy, -hx + t / 2, hy)]
    for p in spec.get("partitions", []):
        if p.get("story", 0) != story:
            continue
        s, e = min(p["start"], p["end"]), max(p["start"], p["end"])
        out.append((p["pos"] - t / 2, s, p["pos"] + t / 2, e) if p["axis"] == "Y"
                   else (s, p["pos"] - t / 2, e, p["pos"] + t / 2))
    return out


def _standing(spec, story, skip):
    """Every volume with collision that reaches a body's height on `story`, but `skip`."""
    sh = L._story_height(spec)
    floor = story * sh
    for v in spec["volumes"]:
        if v is skip or v.get("collision") == "none":
            continue
        z, h = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
        if z + h / 2.0 > floor + 0.05 and z - h / 2.0 < floor + 2.0:
            yield v


def test_the_aisle_gondola_is_a_snack_gondola_in_its_own_kind():
    assert prop_species.species_for_name("gondola_aisle_r00000000_1") == "snack_gondola"
    assert L._prop_material({"materials": []}, "gondola_aisle") == "metal_painted"
    p = L._PIECES["gondola_aisle"]
    # both long faces are shopped in one module, so one volume is the island; capped like every island, a guard the
    # library's rows stay under (the most any floor stands is 12)
    assert p["where"] == "island" and not p["twin"] and p["variants"] and p["most"] == 16


def test_a_gondola_in_a_row_is_cover_and_never_shelter():
    """Furnish stands nothing mid-floor at shelter height: a row is cover a body crouches behind and an eye sees over."""
    lo, hi = L.cover_break_height(), L.shelter_height()
    for w, d, h in L._PIECES["gondola_aisle"]["sizes"]:
        assert lo <= h < hi, (w, d, h, lo, hi)


def test_which_floors_are_a_corner_store_s():
    yes = [(b, rid) for b, rid in CORNER_FLOORS.items()] + [("lf_restaurant_row_001_9003 corner_deli",
                                                            "market_aisles")]
    no = [("deli_a03", "customer_floor"), ("deli_a03", "kitchen"), ("supermarket_a01", "sales_floor"),
          ("supermarket_a02", "mezz_floor"), ("pharmacy_a01", "retail_floor"), ("warehouse_a02", "north_aisles"),
          ("self_storage_a01", "mid_aisle"), ("market_hall_a01", "stall_floor"), ("gs_corner_station", "sales_floor"),
          ("arena_a01", "event_floor"), ("pawn_shop_a01", "shop_floor"), ("office", "floor_1")]
    for b, rid in yes:
        assert L.is_corner_store_floor({"id": rid}, b), (b, rid)
    for b, rid in no:
        assert not L.is_corner_store_floor({"id": rid}, b), (b, rid)


def test_the_library_s_corner_stores_stand_rows_and_no_other_room_does():
    """Every corner store floor holds gondolas, all one way and one length a room; no other room holds one."""
    found = {}
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        b = L.club_building_id(d)
        for room in d.get("rooms") or []:
            g = _gondolas(d, room)
            if not g:
                continue
            assert L.is_corner_store_floor(room, b) and L._room_kind(room, b) == "shop_floor", (name, room["id"])
            assert len({v["size_x"] >= v["size_y"] for v in g}) == 1, (name, "two ways")
            assert len({max(v["size_x"], v["size_y"]) for v in g}) == 1, (name, "two lengths")
            found[name] = room["id"]
    assert found == CORNER_FLOORS


def test_every_gondola_keeps_an_aisle_round_it():
    """An aisle (`island_aisle_width`, the contract's door width) between any two gondolas of a room's rows and
    between every gondola and every wall's face; and no standing piece nearer than furnish's own 0.9 m margin -- the
    pieces placed after the rows keep that one, what stood before them keeps the aisle."""
    aisle = L.island_aisle_width()
    for name, rid in CORNER_FLOORS.items():
        d = _spec(name)
        room = _room(d, rid)
        story = room.get("story", 0)
        g = _gondolas(d, room)
        walls = _walls(d, story)
        for v in g:
            r = _rect(v)
            for w in walls:
                assert _gap(r, w) >= aisle - 1e-6, (name, v["name"], "wall", round(_gap(r, w), 3))
            for u in _standing(d, story, v):
                gap = _gap(r, _rect(u))
                floor_ = aisle if u["name"].startswith("gondola_aisle_r") else 0.9
                assert gap >= floor_ - 1e-6, (name, v["name"], u["name"], round(gap, 3))


def test_no_gondola_stands_in_a_door_s_approach():
    """Furnish keeps a piece 1.5 m from every opening's centre, asked of squares down its length; whatever the
    sampling, no gondola's rectangle comes within an aisle of an opening's centre."""
    aisle = L.island_aisle_width()
    for name, rid in CORNER_FLOORS.items():
        d = _spec(name)
        room = _room(d, rid)
        story = room.get("story", 0)
        hx, hy = d.get("footprint_x", 20) / 2.0, d.get("footprint_y", 20) / 2.0
        centres = []
        for w in d.get("ext_walls", []):
            if w.get("story", 0) != story:
                continue
            run = d.get("footprint_x", 20) if w["wall"] in ("N", "S") else d.get("footprint_y", 20)
            for op in w.get("openings", []):
                u = op.get("pos", 0.0) * run
                centres.append({"N": (u, hy), "S": (u, -hy), "E": (hx, u), "W": (-hx, u)}[w["wall"]])
        for p in d.get("partitions", []):
            if p.get("story", 0) != story:
                continue
            for op in p.get("openings", []):
                u = p["start"] + (op.get("pos", 0.0) + 0.5) * abs(p["end"] - p["start"])
                centres.append((p["pos"], u) if p["axis"] == "Y" else (u, p["pos"]))
        assert centres, name
        for v in _gondolas(d, room):
            r = _rect(v)
            for cx, cy in centres:
                assert _gap(r, (cx, cy, cx, cy)) >= aisle - 1e-6, (name, v["name"], (cx, cy))


def test_the_rows_continue_a_room_s_own_aisles():
    """deli_a03's two authored aisles (x -2.0 and 2.5, 1.0 m deep, renamed `gondola_aisle_01` and `_02`) are on the
    rows' grid: each has a row gondola on its line, at its depth."""
    d = _spec("deli_a03")
    room = _room(d, "market_aisles")
    own = [v for v in d["volumes"] if v["name"] in ("gondola_aisle_01", "gondola_aisle_02")]
    assert len(own) == 2
    g = _gondolas(d, room)
    for v in own:
        line = [u for u in g if abs(u["x"] - v["x"]) < 1e-6 and min(u["size_x"], u["size_y"]) == v["size_x"]]
        assert line, v["name"]


def test_the_rows_fill_the_floor():
    """A regression detector, not a target: measured when 0.247.0 was written, every corner store floor stood 19.2
    to 23.1 % of its floor under furniture after its rows, from 5.4 to 13.4 % before them. Since 0.250.0 reserves a
    floor's routes before its rows (`protected_routes`), 17.2 to 22.1 % -- and the walker's band, 2026-10-21, is
    12 to 25 %: rooms neither crowded nor barren."""
    for name, rid in CORNER_FLOORS.items():
        d = _spec(name)
        share = L.room_floor_share(d, _room(d, rid))
        assert 0.17 <= share <= 0.25, (name, share)


def test_a_deli_is_a_store_to_the_gondola_migration():
    assert migrate_store_gondolas.is_store(["front_register_counter"])
    assert migrate_store_gondolas.is_store(["register_counter"])
    assert not migrate_store_gondolas.is_store(["the_deli_counter", "checkout_lane_1"])
    import presets
    src = open(presets.__file__, encoding="utf-8").read()
    assert "aisle_shelf_0" not in src
