"""A check that reads the nav gate's output runs after the nav gate (0.175.1).

`test_navgate_population.py` compares `build/*.navgate.json` against
`navgate_baseline.json`, and `nav_gate.py --all` is what writes those files.
`check.py` used to run every test in one sweep BEFORE the nav gate, so a
shell built for the commit being checked had no `.navgate.json` yet and was
never compared: a new unjudged shell always passed on the commit that added
it. Measured 2026-10-04: 0.174.0 added six rowhome Empties and committed
clean; 0.175.0's hook then refused for them, because their nav results had
first been written during that hook.

These drive `check.main` with `run` recorded instead of executed, so they
need neither Godot nor a build.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check  # noqa: E402

POPULATION = "test_navgate_population.py"


@pytest.fixture
def calls(monkeypatch):
    got = []
    monkeypatch.setattr(check, "run", lambda args: got.append(list(args)) or 0)
    with pytest.raises(SystemExit):
        check.main()
    return got


def _runs_it(args, name):
    """True when `args` runs the test file `name` (not merely ignores it)."""
    return name in args


def test_the_population_check_runs_after_the_nav_gate(calls):
    nav = next(i for i, a in enumerate(calls) if a and a[0] == "nav_gate.py")
    pop = [i for i, a in enumerate(calls) if _runs_it(a, POPULATION)]
    assert pop and all(i > nav for i in pop), calls


def test_the_first_sweep_leaves_it_out_and_it_runs_once(calls):
    sweep = calls[0]
    assert sweep[:2] == ["-m", "pytest"]
    assert "--ignore=" + POPULATION in sweep
    assert sum(1 for a in calls if _runs_it(a, POPULATION)) == 1


def test_every_test_held_back_exists():
    """A renamed file would fall back into the first sweep without a word, and
    the step after the nav gate would then ask pytest for a file that is not
    there. Name each one that is held back, and keep it real."""
    assert check.AFTER_NAV_GATE
    for f in check.AFTER_NAV_GATE:
        assert os.path.exists(os.path.join(HERE, f)), f
