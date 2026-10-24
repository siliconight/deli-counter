"""Pure tests for the stairwell Phase-4 gameplay semantics (no bpy).
Run: python3 test_stair_gameplay.py"""
import interactives
import stairwell as S
from spec_types import (LevelSpec, Stairwell, Room, ExtWall, Opening,
                        Partition, Volume, Marker, Objective)


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("STAIRWELL ", "") for m in msgs}


def _enclosed(role="primary_egress", door_kind="door", second_stair=False):
    """Stair in a role-'stairwell' enclosure, one door to a corridor with a
    grade exit. The canonical protected-stair fixture."""
    stairs = [Stairwell(x=5, y=5, from_story=0, to_story=1, id="a",
                        width=1.2, role=role)]
    if second_stair:
        stairs.append(Stairwell(x=-15, y=-10, from_story=0, to_story=1,
                                id="b", width=1.2, role="secondary_egress"))
    return LevelSpec(
        name="lvl", n_stories=2, footprint_x=40, footprint_y=30,
        stairs=stairs,
        rooms=[Room(id="well", story=0, bounds=[0, 0, 10, 10],
                    role="stairwell"),
               Room(id="corr", story=0, bounds=[-20, -15, 0, 10],
                    role="connector"),
               Room(id="up", story=1, bounds=[-20, -15, 20, 15],
                    role="connector")],
        partitions=[Partition(story=0, axis="Y", pos=0.0, start=0, end=10,
                              openings=[Opening(kind=door_kind, pos=0.0)])],
        ext_walls=[ExtWall(wall="W", story=0,
                           openings=[Opening(kind="door", pos=0.0)])])


# --- door nodes ---------------------------------------------------------------

def test_door_node_found_with_builder_matched_id():
    sysd = S.derive(_enclosed())[0]
    interior = [d for d in sysd["door_nodes"] if not d["discharge_door"]]
    assert len(interior) == 1
    dn = interior[0]
    assert dn["floor"] == 0 and dn["connects_from"] == "corr"
    expected = interactives.interactive_id("lvl", "int_0_0", 0, "door", 0.0)
    assert dn["interactive"] == expected
    assert dn["default_state"] == "closed"


def test_discharge_door_node_at_grade():
    sp = _enclosed()
    # give the WELL itself an exterior door: well spans y 0..10 on the E wall?
    # simpler: approach room at grade with its own W door
    sp.rooms[0] = Room(id="well", story=0, bounds=[-20, 0, 10, 10],
                       role="stairwell")
    sp.stairs[0].x, sp.stairs[0].y = -15, 5
    sysd = S.derive(sp)[0]
    ddoors = [d for d in sysd["door_nodes"] if d["discharge_door"]]
    assert len(ddoors) == 1
    assert ddoors[0]["connects_from"] == "exterior"
    assert ddoors[0]["wall"] == "ext_0_W"


# --- gameplay block -------------------------------------------------------------

def test_egress_network_defaults():
    gp = S.derive(_enclosed())[0]["gameplay"]
    assert gp["network_authority"] == "server"
    assert gp["replicate_door_state"] is True
    assert gp["allow_random_lock"] is False
    assert gp["egress_side_always_openable"] is True
    assert gp["fire_door"] is True and gp["self_closing"] is True
    assert gp["ai_route_cost_multiplier"] == 1.15   # enclosed


def test_unclassified_stair_is_lockable_and_open():
    sp = LevelSpec(name="s", n_stories=2,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1)])
    sysd = S.derive(sp)[0]
    assert sysd["enclosure"] == "open"
    gp = sysd["gameplay"]
    assert gp["allow_random_lock"] is True
    assert gp["egress_side_always_openable"] is False
    assert gp["fire_door"] is False
    assert gp["ai_route_cost_multiplier"] == 1.0


def test_congestion_math():
    gp12 = S.derive(_enclosed())[0]["gameplay"]["congestion"]
    assert gp12 == {"clear_width_m": 1.2, "max_agents_abreast": 1,
                    "two_way_passable": True}
    sp = LevelSpec(name="s", n_stories=2,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                     width=1.6)])
    gp16 = S.derive(sp)[0]["gameplay"]["congestion"]
    assert gp16["max_agents_abreast"] == 2


