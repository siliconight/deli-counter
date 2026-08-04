"""Floor/ceiling slot derivation (floors.py) -- pure, no bpy."""

import floors


class _Room:
    def __init__(self, rid, story, role, bounds, material=None):
        self.id, self.story, self.role = rid, story, role
        self.bounds, self.material = bounds, material


class _Spec:
    story_height = 3.7
    floor_thick = 0.3
    roof_thick = 0.4
    default_material = "concrete"
    materials = []

    def __init__(self, rooms):
        self.rooms = rooms


#: The rooms of a shipped building, copied off `shell.gameplay.json`.
def _spec():
    return _Spec([
        _Room("gaming_floor", 0, "public_entry", [-22.0, -16.0, 22.0, 8.0]),
        _Room("north_concourse", 0, "connector", [-22.0, 8.0, 10.0, 16.0]),
        _Room("cashier_cage", 0, "objective_room", [10.0, 8.0, 22.0, 16.0]),
        _Room("upper_lounge", 1, "connector", [-22.0, -16.0, 22.0, 0.0]),
        _Room("security_office", 1, "fortifiable", [-22.0, 0.0, 0.0, 16.0]),
        _Room("count_room", 1, "objective_room", [0.0, 0.0, 22.0, 16.0]),
        _Room("vault", -1, "objective_room", [-22.0, -16.0, 22.0, 16.0]),
    ])


def _by_id(slots):
    return {s["slot_id"]: s for s in slots}


def test_every_room_gets_a_floor_and_a_ceiling():
    slots = floors.slab_slots(_spec(), top=2)
    assert len(slots) == 14                       # 7 rooms x 2 surfaces
    ids = _by_id(slots)
    assert "floor_gaming_floor" in ids and "ceiling_gaming_floor" in ids


def test_the_floor_lies_on_the_slab_and_the_ceiling_hangs_under_the_next():
    """The heights are the whole point: one slab is two surfaces."""
    ids = _by_id(floors.slab_slots(_spec(), top=2))
    # storey 0's floor is the top face of the slab below it, plus half a skin
    assert ids["floor_gaming_floor"]["transform"]["translation"][2] == 0.01
    # its ceiling is the underside of the storey-1 slab: 3.7 - 0.3 - 0.01
    assert ids["ceiling_gaming_floor"]["transform"]["translation"][2] == 3.39


def test_the_top_storey_ceiling_uses_roof_thickness():
    """The slab capping the top storey is the roof and may be thicker.

    Mirrors Builder._cap_thick. Getting this wrong buries the top ceiling
    inside the roof slab or floats it below one.
    """
    ids = _by_id(floors.slab_slots(_spec(), top=2))
    # 2*3.7 - roof_thick 0.4 - half skin
    assert ids["ceiling_count_room"]["transform"]["translation"][2] == 6.99
    # a storey below the top uses floor_thick, not roof_thick
    assert ids["ceiling_gaming_floor"]["transform"]["translation"][2] == 3.39


def test_a_basement_room_slots_below_grade():
    ids = _by_id(floors.slab_slots(_spec(), top=2))
    assert ids["floor_vault"]["transform"]["translation"][2] == -3.69
    assert ids["ceiling_vault"]["transform"]["translation"][2] == -0.31


def test_floor_and_ceiling_materials_differ_by_role():
    """A wood floor implies a wood ceiling only if one slab carries both."""
    ids = _by_id(floors.slab_slots(_spec(), top=2))
    assert ids["floor_gaming_floor"]["material"] == "carpet"
    assert ids["ceiling_gaming_floor"]["material"] == "ceiling_tile"
    assert ids["floor_north_concourse"]["material"] == "tile"
    assert ids["floor_security_office"]["material"] == "concrete"
    assert ids["ceiling_security_office"]["material"] == "drywall"


def test_a_room_material_overrides_the_role_map():
    spec = _Spec([_Room("odd", 0, "public_entry", [0, 0, 4, 4],
                        material="wood")])
    ids = _by_id(floors.slab_slots(spec, top=2))
    assert ids["floor_odd"]["material"] == "wood"
    assert ids["ceiling_odd"]["material"] == "wood"


def test_an_unknown_role_falls_back_to_the_spec_default():
    """A new room role must never fail -- it just looks ordinary."""
    spec = _Spec([_Room("new", 0, "casino_spa", [0, 0, 4, 4])])
    ids = _by_id(floors.slab_slots(spec, top=2))
    assert ids["floor_new"]["material"] == "concrete"
    assert ids["ceiling_new"]["material"] == "concrete"


def test_nothing_is_slotted_on_the_roof_slab():
    spec = _Spec([_Room("penthouse", 2, "connector", [0, 0, 4, 4])])
    assert floors.slab_slots(spec, top=2) == []


