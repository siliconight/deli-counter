"""A room holding an objective or loot marker keeps its dressing off its routes (0.251.0, the factory's roadmap 288).

The factory's census of what furnishing costs a route (`docs/findings/furnish_route_cost/` at the factory root), given
an arm that strips only furnish's dressing -- the walker's guide's own measure, dressing over the functional build --
found eight routes over the library that the dressing made more than 10 % longer, seven of them one route in an
objective room, its door to its marker: one to four carton piles, pallets or dust sheets in rooms of 97 to 240 m2 that
stand 3 to 7 % under furniture. `reserves_routes` now says what keeps off a room's routes -- "all" on a corner store's
floor (0.250.0), "dressing" in a room holding a marker -- and the shelter pass keeps its piece off them where it can.
Measured over the 50 specs that moved: the dressing's detours over 10 % 7 -> 0, the routes it narrows to single file
37 -> 5. Refuted, kept: every floor piece kept off a marker room's routes -- 47 rooms, 45 already under the walker's
12 % band, lost 45 pieces, and twin_a01's front_right_1 both of its own and the shelter they gave; and the shelter
piece kept strictly off them -- the pawn_shop preset's safe_room lost its shelter.
"""
import copy
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design as L  # noqa: E402
import migrate_furnish_recipes as M  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _library():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if d.get("rooms"):
            yield os.path.basename(p)[:-5], d


def _holds_marker(d, room):
    """Asked through the endpoints a route is found between, which 0.250.0 has too."""
    return any(kind in ("objective", "loot") for kind, _l, _x, _y in L.room_route_endpoints(d, room))


def _dressing_stems(room, building):
    """A stem furnish places only as a cluster in this room's kind -- what the census calls dressing."""
    kind = L._room_kind(room, building)
    recipe = L._RECIPES[kind]
    pools = list(recipe.get("clusters") or ())
    if room.get("story", 0) < 0 and kind not in ("basement", "vault", "corridor", "wine_cellar"):
        pools.append(L._BASEMENT_CLUSTER)
    clustered = {s for pool, _lo, _hi in pools for s in pool}
    functional = set()
    for key in ("anchors", "wall", "floor", "fixtures"):
        functional |= set(recipe.get(key) or ())
    return clustered - functional


def test_a_room_says_what_keeps_off_its_routes():
    """Every floor piece off a corner store's routes, the clusters off a marker room's, nothing reserved elsewhere."""
    d = _load("deli_a03")
    b = L.club_building_id(d)
    rooms = {r["id"]: r for r in d["rooms"]}
    assert L.reserves_routes(d, rooms["market_aisles"], b) == "all"
    assert L.reserves_routes(d, rooms["apartment_hideout"], b) == "dressing"
    assert L.holds_route_marker(d, rooms["apartment_hideout"])
    plain = [r for r in d["rooms"] if not _holds_marker(d, r) and not L.is_corner_store_floor(r, b)]
    assert plain and all(L.reserves_routes(d, r, b) == "" for r in plain), [r["id"] for r in plain]


def test_no_dressing_stands_on_a_marker_rooms_routes():
    """THE LIBRARY AS SHIPPED. In every room holding an objective or loot marker, no piece of furnish's dressing stands
    within half `two_abreast_width()` of a route the room reserves, allowing the half centimetre a written position may
    move. On 0.250.0 the census's seven dressing detours stood exactly there."""
    on, checked = [], 0
    for name, d in _library():
        b = L.club_building_id(d)
        bare = L.unfurnished(copy.deepcopy(d))
        for room in d["rooms"]:
            if not _holds_marker(d, room) or L.is_corner_store_floor(room, b):
                continue
            stems, tag = _dressing_stems(room, b), L._room_tag(room)
            mine = []
            for v in d["volumes"]:
                m = M._GENERATED.match(v["name"])
                if m and m.group("tag") == tag and m.group("stem") in stems:
                    mine.append(v)
            if not mine:
                continue
            routes = L.protected_routes(bare, room)
            checked += len(mine)
            on += [(name, v["name"]) for v in mine
                   if L.on_protected_route(routes, v["x"], v["y"], v["size_x"] - 0.01, v["size_y"] - 0.01)]
    assert checked, "no dressing found in any marker room: the test asks nothing"
    assert not on, on[:20]


