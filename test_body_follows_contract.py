"""The stair landing and the vault's opening follow the agent contract (0.215.0).

The walker, 2026-10-13: "continue to update the agent contract file so we can make singular changes when we know
the size of characters in the game". 0.214.0 named the body-sized numbers that did not follow yet:
`stairwell.LANDING_DEPTH` (a literal 1.2) and the vault's 1.3 x 2.1 m opening (`vault_room.APERTURE` and
`spec_types`' vault default, literals beside a comment giving the rule). Each is now one function of the contract
in `agent_contract.py`, read where it was spelt, and its derivation is written into the contract. These hold that:
the functions against a stand-in contract with other numbers, the module-level copies against the contract in
force, the vault's rounding at the float that would round it wrong, the built vault slots, and the contract's text.

Runs without Blender. On 0.214.0 `agent_contract.stair_flight_width` does not exist and this fails to import.
"""
import glob
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract        # noqa: E402
import presets               # noqa: E402
import stairwell             # noqa: E402
import vault_room            # noqa: E402
from agent_contract import stair_flight_width, vault_aperture   # noqa: E402
from spec_types import Opening   # noqa: E402


def _stand_in(monkeypatch, **clearances):
    """The contract in force with `clearances` and `cell_size_m` replaced, as `contract()` returns it."""
    c = {k: dict(v) for k, v in agent_contract.contract().items()}
    cell = clearances.pop("cell_size_m", None)
    if cell is not None:
        c["nav_bake"]["cell_size_m"] = cell
    c["clearances"].update(clearances)
    monkeypatch.setattr(agent_contract, "_cache", c)


def test_today_s_numbers_are_the_ones_that_were_spelt():
    """No built thing moves: the functions give the literals they replace."""
    assert stair_flight_width() == 1.2
    assert vault_aperture() == {"width": 1.3, "height": 2.1, "sill": 0.0}


def test_the_module_copies_are_the_contract_s():
    assert stairwell.LANDING_DEPTH == presets.STAIR_FLIGHT_WIDTH == stair_flight_width()
    assert vault_room.APERTURE == vault_aperture()
    resolved = Opening(kind="vault", pos=0.0).resolved()
    assert {k: resolved[k] for k in ("width", "height", "sill")} == vault_aperture()


def test_the_flight_and_landing_follow_the_corridor_and_the_cell(monkeypatch):
    _stand_in(monkeypatch, min_corridor_width_m=1.3, cell_size_m=0.1)
    assert stair_flight_width() == 1.4
    _stand_in(monkeypatch, min_corridor_width_m=1.1, cell_size_m=0.05)
    assert stair_flight_width() == 1.15


@pytest.mark.parametrize("door, headroom, want", [
    (1.25, 2.0, (1.3, 2.1)),
    (1.3, 2.0, (1.3, 2.1)),     # a door already on the 0.1 grid is not rounded past it
    (1.31, 2.0, (1.4, 2.1)),
    (1.2, 2.2, (1.2, 2.3)),
])
def test_the_vault_opening_follows_the_door_and_the_headroom(monkeypatch, door, headroom, want):
    _stand_in(monkeypatch, min_door_width_m=door, min_headroom_m=headroom)
    got = vault_aperture()
    assert (got["width"], got["height"], got["sill"]) == want + (0.0,)
    resolved = Opening(kind="vault", pos=0.0).resolved()
    assert (resolved["width"], resolved["height"]) == want, "spec_types reads the contract when it resolves"


def test_every_built_vault_slot_carries_the_contract_s_opening():
    """What Zoo builds the round door to: the slot's `fit.openings`. Skips where nothing is built."""
    found = 0
    for p in sorted(glob.glob(os.path.join(HERE, "build", "*.slots.json"))):
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        if "vault_door" not in text:
            continue
        data = json.loads(text)
        for s in (data.get("slots", data) if isinstance(data, dict) else data):
            if s.get("role") != "vault_door":
                continue
            ops = (s.get("fit") or {}).get("openings") or []
            assert ops and {k: ops[0][k] for k in ("width", "height", "sill")} == vault_aperture(), (p, ops)
            found += 1
    if not found:
        pytest.skip("no built vault door slot to read")


def test_the_contract_writes_both_derivations_down():
    clear = agent_contract.contract()["clearances"]
    assert "1011.6" in clear["stair_landing_derivation"]
    assert "stairwell.LANDING_DEPTH" in clear["stair_landing_derivation"]
    assert "vault_room.APERTURE" in clear["vault_aperture_derivation"]
    assert "fit.openings" in clear["vault_aperture_derivation"]
    assert "NOT YET FOLLOWING" not in clear["re_derive_when"]
    assert "WRITTEN, NOT FOLLOWING" in clear["re_derive_when"]
