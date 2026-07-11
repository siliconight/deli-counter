"""Pure tests for stair_place.py (no bpy). Run: python3 test_stair_place.py"""
import stair_place as P
import stairwell as S
from spec_types import LevelSpec, Stairwell, Room, ExtWall, Opening


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _office():
    """Two-story plate with a protected room in the NE and a grade exit W."""
    return LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                     seed=7,
                     rooms=[Room(id="lobby", story=0, bounds=[-20, -15, 20, 0],
                                 role="public_entry"),
                            Room(id="bullpen", story=0, bounds=[-20, 0, 20, 15],
                                 role="connector"),
                            Room(id="up", story=1, bounds=[-20, -15, 20, 15],
                                 role="connector"),
                            Room(id="vault", story=1, bounds=[12, 7, 20, 15],
                                 role="objective_room", objective=True)],
                     ext_walls=[ExtWall(wall="W", story=0,
                                        openings=[Opening(kind="door",
                                                          pos=-0.2)])])


# --- profiles + geometry ------------------------------------------------------

def test_ten_profiles_exist():
    assert len(P.PROFILES) == 10
    for pid, prof in P.PROFILES.items():
        assert prof["primary_zones"] and prof["stair_count_policy"] in (
            "one", "two", "occupancy_and_floorplate"), pid


def test_stair_dims_riser_math():
    sp = LevelSpec(name="s", story_height=3.5)
    fw, run, rise, w, style = P.stair_dims(sp, P.PROFILES["office_lowrise"])
    # 3.5 m / 0.17 target -> 21 uniform risers of ~0.167 m
    assert abs(rise - 3.5 / 21) < 1e-9
    assert 3.0 <= run <= 8.0 and run % 0.5 == 0
    assert style == "switchback" and fw == 2 * w


def test_candidate_zones_are_deterministic_and_inside():
    sp = _office()
    prof = P.PROFILES["office_lowrise"]
    a = P.candidate_zones(sp, prof)
    b = P.candidate_zones(sp, prof)
    assert a == b and len(a) > 6
    hx, hy = sp.footprint_x / 2, sp.footprint_y / 2
    for c in a:
        assert -hx < c["x"] < hx and -hy < c["y"] < hy
    zones = {c["zone"] for c in a}
    assert {"exterior_corner", "core_edge", "perimeter_bay"} <= zones


def test_party_wall_only_for_narrow_plates():
    wide = LevelSpec(name="s", footprint_x=30, footprint_y=28)
    narrow = LevelSpec(name="s", footprint_x=10, footprint_y=30)
    prof = P.PROFILES["urban_storefront_narrow"]
    assert not any(c["zone"] == "party_wall"
                   for c in P.candidate_zones(wide, prof))
    assert any(c["zone"] == "party_wall"
               for c in P.candidate_zones(narrow, prof))


# --- rejection with reasons ----------------------------------------------------

def test_rejects_protected_room_overlap_with_reason():
    sp = _office()
    prop = P.propose(sp, "office_lowrise")
    reasons = {r["reason"] for r in prop["rejected"]}
    assert any(r.startswith("overlaps_protected_room:vault") for r in reasons)


def test_rejects_existing_stair_overlap():
    sp = _office()
    sp.stairs = [Stairwell(x=0, y=5, from_story=0, to_story=1, id="old")]
    prop = P.propose(sp, "office_lowrise")
    assert any(r["reason"].startswith("overlaps_existing_stair:old")
               for r in prop["rejected"])


def test_ignore_existing_drops_that_rejection():
    sp = _office()
    sp.stairs = [Stairwell(x=0, y=5, from_story=0, to_story=1, id="old")]
    prop = P.propose(sp, "office_lowrise", ignore_existing=True)
    assert not any("overlaps_existing_stair" in r["reason"]
                   for r in prop["rejected"])


# --- scoring + selection ---------------------------------------------------------

def test_center_scores_below_perimeter():
    sp = _office()
    prof = P.PROFILES["office_lowrise"]
    center = {"zone": "core_edge", "x": 0.0, "y": 0.0}
    corner = {"zone": "exterior_corner", "x": -17.0, "y": -11.0}
    sc_center, _ = P.score_candidate(sp, prof, center, {})
    sc_corner, _ = P.score_candidate(sp, prof, corner, {})
    assert sc_corner > sc_center     # usable_area_damage prices the center


def test_pair_is_separated_and_independent():
    sp = _office()
    prop = P.propose(sp, "office_lowrise")
    assert prop["stair_count"] == 2 and len(prop["stairs"]) >= 2
    a, b = prop["stairs"][0], prop["stairs"][1]
    import math
    dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    assert dist >= max(8.0, 50 * 0.33) - 1e-6
    assert a["role"] == "primary_egress" and b["role"] == "secondary_egress"


def test_proposal_survives_its_own_review():
    """The loop must close: place with stair_place, gate with stairwell."""
    sp = _office()
    prop = P.propose(sp, "office_lowrise")
    from spec_types import Stairwell as SW
    sp.stairs = [SW(**{k: v for k, v in st.items()}) for st in prop["stairs"]]
    errors, _, _ = S.check(sp)
    assert errors == []


def test_single_stair_policy_and_no_stair_for_one_story():
    house = LevelSpec(name="s", n_stories=2, footprint_x=12, footprint_y=10)
    assert P.stair_count(house, P.PROFILES["residential_house"]) == 1
    flat = LevelSpec(name="s", n_stories=1)
    assert P.stair_count(flat, P.PROFILES["office_lowrise"]) == 0


def test_deterministic_proposal():
    a = P.propose(_office(), "office_lowrise")
    b = P.propose(_office(), "office_lowrise")
    assert a["stairs"] == b["stairs"]


def test_unknown_archetype_raises():
    try:
        P.propose(_office(), "casino_megaresort")
        assert False, "should have raised"
    except ValueError as ex:
        assert "unknown archetype" in str(ex)


# --- review integration (STAIR_LOW_ARCHETYPE_FIT) --------------------------------

def test_archetype_fit_warning_fires_for_center_stair():
    sp = _office()
    sp.archetype = "office_lowrise"
    sp.stairs = [Stairwell(x=0, y=0, from_story=0, to_story=1, id="center")]
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert any("STAIR_LOW_ARCHETYPE_FIT" in w for w in warnings)


def test_archetype_fit_clean_for_proposed_stair():
    sp = _office()
    sp.archetype = "office_lowrise"
    prop = P.propose(sp, "office_lowrise")
    from spec_types import Stairwell as SW
    sp.stairs = [SW(**prop["stairs"][0])]
    _, warnings, _ = S.check(sp)
    assert not any("STAIR_LOW_ARCHETYPE_FIT" in w for w in warnings)


def test_unknown_declared_archetype_warns():
    sp = _office()
    sp.archetype = "moon_base"
    sp.stairs = [Stairwell(x=0, y=0, from_story=0, to_story=1)]
    _, warnings, _ = S.check(sp)
    assert any("unknown archetype" in w for w in warnings)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all stair_place tests passed")
