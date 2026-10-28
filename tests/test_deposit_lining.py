"""A bank's deposit vault is lined with boxes (0.288.0, the factory's roadmap 321).

The walker, of the bank's vault: "that vault room needs some love", with a photograph of a room walled floor to
ceiling in numbered boxes. A library bank's deposit wall was one authored 2 m panel. `line_deposit_vaults` fills the
rest of each partition round the vault it faces with more deposit openings -- each a real, drillable module -- and
furnish makes that room the boxes and a viewing table, not a money room.

FAILS ON 0.287.1: there is no `deposit_vault_ids`, no lining and no `bank_deposit`.
"""
import copy
import glob
import json
import os

import level_design as L

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
LINED = {"bank_branch_a02": "vault", "bank_branch_a03": "vault", "bank_job": "vault"}


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _lining(d):
    """[(partition, opening)] the lining wrote."""
    return [(p, o) for p in d.get("partitions") or [] for o in p.get("openings") or []
            if str(o.get("tag", "")).startswith(L.DEPOSIT_LINING_TAG)]


def test_the_vault_a_deposit_wall_faces_is_the_innermost_room_past_it():
    for name, room in LINED.items():
        assert L.deposit_vault_ids(_spec(name)) == {room}, name
    assert L.deposit_vault_ids(_spec("bank_branch_a04")) == set()      # no authored deposit wall, no deposit vault


def test_the_lining_runs_the_vaults_partitions_clear_of_every_opening_and_corner():
    for name, rid in LINED.items():
        d = _spec(name)
        room = next(r for r in d["rooms"] if r["id"] == rid)
        x0, y0, x1, y1 = room["bounds"]
        units = _lining(d)
        assert len(units) >= 3, (name, len(units))
        for p, o in units:
            lo, hi = float(p["start"]), float(p["end"])
            mid, run = (lo + hi) / 2.0, hi - lo
            u, w = mid + o["pos"] * run, o["width"]
            a, b = (y0, y1) if p["axis"] == "Y" else (x0, x1)
            line = float(p["pos"])
            assert line in ((x0, x1) if p["axis"] == "Y" else (y0, y1)), (name, p)
            # it faces the room
            toward = {"Y": "E" if line == x0 else "W", "X": "N" if line == y0 else "S"}[p["axis"]]
            assert o["face"] == toward, (name, o)
            assert 0.6 <= w <= L.DEPOSIT_LINING_MAX_W, (name, o)
            assert a + L.DEPOSIT_LINING_MARGIN - 1e-6 <= u - w / 2.0 and u + w / 2.0 <= b - L.DEPOSIT_LINING_MARGIN + 1e-6
            for other in p["openings"]:
                if other is o:
                    continue
                ou = mid + other["pos"] * run
                ow = float(other.get("width") or 1.0)
                gap = abs(u - ou) - (w + ow) / 2.0
                assert gap >= -1e-6, (name, o, other)


def test_lining_is_idempotent_and_leaves_every_other_bank_alone():
    for name in LINED:
        d = _spec(name)
        again = copy.deepcopy(d)
        L.line_deposit_vaults(again)
        assert again["partitions"] == d["partitions"], name
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        n = os.path.basename(p)[:-5]
        if n.startswith("lf_") or n in LINED:
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        assert not _lining(d), n


def test_a_deposit_vault_is_the_boxes_and_a_table():
    for name, rid in LINED.items():
        d = _spec(name)
        room = next(r for r in d["rooms"] if r["id"] == rid)
        x0, y0, x1, y1 = room["bounds"]
        inside = [v["name"] for v in d["volumes"] if x0 <= v.get("x", 1e9) <= x1 and y0 <= v.get("y", 1e9) <= y1
                  and L._volume_story(d, v) == int(room.get("story", 0) or 0)]
        assert any(n.startswith("table_count") for n in inside), (name, inside)
        assert not any(n.startswith(("shelf_cash", "cash_cart")) for n in inside), (name, inside)


def test_the_built_deposit_vaults_carry_their_units_as_deposit_slots():
    for name in LINED:
        slots = json.load(open(os.path.join(BUILD, name + ".slots.json"), encoding="utf-8"))["slots"]
        deposit = [s for s in slots if s["role"] == "safe_deposit_boxes"]
        assert len(deposit) >= len(_lining(_spec(name))) + 1, (name, len(deposit))
