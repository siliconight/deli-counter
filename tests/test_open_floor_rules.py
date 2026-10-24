"""The walker's table sorts open floors by room pair (open_floor_rules, 0.234.0; the factory's roadmap 260).

Two rooms meeting with no wall between them are one floor (`open_to`) or two rooms (a wall, with a door where
nothing walkable would join them any more), by a row per pair of room ids, applied to the library by
`migrate_open_floor_rules.py` and to every building `presets.make` makes. Beside it: an exterior wall covers its line
as a partition does (`tactical.exterior_parts`), and a room may carry `open_to` into the typed spec.

FAIL ON 0.233.0: there is no open_floor_rules; `spec_loader` refuses a room naming `open_to`; a room meeting an
outdoor room along the exterior wall is an open floor; and `presets.make("corner_deli")` comes out with two.
"""
import copy
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import agent_contract                # noqa: E402
import layout_lint                   # noqa: E402
import open_floor_rules              # noqa: E402
import presets                       # noqa: E402
import spec_loader                   # noqa: E402
import tactical                      # noqa: E402

FRONT, BACK = [-5.0, -5.0, 0.0, 5.0], [0.0, -5.0, 5.0, 5.0]


def _spec(partitions=(), front=None, back=None):
    """Two 5 x 10 m rooms side by side on story 0 meeting along x = 0, a door in from the west and one from the east."""
    rooms = [dict({"id": "front", "story": 0, "bounds": list(FRONT)}, **(front or {})),
             dict({"id": "back", "story": 0, "bounds": list(BACK)}, **(back or {}))]
    return {"name": "t", "footprint_x": 10.0, "footprint_y": 10.0, "rooms": rooms,
            "partitions": [copy.deepcopy(p) for p in partitions],
            "ext_walls": [{"wall": "W", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]},
                          {"wall": "E", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}]}


def _line(spec):
    return [p for p in spec["partitions"] if p["axis"] == "Y" and abs(p["pos"]) < 1e-9]


@pytest.fixture
def table(monkeypatch):
    def use(row):
        monkeypatch.setattr(open_floor_rules, "RULES", {("front", "back"): row})
    return use


def test_an_open_row_names_the_floor_and_moves_nothing(table):
    table(open_floor_rules.OPEN)
    s = _spec()
    assert len(layout_lint.open_floors(s)) == 1
    said = open_floor_rules.apply(s)
    assert len(said) == 1 and "open" in said[0]
    assert s["rooms"][0]["open_to"] == ["back"] and s["partitions"] == []
    assert layout_lint.open_floors(s) == []
    assert open_floor_rules.apply(s) == []                    # once is enough


def test_a_wall_row_extends_the_short_partition_and_keeps_its_door_where_it_stood(table):
    table(open_floor_rules.WALL)
    part = {"story": 0, "axis": "Y", "pos": 0.0, "start": -5.0, "end": 2.0,
            "openings": [{"kind": "door", "pos": 0.0, "width": 1.25, "tag": "between"}]}   # built at y -1.5
    s = _spec([part])
    before = open_floor_rules._built_at(s, s["partitions"][0], s["partitions"][0]["openings"][0])
    said = open_floor_rules.apply(s)
    assert any("extended over 2..5" in x for x in said), said
    (p,) = _line(s)
    assert (p["start"], p["end"]) == (-5.0, 5.0)
    assert abs(open_floor_rules._built_at(s, p, p["openings"][0]) - before) < 1e-9 and before == -1.5
    assert len(p["openings"]) == 1                            # a door already joined them: none added
    assert layout_lint.open_floors(s) == []


def test_a_wall_row_with_no_partition_adds_one_and_a_door_of_the_contracts_width(table):
    table(open_floor_rules.WALL)
    s = _spec()
    open_floor_rules.apply(s)
    (p,) = _line(s)
    assert (p["start"], p["end"]) == (-5.0, 5.0) and p["material"] == "drywall"
    (door,) = p["openings"]
    assert door["kind"] == "door" and door["tag"] == "front_to_back"
    assert door["width"] == agent_contract.min_door_width() == 1.25
    edges, _ = layout_lint.graph(s)
    assert ("back", "door") in edges["front"]
    assert layout_lint.open_floors(s) == [] and layout_lint.reachability_findings(s) == []
    assert open_floor_rules.apply(s) == []


