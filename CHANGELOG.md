# Changelog

**Deli Counter** — a spec-driven Blender level kit for Godot 4.

All notable changes to the kit. Bump `KIT_VERSION` in `version.py` with each
entry. See that file for the versioning convention.

## [0.18.2]
### Fixed — editor plugin: level now actually appears in the test scene
- The plugin's "Build test scene" / "Set up & Play" packed the harness but
  **dropped the instanced level**, leaving only the bare harness (ground +
  light + player, no building) — found on first real in-engine run. Cause: the
  level node's `owner` was never set, so `PackedScene.pack()` discarded it.
  Fix: set `level.owner = root` on the instanced level node (and do NOT recurse
  owner-setting into its children — that's the fragile pattern that drops
  instanced-scene nodes; ref Godot issues #32179/#90823). Removed the now-unused
  `_set_owner_recursive` helper. Plugin version → 0.18.2.

## [0.18.1]
### Docs — stairs and player traversal
- `godot/README.md` gains a "Stairs and player traversal" section: documents
  that generated steps rise ~0.18 m (well under a 0.5 m step-up budget, so any
  reasonable step-up algorithm clears them); points to the robust
  `body_test_motion` stair-step technique (Godot Stair-Step Demo, asset 2481,
  MIT — credits Majikayo Games / Myria666) for production controllers vs. the
  harness's lightweight raycast probe; and notes the Jolt-vs-default physics
  caveat (default physics can mis-detect a flat floor as a step / jitter).
- `template/player.gd` comment now points to that section. No behavior change —
  the harness step-up is unchanged and still clears generated stairs.

## [0.18.0]
### Added — compound preset + final_stand example
- `compound` recipe: a multi-story assault compound with a central atrium (a
  slab hole punched up through the upper floors as a vertical sightline), two
  switchback stairs wrapping the core, and an objective room on the top floor —
  a boss suite to clear in assault mode, or a penthouse vault to crack in heist
  mode. Parameterized by `mode` (assault default; heist supported), `floors`
  (2 or 3, default 3 — the atrium, stairs, upper rooms, and objective all adapt
  to the floor count), and `scale_ref`. `python new_level.py --preset compound
  --name my_compound [--mode heist] [--floors 2]`.
- `specs/final_stand.json`: a worked 3-story boss-compound example (assault),
  the hand-authored spec the preset was derived from — richer per-floor detail
  than the generated version. Maps to the roadmap's climactic level.

## [0.17.0]
### Added — corner_deli preset
- `corner_deli` recipe: a 2-story deli/market over a basement, heist-first.
  Ground floor is customer floor + deli counter, market aisles, kitchen, and a
  stockroom/loading bay; upstairs are a manager office, a back apartment, and
  a server room; the basement holds a vault and cold storage. Three vertical
  routes (a switchback stair spanning basement→roof, a roof ladder, and a
  floor hole). Parameterized by `mode` (heist default; assault supported),
  `basement`, and `scale_ref` — floors fixed at 2. Built from a hand-authored
  spec that validated and built clean; the preset reproduces that geometry and
  flexes the basement + mode. `python new_level.py --preset corner_deli
  --name my_deli [--mode assault] [--no-basement]`.

## [0.16.2]
### Added — keep CATALOG.md from going stale
- `new_level.py` now auto-refreshes `specs/CATALOG.md` after writing a spec, so
  generating a level can't leave the catalog out of sync (the most common CI
  failure).
- `hooks/pre-commit` + `install_hooks.py`: a pre-commit hook that refreshes the
  catalog (staging it if changed) and runs the `check.py` gate before a commit
  lands, catching stale catalogs and broken specs — including hand-edited ones
  — before they reach CI. Install once per clone with `python install_hooks.py`;
  bypass a single commit with `git commit --no-verify`.

## [0.16.1]
### Changed — docs
- Refreshed the README for the plugin workflow: the "Import into Godot 4"
  section now leads with the editor plugin (install once → pick `.glb` → Set
  up & Play) and demotes the manual import-and-wire steps to "under the hood."
  Documented the walkable test harness, updated the pipeline diagram, layout
  tree, and iterate loop, and added an honesty note that the plugin/harness
  are the newest pieces (import pipeline confirmed in-engine; plugin one-click
  flow written against the 4.x editor API, smoke-test in your engine).

