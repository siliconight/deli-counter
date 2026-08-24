"""The unjudged set is frozen. A NEW shell falling into it must fail.

WHAT THIS CATCHES: nav_gate reports `markers: 0 checked -- reachability
UNJUDGED` for a shell with no marker whose type ends in `_spawn`. That is a
report, not a gate -- the exit code is deliberately unchanged (see nav_gate.gd
and nav_gate.py, both of which say so at length). So the unjudged count can grow
without anything failing, and it has: what a session recorded as 18 measured as
17 with five names the note never mentioned.

The per-shell results live in deli_counter/build/, which is not committed. When
build/ is absent these tests SKIP rather than pass, and the baseline's own
integrity is checked instead, so a clean checkout never reports a green sweep of
nothing.
"""
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE_PATH = os.path.join(HERE, "navgate_baseline.json")
BUILD = os.path.join(HERE, "build")

with open(BASELINE_PATH, "r", encoding="utf-8") as _fh:
    BASELINE = json.load(_fh)

UNJUDGED = {e["shell"]: e for e in BASELINE["unjudged"]}
STAIR_FAILURES = {e["shell"]: e for e in BASELINE["stair_failures"]}


def _live():
    if not os.path.isdir(BUILD):
        return None
    out = {}
    for fn in sorted(os.listdir(BUILD)):
        if not fn.endswith(".navgate.json"):
            continue
        # lf_* shells are Level Factory pipeline transients built into this
        # library's build/ as side inputs -- not Deli Counter's authored
        # library, and not this baseline's to freeze. layout_lint.main()
        # made the same call for specs/lf_*.json, and the alternative was
        # measured 2026-08-24: every LF probe mission that rebuilds becomes
        # a fresh "newly unjudged shell" here (lf_unlit_probe_001_5017
        # red-flagged the 0.100.0 adoption for standing in a gate that was
        # never judging it on purpose, joining nine lf_ entries already
        # baselined one-by-one). LF grades its own missions with its own
        # gates; this baseline freezes the authored library only.
        if fn.startswith("lf_"):
            continue
        try:
            with open(os.path.join(BUILD, fn), "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        if isinstance(d, dict):
            out[fn[: -len(".navgate.json")]] = d
    return out or None


def _unjudged(live):
    return {n for n, d in live.items()
            if ((d.get("markers") or {}).get("checked", 0) or 0) == 0}


def _failed(live):
    return {n for n, d in live.items()
            if d.get("stairs_ok", d.get("ok")) is False}


# ---------------------------------------------------------------- baseline
def test_baseline_is_internally_consistent():
    assert BASELINE["counts"]["unjudged"] == len(BASELINE["unjudged"])
    assert BASELINE["counts"]["stair_failures"] == len(BASELINE["stair_failures"])
    names = [e["shell"] for e in BASELINE["unjudged"]]
    assert len(names) == len(set(names)), "duplicate shell in the unjudged list"
    for e in BASELINE["unjudged"] + BASELINE["stair_failures"]:
        assert e.get("reason"), "%s has no reason" % e["shell"]
        assert len(e["reason"]) > 30, "%s reason is too thin" % e["shell"]


def test_baseline_is_not_empty():
    assert BASELINE["counts"]["shells"] >= 100
    assert BASELINE["counts"]["unjudged"] > 0, (
        "an empty unjudged baseline would make every comparison below vacuous")


# ------------------------------------------------------------------- sweep
def test_no_new_unjudged_shell():
    live = _live()
    if live is None:
        pytest.skip("deli_counter/build is absent; nothing to compare against")
    added = sorted(_unjudged(live) - set(UNJUDGED))
    assert not added, (
        "these shells are newly UNJUDGED and are not in the baseline: %s. "
        "Either give each a marker whose type ends in _spawn, or add it to "
        "navgate_baseline.json with a reason." % ", ".join(added))


def test_no_new_stair_failure():
    live = _live()
    if live is None:
        pytest.skip("deli_counter/build is absent; nothing to compare against")
    added = sorted(_failed(live) - set(STAIR_FAILURES))
    assert not added, (
        "these shells newly fail the stair gate: %s" % ", ".join(added))


def test_baseline_has_not_gone_stale():
    """A shell that got fixed must leave the baseline, or it hides the next one."""
    live = _live()
    if live is None:
        pytest.skip("deli_counter/build is absent")
    now = _unjudged(live)
    fixed = sorted(n for n in UNJUDGED if n in live and n not in now)
    assert not fixed, (
        "these are in the unjudged baseline but now check markers: %s. "
        "Remove them from navgate_baseline.json -- a stale entry hides a "
        "future regression." % ", ".join(fixed))


def test_the_sweep_actually_read_shells():
    live = _live()
    if live is None:
        pytest.skip("deli_counter/build is absent")
    assert len(live) >= 100, "only %d shell result(s) read" % len(live)
