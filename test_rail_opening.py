"""A stair rail's opening must be wide enough for the bake to connect it.

WHAT WENT WRONG, because it is the reason every assertion here is an inequality
rather than a fixed number. Deli Counter 0.143.0 clipped a rail's opening to the
solid plate beneath it, `step_d + WALKOFF_CLEAR`. That was right about the floor
and silent about whether what remained still connected. On
`foundry_heist_vertical` the plate is 0.2778 + 0.8 = 1.0778 m and the bake needs
between 1.35 and 1.40, so the basement baked as a disjoint island -- 339
polygons against 1,286 for ground-to-roof, with the stair, a 30 deg ramp and a
ladder all failing to carry. The opening had to be WIDER than the floor under
it, which "opening <= floor" can never give.

0.144.0 lets the opening hang past the plate by up to one body radius. That is
derived rather than chosen: the hazard is an unguarded EDGE, and a body reaches
the void only by getting its capsule centre over it, which the rail prevents
while the overhang stays under `agent_contract.body_radius()`.

WHY THE LIBRARY IS SWEPT HERE AND NOT ONLY BY THE NAV GATE. `nav_gate --all`
would catch a disconnected landing, but it needs a BUILT library, so it fires
when somebody happens to rebuild -- the interval that let 0.143.0's defect sit
unnoticed was five weeks. These read the SPECS and run on a clean checkout.
"""
import glob
import json
import os

import pytest

import agent_contract
import stairwell

HERE = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(HERE, "specs")
#: The styles `stair_guards` emits rail spans for; the others take none.
RAILED = ("straight", "switchback", "scissor")


class _Stair(object):
    """The handful of fields `_step_count` reads, off a raw spec dict."""

    def __init__(self, d):
        self.style = d.get("style")
        self.run = float(d.get("run") or 3.0)
        self.n_steps = d.get("n_steps")
        self.step_rise = float(d.get("step_rise") or 0.18)
        self.id = d.get("id")


