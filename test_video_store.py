"""A 1997 video rental store (0.171.0).

The walker's queue, 2026-09-29: "a new building type: a VHS movie rental
store"; 2026-10-02: MACDADE MOVIES, the curtained back room "suggestive
only", built from the era. Zoo 1.43.0 draws the racks. Held here: the preset
is registered and survives being named by somebody else; its rooms are the
kinds they should be and nobody else's are; the racks the preset authors are
Zoo's, inside its ranges, inside their rooms, clear of each other and of
every door, with an aisle a body walks between them; the back room's racks
are the back room's and no others are; and the library carries the building.
"""
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agent_contract            # noqa: E402
import level_design              # noqa: E402
import presets                   # noqa: E402
import prop_species              # noqa: E402

#: Zoo 1.43.0's `video_rack` genome: width, depth, height.
ZOO_RANGE = ((1.0, 8.0), (0.35, 1.2), (1.2, 2.2))
ZOO_FORMS = ("wall", "island", "adult")
ZOO_VARIANTS = 6


def _store(enrich=True, **kw):
    return presets.make("video_store", enrich=enrich, **kw)


def _racks(spec):
    return [v for v in spec["volumes"] if v["name"].startswith(("tape_wall", "tape_island"))]


def _rect(v):
    return (v["x"] - v["size_x"] / 2.0, v["y"] - v["size_y"] / 2.0,
            v["x"] + v["size_x"] / 2.0, v["y"] + v["size_y"] / 2.0)


def _room_of(spec, v):
    for r in spec["rooms"]:
        x0, y0, x1, y1 = r["bounds"]
        if x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1:
            return r
    raise AssertionError(v["name"])


def test_the_preset_is_registered_one_storey_and_carries_its_name():
    assert presets.REGISTRY["video_store"] is presets.video_store
    spec = _store(enrich=False, name="lf_block_7_9080")
    assert spec["preset"] == "video_store" and spec["n_stories"] == 1
    assert spec["stairs"] == [] and spec["ladders"] == []
    # named by somebody else, it is still a video store
    assert "video_store" in level_design.club_building_id(spec)


def test_its_rooms_are_the_kinds_they_should_be_and_nobody_elses_are():
    spec = _store(enrich=False)
    b = level_design.club_building_id(spec)
    kinds = {r["id"]: level_design._room_kind(r, b) for r in spec["rooms"]}
    assert kinds == {"sales_floor": "video_store", "stockroom": "storage",
                     "back_room": "video_back"}, kinds
    # the same room ids in another building are not a video store's
    for other in ("supermarket_a01", "card_shop_a01 card_shop", "gas_station_a02", None):
        for rid in ("sales_floor", "back_room"):
            assert level_design.video_store_room_kind({"id": rid}, other) is None
            assert not str(level_design._room_kind({"id": rid, "story": 0}, other)).startswith("video")
    for kind in ("video_store", "video_back"):
        r = level_design._RECIPES[kind]
        assert not {"tape_wall", "tape_island"} & (set(r["anchors"]) | set(r["wall"]) | set(r["floor"]))


def test_every_rack_is_zoo_s_at_a_size_and_a_form_it_builds():
    spec = _store(enrich=False)
    racks = _racks(spec)
    forms = [v["form"] for v in racks]
    assert forms.count("wall") == 8 and forms.count("island") == 8 and forms.count("adult") == 3
    assert len({v["name"] for v in racks}) == len(racks)
    mats = {m["id"] for m in spec["materials"]}
    for v in racks:
        assert prop_species.species_for_name(v["name"]) == "video_rack", v["name"]
        assert v["form"] in ZOO_FORMS and 0 <= v["variant"] < ZOO_VARIANTS, v
        dims = (max(v["size_x"], v["size_y"]), min(v["size_x"], v["size_y"]), v["size_z"])
        for got, (lo, hi) in zip(dims, ZOO_RANGE):
            assert lo <= got <= hi, (v["name"], dims)
        assert v["material"] in mats and v["collision"] == "convex"
        assert abs(v["z"] - v["size_z"] / 2.0) < 1e-9          # stands on the floor
    # and the checkout is a counter, not a rack
    assert prop_species.species_for_name("counter_checkout") == "counter"


def test_the_back_rooms_racks_are_the_back_rooms_and_no_others_are():
    spec = _store(enrich=False)
    for v in _racks(spec):
        room = _room_of(spec, v)["id"]
        assert (v["form"] == "adult") == (room == "back_room"), (v["name"], room)
        assert room in ("sales_floor", "back_room"), (v["name"], room)


