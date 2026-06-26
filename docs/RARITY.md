# Building rarity — the contract value behind the door-reveal

A building can carry one **rarity** (`common` / `uncommon` / `rare` / `epic` /
`legendary`). When set, the build stamps that tier and its one canonical colour
onto `gameplay.json` and onto every breachable door/breach anchor, so a networked
door can **pop the right colour the instant it opens** — the "open a Legendary
chest, but it's a whole building" reveal.

This page is about the seam between the kit and your game.

## What the kit does (and deliberately doesn't)

The kit makes **models, not levels.** Rarity is a value on the model's contract,
not a baked effect. So:

**The kit supplies:**
- one `rarity` per building (or none),
- the single canonical colour for that tier (hex + Godot `rgb`), in one place
  (`rarity.py`) so it can't drift into five hard-coded hex strings,
- that colour stamped onto `gameplay.json` (top level) and onto each breachable
  opening + its `DOOR_SOCKET` / `BREACH_PANEL` anchor.

**Your game does the reveal** — the light burst, the rarity sound cue, the HUD
banner, the music swell, the AI barks, the controller rumble. All of it reads the
value the kit exposed. The kit colours the *value*; you stage the *show*. This is
exactly the proposal's own framing: *"the reveal simply exposes information that
already exists."*

**Also your game, not the kit:** the rarity-driven enemy budget, loot budget,
elite/boss probability, events. Those are downstream systems that key off the one
rarity value — gameplay code, the same way objectives and the AI director are.
The kit hands you the source of truth; it doesn't generate encounters.

## The tiers

| Tier | Colour | hex | rgb (Godot 0..1) |
| --- | --- | --- | --- |
| `common` | white | `#FFFFFF` | `1, 1, 1` |
| `uncommon` | green | `#1EFF00` | `0.1176, 1, 0` |
| `rare` | blue | `#0070DD` | `0, 0.4392, 0.8667` |
| `epic` | purple | `#A335EE` | `0.6392, 0.2078, 0.9333` |
| `legendary` | yellow | `#FFD700` | `1, 0.8431, 0` |

`rarity.py` is the source of truth. If you want different hues, change them there
once and everything downstream agrees.

## Setting it

In a spec:

```json
{ "name": "pawn_shop", "mode": "heist", "rarity": "legendary", ... }
```

Or when generating from a preset:

```
python new_level.py --preset corner_deli --name pawn_shop --rarity legendary
```

Leave it out (or `null`) and nothing changes — no rarity fields are emitted, same
as before. A bad tier fails the build offline rather than shipping an
uncolourable building.

## Reading it in Godot

Two paths, same colour. Use whichever fits how you wire doors.

**A. Building-level (authoritative).** Read it once from the building's
`gameplay.json` — the source of truth, and robust even if a styling/re-export
pass ever drops the marker Empties:

```gdscript
var gp = JSON.parse_string(FileAccess.get_file_as_string(gameplay_path))
if gp.rarity != null:
    var c = gp.rarity_color
    var pop := Color(c.rgb[0], c.rgb[1], c.rgb[2])   # legendary -> yellow
    # hand `pop` to whatever stages the reveal for this building
```

**B. Per-door (convenience).** Each `DOOR_SOCKET_*` / `BREACH_PANEL_*` anchor in
the `.glb` carries the rarity as node metadata (exported via glTF `extras`), so a
door scene instanced at that socket reads its own colour with no lookup back to
the building:

```gdscript
# on the networked door, when it opens / is breached:
func _pop_rarity() -> void:
    if not has_meta("rarity_rgb"):
        return                              # building has no rarity
    var rgb = get_meta("rarity_rgb")        # [r, g, b] 0..1
    var pop := Color(rgb[0], rgb[1], rgb[2])
    $RevealLight.light_color = pop
    $RevealLight.visible = true
    # + sound cue, HUD banner, etc. — your reveal, your timing
```

The anchor also carries `rarity` (tier string) and `rarity_color_hex` if you
prefer those.

### "Hidden until breach" is door state, not kit state

The kit always knows the colour; *hiding* it until the breach is your door's job.
The door shows neutral while closed, then pops the stamped colour on open. The
kit gives the door the colour to pop; the door decides **when**. Because the
shell geometry is identical on every client and the rarity is fixed at generation
(it's in the baked contract), every player's door reveals the same colour at the
same moment with nothing to sync but the door's open state.

## Compounds (Lot)

When you assemble buildings into a site with **Lot**, each building keeps its own
rarity: the merged `<site>.site.gameplay.json` records `rarity` + `rarity_color`
per building, and the stamped door openings pass through unchanged. So a
neighbourhood naturally ends up with a spread of rarities — every door on the
block its own little mystery.

(Lot doesn't *assign* rarities across a run yet — each building's rarity comes
from its own spec. Deterministic per-run assignment from the site seed would be a
natural Lot feature if you want the neighbourhood reshuffled each mission.)

## Verifying

The colour table, parsing, stamping, and merge are offline-verified. The one
piece to confirm in-engine on your first walk: that the `DOOR_SOCKET` /
`BREACH_PANEL` custom properties round-trip into Godot node metadata as
`get_meta("rarity_rgb")` on import (path **B**). Path **A** reads straight from
`gameplay.json` and doesn't depend on the glTF import, so it's the safe default if
the metadata ever doesn't survive a re-export.