def _flights():
    """(shell, stair id, step_d) for every railed flight in the library."""
    out = []
    for p in sorted(glob.glob(os.path.join(SPECS, "*.json"))):
        shell = os.path.basename(p)[:-5]
        if shell.startswith("lf_"):
            continue            # Level Factory transients, graded by LF
        try:
            with open(p, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        H = float(d.get("story_height") or 3.0)
        for raw in (d.get("stairs") or []):
            if raw.get("style") not in RAILED:
                continue
            st = _Stair(raw)
            out.append((shell, st.id or "?",
                        st.run / float(stairwell._step_count(st, H))))
    return out


def _opening(step_d):
    """What `stair_guards` will compute for this flight.

    Mirrors the expression rather than importing it, because the expression is
    inside a loop over spec objects this test does not build. The mirror is
    pinned by `test_the_mirror_matches_the_source` below -- an unchecked mirror
    is how two spellings of one quantity start to drift.
    """
    landing_open = 0.8 + agent_contract.min_door_width()
    return min(landing_open,
               step_d + stairwell.WALKOFF_CLEAR + agent_contract.body_radius())


# ----------------------------------------------------------------- vacuity
def test_the_library_actually_has_railed_flights():
    """With no flights every inequality below holds over an empty set and this
    file passes while checking nothing -- the `or []` shape CLAUDE.md records
    as worse than no check at all."""
    assert len(_flights()) >= 100, "only %d railed flight(s)" % len(_flights())


def test_the_mirror_matches_the_source():
    """`_opening` restates `stair_guards`' expression. If the source changes
    shape this test is measuring a formula nothing builds to."""
    with open(os.path.join(HERE, "stairwell.py"), "r", encoding="utf-8") as fh:
        src = fh.read()
    assert "open_rail = min(open_, step_d + WALKOFF_CLEAR" in src
    assert "+ agent_contract.body_radius())" in src
    assert "landing_open = 0.8 + agent_contract.min_door_width()" in src


# ------------------------------------------------------------- the two ends
def test_the_shell_that_needed_the_overhang_gets_it():
    """RAIL_OPEN_MIN IS NOT A LIBRARY-WIDE MINIMUM, and asserting it as one was
    this test file's first mistake -- caught by running it.

    130 of the library's 149 railed flights leave an opening BELOW 1.4 m
    (a typical step_d of 0.2350 gives 1.3850; the shallowest, 0.1667, gives
    1.3167) and every one of them gates `navigable: yes`. So 1.4 is not what a
    rail opening must be in general. It is what THIS landing needed, and the
    reason is topological rather than dimensional: `foundry_heist_vertical`'s
    basement landing sits in a corner against the south wall, so the rail's
    opening is its ONLY way off. Elsewhere a landing has floor on more than one
    side and survives a narrower gap.

    What actually gates the general case is `nav_gate --all`, which measures
    connectivity instead of guessing at a width. This asserts only the specific
    thing 0.144.0 fixed, so a regression on the shell that exposed it fails
    here without a built library.
    """
    got = [(sid, _opening(step_d)) for shell, sid, step_d in _flights()
           if shell == "foundry_heist_vertical"]
    assert got, "foundry_heist_vertical has no railed flight"
    worst = min(o for _sid, o in got)
    assert worst >= stairwell.RAIL_OPEN_MIN - 1e-9, (
        "foundry_heist_vertical's rail opening is %.4f, under the %.2f m its "
        "basement landing was measured to need (FAIL at 1.35, PASS at 1.40). "
        "Its basement will bake as a disjoint island again."
        % (worst, stairwell.RAIL_OPEN_MIN))


def test_most_of_the_library_sits_below_that_threshold_and_is_fine():
    """The other half of the claim above, asserted so the note cannot rot into
    a comment nobody believes. If this ever fails, 1.4 has quietly become a
    general requirement and the framing above needs rewriting."""
    below = [s for _sh, _i, s in _flights()
             if _opening(s) < stairwell.RAIL_OPEN_MIN - 1e-9]
    assert len(below) > 50, (
        "only %d flight(s) sit below RAIL_OPEN_MIN; the claim that it is a "
        "one-shell threshold rather than a library-wide minimum no longer "
        "holds" % len(below))


def test_no_flight_s_opening_overhangs_its_plate_by_a_body_radius_or_more():
    """The defect 0.143.0 was written to fix, asserted the same way. Before it,
    `foundry_heist_vertical` overhung by 0.9722 m against a 0.35 m radius --
    which is why the walker could step off the side of a staircase."""
    r = agent_contract.body_radius()
    bad = []
    for shell, sid, step_d in _flights():
        plate = step_d + stairwell.WALKOFF_CLEAR
        over = _opening(step_d) - plate
        if over > r + 1e-9:
            bad.append((shell, sid, over))
    assert not bad, (
        "these flights' rail openings hang past their floor by a body radius "
        "(%.2f m) or more, so a body can get its centre over the shaft: %s"
        % (r, ", ".join("%s/%s overhang %.4f" % b for b in bad)))


def test_the_overhang_bound_never_exceeds_the_authored_opening():
    """`open_rail` is a `min` of two things, so the overhang rule can only ever
    make the opening SMALLER than `landing_open`, never larger. If the plate
    plus a body radius exceeded it, this rule would be doing nothing and the
    opening would be back to the pre-0.143.0 value that let a body step off."""
    landing_open = 0.8 + agent_contract.min_door_width()
    deepest = max(step_d for _s, _i, step_d in _flights())
    assert deepest + stairwell.WALKOFF_CLEAR + agent_contract.body_radius()         < landing_open, (
        "the deepest step in the library (%.4f) makes the overhang bound "
        "%.4f, which is not below landing_open %.4f -- the clip is inert"
        % (deepest,
           deepest + stairwell.WALKOFF_CLEAR + agent_contract.body_radius(),
           landing_open))


# --------------------------------------------------------------- one source
def test_the_builder_and_the_reserved_rectangle_read_the_same_walk_off():
    """`deli_counter._stairs` carried its own literal 0.8 while
    `stairwell.WALKOFF_CLEAR` governed the guards and `flight_rect`. Two
    spellings of one quantity: moving the named one would have left the hole
    and the discharge plate behind, and the reserved rectangle and the cut hole
    would disagree -- which puts furniture over a void."""
    with open(os.path.join(HERE, "deli_counter.py"), "r",
              encoding="utf-8") as fh:
        src = fh.read()
    assert "clear = stairwell.WALKOFF_CLEAR" in src
    assert "clear = 0.8" not in src, "a literal walk-off is back"


def test_body_radius_is_the_body_and_not_the_bake():
    """0.40 is the bake's radius -- the fattest navigator plus 0.05 -- and
    using it here would spend a safety margin the contract already spent. The
    contract's own note calls that confusion out by name."""
    assert agent_contract.body_radius() == 0.35
    assert agent_contract.body_radius() != \
        agent_contract.contract()["nav_bake"]["agent_radius_m"]


@pytest.mark.parametrize("shell,step_d", [
    # The shell the defect was found on, and the shallowest step in the
    # library -- pinned so a spec edit that moves either is visible here
    # rather than only in a nav sweep five weeks later.
    ("foundry_heist_vertical", 0.2778),
    ("apartment_walkup_a01", 0.1667),
])
def test_the_shells_the_bounds_were_measured_against(shell, step_d):
    got = [d for s, _i, d in _flights() if s == shell]
    assert got, "%s has no railed flight" % shell
    assert any(abs(d - step_d) < 5e-4 for d in got), (
        "%s step depths %s no longer include %.4f, which the bounds were "
        "measured against" % (shell, [round(d, 4) for d in got], step_d))
