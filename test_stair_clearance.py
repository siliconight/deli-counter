"""Pure tests for the physical stair-circulation review (no bpy):
oriented entry/exit edges, landing reservations, and the generated-stair
role/facing contract. Run: python3 test_stair_clearance.py"""
import stairwell as S
from spec_types import (LevelSpec, Stairwell, Room, Partition, Opening,
                        Volume)


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("STAIRWELL ", "") for m in msgs}


# --- endpoint derivation ------------------------------------------------------

def test_straight_endpoints_and_landing_rects():
    st = Stairwell(x=0, y=0, from_story=0, to_story=1,
                   width=1.2, run=4.0, style="straight")
    eps = S.stair_endpoints(st)
    assert [e["end"] for e in eps] == ["lower", "upper"]
    lo, up = eps
    # lower landing flush against the first tread, LANDING_DEPTH deep
    assert lo["rect"] == (-0.6, -2.0 - S.LANDING_DEPTH, 0.6, -2.0)
    assert lo["dir"] == (0, -1)
    # upper landing starts past the slab hole's step-off clearance
    assert up["rect"] == (-0.6, 2.0 + S.EXIT_STEP_OFF, 0.6,
                          2.0 + S.EXIT_STEP_OFF + S.LANDING_DEPTH)
    assert up["dir"] == (0, 1)


def test_endpoints_rotate_with_facing():
    base = dict(x=0, y=0, from_story=0, to_story=1,
                width=1.2, run=4.0, style="straight")
    e = S.stair_endpoints(Stairwell(**base, facing="E"))
    lo, up = e
    assert lo["dir"] == (-1, 0) and up["dir"] == (1, 0)   # ascends +X
    assert up["point"][0] > lo["point"][0]
    w = S.stair_endpoints(Stairwell(**base, facing="W"))
    assert w[0]["dir"] == (1, 0) and w[1]["dir"] == (-1, 0)


def test_switchback_exit_end_alternates_with_leg_count():
    one = Stairwell(x=0, y=0, from_story=0, to_story=1,
                    width=1.2, run=4.0, style="switchback")
    up1 = [e for e in S.stair_endpoints(one) if e["end"] == "upper"][0]
    assert up1["dir"] == (0, 1)          # single leg tops out on +Y
    two = Stairwell(x=0, y=0, from_story=0, to_story=2,
                    width=1.2, run=4.0, style="switchback")
    up2 = [e for e in S.stair_endpoints(two) if e["end"] == "upper"][0]
    assert up2["dir"] == (0, -1)         # second (reversed) leg tops out on -Y


def test_scissor_has_endpoints_at_both_ends():
    st = Stairwell(x=0, y=0, from_story=0, to_story=1,
                   width=1.2, run=4.0, style="scissor")
    eps = S.stair_endpoints(st)
    assert len(eps) == 4
    assert sum(1 for e in eps if e["end"] == "lower") == 2
    assert sum(1 for e in eps if e["end"] == "upper") == 2


def test_l_shaped_exits_along_second_leg():
    st = Stairwell(x=0, y=0, from_story=0, to_story=1,
                   width=1.2, run=4.0, style="l_shaped")
    up = [e for e in S.stair_endpoints(st) if e["end"] == "upper"][0]
    assert up["dir"] == (1, 0)           # leg B ascends local +X
    assert up["rect"][0] == 0.6 + 4.0 + S.EXIT_STEP_OFF


def test_spiral_exterior_decorative_have_no_endpoints():
    assert S.stair_endpoints(Stairwell(x=0, y=0, from_story=0, to_story=1,
                                       style="spiral")) == []
    assert S.stair_endpoints(Stairwell(x=30, y=0, from_story=0, to_story=1,
                                       exterior=True)) == []
    assert S.stair_endpoints(Stairwell(x=0, y=0, from_story=0, to_story=1,
                                       role="decorative_nontraversable")) == []


def test_derive_emits_landings_and_nav_endpoints():
    sp = LevelSpec(name="s", n_stories=2, stairs=[
        Stairwell(x=0, y=0, from_story=0, to_story=1, id="a", facing="E",
                  width=1.2, run=4.0, style="straight")])
    sysd = S.derive(sp)[0]
    assert [l["end"] for l in sysd["landings"]] == ["lower", "upper"]
    lo, up = sysd["nav_endpoints"]["lower"], sysd["nav_endpoints"]["upper"]
    assert lo is not None and up is not None
    assert lo[2] == 0.0 and up[2] == sp.story_height   # z on each floor
    assert up[0] > lo[0]                               # ascends east


# --- oriented entry/exit vs the shell -----------------------------------------

def _shell(stair, **kw):
    return LevelSpec(name="s", n_stories=2, footprint_x=24, footprint_y=18,
                     stairs=[stair], **kw)


