"""A score's alarm hooks: what fixture carries which gameplay event (Deli Counter 0.289.0, the factory's roadmap 323).

Pure, so the tests read it without Blender; `deli_counter._Builder._score_alarms` writes one `alarm` marker per slot a
row names.
"""

#: A SCORE'S ALARM HOOKS (0.289.0, the factory's roadmap 323). The walker: "in the 'score' location there should
#: be gameplay events or something that doesn't mean much for level factory but is part of what would trigger
#: police coming or stuff like that for the dispatch layer", and "they could mean nothing, but they could also be
#: ingested/used by the gameplay layer". So a hook is DATA, not behaviour: where the fixture is, an event name, and
#: one plain fact about the real object -- whether its alarm is audible. No heat, no timers, no response: those are
#: the game's. Keyed on what the generator placed, so every fixture of a kind carries its hook, in any building:
#: (key, value, event, audible) -- key is the slot's `role` or its `species`. A teller's holdup button is silent;
#: a vault door's contact alarm sounds; an ATM's tamper alarm sounds. `score.cash_moved` is an event, not an alarm.
ALARM_FIXTURES = (
    ("species", "teller_line", "alarm.panic_button", False),
    ("role", "vault_door", "alarm.vault_door", True),
    ("role", "safe_deposit_boxes", "alarm.deposit_drilled", False),
    ("species", "drop_safe", "alarm.safe_opened", False),
    ("species", "atm", "alarm.atm_tampered", True),
    ("species", "cash_cart", "score.cash_moved", False),
)
