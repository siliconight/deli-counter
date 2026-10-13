"""A rowhome Empty's stoop (0.211.0, factory roadmap 240): steps up to a raised front door -- the
comps' "three or four steps up to each door ... the first floor stands above the sidewalk" -- walked
on one ramp riding the nosings, inside the terrace's 2.0 m frontage, on its own house's front.

Runs without Blender: `stoop.plan` is pure, and the specs are the presets' own output.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract                    # noqa: E402
import presets                           # noqa: E402
import stoop                             # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402

VARIANTS = sorted(presets.EMPTY_ROWHOMES)
IN = 0.0254
#: the body's floor angle, the one `clearances.unassisted_step_max_m` is derived from
#: (R * (1 - cos 45 deg)); the contract records the step and not the angle
FLOOR_MAX_ANGLE_DEG = 45.0


def _spec(name, **over):
    args = dict(presets.EMPTY_ROWHOMES[name], **over)
    return spec_from_dict(presets.empty_rowhome(name=name, **args))


def _ramp_top(p, y):
    """The ramp collider's TOP face at plan ``y``, from the box `plan` emits (centre, size, pitch)."""
    (_x, cy, cz), (_w, length, thick), pitch = p["ramp"]
    # the top face's centre line: the box centre moved up its normal by half its thickness
    ty = cy - (thick / 2.0) * math.sin(pitch)
    tz = cz + (thick / 2.0) * math.cos(pitch)
    return tz + (y - ty) * math.tan(pitch)


def test_every_house_stands_three_steps_up():
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        assert p is not None, n
        assert p["risers"] == stoop.RISERS == 3
        # the door's threshold (the slab's top plus its sill) is three risers above grade
        assert abs(p["rise"] - 3 * stoop.RISER) < 1e-4, (n, p["rise"])
        assert abs(p["riser"] - stoop.RISER) < 1e-4


def test_the_riser_and_tread_are_inside_the_code():
    # IRC R311.7.5: a riser at most 7 3/4 in, a tread at least 10 in
    assert stoop.RISER <= 7.75 * IN and stoop.TREAD >= 10 * IN


def test_a_riser_is_a_wall_so_the_ramp_is_what_a_body_walks():
    step = agent_contract.contract()["clearances"]["unassisted_step_max_m"]
    # a collider a step would be a wall: the reason the stoop is walked on a ramp
    assert stoop.RISER > step
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        # the ramp's pitch is the flight's, and a body stands on it
        assert abs(p["pitch_deg"] - math.degrees(math.atan2(p["riser"], p["tread"]))) < 1e-6
        assert p["pitch_deg"] < FLOOR_MAX_ANGLE_DEG - 5.0, p["pitch_deg"]
        # its top face passes through every nosing -- the landing's front edge and each tread's
        for k in range(p["risers"]):
            y = p["head_y"] - k * p["tread"]
            assert abs(_ramp_top(p, y) - (p["rise"] - k * p["riser"])) < 1e-6, (n, k)
        # it meets grade at its foot, a tread past the bottom riser: no lip to step onto
        assert abs(_ramp_top(p, p["foot_y"])) < 1e-6
        assert abs(p["foot_y"] - (p["head_y"] - p["risers"] * p["tread"])) < 1e-9
        # and its head ends ON the landing's edge, its top face at the landing's top: nothing
        # stands proud of the landing for a body coming down
        (_x, cy, _cz), (_w, length, thick), pitch = p["ramp"]
        ty = cy - (thick / 2.0) * math.sin(pitch)
        assert abs(ty + (length / 2.0) * math.cos(pitch) - p["head_y"]) < 1e-9
        assert abs(_ramp_top(p, p["head_y"]) - p["rise"]) < 1e-9
        # the landing's top is the door's threshold
        (_lx, _ly, lz), (_lw, _ld, lh) = p["landing"]
        assert abs(lz + lh / 2.0 - p["rise"]) < 1e-9


def test_every_piece_rests_in_the_ground():
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        for (_x, _y, z), (_w, _d, h) in [p["landing"]] + p["treads"] + p["unders"]:
            assert abs(z - h / 2.0 + stoop.SKIRT) < 1e-9
        # a tread's top on the nosing line; a block under it one riser short
        for k, ((_x, _y, z), (_w, _d, h)) in enumerate(p["treads"], 1):
            assert abs(z + h / 2.0 - (p["rise"] - k * p["riser"])) < 1e-9
        assert len(p["unders"]) == p["risers"] - 2


def test_a_stoop_fits_the_terrace_s_frontage():
    # Level Factory's terrace keeps every Empty's front 2.0 m behind the sidewalk's back edge
    # (`level_factory/packages/pipeline/empties.py`, FRONTAGE); the ramp's foot must land inside it
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        assert p["depth"] <= stoop.TERRACE_FRONTAGE - 0.2, (n, p["depth"])
        assert abs(p["depth"] - stoop.depth()) < 1e-9
    # four risers would not, with this landing: why three
    assert stoop.depth(risers=4) > stoop.TERRACE_FRONTAGE


def test_a_stoop_stands_on_its_own_house_s_front():
    for n in VARIANTS:
        s = _spec(n)
        p = stoop.plan(s)
        assert abs(p["x"]) + p["width"] / 2.0 <= s.footprint_x / 2.0, (n, p["x"])
        # in front of the house, against its front face
        assert abs(p["face_y"] - (-s.footprint_y / 2.0 - s.wall_thick / 2.0)) < 1e-9


def test_the_door_and_its_window_rise_with_the_floor():
    for n in VARIANTS:
        plain = presets.empty_rowhome(name=n, **dict(presets.EMPTY_ROWHOMES[n], stoop=0))
        raised = presets.empty_rowhome(name=n, **presets.EMPTY_ROWHOMES[n])
        lift = round(3 * stoop.RISER - raised["floor_thick"] / 2.0, 4)
        front = [w for w in raised["ext_walls"] if w["wall"] == "S" and w["story"] == 0][0]
        was = [w for w in plain["ext_walls"] if w["wall"] == "S" and w["story"] == 0][0]
        door = [o for o in front["openings"] if o.get("tag") == "front_door"][0]
        win = [o for o in front["openings"] if o["kind"] == "window"][0]
        win_was = [o for o in was["openings"] if o["kind"] == "window"][0]
        assert door["sill"] == lift
        assert win["sill"] == round(win_was["sill"] + lift, 4)
        # the window's head still below the storey's top
        assert raised["floor_thick"] / 2.0 + win["sill"] + win["height"] < raised["story_height"]
        # nothing above the ground storey moves
        assert [w for w in raised["ext_walls"] if w["story"] > 0] == \
            [w for w in plain["ext_walls"] if w["story"] > 0]


def test_no_stoop_is_the_house_as_it_was():
    for n in VARIANTS:
        plain = presets.empty_rowhome(name=n, **dict(presets.EMPTY_ROWHOMES[n], stoop=0))
        assert "stoop" not in plain
        front = [w for w in plain["ext_walls"] if w["wall"] == "S" and w["story"] == 0][0]
        door = [o for o in front["openings"] if o.get("tag") == "front_door"][0]
        assert "sill" not in door
        assert stoop.plan(spec_from_dict(plain)) is None


def test_the_stoop_s_concrete_is_declared():
    for n in VARIANTS:
        s = presets.empty_rowhome(name=n, **presets.EMPTY_ROWHOMES[n])
        assert [m for m in s["materials"] if m["id"] == "concrete"], n
