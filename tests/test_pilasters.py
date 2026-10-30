"""A civic building's pilasters (0.294.0, factory roadmap 324): solid piers at the bays its openings imply, Zoo's
`wall_pilaster` (>= 1.150.0). Pure: `pilasters.plan` is tested without a build."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pilasters as P  # noqa: E402
import prop_species  # noqa: E402

#: bank_branch_a02: 30 x 22, walls 0.3 thick; on its east side the first storey's windows at -5.5 and 5.5 (1.6 wide)
#: and the ground storey's door at 5.5 (1.25)
BANK = SimpleNamespace(name="bank_branch_a02", facade=False)
EXTENT = (-15.0, -11.0, 15.0, 11.0)
EAST = [(-5.5, 1.6), (5.5, 1.6), (5.5, 1.25)]


def _plan(spec=BANK, by_side=None, z1=6.9):
    return P.plan(spec, EXTENT, 0.3, 0.0, z1, by_side if by_side is not None else {"E": EAST})


def test_the_banks_east_flank_takes_one_pier_midway_between_its_windows():
    """FAILS ON 0.293.0: no pilasters."""
    assert P.lines(22.0, EAST) == [0.0]
    east = [p for p in _plan() if p["side"] == "E"]
    assert len(east) == 1
    (x, y, z), (sx, sy, sz) = east[0]["centre"], east[0]["size"]
    assert y == pytest.approx(0.0) and z == pytest.approx(6.9 / 2) and sz == pytest.approx(6.9)
    # it stands PROUD off the wall's outer face (15.15) and BURY into it, PIER_W along the wall
    assert x - sx / 2 == pytest.approx(15.15 - P.BURY) and x + sx / 2 == pytest.approx(15.15 + P.PROUD)
    assert sy == pytest.approx(P.PIER_W)


def test_no_pier_near_a_corner_or_an_opening():
    for run, ops in ((22.0, EAST), (30.0, [(-9.0, 1.6), (-3.0, 1.6), (3.0, 1.6), (9.0, 1.6)]),
                     (14.0, []), (40.0, [(0.0, 3.0)])):
        for u in P.lines(run, ops):
            assert abs(u) <= run / 2 - P.CORNER_CLEAR - P.PIER_W / 2 + 1e-9
            for c, w in ops:
                assert abs(u - c) >= w / 2 + P.OPENING_CLEAR + P.PIER_W / 2 - 1e-9


def test_a_long_blank_wall_is_divided_into_bays_no_longer_than_max_bay():
    us = P.lines(40.0, [])
    edges = [-20.0] + us + [20.0]
    assert us and max(b - a for a, b in zip(edges, edges[1:])) <= P.MAX_BAY + 1e-9
    assert P.lines(P.MAX_BAY, []) == []                 # a wall one bay long is left alone
    assert P.lines(12.0, []) == [0.0]                   # two bays: one pier between them


def test_two_windows_too_close_for_a_pier_get_none_between_them():
    assert not [u for u in P.lines(22.0, [(-0.9, 1.0), (0.9, 1.0)]) if -0.9 < u < 0.9]


def test_only_a_civic_building_that_is_not_an_empty_takes_them():
    assert _plan(SimpleNamespace(name="card_shop_a01", facade=False)) == []
    assert _plan(SimpleNamespace(name="bank_branch_a02", facade=True)) == []
    assert P.is_civic("credit_union_a01") and P.is_civic("post_office_a01") and not P.is_civic("train_yard_a01")


def test_its_front_faces_out_and_its_slot_is_the_collider():
    """A slot's rotation turns the module's +Y onto its bearing; the front, -Y, faces rot + 180."""
    ps = _plan(by_side={"N": [], "S": [], "E": EAST, "W": []})
    want = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
    for p in ps:
        assert (p["rot_y"] + 180.0) % 360.0 == want[p["side"]]
        w, d, h = p["dims"]
        assert w == P.PIER_W and d == pytest.approx(P.PROUD + P.BURY) and h == pytest.approx(p["size"][2])
    assert prop_species.species_for_name(ps[0]["slot_id"]) == "wall_pilaster"
    assert prop_species.material_for("wall_pilaster", "concrete") == "plaster"
