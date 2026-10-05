"""Which state an Empty's window is painted in (0.179.0).

The walker, 2026-10-04, with a Bloodlines street as the comp: lights on in
the windows at night to show life. Read off in the factory root's
`docs/reference/EMPTIES_COMPS.md`, "LIT WINDOWS AT NIGHT": mixed per
building, MOST DARK, some lit warm, many of the lit ones behind bars,
curtains and blinds; a vacant 1990s rowhouse boarded.

Zoo (>= 1.64.0) paints the states (`zoo_keeper.core.window_panes`) and maps
each window's pane to its cell; this decides which state a window is in,
because which windows glow is a fact about the building. Pure and seeded --
`zlib.crc32` of the building, its seed and the slot -- so a rebuild paints
the same street.

PER BUILDING, NOT PER PLACEMENT. The state rides on the slot and so on the
module, and every placement of one archetype shares its modules: seven
copies of one rowhome across a street show one pattern seven times. More
variety needs more archetypes or a per-instance pick, and is not here.
"""
from __future__ import annotations

import zlib

#: The states, in Zoo's atlas order. Must equal
#: `zoo_keeper.core.window_panes.STATES` (pinned by `test_empty_panes.py`).
STATES = ("lit", "lit_amber", "lit_cool", "lit_pink",
          "lit_blind", "lit_blind_cool", "lit_curtain", "lit_shade",
          "lit_bars", "dark", "dark_blind", "dark_shade",
          "dark_curtain", "dark_bars", "dark_fan", "boarded")

#: (state, weight), each table summing to 100. COLOUR VARIATION IS KEY (the
#: walker, 0.180.0): the lit share is spread across four room lights and the
#: coverings, so a street is not one warm yellow. Street level: bars on over a
#: third, most dark -- 32 lit in 100.
GROUND = (("dark_bars", 24), ("lit_bars", 12), ("dark", 12), ("dark_blind", 10),
          ("dark_curtain", 8), ("dark_shade", 8), ("dark_fan", 6), ("lit", 6),
          ("lit_amber", 4), ("lit_blind", 4), ("lit_curtain", 3), ("lit_shade", 3))
#: Upstairs: no bars, still more dark than lit -- 42 lit in 100.
UPPER = (("dark", 18), ("dark_blind", 12), ("dark_shade", 10), ("dark_curtain", 12),
         ("dark_fan", 6), ("lit", 8), ("lit_amber", 7), ("lit_cool", 6), ("lit_pink", 4),
         ("lit_blind", 6), ("lit_blind_cool", 4), ("lit_curtain", 4), ("lit_shade", 3))


def _crc(text):
    return zlib.crc32(text.encode("utf-8"))


def _pick(table, key):
    r = _crc(key) % sum(w for _, w in table)
    for state, w in table:
        if r < w:
            return state
        r -= w
    return table[-1][0]


def choose(building, seed, slot_id, story, vacant=False):
    """The state of one window: ``boarded`` on a vacant building, else drawn
    from the street-level table on storey 0 and the upstairs one above.

    VACANCY IS AUTHORED, NOT DRAWN. A seeded one-in-seven left none of the six
    rowhomes vacant (the odds of that are (6/7)^6, about 40%), and the agreed
    family lists boarded as a VARIANT of the rowhome -- so the family table
    says which house is vacant (`presets.EMPTY_ROWHOMES`, spec `vacant`), as it
    says which is siding."""
    if vacant:
        return "boarded"
    return _pick(GROUND if int(story or 0) <= 0 else UPPER,
                 "%s:%s:%s" % (building, seed, slot_id))
