"""The delis' basement divider runs wall to wall (0.222.0), the walker's call of 2026-10-14.

The walker, cold run 9305's deli_a01 (the factory's `docs/findings/walk_2026-10-14/`, finding 5): "this wall
supposed to stop here and have this big opening?". The divider along X at y 1.0 stood -12..12 under rooms that meet
across the whole basement, 7 m open at each end, the vault open to the utility room beside its breach. Asked, the
walker chose "close the basement". Pure: specs and the preset, no build. Frame: the building plan, metres.
"""
import glob
import json
import os

import layout_lint
import migrate_basement_wall as M
import presets

HERE = os.path.dirname(os.path.abspath(__file__))
#: Where 0.221.0 built the divider's door and breach: snap(-0.35 * 24) and snap(0.3 * 24).
BUILT_AT = {"basement_corridor": -8.5, "vault_side_breach": 7.0}


def _snap(v, grid):
    return round(v / grid) * grid


def _divider(d):
    return [p for p in d.get("partitions") or () if p.get("story") == -1 and p.get("axis") == "X"
            and abs(float(p.get("pos", 0.0)) - 1.0) < 1e-9
            and any(o.get("tag") == M.TAG for o in p.get("openings") or ())]


def _built_at(d, p):
    run = float(p["end"]) - float(p["start"])
    return {o.get("tag"): _snap(float(o["pos"]) * run, float(d.get("grid", 0.5))) for o in p["openings"]}


def test_the_preset_builds_the_divider_wall_to_wall():
    d = presets.corner_deli()
    (p,) = _divider(d)
    half = d["footprint_x"] / 2.0
    assert (p["start"], p["end"]) == (-half, half), p
    assert _built_at(d, p) == BUILT_AT


def test_every_deli_in_the_library_is_closed_with_its_openings_where_they_stood():
    n = 0
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        for p in _divider(d):
            n += 1
            half = d["footprint_x"] / 2.0
            assert (p["start"], p["end"]) == (-half, half), path
            assert _built_at(d, p) == BUILT_AT, (path, _built_at(d, p))
    assert n == 6, n


def test_the_migration_keeps_every_opening_adds_the_door_and_is_idempotent():
    d = {"name": "x", "footprint_x": 38.0, "grid": 0.5, "partitions": [
        {"story": -1, "axis": "X", "pos": 1.0, "start": -12.0, "end": 12.0, "openings": [
            {"kind": "door", "pos": -0.35, "tag": "basement_corridor"},
            {"kind": "breach", "pos": 0.3, "tag": "vault_side_breach"}]},
        {"story": -1, "axis": "Y", "pos": 1.0, "start": -14.0, "end": 14.0, "openings": [
            {"kind": "door", "pos": 0.1, "width": 1.25, "tag": "cold_room_door"},
            {"kind": "breach", "pos": -0.32, "width": 1.4}]}]}
    assert M.migrate(d)
    p, q = d["partitions"]
    assert (p["start"], p["end"]) == (-19.0, 19.0)
    assert _built_at(d, p) == BUILT_AT
    ((_q, o),) = _utility_doors(d)
    assert o["width"] == 1.25 and _snap(o["pos"] * 28.0, 0.5) == -4.0, o
    assert M.migrate(d) == []


def test_a_divider_of_another_span_is_refused_not_forced():
    d = {"name": "x", "footprint_x": 38.0, "partitions": [
        {"story": -1, "axis": "X", "pos": 1.0, "start": -10.0, "end": 12.0, "openings": [
            {"kind": "door", "pos": -0.35, "tag": "basement_corridor"}]}]}
    try:
        M.migrate(d)
    except SystemExit as exc:
        assert "not touched" in str(exc)
    else:
        raise AssertionError("a -10..12 divider was migrated")


def _utility_doors(d):
    return [(p, o) for p in d.get("partitions") or () if p.get("story") == -1 and p.get("axis") == "Y"
            for o in p.get("openings") or () if o.get("tag") == M.UTILITY]


def test_the_preset_gives_the_utility_room_a_door_from_the_corridor():
    """Wall to wall, the divider leaves the utility room's two breaches its only ways in; a room reached only by
    breaching gets a door unless it is the objective (the walker, 2026-10-06; layout_lint L24), and asked, the
    walker chose the door, 2026-10-14."""
    d = presets.corner_deli()
    ((p, o),) = _utility_doors(d)
    assert o["kind"] == "door", o
    run = p["end"] - p["start"]
    assert _snap(o["pos"] * run, d["grid"]) == -4.0      # midway between the breach at -9.0 and the divider at 1.0
    assert "utility_room" not in [r["id"] for r in layout_lint.walk_unreachable(d)]


def test_every_deli_s_utility_room_is_walked_into_by_its_door():
    n = 0
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if not _divider(d):
            continue
        n += 1
        ((p, o),) = _utility_doors(d)
        cold = [c for c in p["openings"] if c.get("tag") == M.COLD][0]
        assert o["kind"] == "door" and o["width"] == cold["width"], (path, o)
        assert _snap(o["pos"] * (p["end"] - p["start"]), d.get("grid", 0.5)) == -4.0, (path, o)
        assert "utility_room" not in [r["id"] for r in layout_lint.walk_unreachable(d)], path
    assert n == 6, n


def test_no_two_basement_rooms_meet_past_the_divider():
    """`partition_gaps.py`'s question, asked of the six delis: wherever two basement rooms meet along y 1.0, the
    divider stands."""
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        for p in _divider(d):
            rooms = [r for r in d.get("rooms") or () if r.get("story") == -1]
            south = [r["bounds"] for r in rooms if abs(r["bounds"][3] - 1.0) < 1e-9]
            north = [r["bounds"] for r in rooms if abs(r["bounds"][1] - 1.0) < 1e-9]
            for a in south:
                for b in north:
                    lo, hi = max(a[0], b[0]), min(a[2], b[2])
                    if hi - lo > 1e-9:
                        assert p["start"] <= lo + 1e-9 and hi - 1e-9 <= p["end"], (path, a, b, p["start"], p["end"])
