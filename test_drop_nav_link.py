"""A declared drop carries its own off-mesh nav link (0.226.0, factory roadmap 173).

Run: pytest -q test_drop_nav_link.py
"""
import ladder as L


def test_drop_link_shape():
    nl = L.drop_nav_link("deli_a01_floor_hole_1_8_-4", 1, 8.0, -4.0, None, None, 3.3)
    assert nl["id"] == "deli_a01_floor_hole_1_8_-4_navlink"
    assert nl["start_position"] == [8.0, -4.0, 3.3]          # over the cut, on the storey whose floor it opens
    assert nl["end_position"] == [8.0, -4.0, 0.0]            # on the floor below
    assert nl["bidirectional"] is False                       # a fall is one-way
    assert nl["required_capability"] == "drop"
    assert nl["cost"] == L.DROP_COST and nl["cost"] > max(L._AI_COST.values())
    assert nl["agent_types"] == ["player", "ai_humanoid"]
    assert nl["access_state"] == "open" and nl["reservation_state"] == "free"


def test_the_hole_is_the_cut_the_builder_makes():
    nl = L.drop_nav_link("x", 2, 13.0, -9.0, None, None, 3.6)
    assert nl["hole"] == [[12.25, -9.75], [13.75, -8.25]]      # 1.5 m square by default, as `_vertical_links` cuts
    nl = L.drop_nav_link("x", 2, 0.0, 0.0, 1.0, 1.2, 3.6)
    assert nl["hole"] == [[-0.5, -0.6], [0.5, 0.6]]


def test_a_roof_hatch_drops_into_the_top_storey():
    nl = L.drop_nav_link("x", 2, 0.0, 0.0, None, None, 3.6)   # story 2 of a two-storey building: the roof slab
    assert nl["start_position"][2] == 7.2 and nl["end_position"][2] == 3.6


def test_a_ladder_link_is_untouched():
    """The shape is shared with `_nav_link`; the capability and direction are what differ."""
    keys = set(L.drop_nav_link("x", 1, 0.0, 0.0, None, None, 3.0)) - {"hole"}
    lad = L._nav_link(type("Ld", (), {"x": 0.0, "y": 0.0})(), "l", 0.0, 3.0)
    assert keys == set(lad)
    assert lad["required_capability"] == "climb" and lad["bidirectional"] is True
