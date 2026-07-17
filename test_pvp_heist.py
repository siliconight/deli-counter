"""Tests for the pvp_heist gating profile. Mutation-style: start from the
known-good reference spec (specs/pvp_station_ref.json) and break one thing at
a time, asserting the profile fails with the *expected code* — the Production
Package requires every failing fixture to fail for its documented reason."""

import copy
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "specs", "pvp_station_ref.json")

import pvp_heist
from spec_loader import spec_from_dict


def _ref():
    with open(REF, "r", encoding="utf-8") as f:
        return json.load(f)


def _check(data):
    return pvp_heist.check(spec_from_dict(data))


def _codes(errors):
    return {e.split(":", 1)[0] for e in errors}


def test_reference_passes():
    errors, warnings, summary = _check(_ref())
    assert errors == [], errors
    assert summary["disjoint_routes"] >= 2
    assert summary["protected_rotation"] is True
    assert summary["attacker_spawns"] >= 1
    assert summary["defender_spawns"] >= 1


def test_no_attacker_spawn_fails():
    d = _ref()
    d["markers"] = [m for m in d["markers"] if m["type"] != "attacker_spawn"]
    errors, _, _ = _check(d)
    assert "PVP-SPAWN-A" in _codes(errors)


def test_no_defender_spawn_fails():
    d = _ref()
    d["markers"] = [m for m in d["markers"] if m["type"] != "defender_spawn"]
    errors, _, _ = _check(d)
    assert "PVP-SPAWN-D" in _codes(errors)


def test_spawn_far_outside_envelope_fails():
    d = _ref()
    for m in d["markers"]:
        if m["type"] == "attacker_spawn":
            m["x"], m["y"] = 500.0, 500.0
            break
    errors, _, _ = _check(d)
    assert "PVP-SPAWN-BOUNDS" in _codes(errors)


def test_no_objective_fails():
    d = _ref()
    d["markers"] = [m for m in d["markers"] if m["type"] != "objective"]
    d["objectives"] = []
    errors, _, _ = _check(d)
    assert "PVP-OBJ" in _codes(errors)


def test_opposing_spawn_sightline_fails():
    d = _ref()
    # drop a defender spawn onto an attacker spawn's story and position,
    # nudged one meter over: nothing can occlude a 1 m ray.
    atk = next(m for m in d["markers"] if m["type"] == "attacker_spawn")
    d["markers"].append({"type": "defender_spawn", "id": "LOS",
                        "x": atk["x"] + 1.0, "y": atk["y"], "z": atk.get("z", 0)})
    errors, _, _ = _check(d)
    assert "PVP-SPAWN-LOS" in _codes(errors)


def test_single_route_fails():
    """Wall the objective room down to one approach: disjoint routes < 2."""
    d = _ref()
    # the armory (story 1 objective room) is reachable via booking,
    # detective_offices, garage, interrogation. Shrink the room graph by
    # removing armory's partition openings except one: simulate by moving
    # the objective into a dead-end synthetic room reachable only through
    # one neighbor. Simplest reliable mutation: declare a new room outside
    # the partition grid and put the objective there via marker room=.
    d["rooms"].append({"id": "isolated_vault", "story": 1,
                       "bounds": [14.0, 10.0, 16.9, 12.9],
                       "role": "objective_room"})
    for m in d["markers"]:
        if m["type"] == "objective":
            m["room"] = "isolated_vault"
            m["x"], m["y"] = 15.5, 11.5
    errors, _, summary = _check(d)
    assert summary["disjoint_routes"] < 2
    assert "PVP-ROUTES" in _codes(errors)


def test_breach_into_void_fails():
    d = _ref()
    # add an interior breach on a partition segment that borders no second room
    d["partitions"].append({
        "story": 1, "axis": "Y", "pos": 16.5, "start": 12.0, "end": 12.9,
        "openings": [{"kind": "breach", "pos": 0.5, "width": 1.2, "height": 2.0}]})
    errors, _, _ = _check(d)
    assert "PVP-BREACH" in _codes(errors)


def test_summary_counts_vertical_routes():
    _, _, summary = _check(_ref())
    assert summary["stairs"] >= 1
    assert summary["ladders"] >= 1


def test_validate_gates_pvp_mode(tmp_path, capsys):
    """validate.py must gate pvp_heist errors (end-to-end wiring check)."""
    import validate
    d = _ref()
    d["name"] = "pvp_gate_wiring"
    d["markers"] = [m for m in d["markers"] if m["type"] != "defender_spawn"]
    p = tmp_path / "pvp_gate_wiring.json"
    p.write_text(json.dumps(d))
    ok = validate.validate_file(str(p))
    out = capsys.readouterr().out
    assert ok is False
    assert "PVP-SPAWN-D" in out


def test_non_pvp_modes_unaffected():
    """A heist-mode spec must not run the pvp gate (legacy specs stay valid)."""
    d = _ref()
    d["mode"] = "heist"
    spec = spec_from_dict(d)
    assert spec.mode == "heist"
    # profile still callable directly, but validate.py only gates pvp_heist;
    # here we just confirm the loader accepts the mode switch round-trip.


def test_disjoint_route_counter_menger():
    """Direct-adjacent entry + one interior path = 2 disjoint routes."""
    adj = {
        "entryA": {"obj", "hall"},
        "hall": {"entryA", "obj"},
        "obj": {"entryA", "hall"},
    }
    assert pvp_heist._disjoint_route_count(adj, ["entryA"], ["obj"]) == 2


def test_disjoint_route_counter_single_chokepoint():
    """All paths through one room = 1 route no matter how many doors."""
    adj = {
        "a": {"choke"},
        "b": {"choke"},
        "choke": {"a", "b", "obj"},
        "obj": {"choke"},
    }
    assert pvp_heist._disjoint_route_count(adj, ["a", "b"], ["obj"]) == 1
