"""The module-stem mirror: Deli Counter asks for the file Zoo built.

``themed_tscn.module_stem`` and ``zoo_keeper.core.kit.module_stem`` construct
the same filename from the same slot, and NEITHER PARSES. They agree only by
being kept identical, which no import enforces -- they are different repos.

So the seam is pinned by literals. Zoo's ``tests/test_openings.py`` asserts
these same six-character tags; either side drifting alone fails its own suite
rather than quietly resolving to a module that was never built. That failure
mode is not hypothetical: a plate depth collision and a stairwell collision
both shipped as "one file wins and one room gets the other's geometry".
"""

import themed_tscn


def _slot(role, dims, openings=None, voids=None, style=1):
    return {"slot_id": "s", "role": role, "size_mod": "full", "style": style,
            "fit": {"dims": dims, "pivot": "center",
                    "openings": openings or [], "voids": voids or []}}


DOOR = {"kind": "door", "width": 1.2, "height": 2.2, "sill": 0.0}
WINDOW = {"kind": "window", "width": 3.0, "height": 1.4, "sill": 0.8}


def test_the_opening_tag_matches_zoo_exactly():
    """The literals are the contract. Change one and change Zoo's too."""
    assert themed_tscn.opening_tag([DOOR]) == "97cfbf"
    assert themed_tscn.opening_tag([WINDOW]) == "ba672d"
    assert themed_tscn.opening_tag(
        [{"kind": "garage", "width": 3.2, "height": 2.6,
          "sill": 0.0}]) == "150910"
    assert themed_tscn.opening_tag([]) is None
    assert themed_tscn.opening_tag(None) is None


def test_the_stem_carries_the_opening_tag():
    assert themed_tscn.module_stem(
        "doorway", "rockay", 1, 120, None, None, None,
        "97cfbf") == "doorway_rockay_01_w120_o97cfbf"


def test_a_doorway_slot_resolves_to_the_tagged_stem():
    stem, scaled = themed_tscn.resolve_themed_stem(
        _slot("doorway", [1.2, 0.35, 3.7], [DOOR]), "rockay", 1)
    assert stem == "doorway_rockay_01_w120_o97cfbf"
    assert scaled is False


def test_two_doorways_of_one_width_and_different_apertures_differ():
    """The collision the tag exists for: both were `doorway_rockay_01_w140`,
    one file won, and one room got the other's hole."""
    a = [{"kind": "door", "width": 1.4, "height": 2.2, "sill": 0.0}]
    b = [{"kind": "door", "width": 1.4, "height": 2.4, "sill": 0.0}]
    sa, _ = themed_tscn.resolve_themed_stem(
        _slot("doorway", [1.4, 0.35, 3.7], a), "rockay", 1)
    sb, _ = themed_tscn.resolve_themed_stem(
        _slot("doorway", [1.4, 0.35, 3.7], b), "rockay", 1)
    assert sa != sb


def test_the_order_of_openings_is_kept():
    """Only the first aperture is cut, so a different order is a different
    module. (A plate's voids are a set and sort; these must not.)"""
    assert (themed_tscn.opening_tag([DOOR, WINDOW])
            != themed_tscn.opening_tag([WINDOW, DOOR]))


def test_wall_floor_and_ceiling_names_are_untouched():
    """A wall has no aperture, so no existing wall/plate filename moves."""
    stem, _ = themed_tscn.resolve_themed_stem(
        _slot("wall", [2.0, 0.35, 3.7]), "rockay", 1)
    assert stem == "wall_rockay_01_w200"
    stem, _ = themed_tscn.resolve_themed_stem(
        _slot("floor", [44.0, 24.0, 0.02]), "rockay", 1)
    assert stem == "floor_rockay_01_w4400_d2400"


def test_a_wall_remainder_is_still_one_unit_module():
    slot = _slot("wall", [1.3, 0.35, 3.7])
    slot["size_mod"] = "end"
    stem, scaled = themed_tscn.resolve_themed_stem(slot, "rockay", 1)
    assert stem == "wallEnd_rockay_01" and scaled is True
