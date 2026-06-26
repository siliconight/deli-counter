# Changelog

**Deli Counter** — a spec-driven Blender level kit for Godot 4.

All notable changes to the kit. Bump `KIT_VERSION` in `version.py` with each
entry. See that file for the versioning convention.

## [0.34.0]
### Added — enterability gate (can a body actually get IN?)
- New `enterability.py` + a gate in `validate.py` / `check.py`: the entry-side
  sibling of the reachability gate. A shell with no opening a player fits through
  is a sealed box — it validates clean (rooms reachable from each other) yet
  can't be played because nobody gets inside. Nothing caught that before.
- GATE THE CLEAR-CUT CASE, WARN THE REST: HARD ERROR when there's no usable
  ground-level exterior entry at all (too small / too high a sill / only fixed
  windows). WARN when there's a way in but it's awkward — crouch-only,
  breach-only, vault-only, or a tight squeeze. Always prints a walk-to-verify
  note that swing/vault clearance can't be confirmed offline.
- Body-fit thresholds come from `docs/scale_guidelines.md` (passable width
  >= 0.7 m, comfortable >= 0.9 m; crouch >= 1.1 m, standing >= 1.8 m; a sill
  within 1.2 m is vault-reachable; a window counts as an entry only if it's
  vaultable or low). The scorecard now reports usable-entry counts.
- `gameplay.json` now emits `footprint: [x, y]` (metres), so a site assembler
  (Lot) can test approach space in front of each entry against neighbours.
  No schema change (output-only addition; `SCHEMA_VERSION` stays 1.8.0).

## [0.33.0]
### Changed — rarity now multi-entry aware + aligned to the updated Delco proposal
- **Every** opening (door / window / breach — not just breachable kinds) now
  carries the building's `rarity` + `rarity_color`. The proposal counts a door,
  window, or wall breach as a valid entry attempt, so any of them must resolve to
  the building's rarity. Windows were excluded in 0.32.0; that was wrong.
- Each opening and door-socket anchor now carries a `building` id, and
  `gameplay.json` emits a top-level `building_id` (= level name for a single
  build). So a building with several doors is unambiguous: any entry resolves to
  the same `building_id` + rarity, and the server keys `is_revealed` on it. This
  is what makes the "open its *first* door, reveal once, shared across the squad"
  flow land for multi-door buildings.
- Tier `epic` renamed to `very_rare`, and `legendary`'s colour name yellow ->
  gold (hex unchanged `#FFD700`), to match the proposal's server enum
  `COMMON / UNCOMMON / RARE / VERY_RARE / LEGENDARY`. Colours otherwise unchanged.
  `SCHEMA_VERSION` 1.7.0 -> 1.8.0 (enum value changed + `building_id` /
  `opening.building` added).
- Docs: `docs/RARITY.md` gains a multi-entry / one-building-one-rarity section
  and a baked-vs-server-rolled section (the proposal's per-run roll from the run
  seed is server code; the kit bakes a fixed rarity, good for handcrafted "named
  Legendary" buildings and testing — per-building eligibility + a mission-level
  rarity table are the authored hooks for rolling, offered not yet built).
  Contract doc + README updated.

## [0.32.0]
### Added — optional building rarity (for the networked-door reveal)
- A building can declare one `rarity` (`common` / `uncommon` / `rare` / `epic` /
  `legendary`). Off by default; specs that omit it are byte-identical to before.
