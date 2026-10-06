"""A connection that holds on one voxel grid and not another is not one a
level can count on (0.189.0).

Measured 2026-10-06, roadmap 189 (`docs/findings/stairwell_on_one_grid_in_four/`
at the factory root): deli_a03's objective upstairs joins its ground floor at
8 of 32 grid origins. This gate baked one origin, at the building's own
bounds, and passed it. Cold run 9185's site put the building on another grid
and its walk test lost two candidates of three. A census of the library at
eight origins found the same in ten more shells.

`nav_gate.gd` now bakes each shell again at eight origins and writes, beside
each traversable stair and each checked marker, the list of origins where it
connected (`grid`). It decides nothing; `scope_markers` does, here, where a
test can put it wrong on purpose first -- the same split as the marker scope.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nav_gate                      # noqa: E402

FOOTPRINT = [38.0, 28.0]             # deli_a03: half-extents 19 x 14
GD = os.path.join(HERE, "godot", "addon", "deli_counter", "nav_gate.gd")


def _row(name, x, y, reachable, grid=None):
    r = {"name": name, "type": name.split("_")[0], "x": x, "y": y,
         "snap": 0.3, "reachable": reachable}
    if grid is not None:
        r["grid"] = grid
    return r


def _markers(rows):
    return {"checked": len(rows),
            "reachable": sum(1 for r in rows if r["reachable"]),
            "unreachable": ["%s (snap 0.3m)" % r["name"] for r in rows
                            if not r["reachable"]],
            "detail": rows}


ALL = [True] * 8
FOUR = [True, False, True, False, False, True, True, False]


def test_reached_at_every_origin_is_navigable():
    rows = [_row("objective_A", 10.0, -8.0, True, ALL),
            _row("patrol_point_P01", -2.0, -11.0, True, ALL)]
    _, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT)
    assert nav is True, why


def test_reached_here_but_not_at_every_origin_is_not_navigable():
    """deli_a03's objective, as the census measured it: 4 of 8."""
    rows = [_row("objective_A", 10.0, -8.0, True, FOUR),
            _row("patrol_point_P01", -2.0, -11.0, True, ALL)]
    scoped, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT)
    assert nav is False, why
    assert "grid" in why and "objective_A" in why, why
    assert scoped["interior_grid_fragile"] == ["objective_A (4/8 grid origins)"]


def test_the_unreachable_list_keeps_its_format():
    """Other tools parse `interior_unreachable`; a grid-fragile marker is
    reported beside it, never inside it."""
    rows = [_row("objective_A", 10.0, -8.0, True, FOUR)]
    scoped, _, _ = nav_gate.scope_markers(_markers(rows), FOOTPRINT)
    assert scoped["interior_unreachable"] == []


def test_a_fragile_marker_outside_the_building_is_still_deferred():
    """The street is the site's question at every grid, not this bake's."""
    rows = [_row("objective_A", 10.0, -8.0, True, ALL),
            _row("extraction_STREET", 8.0, -16.0, True, FOUR)]
    _, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT)
    assert nav is True, why


def test_a_result_from_before_the_sweep_reads_as_it_did():
    rows = [_row("objective_A", 10.0, -8.0, True)]
    scoped, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT)
    assert nav is True, why
    assert scoped["interior_grid_fragile"] == []


def test_a_stair_that_climbs_on_some_grids_only_is_not_navigable():
    result = {"stairs": [{"id": "deli_stair_up", "status": "ok", "grid": FOUR},
                         {"id": "deli_stair_down", "status": "ok", "grid": ALL}]}
    assert nav_gate.grid_fragile_stairs(result) == ["deli_stair_up"]
    rows = [_row("objective_A", 10.0, -8.0, True, ALL)]
    _, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT,
                                         stairs_ok=True, stairs_grid_ok=False)
    assert nav is False and "grid" in why, why


def test_the_verdict_says_it():
    result = {"exit_code": 0, "stairs_ok": True, "navmesh_polys": 1300,
              "stairs": [{"id": "deli_stair_up", "status": "ok", "detail": "",
                          "grid": FOUR}],
              "markers": {"checked": 1, "reachable": 1, "unreachable": [],
                          "interior_checked": 1, "interior_reachable": 1,
                          "interior_unreachable": [], "exterior_deferred": [],
                          "interior_grid_fragile": ["objective_A (4/8 grid origins)"]},
              "navigable": False, "navigable_reason": "grid"}
    ok, lines = nav_gate.verdict(result)
    assert ok, "the exit verdict stays the base bake's stairs"
    text = "\n".join(lines)
    assert "4 of 8 voxel-grid origins" in text, text
    assert "objective_A (4/8 grid origins)" in text, text


def test_the_gate_sweeps_fractions_of_a_cell():
    """Read as source: the origins are fractions of the contract's cell, the
    sweep moves the bake through filter_baking_aabb, and the per-origin
    marker check is the quiet form of the one the report prints."""
    src = open(GD, encoding="utf-8").read()
    m = re.search(r"const GRID_FRACTIONS := (\[.*?\]\])", src, re.S)
    assert m, "no GRID_FRACTIONS in nav_gate.gd"
    fr = eval(m.group(1).replace("\n", " ").replace("\t", " "))  # noqa: S307
    assert len(fr) == 8 and len({f[0] for f in fr}) == 8 and len({f[2] for f in fr}) == 8
    assert all(0.0 <= v < 1.0 for f in fr for v in f)
    body = src[src.index("func _grid_sweep"):]
    body = body[:body.index("\nfunc ", 1)]
    assert "filter_baking_aabb" in body
    assert "CELL_SIZE" in body and "CELL_HEIGHT" in body
    assert "_check_markers(gp, nm, graph, false)" in body
