"""A score's alarm hooks (0.289.0, the factory's roadmap 323).

The walker: score locations should carry "gameplay events ... part of what would trigger police coming or stuff like
that for the dispatch layer" -- data a game may use or ignore. Every slot of an alarmed fixture writes one `alarm`
marker: where it is, its event, whether the real alarm is audible. FAILS ON 0.288.0, which writes none.
"""
import json
import os

import score_alarms

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")
ROWS = score_alarms.ALARM_FIXTURES


def _built(name):
    slots = json.load(open(os.path.join(BUILD, name + ".slots.json"), encoding="utf-8"))["slots"]
    gp = json.load(open(os.path.join(BUILD, name + ".gameplay.json"), encoding="utf-8"))
    return slots, gp


def _row(slot):
    return next(((e, a, v) for k, v, e, a in ROWS if slot.get(k) == v), None)


def test_every_alarmed_fixture_in_a_bank_has_its_hook():
    for name in ("bank_branch_a02", "bank_job", "bank_tower_a01"):
        slots, gp = _built(name)
        alarms = {m["id"]: m for m in gp["markers"] if m["type"] == "alarm"}
        want = [s for s in slots if _row(s)]
        assert want and len(alarms) == len(want), (name, len(alarms), len(want))
        for s in want:
            event, audible, fixture = _row(s)
            m = alarms[s["slot_id"]]
            assert m["meta"] == {"event": event, "audible": audible, "fixture": fixture}, (name, m)
            assert [m["x"], m["y"], m["z"]] == [float(c) for c in s["transform"]["translation"]], (name, m)
    _slots, gp = _built("bank_branch_a02")
    events = [m["meta"]["event"] for m in gp["markers"] if m["type"] == "alarm"]
    assert "alarm.panic_button" in events and "alarm.vault_door" in events
    assert events.count("alarm.deposit_drilled") == 7


def test_a_hook_sits_in_its_room():
    _slots, gp = _built("bank_branch_a02")
    by = {m["meta"]["event"]: m for m in gp["markers"] if m["type"] == "alarm"}
    assert by["alarm.deposit_drilled"]["room"] in ("vault", "vault_west", "vault_east")
    assert by["alarm.panic_button"]["room"] is not None


def test_the_vocabulary_is_data_and_nothing_more():
    """Each row is (key, value, event, audible): no heat, timer or response -- those are the game's."""
    for key, value, event, audible in ROWS:
        assert key in ("role", "species") and isinstance(value, str)
        assert event.startswith(("alarm.", "score.")) and isinstance(audible, bool)
    assert len({r[2] for r in ROWS}) == len(ROWS)