def test_no_door_into_an_objective_room(table):
    table(open_floor_rules.WALL)
    s = _spec(back={"objective": True, "role": "objective_room"})
    said = open_floor_rules.apply(s)
    (p,) = _line(s)
    assert p["openings"] == [] and any("is the objective" in x for x in said), said


def test_the_other_policy_puts_a_door_only_where_a_room_would_be_cut_off(table):
    table(open_floor_rules.WALL)
    s = _spec()
    open_floor_rules.apply(s, policy="only_if_sealed")       # both rooms keep their own door outside
    assert _line(s)[0]["openings"] == []
    t = _spec()
    t["ext_walls"] = t["ext_walls"][:1]                       # the back room's only way in was the open floor
    open_floor_rules.apply(t, policy="only_if_sealed")
    assert [o["tag"] for o in _line(t)[0]["openings"]] == ["front_to_back"]
    with pytest.raises(ValueError):
        open_floor_rules.apply(_spec(), policy="always")


def test_a_partition_whose_door_the_grid_would_slide_is_left_alone(table):
    table(open_floor_rules.WALL)
    # a run of 5.5 m, its door built at y -1.75 (snap(0.1 * 5.5) = 0.5 from the middle, -2.25); over 10 m the same
    # place is -1.75 from the middle, which the 0.5 m grid rounds to -2.0: the door would slide 0.25 m
    part = {"story": 0, "axis": "Y", "pos": 0.0, "start": -5.0, "end": 0.5,
            "openings": [{"kind": "door", "pos": 0.1, "width": 1.25, "tag": "kept"}]}
    s = _spec([part])
    said = open_floor_rules.apply(s)
    assert any("would have moved" in x for x in said), said
    first, piece = _line(s)
    assert (first["start"], first["end"]) == (-5.0, 0.5) and first["openings"][0]["pos"] == 0.1
    assert (piece["start"], piece["end"]) == (0.5, 5.0)
    assert layout_lint.open_floors(s) == []


def test_a_pair_with_no_row_is_left_for_l26():
    s = _spec()
    assert open_floor_rules.rule("front", "back") is None
    assert open_floor_rules.apply(s) == [] and len(layout_lint.open_floors(s)) == 1


def test_the_table_reads_either_way_round_and_says_only_open_or_wall():
    assert open_floor_rules.rule("deli_counter", "customer_floor") == open_floor_rules.OPEN
    assert open_floor_rules.rule("kitchen", "market_aisles") == open_floor_rules.WALL
    assert set(open_floor_rules.RULES.values()) <= {open_floor_rules.OPEN, open_floor_rules.WALL}
    assert open_floor_rules.DOORWAY_POLICY in open_floor_rules.POLICIES


def test_an_exterior_wall_covers_its_line():
    # a shop meeting its outdoor forecourt along the footprint's south edge, where the front wall stands
    s = {"name": "t", "footprint_x": 10.0, "footprint_y": 10.0,
         "rooms": [{"id": "forecourt", "story": 0, "bounds": [-5.0, -9.0, 5.0, -5.0]},
                   {"id": "shop", "story": 0, "bounds": [-5.0, -5.0, 5.0, 5.0]}],
         "partitions": [],
         "ext_walls": [{"wall": "S", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}]}
    assert layout_lint.open_floors(s) == []
    assert ("X", -5.0, -5.0, 5.0) in layout_lint._story_parts(s, 0)
    s["auto_exterior"] = False
    s["ext_walls"] = []                                       # no wall there: then it is one floor
    assert len(layout_lint.open_floors(s)) == 1
    assert tactical.exterior_parts((-5.0, -5.0, 5.0, 5.0), ("N", "W")) == [("X", 5.0, -5.0, 5.0),
                                                                           ("Y", -5.0, -5.0, 5.0)]


def test_a_room_naming_open_to_loads():
    s = _spec(front={"open_to": ["back"]})
    spec = spec_loader.spec_from_dict(s)
    assert spec.rooms[0].open_to == ["back"] and spec.rooms[1].open_to == []
    assert "front" in tactical.build_graph(spec)["back"]       # still one floor to the engine


def test_a_deli_made_from_its_preset_comes_out_sorted():
    d = presets.make("corner_deli")
    assert layout_lint.open_floors(d) == []
    rooms = {r["id"]: r for r in d["rooms"]}
    assert "deli_counter" in rooms["customer_floor"].get("open_to", [])
    assert any(o.get("tag") == "market_aisles_to_kitchen" for p in d["partitions"] for o in p.get("openings", []))
    assert layout_lint.reachability_findings(d) == []
