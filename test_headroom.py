"""Headroom over a stair -- the ratified 2.0 m, consumed for the first time.

`agent_contract.json` has ratified `clearances.min_headroom_m: 2.0` with ZERO
consumers repo-wide. Stair validity is planar today: `clearance_findings` uses
z only to filter volumes into a storey band, `circulation.stair_volume` spans
z_lo=-1e6..z_hi=1e6 (prop exclusion, not clearance), and every one of the 34
tests in test_stair_clearance.py works on rects. So nothing in the offline
chain ever asks how much room a body has ABOVE its feet on a flight.

The captured case this pins is `specs/final_stand.json`, which passes
`stairwell.check` with zero errors today and whose `build/final_stand.navgate.json`
reports both stairs `status: "ok"`:

    stair 'final_stand_stair_0'  switchback, x=0.0 y=11.0, story 0 -> 2
    story_height 3.8, step_rise 0.2 -> 19 steps of 0.2 m
    crossing 1, leg 1 (sign -1): tread 17's top face lands at z = 7.40,
        spanning x -1.60..0.00, y 9.21..9.42
    volume 'boss_desk'  x 0.0 y 9.0 z 8.15, 5.0 x 1.6 x 1.2
        -> occupies x -2.50..2.50, y 8.20..9.80, z 7.55..8.75

    7.55 - 7.40 = 0.15 m of head clearance where the contract ratifies 2.0.

That is not a prop near a stair, it is a stair whose last treads run under a
desk. The nav gate bakes with agent_height 1.8 (not the ratified 2.0) and
proves navmesh snap + a polygon path, so it reports ok either way.

Run:  python -m pytest test_headroom.py -q
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract          # noqa: E402
import spec_loader             # noqa: E402
import spec_types              # noqa: E402
import stairwell               # noqa: E402


def _spec(name):
    with open(os.path.join(HERE, "specs", name), "r", encoding="utf-8") as f:
        return spec_loader.spec_from_dict(json.load(f))


def _codes(findings):
    return [c for c, _ in findings]


# ---------------------------------------------------------------------------
# the accessor
# ---------------------------------------------------------------------------

def test_min_headroom_reads_the_ratified_number():
    """A third accessor beside min_door_width/min_corridor_width, and it must
    return what agent_contract.json ratifies -- not a constant that happens to
    agree with it today."""
    assert agent_contract.min_headroom() == 2.0
    assert agent_contract.min_headroom() == \
        agent_contract.contract()["clearances"]["min_headroom_m"]


def test_min_headroom_follows_the_contract_file(tmp_path, monkeypatch):
    """Change the ratified number, the accessor changes. This is the property
    that a hardcoded 2.0 would pass the test above and fail here."""
    p = tmp_path / "alt.json"
    p.write_text(json.dumps({"clearances": {"min_headroom_m": 2.4}}),
                 encoding="utf-8")
    monkeypatch.setenv("DC_AGENT_CONTRACT", str(p))
    monkeypatch.setattr(agent_contract, "_cache", None)
    assert agent_contract.min_headroom() == 2.4
    monkeypatch.setattr(agent_contract, "_cache", None)


# ---------------------------------------------------------------------------
# the ascent path -- the geometry the check stands on
# ---------------------------------------------------------------------------

def test_ascent_surfaces_reach_both_floor_levels():
    """A flight's walking surfaces must start at the lower floor and finish on
    the upper one. If they do not, every headroom number computed from them is
    measured against the wrong feet."""
    spec = _spec("final_stand.json")
    st = spec.stairs[0]
    surf = stairwell.ascent_surfaces(spec, st)
    assert surf, "a switchback spanning two stories has walking surfaces"
    zs = [s[3] for s in surf]
    H = spec.story_height
    assert min(zs) == pytest.approx(H / 19, abs=1e-6)   # first tread top
    assert max(zs) == pytest.approx(2 * H, abs=1e-6)    # arrives on story 2


def test_ascent_surfaces_rotate_with_facing():
    """`facing` rotates the whole stair about (x, y). A path that ignored it
    would sample empty air for every stair not facing N -- and pass."""
    kw = dict(x=0.0, y=0.0, from_story=0, to_story=1, style="straight",
              width=1.6, run=4.0)
    spec = spec_types.LevelSpec(n_stories=2, story_height=3.4)
    n = stairwell.ascent_surfaces(
        spec, spec_types.Stairwell(facing="N", **kw))
    e = stairwell.ascent_surfaces(
        spec, spec_types.Stairwell(facing="E", **kw))
    assert [round(s[2], 4) for s in n] != [round(s[2], 4) for s in e]
    # N travels along y, E along x -- the same run, swapped axes
    assert max(abs(s[2]) for s in n) == pytest.approx(
        max(abs(s[1]) for s in e), abs=1e-6)


# ---------------------------------------------------------------------------
# the check, on captured data
# ---------------------------------------------------------------------------

def test_final_stand_stair_0_runs_under_the_boss_desk():
    """The measured case. 0.15 m of head clearance on the top treads."""
    spec = _spec("final_stand.json")
    st = spec.stairs[0]
    found = stairwell.headroom_findings(spec, st, "final_stand_stair_0")
    assert "STAIR_HEADROOM_BLOCKED" in _codes(found)
    msg = " ".join(m for _, m in found)
    assert "boss_desk" in msg
    assert "0.15" in msg, msg


def test_final_stand_stair_1_is_clear():
    """The second stair in the SAME building has 'garage_cover' sitting ON its
    foot, which is Rule 10's STAIR_VOLUME_INVADED, not headroom. A check that
    flagged both would be reporting overlap, not clearance."""
    spec = _spec("final_stand.json")
    found = stairwell.headroom_findings(spec, spec.stairs[1],
                                        "final_stand_stair_1")
    assert found == []


def test_raising_the_desk_clears_the_finding():
    """The falsifier for the check itself: move the obstruction out of the way
    and the finding must disappear. Without this, a check that always fires
    passes every assertion above.

    The nudge is COMPUTED, not guessed. A first pass at this test lifted the
    desk by a flat 2.0 m and still failed at 1.95 m of clearance, because the
    flight's highest walking surface is the story-2 floor at z=7.60 rather than
    the 7.40 tread the finding quotes -- lifting an obstruction by exactly the
    breach does not clear the breach.
    """
    spec = _spec("final_stand.json")
    top = max(s[3] for s in stairwell.ascent_surfaces(spec, spec.stairs[0]))
    for v in spec.volumes:
        if v.name == "boss_desk":
            v.z = top + agent_contract.min_headroom() + v.size_z / 2 + 0.01
    found = stairwell.headroom_findings(spec, spec.stairs[0],
                                        "final_stand_stair_0")
    assert _codes(found) == []


def test_the_number_comes_from_the_contract(tmp_path, monkeypatch):
    """Relax the ratified headroom below the measured 0.15 m and final_stand
    goes clean. This is what proves the check consumes agent_contract.json
    rather than carrying its own 2.0."""
    spec = _spec("final_stand.json")
    assert stairwell.headroom_findings(spec, spec.stairs[0], "s0")
    p = tmp_path / "loose.json"
    p.write_text(json.dumps({"clearances": {"min_headroom_m": 0.1}}),
                 encoding="utf-8")
    monkeypatch.setenv("DC_AGENT_CONTRACT", str(p))
    monkeypatch.setattr(agent_contract, "_cache", None)
    try:
        assert stairwell.headroom_findings(spec, spec.stairs[0], "s0") == []
    finally:
        agent_contract._cache = None


# ---------------------------------------------------------------------------
# the slab half
# ---------------------------------------------------------------------------

def test_an_uncut_slab_over_a_flight_is_a_finding():
    """`cut_slabs=false` leaves the slab above solid, so the top of the flight
    runs into it. stairwell.check already WARNS about this shape
    (STAIR_TERMINATES_INTO_SLAB) without ever measuring it; this is the
    measurement, in metres, against the ratified number."""
    spec = spec_types.LevelSpec(n_stories=2, story_height=3.4,
                                floor_thick=0.3, footprint_x=20.0,
                                footprint_y=20.0)
    spec.stairs = [spec_types.Stairwell(x=0.0, y=0.0, from_story=0,
                                        to_story=1, style="straight",
                                        cut_slabs=False, id="blocked")]
    found = stairwell.headroom_findings(spec, spec.stairs[0], "blocked")
    assert "STAIR_HEADROOM_UNDER_SLAB" in _codes(found)


def test_cutting_the_slab_clears_it():
    """Same stair, cut_slabs on. The builder's hole spans the whole run, so
    the ceiling becomes the NEXT slab up and the flight is clear."""
    spec = spec_types.LevelSpec(n_stories=2, story_height=3.4,
                                floor_thick=0.3, footprint_x=20.0,
                                footprint_y=20.0)
    spec.stairs = [spec_types.Stairwell(x=0.0, y=0.0, from_story=0,
                                        to_story=1, style="straight",
                                        cut_slabs=True, id="open")]
    assert stairwell.headroom_findings(spec, spec.stairs[0], "open") == []


def test_slab_openings_carry_the_stairs_own_cut():
    """The hole a stair cuts is appended to `spec.slab_holes` by the BUILDER,
    so it is absent at review time -- the containment section says so in as
    many words. Re-deriving it is what lets this check run without Blender."""
    spec = spec_types.LevelSpec(n_stories=2, story_height=3.4)
    spec.stairs = [spec_types.Stairwell(x=1.0, y=2.0, from_story=0,
                                        to_story=1, style="straight")]
    assert spec.slab_holes == []
    op = stairwell.slab_openings(spec)
    assert 1 in op and len(op[1]) == 1
    x0, y0, x1, y1 = op[1][0]
    assert x0 < 1.0 < x1 and y0 < 2.0 < y1


# ---------------------------------------------------------------------------
# how it reports
# ---------------------------------------------------------------------------

def test_check_reports_it_through_the_stairwell_gate():
    """evidence.py runs `stairwell.check` and stores its (errors, warnings)
    under gates.stairwell, so a finding raised here lands in
    build/<name>.validation.json with no new plumbing."""
    spec = _spec("final_stand.json")
    errors, warnings, _summary = stairwell.check(spec)
    everything = errors + warnings
    assert any("STAIR_HEADROOM_BLOCKED" in line for line in everything)


def test_headroom_is_warned_until_the_library_is_at_zero():
    """Measured 2026-08-07 over all 138 specs: 2 stairs breach (final_stand's
    stair_0 at 0.15 m, foundry_heist_vertical's stair_1 at 0.19 m). The repo
    brings a library to zero BEFORE a gate starts refusing builds -- the same
    rollout CONTAINMENT_ENFORCED is mid-way through -- so this ships as intel
    with the promotion switch beside it."""
    assert stairwell.HEADROOM_ENFORCED is False
    spec = _spec("final_stand.json")
    errors, warnings, _ = stairwell.check(spec)
    assert not any("STAIR_HEADROOM" in e for e in errors)
    assert any("STAIR_HEADROOM" in w for w in warnings)


def test_decorative_stairs_are_exempt():
    """A decorative_nontraversable stair is explicitly not walked -- the module
    header says the physical entry/exit/landing checks do not apply to it, and
    headroom is a physical check."""
    spec = spec_types.LevelSpec(n_stories=2, story_height=3.4)
    spec.stairs = [spec_types.Stairwell(
        x=0.0, y=0.0, from_story=0, to_story=1, style="straight",
        cut_slabs=False, role="decorative_nontraversable", id="deco")]
    assert stairwell.headroom_findings(spec, spec.stairs[0], "deco") == []
