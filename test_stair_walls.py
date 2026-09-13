"""A stair's hole may not cut a wall or open under a doorway (layout_lint L21).

THE CAPTURED CASE is the walker's frame from cold run 9048: `bank_branch_a03`'s
basement stair, whose hole straddled the manager's office wall by 1.15 m so the
builder deleted 3.4 m of it, with the office door beside the gap. These pin
the rule on that seat, the designs it must leave alone, the re-seat that
repairs a finding without making anything else worse, and the generator.

    python -m pytest test_stair_walls.py -q
"""
import contextlib
import copy
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint  # noqa: E402
import presets  # noqa: E402
import stair_pitch  # noqa: E402

#: `a03_stair_down` where the walker found it (DC 0.125.0).
_BANK_SEAT = {"x": -11.0, "y": 4.0, "facing": "S"}


def _spec(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def _bank_at_the_walkers_seat():
    d = _spec("bank_branch_a03")
    st = [s for s in d["stairs"] if s["id"] == "a03_stair_down"][0]
    st.update(_BANK_SEAT)
    return d


def test_the_walkers_stair_cuts_the_office_wall():
    out = layout_lint.stair_wall_findings(_bank_at_the_walkers_seat())
    cuts = [f for f in out if "stair cuts a wall" in f and "a03_stair_down" in f]
    assert len(cuts) == 1, out
    assert "pos=2" in cuts[0] and "1.15 m from one edge" in cuts[0], cuts[0]


def test_the_shipped_bank_is_clean_and_the_gate_fails_the_old_seat():
    assert layout_lint.stair_wall_findings(_spec("bank_branch_a03")) == []
    fails, _warns, _ = layout_lint.gate(_bank_at_the_walkers_seat())
    assert any(f.startswith("L21") for f in fails), fails


def test_a_stairs_own_door_at_its_top_is_not_a_finding():
    """The delis' `office_stair_door` stands just past the top of the
    basement flight on purpose."""
    for name in ("deli_a01", "deli_a02", "deli_a03"):
        assert layout_lint.stair_wall_findings(_spec(name)) == [], name


def test_a_door_a_body_width_from_the_hole_is_not_a_finding():
    """The office preset's stair core: side doors exactly 1.00 m from the
    hole, the derived approach depth (2 * body radius + 0.3)."""
    assert abs(layout_lint.DOOR_APPROACH_M - 1.0) < 1e-9
    with contextlib.redirect_stdout(io.StringIO()):
        d = presets.make("office")
    assert layout_lint.stair_wall_findings(d) == []


def test_a_door_closer_than_that_is_a_finding():
    with contextlib.redirect_stdout(io.StringIO()):
        d = presets.make("office")
    for p in d["partitions"]:
        if p["axis"] == "Y" and abs(p["pos"]) == 3.0:
            p["pos"] = 2.5 if p["pos"] > 0 else -2.5
    out = layout_lint.stair_wall_findings(d)
    assert out and all("door opens onto a stair hole" in f or
                       "stair cuts a wall" in f for f in out), out


def test_a_stair_arriving_through_its_own_doorway_is_a_warning():
    d = _spec("strip_retail_a01")
    warns = []
    assert layout_lint.stair_wall_findings(d, warns) == []
    assert len(warns) == 1 and "arrives through a wall" in warns[0], warns


def test_clear_walls_moves_the_stair_and_nothing_gets_worse():
    d = _bank_at_the_walkers_seat()
    before = (set(layout_lint.gate(d)[0]) | stair_pitch._stair_errors(d)
              | stair_pitch._rect_intrusions(d))
    r = stair_pitch.clear_walls(d)
    assert "a03_stair_down" in r["reseated"] and not r["unresolved"], r
    after = (set(layout_lint.gate(d)[0]) | stair_pitch._stair_errors(d)
             | stair_pitch._rect_intrusions(d))
    assert not (after - before), after - before
    assert not [f for f in layout_lint.stair_wall_findings(d)
                if "a03_stair_down" in f]
    # the walls did not move
    assert d["partitions"] == _bank_at_the_walkers_seat()["partitions"]


def test_clear_walls_leaves_a_clean_spec_byte_identical():
    d = _spec("cr_pawn")
    before = copy.deepcopy(d)
    r = stair_pitch.clear_walls(d)
    assert r == {"reseated": {}, "unresolved": []}
    assert d == before


def test_no_preset_generates_a_stair_that_cuts_a_wall():
    for name in sorted(presets.REGISTRY):
        with contextlib.redirect_stdout(io.StringIO()):
            d = presets.make(name)
        if not d.get("footprint_x"):
            continue
        assert layout_lint.stair_wall_findings(d) == [], name


def test_every_placed_piece_names_a_material():
    import migrate_prop_materials as m
    for name in ("bank_branch_a03", "deli_a01", "night_deli", "cr_deli"):
        assert m.unmaterialled(_spec(name)) == [], name
