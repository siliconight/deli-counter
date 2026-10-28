"""A bank's public room is panelled below a chair rail, and its glass front is a storefront (0.285.0, the factory's
roadmap 321).

The walker's bank comps (the factory's docs/reference/BANK_INTERIOR_COMPS.md) put dark wood panelling under white or
beige walls, and a tall window to the street. 0.282.0 plastered a bank's walls floor to ceiling, and its `glass` front
was built as Zoo's opaque `glass_facade` slab: a wall of dark bars inside, a blank one outside (the factory's
docs/findings/bank_interior/, frames 09, 10 and 13).

FAILS ON 0.284.0: no bank carries a panelling slot, and no bank's front is tagged a storefront.
"""
import json
import os

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
#: the banks whose public room has a wall that is not glass, and the two whose front is `glass`
PANELLED = ("bank_branch_a02", "bank_branch_a03", "bank_job")
GLASS_FRONTS = ("bank_branch_a02", "bank_branch_a03", "bank_job")

SHEET_T = 0.006
RAIL_T = 0.009
#: `level_design._WALL_PIECE_AIR`: a wall piece's back stands this far off the face
AIR = 0.01


def _slots(name):
    p = os.path.join(BUILD, name + ".slots.json")
    if not os.path.exists(p):
        pytest.skip("no build of %s" % name)
    return json.load(open(p, encoding="utf-8"))["slots"]


def _gameplay(name):
    return json.load(open(os.path.join(BUILD, name + ".gameplay.json"), encoding="utf-8"))


def _dado(s):
    return "_seg_dado" in s["slot_id"]


def _box(s):
    """A slot's world box (x0, y0, z0, x1, y1, z1): its dims turned by its facing, as `_record_wall_slot` wrote them."""
    d = s["fit"]["dims"]
    t = s["transform"]["translation"]
    along_x = s.get("facing") in ("N", "S", "X")
    w = (d[0], d[1]) if along_x else (d[1], d[0])
    return (t[0] - w[0] / 2, t[1] - w[1] / 2, t[2] - d[2] / 2,
            t[0] + w[0] / 2, t[1] + w[1] / 2, t[2] + d[2] / 2)


def test_a_banks_public_room_is_panelled_below_a_rail():
    for name in PANELLED:
        sl = _slots(name)
        dado = [s for s in sl if _dado(s)]
        assert dado, name
        for s in dado:
            assert s["role"] == "wall" and s["size_mod"] == "end", s["slot_id"]
            assert s["material"] == "wood_panel", s["slot_id"]
            assert s["fit"]["dims"][1] in (SHEET_T, RAIL_T), s["slot_id"]
            # the rail's top is the panelling's, 0.9 m over the wall's foot or a sill
            assert s["fit"]["dims"][2] <= 0.9, s["slot_id"]
        assert {s["fit"]["dims"][1] for s in dado} == {SHEET_T, RAIL_T}, name


def test_the_panelling_stands_on_a_public_rooms_edge_inside_the_wall_pieces_air():
    for name in PANELLED:
        g = _gameplay(name)
        public = [r for r in g["rooms"] if r.get("role") == "public_entry"]
        for s in (s for s in _slots(name) if _dado(s)):
            x0, y0, z0, x1, y1, z1 = _box(s)
            assert max(x1 - x0, y1 - y0) > 0.05
            assert min(x1 - x0, y1 - y0) < AIR, s["slot_id"]
            ok = False
            for r in public:
                bx0, by0, bx1, by1 = r["bounds"]
                if bx0 - 0.2 <= x0 and x1 <= bx1 + 0.2 and by0 - 0.2 <= y0 and y1 <= by1 + 0.2:
                    ok = True
            assert ok, (name, s["slot_id"])


def test_no_two_pieces_of_panelling_overlap():
    for name in PANELLED:
        boxes = [(s["slot_id"], _box(s)) for s in _slots(name) if _dado(s)]
        for i, (na, a) in enumerate(boxes):
            for nb, b in boxes[i + 1:]:
                ov = [min(a[k + 3], b[k + 3]) - max(a[k], b[k]) for k in range(3)]
                assert min(ov) <= 1e-6, (name, na, nb, ov)


def test_no_other_building_is_panelled():
    for name in ("deli_a03", "pharmacy_a01", "supermarket_a01", "credit_union_a01"):
        assert not [s for s in _slots(name) if _dado(s)], name


def test_a_banks_glass_front_is_a_storefront_and_nothing_else_moved():
    for name in GLASS_FRONTS:
        front = [s for s in _slots(name) if s.get("glazing") == "storefront"]
        assert front, name
        assert {s["role"] for s in front} <= {"wall", "doorway"}, name
        g = _gameplay(name)
        public = {r["id"] for r in g["rooms"] if r.get("role") == "public_entry"}
        assert public
    # a pharmacy's and a supermarket's glass fronts are the walker's call, and stay opaque
    for name in ("pharmacy_a01", "supermarket_a01"):
        assert not [s for s in _slots(name) if s.get("glazing") == "storefront"], name


def test_a_vaults_fixtures_ask_for_what_they_are_made_of():
    """The library's deposit-box walls and vault doors took their wall's `concrete`; they ask their species for the
    spec's own `metal`, which is not what either is made of, so each takes its own (`FIXTURE_OPENINGS`)."""
    import glob
    seen = {"safe_deposit_boxes": 0, "vault_door": 0}
    want = {"safe_deposit_boxes": "metal_bare", "vault_door": "metal_painted"}
    for p in glob.glob(os.path.join(BUILD, "*.slots.json")):
        for s in json.load(open(p, encoding="utf-8"))["slots"]:
            if s["role"] in want:
                assert s["material"] == want[s["role"]], (os.path.basename(p), s["slot_id"], s["material"])
                seen[s["role"]] += 1
    assert seen["safe_deposit_boxes"] >= 5 and seen["vault_door"] >= 3, seen
