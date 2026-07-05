# SLOT_MANIFEST.md

The slot manifest — Deli Counter's art-pass input

**Status:** emitted as of **0.37.0** (`<name>.slots.json`). Supersedes the separate
`PLACEMENTS_MANIFEST.md` and `ASSET_SWAP_CONTRACT.md` drafts — this is the single concrete format both
described.

When a building is locked, DC writes a **slot manifest**: one record per swappable module — every wall
segment, every opening, every placement. It's the artist's work list *and* the swap recipe. The art
pass is then mechanical: author `<type>_<theme>_<style>.glb` files; a resolve step points each slot at
its themed module (falling back to greybox), and the 0.36.0 instancing reuses each module N times.

This is **output-only** — no schema change, no geometry change. The `.glb` is unchanged; the manifest
is a sidecar.

---

## Why a slot, not a mesh name

A locked building is a mix: kitbashed pieces are already module references, but greyboxed pieces are
generated geometry with no identity. The manifest gives **every** swappable piece — grey and kitbash
alike — a stable id, a kind, a transform, and a fit contract. So the whole building becomes one uniform
list of slots, and "swap `wall_greybox_01` → `wall_gasstation_01`" is a one-field resolve, not a
remodel.

## Format

```json
{
  "slot_manifest_version": "1.0.0",
  "building_id": "fuel_stop",
  "theme": "greybox",
  "module_library": "art/zoo",
  "module_size": 2.0,
  "space": "spec/Blender Z-up raw coords; rot_y = degrees about up",
  "slots": [
    {
      "slot_id": "ext_0_N_seg0",
      "role": "wall", "size_mod": "full", "style": 1,
      "current_ref": "wall_greybox_01",
      "kit_axis": "theme",
      "wall": "ext_0_N", "story": 0, "facing": "N",
      "transform": { "translation": [-3.0, 4.0, 1.5], "rot_y": 0, "scale": [1,1,1] },
      "fit": { "dims": [2.0, 0.2, 3.0], "pivot": "center", "openings": [], "collision": "convex" }
    },
    {
      "slot_id": "ext_0_N_open0",
      "role": "doorway", "size_mod": "full", "style": 1,
      "current_ref": "doorway_greybox_01",
      "kit_axis": "theme",
      "wall": "ext_0_N", "story": 0, "facing": "N",
      "transform": { "translation": [-2.0, 4.0, 1.5], "rot_y": 0, "scale": [1,1,1] },
      "fit": { "dims": [1.0, 0.2, 3.0], "pivot": "center",
               "openings": [{ "kind": "door", "width": 1.0, "height": 2.1, "sill": 0.0 }],
               "collision": "convex" }
    },
    {
      "slot_id": "pump_a",
      "role": "prop", "size_mod": "full", "style": 1,
      "current_ref": "gas_pump",
      "kit_axis": "material",
      "wall": null, "story": null, "facing": null,
      "transform": { "translation": [2.0, -3.0, 0.0], "rot_y": 90, "scale": [1,1,1] },
      "fit": { "dims": null, "pivot": "asset", "openings": [], "collision": "convex" }
    }
  ]
}
```

## Field reference

- **slot_id** — stable, unique id for this position. A swap is addressable by it; coverage is tracked
  by it. (Wall segment node name, opening group name, or placement name.)
