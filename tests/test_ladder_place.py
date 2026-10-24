"""Pure tests for ladder_place.py Phase 2 (no bpy).
Run: python3 test_ladder_place.py"""
import ladder_place as P
import ladder as L
from spec_types import (LevelSpec, Ladder, Room, ExtWall, Opening, Volume,
                        Parapet)


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("LADDER ", "") for m in msgs}


def _shop():
    """Small commercial box: front door on S, service room + roof equipment on
    the rear (N), clean side walls."""
    return LevelSpec(
        name="s", n_stories=2, story_height=3.0, footprint_x=26, footprint_y=18,
        rooms=[Room(id="sales", story=0, bounds=[-13, -9, 13, 2],
                    role="public_entry"),
               Room(id="mech", story=0, bounds=[-13, 2, 13, 9],
                    role="mechanical")],
        ext_walls=[ExtWall(wall="S", story=0,
                           openings=[Opening(kind="door", pos=0.0)])],
        volumes=[Volume(name="rooftop_hvac_unit", x=0, y=7, z=6.2,
                        size_x=2, size_y=2, size_z=1.2)])


# --- profiles -----------------------------------------------------------------

def test_six_profiles_exist():
    assert len(P.PROFILES) == 6
    for pid, prof in P.PROFILES.items():
        assert "default_role" in prof and "fall_protection_trigger_m" in prof


def test_office_forbids_exterior_ladder():
    sp = _shop()
    prop = P.propose(sp, "modern_office")
    assert prop["ladders"] == []
    assert any("does not allow exterior roof ladders" in n
               for n in prop["notes"])


# --- candidate generation + rejection -----------------------------------------

def test_candidates_from_walls_deterministic():
    sp = _shop()
    prof = P.PROFILES["modern_small_commercial"]
    a = P.candidate_zones(sp, prof)
    b = P.candidate_zones(sp, prof)
    assert a == b and len(a) > 4
    walls = {c["wall"] for c in a}
    assert walls == {"N", "S", "E", "W"}


def test_front_door_wall_rejected_in_climb_zone():
    sp = _shop()
    prop = P.propose(sp, "modern_small_commercial")
    reasons = {r["reason"] for r in prop["rejected"]}
    assert any(r.startswith("door_in_climb_zone:S") for r in reasons)


def test_hazard_at_base_rejected():
    sp = _shop()
    sp.volumes.append(Volume(name="electrical_transformer", x=12.6, y=5.4,
                             z=1.0, size_x=1, size_y=1, size_z=1.5))
    prop = P.propose(sp, "modern_small_commercial")
    reasons = {r["reason"] for r in prop["rejected"]}
    assert any(r.startswith("hazard_at_base:electrical_transformer")
               for r in reasons)


def test_tall_climb_rejected_without_offset_profile():
    sp = _shop()
    sp.story_height = 4.0
    sp.n_stories = 2       # 8 m > 7.3 m trigger
    prop = P.propose(sp, "modern_small_commercial")
    # every candidate should be rejected for the climb, so nothing proposed
    assert all(r["reason"].startswith("climb_too_tall")
               or "climb_zone" in r["reason"] for r in prop["rejected"])
    assert prop["ladders"] == []


def test_warehouse_offset_allows_tall_climb():
    sp = _shop()
    sp.story_height = 4.0
    prop = P.propose(sp, "warehouse_industrial")
    assert prop["ladders"]       # offset sections allowed -> tall climb ok


# --- scoring ------------------------------------------------------------------

def test_rear_service_wall_scores_highest():
    sp = _shop()
    prop = P.propose(sp, "modern_small_commercial")
    best = prop["scored"][0]
    assert best["is_rear"] is True and best["is_front"] is False
    # any front (S) candidate that survived scores below the rear; front walls
    # here are rejected outright (door in climb zone), which is even stronger
    fronts = [s["score"] for s in prop["scored"] if s["is_front"]]
    if fronts:
        assert best["score"] > max(fronts)
    else:
        assert any(r["is_front"] for r in prop["rejected"])


def test_equipment_boosts_destination_relevance():
    sp = _shop()
    prof = P.PROFILES["modern_small_commercial"]
    near = {"wall": "N", "x": 0.0, "y": 8.65, "facing": "N", "frac": 0.0,
            "is_front": False, "is_rear": True}
    far = {"wall": "E", "x": 12.65, "y": -8.0, "facing": "E", "frac": -0.4,
           "is_front": False, "is_rear": False}
    _, tn = P.score_candidate(sp, near, prof)
    _, tf = P.score_candidate(sp, far, prof)
    assert tn["destination_relevance"] > tf["destination_relevance"]


