"""A generator never draws a stair flight narrower than a corridor (0.190.0).

Measured 2026-10-06, roadmap 189 at the factory root: twin_a01's 0.9 m
flights traversed at 7 of 8 voxel-grid origins under the nav gate's sweep, and
1.2 m flights at 8 of 8. Moving the furniture nearest the tear changed
nothing; widening the flight did. `presets.STAIR_FLIGHT_WIDTH` is the
contract's corridor minimum and one bake cell, and the two generators that
drew 0.9 m flights draw it now.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract                # noqa: E402
import presets                       # noqa: E402


def _contract():
    return agent_contract.contract()


def test_the_flight_width_is_derived_from_the_contract():
    c = _contract()
    want = (c["clearances"]["min_corridor_width_m"]
            + c["nav_bake"]["cell_size_m"])
    assert abs(presets.STAIR_FLIGHT_WIDTH - want) < 1e-9


def test_no_preset_draws_a_flight_narrower_than_a_corridor():
    floor = float(_contract()["clearances"]["min_corridor_width_m"])
    narrow = []
    for name in sorted(presets.REGISTRY):
        with contextlib.redirect_stdout(io.StringIO()):
            d = presets.make(name)
        for st in d.get("stairs") or []:
            w = st.get("width")
            if w is not None and float(w) < floor:   # None: the builder's 1.6
                narrow.append((name, w))
    assert not narrow, narrow


def test_twin_a01_stands_on_the_measured_width():
    with open(os.path.join(HERE, "specs", "twin_a01.json"), encoding="utf-8") as f:
        spec = json.load(f)
    assert [st["width"] for st in spec["stairs"]] == [presets.STAIR_FLIGHT_WIDTH] * 2
