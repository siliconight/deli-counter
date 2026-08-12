"""Pure tests for roofs.py (no bpy). Run: python3 test_roofs.py"""
import roofs
from spec_types import LevelSpec, Room


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def test_footprint_single_slot():
    sp = LevelSpec(name="wawa", footprint_x=32, footprint_y=22,
                   roof_mode="footprint")
    slots = roofs.roof_slots(sp, story=1, cz=4.35, ft=0.2)
    assert len(slots) == 1
    s = slots[0]
    assert s["slot_id"] == "roof_footprint"
    assert s["role"] == "roof" and s["facing"] == "up"
    assert s["transform"]["rot_y"] == 0
    assert s["transform"]["scale"] == [1.0, 1.0, 1.0]
    assert s["fit"]["dims"] == [32.0, 22.0, 0.2]
    assert s["fit"]["pivot"] == "center" and s["fit"]["collision"] == "trimesh"


def test_per_room_and_roofed_optout():
    sp = LevelSpec(name="s", roof_mode="per_room", rooms=[
        Room(id="sales", story=1, bounds=[-16, -11, 6, 11]),
        Room(id="forecourt", story=1, bounds=[-14, -24, 14, -11], roofed=False),
        Room(id="office", story=1, bounds=[6, 2, 16, 11]),
        Room(id="upstairs", story=2, bounds=[0, 0, 4, 4]),  # wrong story
    ])
    slots = roofs.roof_slots(sp, story=1, cz=4.35, ft=0.2)
    assert [s["slot_id"] for s in slots] == ["roof_sales", "roof_office"]
    sales = slots[0]
    # bounds -> center + dims
    assert sales["transform"]["translation"][:2] == [-5.0, 0.0]
    assert sales["fit"]["dims"] == [22.0, 22.0, 0.2]
    assert sales["room"] == "sales"


def test_per_room_all_open_is_empty():
    sp = LevelSpec(name="s", roof_mode="per_room", rooms=[
        Room(id="yard", story=1, bounds=[0, 0, 4, 4], roofed=False),
    ])
    assert roofs.roof_slots(sp, story=1, cz=1.0, ft=0.2) == []


def test_stable_slot_ids():
    sp = LevelSpec(name="s", roof_mode="per_room",
                   rooms=[Room(id="vault", story=1, bounds=[0, 0, 6, 6])])
    a = roofs.roof_slots(sp, 1, 4.35, 0.2)
    b = roofs.roof_slots(sp, 1, 4.35, 0.2)
    assert a == b and a[0]["slot_id"] == "roof_vault"




# --------------------------------------------------------------------------- #
# The roof carries the slab's holes (2026-08-09)
#
# A roof slot is NOT a skin. `fit.dims` is the slab's real thickness and
# `collision` is `trimesh`, so the themed module is a collider spanning the
# whole plan. A floor or ceiling skin that forgets a void looks wrong; a roof
# that forgets one IS a wall -- which is what a ladder in `bank_branch_a04` rose
# a full storey into.
# --------------------------------------------------------------------------- #

class _Hole:
    """Same stand-in `test_floors` uses -- spec_types.SlabHole's four fields."""

    def __init__(self, story, x, y, sx, sy):
        self.story, self.x, self.y = story, x, y
        self.size_x, self.size_y = sx, sy


def test_a_roof_over_nothing_has_no_voids():
    """THE CLEAN CASE, asserted on purpose. "It cut the hole for the broken
    building" cannot tell you it would not also punch one in a solid roof, and
    only the clean report has any value -- the lesson `module_extents --kit`
    paid for with a Z-up fixture that agreed with a Y-up reader."""
    sp = LevelSpec(name="s", footprint_x=32, footprint_y=22,
                   roof_mode="footprint")
    slots = roofs.roof_slots(sp, story=1, cz=4.35, ft=0.2)
    assert slots[0]["fit"]["voids"] == []


def test_a_slab_hole_at_the_roof_storey_reaches_the_roof_slot():
    sp = LevelSpec(name="s", footprint_x=40, footprint_y=30,
                   roof_mode="footprint")
    sp.slab_holes = [_Hole(2, 16.0, 11.55, 1.1, 1.3)]
    slots = roofs.roof_slots(sp, story=2, cz=8.25, ft=0.3)
    assert slots[0]["fit"]["voids"] == [
        {"x0": 15.45, "y0": 10.9, "x1": 16.55, "y1": 12.2}]