# --- transition selection -----------------------------------------------------

def test_parapet_selects_crossover():
    sp = _shop()
    sp.parapets = [Parapet(story=2, height=1.0)]
    prop = P.propose(sp, "modern_small_commercial")
    assert prop["ladders"][0]["transition"] == "parapet_crossover_platform"


def test_no_parapet_selects_through_step():
    sp = _shop()
    prop = P.propose(sp, "modern_small_commercial")
    assert prop["ladders"][0]["transition"] == "through_step_off"


# --- loop closure: proposal survives ladder.check -----------------------------

def test_proposal_passes_review():
    sp = _shop()
    prop = P.propose(sp, "modern_small_commercial")
    sp.ladders = [Ladder(**l) for l in prop["ladders"]]
    errors, _, _ = L.check(sp)
    assert errors == []


def test_proposal_deterministic():
    a = P.propose(_shop(), "modern_small_commercial")
    b = P.propose(_shop(), "modern_small_commercial")
    assert a["ladders"] == b["ladders"]


def test_unknown_profile_raises():
    try:
        P.propose(_shop(), "space_station")
        assert False
    except ValueError as ex:
        assert "unknown profile" in str(ex)


# --- Phase-2 review checks (facade findings) ----------------------------------

def test_public_facade_ladder_warns():
    sp = _shop()
    # author an exterior ladder on the front (S) wall
    sp.ladders = [Ladder(x=0, y=-8.65, from_story=0, to_story=2, facing="S",
                         id="front", role="roof_access",
                         placement_mode="exterior_wall", lower_surface="grade",
                         upper_surface="roof", transition="through_step_off")]
    _, warnings, _ = L.check(sp)
    assert "LADDER_PUBLIC_FACADE" in _codes(warnings)


def test_vehicle_conflict_gates():
    sp = _shop()
    sp.volumes.append(Volume(name="forklift_lane", x=-12.65, y=-5.4, z=0.5,
                             size_x=3, size_y=3, size_z=0.2))
    sp.ladders = [Ladder(x=-12.65, y=-5.4, from_story=0, to_story=2, facing="W",
                         id="side", role="roof_access",
                         placement_mode="exterior_wall", lower_surface="grade",
                         upper_surface="roof", transition="through_step_off")]
    errors, _, _ = L.check(sp)
    assert "LADDER_VEHICLE_CONFLICT" in _codes(errors)


def test_drainage_warns():
    sp = _shop()
    sp.volumes.append(Volume(name="roof_scupper", x=12.65, y=5.4, z=6.0,
                             size_x=0.3, size_y=0.3, size_z=0.5))
    sp.ladders = [Ladder(x=12.65, y=5.4, from_story=0, to_story=2, facing="E",
                         id="side", role="roof_access",
                         placement_mode="exterior_wall", lower_surface="grade",
                         upper_surface="roof", transition="through_step_off")]
    _, warnings, _ = L.check(sp)
    assert "LADDER_NEAR_DRAINAGE" in _codes(warnings)


def test_roof_edge_risk_warns_without_parapet():
    sp = _shop()
    # dismount right at the E edge, no parapet
    sp.ladders = [Ladder(x=12.65, y=0, from_story=0, to_story=2, facing="E",
                         id="edge", role="roof_access",
                         placement_mode="exterior_wall", lower_surface="grade",
                         upper_surface="roof", transition="through_step_off")]
    _, warnings, _ = L.check(sp)
    assert "LADDER_TOP_EDGE_RISK" in _codes(warnings)


def test_parapet_clears_edge_risk():
    sp = _shop()
    sp.parapets = [Parapet(story=2, height=1.0)]
    sp.ladders = [Ladder(x=12.65, y=0, from_story=0, to_story=2, facing="E",
                         id="edge", role="roof_access",
                         placement_mode="exterior_wall", lower_surface="grade",
                         upper_surface="roof",
                         transition="parapet_crossover_platform")]
    _, warnings, _ = L.check(sp)
    assert "LADDER_TOP_EDGE_RISK" not in _codes(warnings)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all ladder_place tests passed")
