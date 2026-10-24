"""Pure tests for ladder.py Phase 1 (no bpy). Run: python3 test_ladder.py"""
import ladder as L
from spec_types import (LevelSpec, Ladder, Room, ExtWall, Opening, Partition,
                        Volume, Parapet)


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("LADDER ", "") for m in msgs}


def _roof_ladder(**kw):
    """A clean interior roof-access ladder from a service room to the roof."""
    base = dict(x=5, y=5, from_story=0, to_story=2, facing="S",
                id="a", role="roof_access", lower_surface="mech",
                upper_surface="roof", transition="roof_hatch_exit",
                access_control="locked_hatch")
    base.update(kw)
    return LevelSpec(
        name="s", n_stories=2, story_height=3.0, footprint_x=40, footprint_y=30,
        ladders=[Ladder(**base)],
        rooms=[Room(id="mech", story=0, bounds=[0, 0, 10, 10], role="mechanical"),
               Room(id="corr", story=0, bounds=[-20, 0, 0, 10], role="connector")],
        ext_walls=[ExtWall(wall="W", story=0,
                           openings=[Opening(kind="door", pos=0.2)])])


# --- derivation ---------------------------------------------------------------

def test_derive_payload_shape():
    d = L.derive(_roof_ladder())[0]
    assert d["role"] == "roof_access"
    assert d["lower_surface"] == "mech" and d["upper_surface"] == "roof"
    assert d["climb_height_m"] == 6.0            # 2 stories x 3.0
    assert d["egress_classification"] == "not_egress"
    assert d["counts_as_primary_egress"] is False
    assert d["counts_as_public_circulation"] is False
    assert set(d["route_nodes"]) == {
        "lower_approach", "lower_mount", "climb_start", "climb_end",
        "upper_dismount", "upper_route"}
    assert d["gameplay"]["mount_anchor_id"] == "a_mount"
    assert d["gameplay"]["occupancy_limit"] == 1


def test_default_ids_stable():
    sp = LevelSpec(name="s", n_stories=2, ladders=[
        Ladder(x=0, y=0, from_story=0, to_story=1, role="service_access"),
        Ladder(x=3, y=0, from_story=0, to_story=1, role="service_access")])
    assert [d["id"] for d in L.derive(sp)] == ["ladder_0", "ladder_1"]


def test_roof_hatch_interaction_from_access_control():
    d = L.derive(_roof_ladder())[0]
    assert d["gameplay"]["interaction_required"] is True    # locked_hatch
    d2 = L.derive(_roof_ladder(access_control=None))[0]
    assert d2["gameplay"]["interaction_required"] is False


# --- Rule 1: role required ----------------------------------------------------

def test_no_role_is_hard_error():
    sp = _roof_ladder(role=None)
    errors, _, _ = L.check(sp)
    assert "LADDER_NO_ROLE" in _codes(errors)


def test_unknown_role_is_hard_error():
    sp = _roof_ladder(role="fire_pole")
    errors, _, _ = L.check(sp)
    assert "LADDER_NO_ROLE" in _codes(errors)


def test_clean_roof_ladder_passes():
    errors, warnings, _ = L.check(_roof_ladder())
    assert errors == []


# --- Rule 2: two real surfaces + onward route ---------------------------------

def test_bad_lower_surface_gates():
    sp = _roof_ladder(lower_surface="does_not_exist")
    errors, _, _ = L.check(sp)
    assert "LADDER_NO_LOWER_SURFACE" in _codes(errors)


def test_ladder_to_nowhere_gates():
    # climbs to story 1 of a 2-story building, but no room exists at story 1
    sp = LevelSpec(name="s", n_stories=2,
                   ladders=[Ladder(x=5, y=5, from_story=0, to_story=1,
                                   role="service_access")],
                   rooms=[Room(id="base", story=0, bounds=[0, 0, 10, 10])])
    errors, _, _ = L.check(sp)
    assert "LADDER_TO_NOWHERE" in _codes(errors)


def test_disconnected_lower_route_gates():
    # lower room exists but is an island (no neighbors, no exterior door)
    sp = LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                   ladders=[Ladder(x=5, y=5, from_story=0, to_story=2,
                                   role="roof_access", lower_surface="island",
                                   upper_surface="roof",
                                   transition="roof_hatch_exit")],
                   rooms=[Room(id="island", story=0, bounds=[0, 0, 10, 10])])
    errors, _, _ = L.check(sp)
    assert "LADDER_ROUTE_DISCONNECTED" in _codes(errors)


# --- Rule 8/9: climb clearance + door/window ----------------------------------

def test_volume_in_climb_gates():
    sp = _roof_ladder()
    sp.volumes = [Volume(name="condenser", x=5, y=5, z=2.0,
                         size_x=1.5, size_y=1.5, size_z=1.5)]
    errors, _, _ = L.check(sp)
    assert "LADDER_CLIMB_VOLUME_BLOCKED" in _codes(errors)


def test_ladder_furniture_not_a_blocker():
    sp = _roof_ladder()
    sp.volumes = [Volume(name="ladder_cage_a", x=5, y=5, z=2.0,
                         size_x=0.6, size_y=0.6, size_z=3.0)]
    errors, _, _ = L.check(sp)
    assert "LADDER_CLIMB_VOLUME_BLOCKED" not in _codes(errors)


def test_door_in_climb_zone_gates():
    # a partition door landing right at the ladder base
    sp = _roof_ladder()
    sp.partitions = [Partition(story=0, axis="X", pos=5.0, start=3, end=7,
                               openings=[Opening(kind="door", pos=0.0)])]
    errors, _, _ = L.check(sp)
    assert "LADDER_DOOR_CONFLICT" in _codes(errors)


