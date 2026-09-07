"""L19: a stair may not reserve ground outside its own building (roadmap 115).

THE CAPTURED CASE is `primos_pizza`, quarantined 2026-09-07 for a stair the
navmesh baked as two islands. Its stair sat at y 4.5 with `run` 5.2, so the
rectangle it reserves reached y 7.9 in a building whose north face is at
y 7.0, and `tools/stair_probe.gd` found the first surface under the walker at
the foot of the climb to be `ext_col_0_N_lintel1` -- the exterior wall.

TWO WRONG ANSWERS ARE PINNED HERE ALONGSIDE THE RIGHT ONE, because both were
reached on the way and both looked finished:

  y 4.5 run 5.2   0.90 m past the wall CENTRELINE   the original defect
  y 4.0 run 4.4   0.00 m past the centreline, and   the first repair: it
                  0.15 m past the wall's inner      passes a centreline rule
                  FACE                              and is still in the wall
  y 3.9 run 4.0   0.15 m of clearance to the face   what ships

The middle row is why this rule measures to `footprint/2 - wall_thick/2`.
`footprint_x / 2` is where the exterior wall is CENTRED, so a flight reaching
exactly that already buries half a wall thickness of itself in solid. At that
moment the centreline reading returned ZERO findings across all 162 specs and
the face reading returned one -- the stair that was supposed to be fixed.

    python -m pytest test_stair_bounds.py -q
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint
import spec_loader
import stairwell


def _spec():
    with open(os.path.join(HERE, "specs", "primos_pizza.json"),
              encoding="utf-8") as f:
        return json.load(f)


def _with_stair(**kw):
    d = _spec()
    d["stairs"][0].update(kw)
    return d


# ---- the rule fires on the captured case ----------------------------------

def test_the_original_placement_is_a_finding():
    out = layout_lint.stair_bounds_findings(_with_stair(y=4.5, run=5.2))
    assert len(out) == 1, out
    assert "L19" in out[0] and "primos_pizza_stair_0" in out[0]
    assert "1.05" in out[0], out[0]      # 0.90 past centreline + half a wall


def test_the_first_repair_still_fires_because_it_is_inside_the_wall():
    """It cleared the footprint LINE and not the wall. A centreline rule would
    have called this fixed and shipped a flight buried 0.15 m in solid."""
    out = layout_lint.stair_bounds_findings(_with_stair(y=4.0, run=4.4))
    assert len(out) == 1, out
    assert "0.15" in out[0], out[0]
    assert "inner face" in out[0]


def test_the_shipped_placement_passes():
    assert layout_lint.stair_bounds_findings(_spec()) == []


def test_an_exterior_tower_is_exempt():
    """An exterior stair stands OUTSIDE the shell against a facade by design
    (spec s8.4). Reporting it would make the rule unusable on every tower."""
    assert layout_lint.stair_bounds_findings(
        _with_stair(y=4.5, run=5.2, exterior=True)) == []


def test_the_finding_says_what_to_do_and_what_not_to_do():
    out = layout_lint.stair_bounds_findings(_with_stair(y=4.5, run=5.2))
    assert "Move the stair or shorten its run" in out[0]
    assert "do NOT cut the shell" in out[0]


# ---- the shipped geometry, measured rather than asserted -------------------

def test_the_shipped_stair_clears_the_wall_and_stays_walkable():
    spec = spec_loader.load_spec(os.path.join(HERE, "specs",
                                              "primos_pizza.json"))
    st = spec.stairs[0]
    bx = spec.footprint_x / 2 - spec.wall_thick / 2
    by = spec.footprint_y / 2 - spec.wall_thick / 2
    worst = None
    for s in range(min(st.from_story, st.to_story),
                   max(st.from_story, st.to_story)):
        x0, y0, x1, y1 = stairwell.flight_rect(st, s)
        m = min(bx - x1, x0 + bx, by - y1, y0 + by)
        worst = m if worst is None else min(worst, m)
    assert worst >= 0.1, worst          # real clearance, not tangency
    # ...and shortening a run steepens a flight. `agent_max_slope_deg` is 55
    # but `floor_max_angle` -- what a body actually stands on -- is 45, and
    # CLAUDE.md records 20 of 38 buildings already emitting 45.0-51.3 degrees.
    pitch = math.degrees(math.atan2(spec.story_height, st.run))
    assert pitch < 45.0, pitch


def test_no_other_spec_in_the_library_trips_the_rule():
    """Attribute the whole output: if this rule ever fires on something else,
    that is a finding to account for, not a threshold to loosen."""
    import glob
    hits = {}
    paths = sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
    assert len(paths) > 100, len(paths)   # a sweep over nothing proves nothing
    for path in paths:
        with open(path, encoding="utf-8") as f:
            try:
                d = json.load(f)
            except Exception:
                continue
        out = layout_lint.stair_bounds_findings(d)
        if out:
            hits[os.path.basename(path)] = out
    assert hits == {}, hits
