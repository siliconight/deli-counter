"""Pure tests for ladder Phase 4 (industrial platforms, no bpy).
Run: python3 test_ladder_platform.py"""
import ladder as L
import ladder_place as P
from spec_types import LevelSpec, Ladder, Room, Platform, Volume, ExtWall, Opening


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("LADDER ", "") for m in msgs}


def _warehouse(**plat_kw):
    """One-story warehouse with a catwalk overhead, service floor below."""
    pk = dict(id="catwalk_a", x=0, y=0, z=4.5, size_x=16, size_y=2,
              role="catwalk", destination="conveyor_line",
              guard_edges=["N", "E", "W"])
    pk.update(plat_kw)
    return LevelSpec(
        name="wh", n_stories=1, story_height=8.0, footprint_x=50, footprint_y=40,
        platforms=[Platform(**pk)],
        rooms=[Room(id="floor", story=0, bounds=[-25, -20, 25, 20],
                    role="service_access")],
        ext_walls=[ExtWall(wall="S", story=0,
                           openings=[Opening(kind="garage", pos=0.0)])])


def _plat_ladder(sp, **kw):
    base = dict(x=0, y=-2, from_story=0, to_story=1, facing="N",
                id="pl", role="maintenance_access", placement_mode="platform",
                lower_surface="floor", upper_surface="catwalk_a",
                transition="side_step_off")
    base.update(kw)
    sp.ladders = [Ladder(**base)]
    return sp


# --- platform primitive ------------------------------------------------------

def test_platform_resolves_as_surface():
    sp = _warehouse()
    assert L._platform_by_id(sp, "catwalk_a") is not None
    assert L._surface_valid(sp, "catwalk_a", 0) is True
    # story of a z=4.5 platform in 8 m stories = 0
    assert L._surface_story(sp, "catwalk_a", 0) == 0


def test_platform_pins_climb_z():
    sp = _plat_ladder(_warehouse(z=6.0))
    d = L.derive(sp)[0]
    # upper anchor sits at the platform deck (6.0), not the story-1 slab (8.0)
    assert d["upper_anchor"][2] == 6.0
    assert d["climb_height_m"] == 6.0


def test_platform_ladder_reviews_clean():
    sp = _plat_ladder(_warehouse())
    errors, warnings, _ = L.check(sp)
    assert errors == []
    assert "LADDER_TO_NOWHERE" not in _codes(warnings)


# --- destination rule (s5.6) --------------------------------------------------

def test_platform_without_destination_warns():
    sp = _plat_ladder(_warehouse(destination=None, role="equipment"))
    errors, warnings, _ = L.check(sp)
    assert "LADDER_TO_NOWHERE" in _codes(warnings)


def test_catwalk_without_destination_ok():
    # a catwalk is itself circulation; it needn't declare a destination
    sp = _plat_ladder(_warehouse(destination=None, role="catwalk"))
    _, warnings, _ = L.check(sp)
    assert "LADDER_TO_NOWHERE" not in _codes(warnings)


# --- guarded-opening rule (Rule 7) -------------------------------------------

def test_fully_guarded_platform_warns():
    sp = _plat_ladder(_warehouse(guard_edges=["N", "S", "E", "W"]))
    _, warnings, _ = L.check(sp)
    assert "LADDER_UNGUARDED_OPENING" in _codes(warnings)


def test_open_edge_platform_ok():
    sp = _plat_ladder(_warehouse(guard_edges=["N", "E", "W"]))  # S open
    _, warnings, _ = L.check(sp)
    assert "LADDER_UNGUARDED_OPENING" not in _codes(warnings)


# --- offset sections / rest platform (s11.6) ----------------------------------

def test_tall_climb_without_rest_warns():
    # tall platform, safety_rail (satisfies s11.5) but no offset/rest deck ->
    # s11.6 nudge to prefer offset sections
    sp = _warehouse(z=9.0)
    sp = _plat_ladder(sp, fall_protection="safety_rail")
    errors, warnings, _ = L.check(sp)
    assert errors == []
    assert any("rest platform" in w for w in warnings)


def test_tall_climb_with_offset_profile_ok():
    sp = _warehouse(z=9.0)
    sp = _plat_ladder(sp, fall_protection="offset")
    _, warnings, _ = L.check(sp)
    assert not any("rest platform" in w for w in warnings)


def test_tall_climb_with_rest_deck_ok():
    sp = _warehouse(z=9.0)
    sp.platforms.append(Platform(id="rest1", x=0, y=-2, z=4.5, size_x=2,
                                 size_y=2, role="rest",
                                 guard_edges=["N", "E", "W"]))
    sp = _plat_ladder(sp, fall_protection="safety_rail")
    _, warnings, _ = L.check(sp)
    assert not any("rest platform" in w for w in warnings)


# --- placement (equipment mode) -----------------------------------------------

def test_equipment_mode_proposes_from_platform():
    sp = _warehouse()
    prop = P.propose(sp, "warehouse_industrial", mode="equipment")
    assert prop["mode"] == "equipment"
    assert len(prop["ladders"]) == 1
    lad = prop["ladders"][0]
    assert lad["placement_mode"] == "platform"
    assert lad["upper_surface"] == "catwalk_a"
    assert lad["transition"] == "side_step_off"


def test_equipment_proposal_passes_review():
    sp = _warehouse(z=9.0)      # tall enough to force offset
    prop = P.propose(sp, "warehouse_industrial", mode="equipment")
    sp.ladders = [Ladder(**l) for l in prop["ladders"]]
    errors, warnings, _ = L.check(sp)
    assert errors == []
    assert prop["ladders"][0]["fall_protection"] == "offset"


def test_equipment_anchors_off_open_edge():
    sp = _warehouse(guard_edges=["N", "E", "W"])   # S is open
    prop = P.propose(sp, "warehouse_industrial", mode="equipment")
    lad = prop["ladders"][0]
    # base sits south of the platform, climber faces north back toward it
    assert lad["y"] < 0 and lad["facing"] == "N"


def test_equipment_fully_guarded_rejected():
    sp = _warehouse(guard_edges=["N", "S", "E", "W"])
    prop = P.propose(sp, "warehouse_industrial", mode="equipment")
    assert any("fully_guarded" in r["reason"] for r in prop["rejected"])


def test_equipment_hazard_base_rejected():
    sp = _warehouse(guard_edges=["N", "E", "W"])
    sp.volumes = [Volume(name="electrical_panel", x=0, y=-1.5, z=1.0,
                         size_x=1, size_y=1, size_z=1.5)]
    prop = P.propose(sp, "warehouse_industrial", mode="equipment")
    assert any("hazard_at_base" in r["reason"] for r in prop["rejected"])


def test_equipment_deterministic():
    a = P.propose(_warehouse(), "warehouse_industrial", mode="equipment")
    b = P.propose(_warehouse(), "warehouse_industrial", mode="equipment")
    assert a["ladders"] == b["ladders"]


def test_no_platforms_notes():
    sp = LevelSpec(name="s", n_stories=1, footprint_x=20, footprint_y=20,
                   rooms=[Room(id="f", story=0, bounds=[-10, -10, 10, 10])])
    prop = P.propose(sp, "warehouse_industrial", mode="equipment")
    assert prop["ladders"] == []
    assert any("no platforms" in n for n in prop["notes"])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all ladder platform tests passed")
