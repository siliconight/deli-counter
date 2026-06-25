# GridMap parts-kit (optional)

**This is an optional companion to Deli Counter's main output. The baked `.glb`
is still the primary, replication-free level shell — the parts-kit doesn't
change or replace it.** The kit is for a *different* workflow: if you want to
hand-greybox a fresh layout by eye, on a grid, in the Godot editor, this gives
you a palette of modular pieces to paint with in a `GridMap`. Ignore it
entirely if you only want the generated shells.

## Why it exists

Deli Counter's core generates a *monolithic, deterministic* building from a
spec. That's deliberate. But sometimes you just want to *sketch* — block out a
room layout by hand to feel it out, before (or instead of) writing a spec. A
`GridMap` + this `MeshLibrary` lets you do that: click to place walls, doors,
floors, stairs on a grid. It's the quick-sketch counterpart to the precise
spec-driven pipeline.

It is **not** a replacement for the baked shell, and a GridMap is a live
node that composes tiles at runtime — so a hand-painted GridMap level is *not*
the replication-free baked artifact the `.glb` is. Use the kit to sketch; use
the spec pipeline to produce the real deterministic shell.

## What's in the kit

A standard set of grid-aligned modules (1 m structural cell, 3 m story, sized to
the kit's scale guidelines):

| module | what it is |
|--------|-----------|
| `floor_1x1` | floor / ceiling tile |
| `wall_1m` | solid wall segment, full story |
| `wall_half_1m` | half wall / railing at cover height |
| `wall_door_1m` | wall with a 1.2 × 2.2 m doorway |
| `wall_window_1m` | wall with a mid-height window |
| `pillar` | square column |
| `counter_unit` | counter / low shelf |
| `stair_flight` | straight flight, one story over ~4 cells |
| `crate_1m` | 1 m cover cube |

Every module carries box collision, so a painted blockout is immediately
walkable in the test harness. Run `python meshlib_kit.py` for the manifest.

## How to use it

1. In Godot, open `addons/deli_counter/meshlib_kit.gd` in the script editor and
   **File → Run** (Ctrl+Shift+X). It writes
   `addons/deli_counter/deli_counter_kit.meshlib`. (Built in-engine, so the mesh
   and collision data is always valid.)
2. Add a **GridMap** node to a scene.
3. In the GridMap inspector, set **Mesh Library** to the `.meshlib` file.
4. Set **Cell Size** to `(1, 1, 1)` for structural painting, or `(0.5, 3, 0.5)`
   to match the fine grid.
5. Pick a module from the palette and paint. The collision comes along for free,
   so you can drop in the player and walk your sketch immediately.

## Relationship to the spec pipeline

Think of it as the loosest of the on-ramps:

- **GridMap sketch** (this) — fastest, by hand, for feeling out a layout. Not
  deterministic, not the baked shell.
- **`describe.py` interview** — guided spec authoring.
- **`new_level.py --preset`** — parametric from a recipe.
- **hand-authored JSON** — full control.

The bottom three all produce a real spec → baked `.glb`. The GridMap sketch is
a thinking tool that sits beside them. Everything stays optional and deletable —
delete `meshlib_kit.gd` and `meshlib_kit.py` and nothing else changes.
