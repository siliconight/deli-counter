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


# THE RAILINGS (0.212.0): Zoo's stoop_railing, one a side in two sections

def test_every_stoop_has_a_railing_each_side_in_two_sections():
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        assert [r["name"] for r in p["rails"]] == [
            "stoop_rail_w_level", "stoop_rail_w_flight", "stoop_rail_e_level", "stoop_rail_e_flight"]
        assert [r["form"] for r in p["rails"]] == ["level", "flight"] * 2


def test_a_railing_stands_just_inside_the_stoop_s_side_and_leaves_the_way_up_wide():
    narrowest = agent_contract.contract()["clearances"]["min_corridor_width_m"]
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        xs = sorted({r["centre"][0] for r in p["rails"]})
        assert len(xs) == 2
        # each outer face RAIL_INSET inside the stoop's side
        assert abs((xs[0] - stoop.RAIL_D / 2) - (p["x"] - p["width"] / 2 + stoop.RAIL_INSET)) < 1e-9
        assert abs((xs[1] + stoop.RAIL_D / 2) - (p["x"] + p["width"] / 2 - stoop.RAIL_INSET)) < 1e-9
        # and the way up between them wider than the contract's narrowest corridor
        assert (xs[1] - xs[0]) - stoop.RAIL_D >= narrowest, (n, xs)


def _as_the_gate_reads_them(p, out=0.0):
    """The stoop's pieces and railings as the composer's z-fight gate reads a module -- its box,
    ``(name, (lo, hi))``. ``out`` moves each railing that far toward the stoop's side."""
    def box(c, s):
        return (tuple(c[i] - s[i] / 2 for i in range(3)), tuple(c[i] + s[i] / 2 for i in range(3)))
    boxes = [("stoop_landing", box(*p["landing"]))]
    boxes += [("stoop_tread_%d" % k, box(*t)) for k, t in enumerate(p["treads"], 1)]
    for r in p["rails"]:
        c = list(r["centre"])
        c[0] += out if c[0] > p["x"] else -out
        boxes.append((r["name"], box(c, r["size"])))
    return boxes


def test_no_railing_meets_a_step_face_to_face():
    """Flush with the stoop's side, a flight's box shared the middle tread's side plane, facing the
    same way, over a tread by a riser -- 0.0497 m^2, under the gate's 0.05 m^2 floor. Asked with no
    floor, the gate finds no railing in a pair a camera can reach; the control, each railing pushed
    flush, finds the two flights against the middle tread."""
    import zfight_gate
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        seen, _buried = zfight_gate.visible_fights(_as_the_gate_reads_them(p), area_min=0.0)
        assert not [f for f in seen if "rail" in f["a"] + f["b"]], (n, seen)
        flush, _buried = zfight_gate.visible_fights(
            _as_the_gate_reads_them(p, out=stoop.RAIL_INSET), area_min=0.0)
        assert sorted((f["a"], f["b"]) for f in flush) == [
            ("stoop_tread_1", "stoop_rail_e_flight"), ("stoop_tread_1", "stoop_rail_w_flight")], (n, flush)
        for f in flush:
            assert abs(f["area"] - round(p["tread"] * p["riser"], 3)) < 1e-9, f


def test_the_level_section_runs_the_landing_at_rail_height():
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        for r in (r for r in p["rails"] if r["form"] == "level"):
            (_x, y, z), (sx, sy, sz) = r["centre"], r["size"]
            assert abs((y - sy / 2) - p["head_y"]) < 1e-9 and abs((y + sy / 2) - p["face_y"]) < 1e-9
            assert abs((z - sz / 2) - p["rise"]) < 1e-9 and abs(sz - stoop.RAIL_H) < 1e-9
            # the module's dims: its run along its X
            assert r["dims"] == (sy, sx, sz)