def test_a_hole_through_a_lower_slab_is_not_the_roofs():
    """`slab_holes` carries every storey's openings. A stairwell through
    storey 1 must not punch the roof."""
    sp = LevelSpec(name="s", footprint_x=40, footprint_y=30,
                   roof_mode="footprint")
    sp.slab_holes = [_Hole(1, 4.0, -6.0, 3.0, 4.0)]
    slots = roofs.roof_slots(sp, story=2, cz=8.25, ft=0.3)
    assert slots[0]["fit"]["voids"] == []


class _BareSpec:
    """A spec object with no `slab_holes` attribute at all -- the stand-in
    `test_floors` uses for the same guarantee. `LevelSpec` defaults the field to
    a list, so it cannot express this case and the `getattr` guard would go
    untested against it."""

    roof_mode = "footprint"
    footprint_x, footprint_y = 32.0, 22.0
    rooms, materials = (), ()
    default_material = None


def test_a_spec_with_no_slab_holes_attribute_still_slots():
    sp = _BareSpec()
    assert not hasattr(sp, "slab_holes")
    assert roofs.roof_slots(sp, story=1, cz=4.35, ft=0.2)[0]["fit"]["voids"] == []


def test_per_room_roofs_each_take_only_their_own_holes():
    sp = LevelSpec(name="s", roof_mode="per_room", rooms=[
        Room(id="west", story=2, bounds=[-16, -11, 0, 11]),
        Room(id="east", story=2, bounds=[0, -11, 16, 11]),
    ])
    sp.slab_holes = [_Hole(2, 8.0, 0.0, 2.0, 2.0)]      # inside `east` only
    slots = {s["slot_id"]: s for s in roofs.roof_slots(sp, 2, 8.25, 0.3)}
    assert slots["roof_west"]["fit"]["voids"] == []
    assert len(slots["roof_east"]["fit"]["voids"]) == 1


def test_a_hole_outside_every_roofed_room_is_dropped_not_clamped():
    sp = LevelSpec(name="s", roof_mode="per_room",
                   rooms=[Room(id="hall", story=2, bounds=[-5, -5, 5, 5])])
    sp.slab_holes = [_Hole(2, 100.0, 100.0, 2.0, 2.0)]
    assert roofs.roof_slots(sp, 2, 8.25, 0.3)[0]["fit"]["voids"] == []


def test_the_bank_branch_ladder_gets_out_onto_the_roof():
    """THE REGRESSION, with the numbers off the shipped building.

    `bank_branch_a04`: 40 x 30 footprint, storey 4.2, roof at storey 2, one
    ladder at spec (16, 12) width 0.5 facing S climbing storey 1 -> 2. The walk
    bot stalled against a collider named `Roof` at ladder-local 3.90 -- world
    8.10, the exact underside of a slab spanning 8.10..8.40 -- with
    `aperture_z: []`, no opening anywhere across the sweep.

    The hole itself was never in doubt: `slab_col_2-colonly` carries it, corners
    15.45/16.55/-10.90, exactly where `ladder_geom.through_hole` puts it. So
    this asserts the OTHER half -- that the roof slot laid over that slab asks
    for the same rectangle, and that the rectangle admits the climbing capsule.
    """
    import ladder_geom
    hx, hy, hsx, hsy = ladder_geom.through_hole(16.0, 12.0, 0.5, "S")
    sp = LevelSpec(name="bank_branch_a04", footprint_x=40, footprint_y=30,
                   n_stories=2, story_height=4.2, roof_mode="footprint")
    sp.slab_holes = [_Hole(2, hx, hy, hsx, hsy)]
    void = roofs.roof_slots(sp, story=2, cz=8.25, ft=0.3)[0]["fit"]["voids"][0]

    # the climb column the capsule needs: CLIMB_STANDOFF +/- capsule radius,
    # measured from the ladder face along the APPROACH direction (facing S =
    # -y), and the ladder's own width across it.
    standoff, capsule_r = ladder_geom.CLIMB_STANDOFF, 0.35
    assert void["y0"] <= 12.0 - (standoff + capsule_r)
    assert void["y1"] >= 12.0 - (standoff - capsule_r)
    assert void["x0"] <= 16.0 - 0.25 and void["x1"] >= 16.0 + 0.25



if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_"):
            _run(_fn)
    print("\nall roof tests passed")