## [0.16.0]
### Added — Godot editor plugin (kills the per-level file shuffle)
- `godot/addon/deli_counter/`: a self-contained Godot editor plugin. Install
  once (copy to `res://addons/deli_counter/`, enable in Project Settings →
  Plugins) and a **Deli Counter** dock appears. Pick a level `.glb`, click
  **Set up & Play ▶**, and it assigns the post-import marker script + reimports
  (no Import-tab dance), builds a walkable test scene under
  `res://deli_counter_tests/` with the level instanced in the harness, opens
  it, and runs it. Numbered buttons also expose the steps individually.
- The addon bundles the post-import script, `deli_level.gd`, and the test
  harness `template/`, so install is one folder. Supersedes the manual
  "copy the template + set the import script by hand" workflow.
- `plugin.cfg` author is "Deli Counter" (the tool names itself, matching how
  gool authors itself) — no brand reference.

## [0.15.1]
### Fixed — stair traversal (found by walking the police station in Godot)
- The stair slab-hole was centered on the stairwell base and sized to the
  stair footprint, so it stopped right at the top step — a player's body would
  clip the slab lip cresting the top and get stuck "near the top." The hole now
  extends ~0.8 m past the top landing in the flight's travel direction and is
  wider (player radius + margin), so you can walk off onto the upper floor.
- Test-harness player (`godot/template/player.gd`) gained stair-stepping:
  `CharacterBody3D` has no built-in step handling and stopped dead at every
  step edge. It now snaps up onto anything shorter than `max_step_height`
  (0.4 m default). Also added dedicated `move_*` input actions with a fallback
  to arrow keys, and the README documents the four WASD bindings to add.

## [0.15.0]
### Added — police_station preset (roadmap Level 7)
- `police_station` recipe: a dense two-story precinct + roof access. Ground
  floor is public lobby + front desk, holding cells, booking, and a garage
  bay; upstairs are detective offices, interrogation, and a **reinforced
  armory** as the objective. Exercises every vertical primitive at once — a
  switchback stairwell (main route), a roof ladder + hatch (flanking entry),
  and a floor hole over the armory (top-down pressure). Breach-vs-reinforced:
  soft interior walls breach, the armory door is reinforced. `assault` and
  `heist` modes both validate; heist emits an armory-raid loot loop with the
  garage bay as extraction.
- `python new_level.py --preset police_station --name my_precinct [--mode heist]`.

## [0.14.0]
### Added — Godot level test harness (roadmap #5)
- `godot/template/`: a drop-in test scene for walking a generated level at
  player scale. `level_test.tscn` (root + ground + light + environment + HUD),
  `player.gd` (CharacterBody3D FPS controller, 1.8 m capsule / 1.6 m eye, sized
  to the scale guidelines), and `level_test.gd` (loads the level, respawns at
  the first spawn marker, F4 bakes a NavigationMesh, F3 toggles scale proxies).
- Collision-view honesty: Godot's runtime collision toggle is unreliable, so
  the harness uses a startup `show_collision_shapes` export and points to the
  editor's Debug → Visible Collision Shapes menu instead of shipping a flaky
  hotkey.
- `godot/template/README.md` with the per-level workflow and a "what to check"
  scale/playability pass.

## [0.13.1]
### Fixed — post-import marker placement (found during first Godot import)
- The post-import script read each marker's `global_transform` while mutating
  the scene tree, which threw `!is_inside_tree()` errors and returned identity
  — markers converted successfully but could snap to the origin instead of
  their real positions. Transforms are now captured up front, before any node
  is reparented or freed, so converted Marker3D nodes land where the spec put
  them. Confirmed: first real Godot import converts all markers; collision
  StaticBody3D/CollisionShape3D auto-generate from the suffixes (Checkpoints 2
  and 3 pass).

