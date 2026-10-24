"""Every hole in a stacked shaft is declared, and its drop lands where a body would (0.232.0, the factory's
roadmap 173).

Cold run 9329's export refused county_hospital_001: the generated hospital stacks an elevator shaft's holes on every
storey and declared only storey 1's, so the storey-2 rim fell 7.2 m with nothing declaring it. And a declared drop
ended on "the floor below", which over a stacked shaft is cut too.

Run: python -m pytest -q tests/test_hospital_shaft.py
"""
import ladder
import presets


def _shaft(spec):
    holes = {(h["story"], h["x"], h["y"]) for h in spec.get("slab_holes") or []}
    declared = {(v["story"], v["x"], v["y"]) for v in spec.get("vertical_links") or []
                if v.get("kind") == "floor_hole"}
    return holes, declared


def test_every_stacked_hole_is_declared_at_three_floors():
    holes, declared = _shaft(presets.hospital(floors=3))
    assert len(holes) == 2 and holes <= declared, (holes, declared)


def test_every_stacked_hole_is_declared_at_four_floors():
    holes, declared = _shaft(presets.hospital(floors=4))
    assert len(holes) == 3 and holes <= declared, (holes, declared)


def test_a_drop_falls_through_the_cuts_below_it():
    shaft = [{"story": s, "x": 0.0, "y": 12.0, "size_x": 2.6, "size_y": 2.6} for s in (1, 2, 3)]
    assert ladder.drop_landing(3, 0.0, 12.0, shaft) == 0
    assert ladder.drop_landing(2, 0.0, 12.0, shaft) == 0
    assert ladder.drop_landing(1, 0.0, 12.0, shaft) == 0
    # beside the shaft, the floor below holds
    assert ladder.drop_landing(3, 5.0, 12.0, shaft) == 2


def test_a_single_cut_lands_on_the_floor_below():
    one = [{"story": 2, "x": 0.0, "y": 0.0, "size_x": 2.0, "size_y": 2.0}]
    assert ladder.drop_landing(2, 0.0, 0.0, one) == 1


def test_the_link_ends_where_it_lands():
    link = ladder.drop_nav_link("h", 2, 0.0, 12.0, 2.6, 2.6, 3.6, land_story=0)
    assert link["start_position"][2] == 7.2 and link["end_position"][2] == 0.0
    plain = ladder.drop_nav_link("h", 2, 0.0, 12.0, 2.6, 2.6, 3.6)
    assert plain["end_position"][2] == 3.6
