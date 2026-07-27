"""Pure tests for lateral stair containment (no bpy): a body may fall ALONG a
stair but never OUT of it. Covers containment_findings() and its wiring into
check()/circulation_contract. Run: python3 test_stair_containment.py"""
import stairwell as S
from spec_types import LevelSpec, Stairwell, Partition, Volume


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(pairs):
    return {c for c, _ in pairs}


def _shell(stair, **kw):
    # a large plate so a centered stair's sides are nowhere near the shell
    return LevelSpec(name="s", n_stories=2, footprint_x=24, footprint_y=18,
                     stairs=[stair], **kw)


def _straight(**kw):
    base = dict(x=0, y=0, from_story=0, to_story=1, width=1.2, run=4.0,
                style="straight", id="a")
    base.update(kw)
    return Stairwell(**base)


# --- the core failure: a flight open on its sides -----------------------------

def test_open_flight_flags_both_lateral_sides():
    sp = _shell(_straight())
    codes = _codes(S.containment_findings(sp, sp.stairs[0], "a"))
    assert codes == {"STAIR_LATERAL_OPEN"}, codes
    # exactly the two non-mouth sides (W, E); the N/S mouths are never demanded
    msgs = [m for _, m in S.containment_findings(sp, sp.stairs[0], "a")]
    assert len(msgs) == 2
    assert all(" side of the flight is open" in m for m in msgs)


def test_mouth_edges_are_never_required_to_be_guarded():
    # facing N -> mouths on S and N; a finding may only ever cite W or E.
    sp = _shell(_straight())
    for _, m in S.containment_findings(sp, sp.stairs[0], "a"):
        assert m.startswith("'a' W") or m.startswith("'a' E"), m


# --- what satisfies containment ----------------------------------------------

def test_partitions_along_both_sides_clear_it():
    st = _straight()
    # vertical (axis Y) walls at x = -0.6 and +0.6, spanning the flight in Y
    parts = [Partition(story=0, axis="Y", pos=-0.6, start=-2.0, end=2.0),
             Partition(story=0, axis="Y", pos=0.6, start=-2.0, end=2.0)]
    sp = _shell(st, partitions=parts)
    assert S.containment_findings(sp, st, "a") == []


def test_solid_guard_volumes_clear_it():
    st = _straight()
    rail = lambda x: Volume(name=f"stair_rail_{x}", x=x, y=0.0, z=1.05,
                            size_x=0.1, size_y=4.0, size_z=1.1)  # convex default
    sp = _shell(st, volumes=[rail(-0.6), rail(0.6)])
    assert S.containment_findings(sp, st, "a") == []


def test_decorative_guard_without_collision_does_not_count():
    # audit M1: a rail named like a guard but with collision='none' is not a
    # body-retaining barrier -- the side stays flagged.
    st = _straight()
    rail = lambda x: Volume(name=f"stair_rail_{x}", x=x, y=0.0, z=1.05,
                            size_x=0.1, size_y=4.0, size_z=1.1,
                            collision="none")
    sp = _shell(st, volumes=[rail(-0.6), rail(0.6)])
    assert _codes(S.containment_findings(sp, st, "a")) == {"STAIR_LATERAL_OPEN"}


def test_person_sized_gap_still_flags():
    # a wall covering only part of the side leaves a gap wider than the capsule
    st = _straight()
    parts = [Partition(story=0, axis="Y", pos=-0.6, start=-2.0, end=2.0),
             Partition(story=0, axis="Y", pos=0.6, start=-2.0, end=0.5)]  # short
    sp = _shell(st, partitions=parts)
    codes = _codes(S.containment_findings(sp, st, "a"))
    assert codes == {"STAIR_LATERAL_OPEN"}, codes  # the E side gap remains


def test_shell_wall_counts_as_containment():
    # tuck the stair against the east inner face (ix = 12 - wall_thick)
    ix = 24 / 2 - LevelSpec(name="_").wall_thick
    st = _straight(x=ix - 0.6)           # E edge lands on the inner face
    sp = _shell(st)
    msgs = [m for _, m in S.containment_findings(sp, st, "a")]
    assert len(msgs) == 1 and msgs[0].startswith("'a' W"), msgs


# --- the floor-opening (walk-in) failure --------------------------------------

def test_non_mouth_end_flags_opening_unguarded():
    # a 2-leg switchback tops out on the same (S) end it entered, so the N end
    # of the reserved opening is a dangling edge a body on the upper floor walks
    # into -> STAIR_OPENING_UNGUARDED, distinct from the flight-side code.
    st = Stairwell(x=0, y=0, from_story=0, to_story=2, width=1.2, run=4.0,
                   style="switchback", id="a")
    sp = LevelSpec(name="s", n_stories=3, footprint_x=40, footprint_y=40,
                   stairs=[st])
    codes = _codes(S.containment_findings(sp, st, "a"))
    assert "STAIR_OPENING_UNGUARDED" in codes, codes
    assert "STAIR_LATERAL_OPEN" in codes           # the sides are still open too


# --- scope: what is out of scope ---------------------------------------------

def test_out_of_scope_stairs_report_nothing():
    big = dict(footprint_x=40, footprint_y=40, n_stories=2)
    spiral = LevelSpec(name="s", stairs=[Stairwell(x=0, y=0, from_story=0,
                       to_story=1, style="spiral", id="a")], **big)
    exterior = LevelSpec(name="s", stairs=[Stairwell(x=30, y=0, from_story=0,
                         to_story=1, exterior=True, id="a")], **big)
    deco = LevelSpec(name="s", stairs=[Stairwell(x=0, y=0, from_story=0,
                     to_story=1, role="decorative_nontraversable", id="a")],
                     **big)
    for sp in (spiral, exterior, deco):
        assert S.containment_findings(sp, sp.stairs[0], "a") == []


# --- wiring: severity + contract stamp respect the rollout flag ---------------

def test_check_reports_containment_as_warning_by_default():
    assert S.CONTAINMENT_ENFORCED is False
    sp = _shell(_straight())
    errors, warnings, _ = S.check(sp)
    assert "STAIR_LATERAL_OPEN" not in _codes_from_msgs(errors)
    assert "STAIR_LATERAL_OPEN" in _codes_from_msgs(warnings)


def test_check_promotes_to_hard_error_when_enforced():
    sp = _shell(_straight())
    S.CONTAINMENT_ENFORCED = True
    try:
        errors, _, _ = S.check(sp)[0], *S.check(sp)[1:]
        errs = S.check(sp)[0]
        assert "STAIR_LATERAL_OPEN" in _codes_from_msgs(errs)
        # and it joins the compliance stamp
        contract = S.circulation_contract(sp)
        assert "STAIR_LATERAL_OPEN" in contract["checks"]
        assert contract["all_compliant"] is False
    finally:
        S.CONTAINMENT_ENFORCED = False
    # once reset, the stamp drops back to the longitudinal checks only
    assert "STAIR_LATERAL_OPEN" not in S.circulation_contract(sp)["checks"]


def _codes_from_msgs(msgs):
    # check() emits "STAIRWELL <CODE>: ..." strings
    return {m.split(":")[0].replace("STAIRWELL ", "").strip() for m in msgs}


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for fn in ALL:
        _run(fn)
    print(f"\n{len(ALL)} containment tests passed.")