def test_the_flight_runs_from_a_post_on_the_bottom_tread_to_the_landing():
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        bottom_top = p["rise"] - (p["risers"] - 1) * p["riser"]
        nosing = p["head_y"] - (p["risers"] - 1) * p["tread"]
        for r in (r for r in p["rails"] if r["form"] == "flight"):
            (_x, y, z), (sx, sy, sz) = r["centre"], r["size"]
            lo, hi = y - sy / 2, y + sy / 2
            assert abs(hi - p["head_y"]) < 1e-9
            # the post: its centre RAIL_BACK onto the bottom tread, wholly on it
            post = lo + stoop.RAIL_POST / 2
            assert abs(post - (nosing + stoop.RAIL_BACK)) < 1e-9
            assert nosing < lo and lo + stoop.RAIL_POST < nosing + p["tread"]
            # its foot on that tread, its top RAIL_H over the landing
            assert abs((z - sz / 2) - bottom_top) < 1e-9
            assert abs((z + sz / 2) - (p["rise"] + stoop.RAIL_H)) < 1e-9
            assert r["dims"] == (sy, sx, sz)
            # and it ends inside the stoop's depth, which the frontage holds
            assert p["face_y"] - lo < p["depth"]


def test_a_railing_turns_its_high_end_to_the_house():
    """Zoo draws a railing's run along its X, the high end at +X. The composer turns a module by
    `tscn_export.godot_basis` (Ry(-t)), so RAIL_ROT_Y must take +X to Godot -Z -- Blender +Y, into the
    house; 90 would point each flight's rail down at the street."""
    from tscn_export import godot_basis
    rows = godot_basis(stoop.RAIL_ROT_Y, [1.0, 1.0, 1.0])
    # the nine numbers are the matrix's rows: +X's image is its first column
    image = (rows[0], rows[3], rows[6])
    assert abs(image[0]) < 1e-9 and abs(image[1]) < 1e-9 and image[2] < -0.999, image
    wrong = godot_basis(90.0, [1.0, 1.0, 1.0])
    assert wrong[6] > 0.999


def test_the_flight_s_collider_rides_its_rail():
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        bottom_top = p["rise"] - (p["risers"] - 1) * p["riser"]
        for r in p["rails"]:
            kind = r["collider"][0]
            if r["form"] == "level":
                assert kind == "box" and r["collider"][1:] == (r["centre"], r["size"])
                continue
            assert kind == "slab"
            _k, (_cx, cy, cz), (sx, _length, thick), pitch = r["collider"]
            # the slab's top face: its centre moved up its normal by half its thickness
            ty, tz = cy - (thick / 2) * math.sin(pitch), cz + (thick / 2) * math.cos(pitch)

            def top_at(y):
                return tz + (y - ty) * math.tan(pitch)
            (_x, y, _z), (_sx, sy, _sz) = r["centre"], r["size"]
            post = y - sy / 2 + stoop.RAIL_POST / 2
            assert abs(top_at(post) - (bottom_top + stoop.RAIL_H)) < 1e-9
            assert abs(top_at(p["head_y"]) - (p["rise"] + stoop.RAIL_H)) < 1e-9
            # RAIL_H deep, measured upright; as thin as the railing
            assert abs(thick / math.cos(pitch) - stoop.RAIL_H) < 1e-9
            assert sx == stoop.RAIL_D


def test_the_rail_height_is_the_code_s():
    # IRC R311.7.8.1: 34 to 38 in, measured upright over the nosings' sloped plane; drawn at 36, as
    # Zoo's stoop_railing_forms draws it
    assert abs(stoop.RAIL_H - 36 * IN) < 1e-4
    for n in VARIANTS:
        p = stoop.plan(_spec(n))
        bottom_top = p["rise"] - (p["risers"] - 1) * p["riser"]
        for r in (r for r in p["rails"] if r["form"] == "flight"):
            (_x, y, _z), (_sx, sy, _sz) = r["centre"], r["size"]
            post = y - sy / 2 + stoop.RAIL_POST / 2
            # the rail runs straight from RAIL_H over the bottom tread at the post to RAIL_H over the
            # landing at its edge; the walked surface under it is the nosing line
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):
                at = post + t * (p["head_y"] - post)
                over = bottom_top + stoop.RAIL_H + t * (p["rise"] - bottom_top) - stoop.surface_z(p, at)
                assert 34 * IN - 1e-9 <= over <= 38 * IN + 1e-9, (n, t, over)
            # lowest at the post, where it stands RAIL_BACK up the bottom tread: 34.75 in
            over = bottom_top + stoop.RAIL_H - stoop.surface_z(p, post)
            assert abs(over / IN - 34.75) < 0.01, (n, over / IN)


def test_the_railing_s_iron_is_declared():
    for n in VARIANTS:
        s = presets.empty_rowhome(name=n, **presets.EMPTY_ROWHOMES[n])
        assert [m for m in s["materials"] if m["id"] == "metal_painted"], n
