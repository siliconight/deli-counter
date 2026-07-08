"""interactives.py -- derive interactive-fixture state machines (pure, no bpy).

Doors, breachable walls, and breakable windows are the fixtures whose state all
players must agree on in an online game. This module turns an authored opening
into a replicable STATE MACHINE ``(id, states[], default, transitions[])`` --
the entire networked surface. It describes STATE, never synchronization, so it
stays network-solution agnostic: the same machine maps onto a server snapshot,
event/RPC, deterministic lockstep, or rollback without committing to any.

Two views come out of one machine:

- ``slot_interactive()`` -- the art-facing subset written into the
  ``<name>.slots.json`` slot's ``interactive`` block. Zoo reads it to build a
  per-state art variant (``_<state>`` naming law). ``state_geometry`` maps a
  state to the Zoo module species that backs it, which makes a breachable wall
  the ``breached`` STATE of a wall slot (``intact`` -> wall geometry,
  ``breached`` -> breach geometry) rather than a standalone module.
- ``gameplay_interactive()`` -- the netcode-facing entry written into the
  ``<name>.gameplay.json`` ``interactives`` array (id, slot_ref, transform,
  states, default, transitions). The game spawns one replicated node per id and
  drives which art variant renders.

Ownership: Deli Counter assigns the stable id and emits both blocks; Zoo builds
the art; the game owns replication. See docs/INTERACTIVES.md (the contract,
shared with the zoo repo).
"""
from __future__ import annotations

import hashlib

INTERACTIVE_CONTRACT_VERSION = "1.0.0"

# Inferred defaults per FIXTURE kind. `state_geometry` maps a state to the Zoo
# module species that backs it; omit it and the non-default state is identical
# art today, so Zoo defers it and the resolver falls back to the base module
# (progressive art pass). `collision_per_state` / `reversible` are ADVISORY --
# descriptions the game may honor or ignore, never instructions to the netcode.
_DEFAULTS = {
    "door": {
        "kind": "door",
        "states": ["closed", "open"],
        "default": "closed",
        "transitions": [
            {"event": "toggle", "from": "closed", "to": "open"},
            {"event": "toggle", "from": "open", "to": "closed"},
        ],
        "reversible": True,
        "collision_per_state": {"closed": True, "open": False},
    },
    "breach_wall": {
        "kind": "breach_wall",
        "states": ["intact", "breached"],
        "default": "intact",
        "state_geometry": {"intact": "wall", "breached": "breach"},
        "transitions": [
            {"event": "breach", "from": "intact", "to": "breached"},
        ],
        "reversible": False,
        "collision_per_state": {"intact": True, "breached": False},
    },
    "window": {
        "kind": "window",
        "states": ["intact", "broken"],
        "default": "intact",
        "transitions": [
            {"event": "break", "from": "intact", "to": "broken"},
        ],
        "reversible": False,
        "collision_per_state": {"intact": True, "broken": True},
    },
    "vault_door": {
        # a heist hero portal. The closed states (locked/unlocked) are a solid
        # armored door; open is a passage; breached is blown. state_geometry
        # maps each state to the Zoo module that backs it: the closed door has
        # its own species, open reuses `doorway`, breached reuses `breach`
        # (so a vault door is a doorway/breach at its other states, same as a
        # breachable wall is a wall's breached state). unlocked == locked art
        # today, so Zoo defers it to the base until the art pass adds a handle.
        "kind": "vault_door",
        "states": ["locked", "unlocked", "open", "breached"],
        "default": "locked",
        "state_geometry": {"locked": "vault_door", "unlocked": "vault_door",
                           "open": "doorway", "breached": "breach"},
        "transitions": [
            {"event": "unlock", "from": "locked", "to": "unlocked"},
            {"event": "lock", "from": "unlocked", "to": "locked"},
            {"event": "open", "from": "unlocked", "to": "open"},
            {"event": "close", "from": "open", "to": "unlocked"},
            {"event": "breach", "from": "locked", "to": "breached"},
            {"event": "breach", "from": "unlocked", "to": "breached"},
        ],
        "reversible": False,   # the lock/open cycle reverses; a breach doesn't
        "collision_per_state": {"locked": True, "unlocked": True,
                                "open": False, "breached": False},
    },
    "teller_window": {
        # a bank teller line: a solid counter + bulletproof glass. Intact blocks;
        # shattered is passable. Shattered reuses the same teller_line art today
        # (no state_geometry), so Zoo defers it to the base until a
        # shattered-glass art pass. Terminal once shattered.
        "kind": "teller_window",
        "states": ["intact", "shattered"],
        "default": "intact",
        "transitions": [
            {"event": "shatter", "from": "intact", "to": "shattered"},
        ],
        "reversible": False,
        "collision_per_state": {"intact": True, "shattered": False},
    },
    "safe_deposit_boxes": {
        # a vault-room wall of deposit boxes. Intact is a solid wall; drilled is
        # the robbed/opened state (reuses the same art today -> deferred). The
        # wall stays solid in both states (you don't walk through it); per-box
        # loot is gameplay's granularity, not the wall's art state.
        "kind": "safe_deposit_boxes",
        "states": ["intact", "drilled"],
        "default": "intact",
        "transitions": [
            {"event": "drill", "from": "intact", "to": "drilled"},
        ],
        "reversible": False,
        "collision_per_state": {"intact": True, "drilled": True},
    },
}