## [0.13.0]
### Godot import — hardened the pipeline for first real-engine use
- Fixed the post-import script's node-owner handling, the known
  `EditorScenePostImport` gotcha where converted nodes are silently dropped
  from the saved scene unless their `owner` is the returned scene root. Owner
  is now set to the root (passed in explicitly) *after* `add_child`, and
  recursively on any instanced scene's children. Removed the fragile
  `_scene_root` tree-walk.
- `godot/IMPORT_GUIDE.md`: a step-by-step import procedure with verification
  checkpoints (geometry+collision import, then the marker-conversion reimport,
  then group checks, then a walkable greybox) so the first Godot import is a
  checklist, not guesswork.
- `build.py` Blender auto-detect now covers 4.3/4.4/4.5 and the Steam install
  path, not just 4.1/4.2.

## [0.12.0]
### Added — preset recipes (walk-up authoring)
- `presets.py`: parameterized recipe generators that emit a complete, playable
  spec (tactical layer, materials, vertical, spawns) — not just a shell. Pure
  Python, no Blender. First recipe: **bank** (glass-front lobby + teller line,
  manager office, security room, basement vault objective reached by a stair),
  parameterized by `mode`, `floors`, `basement`, `scale_ref`. In `heist` mode
  it emits the full heist loop (objectives, loot, extraction/secure zones,
  crew/responder spawns); in `assault` it uses the room-objective layout.
- `new_level.py`: CLI walk-up entry point —
  `python new_level.py --preset bank --name my_bank [--mode heist] [--floors 3]
  [--no-basement] [--scale-ref]`. Generates `specs/<name>.json`, validates it
  immediately, and prints the build command. `--list` shows available recipes.
- Recipe registry is extensible: corner_store, rowhome, warehouse,
  police_station, and safehouse will follow the bank's structure.

## [0.11.0]
### Added — scale-reference proxies
- `scale_ref` spec flag (default off). When on, the build drops a 1.8 m
  human-proxy capsule (0.4 m radius, per the scale guidelines) at every spawn
  marker into a separate `SCALE_REF` collection — a one-glance check in
  Blender that the level is sized for a human player. Proxies are named after
  their spawn (`SCALEREF_ATTACKER_SPAWN_A`, …); if a spec has no spawns, one
  is placed at the origin.
- `SCALE_REF` stays visible in the viewport for inspection but is excluded
  from every export format (.glb/.gltf/.obj), so the proxies never leak into
  the shipped model.

## [0.10.1]
### Fixed
- `_run_in_blender.py` manual run (Scripting workspace) is now foolproof:
  an explicit `PKG_DIR` config (since Blender's text editor can't always
  resolve `__file__`), a clear import-failure message pointing at it, and
  leaving `OUT_PATH` empty now builds **into the viewport** for inspection
  instead of silently doing nothing. Headless `build.py` path unchanged.
- Replaced deprecated `datetime.utcnow()` in the manifest writer.

## [0.10.0]
### Added — full vertical traversal vocabulary
- `ladders`: vertical climb between stories (rails + rungs, cuts the slab,
  emits a `LADDER_*` marker). Pairs with hatches.
- `ramps`: inclined walkable slab between heights; slope derived from
  rise/run, with a `max_slope_deg` walkable ceiling.
- `vault_ledges`: waist-height ledge to vault over within a floor (tagged
  `VAULTLEDGE_*`); takes a `material`.
- Ladders and ramps count as vertical access and connect rooms across stories
  in the reachability graph, same as stairs.
- `validate.py` warns when a ramp's slope exceeds its walkable max (too steep
  → use stairs or a longer run).
### Fixed
- Stair step count now derives from floor height and a target `step_rise`
  (default 0.2 m, game-feel; overridable, or set `n_steps` explicitly), so
  step rise stays consistent across floor heights instead of drifting with a
  hardcoded 12 steps. Dimensions follow the scale guidelines (exaggerated
  defaults, per-element override). Schema 1.5.0.

## [0.9.0]
### Added
- `docs/scale_guidelines.md`: meter-based level-size targets for blockouts —
  player scale, grid/structural sizes, and per-mode building/room/route
  dimensions (assault, heist, and a co-op-route style), plus a recommended
  first-prototype canvas (96×96 m, 60×60 m building, 3 floors) and acceptance
  criteria. The structural half of the criteria is what `validate.py` already
  enforces; the in-engine half (navmesh/AI/framerate) is the Godot check.

