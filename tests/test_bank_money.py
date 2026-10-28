"""A bank lobby's officers' desks and a bank vault's money (0.286.0, the factory's roadmap 321).

The walker, of the bank after the interior pass: "add the lobby desks" -- its 390 m2 lobby stood a check desk, a
queue, chairs and plants -- and "we need to make the cash! in the vault room!": the vault held a cash cart, two safes
and a count table with a few bundles on it, each bundle a note's size. A bank lobby's floor takes desks (comp 5's
grey steel desks and CRTs, `desk`'s `office` stock); a bank's vault anchors a money rack -- Zoo 1.142.0's `shelving`
stock `vault`, strapped bricks and deposit bags -- and a cash cart beside its safe, and its wall run's racks are
money racks.

FAILS ON 0.285.0: there is no `shelf_cash`, a bank lobby's floor is empty, and its vault's racks are a back office's.
"""
import glob
import json
import os

import level_design
import prop_species

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
BANKS = ("bank_branch_a02", "bank_branch_a03", "bank_branch_a04", "bank_job", "bank_tower_a01", "bank_tower_a02",
         "bank_tower_a03")


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _in(d, v, room):
    x0, y0, x1, y1 = room["bounds"]
    return (x0 <= v.get("x", 1e9) <= x1 and y0 <= v.get("y", 1e9) <= y1
            and level_design._volume_story(d, v) == int(room.get("story", 0) or 0))


def _rooms(d, kind):
    b = level_design.club_building_id(d)
    return [r for r in d["rooms"] if level_design._room_kind(r, b) == kind]


def test_the_recipes():
    lobby, vault = level_design._RECIPES["bank_lobby"], level_design._RECIPES["bank_vault"]
    assert lobby["floor"] == ("desk",)
    assert vault["all_anchors"] and set(vault["anchors"]) == {"shelf_cash", "safe_floor", "cash_cart"}
    assert "shelf_run" not in vault["wall"] and "shelf_cash" in vault["wall"]
    # the control: any other vault, a deli's back safe among them, keeps its back office's rack and no money
    assert "shelf_cash" not in str(level_design._RECIPES["vault"])
    piece = level_design._PIECES["shelf_cash"]
    assert piece["stock"] == "vault" and piece["where"] == "wall" and piece["front"]
    assert prop_species.species_for_name("shelf_cash_r3a1da818_2") == "shelving"


def test_every_library_bank_lobby_stands_a_desk_and_every_vault_its_money():
    for name in BANKS:
        d = _spec(name)
        lobbies, vaults = _rooms(d, "bank_lobby"), _rooms(d, "bank_vault")
        assert lobbies and vaults, name
        assert any(_in(d, v, r) and v["name"].startswith("desk") for r in lobbies for v in d["volumes"]), name
        for r in vaults:
            inside = [v["name"] for v in d["volumes"] if _in(d, v, r)]
            for piece in ("shelf_cash", "cash_cart", "safe_floor"):
                assert any(n.startswith(piece) for n in inside), (name, r["id"], piece, inside)


def test_no_other_building_has_a_money_rack():
    seen = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        n = os.path.basename(p)[:-5]
        if n.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        racks = [v["name"] for v in d.get("volumes", []) if str(v.get("name", "")).startswith("shelf_cash")]
        if n in BANKS:
            seen += len(racks)
        else:
            assert not racks, (n, racks)
    assert seen >= 20, seen


def test_the_built_racks_ask_zoo_for_the_vaults_stock():
    racks = 0
    for p in glob.glob(os.path.join(BUILD, "*.slots.json")):
        for s in json.load(open(p, encoding="utf-8"))["slots"]:
            if s["slot_id"].startswith("shelf_cash"):
                assert s["species"] == "shelving" and s["stock"] == "vault", (os.path.basename(p), s)
                racks += 1
            elif s.get("species") == "shelving":
                assert s.get("stock") != "vault", (os.path.basename(p), s["slot_id"])
    assert racks >= 20, racks
