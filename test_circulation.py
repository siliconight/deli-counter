"""Unit tests for circulation.py -- the prop-vs-circulation gate.

Volumes come from real contract data shapes (gameplay ladder markers, doorway
slots, stair systems); props are synthetic GLB-space AABBs. Sub-second, pure.
"""
import circulation as C


def _ladder(**kw):
    m = {"name": "LADDER_0", "type": "ladder", "id": "ladder_0",
         "x": 2.0, "y": -3.0, "z": 0.0,
         "climb_height": 3.6, "width": 0.5, "facing": "S"}
    m.update(kw)
    return m


def _doorway(**kw):
    s = {"slot_id": "w_open0", "role": "doorway",
         "transform": {"translation": [1.0, 0.0, 1.8], "rot_y": 0,
                       "scale": [1, 1, 1]},
         "fit": {"dims": [1.2, 0.2, 3.6], "pivot": "center",
                 "openings": [{"kind": "door", "width": 1.0, "height": 2.1,
                               "sill": 0.0}]}}
    s.update(kw)
    return s


def _stair(**kw):
    st = {"id": "stair_0",
          "footprint_polygon": [[4, 4], [7, 4], [7, 6], [4, 6]]}
    st.update(kw)
    return st


# ---- volume derivation ------------------------------------------------------

def test_ladder_volume_matches_climb_contract():
    lo, hi = C.ladder_volume(_ladder())
    # facing S -> approach is -Y: volume sits at y in [-3.85, -3.05]
    assert abs(lo[1] - -3.85) < 1e-9 and abs(hi[1] - -3.05) < 1e-9
    # across (X): width + catch margin, centred on x=2
    assert abs((hi[0] - lo[0]) - (0.5 + 0.6)) < 1e-9
    # vertical: [-0.5, climb_height + 0.5] (mount headroom split by centring)
    assert abs(lo[2] - -0.5) < 1e-9 and abs(hi[2] - 4.1) < 1e-9


def test_ladder_volume_faces_each_direction():
    for facing, axis, sign in (("N", 1, 1), ("S", 1, -1),
                               ("E", 0, 1), ("W", 0, -1)):
        lo, hi = C.ladder_volume(_ladder(facing=facing))
        centre = (lo[axis] + hi[axis]) / 2
        base = -3.0 if axis == 1 else 2.0
        assert (centre - base) * sign > 0, facing


def test_doorway_volume_spans_both_sides_of_wall():
    lo, hi = C.doorway_volume(_doorway())
    # rot 0: aperture along X (1.0 wide), clearance along Y
    assert abs((hi[0] - lo[0]) - 1.0) < 1e-9
    assert abs((hi[1] - lo[1]) - (0.2 + 2 * C.DOOR_CLEARANCE)) < 1e-9
    # z: sill 0 at segment bottom (1.8 - 1.8) up 2.1
    assert abs(lo[2] - 0.0) < 1e-9 and abs(hi[2] - 2.1) < 1e-9


def test_doorway_volume_rotated_wall_swaps_axes():
    lo, hi = C.doorway_volume(_doorway(
        transform={"translation": [1.0, 0.0, 1.8], "rot_y": 90,
                   "scale": [1, 1, 1]}))
    assert abs((hi[1] - lo[1]) - 1.0) < 1e-9         # width now along Y
    assert (hi[0] - lo[0]) > 1.0                     # clearance along X


def test_doorway_volume_ignores_non_doorway_roles():
    assert C.doorway_volume(_doorway(role="window")) is None


def test_stair_volume_is_full_column_over_footprint():
    lo, hi = C.stair_volume(_stair(), z_lo=-1.0, z_hi=8.0)
    assert lo[:2] == [4, 4] and hi[:2] == [7, 6]
    assert lo[2] == -1.0 and hi[2] == 8.0


def test_circulation_volumes_collects_all_families():
    vols = C.circulation_volumes(
        {"slots": [_doorway(), {"slot_id": "w0", "role": "wall"}]},
        {"markers": [_ladder(), {"type": "door"}],
         "stair_systems": [_stair()]})
    names = sorted(n.split(":")[0] for n, _ in vols)
    assert names == ["doorway", "ladder", "stair"]


# ---- conflict detection -----------------------------------------------------

def _godot_box_at(bx, by, bz, sx=0.5, sy=0.5, sz=0.5):
    """A prop AABB in GLB space centred on the BLENDER point (bx, by, bz)."""
    gx, gy, gz = bx, bz, -by
    return ([gx - sx / 2, gy - sy / 2, gz - sz / 2],
            [gx + sx / 2, gy + sy / 2, gz + sz / 2])


def test_prop_in_ladder_volume_flags():
    vols = [("ladder:l0", C.ladder_volume(_ladder()))]
    # crate parked on the approach side of the ladder base
    props = [("crate", _godot_box_at(2.0, -3.4, 0.5))]
    out = C.prop_conflicts(props, vols)
    assert len(out) == 1 and out[0]["volume"] == "ladder:l0"
    assert out[0]["penetration"] > 0.1


def test_prop_beside_ladder_passes():
    vols = [("ladder:l0", C.ladder_volume(_ladder()))]
    # same distance out, but 2 m along the wall -- clear of the climb volume
    props = [("crate", _godot_box_at(4.0, -3.4, 0.5))]
    assert C.prop_conflicts(props, vols) == []


def test_prop_in_doorway_flags_and_graze_ignored():
    vols = [("doorway:d0", C.doorway_volume(_doorway()))]
    blocked = [("shelf", _godot_box_at(1.0, 0.0, 1.0))]
    assert len(C.prop_conflicts(blocked, vols)) == 1
    # 1 cm graze on the clearance edge: below PEN_MIN, not a finding
    graze = [("skirting", _godot_box_at(1.0, 0.2 / 2 + C.DOOR_CLEARANCE
                                        + 0.25 - 0.01, 1.0))]
    assert C.prop_conflicts(graze, vols) == []


def test_doorway_trim_tolerated_but_ladder_is_not():
    """A door frame's AABB covers the aperture but is only frame-deep on its
    thin axis (5 cm measured on real builds): legal at a doorway, still a
    finding inside a ladder climb volume."""
    door_vols = [("doorway:d0", C.doorway_volume(_doorway()))]
    # frame-depth trim: thin (5 cm overlap) along the wall normal (Y)
    frame = [("Cover_frame", _godot_box_at(1.0, 0.0, 1.0,
                                           sx=1.2, sy=1.2, sz=0.05))]
    assert C.prop_conflicts(frame, door_vols) == []
    lad_vols = [("ladder:l0", C.ladder_volume(_ladder()))]
    # the same 5 cm intrusion into a climb volume DOES flag (> PEN_MIN)
    sliver = [("bracket", _godot_box_at(2.0, -3.075, 1.0,
                                        sx=0.3, sy=0.05, sz=0.3))]
    out = C.prop_conflicts(sliver, lad_vols)
    assert len(out) == 1 and out[0]["penetration"] > C.PEN_MIN


def test_prop_in_stair_shaft_flags_at_any_height():
    vols = [("stair:s0", C.stair_volume(_stair(), z_lo=0.0, z_hi=7.2))]
    for z in (0.5, 3.7, 6.9):
        props = [("box", _godot_box_at(5.5, 5.0, z))]
        assert len(C.prop_conflicts(props, vols)) == 1, z


def test_empty_inputs_are_clean():
    assert C.circulation_volumes({}, {}) == []
    assert C.prop_conflicts([], []) == []
    assert C.prop_conflicts([("p", ([0, 0, 0], [1, 1, 1]))], []) == []
