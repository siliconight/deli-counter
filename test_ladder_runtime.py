"""Pure tests for ladder Phase 6 (Godot runtime + networking, no bpy).
Run: python3 test_ladder_runtime.py"""
import ladder as L
from spec_types import LevelSpec, Ladder, Room, ExtWall, Opening


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("LADDER ", "") for m in msgs}


def _ladder(**kw):
    base = dict(x=0, y=0, from_story=0, to_story=2, facing="S", id="a",
                role="roof_access", placement_mode="interior",
                lower_surface="mech", upper_surface="roof",
                transition="roof_hatch_exit", access_control="locked_hatch")
    base.update(kw)
    return LevelSpec(
        name="s", n_stories=2, story_height=3.0, footprint_x=40, footprint_y=30,
        ladders=[Ladder(**base)],
        rooms=[Room(id="mech", story=0, bounds=[-5, -5, 5, 5],
                    role="mechanical"),
               Room(id="corr", story=0, bounds=[-20, -5, -5, 5],
                    role="connector")],
        ext_walls=[ExtWall(wall="W", story=0,
                           openings=[Opening(kind="door", pos=0.2)])])


# --- traversal component (s17.1) ----------------------------------------------

def test_traversal_component_shape():
    d = L.derive(_ladder())[0]
    tc = d["traversal_component"]
    assert tc["component"] == "LadderTraversal"
    assert tc["mount_trigger"] == "a_mount"
    assert tc["dismount_trigger"] == "a_dismount"
    assert tc["climb_axis"] == [[0, 0, 0.0], [0, 0, 6.0]]
    assert tc["replication_state"] == "server"
    assert tc["interaction_permissions"] == "restricted"   # locked_hatch


def test_open_ladder_permissions():
    d = L.derive(_ladder(access_control=None))[0]
    assert d["traversal_component"]["interaction_permissions"] == "open"


# --- nav-link (s17.2) ---------------------------------------------------------

def test_nav_link_shape():
    d = L.derive(_ladder())[0]
    nl = d["nav_link"]
    assert nl["id"] == "a_navlink"
    assert nl["start_position"] == [0, 0, 0.0]
    assert nl["end_position"] == [0, 0, 6.0]
    assert nl["bidirectional"] is True
    assert nl["required_capability"] == "climb"
    assert nl["agent_types"] == ["player", "ai_humanoid"]
    assert nl["access_state"] == "locked"                  # locked_hatch


def test_nav_link_direction_maps_bidirectional():
    up = L.derive(_ladder(direction="up_only"))[0]["nav_link"]
    assert up["bidirectional"] is False
    dep = L.derive(_ladder(direction="deploy_then_bidirectional",
                           access_control="locked_gate"))[0]["nav_link"]
    assert dep["bidirectional"] is True


def test_nav_link_cost_by_type():
    fixed = L.derive(_ladder(ladder_type="fixed_vertical"))[0]["nav_link"]
    ship = L.derive(_ladder(ladder_type="ship"))[0]["nav_link"]
    assert ship["cost"] < fixed["cost"]        # a ship ladder is cheaper for AI


# --- authority split (s17.3) --------------------------------------------------

def test_authority_split():
    d = L.derive(_ladder())[0]
    auth = d["authority"]
    assert "locked" in auth["server_owned"]
    assert "player_transition_acceptance" in auth["server_owned"]
    assert "ai_reservation" in auth["server_owned"]
    assert "animation_blend" in auth["client_owned"]
    assert "camera_motion" in auth["client_owned"]
    # no overlap between server- and client-owned state
    assert not (set(auth["server_owned"]) & set(auth["client_owned"]))


def test_authority_present_even_when_open():
    # a non-interactive ladder still declares the split (netcode reads it)
    d = L.derive(_ladder(access_control=None))[0]
    assert d["authority"]["server_owned"]
    assert d["gameplay"]["server_authoritative_state"] is True


# --- AI policy (s17.4) --------------------------------------------------------

def test_ai_policy():
    d = L.derive(_ladder())[0]
    ai = d["ai"]
    assert ai["can_use"] is True
    assert ai["one_at_a_time"] is True
    assert ai["may_attack_while_climbing"] is False
    assert ai["may_follow_to_roof"] is True          # roof_access
    assert ai["recover_if_blocked"] == "return_to_lower_mount"


def test_ai_cannot_use_scripted():
    d = L.derive(_ladder(direction="scripted_direction"))[0]
    assert d["ai"]["can_use"] is False
    assert d["gameplay"]["ai_traversable"] is False


def test_service_ladder_does_not_follow_to_roof():
    d = L.derive(_ladder(role="service_access", upper_surface="mech1",
                         transition="through_step_off"))[0]
    assert d["ai"]["may_follow_to_roof"] is False


# --- combat policy (s17.5) ----------------------------------------------------

def test_combat_policy_defaults():
    d = L.derive(_ladder())[0]
    c = d["combat"]
    assert c["weapons_allowed_while_climbing"] is False
    assert c["can_be_interrupted"] is True
    assert c["can_be_blocked"] is True
    assert c["occupancy_limit"] == 1


def test_combat_can_fall_tracks_fall_protection():
    unprotected = L.derive(_ladder())[0]["combat"]
    assert unprotected["can_fall"] is True
    protected = L.derive(_ladder(fall_protection="safety_rail"))[0]["combat"]
    assert protected["can_fall"] is False


def test_meta_combat_override():
    sp = _ladder()
    sp.ladders[0].meta = {"combat": {"weapons_allowed_while_climbing": True,
                                     "can_be_destroyed": True}}
    c = L.derive(sp)[0]["combat"]
    assert c["weapons_allowed_while_climbing"] is True
    assert c["can_be_destroyed"] is True
    assert c["can_be_interrupted"] is True          # untouched default


def test_meta_occupancy_propagates_everywhere():
    sp = _ladder()
    sp.ladders[0].meta = {"gameplay": {"occupancy_limit": 2}}
    d = L.derive(sp)[0]
    assert d["gameplay"]["occupancy_limit"] == 2
    assert d["combat"]["occupancy_limit"] == 2
    assert d["ai"]["one_at_a_time"] is False
    assert d["ai"]["should_wait_for_agent"] is False


# --- Phase-6 review checks (s13.2, s15.3) -------------------------------------

def test_deploy_without_control_warns():
    sp = _ladder(direction="deploy_then_bidirectional", access_control=None)
    errors, warnings, _ = L.check(sp)
    assert errors == []
    assert any("deployment control" in w for w in warnings)


def test_scripted_direction_warns():
    sp = _ladder(direction="scripted_direction")
    _, warnings, _ = L.check(sp)
    assert any("AI teleport ladder" in w for w in warnings)


def test_deadlock_risk_warns():
    sp = _ladder()
    sp.ladders[0].meta = {"gameplay": {"occupancy_limit": 2}}
    _, warnings, _ = L.check(sp)
    assert "LADDER_MULTIPLAYER_DEADLOCK_RISK" in _codes(warnings)


def test_one_way_high_occupancy_no_deadlock_warn():
    sp = _ladder(direction="up_only")
    sp.ladders[0].meta = {"gameplay": {"occupancy_limit": 2}}
    _, warnings, _ = L.check(sp)
    assert "LADDER_MULTIPLAYER_DEADLOCK_RISK" not in _codes(warnings)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all ladder runtime tests passed")
