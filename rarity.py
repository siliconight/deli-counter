"""
rarity.py  --  the canonical building-rarity tier + colour table (no Blender)
=============================================================================
Deli Counter optionally stamps a single *rarity* onto a building. The rarity is
a contract value, not a visual effect: the kit records WHICH tier a building is
and the ONE canonical colour that tier pops in, then exposes both on the
gameplay.json top level and on every breachable door/breach anchor. The actual
reveal -- the light burst, the sound cue, the HUD banner when a networked door
opens -- is game code that reads this value. The tool carries the number; the
game does the show. (See docs/RARITY.md.)

This module is the single source of truth for the five tiers and their colours
so game code, the door reveal, and any sibling tool (Lot) all agree on what
"legendary yellow" actually is, instead of five hard-coded hex strings drifting
apart across a codebase.

Colours follow the design proposal's tier -> colour names (white / green / blue
/ purple / yellow) using the genre-standard loot-rarity hues, so a player reads
the tier from the colour with no legend.

bpy-free on purpose: importable by the offline validator, by Lot, and by the
Blender builder alike.
"""

from __future__ import annotations
from typing import Optional

# Ordered low -> high. Order is meaningful (a tier's index is its rank).
RARITY_TIERS = ["common", "uncommon", "rare", "epic", "legendary"]

# tier -> (human colour name from the proposal, canonical sRGB hex).
# Hex is the single source; rgb is derived from it so the two never drift.
_RARITY = {
    "common":    ("white",  "#FFFFFF"),
    "uncommon":  ("green",  "#1EFF00"),
    "rare":      ("blue",   "#0070DD"),
    "epic":      ("purple", "#A335EE"),
    "legendary": ("yellow", "#FFD700"),
}


def _hex_to_rgb(h: str) -> list[float]:
    """'#RRGGBB' -> [r, g, b] floats in 0..1, rounded to 4 dp (Godot Color)."""
    h = h.lstrip("#")
    return [round(int(h[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)]


def is_valid(rarity: Optional[str]) -> bool:
    """True if rarity is None (unset = no rarity) or a known tier."""
    return rarity is None or rarity in _RARITY


def resolve_rarity(rarity: Optional[str]) -> Optional[dict]:
    """Resolve a tier name to its colour record, or None if unset.

    Returns ``{"tier", "rank", "color_name", "hex", "rgb": [r,g,b]}`` -- the
    exact dict the kit drops into gameplay.json's ``rarity_color`` and onto each
    door/breach anchor. ``None`` in -> ``None`` out (a building with no declared
    rarity keeps the current behaviour: no rarity fields emitted).

    Raises ValueError on an unknown tier so a typo fails loudly offline rather
    than silently shipping a building the door reveal can't colour.
    """
    if rarity is None:
        return None
    if rarity not in _RARITY:
        raise ValueError(
            f"unknown rarity {rarity!r}; expected one of {RARITY_TIERS} or null"
        )
    name, hexv = _RARITY[rarity]
    return {
        "tier": rarity,
        "rank": RARITY_TIERS.index(rarity),
        "color_name": name,
        "hex": hexv,
        "rgb": _hex_to_rgb(hexv),
    }


if __name__ == "__main__":
    # quick offline dump of the canonical table
    import json
    print(json.dumps({t: resolve_rarity(t) for t in RARITY_TIERS}, indent=2))
