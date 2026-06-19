# Changelog

**Deli Counter** — a spec-driven Blender level kit for Godot 4.

All notable changes to the kit. Bump `KIT_VERSION` in `version.py` with each
entry. See that file for the versioning convention.

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
