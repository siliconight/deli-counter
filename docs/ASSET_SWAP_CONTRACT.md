# ASSET_SWAP_CONTRACT.md

> **Status (as of 0.35.0): design spec — NOT yet implemented.** The shipped modular geometry lives in `docs/WALL_SEGMENTATION.md`; this document describes the intended direction (slot keys / manifest / themed-prefab swap) that builds on it.

The art-pass swap contract — Deli Counter

**Status:** design spec · the agreement between the greybox emitter and the authored prefab zoos

This is the contract that makes "progressively replace greybox pieces with themed pieces at the same
transforms" mechanical instead of manual. It defines two things that must agree: the **slot** Deli
Counter emits for each greybox piece, and the **zoo entry** an artist authors to fill it. It builds
on `PLACEMENTS_MANIFEST.md` (the slot is a manifest record with a few more fields) and
`ART_PASS_MODULAR.md` (the grid/pivot rules that make a fixed prefab actually fit).

---

## The workflow this serves

1. DC emits a building's layout as separate named greybox pieces + a slot per piece.
2. In the Godot editor you compose the **building** scene (just the building) from pieces — greybox
   and/or kitbashed prefabs — and save it as a reusable scene.
3. You lock the layout when you're happy with it.
4. **Art pass:** a Godot editor tool reads the slots, picks an active theme, and swaps each
   structural greybox piece for its themed equivalent **at the same transform**. Unfilled slots stay
   greybox, so a half-finished pass still builds (mixed greybox + themed).
5. The finished building scene is instantiated into the **mission** scene (this is the DC → Lot
   split: DC/building, Lot/site).

The swap happens at building-scene level, theme by theme, so editing the gas-station set never
touches the diner set. End state: every role × theme has a full zoo of styles.