def test_a_wall_rack_stands_against_a_wall_facing_the_room():
    spec = _store(enrich=False)
    wt = spec["wall_thick"]
    for v in _racks(spec):
        if v["form"] == "island":
            continue
        x0, y0, x1, y1 = _room_of(spec, v)["bounds"]
        rx0, ry0, rx1, ry1 = _rect(v)
        long_x = v["size_x"] >= v["size_y"]
        turned = abs(float(v.get("rot_z") or 0.0) - 180.0) < 1e-6
        # its front: long in x faces -y, long in y faces -x, 180 turns it
        fx, fy = (0.0, 1.0 if turned else -1.0) if long_x else (1.0 if turned else -1.0, 0.0)
        # its BACK is within a wall's half thickness and a finger of the
        # room's edge on the side its front does not face
        back = {(0.0, -1.0): y1 - ry1, (0.0, 1.0): ry0 - y0,
                (-1.0, 0.0): x1 - rx1, (1.0, 0.0): rx0 - x0}[(fx, fy)]
        assert abs(back - (wt / 2.0 + 0.01)) < 1e-6, (v["name"], back)


def test_no_two_solids_overlap_and_every_gap_is_shut_or_an_aisle():
    """Two racks are either one run (2 cm apart, end to end) or have an
    aisle a body walks between them: nothing in between, which is a slot a
    capsule wedges into."""
    spec = _store(enrich=False)
    aisle = agent_contract.min_corridor_width()
    solids = _racks(spec) + [v for v in spec["volumes"] if v["name"] == "counter_checkout"]
    for a, b in itertools.combinations(solids, 2):
        if _room_of(spec, a) is not _room_of(spec, b):
            continue
        ax0, ay0, ax1, ay1 = _rect(a)
        bx0, by0, bx1, by1 = _rect(b)
        dx = max(bx0 - ax1, ax0 - bx1, 0.0)
        dy = max(by0 - ay1, ay0 - by1, 0.0)
        assert dx > 0 or dy > 0, (a["name"], b["name"])            # no overlap
        gap = max(dx, dy) if (dx == 0 or dy == 0) else (dx * dx + dy * dy) ** 0.5
        assert gap <= 0.021 or gap >= aisle - 1e-9, (a["name"], b["name"], round(gap, 3))


def test_every_door_is_clear_of_every_rack():
    spec = _store(enrich=False)
    hx, hy = spec["footprint_x"] / 2.0, spec["footprint_y"] / 2.0
    doors = []
    for w in spec["ext_walls"]:
        for o in w["openings"]:
            if o["kind"] != "door":
                continue
            u = o["pos"] * (spec["footprint_x"] if w["wall"] in "SN" else spec["footprint_y"])
            doors.append({"S": (u, -hy), "N": (u, hy), "W": (-hx, u), "E": (hx, u)}[w["wall"]])
    for p in spec["partitions"]:
        for o in p["openings"]:
            u = (p["start"] + p["end"]) / 2.0 + o["pos"] * (p["end"] - p["start"])
            doors.append((u, p["pos"]) if p["axis"] == "X" else (p["pos"], u))
    assert len(doors) == 5
    reach = agent_contract.min_door_width()
    for dx, dy in doors:
        for v in _racks(spec) + [x for x in spec["volumes"] if x["name"] == "counter_checkout"]:
            x0, y0, x1, y1 = _rect(v)
            gx = max(x0 - dx, dx - x1, 0.0)
            gy = max(y0 - dy, dy - y1, 0.0)
            assert (gx * gx + gy * gy) ** 0.5 >= reach, (v["name"], (dx, dy))


def test_the_back_room_has_two_ways_in():
    spec = _store(enrich=False)
    x0, y0, x1, y1 = next(r["bounds"] for r in spec["rooms"] if r["id"] == "back_room")
    ways = 0
    for p in spec["partitions"]:
        for o in p["openings"]:
            u = (p["start"] + p["end"]) / 2.0 + o["pos"] * (p["end"] - p["start"])
            at = (u, p["pos"]) if p["axis"] == "X" else (p["pos"], u)
            if x0 - 1e-6 <= at[0] <= x1 + 1e-6 and y0 - 1e-6 <= at[1] <= y1 + 1e-6:
                ways += 1
    assert ways == 2


def test_the_furnisher_adds_no_rack_and_keeps_the_authored_ones():
    raw, done = _store(enrich=False), _store(enrich=True)
    assert [v for v in _racks(done)] == _racks(raw)
    posters = [v for v in done["volumes"] if v["name"].startswith("poster_wall_store_")]
    assert len(posters) >= 1
    assert not [v for v in done["volumes"] if v["name"].startswith("wall_tv")]


def test_the_library_carries_the_building():
    p = os.path.join(HERE, "specs", "video_store_a01.json")
    with open(p, encoding="utf-8") as f:
        lib = json.load(f)
    assert lib["preset"] == "video_store" and lib["name"] == "video_store_a01"
    assert [v["name"] for v in _racks(lib)] == [v["name"] for v in _racks(_store(enrich=False))]
    lp = os.path.join(HERE, "build", "video_store_a01.lights.json")
    if os.path.exists(lp):
        with open(lp, encoding="utf-8") as f:
            signs = [a for a in json.load(f)["anchors"] if a["type"] == "sign"]
        assert len(signs) == 1 and signs[0]["business"] == level_design.club_building_id(lib)