- New `rarity.py` — the single canonical tier→colour table (white / green /
  blue / purple / yellow, the proposal's colours as genre-standard loot hues),
  exposing hex + Godot-ready `rgb`. One source of truth so the colour can't
  drift into hard-coded hex strings across game code.
- `gameplay.json` now emits `rarity` + `rarity_color` at the top level (the
  source of truth), and stamps the same colour onto every *breachable* opening
  (`door` / `garage` / `breach`; windows excluded). The `DOOR_SOCKET_*` /
  `BREACH_PANEL_*` anchors also carry the rarity as custom properties → glTF
  `extras` → Godot node metadata, so a networked door instanced at a socket pops
  the right colour with no lookup back to the building root.
- `new_level.py --rarity <tier>` stamps a generated level. `specs/rarity_demo.json`
  demonstrates it.
- Contract is the *value*, not the effect: the reveal (light/sound/HUD) and any
  rarity-driven enemy/loot budgets stay game code that reads this value — see the
  new `docs/RARITY.md` (with Godot wiring) and the updated
  `docs/GAMEPLAY_JSON_CONTRACT.md`. `SCHEMA_VERSION` → 1.7.0 (additive: a new
  optional top-level field + two optional opening fields; old specs still load).

## [0.31.1]
### Added — docs
- `docs/CUSTOMIZING.md`: how to take a level the last 20% without breaking
  determinism — the ".glb is disposable, iterate the spec" model, the fast
  watch+rebuild loop, and a decision tree for the rare detail the spec cannot
  express (kitbash part, Godot overlay layer, or a knowingly-hand-owned copy).
  README points to it from the iterating section. Docs only, no behavior change.

## [0.31.0]
### Added — authoritative surface-role metadata (from external pipeline review)
- The builder now records an authoritative role for every VISUAL mesh
  (floor / ceiling / wall / stair / ramp / ladder / prop) at creation time and
  emits it as `surface_roles` (node name → role) in `gameplay.json`. Downstream
  tools — Patina styling, the `--vertex-nuance` pass — should consume these
  labels instead of inferring floor/wall/ceiling from geometry, which is
  error-prone across Blender/glTF/world-axis conventions (it misclassified
  shelves as ceilings, slabs as walls). The builder knows what it placed; it now
  shares that knowledge instead of throwing it away.
- `--vertex-nuance` now uses the authoritative role for its base tint (falling
  back to a normal-based guess only for unroled meshes) — so the fix improves two
  consumers at once.
- `docs/GAMEPLAY_JSON_CONTRACT.md` — formally documents `gameplay.json` as the
  canonical companion contract (all fields, plus the new `surface_roles`), and
  states the marker-preservation requirement: a tool that re-emits the `.glb`
  must preserve marker Empties or document that consumers read marker placement
  from `gameplay.json` (which stays authoritative regardless). Addresses the
  review's "make gameplay.json the formal contract" and marker-drop findings on
  the Deli Counter side.

## [0.30.1]
### Changed — README brought current (docs only, no behavior change)
- The README had not been touched since 0.27.0 and was missing four releases of
  features. Updated to cover everything through 0.30.0:
  - Layout file list now lists all current modules (tactical, polybudget, guards,
    navigability, floorplan, presets, new_level, describe, meshlib_kit, etc.).
  - Quick start lists all 9 presets (was 4) and the current flags (--mode incl.
    survival, --no-audio, --vertex-nuance), and names the three co-equal on-ramps.
  - New sections: poly budget (intel), navigability (offline proxy + F4/F5
    navmesh check), floorplan intel maps, and an "Optional visual passes" section
    covering --vertex-nuance and the GridMap parts-kit.
- No code, schema, or builder changes. Output is byte-identical to 0.30.0.

## [0.30.0]
### Added — optional anti-flatness vertex-nuance pass
- `--vertex-nuance` (CLI flag) / `"vertex_nuance": true` (spec field): an opt-in,
  **visual-only** builder pass that makes a blockout read less like a flat CG
  box — for readability, not beauty. Off by default; the pure honest greybox
  stays the default output. Three geometry-derived (deterministic) effects:
  densify visual faces to ~grid edge length (gives vertex color resolution +
  tames affine-mapping swim), bevel hard edges ~1.5 cm (light catches them), and
  bake procedural vertex colors — fake AO in crevices, a height/grime gradient
  near the floor, and a per-surface floor/wall/ceiling base tint. No UVs, no
  textures, no hand-painting; the color ships in the `.glb`.
- COLLISION is never touched — the pass applies object scale into the mesh first
  (dodging the non-uniform-scale trap) then edits VISUAL meshes only. Markers and
  the gameplay.json are untouched.
- `godot/VERTEX_NUANCE.md` — what it does, and how to display it in Godot
  (StandardMaterial3D → Vertex Color → Use as Albedo). Pairs naturally with a
  PS1-style vertex-lit shader.
- Builder-side (Blender) code: offline-verified that it parses, the default path
  is byte-identical (no behavior change when off), the flag plumbs through schema
  → loader → builder, and the pass executes its full sequence. The actual beveled
  + colored geometry is walk-to-verify in Blender/Godot (can't render Blender in
  CI).

### Added — optional GridMap parts-kit MeshLibrary
- A standard, grid-aligned modular parts-kit (wall / half-wall / doorway /
  window / floor / pillar / counter / stair / crate) you can paint with in a
  Godot `GridMap` to hand-greybox a fresh layout. **Purely optional and
  additive — the baked `.glb` remains the primary, replication-free output;
  this changes nothing in the core pipeline.** It's a quick-sketch on-ramp that
  sits beside the spec-driven ones, not a replacement (a live GridMap is not the
  deterministic baked shell).
- `godot/addon/deli_counter/meshlib_kit.gd` — an `@tool` EditorScript that
  builds the MeshLibrary **in-engine** (via SurfaceTool + BoxShape3D, saved with
  ResourceSaver) so the mesh and collision data is always valid. Chosen over
  hand-packing a `.tres` after finding Godot itself can silently drop meshes on
  malformed library data (godot#85085); building in-engine sidesteps that.
  Editor-only, first run is in Godot.
- `meshlib_kit.py` — the offline half: the canonical kit manifest (module names,
  grid dimensions, collision) sized to the scale guidelines, kept in sync with
  the GDScript generator and fully verifiable without Blender/Godot. Run it for
  the kit catalog.
- `godot/MESHLIB_KIT.md` — how to generate and paint with the kit, and where it
  sits among the on-ramps. Delete both `meshlib_kit.*` files and nothing else
  changes.

## [0.29.1]
### Fixed — switchback stairs built overlapping legs (unwalkable)
- Switchback stairs generated every flight at the SAME x, so an up-leg and the
  next (reversed) leg occupied the same footprint — their steps interpenetrated
  into smeared, unclimbable geometry. Found by walking corner_deli in Godot
  (the geometry validated fine offline; only physical overlap breaks it, which
  only a walk catches). Fix: reversed legs now offset sideways by the stair
  width into a parallel run, with a landing bridging the two runs at each turn.
  Affects every preset using switchback stairs (corner_deli, compound, hospital,
  casino_tower, suburban_safehouse, rowhome). Rebuild GLBs to get the fix.

### Fixed — ladders had no collision (walk-through ghost)
- Ladder rails and rungs were emitted to the VISUAL collection only, never as
  collision — despite a code comment claiming otherwise — so the player walked
  straight through every ladder. Also found by walking corner_deli. Fix: rails
  and rungs now generate `-convcolonly` collision so the ladder is a solid
  physical object. Climbing remains a gameplay mechanic the game wires to the
  `LADDER_` marker (the shell provides solid geometry + the climb anchor; the
  game moves the player up the volume).

## [0.29.0]
### Added — tighter spec→walk iteration loop (roadmap I-2)
- `build.py --watch`: polls `specs/` mtimes (stdlib only, no watchdog dep) and
  rebuilds a spec the moment you save it; Godot auto-reimports the changed
  `.glb`. Pass a spec path to watch just that one, or none to watch all. Seeds
  mtimes without an initial build, so it only reacts to changes. (Watch loop
  logic verified offline with a stubbed builder.)
- Editor dock **"↻ Rebuild last level"** button: re-runs reimport → build scene
  → play on the last-picked `.glb` with no file picker — the one-click other
  half of the `--watch` loop. Forces `scan()` + `reimport_files()` first so the
  fresh geometry replaces Godot's cached import (avoids replaying stale
  geometry, and sidesteps the UID-cache reload quirk). *Editor `@tool` GDScript
  — first run is in-engine; drafted against existing plugin patterns.*
- **Import-step audit** in `godot/IMPORT_GUIDE.md`: an honest table of every
  step (collision, markers, transforms, stairs, UID reload…) marked Automatic /
  one-time setup / manual. Net: the normal plugin loop has no manual steps; the
  only manual touch is the rare UID-cache reload (a Godot quirk, one-click menu
  fix), now documented rather than tribal knowledge.

## [0.28.0]
### Added — top-down floorplan intel map (roadmap I-1)
- `floorplan.py` (bpy-free): renders an annotated top-down SVG per story —
  rooms as labelled, role-colored boxes; exterior + partition walls with gaps
  at doorways/openings; gameplay markers (spawns, objectives, loot, cover,
  cameras…) as icons; legend + north arrow. Pure-Python SVG strings, no
  Pillow/cairo/matplotlib — offline, deterministic, dependency-free, runs
  without Blender. Canvas auto-widens to show markers outside the footprint
  (e.g. attacker spawns breaching from outside).
- Addresses the review's sharpest finding: the tool computed rich spatial intel
  and produced *zero visual output*. Numbers in a table don't communicate a
  space; a designer can now see the layout and judge feel.
- Wired into `validate.py` (and thus `check.py`/CI): every validated spec writes
  its per-story SVGs to `build/floorplans/`. Also runnable standalone:
  `python floorplan.py specs/<name>.json <outdir>`.
- This is the read-half; the planned tactical overlays (graph edges,
  chokepoints, single-route-objective flags in red) layer on in a later pass,
  and a 2D authoring surface (roadmap I-6) would be the write-half companion.

## [0.27.0]
### Added — navigability checks ("can AI enemies path to the player?")
Two layers, because the honest answer needs a real navmesh but a cheap offline
pre-filter catches the gross failures first.
- **Offline proxy** (`navigability.py`, in `validate.py`/CI): flags floor-level
  doorways narrower than a nav agent can pass (~1.1 m for Godot's default 0.5 m
  radius) and backstops isolated-room detection. Room-graph resolution — a
  pre-filter, not the truth; reported as warnings (navigation is a gameplay
  concern), with the standing reminder that the authoritative check is a real
  navmesh bake. Well-calibrated: only the presets with intentionally tight
  (1.0 m) residential/shop doors flag; most pass clean.
- **Godot navmesh check** (`godot/template/level_test.gd` F5 + `NAVMESH_CHECK.md`):
  the authoritative, capsule-accurate version, to run when you walk a level.
  F4 bakes the navmesh; **F5** then queries a path from the player to every
  gameplay marker and reports which an agent can actually reach ("12/12
  reachable" or names the off-navmesh / no-path anchors). If an enemy can path
  to an anchor, it can path back to shoot the player. Catches what the offline
  proxy can't — slivers, stair-bake gaps, sub-room holes.

This stays on the right side of the model/gameplay line: the tool doesn't run
AI, but it verifies the shell is *navigable* so your AI can. Navigability is
intel + a real-navmesh tool; only true unreachability (already a hard gate via
tactical reachability) fails the build.

## [0.26.0]
### Changed — the acoustic / gool audio bridge is explicitly optional
- Made clear (and easy) that the acoustic-materials audio bridge is opt-in, not
  required. A spec with no `materials` block already built fine; now:
  - `new_level.py --no-audio` strips the acoustic palette + all `material`
    references from any preset, so the spec carries zero audio data (the
    `gameplay.json` `surfaces` block comes out empty). Geometry, collision, and
    markers are identical with or without it.
  - The README's acoustic section now leads with "this is entirely optional" —
    a game not using an acoustic audio engine ignores it, and the tool never
    requires the bridge.
- No behavior change for the audio path: presets still include a palette by
  default (harmless if unused), and games that want gool integration get the
  same surfaces map as before.

## [0.25.1]
### Changed — docs
- Clarified that the three on-ramps (describe.py, new_level.py --preset, hand-authored JSON) are co-equal and independent; describe.py is an optional convenience layer, not a required first step. Reframed GETTING_STARTED + noted it in describe.py itself.

## [0.25.0]
### Added — `describe.py`: guided interview (describe a building, get a level)
- The on-ramp between "I want a two-story bank with a vault" and
  `--preset bank --floors 2`. Fully offline, no AI: a short series of questions
  (playstyle → setting → size → params) whose answers map deterministically to
  the best-fit preset via a scoring decision tree, then generate + validate.
- It's a *recommender*, not a generator: it always lands on one of the nine
  proven presets (validated, budgeted, guarded) — never invents geometry. It
  explains *why* it picked a preset, shows runner-up options to redirect to,
  and lets you override the auto-chosen parameters. Falls back to a versatile
  default when given no signal.
- Verified the routing: "small shop to rob" → corner_deli, "co-op horde in a
  hospital" → hospital, "warehouse shootout" → warehouse, "raid a precinct" →
  police_station, etc. `python describe.py`.

## [0.24.0]
### Added — offline guards (encode judgment that used to be manual)
- `guards.py` + wired into `validate.py`/`check.py` (CI). Two hard gates that
  used to live in a human's head:
  - **IP-name guard** (repo integrity): scans every author-controlled string in
    a spec — name, room ids/roles, marker ids/types/meta, zone/objective/loot
    ids, opening tags — for brand/inspiration terms (delco, payday, scarface,
    valve, l4d, etc.). A match **fails the build**. Boundary-aware matching
    catches brand-in-identifier (`payday_vault`, `delco_x`) while skipping
    embedded-in-a-word false positives (`besieged_corridor` is clean). An
    `IP_ALLOWLIST` blesses legitimate strings that contain a flagged substring;
    the error message names the exact string to allowlist.
  - **Step-rise budget** (model integrity): a stair whose per-step rise exceeds
    the 0.5 m climb budget is physically unclimbable — a broken model — so it
    **fails the build** (warns as it approaches 0.4 m). Generated stairs are
    ~0.18 m and pass with wide margin; this catches hand-authored specs with a
    large `step_rise` or tiny `n_steps`.
- These make the tool more self-sufficient: the IP grep and the "can the player
  climb this?" check now run automatically in CI instead of relying on someone
  remembering. Reachability, step-rise, and IP are the hard gates; everything
  else (path metrics, poly budget) stays informational.

## [0.23.0]
### Added — warehouse, suburban_safehouse, rowhome, casino_tower presets
- Completes the single-building preset library (9 total): every roadmap level
  the tool can honestly build now has a recipe. The two outdoor levels
  (strip_mall, flooded_underpass) are intentionally NOT presets — they need the
  outdoor primitive the tool doesn't have, not a building pretending to be one.
- **warehouse** (L6): assault sandbox — big open single-floor shed, loading
  docks, sparse crate/rack cover for long sightlines, one fortifiable office
  (two access paths). Heist mode adds an office safe + goods loot.
- **suburban_safehouse** (L2): assault, compact multi-story house with a
  basement (default), central stair, attic objective — tight vertical clears.
- **rowhome**: assault, narrow deep 3-floor terrace with solid party walls and
  a single rear stair — stacked front-to-back clears. Heist supported.
- **casino_tower** (L9): hybrid, default heist — open gaming floor, cashier
  cage + count room upstairs, basement vault; cage/vault objectives, loot,
  extraction. Assault mode secures the vault instead.
- All four validate clean in both modes (caught and fixed a real office-
  connectivity bug in warehouse during authoring — the validator's >=2-access
  rule doing its job).

## [0.22.0]
### Added — hospital preset (first survival-first preset)
- `hospital` recipe (roadmap L8): a multi-story hospital built survival-first —
  team starts in the ground-floor lobby (safe_room), fights up through wards
  floor by floor via two stairwells, reaches a rooftop helipad holdout (finale)
  with a helicopter extraction. Horde spawns spread across every floor plus an
  elevator-shaft vertical channel. Params: `mode` (survival default; assault
  supported — rooftop becomes a capture objective, horde dropped), `floors`
  (2-4, default 3), `scale_ref`. Proves survival mode translates into
  *generated* geometry, not just hand-authored specs: the default generates
  with finale reachable, a 2-hop / 4-route run, 7 horde spawns.

### Fixed — new_level.py overrode preset defaults
- The CLI passed `--mode assault` and `--floors 2` unconditionally, silently
  forcing *every* preset to assault/2-floor regardless of its own defaults
  (so hospital came out assault, corner_deli/compound lost their intended
  mode/floors when generated via CLI). Now only user-specified args are passed;
  each preset's own defaults stand otherwise. `--mode` also gains `survival`,
  and a `--basement` flag complements `--no-basement`.

## [0.21.0]
### Added — offline polygon-budget estimate
- `polybudget.py`: a pure-Python triangle-count estimator that predicts a
  shell's poly count from the spec *without* running Blender (the geometry is
  deterministic, so it can be checked offline in CI). Reports total tris and
  per-piece distribution, surfaced in `validate.py` output.
- Checks against the **Environment/Module budget** (target 50-500, cap 1,000
  tris per piece). Intel, not judgment — same principle as the path metrics:
  the tool makes models, an artist may exceed a target deliberately. It only
  *notes* (never errors on) pieces over the hard cap, and flags imported
  kitbash assets whose tri count can't be estimated offline (verify those in
  Blender).
