"""A wall may not stand under a hole in its own ceiling (layout_lint L27, 0.235.0; the factory's roadmap 260).

THE CAPTURED CASE: 0.234.0's open-floor table walled the delis' kitchens from their market aisles along x 7, and their
2.2 m drop at (8, -4) spans x 6.9..9.1 -- the wall's centreline 0.1 m inside the hole's edge, its new door under the
hole, seen in the factory's cold run 9338. L27 names such a wall, reading walls as the builder stands them; the table
slides a hole off a wall it lays, or refuses the pair, and slides one off a WALL pair's wall already standing.

FAIL ON 0.234.0: there is no L27 (`ceiling_hole_walls`); the table lays the wall and leaves the hole over it; and the
library's six delis carry their drop over the kitchen wall.
"""
import glob
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402
import open_floor_rules              # noqa: E402
import presets                       # noqa: E402

#: The walls the library stood under a hole before the table: named by L27, not moved by it (see L27's docstring).
BEFORE_THE_TABLE = {("bank", "int_0_1"), ("cbp_town_finale_midbalanced_schemafixed", "int_0_2"),
                    ("final_stand", "int_0_0")}


def _two_storeys(hole_x=0.75, wall=True, back=(0.0, -5.0, 5.0, 5.0)):
    """Story 0: rooms front (x -5..0) and back meeting along x = 0, a 0.3 m wall there with a door when `wall`, a door
    in from the west and one from the east; story 1: one room over both. A 2.2 m hole in story 1's floor centred at
    (hole_x, 0), authored twice as the delis' drop is: a slab hole and a floor_hole link."""
    return {"name": "t", "footprint_x": 10.0, "footprint_y": 10.0, "n_stories": 2, "wall_thick": 0.3, "grid": 0.5,
            "rooms": [{"id": "front", "story": 0, "bounds": [-5.0, -5.0, 0.0, 5.0]},
                      {"id": "back", "story": 0, "bounds": list(back)},
                      {"id": "loft", "story": 1, "bounds": [-5.0, -5.0, 5.0, 5.0]}],
            "partitions": ([{"story": 0, "axis": "Y", "pos": 0.0, "start": -5.0, "end": 5.0,
                             "openings": [{"kind": "door", "pos": 0.0, "width": 1.25, "tag": "front_to_back"}]}]
                           if wall else []),
            "slab_holes": [{"story": 1, "x": hole_x, "y": 0.0, "size_x": 2.2, "size_y": 2.2}],
            "vertical_links": [{"kind": "floor_hole", "story": 1, "x": hole_x, "y": 0.0, "size_x": 2.2,
                                "size_y": 2.2, "role": "drop"}],
            "ext_walls": [{"wall": "W", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]},
                          {"wall": "E", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}]}


@pytest.fixture
def table(monkeypatch):
    def use(row):
        monkeypatch.setattr(open_floor_rules, "RULES", {("front", "back"): row})
    return use


def test_l27_names_a_wall_under_a_hole_in_its_ceiling():
    s = _two_storeys()
    (w,) = layout_lint.ceiling_hole_walls(s)
    assert (w["wall"], w["index"], w["story"], w["axis"], w["pos"]) == ("int_0_0", 0, 0, "Y", 0.0)
    assert w["into"] == pytest.approx(0.3) and w["along"] == pytest.approx(2.2)
    assert len(w["refs"]) == 2                             # the slab hole and its link are one hole
    (msg,) = [x for x in layout_lint.lint_spec(s, "t")[2] if x.startswith("L27 ")]
    assert "move the hole clear of the wall" in msg


def test_a_hole_flush_with_the_walls_face_is_its_enclosure_not_over_it():
    assert layout_lint.ceiling_hole_walls(_two_storeys(hole_x=0.15 + 1.1)) == []      # its edge on the east face
    (w,) = layout_lint.ceiling_hole_walls(_two_storeys(hole_x=0.10 + 1.1))            # 5 cm past it
    assert w["into"] == pytest.approx(0.05)