def test_skins_carry_no_collision():
    """DC's trimesh slab stays authoritative. A floor skin with its own
    collision would put a second walkable surface 2 cm above the first."""
    for s in floors.slab_slots(_spec(), top=2):
        assert s["fit"]["collision"] == "none"
        assert s["fit"]["dims"][2] == floors.SKIN_THICK


def test_facings_are_up_and_down():
    ids = _by_id(floors.slab_slots(_spec(), top=2))
    assert ids["floor_vault"]["facing"] == "up"
    assert ids["ceiling_vault"]["facing"] == "down"


def test_room_bounds_become_the_slot_footprint():
    ids = _by_id(floors.slab_slots(_spec(), top=2))
    f = ids["floor_cashier_cage"]
    assert f["fit"]["dims"][:2] == [12.0, 8.0]
    assert f["transform"]["translation"][:2] == [16.0, 12.0]
    assert f["room"] == "cashier_cage"


def test_deterministic():
    assert floors.slab_slots(_spec(), top=2) == floors.slab_slots(_spec(), top=2)


# --------------------------------------------------------------------------- #
# Slab holes: a skin laid over a slab full of holes must have the same holes
# --------------------------------------------------------------------------- #

class _Hole:
    def __init__(self, story, x, y, sx, sy):
        self.story, self.x, self.y = story, x, y
        self.size_x, self.size_y = sx, sy


def _spec_with_holes():
    s = _spec()
    # a stairwell through the storey-1 slab, inside gaming_floor's footprint
    s.slab_holes = [_Hole(1, 4.0, -6.0, 3.0, 4.0)]
    return s


def test_a_hole_opens_the_ceiling_below_and_the_floor_above():
    """One slab, two surfaces, and the hole belongs to both of them.

    A hole with story == s cuts the slab whose top face is the floor of s, so
    it opens the FLOOR of storey s and the CEILING of storey s-1. Getting the
    storey off by one leaves the stairwell capped from one side.
    """
    ids = _by_id(floors.slab_slots(_spec_with_holes(), top=2))
    # gaming_floor is storey 0: its ceiling is the underside of the storey-1 slab
    assert len(ids["ceiling_gaming_floor"]["fit"]["voids"]) == 1
    # upper_lounge is storey 1: its floor is the top face of that same slab
    assert len(ids["floor_upper_lounge"]["fit"]["voids"]) == 1
    # and neither the floor below nor the ceiling above is touched
    assert ids["floor_gaming_floor"]["fit"]["voids"] == []
    assert ids["ceiling_upper_lounge"]["fit"]["voids"] == []


def test_voids_are_in_the_skin_own_centred_coords():
    """Modules are centre-pivot, so a world hole has to be re-centred."""
    ids = _by_id(floors.slab_slots(_spec_with_holes(), top=2))
    # gaming_floor spans [-22,-16,22,8] -> centre (0.0, -4.0). The hole is at
    # x 4.0 size 3.0 and y -6.0 size 4.0, so 2.5..5.5 in x and -8.0..-4.0 in y,
    # which re-centres to -4.0..0.0. The two rooms sharing this slab see the
    # SAME hole at different local offsets, because their centres differ.
    v = ids["ceiling_gaming_floor"]["fit"]["voids"][0]
    assert v == {"x0": 2.5, "y0": -4.0, "x1": 5.5, "y1": 0.0}
    # upper_lounge spans [-22,-16,22,0] -> centre (0.0, -8.0)
    assert ids["floor_upper_lounge"]["fit"]["voids"][0] == {
        "x0": 2.5, "y0": 0.0, "x1": 5.5, "y1": 4.0}


def test_a_hole_outside_a_room_is_not_carried():
    s = _spec()
    s.slab_holes = [_Hole(1, 100.0, 100.0, 3.0, 4.0)]
    for slot in floors.slab_slots(s, top=2):
        assert slot["fit"]["voids"] == []


def test_no_slab_holes_at_all_is_not_an_error():
    """An older spec with no slab_holes attribute must still slot."""
    s = _spec()
    assert not hasattr(s, "slab_holes")
    assert all(x["fit"]["voids"] == [] for x in floors.slab_slots(s, top=2))


def test_a_hole_listed_twice_is_carried_once():
    """slab_holes really does contain duplicates.

    A hatch authored in the spec is appended again by `_vertical_links`, and
    three plates came out with the same rect listed twice. Harmless to the
    tiling, fatal to the naming: void_tag hashes the list, so identical
    geometry would resolve to two different module files.
    """
    s = _spec()
    s.slab_holes = [_Hole(1, 4.0, -6.0, 3.0, 4.0),
                    _Hole(1, 4.0, -6.0, 3.0, 4.0)]
    ids = _by_id(floors.slab_slots(s, top=2))
    assert len(ids["ceiling_gaming_floor"]["fit"]["voids"]) == 1