## [0.8.1]
### Fixed
- Room-connectivity graph sampled each partition only at its midpoint, so a
  long interior wall bordering more than one room recorded just one of those
  connections. It now samples at each opening's actual position along the
  wall, so every doorway links whatever rooms flank it. Fixes false
  "objective room has 1 access path" errors on realistic layouts.
### Added
- Example spec `stop_n_go.json`: a gas-station convenience store (assault),
  built from researched retail-layout conventions — glass storefront,
  register counter mid-floor, aisle shelving, back-of-house stockroom +
  walk-in cooler objective, rear service exit, breachable cooler panel.

## [0.8.0]
### Added — acoustic material palette (audio-engine bridge)
- `materials` palette: named acoustic materials each mapping to an audio
  material enum (Default/Air/Glass/Wood/Drywall/Concrete/Metal/Curtain/
  Foliage) and/or explicit `absorption`/`damping` floats (0..1).
- Surfaces reference a material by id: `material` field on `ext_walls`,
  `partitions`, and `volumes`, plus a spec-level `default_material` fallback.
  Palette + inline override.
- The build writes a `surfaces` map into `<name>.gameplay.json` — collision
  node name → resolved acoustic material — so the game's audio raycaster can
  read the hit body's name and hand the right material to the audio engine's
  geometry-query seam. **No visual PBR is baked** (texturing happens in the
  engine); this is the acoustic side only.
- `validate.py` checks every `material` reference (and `default_material`)
  resolves to a defined palette entry.
- `rowhouse_raid.json` updated with a 3-material palette (brick/drywall/glass)
  as a worked example. Schema 1.4.0.

## [0.7.0]
### Added — second tactical mode: heist (PvE crew play)
- `mode` field on the spec: `"assault"` (default, the existing
  attacker/defender breach model) or `"heist"` (PvE crew objectives + loot +
  extraction). Existing specs default to assault — fully back-compatible.
- Heist grammar: `objectives` (independent, completable in any order, with
  `kind`/`required`/`duration`), `loot` (spawns with `value`/`bags`/`kind`
  for a loot economy), and `zones` (`extraction` / `secure` / `drop`
  volumetric regions). Spawns can carry a `phase` tag (stealth/alarm/loud/…)
  in their `meta` — the phase state machine itself lives in game code.
- Emitted as markers (`OBJECTIVE_*`, `LOOT_*`, `EXTRACTION_ZONE_*`,
  `SECURE_ZONE_*`) and captured in `<name>.gameplay.json` (now includes
  `mode` and the heist sections).
- `tactical.py` branches on mode: heist validation checks extraction exists,
  crew entry exists, required objectives present, loot is deliverable, and
  objectives are reachable — instead of the assault breach rules. Scorecard
  is mode-specific (heist shows objectives/loot value/bags/phases).
- Fixed: room-connectivity graph now uses the actual `stairs` section (not
  just `vertical_links`) so multi-story reachability is correct. Improves
  assault validation too.
- New example spec `harbor_score.json` (heist: drill/hack objectives, loot
  worth 900k across 8 bags, secure + extraction zones, phased spawns).
- Schema 1.3.0.

## [0.6.0]
### Added — Godot integration (closes the compiler → playable loop)
- `godot/deli_counter_postimport.gd`: an `EditorScenePostImport` hook that
  runs at import time and converts baked marker nodes into game nodes —
  spawns, objectives, camera/door sockets, cover, hatches, and NAV_REGIONs
  become `Marker3D` nodes in gameplay groups (or instances of your own scenes
  via the `SCENE_FOR_TAG` map). Breach panels are tagged with metadata.
  Reads the companion `<name>.gameplay.json` automatically.
- `godot/deli_level.gd` (`class_name DeliLevel`): runtime helper to query the
  level (attacker/defender spawns, objectives, cover, breach panels) and a
  `breach()` call that frees a soft panel and optionally spawns a replacement.
- `godot/README.md`: install, import-hook setup, customization, runtime usage.
- CI: `.github/workflows/check.yml` runs `check.py` on push/PR to main.
- `package.py`: builds versioned `dist/deli_counter-<version>.zip` + `VERSION`
  stamp. `dist/` gitignored (attach to GitHub Releases).

