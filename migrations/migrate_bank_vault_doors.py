#!/usr/bin/env python3
"""
migrate_bank_vault_doors.py  --  a bank's vault gate is a vault door (0.290.0)
==============================================================================

One-shot, idempotent migration over specs/*.json. Four of the library's score banks enter their vault through an
ordinary door: `bank_branch_a04`, `bank_tower_a01`, `credit_union_a01`, `credit_union_a03` each have one partition door
tagged `vault_gate` between an approach room and an `objective_room` vault, built as a `doorway`. So none of them has
a `vault_door` -- not the piece, not its interactive states, and not the `alarm.vault_door` hook Deli Counter 0.289.0
writes at one (the factory's roadmap 323; its `docs/findings/gameplay_events/`).

Each such door becomes the vault door the other banks author (`bank_branch_a02`'s `vault_door_0`): kind `vault`, 1.3 m
wide, 2.1 m high, from the floor, in `metal`, its `face` toward the room it is entered from, as theirs is. Its tag and
every other key are kept. Then the spec is refurnished (`migrate_furnish_recipes.migrate`), because the vault's rows
keep clear of a vault door's swing and a doorway's they did not; the library is a fixed point of its furnishing pass.

A `vault_gate` whose far side is not an objective room, or a spec with more than one, is left and reported: which door
is the vault's is then a design question, not this migration's. So is a vault door whose leaf would swing over a stair
or anything else `vault_room.findings` refuses (layout_lint's L22): the gate is converted, held to that check, and put
back if the check, run after the refurnish, fails on it -- `credit_union_a01`'s would have swung across `cu01_stair_w`. Only `bank*` and `credit_union*` specs are read --
fourteen other families tag a `vault_gate` into rooms that are not a bank's vault. `lf_*` specs are Level Factory's
per-run transients and are skipped.

    python migrations/migrate_bank_vault_doors.py            # write specs/
    python migrations/migrate_bank_vault_doors.py --check    # report only; exit 1 if any would change
"""
import copy
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "migrations"))

import migrate_furnish_recipes  # noqa: E402
import vault_room  # noqa: E402

FAMILIES = ("bank", "credit_union")
GATE_TAG = "vault_gate"
#: `bank_branch_a02`'s `vault_door_0`, the vault door every authored bank vault has.
VAULT_DOOR = {"kind": "vault", "width": 1.3, "height": 2.1, "sill": 0.0, "material": "metal"}
#: How far either side of a partition a point is taken to ask which room is there (metres).
PROBE = 0.3


def _room_at(rooms, x, y):
    """The innermost room holding (x, y), as `layout_lint._room_at` reads it."""
    holding = [r for r in rooms if r["bounds"][0] - 1e-6 <= x <= r["bounds"][2] + 1e-6
               and r["bounds"][1] - 1e-6 <= y <= r["bounds"][3] + 1e-6]
    return min(holding, key=lambda r: (r["bounds"][2] - r["bounds"][0]) * (r["bounds"][3] - r["bounds"][1]),
               default=None)


def _sides(spec, part, op):
    """((room on the low side, its face), (room on the high side, its face)) across a partition at its opening.
    A face names the side the door looks out of: a vault on the low side is looked out of to the high side."""
    hx, hy = spec["footprint_x"] / 2.0, spec["footprint_y"] / 2.0
    axis = part.get("axis", "X")
    lo, hi = (-hx, hx) if axis == "X" else (-hy, hy)
    s = lo if part.get("start") is None else float(part["start"])
    e = hi if part.get("end") is None else float(part["end"])
    along = (s + e) / 2.0 + float(op.get("pos", 0.0)) * (e - s)
    p = float(part["pos"])
    story = int(part.get("story", 0) or 0)
    rooms = [r for r in spec.get("rooms") or [] if int(r.get("story", 0) or 0) == story]
    if axis == "X":           # runs along x at y = pos: low side south, high side north
        return (_room_at(rooms, along, p - PROBE), "N"), (_room_at(rooms, along, p + PROBE), "S")
    return (_room_at(rooms, p - PROBE, along), "E"), (_room_at(rooms, p + PROBE, along), "W")


def gates(spec):
    """[(partition, opening, face)] for each door tagged `vault_gate` into an objective room, and [reasons] for each
    left alone."""
    found, left = [], []
    for part in spec.get("partitions") or []:
        for op in part.get("openings") or []:
            if op.get("tag") != GATE_TAG or op.get("kind") != "door":
                continue
            (a, face_a), (b, face_b) = _sides(spec, part, op)
            vault = [(r, f) for r, f in ((a, face_a), (b, face_b)) if r and r.get("role") == "objective_room"]
            if len(vault) != 1:
                left.append("a %s between %s and %s: not one objective room" % (
                    GATE_TAG, a and a["id"], b and b["id"]))
                continue
            found.append((part, op, vault[0][1]))
    if len(found) > 1:
        left.append("%d %s doors into objective rooms: which is the vault's is a design call" % (len(found), GATE_TAG))
        found = []
    return found, left


def _refused(spec):
    """What `vault_room.findings` fails on a vault gate, as layout_lint's L22 reads it."""
    fails, _warns = vault_room.findings(spec)
    return [f for f in fails if GATE_TAG in f]


def migrate(spec, left=None):
    """Make the spec's vault gate its vault door and refurnish it; the number of doors changed. A door the vault
    check refuses is put back as it was, and ``left`` hears why."""
    # Held to the check AFTER the refurnish: a piece standing in the swing is furnishing the refurnish moves, so only
    # what furnish does not own -- a stair, a wall -- can refuse a door.
    found, _left = gates(spec)
    if not found:
        return 0
    trial = copy.deepcopy(spec)
    for _part, op, face in gates(trial)[0]:
        op.update(VAULT_DOOR)
        op["face"] = face
    migrate_furnish_recipes.migrate(trial)
    why = _refused(trial)
    if why:
        if left is not None:
            left.extend("kept the door: " + w for w in why)
        return 0
    spec.clear()
    spec.update(trial)
    return len(found)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    changed = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)
        if name.startswith("lf_") or not name.startswith(FAMILIES):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        _found, left = gates(d)
        before = json.dumps(d, indent=1) + "\n"
        n = migrate(d, left)
        for why in left:
            print(f"[bank_vault_doors] {name}: left, {why}")
        after = json.dumps(d, indent=1) + "\n"
        if after == before:
            continue
        changed += 1
        print(f"[bank_vault_doors] {name}: {n} vault gate(s) -> vault door")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(after)
    verb = "would change" if check else "changed"
    print(f"[bank_vault_doors] {changed} spec(s) {verb}")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
