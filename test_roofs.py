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


if __name__ == "__main__":
    _run(test_footprint_single_slot)
    _run(test_per_room_and_roofed_optout)
    _run(test_per_room_all_open_is_empty)
    _run(test_stable_slot_ids)
    print("\nall roof tests passed")
