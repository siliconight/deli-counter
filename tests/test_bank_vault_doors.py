"""A bank's vault gate is a vault door (0.290.0, the factory's roadmap 323).

Four score banks entered their vault through an ordinary door tagged `vault_gate`, so they had no vault door, no
vault-door states and no `alarm.vault_door` hook. `migrations/migrate_bank_vault_doors.py` made each the vault door the
other banks author. FAILS ON 0.289.0, whose four build a doorway there.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "migrations"))

import migrate_bank_vault_doors as m  # noqa: E402

BUILD = os.path.join(HERE, "build")
GATED = ("bank_branch_a04", "bank_tower_a01", "credit_union_a03")
#: Its vault door's leaf would swing across a stair (layout_lint L22): it keeps its door.
KEPT = "credit_union_a01"


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def test_each_gated_vault_is_entered_through_a_vault_door_facing_its_approach():
    for name in GATED:
        spec = _spec(name)
        doors = [(p, o) for p in spec["partitions"] for o in p.get("openings") or [] if o.get("tag") == m.GATE_TAG]
        assert len(doors) == 1, name
        part, op = doors[0]
        assert {k: op[k] for k in m.VAULT_DOOR} == m.VAULT_DOOR, (name, op)
        (a, face_a), (b, face_b) = m._sides(spec, part, op)
        vault, face = (a, face_a) if a["role"] == "objective_room" else (b, face_b)
        assert vault["role"] == "objective_room" and op["face"] == face, (name, op["face"], face)


def test_each_built_one_has_its_vault_door_and_its_alarm():
    for name in GATED:
        slots = json.load(open(os.path.join(BUILD, name + ".slots.json"), encoding="utf-8"))["slots"]
        gp = json.load(open(os.path.join(BUILD, name + ".gameplay.json"), encoding="utf-8"))
        assert sum(s.get("role") == "vault_door" for s in slots) == 1, name
        events = [mk["meta"]["event"] for mk in gp["markers"] if mk.get("type") == "alarm"]
        assert events.count("alarm.vault_door") == 1, (name, events)


def test_the_migration_is_a_fixed_point_and_leaves_what_is_not_a_bank_vault():
    """Run again it changes nothing; the banks whose score is not a vault keep their doors."""
    assert m.main(["--check"]) == 0
    for name in ("bank_tower_a02", "bank_tower_a03", "credit_union_a02"):
        assert m.gates(_spec(name)) == ([], []), name
        assert not any(o.get("kind") == "vault" for p in _spec(name)["partitions"] for o in p.get("openings") or [])


def test_a_vault_door_whose_swing_the_vault_check_refuses_is_not_made():
    """credit_union_a01's leaf would swing across `cu01_stair_w`: the gate stays a door, and saying so is the
    migration's, not a lint failure after it. No bank or credit union fails L22."""
    import copy

    import layout_lint
    spec = _spec(KEPT)
    gate, = [o for p in spec["partitions"] for o in p.get("openings") or [] if o.get("tag") == m.GATE_TAG]
    assert gate["kind"] == "door"
    trial, left = copy.deepcopy(spec), []
    assert m.migrate(trial, left) == 0 and left and "cu01_stair_w" in left[0], left
    for name in GATED + (KEPT,):
        fails = layout_lint.lint_spec(_spec(name), name)[0]
        assert not [f for f in fails if f.startswith("L22")], (name, fails)
