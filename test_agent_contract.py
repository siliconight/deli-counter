"""The contract's fallbacks are the contract's values.

`agent_contract.py` promises, in its own docstring, that "every consumer keeps
a hardcoded fallback equal to the ratified values, so a missing file degrades
gracefully instead of failing the pipeline". That promise was false for two
keys from the day the values changed until 2026-09-08.

WHY THAT IS WORSE THAN IT SOUNDS. The fallbacks only fire when the file is
missing, unreadable, or partial -- so the drift is invisible in every ordinary
run, and it was. But `nav_env()` turns whatever `contract()` returns into
DC_NAV_* environment variables for the GDScript gates, and `nav_gate.gd` reads
those with `_envf(name, fallback)`. A present environment variable beats the
fallback behind it. `nav_gate.gd`'s own numbers were corrected when the values
moved (`d7d1f70`); this module's were not; and this module's are the ones that
arrive as env vars. The one copy that was fixed gets overwritten by the copy
that was not.

The two that had drifted are exactly the two the contract's own derivation
notes record as refuted:

    agent_max_climb_m   0.5   -> 0.15   "Was 0.5" -- permitted a 0.49 m
                                        stringer; four walkers parked on it
    cell_size_m         0.15  -> 0.1    "Was 0.15" -- capped connected slope
                                        at 45 deg against a stated 55; eight
                                        path proofs failed as disjoint islands

So the graceful degradation was to a navmesh measured to disconnect.

    python -m pytest test_agent_contract.py -q
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract as AC


def _live():
    with open(os.path.join(HERE, "agent_contract.json"), encoding="utf-8") as f:
        return json.load(f)


def _pairs(defaults, live, path=""):
    """Every (dotted key, fallback, contract value) the two blocks share."""
    for key, fallback in defaults.items():
        if key not in live:
            continue
        here = f"{path}{key}"
        if isinstance(fallback, dict) and isinstance(live[key], dict):
            yield from _pairs(fallback, live[key], here + ".")
        else:
            yield here, fallback, live[key]


def test_every_fallback_equals_the_ratified_value():
    """THE GUARD. Not the two numbers -- the invariant, so the next value to
    move cannot rot the same way while both copies still look plausible."""
    drift = [(k, f, v) for k, f, v in _pairs(AC._DEFAULTS, _live()) if f != v]
    assert drift == [], "\n".join(
        f"  {k}: fallback {f!r}, contract {v!r}" for k, f, v in drift)


def test_the_shared_keys_are_actually_shared():
    """A guard that compares an empty intersection passes for free. Pin the
    count so deleting a section from either side fails loudly rather than
    quietly shrinking what is checked."""
    shared = list(_pairs(AC._DEFAULTS, _live()))
    assert len(shared) >= 20, [k for k, _, _ in shared]


def test_a_missing_contract_still_exports_the_ratified_bake(monkeypatch):
    """The path that made the drift dangerous, exercised directly: with no
    contract to read, what reaches the GDScript gates must still be the
    numbers the gates were tuned against."""
    monkeypatch.setenv("DC_AGENT_CONTRACT", os.path.join(HERE, "no_such.json"))
    monkeypatch.setattr(AC, "_cache", None)
    env = AC.nav_env({})
    live = _live()["nav_bake"]
    assert float(env["DC_NAV_CLIMB"]) == live["agent_max_climb_m"]
    assert float(env["DC_NAV_CELL"]) == live["cell_size_m"]
    assert float(env["DC_NAV_RADIUS"]) == live["agent_radius_m"]
    AC._cache = None
