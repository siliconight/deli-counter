"""A bank's rooms are lit and floored as the walker's bank comps (0.280.0, the factory's roadmap 321).

The comps (the factory's docs/reference/BANK_INTERIOR_COMPS.md): "bright, even ceilings" in every public room, terrazzo
or pale tile under the public in five of twelve, the money "in hard rooms ... all lit by bare tubes". Measured before
(docs/findings/bank_interior/): bank_branch_a02's lobby carpeted maroon under one lamp a 39 m2, a mean of 37; its vault
floor under bare bulbs, one a 55 m2. Now a bank's public room (`public_entry`) takes a selling room's lamp density, the
bake-only reach and a tile floor, and its rooms below grade or over the take take tubes.

FAILS ON 0.279.0: `lights.is_bank` does not exist, and a bank's lobby is carpet under one lamp a 39 m2.
"""
import json
import os
import types

import pytest

import floors
import hole_causes
import lights

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
BANKS = ("bank_branch_a02", "bank_branch_a03", "bank_branch_a04", "bank_job", "bank_tower_a01", "bank_tower_a02")


def _cap(_story):
    return 0.3


LOBBY = {"id": "lobby", "role": "public_entry", "story": 0, "center": [0.0, -4.5, 0.0],
         "bounds": [-15.0, -11.0, 15.0, 2.0]}
OFFICE = {"id": "manager_office", "role": "fortifiable", "story": 0, "center": [-7.5, 6.5, 0.0],
          "bounds": [-15.0, 2.0, 0.0, 11.0]}
VAULT = {"id": "vault", "role": "objective_room", "story": -1, "objective": True, "center": [-4.0, -7.0, -3.6],
         "bounds": [-8.0, -11.0, 0.0, -3.0]}


def test_a_bank_is_named_by_a_whole_word():
    for b in ("bank_branch_a02", "bank_job", "bank_tower_a01", "bank"):
        assert lights.is_bank(b), b
    for b in ("riverbank_house", "supermarket_a01", "pawn_shop_a01", None, ""):
        assert not lights.is_bank(b), b


def test_a_banks_public_floor_is_tile_and_anyone_elses_lobby_keeps_its_carpet():
    room = types.SimpleNamespace(id="lobby", role="public_entry")
    assert floors._material(room, "floor", floors.FLOOR_BY_ROLE, "concrete", "bank_branch_a02") == "tile"
    assert floors._material(room, "floor", floors.FLOOR_BY_ROLE, "concrete", "hotel_a01") == "carpet"
    assert floors._material(room, "floor", floors.FLOOR_BY_ROLE, "concrete") == "carpet"
    # a room's own material still wins
    own = types.SimpleNamespace(id="lobby", role="public_entry", floor_material="wood")
    assert floors._material(own, "floor", floors.FLOOR_BY_ROLE, "concrete", "bank_job") == "wood"


def test_the_hole_rule_asks_the_floor_as_the_slab_does():
    spec = {"name": "bank_job", "default_material": "concrete"}
    assert hole_causes._surface(spec, {"id": "lobby", "role": "public_entry"}, "floor") == "tile"
    spec = {"name": "hotel_a01", "default_material": "concrete"}
    assert hole_causes._surface(spec, {"id": "lobby", "role": "public_entry"}, "floor") == "carpet"


def _rows(rooms, business):
    out = {}
    for a in lights.derive_light_anchors(rooms, [], 3.6, cap_thick=_cap, wall_thick=0.3,
                                         bake_reach_rooms=lights._bake_reach_rooms(rooms, business),
                                         selling_rooms=lights._selling_rooms(rooms, business),
                                         tube_rooms=lights._tube_rooms(rooms, business)):
        if a["type"] in ("fluorescent", "pendant", "dome"):
            out.setdefault(a["room"], []).append(a)
    return out


def test_a_banks_lobby_is_lit_as_a_selling_room_and_its_money_by_tubes():
    bank = _rows([LOBBY, OFFICE, VAULT], "bank_branch_a02")
    other = _rows([LOBBY, OFFICE, VAULT], "hotel_a01")
    lamps = lambda rows: sum(a["row"]["count"] for a in rows)          # noqa: E731
    assert lamps(bank["lobby"]) > lamps(other["lobby"])
    assert all(a.get("bake_reach", 0.0) > 0.0 for a in bank["lobby"])
    assert not any("bake_reach" in a for a in other["lobby"])
    assert {a["type"] for a in bank["vault"]} == {"fluorescent"}
    assert {a["type"] for a in other["vault"]} == {"pendant"}          # the control: a cellar stays moody
    # a room the rule does not name is the room it was
    assert bank["manager_office"] == other["manager_office"]


@pytest.mark.parametrize("name", BANKS)
def test_every_built_banks_public_floor_is_tile_and_no_room_is_moody(name):
    slots_p = os.path.join(BUILD, name + ".slots.json")
    lights_p = os.path.join(BUILD, name + ".lights.json")
    if not (os.path.exists(slots_p) and os.path.exists(lights_p)):
        pytest.skip("%s is not built" % name)
    spec = json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))
    public = {r["id"] for r in spec["rooms"] if r.get("role") == "public_entry"}
    assert public, name
    slots = json.load(open(slots_p, encoding="utf-8"))["slots"]
    floor = {s["slot_id"][len("floor_"):]: s.get("material") for s in slots if s["slot_id"].startswith("floor_")}
    assert all(floor[r] == "tile" for r in public), (name, {r: floor.get(r) for r in public})
    anchors = json.load(open(lights_p, encoding="utf-8"))["anchors"]
    assert not any(a.get("type") == "pendant" for a in anchors), name
    assert all(a.get("bake_reach", 0.0) > 0.0 for a in anchors
               if a.get("type") == "fluorescent" and a.get("room") in public), name