def test_a_wall_cut_by_a_hole_in_its_own_floor_is_not_under_the_hole_above():
    """final_stand's storey-1 walls cross its two-storey atrium: the builder cuts them over storey 1's hole (roadmap
    114), so nothing of them stands under storey 2's -- a census of authored partitions counted two that are not
    there."""
    s = _two_storeys()
    s["n_stories"] = 3
    s["rooms"].append({"id": "attic", "story": 2, "bounds": [-5.0, -5.0, 5.0, 5.0]})
    s["partitions"] = [{"story": 1, "axis": "Y", "pos": 0.0, "start": -5.0, "end": 5.0}]
    s["vertical_links"] = []
    s["slab_holes"] = [{"story": 1, "x": 0.0, "y": 0.0, "size_x": 4.0, "size_y": 4.0},
                       {"story": 2, "x": 0.0, "y": 0.0, "size_x": 3.0, "size_y": 3.0}]
    assert layout_lint.ceiling_hole_walls(s) == []
    s["slab_holes"] = s["slab_holes"][1:]                  # nothing cut under it: the wall stands under the upper one
    (w,) = layout_lint.ceiling_hole_walls(s)
    assert w["story"] == 1 and w["along"] == pytest.approx(3.0)


def test_the_table_slides_a_hole_off_the_wall_it_lays(table):
    table(open_floor_rules.WALL)
    s = _two_storeys(wall=False)
    said = open_floor_rules.apply(s)
    (p,) = s["partitions"]
    assert (p["axis"], p["pos"], p["start"], p["end"]) == ("Y", 0.0, -5.0, 5.0)
    # one cell east, the side its centre was on: its west edge on the wall's face, the hole and its link as one
    assert s["slab_holes"][0]["x"] == s["vertical_links"][0]["x"] == 1.25
    assert any("slid +0.50 m in x" in x for x in said), said
    assert layout_lint.ceiling_hole_walls(s) == [] and layout_lint.open_floors(s) == []
    assert open_floor_rules.apply(s) == []


def test_a_hole_that_cannot_open_into_one_room_refuses_the_pair(table):
    table(open_floor_rules.WALL)
    s = _two_storeys(wall=False, back=(0.0, -5.0, 2.0, 5.0))     # 2 m wide below: no slide fits a 2.2 m hole in it
    said = open_floor_rules.apply(s)
    assert s["partitions"] == [] and s["slab_holes"][0]["x"] == 0.75
    assert any("REFUSED" in x and "(L27)" in x for x in said), said
    assert len(layout_lint.open_floors(s)) == 1


def test_a_wall_rows_wall_already_standing_gets_its_hole_slid(table):
    table(open_floor_rules.WALL)
    s = _two_storeys()                                     # the wall stands with the hole over it: the delis on 0.234.0
    said = open_floor_rules.apply(s)
    assert s["slab_holes"][0]["x"] == s["vertical_links"][0]["x"] == 1.25, said
    assert layout_lint.ceiling_hole_walls(s) == []
    assert open_floor_rules.apply(s) == []


def test_a_wall_the_table_did_not_ask_for_keeps_its_hole():
    s = _two_storeys()                                     # front|back has no row
    assert open_floor_rules.apply(s) == [] and len(layout_lint.ceiling_hole_walls(s)) == 1


def test_the_library_stands_no_wall_under_a_hole_but_the_three_it_had_before_the_table():
    named = set()
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(path)[:-5]
        if name.startswith("lf_"):
            continue
        d = json.load(open(path, encoding="utf-8"))
        named |= {(name, w["wall"]) for w in layout_lint.ceiling_hole_walls(d)}
    assert named == BEFORE_THE_TABLE


def test_a_deli_made_from_its_preset_drops_into_its_kitchen():
    d = presets.make("corner_deli")
    assert layout_lint.ceiling_hole_walls(d) == []
    (drop,) = [v for v in d["vertical_links"] if v.get("role") == "vertical_attack_angle"]
    kitchen = [r for r in d["rooms"] if r["id"] == "kitchen"][0]["bounds"]
    assert kitchen[0] <= drop["x"] - drop["size_x"] / 2.0 and drop["x"] + drop["size_x"] / 2.0 <= kitchen[2]