- Calibrated against a real exported GLB (corner_deli: estimate within ~90% of
  actual visual tris). Reports the shippable VISUAL budget; collision proxies
  are separate and not counted against the Environment budget.
- Finding: the generated blockout shells are light — whole buildings land at
  ~150-2,500 tris total, no single piece near the 1,000 cap. The structural
  shell is a lightweight canvas the art team builds detail onto.

## [0.20.0]
### Added — tactical path metrics (intel, not judgment)
- `tactical.py` gains offline room-graph path analysis, reported in every
  scorecard: **route count** (node-disjoint paths to each objective/finale, via
  max-flow on a node-split graph — a flanking measure), **shortest run length**
  (hops), and **chokepoints** (rooms every route is forced through). Works
  across all three modes; no engine needed, gates CI like the rest.
- Framed explicitly as **information for the gameplay layer, not the tool's
  opinion.** Deli Counter makes models, not gameplay — a single-route vault or
  a chokepoint may be the intended design. These metrics never warn or fail.
  The *only* hard path gate remains **reachability**: an unreachable
  objective/finale is a broken model and fails the build; everything past "can
  you get there at all" is intel the gameplay engineer interprets.
- Verified the route counter against canonical graphs (linear=1, diamond=2,
  double-corridor=2) and fixed two max-flow node-capacity bugs found in
  testing before they could report confidently-wrong numbers.