**One architectural consequence, stated plainly:** in this model the finished building lives in the
editor, assembled from prefabs — so DC stops being the source of the *finished building* and becomes
the source of the **layout + the greybox zoo + the slot keys**. Artists get editor control; the
replication-free thesis is unaffected (instanced static geometry still isn't synced). Choose this
deliberately — it's a softening of "DC is the single source of the building" to "…of the layout."

---

## The contract: a slot and a zoo entry must agree on five things

1. **Identity** — role + style + size variant (the name resolves the right GLB).
2. **Dimensions** — the zoo entry is authored at exactly the slot's module size, so it drops in at
   scale 1 with no stretch.
3. **Pivot / origin** — both use the same pivot convention, so same transform = same placement.
4. **Openings** — if the slot is an opening, the entry has the hole/frame in the right place.
5. **Collision** — the entry provides collision (or declares it inherits DC's auto-collision rule).

If all five hold, swap is a name lookup + a transform copy. If any fails, the piece stretches,
floats, clips, or ghosts.

---

## Taxonomy (pinned — author nothing until this is fixed)

The swap tool keys entirely off names, so the axes are closed and ordered. Canonical filename:

```
<role>_<kit>_<style>[_<sizemod>][_w<cm>][_<state>].glb
```

- **role** — structural class. Closed vocabulary: `wall`, `doorway`, `window`, `floor`, `ceiling`,
  `roof`, `stair`, `ramp`, `ladder`, `column`, `beam`, `railing`, `catwalk`, `bars`, and `prop_<name>`
  for props.
- **kit** — the swap namespace, the thing an art pass changes. For **structural** pieces this is a
  **theme** (`greybox`, `gasstation`, `diner`, `bank`, …). For **material-defined props** it's a
  **material** (`wood`, `metal`, `glass`, …). The slot declares which (`kit_axis: "theme" | "material"`)
  so the tool knows whether the active *theme* selector or a *material* selector drives the swap.
- **style** — integer variant within the kit (`1`, `2`, …), written 2-digit in filenames (`01`).
- **sizemod** — optional module variant. Closed vocabulary: omitted = `full`; else `half`, `wide`,
  `narrow`, `corner_in`, `corner_out`, `end`, `plain`. Note: the wall remainder is folded into the
  **role** as its own type (`wallEnd`) rather than a sizemod, so a kit can author a dedicated end piece.
- **width** — optional `w<cm>` token (cm = round(width × 100), e.g. `w90`). Modules are instanced at
  authored size and never scaled, so this lets varied-width openings each get an exact-fit module.
  - **One exception — greybox wall remainders (`wallEnd`).** A wall run rarely divides evenly into
    full modules, so it leaves a solid filler strip whose size varies slot to slot (a single run can
    leave a 1.5 m, a 0.6 m, and a 0.2 m piece). These are plain solid boxes, never themed, so instead
    of authoring a module per width the builder emits them against a **unit (1×1×1) module** and
    carries the size as a per-slot `scale` in the manifest transform. Author `wallEnd_greybox_01.glb`
    as a 1 m cube centered at origin; one module then fills every remainder exactly. This is the *only*
    slot type that scales — full walls, doorways, and windows stay exact-fit so themed art is never
    stretched. (`scale ≠ [1,1,1]` in the manifest is the signal that a slot is unit-scaled filler.)
- **state** — optional model state, free token (`damaged`, `weathered`, …). Cosmetic to resolution;
  it's recorded in the slot manifest's `current_ref` and (on the `.tscn` path) set as `dc_state`
  metadata on the overlay, so game code can act on it.

**Resolution precedence** (per kit, active theme then `greybox`, most specific first):
`…_w<cm>_<state>` → `…_w<cm>` → `…_<state>` → `…`. Selectors: `DC_THEME` / spec `theme` picks the kit;
`DC_STATE` / spec `state` picks the state. Backward compatible — with neither width nor state files
present, resolution is the plain `<role>_<kit>_<style>` name.

Mapping the examples:

- `door_wood_1` → `prop_door` · material `wood` · style 1 ✓
- `door_metal_3` → `prop_door` · material `metal` · style 3 ✓
- `wall_gasstation_1` → `wall` · theme `gasstation` · style 1 ✓
- `wall_greybox_1` / `wall_chineserestaurant_1` → `wall` · theme `greybox`/`chineserestaurant` · style 1 ✓

**Existing library needs a one-time normalization pass.** Names like `doorway_1_half`, `beam_1`,
`arc_1_wall_1_plain` carry no kit token — they're implicitly one base kit. Under the contract they
become `doorway_greybox_1_half`, `beam_greybox_1`, etc. (the current set *is* the `greybox` theme).
Until that pass runs, the swap tool can't resolve them. Do it before anyone authors a second theme.

---

## Slot schema (DC emits one per greybox piece)

A slot is a `placements.json` record (see `PLACEMENTS_MANIFEST.md`) plus the swap fields:

```json
{
  "slot_id": "wall_N_3",
  "role": "wall",
  "style": 1,
  "kit_axis": "theme",
  "default_kit": "greybox",
  "module": [4.0, 3.0, 0.2],
  "size_mod": "full",
  "facing": "N",
  "pivot": "center",
  "openings": [],
  "collision": "convex",
  "transform": {
    "position": [0.0, 1.5, -4.0],
    "rotation_euler_deg": [0.0, 0.0, 0.0],
    "scale": [1.0, 1.0, 1.0]
  }
}
```

- `module` is the dimensions a replacement **must** be authored at — the no-stretch target. It's why
  module segmentation is required (next section): a parametric "wall as long as the building side"
  has no module to match.
- `scale` is `[1,1,1]` for themed swaps — the fit comes from authoring to `module`, not from
  scaling. (Scaling stays available for greybox-only blocks that read fine distorted.)
- `default_kit` is what currently fills the slot; `kit_axis` tells the tool which selector overrides it.

---

## Zoo entry requirements (what an authored GLB must satisfy)

- Named per the taxonomy: `<role>_<kit>_<style>[_<sizemod>].glb`.
- Authored at exactly the slot's `module` dimensions (within ε ≈ 1 mm), so it lands at scale 1.
- Pivot / local origin at the slot's `pivot` convention (centered for walls, etc. — see
  `ART_PASS_MODULAR.md`).
- If filling an opening slot, the hole / frame is in the slot's declared position.
- Provides its own collision, **or** is named with DC's collision suffix convention so the importer
  auto-generates it.
- Material assigned inside the GLB.
- Scale-neutral: no reliance on per-instance stretch.

---

## Resolution rule

```
fill(slot, active_theme):
    kit = active_theme  if slot.kit_axis == "theme"
          active_material(slot)  if slot.kit_axis == "material"
    name = f"{slot.role}_{kit}_{slot.style}" + (f"_{slot.size_mod}" if size_mod != "full" else "")
    glb  = library.get(name) or library.get(f"{slot.role}_{slot.default_kit}_{slot.style}...")
    instance glb at slot.transform   # scale stays [1,1,1]
```

The `or default_kit` fallback is what lets the art pass be *progressive*: an unauthored slot falls
back to greybox, so the building always composes. That's the collaborator's "progressively replace"
made literal.

---

## Openings become their own slots (key design decision)

DC currently builds a wall-with-a-hole as one piece (`_box_with_holes`) plus a `DOOR_SOCKET` marker.
The zoo (image 1) authors **doorways as their own pieces** — `doorway_1`, `doorway_1_half`,
`doorway_2_wide`. So for the swap workflow, DC should emit an **opening as its own slot** (a
`doorway` / `window` slot) flanked by plain module-wall slots, rather than one monolithic
wall-with-hole. Then `wall_<theme>_*` stays a clean tiling panel, and `doorway_<theme>_*` is a
separate swappable frame. This is the part of module segmentation that's specific to swap: decompose
openings, don't just cut holes.

---

## Validation (INTEL, never a gate)

A coverage check (in `check.py` or the editor tool) reconciles a building's slots against a theme's
zoo and reports, without failing:

- **Uncovered slots** — slots with no matching zoo entry for the active theme (what's left to author).
- **Dimension mismatches** — a zoo entry whose authored size ≠ the slot `module` (would stretch).
- **Dead assets** — zoo entries that match no slot in any building (authored but unused).

This is the "is the gas-station zoo finished?" dashboard, and it stays advisory — consistent with
DC's gate philosophy.

---

## Who owns what

- **Deli Counter** — module-segmented greybox, openings-as-slots, and the slot keys (the manifest
  enriched with role / style / module / size_mod / kit_axis / facing / pivot / openings / collision).
- **Artists** — the themed zoos authored to the taxonomy + fit rules above.
- **Godot editor tool** (`meshlib_kit.gd` territory) — reads slots, picks the active theme, resolves
  and instances per the rule, falls back to greybox. **Not DC's job.**

The two real DC engineering items remain: module segmentation incl. opening decomposition, and
emitting these slot keys (mostly repurposing the placements manifest). Everything past the slot
boundary is authoring and editor tooling.
