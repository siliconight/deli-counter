# ART_PASS_MODULAR.md

> **Status (as of 0.35.0): design spec — NOT yet implemented.** The shipped modular geometry lives in `docs/WALL_SEGMENTATION.md`; this document describes the intended direction (slot keys / manifest / themed-prefab swap) that builds on it.

Modular / prefab art-pass conventions — Deli Counter

**Status:** design notes · direction under consideration · pairs with `docs/PLACEMENTS_MANIFEST.md`

These are the rules that govern the optional `gridmap` / `multimesh` paths the placement manifest's
`instancing` field selects. None of this changes the blockout. The monolith stays the default and
the correct shippable shell; modular is an **authoring/art-pass** representation you opt into per
piece.

---

## The one principle: triage, not a switch

"Single mesh vs modular" is not a global decision. It's per-`part_type`, because the memory and
draw-call wins and the lighting cost all depend on which Godot construct emits the piece. The
manifest already carries the routing (`mesh` / `gridmap` / `multimesh`); this doc is *why* a given
piece gets a given mode.

Rule of thumb:

- **Structural envelope** (exterior walls, partitions, floor, stairs, landings) → `mesh`, or merged
  into the static shell. Mostly unique, dominates screen space, and it's the only path that can take
  baked lightmaps.
- **Grid-aligned modular blocks** (repeating wall segments, modular trim runs) → `gridmap`.
- **Repeated props / fixtures** (gas pumps, shelving, counters, light fixtures, repeated signage)
  → `multimesh`, grouped by `instance_group`. This is where the "one mesh in VRAM, the rest are just
  transforms" win is real.

A flat-out instancing of *everything* is the wrong target: you'd get resource sharing but
reintroduce the node-hierarchy clutter that was the monolith's main advantage, and you wouldn't
guarantee the draw-call batching. Triage is the point.

---

## The lighting fork (the real cost of instancing)

This is the trade hiding behind "single meshes have no seam risk." It's specifically about **baked
lightmaps**:

- `gridmap` and `multimesh` geometry **cannot receive per-instance baked lightmaps** — `LightmapGI`
  needs a unique UV2 per surface, and instances share the mesh. So any piece you mark instanced
  commits its lighting to **real-time / SDFGI / vertex-color**.
- `mesh` (and the monolith) **keep baked lightmaps on the table**.

For DC this is less of a sacrifice than it sounds: the golden-path aesthetic (PS1 / early-Xbox →
early 360) and the Patina / vertex-nuance layer already lean on vertex-color light and low-frequency
detail, not high-frequency baked GI. Vertex-color lighting has no lightmap-seam problem at all. So
the natural DC posture is: **vertex-color / SDFGI everywhere, baked lightmaps only on bespoke `mesh`
hero geometry if ever.** Just make it a deliberate decision per build, not something discovered at
bake time.

If a build mixes baked-lightmap `mesh` pieces with instanced pieces, the lighting models won't match
at the seam — that's the one place the collaborator's "seam risk" genuinely returns, and it's a
reason to keep a building's lighting model consistent rather than mixed.

---

## Grid and pivot rules

DC already works on a 0.5 m grid with metric units. The modular path adds module discipline on top:

- **Module size = a power-of-two-friendly multiple of the grid.** Pick one primary module for
  modular wall/floor blocks (2 m is the natural DC choice: 4 grid cells, divides into 1 m and 0.5 m
  sub-pieces cleanly). Main modular parts snap to the module in every axis; this is what lets fixed
  prefabs tile without stretching.
- **Main parts on-grid, breakup parts free.** Big modular blocks must land on the module grid or
  they won't snap. Small breakup pieces (ledges, panels, single props) can sit at sub-grid positions
  or off-grid entirely — that freedom is what hides the repetition.
- **Pivot convention, fixed per kind.** Snapping depends entirely on pivots being predictable:
  - Walls → pivot **centered on thickness** (so one corner piece serves as both inner and outer
    corner with no offset).
  - Floor / ceiling tiles → pivot at a **consistent corner** of the footprint.
  - Props → pivot at the **footprint center, on the ground plane** (z = 0), so rotation about the
    vertical doesn't shift the base.
  Pin whichever you choose in the library and never mix conventions within a kind.
- **Scale / rotation reuse.** Allowing non-90° wall runs and scaled reuse of a single block makes a
  building read as less tiled. The catch for DC: stretching a piece with baked, UV-mapped textures
  distorts them. Triplanar / world-space projection sidesteps that, but it fights the deliberate
  fixed-texel PS1 look — so prefer **vertex-color variation over stretched-UV reuse** for DC, and
  reserve scaling for pieces that read fine distorted (plain blocks, fills).

---

## Balancing modularity and uniqueness

Repetition is the failure mode of a modular kit — the eye starts seeing the same part everywhere and
the scene reads as generic. DC's toolbox for breaking that up, in aesthetic priority order:

1. **Per-instance MultiMesh color / custom-data** (the primary lever). The `instance` block in the
   manifest feeds Godot's per-instance color and custom-data buffers, so identical instances tint
   and vary without duplicating the mesh. This is the synthesis: uniqueness *and* the instancing win.
   Drive it deterministically from the build seed so the manifest stays byte-identical.
2. **Patina / vertex-nuance variation** per piece — the existing vertex-color art pass, now
   targetable per-part via the manifest's `node` join key instead of whole-mesh.
3. **A deliberate mix of big and small parts.** A kit of only big blocks reads as obviously modular;
   a few small breakup parts (placed off-grid) add complexity. But too many small pieces becomes
   clutter — balance it.
4. **Non-grid placement and rotation of small props** — scatter, slight rotation, the occasional
   off-axis run.
5. **Decals / world-space dirt overlays** to differentiate adjacent identical pieces. These are
   largely **game-side** in DC's split (the shell provides geometry + anchors; decal projection is
   runtime/material work), so note them as a downstream consumer hook rather than something DC bakes.

Keep the toolbox era-appropriate: vertex color and low-frequency variation fit the golden path;
high-frequency PBR edge-wear and dense decal work do not.

---

## How this stays in DC's lane (gate philosophy)

Consistent with the enterability / IP gates being the only hard ones, the modular path is **INTEL,
not a new mandate**:

- In `--modular`, DC can **WARN** when a main modular part lands off the module grid (it won't snap)
  or when pivots are inconsistent — surfaced, not failed.
- An opt-in strict mode can promote the off-grid-main-part warning to an error for teams that want
  the kit kept clean ("gate clear-cut, warn the rest").
- DC still does not author art. It emits the recipe (the manifest with `instancing` + `instance`),
  the grid/pivot conventions are advice the library must follow, and the actual prefab meshes,
  MultiMesh setup, decals, and lighting model are game/art-side work.

---

## Workflow

Blockout as monolith (fast iteration, walk it, fix collision) → freeze the layout → assign
`instancing` per `part_type` → author the prefab library once against the grid/pivot conventions →
reuse across all presets → optionally flatten back to a monolith for ship if you want minimum draw
calls. Prefab becomes the authoring representation; monolith stays an optional ship-time
optimization.

---

## Reference

L. Kronenberger, "Balancing modularity and uniqueness in Environment Art," Beyond Extent (2020) —
the source for the modularity drawbacks, the grid/pivot/power-of-two advice, the big-vs-small
balance, and the break-the-repetition toolbox. Unreal-oriented; the principles port, the engine
specifics (MultiMesh/GridMap, SDFGI, lightmap UV2) are the Godot translation above.