def test_window_in_climb_zone_warns():
    sp = _roof_ladder(facing="N")
    # window on the N wall (y = footprint_y/2 = 5); ladder base at y=4 so the
    # climb envelope (extends +Y for facing N) reaches the wall
    sp.footprint_y = 10
    sp.ladders[0].x, sp.ladders[0].y = 0, 4
    sp.ext_walls.append(ExtWall(wall="N", story=0,
                                openings=[Opening(kind="window", pos=0.0)]))
    errors, warnings, _ = L.check(sp)
    assert "LADDER_WINDOW_CONFLICT" in _codes(warnings)


# --- Rule 6: parapet crossover ------------------------------------------------

def test_parapet_without_crossover_warns_for_service():
    sp = _roof_ladder(transition="through_step_off")
    sp.parapets = [Parapet(story=2, height=1.0)]
    errors, warnings, _ = L.check(sp)
    assert "PARAPET_CROSSOVER_MISSING" in _codes(warnings)   # not escape -> warn


def test_hatch_transition_satisfies_parapet():
    sp = _roof_ladder(transition="roof_hatch_exit")
    sp.parapets = [Parapet(story=2, height=1.0)]
    errors, warnings, _ = L.check(sp)
    assert "PARAPET_CROSSOVER_MISSING" not in _codes(warnings)


# --- Rule 11: long climb ------------------------------------------------------

def test_long_climb_unprotected_gates():
    sp = _roof_ladder(from_story=0, to_story=2)
    sp.story_height = 4.0          # 8 m > 7.3 m trigger
    errors, _, _ = L.check(sp)
    assert "LADDER_LONG_CLIMB_UNPROTECTED" in _codes(errors)


def test_long_climb_with_rail_clean():
    sp = _roof_ladder(from_story=0, to_story=2, fall_protection="safety_rail")
    sp.story_height = 4.0
    errors, _, _ = L.check(sp)
    assert "LADDER_LONG_CLIMB_UNPROTECTED" not in _codes(errors)
    assert L.derive(sp)[0]["fall_protection"]["required"] is True


# --- s2 invariant: never ordinary egress --------------------------------------

def test_secondary_escape_on_nonescape_role_gates():
    sp = _roof_ladder(counts_as_secondary_escape=True)   # role roof_access
    errors, _, _ = L.check(sp)
    assert "LADDER_INVALID_EGRESS" in _codes(errors)


def test_escape_role_may_opt_into_secondary_escape():
    sp = _roof_ladder(role="legacy_secondary_escape",
                      counts_as_secondary_escape=True, access_control=None)
    errors, warnings, _ = L.check(sp)
    assert "LADDER_INVALID_EGRESS" not in _codes(errors)
    d = L.derive(sp)[0]
    assert d["counts_as_secondary_escape"] is True
    assert d["egress_classification"] == "legacy_secondary_escape"
    assert "LEGACY_FIRE_ESCAPE_PROFILE" in _codes(warnings)


def test_derive_never_marks_primary_egress():
    for role in L.LADDER_ROLES:
        sp = _roof_ladder(role=role)
        d = L.derive(sp)[0]
        assert d["counts_as_primary_egress"] is False
        assert d["counts_as_public_circulation"] is False


# --- Rule 14: fire-escape ladder needs a system -------------------------------

def test_fire_escape_termination_needs_system():
    sp = _roof_ladder(role="fire_escape_termination")
    errors, _, _ = L.check(sp)
    assert "FIRE_ESCAPE_LADDER_ORPHANED" in _codes(errors)
    # a fire_escape_id that names no real system is still orphaned
    sp1 = _roof_ladder(role="fire_escape_termination", fire_escape_id="ghost")
    assert "FIRE_ESCAPE_LADDER_ORPHANED" in _codes(L.check(sp1)[0])
    # linked to a real fire-escape system -> not orphaned
    from spec_types import FireEscape
    sp2 = _roof_ladder(role="fire_escape_termination", fire_escape_id="fe_1")
    sp2.fire_escapes = [FireEscape(id="fe_1", wall="W", served_stories=[1],
                                   termination="stair_to_grade")]
    errors2, _, _ = L.check(sp2)
    assert "FIRE_ESCAPE_LADDER_ORPHANED" not in _codes(errors2)


# --- Rule 13: restricted + public --------------------------------------------

def test_public_restricted_ladder_warns():
    sp = _roof_ladder(access_class="public", access_control=None)
    errors, warnings, _ = L.check(sp)
    assert "LADDER_SECURITY_EXPOSURE" in _codes(warnings)


# --- meta escape hatch --------------------------------------------------------

def test_meta_gameplay_overlay():
    sp = _roof_ladder()
    sp.ladders[0].meta = {"gameplay": {"occupancy_limit": 2},
                          "note": "wide industrial ladder"}
    d = L.derive(sp)[0]
    assert d["gameplay"]["occupancy_limit"] == 2
    assert d["gameplay"]["player_traversable"] is True
    assert d["meta"]["note"] == "wide industrial ladder"


def test_no_rooms_skips_route_analysis():
    sp = LevelSpec(name="s", n_stories=2,
                   ladders=[Ladder(x=0, y=0, from_story=0, to_story=2,
                                   role="roof_access", upper_surface="roof",
                                   transition="roof_hatch_exit")])
    errors, _, summary = L.check(sp)
    assert summary["route_analysis"] == "skipped (no rooms)"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all ladder tests passed")
