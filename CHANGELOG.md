# Changelog

**Deli Counter** — a spec-driven Blender level kit for Godot 4.

All notable changes to the kit. Bump `KIT_VERSION` in `version.py` with each
entry. See that file for the versioning convention.

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