def test_entry_into_exterior_shell_gates_egress():
    # entry landing needs y down to -9.2 but the inner wall face is at -8.7
    sp = _shell(Stairwell(x=0, y=-6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"))
    errors, _, _ = S.check(sp)
    assert "STAIR_ENTRY_FACES_SOLID" in _codes(errors)


def test_exit_into_exterior_shell_gates_egress():
    sp = _shell(Stairwell(x=0, y=6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"))
    errors, _, _ = S.check(sp)
    assert "STAIR_EXIT_FACES_SOLID" in _codes(errors)


def test_facing_moves_the_failure_to_the_right_wall():
    # same anchor, facing S: the ENTRY is now on the +Y side and clears, but
    # the exit walks into the south wall instead
    sp = _shell(Stairwell(x=0, y=-6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", facing="S", id="a",
                          role="primary_egress"))
    errors, _, _ = S.check(sp)
    codes = _codes(errors)
    assert "STAIR_EXIT_FACES_SOLID" in codes
    assert "STAIR_ENTRY_FACES_SOLID" not in codes


def test_clear_stair_reviews_clean():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"))
    errors, _, _ = S.check(sp)
    assert errors == []


def test_unclassified_stair_gets_intel_not_errors():
    sp = _shell(Stairwell(x=0, y=-6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight"))
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert "STAIR_ENTRY_FACES_SOLID" in _codes(warnings)


def test_decorative_stair_skips_physical_review():
    sp = _shell(Stairwell(x=0, y=-6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="decorative_nontraversable"))
    errors, warnings, _ = S.check(sp)
    assert "STAIR_ENTRY_FACES_SOLID" not in _codes(errors | warnings
                                                   if isinstance(errors, set)
                                                   else set(errors)
                                                   | set(warnings))


# --- partitions, volumes, and other stairs on the landings ---------------------

def test_doorless_partition_at_first_tread_gates():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"),
                partitions=[Partition(story=0, axis="X", pos=-2.2,
                                      start=-5, end=5)])
    errors, _, _ = S.check(sp)
    assert "STAIR_ENTRY_FACES_SOLID" in _codes(errors)


def test_doored_partition_at_first_tread_passes():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"),
                partitions=[Partition(story=0, axis="X", pos=-2.2,
                                      start=-5, end=5,
                                      openings=[Opening(kind="door",
                                                        pos=0.0)])])
    errors, _, _ = S.check(sp)
    assert "STAIR_ENTRY_FACES_SOLID" not in _codes(errors)


def test_partition_deeper_on_landing_blocks_it():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"),
                partitions=[Partition(story=0, axis="X", pos=-2.8,
                                      start=-5, end=5)])
    errors, _, _ = S.check(sp)
    assert "STAIR_LOWER_LANDING_BLOCKED" in _codes(errors)


def test_volume_on_landing_blocks_it():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"))
    sp.volumes = [Volume(name="vending_machine", x=0, y=-2.6, z=0.5,
                         size_x=1.0, size_y=1.0, size_z=1.8)]
    errors, _, _ = S.check(sp)
    assert "STAIR_LOWER_LANDING_BLOCKED" in _codes(errors)


def test_stair_furniture_volume_is_exempt():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"))
    sp.volumes = [Volume(name="stair_rail_guard", x=0, y=-2.6, z=0.5,
                         size_x=1.0, size_y=1.0, size_z=1.0)]
    errors, _, _ = S.check(sp)
    assert errors == []


def test_other_stair_footprint_consumes_landing():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"))
    sp.stairs.append(Stairwell(x=0, y=-4.4, from_story=0, to_story=1,
                               width=1.2, run=4.0, style="straight",
                               id="squatter"))
    errors, _, _ = S.check(sp)
    blocked = [e for e in errors if "STAIR_LOWER_LANDING_BLOCKED" in e]
    assert any("'squatter'" in e for e in blocked)


def test_landing_in_unrouted_space_gates_when_rooms_exist():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="a",
                          role="primary_egress"),
                rooms=[Room(id="north_only", story=0, bounds=[-12, -2, 12, 9],
                            role="connector"),
                       Room(id="up", story=1, bounds=[-12, -9, 12, 9],
                            role="connector")])
    # the room stops at y=-2: the lower landing (y -3.2..-2) has no room
    errors, _, _ = S.check(sp)
    assert "STAIR_LOWER_LANDING_BLOCKED" in _codes(errors)
    assert any("unrouted" in e for e in errors)


# --- generated-stair contract: role + facing are mandatory ----------------------

def test_generated_stair_without_role_errors():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, id="g",
                          meta={"generated_by": "unit_test"}))
    errors, _, _ = S.check(sp)
    assert "STAIR_MISSING_ROLE" in _codes(errors)


def test_generated_stair_without_facing_errors():
    st = Stairwell(x=0, y=0, from_story=0, to_story=1, id="g",
                   role="service", meta={"generated_by": "unit_test"})
    st.facing = None
    errors, _, _ = S.check(_shell(st))
    assert "STAIR_MISSING_FACING" in _codes(errors)


def test_generated_stair_with_both_is_clean():
    sp = _shell(Stairwell(x=0, y=0, from_story=0, to_story=1, id="g",
                          width=1.2, run=4.0, style="straight", facing="N",
                          role="service", meta={"generated_by": "unit_test"}))
    errors, _, _ = S.check(sp)
    assert errors == []


def test_generated_flag_promotes_clearance_to_errors():
    # non-egress role, but generated: physical findings still gate hard
    sp = _shell(Stairwell(x=0, y=-6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="g", role="service",
                          meta={"generated_by": "unit_test"}))
    errors, _, _ = S.check(sp)
    assert "STAIR_ENTRY_FACES_SOLID" in _codes(errors)


def test_authored_stair_without_meta_keeps_old_severity():
    sp = _shell(Stairwell(x=0, y=-6, from_story=0, to_story=1, width=1.2,
                          run=4.0, style="straight", id="g", role="service"))
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert "STAIR_ENTRY_FACES_SOLID" in _codes(warnings)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all stair clearance tests passed")
