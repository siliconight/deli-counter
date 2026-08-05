"""A gate that grades stale artefacts reports confidently about the past.

The case this exists for, measured 2026-08-05: `nav_gate.py --all` ran for
the first time against 103 built shells and called 10 stairs unwalkable and
19 objectives unreachable. All fossils. `build/mansion_a01.glb` was built
2026-07-21; `stairwell.ramp_foot_extension`, which fixes precisely that
failure, was written 2026-07-29. A rebuild of that one shell flipped both
stairs to ok and the objective to reachable with the bake parameters
untouched.

Nothing was wrong with the code. The gate was grading a two-week-old build
and nobody could tell, because `check.py` never asked how old build/ was.

Run:  python -m pytest test_build_freshness.py
"""
import os
import time

import build_freshness as bf


def _mk(tmp_path, sources, shells, gameplay_for=None):
    """Build a fake tree: sources at t=1000, shells at their given times."""
    (tmp_path / "build").mkdir()
    for name, mtime in sources.items():
        p = tmp_path / name
        p.write_text("x")
        os.utime(p, (mtime, mtime))
    gameplay_for = shells if gameplay_for is None else gameplay_for
    for name, mtime in shells.items():
        p = tmp_path / "build" / (name + ".glb")
        p.write_text("x")
        os.utime(p, (mtime, mtime))
        if name in gameplay_for:
            (tmp_path / "build" / (name + ".gameplay.json")).write_text("{}")
    return str(tmp_path)


# --- the failure this was written for ----------------------------------

def test_a_shell_older_than_the_builder_is_stale(tmp_path):
    """mansion_a01, in miniature: shell built before the fix that repairs it."""
    here = _mk(tmp_path,
               {"deli_counter.py": 1000, "stairwell.py": 5000},
               {"mansion_a01": 2000})
    stale = bf.stale_shells(here, ("deli_counter.py", "stairwell.py"))
    assert len(stale) == 1
    assert stale[0][0].endswith("mansion_a01.glb")
    assert stale[0][3] == "stairwell.py"     # names WHICH source moved


def test_a_shell_newer_than_every_source_is_fresh(tmp_path):
    here = _mk(tmp_path,
               {"deli_counter.py": 1000, "stairwell.py": 5000},
               {"mansion_a01": 9000})
    assert bf.stale_shells(here, ("deli_counter.py", "stairwell.py")) == []


def test_the_newest_source_wins_not_the_first(tmp_path):
    """A shell newer than the builder but older than stairwell.py is still
    stale. Comparing against only one source is how this hid for two weeks --
    deli_counter.py had not changed, stairwell.py had."""
    here = _mk(tmp_path,
               {"deli_counter.py": 1000, "stairwell.py": 5000},
               {"mansion_a01": 3000})
    stale = bf.stale_shells(here, ("deli_counter.py", "stairwell.py"))
    assert len(stale) == 1
    assert stale[0][3] == "stairwell.py"


# --- scope --------------------------------------------------------------

def test_a_glb_with_no_gameplay_json_is_ignored(tmp_path):
    """nav_gate --all only reads shells that have a gameplay.json beside
    them. Reporting anything else as stale would be noise about a file no
    gate consumes."""
    here = _mk(tmp_path, {"deli_counter.py": 5000},
               {"mansion_a01": 1000, "scratch_export": 1000},
               gameplay_for={"mansion_a01"})
    stale = bf.stale_shells(here, ("deli_counter.py",))
    assert len(stale) == 1
    assert stale[0][0].endswith("mansion_a01.glb")


def test_a_missing_source_is_not_an_error(tmp_path):
    """The source list names optional modules. One being absent must not
    crash the gate or silently disable it."""
    here = _mk(tmp_path, {"deli_counter.py": 5000}, {"a": 1000})
    stale = bf.stale_shells(here, ("deli_counter.py", "does_not_exist.py"))
    assert len(stale) == 1


def test_no_sources_at_all_reports_nothing_rather_than_everything(tmp_path):
    """If the comparison basis is missing, the honest answer is 'cannot
    tell', not 'all stale' -- a gate that cries wolf gets switched off."""
    here = _mk(tmp_path, {}, {"a": 1000})
    assert bf.stale_shells(here, ("nothing.py",)) == []


def test_results_are_ordered_oldest_first(tmp_path):
    """The worst offender is the useful one to name in a one-line summary."""
    here = _mk(tmp_path, {"deli_counter.py": 9000},
               {"newer": 5000, "oldest": 1000, "middle": 3000})
    stale = bf.stale_shells(here, ("deli_counter.py",))
    assert [os.path.basename(s[0]) for s in stale] == [
        "oldest.glb", "middle.glb", "newer.glb"]


# --- the exit contract --------------------------------------------------

def test_source_stamp_names_the_newest_file(tmp_path):
    here = _mk(tmp_path, {"a.py": 1000, "b.py": 7000, "c.py": 3000}, {})
    newest, who = bf.source_stamp(here, ("a.py", "b.py", "c.py"))
    assert who == "b.py"
    assert newest == 7000


def test_stairwell_is_in_the_watched_list():
    """The two-week drift was stairwell.py specifically. If someone trims
    this list, that omission should be deliberate and visible."""
    assert "stairwell.py" in bf.GEOMETRY_SOURCES
    assert "deli_counter.py" in bf.GEOMETRY_SOURCES
    assert "build.py" in bf.GEOMETRY_SOURCES


def test_gates_that_only_read_shells_are_not_watched():
    """nav_gate/zfight_gate/circulation re-run against whatever is present;
    editing them does not make a shell stale. Listing them would demand a
    full rebuild every time a checker changed, which trains people to ignore
    the gate."""
    for tool in ("nav_gate.py", "zfight_gate.py", "circulation.py",
                 "check.py", "layout_lint.py"):
        assert tool not in bf.GEOMETRY_SOURCES, tool