def _stripped_room(name, rid):
    """A spec with one room stripped of furnish's pieces and the shelter pass's, so the room needs shelter whatever
    version furnished it."""
    d0 = _load(name)
    room = next(r for r in d0["rooms"] if r["id"] == rid)
    tag = L._room_tag(room)
    d0["volumes"] = [v for v in d0["volumes"] if not v["name"].endswith("_" + rid + "_shelter")
                     and not (M._GENERATED.match(v["name"]) and "_" + tag + "_" in v["name"])]
    return d0, room


def _sheltered(d0, rid, routes, monkeypatch):
    """The shelter pass run on a copy of `d0`, the room `rid` reserving `routes`; its shelter pieces."""
    monkeypatch.setattr(L, "protected_routes", lambda spec, rm: routes if rm["id"] == rid else [])
    d = copy.deepcopy(d0)
    L.seed_cover(d)
    return [v for v in d["volumes"] if v["name"].endswith("_" + rid + "_shelter")]


def _through(room, piece):
    """A thin route (half 0.30 m) across the room through where `piece` stands."""
    x0, _y0, x1, _y1 = room["bounds"]
    return [([(x0, piece["y"]), (x1, piece["y"])], 0.30)]


def test_the_shelter_pass_keeps_off_a_rooms_routes_where_it_can(monkeypatch):
    """`seed_cover`'s shelter piece keeps off a room's reserved routes as furnish's pieces do. apartment_walkup_a02's
    safe_flat, stripped: asked no route, the pass stands its crate stack at one spot; given a route through that spot,
    it stands it elsewhere, off the route. On 0.250.0, which asks no route, the crate stands on it."""
    d0, room = _stripped_room("apartment_walkup_a02", "safe_flat")
    free = _sheltered(d0, "safe_flat", [], monkeypatch)
    assert len(free) == 1, "asked no route the room is sheltered"
    planted = _through(room, free[0])
    moved = _sheltered(d0, "safe_flat", planted, monkeypatch)
    assert len(moved) == 1, "a room keeps its shelter"
    v = moved[0]
    assert not L.on_protected_route(planted, v["x"], v["y"], v["size_x"] - 0.01, v["size_y"] - 0.01), v


def test_a_room_with_no_spot_off_its_routes_keeps_its_shelter(monkeypatch):
    """twin_a01's front_right_1 has one clear spot for a crate stack. With a route through it, the pass stands the
    crate there rather than leave a room both sides see over everything in: kept strictly off its routes, the
    pawn_shop preset's safe_room lost its shelter and `test_cover_breaks_sightlines` failed on it."""
    d0, room = _stripped_room("twin_a01", "front_right_1")
    free = _sheltered(d0, "front_right_1", [], monkeypatch)
    assert len(free) == 1, "asked no route the room is sheltered"
    kept = _sheltered(d0, "front_right_1", _through(room, free[0]), monkeypatch)
    assert [(v["x"], v["y"]) for v in kept] == [(free[0]["x"], free[0]["y"])], kept


def test_a_shelter_piece_on_a_route_is_the_pass_s_fallback():
    """A shelter piece in a room that reserves its routes stands off them, unless the room has no clear spot off them
    -- then the pass stands it anywhere clear rather than leave a room both sides see over everything in. So every
    shelter piece the library stands on its room's routes must be the pass's own choice now: taken out, the pass puts
    it back on the same spot, which it would not if a spot off the routes were clear. Asked of the pieces of earlier
    versions too, which no pass moves. Until 0.252.0 this asked that none stood on a route, which the fallback breaks
    legitimately: landmark_hall_a01's artifact_room, once 0.252.0 took away a dining table whose chair fitted only on
    the room's routes, had a clear spot only on them -- at 0.252.0 the one such piece in the library."""
    on = []
    for name, d in _library():
        b = L.club_building_id(d)
        bare = None
        for room in d["rooms"]:
            if not (_holds_marker(d, room) or L.is_corner_store_floor(room, b)):
                continue
            mine = [v for v in d["volumes"] if v["name"].endswith("_" + room["id"] + "_shelter")]
            if not mine:
                continue
            bare = bare or L.unfurnished(copy.deepcopy(d))
            routes = L.protected_routes(bare, room)
            for v in mine:
                if not L.on_protected_route(routes, v["x"], v["y"], v["size_x"] - 0.01, v["size_y"] - 0.01):
                    continue
                again = copy.deepcopy(d)
                again["volumes"] = [w for w in again["volumes"] if w["name"] != v["name"]]
                L.seed_cover(again)
                back = [(w["x"], w["y"]) for w in again["volumes"] if w["name"] == v["name"]]
                if back != [(v["x"], v["y"])]:
                    on.append((name, v["name"], (v["x"], v["y"]), back))
    assert not on, on
