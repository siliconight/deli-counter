"""Pure tests for stairwell.py (no bpy). Run: python3 test_stairwell.py"""
import stairwell as S
from spec_types import LevelSpec, Stairwell, Room, ExtWall, Opening, Partition


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("STAIRWELL ", "") for m in msgs}


# --- derivation -------------------------------------------------------------

def test_footprint_and_floors():
    sp = LevelSpec(name="s", n_stories=2)
    st = Stairwell(x=10, y=7.5, from_story=0, to_story=1,
                   width=1.2, run=5.0, style="switchback")
    # switchback reserves both parallel runs: width + 2*(width/2) = 2*width
    assert S.footprint_rect(st) == (10 - 1.2, 5.0, 10 + 1.2, 10.0)
    st2 = Stairwell(x=0, y=0, from_story=0, to_story=1, width=1.2, run=4.0,
                    style="straight")
    assert S.footprint_rect(st2) == (-0.6, -2.0, 0.6, 2.0)
    # clamp: no basement -> nothing below 0; to_story past top = roof level
    st3 = Stairwell(x=0, y=0, from_story=-1, to_story=3)
    assert S.floors_served(sp, st3) == [0, 1, 2]


def test_derive_payload_shape():
    sp = LevelSpec(name="s", n_stories=2, stairs=[
        Stairwell(x=0, y=0, from_story=0, to_story=1, id="a",
                  role="primary_egress")])
    sysd = S.derive(sp)[0]
    assert sysd["id"] == "a" and sysd["role"] == "primary_egress"
    assert sysd["shape"] == "switchback"
    assert sysd["floors_served"] == [0, 1]
    assert len(sysd["footprint_polygon"]) == 4
    assert sysd["egress"]["counts_as_exit"] is True
    assert sysd["approach"] == [] and sysd["discharge"] is None  # no rooms


def test_default_ids_are_stable():
    sp = LevelSpec(name="s", stairs=[
        Stairwell(x=0, y=0, from_story=0, to_story=1),
        Stairwell(x=9, y=0, from_story=0, to_story=1)])
    assert [d["id"] for d in S.derive(sp)] == ["stair_0", "stair_1"]


# --- severity policy: unclassified warns, egress gates ----------------------

def _prohibited_spec(role):
    return LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                     stairs=[Stairwell(x=5, y=5, from_story=0, to_story=1,
                                       id="a", role=role)],
                     rooms=[Room(id="stock", story=0, bounds=[0, 0, 10, 10],
                                 role="storage"),
                            Room(id="up", story=1, bounds=[0, 0, 10, 10],
                                 role="connector")])


def test_unclassified_stair_warns_not_errors():
    errors, warnings, summary = S.check(_prohibited_spec(None))
    assert errors == []
    assert "STAIR_ACCESS_THROUGH_PROHIBITED_ROOM" in _codes(warnings)
    assert summary["classified"] == 0


def test_egress_stair_gates_prohibited_approach():
    errors, warnings, _ = S.check(_prohibited_spec("primary_egress"))
    assert "STAIR_ACCESS_THROUGH_PROHIBITED_ROOM" in _codes(errors)


def test_unknown_role_downgrades_to_intel():
    errors, warnings, _ = S.check(_prohibited_spec("escalator"))
    assert errors == []
    assert any("unknown role" in w for w in warnings)


# --- approach through an enclosure (role "stairwell") ------------------------

def test_enclosure_with_only_prohibited_neighbors_gates():
    sp = LevelSpec(name="s", n_stories=1, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=5, y=5, from_story=0, to_story=1,
                                     id="a", role="primary_egress")],
                   rooms=[Room(id="well", story=0, bounds=[0, 0, 10, 10],
                               role="stairwell"),
                          Room(id="stock", story=0, bounds=[10, 0, 20, 10],
                               role="storage")])
    errors, _, _ = S.check(sp)
    assert "STAIR_ACCESS_THROUGH_PROHIBITED_ROOM" in _codes(errors)


def test_enclosure_with_corridor_neighbor_and_discharge_is_clean():
    sp = LevelSpec(name="s", n_stories=1, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=5, y=5, from_story=0, to_story=1,
                                     id="a", role="primary_egress")],
                   rooms=[Room(id="well", story=0, bounds=[0, 0, 10, 10],
                               role="stairwell"),
                          Room(id="stock", story=0, bounds=[10, 0, 20, 10],
                               role="storage"),
                          Room(id="corr", story=0, bounds=[-20, 0, 0, 10],
                               role="connector")],
                   ext_walls=[ExtWall(wall="W", story=0,
                                      openings=[Opening(kind="door", pos=0.2)])])
    errors, _, _ = S.check(sp)
    assert errors == []
    d = S.derive(sp)[0]["discharge"]
    assert d["type"] == "exit_passage" and d["destination"] == "corr"