### Note
- 0.19.1 was a docs-only bump (README multiplayer-shell thesis + procedural
  aspiration note).

## [0.19.0]
### Added — survival mode (third tactical default), schema 1.6.0
- New `mode: survival` — co-op PvE horde defense as a directional run through
  the building: team starts in a `safe_room` zone, moves through the level, and
  reaches a `finale` holdout to survive a final wave (optional `extraction` for
  rescue/escape). New marker types `survivor_spawn` / `horde_spawn` / `rescue`
  (freeform, no schema change); new zone kinds `safe_room` / `finale`; room
  roles `safe_room` / `finale` / `route_node` read as hints.
- Validation (`tactical.py` `_analyze_survival`) checks the run is playable: a
  start and a finale exist, **the finale is reachable from the start through the
  building** (hard error if not — the survival analogue of heist objective
  reachability), and horde spawns apply pressure (warns if missing/sparse). New
  `[survival]` scorecard. Verified: a reachable run passes; removing the stair
  to the holdout hard-fails with "finale holdout not reachable from the start".
- Schema 1.6.0: `mode` enum gains `survival`; zone `kind` enum gains
  `safe_room` / `finale`. Backward-compatible — all existing assault/heist
  specs validate unchanged.
- `specs/survival_demo.json`: a worked 2-story survival example (lobby start →
  roof holdout, horde spawns along the route).
- Scoped to single-building runs. An outdoor path-through-a-town survival map is
  the same open-space limitation the tool has for outdoor levels generally.

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
