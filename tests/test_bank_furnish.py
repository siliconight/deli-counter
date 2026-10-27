"""A bank's lobby is furnished as the walker's comps, and a bank's vault keeps a cash cart (0.281.0, roadmap 321).

The comps (the factory's docs/reference/BANK_INTERIOR_COMPS.md): the teller line is the room, "a check desk island
stands mid-floor in front of it", a queue of stanchions, waiting chairs; the money room's "steel cage cart". Measured
before (docs/findings/bank_interior/): bank_branch_a02's 390 m2 lobby stood a bench, two bins and a queue, and the
general lobby recipe a bank shared with a hotel handed it vending, cigarettes, a payphone and a sofa.

FAILS ON 0.280.0: there is no `bank_lobby` or `bank_vault` kind, no check desk and no cash cart.
"""
import glob
import json
import os

import level_design
import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANKS = ("bank_branch_a02", "bank_branch_a03", "bank_branch_a04", "bank_job", "bank_tower_a01", "bank_tower_a02",
         "bank_tower_a03")
NOT_IN_A_BANK = ("vending", "cigarettes", "payphone", "sofa")


def test_a_banks_public_room_and_vault_are_their_own_kinds_and_no_one_elses():
    lobby = {"id": "lobby", "role": "public_entry", "story": 0}
    vault = {"id": "vault_west", "role": "fortifiable", "story": -1}
    assert level_design._room_kind(lobby, "bank_branch_a02") == "bank_lobby"
    assert level_design._room_kind(lobby, "hotel_a01") == "lobby"
    assert level_design._room_kind(vault, "bank_job") == "bank_vault"
    assert level_design._room_kind(vault, "deli_a01") == "vault"           # the control: a deli's back safe


def test_the_bank_lobby_recipe_stands_a_check_desk_and_none_of_the_general_lobbys_extras():
    r = level_design._RECIPES["bank_lobby"]
    assert "check_desk" in r["anchors"]
    named = set(r["anchors"]) | set(r["wall"]) | set(r["floor"]) | {p for c in r["clusters"] for p in c[0]}
    assert not named & set(NOT_IN_A_BANK), named
    assert "cash_cart" in level_design._RECIPES["bank_vault"]["floor"]
    assert "cash_cart" not in level_design._RECIPES["vault"]["floor"]


def test_the_pieces_route_to_zoos_species():
    assert prop_species.species_for_name("check_desk_rcce455f7_1") == "check_desk"
    assert prop_species.species_for_name("cash_cart_r3a1da818_6") == "cash_cart"


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _in(v, room):
    x0, y0, x1, y1 = room["bounds"]
    return x0 <= v.get("x", 1e9) <= x1 and y0 <= v.get("y", 1e9) <= y1


def test_every_library_bank_has_its_check_desk_and_carts_and_no_lobby_extras():
    for name in BANKS:
        d = _spec(name)
        b = level_design.club_building_id(d)
        lobbies = [r for r in d["rooms"] if level_design._room_kind(r, b) == "bank_lobby"]
        vaults = [r for r in d["rooms"] if level_design._room_kind(r, b) == "bank_vault"]
        assert lobbies and vaults, name
        vols = d["volumes"]
        assert any(v["name"].startswith("check_desk") for v in vols), name
        assert any(v["name"].startswith("cash_cart") for v in vols), name
        for r in lobbies:
            story = int(r.get("story", 0) or 0)
            extras = [v["name"] for v in vols if _in(v, r) and v["name"].startswith(NOT_IN_A_BANK)
                      and level_design._volume_story(d, v) == story]
            assert not extras, (name, r["id"], extras)


def test_no_other_building_has_either():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        n = os.path.basename(p)[:-5]
        if n.startswith("lf_") or n in BANKS:
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        names = [str(v.get("name", "")) for v in d.get("volumes") or []]
        assert not any(x.startswith(("check_desk", "cash_cart")) for x in names), n
