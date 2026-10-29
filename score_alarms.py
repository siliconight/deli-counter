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


#: WHERE A DRILL STANDS (0.291.0, the factory's roadmap 323). The walker: "opening the safe should be a gameplay event
#: where you have to stand in an area for a certain amount of time close to the 'drill' and then the door opens". A
#: drill zone is DATA like a hook: where the crew stands to drill, sent as a body enters it and as it leaves (Dispatch
#: 0.8.0's two-rule `fires`), naming the interactive it opens (`target`). How long the drill takes, whether it pauses
#: or jams, and what it sets off are the game's. (key, value) -- the slot's `role`: a vault door, whose interactive
#: goes locked -> unlocked -> open, and a deposit unit, whose goes intact -> drilled.
DRILL_FIXTURES = (
    ("role", "vault_door"),
    ("role", "safe_deposit_boxes"),
)


def drill_zone(slot, body_radius):
    """``(x, y, z, radius)`` of the drill zone in front of ``slot``, or None when it has no interactive to open.

    A slot's `rot_y` is a compass bearing that turns its local +y onto world (sin t, cos t) (`vault_room`'s WORLD), and
    a vault door's +y looks out of the vault toward its approach (its `face`), as a deposit unit's looks out of its
    wall. The zone stands there: its centre half the slot's depth plus a body's radius out from the face, its radius
    half the opening's width plus a body's radius, so a body anywhere across the face is in it. Plan metres, the
    builder's Z-up frame; ``z`` is the slot's, as an alarm's is."""
    import math
    iv = slot.get("interactive") or {}
    if not iv.get("id"):
        return None
    x, y, z = (float(v) for v in slot["transform"]["translation"])
    t = math.radians(float(slot["transform"].get("rot_y", 0.0) or 0.0))
    fit = slot.get("fit") or {}
    dims = fit.get("dims") or [0.0, 0.0, 0.0]
    openings = fit.get("openings") or []
    width = float(openings[0].get("width") or dims[0]) if openings else float(dims[0])
    out = float(dims[1]) / 2.0 + float(body_radius)
    return (x + math.sin(t) * out, y + math.cos(t) * out, z, width / 2.0 + float(body_radius))