- **role** — `wall` / `doorway` / `window` / `breach` / `prop`. What kind of module fills the slot.
- **size_mod** — `full` (whole module), `end` (a span's leftover partial → a `wallEnd` type),
  `span` (Phase-A un-tiled). Folds into the type token for the ref name.
- **style** — variant number (default 1). Lets a theme ship `wall_gasstation_01`, `_02`, …
- **current_ref** — the module there now: `<type>_<theme>_<style>` (`wall_greybox_01`,
  `wallEnd_greybox_01`, `doorway_greybox_01`). `type` folds size per the naming law.
- **kit_axis** — what the swap varies by. `theme` for structural (swaps by mission theme — the
  gas-station case); `material` for props (swap by material, not theme); a `fixed` piece wouldn't be
  emitted as a swappable slot.
- **wall / story / facing** — provenance: parent wall, storey index, cardinal facing (or `X`/`Y` for
  partitions).
- **transform** — `translation` (raw spec/Blender Z-up, same space as `gameplay.json`), `rot_y`
  (degrees about up, to orient a canonically-authored module: N 0 / E 90 / S 180 / W 270), `scale`
  (always `[1,1,1]` for structural — no-stretch).
- **fit** — what a replacement must match, 1:1:
  - `dims` — the module's extents (null for props authored at their own size).
  - `pivot` — `center` (structural) / `asset` (placement). Author modules origin-centered and the
    placement point *is* the transform.
  - `openings` — for doorway/window/breach: the aperture `{kind, width, height, sill}` the themed
    frame must clear.
  - `collision` — the collision mode the replacement must provide. **Constraint:** a themed module must
    supply equivalent collision, or the enterability/nav gates drift (a door that seals, a wall that
    opens). The gates run on the assembled result and catch it; a coverage check flags it earlier.

## How the art pass consumes it

```
for slot in manifest.slots:
    if slot.kit_axis == "fixed": continue
    type = typename(slot.role, slot.size_mod)           # wall / wallEnd / doorway / window / prop
    item = f"{type}_{theme}_{slot.style:02d}"            # wall_gasstation_01
    module = find(module_library, item) or find(module_library, f"{type}_greybox_{slot.style:02d}")
    instance(module, at=slot.transform)                  # 0.36.0: shared mesh, one in VRAM
```

This gives the three properties of the art pass:

- **Theme-namespaced** — theme modules are separate files; editing `wall_gasstation_01` updates every
  gas-station wall and touches nothing else, because the manifest only points gas-station buildings at
  gas-station files.
- **Progressive** — an uncovered role falls back to greybox, so the pass fills in role by role.
- **Cheap** — every slot of a role points at one file: one mesh + one texture in VRAM, edit-one-update-all.

## Interactive fixtures (`interactive` block)

A door, breachable wall, or breakable-window slot carries an extra `interactive`
block — the art-facing view of its state machine:

```json
"interactive": {
  "id": "primos_pizza:if:2cf6a380",
  "kind": "breach_wall",
  "states": ["intact", "breached"],
  "default": "intact",
  "state_geometry": { "intact": "wall", "breached": "breach" },
  "collision_per_state": { "intact": true, "breached": false }
}
```

Zoo reads this to build a **per-state art variant** (`_<state>` naming law):
the default state is the base module; each non-default state whose geometry
differs is a `<stem>_<state>` variant, built with its `state_geometry` species.
That is what makes a breachable wall the `breached` STATE of a wall slot
(`intact` → wall geometry, `breached` → breach geometry), not a separate module.
The same `id` appears in `gameplay.json`'s `interactives` array (the netcode
side). Doors/breaches get this by inference; a window only when authored
`breakable`. Full contract: `docs/INTERACTIVES.md`.

## What DC does / doesn't

- **DC emits** the manifest from the locked layout — the deterministic recipe of *what module, what
  kind, where, must-fit-what*. Transforms come straight off the modular emitter's per-segment data, so
  this is also the **auto-placement** output: DC has written down the placements you'd otherwise
  hand-author.
- **DC does not** author the theme modules (artist) or perform the swap (a resolve at build or load).

## Open items

- **The resolve/instance step is built (0.38.0):** with a module library + theme
  configured, DC resolves each slot → `<type>_<theme>_<style>.glb` (greybox
  fallback) and instances it at the slot transform, reusing the 0.36.0
  import-once cache; uncovered roles fall back to a generated box. A load-time
  Godot variant remains an option. Either is a pure function of manifest +
  module library → deterministic.
- Coverage intel ships in the manifest's `coverage` block (per role/kit:
  theme / greybox / generated) — the art-pass progress meter.
- A wall segment's `rot_y` distinguishes facing, but front/back symmetry of a
  wall module means N vs S may not need distinct art; openings with a defined
  interior face will. Validate when the first themed opening lands.
