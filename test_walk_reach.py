"""A room a body can only reach by breaching (layout_lint L24, 0.194.0).

L12 asks whether every room has a path from an exterior entrance, and counts
every way through a wall: a door, a garage, a breach panel, a vaultable
window, a floor-hole drop. So a room whose only ways in are breach panels
passes it. deli_a01's server room was that room: 186 m2 on story 1, a
soft-wall breach from the upper hall and another from the apartment, no
door, and cold run 9188's site bake made it a navmesh island of its own
(`docs/findings/deli_a01_upper_storey_9188/` at the factory root). The
walker's call, 2026-10-06: give it a door.

L24 runs L12's search a second time over doors, garages, vault doors,
stairs, ladders and ramps only, and names what the first search reached and
the second did not. Measured across the library first: 16 rooms in 8 built
specs (22 in 11 counting Level Factory's lf_ specs). One got its door; the
other 15 are frozen in walk_reach_baseline.json for the walker to decide.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402

BASELINE = os.path.join(HERE, "walk_reach_baseline.json")


def _spec(kind, **extra):
    """Two 5 x 10 m rooms side by side, a door in from the west, `kind` between."""
    op = dict({"kind": kind, "pos": 0.0, "width": 1.2}, **extra)
    return {"name": "t", "footprint_x": 10.0, "footprint_y": 10.0,
            "rooms": [{"id": "front", "story": 0, "bounds": [-5.0, -5.0, 0.0, 5.0]},
                      {"id": "back", "story": 0, "bounds": [0.0, -5.0, 5.0, 5.0]}],
            "partitions": [{"story": 0, "axis": "Y", "pos": 0.0,
                            "start": -5.0, "end": 5.0, "openings": [op]}],
            "ext_walls": [{"wall": "W", "story": 0,
                           "openings": [{"kind": "door", "pos": 0.0, "width": 1.2}]}]}


def _walk(spec):
    return sorted(r["id"] for r in layout_lint.walk_unreachable(spec))


def test_a_room_behind_a_breach_is_named():
    s = _spec("breach", breach_class="soft_wall")
    assert not layout_lint.reachability_findings(s)          # L12 passes it
    assert _walk(s) == ["back"]
    found = layout_lint.walk_reach_findings(s)
    assert len(found) == 1 and found[0].startswith("L24 ") and "'back'" in found[0]


def test_a_door_a_garage_or_a_vault_door_is_a_way_in():
    for kind in ("door", "garage", "vault"):
        assert _walk(_spec(kind)) == [], kind
    assert layout_lint.walk_reach_findings(_spec("door")) == []


def test_a_window_is_not_a_way_in():
    s = _spec("window", vaultable=True, sill=1.0)
    assert not layout_lint.reachability_findings(s)          # L12 vaults it
    assert _walk(s) == ["back"]


def test_a_floor_hole_is_a_drop_not_a_way_up():
    s = _spec("door")
    s["rooms"].append({"id": "loft", "story": 1, "bounds": [-5.0, -5.0, 5.0, 5.0]})
    s["vertical_links"] = [{"kind": "floor_hole", "story": 1, "x": -2.0, "y": 0.0}]
    assert not layout_lint.reachability_findings(s)
    assert _walk(s) == ["loft"]
    s["stairs"] = [{"x": -2.0, "y": 2.0, "from_story": 0, "to_story": 1}]
    assert _walk(s) == []


def test_the_search_leaves_the_spec_alone():
    s = _spec("breach", breach_class="soft_wall")
    before = json.dumps(s, sort_keys=True)
    layout_lint.walk_unreachable(s)
    assert json.dumps(s, sort_keys=True) == before


def test_lint_reports_it_as_a_warning_not_a_failure():
    spec = json.load(open(os.path.join(HERE, "specs", "deli_a02.json"), encoding="utf-8"))
    _name, fails, warns = layout_lint.lint_spec(spec, "deli_a02")
    assert any(w.startswith("L24 ") and "'server_room'" in w for w in warns), warns
    assert not any(f.startswith("L24 ") for f in fails)


def test_deli_a01s_server_room_has_a_door():
    spec = json.load(open(os.path.join(HERE, "specs", "deli_a01.json"), encoding="utf-8"))
    assert "server_room" not in _walk(spec)
    doors = [o for p in spec["partitions"] if p.get("story") == 1
             for o in p.get("openings", []) if o.get("tag") == "hall_to_server_room"]
    assert len(doors) == 1 and doors[0]["kind"] == "door", doors


def _library():
    out = {}
    for m in sorted(glob.glob(os.path.join(HERE, "build", "*.manifest.json"))):
        name = os.path.basename(m)[:-len(".manifest.json")]
        p = os.path.join(HERE, "specs", name + ".json")
        if name.startswith("lf_") or not os.path.exists(p):
            continue
        got = layout_lint.walk_unreachable(json.load(open(p, encoding="utf-8")))
        if got:
            out[name] = sorted(r["id"] for r in got)
    return out


def _frozen():
    d = json.load(open(BASELINE, encoding="utf-8"))
    return {k: sorted(v) for k, v in d["walk_unreachable"].items()}


def test_no_new_room_only_a_breach_reaches():
    frozen = _frozen()
    new = {k: [n for n in v if n not in frozen.get(k, [])] for k, v in _library().items()}
    assert not {k: v for k, v in new.items() if v}, new


def test_walk_baseline_has_not_gone_stale():
    lib = _library()
    gone = {k: [n for n in v if n not in lib.get(k, [])] for k, v in _frozen().items()}
    assert not {k: v for k, v in gone.items() if v}, gone


# ------------------------------------------------------- open floor (0.197.0)
# L24 shipped asking L12's graph, which joins rooms through openings, stairs
# and ladders only. deli_a01's basement partition along y = 1 stops at x 12,
# so the utility room's north edge from x 12 to 19 is open floor, and cold run
# 9189's bake walks across it on the street's island -- while L24 named the
# room "reachable only by breaching". Nine of the fifteen rooms 0.194.0 froze
# were open floor. tactical.build_graph has modelled it all along; the rule
# is now one function both ask.

def _open_plan(partition_end):
    """`_spec`'s two rooms, a breach between them, the partition between them
    covering their 10 m shared edge from y -5 to `partition_end`."""
    s = _spec("breach", breach_class="soft_wall")
    s["partitions"][0]["end"] = partition_end
    return s


def test_an_open_floor_edge_is_a_way_in():
    assert _walk(_open_plan(2.0)) == []            # 3 m of the edge uncovered
    assert _walk(_open_plan(4.5)) == ["back"]      # 0.5 m: a gap, not a way in


def test_lint_asks_tacticals_open_floor_rule(monkeypatch):
    import tactical
    monkeypatch.setattr(tactical, "shared_open_edge", lambda a, b, parts: False)
    assert _walk(_open_plan(2.0)) == ["back"]


def test_deli_a01s_utility_room_is_open_floor():
    spec = json.load(open(os.path.join(HERE, "specs", "deli_a01.json"), encoding="utf-8"))
    assert "utility_room" not in _walk(spec)
