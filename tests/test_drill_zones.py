"""Where a crew stands to drill (0.291.0, the factory's roadmap 323).

The walker: "opening the safe should be a gameplay event where you have to stand in an area for a certain amount of
time close to the 'drill' and then the door opens", then "no drill time from the factory ... These will be networked
events programmed somwhere else...we just want the seams/hooks in place". Every vault door and deposit wall writes one
`drill` marker: a zone in front of it, sent on entry and exit, naming the interactive it opens. FAILS ON 0.290.0, which
writes none.
"""
import json
import math
import os

import score_alarms

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
BANKS = ("bank_branch_a02", "bank_branch_a03", "bank_job", "bank_tower_a01", "bank_branch_a04", "credit_union_a03")


def _built(name):
    slots = json.load(open(os.path.join(BUILD, name + ".slots.json"), encoding="utf-8"))["slots"]
    gp = json.load(open(os.path.join(BUILD, name + ".gameplay.json"), encoding="utf-8"))
    return slots, gp


def _room(rooms, x, y, story):
    holding = [r for r in rooms if int(r.get("story", 0) or 0) == story
               and r["bounds"][0] <= x <= r["bounds"][2] and r["bounds"][1] <= y <= r["bounds"][3]]
    return min(holding, key=lambda r: (r["bounds"][2] - r["bounds"][0]) * (r["bounds"][3] - r["bounds"][1]),
               default=None)


def test_every_vault_door_and_deposit_wall_has_one_drill_zone_naming_it():
    for name in BANKS:
        slots, gp = _built(name)
        drills = {m["id"]: m for m in gp["markers"] if m["type"] == "drill"}
        want = [s for s in slots if any(s.get(k) == v for k, v in score_alarms.DRILL_FIXTURES)]
        assert want and len(drills) == len(want), (name, len(drills), len(want))
        for s in want:
            m = drills["drill_" + s["slot_id"]]
            assert m["meta"]["target"] == s["interactive"]["id"] and m["meta"]["fixture"] == s["role"]
            assert m["meta"]["event"] == "zone.drill" and m["meta"]["fires"] == ["on_enter", "on_exit"]
            assert m["meta"]["repeat"] == "edge" and m["meta"]["radius"] > 0


def test_a_vault_doors_zone_stands_on_its_approach_and_reaches_across_its_face():
    """The zone's centre is in the room the door is entered from, not the vault; a body at either jamb is in it."""
    import agent_contract
    body = agent_contract.body_radius()
    for name in ("bank_branch_a02", "bank_job", "bank_tower_a01"):
        slots, gp = _built(name)
        rooms = gp["rooms"]
        for s in [s for s in slots if s.get("role") == "vault_door"]:
            m = next(m for m in gp["markers"] if m["id"] == "drill_" + s["slot_id"])
            x, y, _z = s["transform"]["translation"]
            story = s.get("story", 0)
            vault = _room(rooms, *(score_alarms.drill_zone(dict(s, transform=dict(s["transform"],
                          rot_y=s["transform"].get("rot_y", 0) + 180)), body)[:2]), story)
            here = _room(rooms, m["x"], m["y"], story)
            assert here is not None and vault is not None and here["id"] != vault["id"], (name, here, vault)
            half = s["fit"]["openings"][0]["width"] / 2.0
            assert math.isclose(m["meta"]["radius"], half + body, abs_tol=1e-3)


def test_no_drill_time_anywhere():
    """The walker: "no drill time from the factory". A drill marker carries where, how big, which edges, what it
    opens -- nothing about how long."""
    _slots, gp = _built("bank_branch_a02")
    for m in [m for m in gp["markers"] if m["type"] == "drill"]:
        assert set(m["meta"]) == {"event", "fires", "repeat", "radius", "target", "fixture"}