# opening.kind -> fixture kind (the inference). A garage door is a door; a
# breach opening is a breachable wall; a vault opening is a vault door; a teller
# opening is a teller window; a safe_deposit opening is a box wall; a window is
# interactive only when the author marks it breakable.
_KIND_TO_FIXTURE = {"door": "door", "garage": "door", "breach": "breach_wall",
                    "vault": "vault_door", "teller": "teller_window",
                    "safe_deposit": "safe_deposit_boxes"}


def _copy_machine(spec):
    return {k: (v.copy() if isinstance(v, (dict, list)) else v)
            for k, v in spec.items()}


def interactive_id(building, wall_name, story, kind, pos):
    """A stable, deterministic id for one fixture.

    Derived from the fixture's PLACE -- building, wall, story, kind, and the
    authored fractional position along the wall -- NOT any array index. So
    re-greyboxing a building, or adding an opening elsewhere, never renumbers
    this fixture and breaks a saved or replicated reference. Moving the opening
    changes the id, which is correct: it is a different place.
    """
    key = f"{building}|{wall_name}|{story}|{kind}|{round(float(pos), 4)}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    return f"{building}:if:{digest}"


def derive_interactive(building, wall_name, story, opening_kind, pos,
                       breakable=False, override=None):
    """Return an interactive state machine for an opening, or None if it isn't
    interactive.

    Inference by opening kind: doors/garages -> a ``door``; a ``breach`` opening
    -> a ``breach_wall``; a ``window`` -> a ``window`` only when ``breakable``.

    ``override`` gives authored control on top of the inference:
      * ``None``  -> use the inferred machine (or none).
      * ``False`` -> force non-interactive (e.g. a fixed, decorative door).
      * ``dict``  -> merged over the inferred machine, or used standalone for a
                     fully custom fixture on an otherwise non-interactive kind.
    """
    if override is False:
        return None

    fixture = _KIND_TO_FIXTURE.get(opening_kind)
    if fixture is None and opening_kind == "window" and breakable:
        fixture = "window"

    machine = _copy_machine(_DEFAULTS[fixture]) if fixture is not None else None

    if isinstance(override, dict):
        machine = {**(machine or {}), **override}
    if machine is None:
        return None

    machine["id"] = interactive_id(building, wall_name, story,
                                   machine.get("kind", opening_kind), pos)
    machine["source"] = "authored" if isinstance(override, dict) else "inferred"
    return machine


def slot_interactive(machine):
    """The art-facing subset for a slots.json slot's ``interactive`` block. Zoo
    reads ``states`` + ``state_geometry`` to build per-state art variants."""
    out = {
        "id": machine["id"],
        "kind": machine["kind"],
        "states": list(machine["states"]),
        "default": machine["default"],
    }
    if "state_geometry" in machine:
        out["state_geometry"] = dict(machine["state_geometry"])
    if "collision_per_state" in machine:
        out["collision_per_state"] = dict(machine["collision_per_state"])
    return out


def gameplay_interactive(machine, slot_ref, transform, building=None):
    """The netcode-facing entry for a gameplay.json ``interactives`` item. The
    game spawns one replicated node per id and drives which variant renders."""
    entry = {
        "id": machine["id"],
        "kind": machine["kind"],
        "slot_ref": slot_ref,
        "transform": transform,
        "states": list(machine["states"]),
        "default": machine["default"],
        "transitions": [dict(t) for t in machine.get("transitions", [])],
        "source": machine.get("source", "inferred"),
    }
    if "reversible" in machine:
        entry["reversible"] = machine["reversible"]
    if building is not None:
        entry["building"] = building
    return entry
