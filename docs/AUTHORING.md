# Authoring good buildings with Deli Counter

The mental model that ties everything together: **a Deli Counter greybox isn't a
rough sketch you throw away — it's the final building already standing, just
wearing boxes.** Every box is a stand-in for a specific themed piece, named and
sized so an artist's swap is 1:1. Author it that way and the same file is three
things at once: a function-locked playable level, a kit-of-parts an artist can
dress, and an already-instanced scene. Author it as a pile of unique boxes and
you get none of those.

## The one golden rule

**An art pass never touches collision or nav.** Collision and navigation live on
the greybox; a theme swap changes only what a piece *looks like*, never its
shape-for-gameplay. This is what makes "swap the skin" safe by construction — a
locked, walked greybox can't be broken by art, because art has no way to reach
the thing that was locked. On the `.tscn` + `theme_swap` path the artist edits
modules in `res://art/zoo/` and never opens the level scene at all, so they
physically cannot move a wall's collider.

## Match the primitive to the job

Everything in a building is one of three things, and the choice decides whether
it instances, whether it themes, and whether it stays cheap.

### Structure — walls, floors, openings, stairs, ramps

Author these in the spec's structural grammar (`ext_walls`, `partitions`,
`stairs`, …) with `modular` on — the default for new specs from `new_level.py`.
Each wall run becomes named swap-slots: identical tiles share one mesh, and every
slot is a 1:1 swap point a theme kit replaces. This is your shell. Author it for
*function* first; the art rides on top for free.

### Repeated props — pumps, lockers, shelves, crates, pillars, counters

Anything that appears more than once should be **one `asset` placed N times via
`placements`**, never N `volumes`. Placements are the form that instances: one
mesh and one texture in VRAM, the rest are transforms. You also art-pass the
source file once and every instance updates, and the art persists across
rebuilds. This is the single biggest lever for both memory and dress-ability.

### One-offs and massing — a canopy, a unique service counter, a weird machine

`volumes` are fine here. They don't repeat, so instancing buys nothing, and a
procedural box is the fastest way to block out unique massing. Use volumes for
greybox stand-ins of genuinely singular geometry.

> **The rule of thumb:** the moment something repeats, promote it from a volume
> to a placed asset. Repetition is the signal.

## Why this gets you all three things at once

**Good and fun** — only the greybox can get this right. Art can't rescue a boring
layout or break a fun one, so fun lives here: routes, flow, verticality, cover
rhythm, sightline breaks, readable landmarks. Build for *decisions* — every
objective room with at least two ways in (the build gate enforces this), flanks
around chokepoints, vertical interest. Then **walk it at player scale** and tune
until it feels good; that's the only real test. Because the art pass is
collision/nav-neutral, you can iterate on fun as hard as you want with zero art
risk.

**Easy to dress later** — make the greybox a clean swap contract. Two habits:
every cosmetic element is either a named modular slot or a placed asset (both are
swap points) — never a bare volume, which is not a swap point. And keep a **tight
palette**: standardize opening widths and prop types. A small vocabulary means an
artist authors *one* themed module per type and it fits everywhere — the
difference between a kit they finish in a weekend and an endless list of bespoke
pieces. The `<name>.slots.json` manifest is literally the handoff document: every
slot, its dims, its transform.

**Resource/VRAM sharing** — the same discipline, for free. That tight palette is
exactly what produces instancing: identical wall tiles share one mesh (66 walls →
1 mesh), and repeated props as placements of one asset share one mesh and one
texture. Fewer distinct widths and prop types = fewer unique meshes = more
sharing. "Small vocabulary" buys easy art *and* cheap memory in one move.

## What instances, and what doesn't

Mesh-sharing (one geometry + one texture in VRAM, repeats are just transforms) is
achieved for three things, all by linking one mesh datablock:

- **modular wall segments** — identical tiles share one mesh,
- **resolver modules** — a module GLB imported once, linked to every slot,
- **repeated `placements` of an asset** — imported and joined once, the cached
  mesh linked for every later placement (and it persists across rebuilds).

It survives the pipeline as: one Blender mesh datablock → one glTF mesh with N
nodes → one Godot `Mesh` resource shared by N `MeshInstance3D`.

**Not shared:** procedural `volumes`. Each volume gets its own mesh, even when
identical — so a row of eight pump *volumes* is eight meshes. That's the whole
reason repeated props belong in `placements`.

One precision: this is resource/VRAM sharing, not automatic single-draw-call GPU
instancing (Deli Counter emits no `MultiMesh`). The memory win holds regardless;
for one draw call at huge counts, convert those instances to a
`MultiMeshInstance3D` in-engine. See the README "Instancing & memory" section.

