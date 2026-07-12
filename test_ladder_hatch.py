"""Pure tests for ladder Phase 3 (interior roof-hatch, no bpy).
Run: python3 test_ladder_hatch.py"""
import ladder as L
import ladder_place as P
from spec_types import (LevelSpec, Ladder, Room, ExtWall, Opening, Volume,
                        Parapet)


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("LADDER ", "") for m in msgs}


def _hatch(**kw):
    """A clean interior roof-hatch ladder rising from a mechanical room."""
    base = dict(x=5, y=5, from_story=0, to_story=2, facing="S", id="h",
                role="roof_access", placement_mode="interior",
                lower_surface="mech", upper_surface="roof",
                transition="roof_hatch_exit", access_control="locked_hatch")
    base.update(kw)
    return LevelSpec(
        name="s", n_stories=2, story_height=3.0, footprint_x=40, footprint_y=30,
        ladders=[Ladder(**base)],
        rooms=[Room(id="mech", story=0, bounds=[0, 0, 10, 10],
                    role="mechanical"),
               Room(id="corr", story=0, bounds=[-20, 0, 0, 10],
                    role="connector"),
               Room(id="mech1", story=1, bounds=[0, 0, 10, 10],
                    role="mechanical")],
        ext_walls=[ExtWall(wall="W", story=0,
                           openings=[Opening(kind="door", pos=0.2)])])


# --- review: hatch-room validation (s8.2) -------------------------------------

def test_clean_hatch_passes():
    errors, warnings, _ = L.check(_hatch())
    assert errors == []
    assert "ROOF_HATCH_BLOCKED" not in _codes(warnings)


def test_hatch_in_public_room_gates():
    sp = _hatch(lower_surface="lobby")
    sp.rooms.append(Room(id="lobby", story=0, bounds=[0, 0, 10, 10],
                         role="public_entry"))
    # move mech out of the way so 'lobby' is the base
    sp.rooms[0] = Room(id="mech_far", story=0, bounds=[20, 20, 30, 30],
                       role="mechanical")
    errors, _, _ = L.check(sp)
    assert "ROOF_HATCH_BLOCKED" in _codes(errors)


def test_hatch_in_odd_room_warns():
    sp = _hatch(lower_surface="loot")
    sp.rooms.append(Room(id="loot", story=0, bounds=[0, 0, 10, 10],
                         role="loot_room"))
    errors, warnings, _ = L.check(sp)
    assert errors == []
    assert any("prefer a service" in w for w in warnings)


# --- review: hatch clearance (s8.3) -------------------------------------------

def test_equipment_over_hatch_gates():
    sp = _hatch()
    sp.volumes = [Volume(name="rooftop_duct", x=5, y=5, z=6.5,
                         size_x=1.0, size_y=1.0, size_z=1.0)]
    errors, _, _ = L.check(sp)
    assert "ROOF_HATCH_BLOCKED" in _codes(errors)
    assert any("emerges under" in e for e in errors)


def test_parapet_edge_blocks_cover_gates():
    sp = _hatch(x=19.5, y=5)      # near the E roof edge (hx=20)
    sp.rooms[0] = Room(id="mech", story=0, bounds=[15, 0, 20, 10],
                       role="mechanical")
    sp.parapets = [Parapet(story=2, height=1.0)]
    errors, _, _ = L.check(sp)
    assert "ROOF_HATCH_BLOCKED" in _codes(errors)
    assert any("swing collides with the parapet" in e for e in errors)


def test_central_hatch_with_parapet_ok():
    sp = _hatch()                 # base at (5,5), far from any edge
    sp.parapets = [Parapet(story=2, height=1.0)]
    errors, _, _ = L.check(sp)
    assert "ROOF_HATCH_BLOCKED" not in _codes(errors)


def test_hatch_without_access_control_warns():
    sp = _hatch(access_control=None)
    errors, warnings, _ = L.check(sp)
    assert errors == []
    assert any("no access_control" in w for w in warnings)


def test_exterior_ladder_skips_hatch_checks():
    # an exterior ladder reaching the roof is not a hatch ladder
    sp = _hatch(placement_mode="exterior_wall", transition="through_step_off",
                lower_surface="grade")
    errors, warnings, _ = L.check(sp)
    assert "ROOF_HATCH_BLOCKED" not in _codes(errors)


# --- placement: interior hatch mode -------------------------------------------

def _office_top_service():
    """Two-story building with a top-floor mechanical room (hatch origin)."""
    return LevelSpec(
        name="s", n_stories=2, story_height=3.0, footprint_x=40, footprint_y=30,
        rooms=[Room(id="lobby", story=0, bounds=[-20, -15, 20, 15],
                    role="public_entry"),
               Room(id="mech", story=1, bounds=[8, 5, 18, 14],
                    role="mechanical"),
               Room(id="floor1", story=1, bounds=[-20, -15, 8, 15],
                    role="connector")])


def test_hatch_mode_proposes_from_service_room():
    sp = _office_top_service()
    prop = P.propose(sp, "modern_office", mode="hatch")
    assert prop["mode"] == "hatch"
    assert len(prop["ladders"]) == 1
    lad = prop["ladders"][0]
    assert lad["placement_mode"] == "interior"
    assert lad["lower_surface"] == "mech"
    assert lad["transition"] == "roof_hatch_exit"
    assert lad["access_control"] == "locked_hatch"


def test_hatch_proposal_passes_review():
    sp = _office_top_service()
    prop = P.propose(sp, "modern_office", mode="hatch")
    sp.ladders = [Ladder(**l) for l in prop["ladders"]]
    errors, _, _ = L.check(sp)
    assert errors == []


def test_hatch_mode_deterministic():
    a = P.propose(_office_top_service(), "modern_office", mode="hatch")
    b = P.propose(_office_top_service(), "modern_office", mode="hatch")
    assert a["ladders"] == b["ladders"]


def test_hatch_rejects_equipment_room():
    sp = _office_top_service()
    sp.volumes = [Volume(name="hvac_condenser", x=13, y=9.5, z=6.5,
                         size_x=1, size_y=1, size_z=1)]
    prop = P.propose(sp, "modern_office", mode="hatch")
    # the only service room's centroid is under the equipment -> rejected
    assert any("equipment_over_hatch" in r["reason"]
               for r in prop["rejected"])


def test_profile_without_hatch_allowance():
    sp = _office_top_service()
    prop = P.propose(sp, "residential_house", mode="hatch")
    assert prop["ladders"] == []
    assert any("does not allow roof-hatch" in n for n in prop["notes"])


def test_hatch_falls_back_to_connector():
    # no dedicated service room on top; a connector should host the hatch
    sp = LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                   rooms=[Room(id="lobby", story=0, bounds=[-20, -15, 20, 15],
                              role="public_entry"),
                          Room(id="hall1", story=1, bounds=[-20, -15, 20, 15],
                              role="connector")])
    prop = P.propose(sp, "modern_office", mode="hatch")
    assert len(prop["ladders"]) == 1
    assert prop["ladders"][0]["lower_surface"] == "hall1"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all ladder hatch tests passed")