# --- discharge --------------------------------------------------------------

def test_direct_exterior_discharge():
    sp = LevelSpec(name="s", n_stories=1, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=-15, y=5, from_story=0, to_story=1)],
                   rooms=[Room(id="well", story=0, bounds=[-20, 0, -10, 10])],
                   ext_walls=[ExtWall(wall="W", story=0,
                                      openings=[Opening(kind="door", pos=0.2)])])
    d = S.derive(sp)[0]["discharge"]
    assert d["type"] == "direct_exterior" and d["route_hops"] == 0


def test_no_ground_discharge_gates_egress():
    sp = LevelSpec(name="s", n_stories=1, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=5, y=5, from_story=0, to_story=1,
                                     id="a", role="secondary_egress")],
                   rooms=[Room(id="well", story=0, bounds=[0, 0, 10, 10])])
    errors, _, _ = S.check(sp)
    assert "STAIR_NO_GROUND_DISCHARGE" in _codes(errors)


# --- egress pairs: separation + independence ---------------------------------

def test_required_stairs_too_close():
    # 40x30 plate: diag 50 m, factor 0.33 -> required 16.5 m; these sit 5 m apart
    sp = LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                     id="a", role="primary_egress"),
                           Stairwell(x=5, y=0, from_story=0, to_story=1,
                                     id="b", role="secondary_egress")])
    errors, _, _ = S.check(sp)
    assert "REQUIRED_STAIRS_TOO_CLOSE" in _codes(errors)


def test_shared_chokepoint_gates():
    sp = LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=-13, y=10, from_story=0, to_story=1,
                                     id="a", role="primary_egress"),
                           Stairwell(x=13, y=10, from_story=0, to_story=1,
                                     id="b", role="secondary_egress")],
                   rooms=[Room(id="left", story=0, bounds=[-20, 5, -6, 15]),
                          Room(id="right", story=0, bounds=[6, 5, 20, 15]),
                          Room(id="hall", story=0, bounds=[-20, -5, 20, 5],
                               role="connector"),
                          Room(id="exitrm", story=0, bounds=[-20, -15, 20, -5],
                               role="lobby")],
                   ext_walls=[ExtWall(wall="S", story=0,
                                      openings=[Opening(kind="door", pos=0.0)])])
    errors, _, _ = S.check(sp)
    assert "REQUIRED_ROUTES_SHARE_SINGLE_CHOKEPOINT" in _codes(errors)
    assert any("'hall'" in e for e in errors)


# --- declared stacks (Rule 2) -------------------------------------------------

def test_declared_stack_must_align():
    sp = LevelSpec(name="s", n_stories=3, stairs=[
        Stairwell(x=0, y=0, from_story=0, to_story=1, id="lo",
                  stack_id="core"),
        Stairwell(x=12, y=0, from_story=1, to_story=2, id="hi",
                  stack_id="core")])
    errors, _, _ = S.check(sp)
    assert "STAIR_NOT_STACKED" in _codes(errors)


def test_aligned_stack_is_clean():
    sp = LevelSpec(name="s", n_stories=3, stairs=[
        Stairwell(x=0, y=0, from_story=0, to_story=1, id="lo",
                  stack_id="core"),
        Stairwell(x=0, y=0, from_story=1, to_story=2, id="hi",
                  stack_id="core")])
    errors, _, _ = S.check(sp)
    assert errors == []


# --- intel warnings -----------------------------------------------------------

def test_basement_continuation_warns():
    sp = LevelSpec(name="s", n_stories=2, has_basement=True,
                   stairs=[Stairwell(x=0, y=0, from_story=-1, to_story=1,
                                     id="a", role="primary_egress")])
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert "BASEMENT_CONTINUATION_NOT_INTERRUPTED" in _codes(warnings)


def test_door_over_treads_warns():
    sp = LevelSpec(name="s", n_stories=1,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                     width=1.2, run=6.0, style="straight")],
                   partitions=[Partition(story=0, axis="X", pos=0.0,
                                         start=-5, end=5,
                                         openings=[Opening(kind="door",
                                                           pos=0.0)])])
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert "STAIR_DOOR_OPENS_ONTO_TREAD" in _codes(warnings)


def test_no_rooms_skips_route_analysis():
    sp = LevelSpec(name="s", n_stories=2,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                     id="a", role="primary_egress")])
    errors, _, summary = S.check(sp)
    assert errors == []
    assert summary["route_analysis"] == "skipped (no rooms)"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all stairwell tests passed")