def test_meta_gameplay_overlay_is_the_escape_hatch():
    sp = _enclosed()
    sp.stairs[0].meta = {"gameplay": {"allow_random_lock": True},
                         "note": "scripted blackout scenario"}
    sysd = S.derive(sp)[0]
    assert sysd["gameplay"]["allow_random_lock"] is True     # authored override
    assert sysd["gameplay"]["network_authority"] == "server"  # rest intact
    assert sysd["meta"]["note"] == "scripted blackout scenario"


# --- egress identity --------------------------------------------------------------

def test_independence_groups_and_pairing():
    sp = _enclosed(second_stair=True)
    # give stair b its own room + exit so the two discharge destinations differ
    # (shrink corr so bwell doesn't sit inside it)
    sp.rooms[1] = Room(id="corr", story=0, bounds=[-20, 0, 0, 10],
                       role="connector")
    sp.rooms.append(Room(id="bwell", story=0, bounds=[-20, -15, -10, 0]))
    sp.ext_walls.append(ExtWall(wall="S", story=0,
                                openings=[Opening(kind="door", pos=-0.35)]))
    systems = S.derive(sp)
    a = next(s for s in systems if s["id"] == "a")
    b = next(s for s in systems if s["id"] == "b")
    assert a["egress"]["paired_with"] == "b"
    assert b["egress"]["paired_with"] == "a"
    assert a["egress"]["independence_group"] != b["egress"]["independence_group"]


# --- Rule 10: reserved volume --------------------------------------------------------

def test_volume_in_egress_shaft_gates():
    sp = _enclosed()
    sp.volumes = [Volume(name="crate_stack", x=5, y=5, z=1.0,
                         size_x=1.0, size_y=1.0, size_z=2.0)]
    errors, _, _ = S.check(sp)
    assert "STAIR_VOLUME_INVADED" in _codes(errors)


def test_volume_in_unclassified_shaft_warns():
    sp = _enclosed(role=None)
    sp.volumes = [Volume(name="crate_stack", x=5, y=5, z=1.0,
                         size_x=1.0, size_y=1.0, size_z=2.0)]
    errors, warnings, _ = S.check(sp)
    assert "STAIR_VOLUME_INVADED" not in _codes(errors)
    assert "STAIR_VOLUME_INVADED" in _codes(warnings)


def test_stair_furniture_and_markers_and_objectives():
    sp = _enclosed()
    sp.volumes = [Volume(name="stair_rail_guard", x=5, y=5, z=1.0,
                         size_x=0.2, size_y=4.0, size_z=1.0)]   # skipped
    sp.markers = [Marker(type="cover_low", x=5, y=5, z=0.0, id="c1")]
    sp.objectives = [Objective(id="drill_spot", x=5.2, y=5.2)]
    errors, _, _ = S.check(sp)
    inv = [e for e in errors if "STAIR_VOLUME_INVADED" in e]
    assert len(inv) == 1
    assert "cover_low marker 'c1'" in inv[0]
    assert "objective 'drill_spot'" in inv[0]
    assert "stair_rail_guard" not in inv[0]


# --- s9.3 locked egress roulette -------------------------------------------------------

def test_locked_only_egress_door_gates():
    sp = _enclosed(door_kind="vault")     # vault machine defaults to locked
    errors, _, _ = S.check(sp)
    assert "LOCKED_EGRESS_DOOR" in _codes(errors)


def test_locked_door_with_backup_egress_downgrades():
    sp = _enclosed(door_kind="vault", second_stair=True)
    sp.rooms[1] = Room(id="corr", story=0, bounds=[-20, 0, 0, 10],
                       role="connector")
    sp.rooms.append(Room(id="bwell", story=0, bounds=[-20, -15, -10, 0]))
    sp.ext_walls.append(ExtWall(wall="S", story=0,
                                openings=[Opening(kind="door", pos=-0.35)]))
    errors, warnings, _ = S.check(sp)
    assert "LOCKED_EGRESS_DOOR" not in _codes(errors)
    assert any("relies on 'b' staying available" in w for w in warnings)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all stair gameplay tests passed")
