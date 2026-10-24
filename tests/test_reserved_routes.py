"""A corner store's selling floor reserves its routes before its rows are laid (0.250.0, the factory's roadmap 288).

The factory's census of what furnishing costs a route (`docs/findings/furnish_route_cost/` at the factory root) found
the corner stores' rows -- 0.247.0's -- the most of it: 16 of their 85 routes between doors grown over the 10 % the
walker's guide flags, 44 narrowed from two abreast to single file. `protected_routes` reserves square routes between a
room's doors and markers, a greedy spanner at the guide's 10 %, before furnish places anything there; rows, floor
pieces, clusters and chairs keep half `two_abreast_width()` off them. Measured over the fourteen corner-store specs:
the routes over 10 % from 20 to 4, none of them on a corner floor; the routes narrowed to single file from 70 to 54;
every corner floor's share 17.2 to 22.1 %, inside the walker's band.
"""
import copy
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_contract  # noqa: E402
import level_design as L  # noqa: E402
import migrate_furnish_recipes as M  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _corner_floors():
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        b = L.club_building_id(d)
        for r in d.get("rooms") or []:
            if L.is_corner_store_floor(r, b):
                out.append((os.path.basename(p)[:-5], d, r))
    return out


def _stripped(d):
    """The floor every pass asks for a room's routes on: less what furnish and the fixtures pass wrote."""
    return L.unfurnished(copy.deepcopy(d))


def test_every_pass_reserves_on_the_floor_the_refurnish_starts_from():
    """`unfurnished` strips what `migrate_furnish_recipes` strips, volume for volume, across the library: the routes
    furnish reserves are asked of the floor a refurnish starts from, whatever order the rooms come in."""
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        tags = {L._room_tag(r) for r in d.get("rooms") or []}
        kept = [v["name"] for v in d.get("volumes") or [] if not M.furnished_by_this_pass(v, tags)]
        assert [v["name"] for v in L.unfurnished(d)["volumes"]] == kept, os.path.basename(p)


def test_two_abreast_is_the_guides_formula_on_the_contracts_body(monkeypatch):
    r = agent_contract.body_radius()
    assert L.two_abreast_width() == round(2 * 2 * r + 2 * 0.15 + 0.20, 4) == 1.9
    monkeypatch.setattr(agent_contract, "body_radius", lambda: 0.40)
    assert L.two_abreast_width() == 2.1


def test_route_endpoints_stand_inside_the_doors_the_builder_cuts():
    """A partition door and an exterior door, each where `partition_bounds.host_openings` puts it, a body's centre
    half a metre inside the wall's face; a breach and a window are no route; an objective marker is."""
    d = {"footprint_x": 10.0, "footprint_y": 6.0, "wall_thick": 0.3, "story_height": 3.0,
         "rooms": [{"id": "a", "story": 0, "bounds": [-5.0, -3.0, 1.0, 3.0]},
                   {"id": "b", "story": 0, "bounds": [1.0, -3.0, 5.0, 3.0]}],
         "partitions": [{"story": 0, "axis": "Y", "pos": 1.0, "start": -3.0, "end": 3.0,
                         "openings": [{"kind": "door", "pos": 0.25, "width": 1.25},
                                      {"kind": "breach", "pos": -0.25, "width": 1.4}]}],
         "ext_walls": [{"wall": "W", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.25},
                                                              {"kind": "window", "pos": 0.3, "width": 1.0}]}],
         "markers": [{"type": "objective", "id": "A", "x": -2.0, "y": 1.0, "z": 0.0}], "volumes": []}
    got = sorted((k, round(x, 3), round(y, 3)) for k, _l, x, y in L.room_route_endpoints(d, d["rooms"][0]))
    assert got == [("door", -4.35, 0.0), ("door", 0.35, 1.5), ("objective", -2.0, 1.0)], got


def test_reserved_routes_run_square():
    """Every segment of every route reserved on the library's corner-store floors runs along an axis, down an aisle
    or across a row square: the diagonal an empty floor allows cut the rows into scattered short gondolas."""
    for name, d, room in _corner_floors():
        routes = L.protected_routes(_stripped(d), room)
        assert routes, name
        for pts, half in routes:
            assert half == L.two_abreast_width() / 2.0
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                assert abs(ax - bx) < 1e-9 or abs(ay - by) < 1e-9, (name, (ax, ay), (bx, by))


def test_nothing_furnish_stood_on_a_corner_floor_stands_on_its_routes():
    """The library as shipped: every piece furnish stood on a corner-store floor keeps half `two_abreast_width()` off
    every route the floor reserved, allowing the half centimetre a written position may move (`_make_volume`). Not
    asked, as the code does not ask them: a wall piece, a fixture (`place_fixtures`), and the seat either brings --
    they stand in the wall's zone, and asked, two stores lost both their video poker cabinets."""
    for name, d, room in _corner_floors():
        routes = L.protected_routes(_stripped(d), room)
        tag = L._room_tag(room)
        floor = room.get("story", 0) * L._story_height(d)
        fixtures = set(L._RECIPES[L._room_kind(room, L.club_building_id(d))].get("fixtures") or ())
        wall_hosts, made = set(), []
        for v in d["volumes"]:
            m = M._GENERATED.match(v["name"])
            if not m or m.group("tag") != tag:
                continue
            # a piece is `stem_tag_seq`, the seat a host brings `stem_tag_seq_j`
            tail = v["name"].split("_" + tag + "_", 1)[1].split("_")
            stem = m.group("stem")
            if stem in fixtures or (stem in L._PIECES and L._PIECES[stem]["where"] == "wall"):
                wall_hosts.add(tail[0])
                continue
            made.append((v, tail))
        for v, tail in made:
            if len(tail) == 2 and tail[0] in wall_hosts:
                continue
            if L._hung(v, floor):
                continue
            assert not L.on_protected_route(routes, v["x"], v["y"], v["size_x"] - 0.01, v["size_y"] - 0.01), \
                (name, v["name"])


def test_a_floor_that_stands_rows_or_a_room_holding_a_marker_asks_for_its_routes(monkeypatch):
    """The recipe's `protect_routes`, set where `reserves_routes` says: furnishing office and deli_a03 from bare asks
    for the routes of the deli's market aisles, a shop floor that stands rows, and of the two rooms holding an
    objective or loot marker (0.251.0) -- office's exec_suite and the deli's apartment_hideout -- and of no other."""
    calls = []
    real = L.protected_routes

    def counting(spec, room):
        calls.append(room["id"])
        return real(spec, room)

    monkeypatch.setattr(L, "protected_routes", counting)
    for name in ("office", "deli_a03"):
        L.furnish(_stripped(_load(name)))
    assert calls == ["exec_suite", "market_aisles", "apartment_hideout"], calls
