"""The body-sized numbers the census found spelt as literals read the agent contract (0.216.0).

The walker, 2026-10-13: "continue to update the agent contract file so we can make singular changes when we know
the size of characters in the game". The factory's census of this repo's module-level numbers
(`docs/findings/agent_contract_follows/literal_census.py`) flagged 127 of 317; read one by one, eleven were a
body's size written down with the rule beside it -- a capsule's width, a body's height and eye, the step a
controller lifts, two agents abreast, the floor in front of a door, the door minimum, a bake radius's gap.
Each now reads the contract through `agent_contract.py`, at the value it was. And `combat_audit` kept its own
copy of the builder's opening defaults, two of them stale: a width-less door at 1.2 (the builder: the contract's
1.25 since 0.214.0) and a width-less vault at 1.4 (the builder: 1.3 x 2.1). It reads the builder's now.

Runs without Blender. On 0.215.0 `agent_contract.body_height` does not exist and this fails to import.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract        # noqa: E402
from agent_contract import (body_eye_height, body_height, body_radius, door_approach,   # noqa: E402
                            max_step_up, min_door_width, nav_radius)
import combat_audit          # noqa: E402
import enterability          # noqa: E402
import guards                # noqa: E402
import ladder_geom           # noqa: E402
import layout_lint           # noqa: E402
import level_design          # noqa: E402
import lights                # noqa: E402
import sightlines            # noqa: E402
import stairwell             # noqa: E402
import vault_room            # noqa: E402
from spec_types import Opening   # noqa: E402


def test_the_accessors_read_the_contract_s_fields():
    c = agent_contract.contract()
    player = c["characters"]["player"]
    assert body_height() == float(player["height_m"])
    assert body_eye_height() == float(player["eye_height_m"])
    assert max_step_up() == float(player["max_step_up_m"])
    assert nav_radius() == float(c["nav_bake"]["agent_radius_m"])
    assert door_approach() == 2.0 * body_radius() + 0.3


def test_each_routed_number_is_its_rule_of_the_contract():
    assert enterability.MIN_PASS_WIDTH == stairwell._AGENT_PASS_WIDTH == 2.0 * body_radius()
    assert enterability.STAND_HEIGHT == body_height()
    assert sightlines.EYE == sightlines.SIGHT_BLOCK_H == body_eye_height()
    assert vault_room.DOOR_WIDTH == lights._AISLE_MIN_FALLBACK == min_door_width()
    assert vault_room.APPROACH == layout_lint.DOOR_APPROACH_M == door_approach()
    assert guards.MAX_STEP_UP == max_step_up()
    assert combat_audit.WIDE_DOOR == 4.0 * body_radius()
    assert level_design._CLUSTER_GAP[1] == 2.0 * nav_radius()
    assert ladder_geom.HOLE_ALONG == round(ladder_geom.CLIMB_STANDOFF + body_radius()
                                           + ladder_geom.HOLE_ALONG_MARGIN, 3)


def test_today_s_numbers_are_the_ones_that_were_spelt():
    """No built thing moves: at the ratified contract every rule gives the literal it replaced."""
    assert (enterability.MIN_PASS_WIDTH, stairwell._AGENT_PASS_WIDTH, enterability.STAND_HEIGHT) == (0.7, 0.7, 1.8)
    assert (sightlines.EYE, sightlines.SIGHT_BLOCK_H, guards.MAX_STEP_UP) == (1.6, 1.6, 0.5)
    assert (vault_room.DOOR_WIDTH, vault_room.APPROACH, lights._AISLE_MIN_FALLBACK) == (1.25, 1.0, 1.25)
    assert (combat_audit.WIDE_DOOR, level_design._CLUSTER_GAP, ladder_geom.HOLE_ALONG) == (1.4, (0.3, 0.8), 1.3)


def test_combat_audit_reads_an_opening_at_the_width_it_is_built():
    """FAILS ON 0.215.0: a width-less door read 1.2 and a width-less vault 1.4 there."""
    for kind in ("door", "window", "garage", "breach", "vault", "teller", "safe_deposit"):
        op = Opening(kind=kind, pos=0.0)
        assert combat_audit._op_width(op) == op.resolved()["width"], kind
    assert combat_audit._op_width(Opening(kind="door", pos=0.0, width=1.6)) == 1.6
