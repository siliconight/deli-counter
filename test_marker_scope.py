"""A building-scope bake may only judge markers inside the building.

Measured 2026-08-08 over all 135 shells in `build/` carrying both a gameplay
and a navgate manifest (`marker_scope_census.py`):

    extraction OUTSIDE the footprint x UNREACHABLE      99
    extraction OUTSIDE the footprint x reachable         8
    extraction INSIDE  the footprint x reachable        11
    extraction INSIDE  the footprint x UNREACHABLE       1
    no extraction marker at all                         16

An extraction point stands on the street. Lot lays the street when it
assembles the site, so a per-building navmesh cannot contain it. The gate
asked anyway and answered "no" 99 times, and none of those answers were about
the building. `docs/NAV_GATE_FINDINGS.md` called this benign on 2026-08-05 and
said the distinction was "NOT yet implemented"; a Level Factory selection rule
was then keyed on the uncorrected number and kept 6 of 134 shells, two of them
for having no extraction marker or one placed indoors.

THE DISCRIMINATOR IS GEOMETRY, NOT SNAP DISTANCE. The two disagree ten times
in this library -- six of them where a real interior defect would be dropped
as benign (`cr_deli objective_SAFE`, snap 2.6 m, inside the footprint) and
four where a benign exterior one would be reported (`gas_station
extraction_FORECOURT`, snap 1.2 m, outside it). Snap distance correlates with
being outside the building without being that fact.

WHY THIS LIVES IN PYTHON. The classification could be four lines of GDScript,
and then nothing could red-test it. `nav_gate.gd` reports what it measured --
each marker's position, snap and reachability -- and the scoping decision is
made here, where a test can put it wrong on purpose first.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nav_gate                      # noqa: E402


FOOTPRINT = [30.0, 22.0]             # bank_branch_a02: half-extents 15 x 11


def _row(name, type_, x, y, snap, reachable):
    return {"name": name, "type": type_, "x": x, "y": y,
            "snap": snap, "reachable": reachable}


def _markers(rows):
    """The shape `nav_gate.gd` emits: legacy totals over EVERY checked marker,
    plus the per-marker detail the scoping needs."""
    unreachable = [f"{r['name']} (snap {r['snap']:.1f}m)"
                   for r in rows if not r["reachable"]]
    return {"checked": len(rows),
            "reachable": sum(1 for r in rows if r["reachable"]),
            "unreachable": unreachable, "detail": rows}


# bank_branch_a02, as measured: objective in the vault, extraction 2 m past
# the south wall at y -13.0 against a half-depth of 11.0.
A02 = [_row("objective_A", "objective", -8.0, 5.0, 0.2, True),
       _row("extraction_STREET", "extraction", 4.0, -13.0, 2.6, False)]


# ---------------------------------------------------------------------------
# the falsifier
# ---------------------------------------------------------------------------

def test_an_exterior_extraction_does_not_make_a_building_unnavigable():
    """THE one that has to go red first. 99 shells report exactly this shape
    and every one of them currently reads as not navigable."""
    _, nav, why = nav_gate.scope_markers(_markers(A02), FOOTPRINT,
                                         stairs_ok=True)
    assert nav is True, why
    assert "extraction_STREET" in why or "1 deferred" in why


def test_an_interior_objective_that_is_unreachable_still_fails():
    """final_stand: the shell walked on 2026-08-07 with an objective nobody
    can reach. The correction must not launder it."""
    rows = [_row("objective_final_boss", "objective", 2.0, 3.0, 0.7, False)]
    _, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT,
                                         stairs_ok=True)
    assert nav is False
    assert "objective_final_boss" in why


def test_snap_distance_is_not_the_discriminator():
    """`cr_deli objective_SAFE` snaps 2.6 m and sits INSIDE the building;
    `gas_station extraction_FORECOURT` snaps 1.2 m and sits OUTSIDE it. A rule
    keyed on SNAP_MAX = 2.0 gets both backwards."""
    inside_far = [_row("objective_A", "objective", -8.0, 5.0, 0.2, True),
                  _row("objective_SAFE", "objective", 1.0, 2.0, 2.6, False)]
    scoped, nav, _ = nav_gate.scope_markers(_markers(inside_far), FOOTPRINT,
                                            stairs_ok=True)
    assert nav is False, "an interior defect at snap 2.6 must still be a defect"
    assert scoped["interior_unreachable"]
    assert not scoped["exterior_deferred"]

    outside_near = [_row("objective_A", "objective", -8.0, 5.0, 0.2, True),
                    _row("extraction_FORECOURT", "extraction", 0.0, -12.0,
                         1.2, False)]
    scoped, nav, _ = nav_gate.scope_markers(_markers(outside_near), FOOTPRINT,
                                            stairs_ok=True)
    assert nav is True, "an exterior marker at snap 1.2 is still exterior"
    assert len(scoped["exterior_deferred"]) == 1


# ---------------------------------------------------------------------------
# the deferral has to be a record, not a deletion
# ---------------------------------------------------------------------------

def test_the_deferral_is_recorded_and_says_who_owns_it():
    """Dropping a check silently is the failure this repo has paid for three
    times. A deferred marker must be named, and the manifest must say what is
    supposed to judge it."""
    scoped, _, _ = nav_gate.scope_markers(_markers(A02), FOOTPRINT,
                                          stairs_ok=True)
    deferred = scoped["exterior_deferred"]
    assert len(deferred) == 1
    assert deferred[0]["name"] == "extraction_STREET"
    assert deferred[0]["reachable"] is False
    assert "site" in scoped["scope_note"].lower()


def test_the_legacy_counts_are_untouched():
    """`library_census.py` and every .navgate.json on disk read
    checked/reachable/unreachable. Narrowing those in place would silently
    change what 135 existing files mean."""
    scoped, _, _ = nav_gate.scope_markers(_markers(A02), FOOTPRINT,
                                          stairs_ok=True)
    assert scoped["checked"] == 2
    assert scoped["reachable"] == 1
    assert scoped["unreachable"] == ["extraction_STREET (snap 2.6m)"]


def test_interior_counts_are_reported_separately():
    scoped, _, _ = nav_gate.scope_markers(_markers(A02), FOOTPRINT,
                                          stairs_ok=True)
    assert scoped["interior_checked"] == 1
    assert scoped["interior_reachable"] == 1
    assert scoped["interior_unreachable"] == []


# ---------------------------------------------------------------------------
# unjudged is not passing -- three different ways to have judged nothing
# ---------------------------------------------------------------------------

def test_a_building_whose_only_marker_is_exterior_is_unjudged():
    """Deferring every marker leaves nothing measured. That is null, and it is
    emphatically not True -- `parking_garage` is fit today for exactly this
    kind of emptiness."""
    rows = [_row("extraction_STREET", "extraction", 4.0, -13.0, 2.6, False)]
    _, nav, why = nav_gate.scope_markers(_markers(rows), FOOTPRINT,
                                         stairs_ok=True)
    assert nav is None
    assert "UNJUDGED" in why


def test_no_footprint_means_unscoped_rather_than_all_interior():
    """Without a footprint there is no inside. Defaulting to "all interior"
    would quietly restore the old verdict under the new name; defaulting to
    "all exterior" would pass everything. Neither is an answer."""
    scoped, nav, why = nav_gate.scope_markers(_markers(A02), [],
                                              stairs_ok=True)
    assert nav is None
    assert "UNSCOPED" in why
    assert "footprint" in why
    assert "interior_checked" not in scoped


def test_a_result_without_detail_rows_is_unscoped():
    """135 .navgate.json files predate the detail rows. They must report as
    unscoped, not be scored against an absent classification."""
    legacy = {"checked": 2, "reachable": 1,
              "unreachable": ["extraction_STREET (snap 2.6m)"]}
    scoped, nav, why = nav_gate.scope_markers(legacy, FOOTPRINT,
                                              stairs_ok=True)
    assert nav is None
    assert "UNSCOPED" in why
    assert scoped == legacy


def test_zero_markers_is_still_unjudged():
    _, nav, why = nav_gate.scope_markers(_markers([]), FOOTPRINT,
                                         stairs_ok=True)
    assert nav is None
    assert "UNJUDGED" in why


def test_nothing_checked_and_everything_deferred_read_differently():
    """Both are unjudged, and they are not the same fact. `warehouse` has no
    spawn marker so the gate checked nothing; `parking_garage` checks one and
    it stands on the street. The first manifest written by this split said
    "every checked marker is outside the building" about `warehouse`, which is
    a sentence about markers it never had."""
    _, _, none_checked = nav_gate.scope_markers(_markers([]), FOOTPRINT,
                                                stairs_ok=True)
    rows = [_row("extraction_STREET", "extraction", 4.0, -13.0, 2.6, False)]
    _, _, all_deferred = nav_gate.scope_markers(_markers(rows), FOOTPRINT,
                                                stairs_ok=True)
    assert none_checked != all_deferred
    assert "no marker was checked at all" in none_checked
    assert "outside the building" not in none_checked
    assert "outside the building" in all_deferred


# ---------------------------------------------------------------------------
# what must not have moved
# ---------------------------------------------------------------------------

def test_a_failed_stair_still_dominates():
    """Stairs are the thing the exit code gates on. A building that cannot be
    walked is not navigable however tidy its markers are."""
    _, nav, why = nav_gate.scope_markers(_markers(A02), FOOTPRINT,
                                         stairs_ok=False)
    assert nav is False
    assert "stair" in why


def test_the_boundary_is_inclusive_of_the_wall_line():
    """A marker exactly on the footprint edge is INSIDE. The building owns its
    own threshold; picking the other convention would defer doorway markers."""
    rows = [_row("objective_DOOR", "objective", 15.0, 0.0, 0.1, False)]
    scoped, nav, _ = nav_gate.scope_markers(_markers(rows), FOOTPRINT,
                                            stairs_ok=True)
    assert nav is False
    assert not scoped["exterior_deferred"]


# ---------------------------------------------------------------------------
# the wrapper says it out loud
# ---------------------------------------------------------------------------

def test_verdict_prints_the_interior_count_and_the_deferral():
    scoped, nav, why = nav_gate.scope_markers(_markers(A02), FOOTPRINT,
                                              stairs_ok=True)
    ok, lines = nav_gate.verdict({"exit_code": 0, "ok": True,
                                  "stairs_ok": True, "navigable": nav,
                                  "navigable_reason": why, "stairs": [],
                                  "markers": scoped})
    assert ok is True
    text = "\n".join(lines)
    assert "interior" in text
    assert "deferred to site" in text
    assert "extraction_STREET" in text


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
        except AssertionError as ex:                    # noqa: PERF203
            failed += 1
            print(f"[FAIL] {name}: {ex or 'assertion failed'}")
        except Exception as ex:                         # noqa: BLE001
            failed += 1
            print(f"[ERROR] {name}: {type(ex).__name__}: {ex}")
        else:
            print(f"[ok] {name}")
    print("all marker scope tests passed" if not failed
          else f"{failed} test(s) failed")
    raise SystemExit(1 if failed else 0)