## Worked example: fuel-station pumps, volumes → instanced placements

The `fuel_stop_heist` greybox blocks its six pumps and three islands as
`volumes`. That's fine as pure blockout, but each box is its own mesh and none is
a swap point. Here's the conversion.

**Before** — nine volumes, nine meshes, no swap points:

```json
"volumes": [
  {"name": "pump_island_1", "x": -6.0, "y": -22.0, "z": 0.15,
   "size_x": 1.6, "size_y": 8.0, "size_z": 0.3, "collision": "convex"},
  {"name": "pump_1", "x": -6.0, "y": -25.0, "z": 1.0,
   "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex"}
  // ... pump_island_2/3, pump_2..6 ...
]
```

**After** — one asset per repeated shape, placed N times. Six pumps share one
mesh; three islands share another; each asset is a single swap point:

```json
"assets": [
  {"id": "pump",        "file": "props/pump_greybox.glb",        "collision": "box"},
  {"id": "pump_island", "file": "props/pump_island_greybox.glb", "collision": "box"}
],
"placements": [
  {"asset": "pump_island", "x": -6.0, "y": -22.0, "z": 0.15, "name": "pump_island_1"},
  {"asset": "pump_island", "x":  0.0, "y": -22.0, "z": 0.15, "name": "pump_island_2"},
  {"asset": "pump_island", "x":  6.0, "y": -22.0, "z": 0.15, "name": "pump_island_3"},
  {"asset": "pump", "x": -6.0, "y": -25.0, "z": 1.0, "name": "pump_1"},
  {"asset": "pump", "x": -6.0, "y": -19.0, "z": 1.0, "name": "pump_2"},
  {"asset": "pump", "x":  0.0, "y": -25.0, "z": 1.0, "name": "pump_3"},
  {"asset": "pump", "x":  0.0, "y": -19.0, "z": 1.0, "name": "pump_4"},
  {"asset": "pump", "x":  6.0, "y": -25.0, "z": 1.0, "name": "pump_5"},
  {"asset": "pump", "x":  6.0, "y": -19.0, "z": 1.0, "name": "pump_6"}
]
```

Why this reproduces the building exactly while improving it:

- The asset boxes are origin-centered, so a placement at a former volume's center
  lands the geometry in the same spot.
- `collision: "box"` auto-generates an axis-aligned collider per placement — no
  collider authored in the GLB. (`convex`, `trimesh`, `file`, and `none` are the
  other strategies.)
- Six pumps now share one mesh; three islands share another. Memory drops from
  nine prop meshes to two.
- Each asset is one swap point. An artist replaces `pump_greybox.glb` with a
  themed pump at the same dims and all six pumps instance the new art — authored
  once.

**To run this example:** author the two greybox assets with
`assets/props/make_pump_greybox.py` (run it in Blender; it writes
`pump_greybox.glb` and `pump_island_greybox.glb` into `assets/props/` at the
right dims), apply the spec change above, then **build and walk it** — the
placement import is in-engine, so confirm the pumps land and collide correctly
before relying on it. (Greybox stand-ins, so a wrong box is cheap to re-author.)

## The loop

1. `new_level --preset … --name …` → a functional greybox (modular on by default).
2. Shape the shell in the spec — rooms, openings, vertical links. Block out props:
   repeated as placements, unique as volumes.
3. Build → **walk the greybox** at player scale. Function locks here; the gates
   plus the walk catch the real bugs (overlap, missing collision, dead egress —
   the class offline checks miss, roughly two per walk).
4. Art-pass by swapping greybox modules for a theme kit — baked resolver or the
   live `.tscn` / `theme_swap` path. Author the kit **once per genre** and reuse
   it across every building of that genre.
5. Re-walk.

## One invariant and one convention

These aren't per-building decisions — adopt them once and stop thinking about them.

- **Invariant: collision and nav live on the greybox.** This isn't a choice you
  make; it's a property the tool enforces. A theme swap only changes visuals, so a
  walked greybox can't be broken by art — which is what lets you hand a level to an
  artist without worrying. It's the line everything else rests on.
- **Convention: keep a fixed width palette.** Pick a small set of standard opening
  widths once (for example doors always 0.9 or 1.2, garage 1.8, windows 1.2 or
  2.4) and draw every spec from it from then on. Then one themed module per width
  drops into every opening of that width across every building, and identical
  widths share one mesh. Author arbitrary widths instead and each one needs its
  own bespoke module.
