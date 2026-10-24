"""The enemy's body is the NPC's, and the NPC's is the player's until it says
otherwise (0.253.0, the factory's roadmap 292).

`characters.npc_standard` said "cops/civilians share player metrics until a
distinct class ships" and restated the player's radius and height beside it,
which nothing read; `sightlines.enemy_sight_height_m` said the enemy's eye a
second time, and nothing said which governed. Level Factory's seam wrote the
player's body into every Laser Tag run and left the enemy's eye at Laser Tag's
1.6, so a studio stating a 2.05 m character fielded enemies of its size
sighting from 1.6 m.

Now the bodies decide: `npc_body()` is the NPC block's stated metrics over the
player's, `sight_heights()` reads both eyes from the bodies and checks the
`sightlines` copies against them, and no copy is merged into a contract that
leaves it out -- so a studio states its body once.

THE TEST THAT MATTERS IS `test_a_studio_states_its_body_once_and_the_crossing_follows_it`.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agent_contract as AC  # noqa: E402

#: A 2.05 m character: the eye at 0.9 of stature, the chest inside the capsule.
TALL = {"radius_m": 0.45, "height_m": 2.05, "eye_height_m": 1.85,
        "chest_height_m": 1.15}


def _load(tmp_path, monkeypatch, body):
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    monkeypatch.setenv("DC_AGENT_CONTRACT", str(path))
    monkeypatch.setattr(AC, "_cache", None)


def test_a_studio_states_its_body_once_and_the_crossing_follows_it(
        tmp_path, monkeypatch):
    """THE POINT OF THE ITEM. A contract stating a 2.05 m player and nothing
    else: both sides sight from its 1.85 m eye, the lines cross at 1.5 m, and
    shelter stands at 1.85 m. Until 0.253.0 the module merged its own copies
    of the sight heights and the aim point into a contract that left them
    out, and refused this body for disagreeing with the 1.0 m aim it had not
    stated."""
    _load(tmp_path, monkeypatch, {"characters": {"player": TALL}})
    assert AC.cover_break_height() == pytest.approx((1.85 + 1.15) / 2.0)
    assert AC.shelter_height() == pytest.approx(1.85)
    assert AC.sight_heights() == (1.85, 1.85)


def test_the_npc_is_the_player_until_it_says_otherwise(tmp_path, monkeypatch):
    _load(tmp_path, monkeypatch, {"characters": {
        "player": TALL, "npc_standard": {"note": "shares"}}})
    npc = AC.npc_body()
    assert {k: npc[k] for k in TALL} == TALL
    _load(tmp_path, monkeypatch, {"characters": {
        "player": TALL, "npc_standard": {"eye_height_m": 1.7}}})
    npc = AC.npc_body()
    assert npc["eye_height_m"] == 1.7
    assert npc["height_m"] == 2.05
    assert AC.sight_heights() == (1.85, 1.7)


def test_a_sight_height_that_disagrees_with_its_body_is_refused(
        tmp_path, monkeypatch):
    """The failure this replaces is a second statement of one number that
    nothing held to the first."""
    _load(tmp_path, monkeypatch, {
        "characters": {"player": {"radius_m": 0.35, "height_m": 1.8,
                                  "eye_height_m": 1.6,
                                  "chest_height_m": 1.0}},
        "sightlines": {"crew_sight_height_m": 1.6,
                       "enemy_sight_height_m": 1.5, "aim_height_m": 1.0}})
    with pytest.raises(ValueError, match="one body, one eye"):
        AC.sight_heights()
    with pytest.raises(ValueError, match="one body, one eye"):
        AC.cover_break_height()


def test_the_shipped_npc_states_no_metric_of_its_own():
    """The contract as it stands: the enemy is the player, and the shipped
    copies agree with the bodies."""
    npc = AC.contract()["characters"]["npc_standard"]
    assert not [k for k, v in npc.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)]
    s = AC.contract()["sightlines"]
    assert AC.sight_heights() == (s["crew_sight_height_m"],
                                  s["enemy_sight_height_m"])
