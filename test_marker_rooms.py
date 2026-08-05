"""L16: a marker's `room` must be the room it stands in.

`room` is a LABEL a marker carries. Nothing re-derives it from the marker's
coordinates, so the two drift apart with no symptom -- and every consumer that
reasons about rooms is then reasoning about the wrong space: objective
placement rules, patrol routing, the L6 main-entry check, AI room logic.

Found 2026-08-05 while chasing unreachable objectives in the nav gate. The nav
finding turned out to be mostly a convention (attackers spawn outside and
breach in, so interior markers are legitimately unreachable from an exterior
spawn through closed doors). This is what was left once that was stripped out,
and it is a real data defect:

    gas_station_a01  objective 'A'  tagged back_office, stands in sales_floor
    cr_deli          objective 'REGISTER'  tagged deli_counter, stands in
                                           customer_floor

`back_office` versus the public sales floor, and behind the counter versus in
front of it, are not the same place to a heist.

Run:  python -m pytest test_marker_rooms.py
"""
import sys
import types

# layout_lint imports partition_bounds at module scope for an unrelated rule.
if "partition_bounds" not in sys.modules:            # pragma: no cover
    _m = types.ModuleType("partition_bounds")
    _m.partition_overshoot = lambda *a, **k: None
    sys.modules["partition_bounds"] = _m

from layout_lint import marker_room_findings


def spec(rooms, markers):
    return {"rooms": rooms, "markers": markers}


ROOM_A = {"id": "a", "story": 0, "bounds": [0, 0, 10, 10]}
ROOM_B = {"id": "b", "story": 0, "bounds": [20, 0, 30, 10]}


# --- the defect -----------------------------------------------------------

def test_a_marker_in_the_wrong_room_is_reported():
    out = marker_room_findings(spec(
        [ROOM_A, ROOM_B],
        [{"type": "objective", "id": "A", "x": 25, "y": 5, "room": "a"}]))
    assert len(out) == 1
    assert "tagged room 'a'" in out[0]


def test_the_finding_names_the_room_it_is_actually_in():
    """'says A, is in B' is actionable; 'is wrong' is not."""
    out = marker_room_findings(spec(
        [ROOM_A, ROOM_B],
        [{"type": "objective", "id": "A", "x": 25, "y": 5, "room": "a"}]))
    assert "stands in b" in out[0]


def test_a_marker_inside_its_declared_room_is_clean():
    assert marker_room_findings(spec(
        [ROOM_A, ROOM_B],
        [{"type": "objective", "id": "A", "x": 5, "y": 5, "room": "a"}])) == []


def test_a_marker_in_no_room_at_all_says_so():
    out = marker_room_findings(spec(
        [ROOM_A],
        [{"type": "loot", "id": "L", "x": 99, "y": 99, "room": "a"}]))
    assert len(out) == 1
    assert "no room on this storey" in out[0]


# --- attacker spawns are a convention, not a defect -----------------------

def test_attacker_spawns_outside_the_footprint_are_exempt():
    """They are authored outside on purpose -- attackers breach in -- and
    `room` names what they breach INTO. Every spec in the library does this,
    so flagging it would bury the real findings under a convention."""
    assert marker_room_findings(spec(
        [ROOM_A],
        [{"type": "attacker_spawn", "id": "FRONT", "x": 5, "y": -6,
          "room": "a"}])) == []


def test_a_defender_spawn_is_NOT_exempt():
    """Defenders start inside. A defender tagged to the wrong room is the
    same defect as an objective tagged to the wrong room."""
    out = marker_room_findings(spec(
        [ROOM_A, ROOM_B],
        [{"type": "defender_spawn", "x": 25, "y": 5, "room": "a"}]))
    assert len(out) == 1
    assert "defender_spawn" in out[0]


# --- storey matters -------------------------------------------------------

def test_a_room_on_another_storey_is_not_where_the_marker_is():
    """Two rooms can occupy the same plan rectangle on different floors.
    The same-storey candidate is the useful answer."""
    upstairs = {"id": "up", "story": 1, "bounds": [20, 0, 30, 10]}
    out = marker_room_findings(spec(
        [ROOM_A, ROOM_B, upstairs],
        [{"type": "objective", "id": "A", "x": 25, "y": 5, "room": "a"}]))
    assert "stands in b" in out[0]
    assert "up" not in out[0]


# --- things that must not fire --------------------------------------------

def test_a_room_with_no_bounds_cannot_be_judged():
    """Silence, not a false positive. An unbounded room is unknown, and a
    linter that guesses gets switched off."""
    assert marker_room_findings(spec(
        [{"id": "a", "story": 0}],
        [{"type": "objective", "id": "A", "x": 99, "y": 99,
          "room": "a"}])) == []


def test_an_unknown_room_tag_is_left_to_other_rules():
    assert marker_room_findings(spec(
        [ROOM_A],
        [{"type": "objective", "id": "A", "x": 5, "y": 5,
          "room": "does_not_exist"}])) == []


def test_a_marker_with_no_room_tag_is_not_a_finding():
    assert marker_room_findings(spec(
        [ROOM_A],
        [{"type": "objective", "id": "A", "x": 99, "y": 99}])) == []


def test_a_marker_with_no_coordinates_is_skipped():
    assert marker_room_findings(spec(
        [ROOM_A], [{"type": "objective", "id": "A", "room": "a"}])) == []


def test_a_spec_with_no_rooms_is_not_an_error():
    assert marker_room_findings(spec([], [{"type": "objective", "id": "A",
                                           "x": 1, "y": 1, "room": "a"}])) == []


def test_boundary_is_inclusive():
    """A counter set flush to a room's edge is in that room, not a finding.
    Off-by-one here would flag half the library."""
    assert marker_room_findings(spec(
        [ROOM_A],
        [{"type": "objective", "id": "A", "x": 10, "y": 10,
          "room": "a"}])) == []


def test_crew_spawns_are_exempt_like_attacker_spawns():
    """Crew spawn outside and enter, same as attackers. Defenders do not --
    that asymmetry is the whole point of the exemption list."""
    rooms = [{"id": "a", "story": 0, "bounds": [0, 0, 10, 10]}]
    assert marker_room_findings(spec(
        rooms, [{"type": "crew_spawn", "id": "A", "x": 5, "y": -6,
                 "room": "a"}])) == []
    assert len(marker_room_findings(spec(
        rooms, [{"type": "defender_spawn", "x": 5, "y": -6,
                 "room": "a"}]))) == 1