## [0.5.0]
### Added — tactical layer (turns levels into playable level packages)
- **Tactical grammar** (all optional; plain building specs still build):
  `rooms` (named spaces with bounds/role/combat_range/fortifiable),
  `vertical_links` (stair / floor_hole / hatch with designed roles), and
  `markers` (spawns, objectives, cover, camera/door sockets, etc.).
- **Tactical openings**: `door`/`window`/`breach`/`garage` now carry optional
  `tag`, `breach_class`, `material`, `vaultable`, `reinforceable`.
- **Gameplay markers delivered both ways**: named Empties baked into the GLB
  (a `MARKERS` collection — `ATTACKER_SPAWN_A`, `OBJECTIVE_A`, `NAV_REGION_*`,
  `DOOR_SOCKET_*`, `BREACH_PANEL_*`, `HATCH_*`) **and** a companion
  `<name>.gameplay.json` so Godot can read meaning without parsing names.
- **Graph-based tactical validation** in `validate.py` via new `tactical.py`
  (no Blender): >=2 attacker entries, every floor has vertical access, every
  objective room has >=2 access paths, no unreachable rooms, min opening
  width, breach metadata present, spawns-vs-objectives. Hard-fails the gate.
- **Tactical scorecard** printed per level and shown in `CATALOG.md`.
- New example spec `rowhouse_raid.json` (basement objective, vertical angle,
  breachable walls, switchback rotation) exercising the full grammar.
- Schema 1.2.0. Sightline analysis + in-engine nav smoke test intentionally
  deferred to a Godot-side Phase 2 (need real geometry raycasts).

## [0.4.1]
### Changed
- Named the tool **Deli Counter**.

## [0.4.0]
### Added
- **Kitbashing**: levels can compose from external model assets. New spec
  sections `assets` (a library of source models, referenced by stable `id`)
  and `placements` (instances with position, rotation, scale). Assets are
  vendored under `assets/` and committed (schema 1.1.0).
- Asset formats: `.glb` (preferred, self-contained), `.obj` (+ `.mtl`),
  `.blend` (appended; optional `blend_object` to pick one object).
- Per-asset / per-placement collision strategy: `convex` (auto hull,
  default), `box` (AABB), `file` (separate low-poly mesh), `trimesh`
  (static), `none`. Imported geometry is baked into the monolithic level
  with its collision proxy tagged for Godot like generated geometry.
- `validate.py` now checks placements reference defined asset ids and that
  vendored asset files (and collision files) exist.
- `assets/README.md` documents the vendoring convention; `assets/props/`
  ships an example `crate.obj`. New example spec `kitbash_demo.json`.

## [0.3.0]
### Added
- Multi-format export: `glb` (engine-ready), `gltf` (text + .bin, web/AR/VR),
  `obj` (+ .mtl, static archival format that diffs well in source control).
  CLI: `python build.py specs/bank.json -f glb,obj`.
- Build manifests: each build writes `<name>.manifest.json` recording kit
  version, schema version, spec hash, timestamp, and output formats — so any
  model in source control traces back to the exact spec + code.
- `catalog.py`: auto-generates `specs/CATALOG.md` documenting every level.
- `check.py`: single gate (validate + catalog freshness) for CI/pre-commit.
- `version.py`: single source of truth for kit + schema version.
- Second example spec: `warehouse.json`.

## [0.2.0]
### Changed
- Reworked into a reproducible package under `levels/`.
- Specs are now JSON data (`specs/*.json`) validated against
  `schema/level.schema.json`, not Python files.
- Split pure-Python `spec_types.py` from the bpy-dependent builder so
  validation runs without Blender.
### Added
- Headless CLI (`build.py`) + manual Blender fallback (`_run_in_blender.py`).
- `validate.py` for fast pre-build checking.

## [0.1.0]
### Added
- Initial spec-driven generator (`deli_counter.py`): LevelSpec dataclasses +
  builder producing dual VISUAL/COLLISION meshes with Godot glTF collision
  naming. Worked example: `bank`.
