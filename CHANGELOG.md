## [0.69.0] - Semantic ladder connections (ladder spec Phase 1)

- First cut of the ladder placement spec (new doc folded in:
  docs/deli_counter_ladder_placement_spec.md). A ladder stops being decoration
  on a blank wall and becomes a SYSTEM: a specialized connection between two
  usable surfaces with a role, a safe lower approach, a resolved top
  transition, a preserved climbing volume, and a route at both ends.
- New pure analyzer `ladder.py` in the validate chain (after stairwell). The
  governing invariant is absolute (spec s2): a ladder is NEVER counted as
  ordinary required egress -- counts_as_primary_egress and
  counts_as_public_circulation are always false, and only the two escape roles
  (legacy_secondary_escape / fire_escape_termination) may opt into
  counts_as_secondary_escape.
- Ladder gains semantic identity (schema 1.17.0 -> 1.18.0, all additive):
  id, role (8 classifications from spec s2/s6), ladder_type, placement_mode,
  lower_surface / upper_surface (room id or a derived token: roof / grade /
  site / pit_N), direction, access_class, counts_as_secondary_escape,
  transition, fall_protection, access_control, fire_escape_id, and meta.
- Phase-1 review checks (severity per spec s15): LADDER_NO_ROLE (HARD --
  Rule 1, a roleless ladder is not generated, unlike an unclassified stair
  which is only intel), LADDER_NO_LOWER_SURFACE / LADDER_NO_UPPER_SURFACE and
  LADDER_TO_NOWHERE (Rule 2 -- two real traversable surfaces),
  LADDER_ROUTE_DISCONNECTED (onward route at both ends),
  LADDER_CLIMB_VOLUME_BLOCKED (Rule 8 -- props/equipment in the climb
  envelope), LADDER_DOOR_CONFLICT / LADDER_WINDOW_CONFLICT (Rule 9),
  PARAPET_CROSSOVER_MISSING (Rule 6), LADDER_LONG_CLIMB_UNPROTECTED (Rule 11 --
  climbs over 7.3 m need a fall-protection profile), LADDER_INVALID_EGRESS
  (s2 invariant), FIRE_ESCAPE_LADDER_ORPHANED (Rule 14), plus intel warnings
  (LADDER_SECURITY_EXPOSURE, LADDER_LOW_GAMEPLAY_CLEARANCE,
  LADDER_EXCESSIVE_HEIGHT, LADDER_NO_VISUAL_DESTINATION,
  LEGACY_FIRE_ESCAPE_PROFILE).
- gameplay.json gains a `ladders` section (spec s14): identity, connected
  surfaces, mount/upper anchors, climb geometry with the reserved climb_rect,
  transition, fall protection, access control, the six route_nodes (s13.1),
  and the gameplay/network block. Documented in
  docs/GAMEPLAY_JSON_CONTRACT.md. The builder drops <ID>_MOUNT / <ID>_DISMOUNT
  empties for the post-import nav-link; ladder rail/rung geometry is unchanged
  from before, so all shell.glb output is byte-identical.
- All six shipped specs with ladders (07_police_station, cbp_town_finale,
  corner_deli_heist_01, foundry_heist_vertical, gs_auto_shop, primos_pizza)
  now carry real roles: roof_access for climbs to the top slab, service_access
  for interior and pit climbs. cbp_town_finale's 8 m roof climb tripped
  LADDER_LONG_CLIMB_UNPROTECTED and now declares a safety_rail -- the check
  catching a real unprotected long climb on existing content.
- 26 new tests (111 total). Gate green.

## [0.68.0] - Advanced stair types (spec Phase 5) -- stair spec COMPLETE

- The geometry phase. _stairs() is restructured around a local stair frame
  (ascent along +Y) rotated at emission by a new `facing` field (N/S/E/W;
  "N" is the identity, so every pre-0.68 spec bakes byte-identical
  geometry). Collision ramps tilt about the correct world axis per facing;
  slab holes rotate with the stair.
- Three new styles (schema 1.16.0 -> 1.17.0, style enum extended):
  `l_shaped` (spec 6.3: half-rise leg, corner landing, perpendicular second
  leg -- a lobby/corner stair with per-leg collision ramps and a bounding
  slab hole); `scissor` (spec 6.4: two INDEPENDENT full-height opposite-
  direction flights sharing one shaft, thin divider baked between the
  channels; authored-only -- stair_place never proposes it); `spiral`
  (spec 6.5: one revolution per story of wedge treads around a pole,
  `width` = radius, per-step collision -- decorative/private/service only,
  and the review hard-refuses an egress role on it:
  STAIR_STYLE_NOT_EGRESS_CAPABLE).
- Exterior stair towers (spec s8.4): `exterior: true` on a Stairwell
  authored outside the shell. The review swaps its contract -- no interior
  approach demanded; instead every occupied served floor needs a facade door
  within reach of the tower (EXTERIOR_TOWER_NO_DOOR gates egress towers),
  door_nodes come from those facade doors, and discharge is the site itself
  ({"type": "exterior_tower", "destination": "site"}). Egress-pair
  independence treats a tower route as independent by construction.
- Transfer floors (Rule 2 relaxation): `transfer: true` on a stack member
  legitimizes a footprint shift at the junction story IF a body can walk
  between the two stairs there -- verified on the room graph (same or
  adjacent approach rooms), error with the reason when unwalkable, accepted
  with a warning when no rooms exist to check. `transfer_floor` is emitted
  on both members. The plain STAIR_NOT_STACKED error now names the fix.
- Roof + basement access: `roof_access` emitted when the stair tops out past
  the last occupied story (corner_deli's roof stair now says so), and a new
  STAIR_TERMINATES_INTO_SLAB intel warning fires when a multi-story stair
  has cut_slabs=false (runs end against slabs; cut the holes or author the
  bulkhead). Rule 8 basement handling unchanged from 0.65.
- Atrium convenience stairs need no new machinery: an open (unenclosed)
  stair with role public_convenience already gets open-enclosure gameplay
  semantics and never counts toward egress. Split-level buildings are OUT of
  scope: DC's slab model has one story_height; a stair tool cannot add
  variable floor levels -- tracked as a non-goal until the slab model does.
- 13 new tests (85 total). Gate green; all shipped specs byte-stable.

This closes all five phases of docs/stairwell_placement_spec.md.

## [0.67.0] - Stair gameplay + network semantics (spec Phase 4)

- stair_systems entries in gameplay.json now carry the full s13 gameplay
  contract. `door_nodes`: every door a body moves through to use the stair
  (partition openings flanking the approach room per served floor, plus the
  approach room's exterior doors at grade, flagged `discharge_door`), each
  carrying the SAME stable interactive id the builder bakes -- computed
  through interactives.derive_interactive on the identical wall-name
  convention, so netcode, slots.json, and the egress contract key on one id.
- `enclosure` ("protected" when the approach room is a role-"stairwell"
  enclosure, else "open") and a derived s9.3 `gameplay` block:
  network_authority=server, replicate_door_state, allow_random_lock (false
  for egress roles), egress_side_always_openable, fire_door/self_closing
  (enclosed egress), ai_route_cost_multiplier (1.15 enclosed / 1.0 open),
  and `congestion` intel (clear width, max agents abreast at the 0.7 m pass
  band, two-way passability).
- Egress route identity: `egress.independence_group` keys on the grade
  discharge destination (stairs sharing one are not independent routes) and
  `egress.paired_with` closes the two-stair contract. This plus
  allow_random_lock is the handshake Dispatch consumes to keep mission
  randomization from invalidating required routes -- documented in
  docs/GAMEPLAY_JSON_CONTRACT.md (new stair_systems section).
- `Stairwell.meta` (schema 1.15.0 -> 1.16.0, like VerticalLink.meta): passes
  through to gameplay.json, and a meta["gameplay"] dict overlays the derived
  defaults -- the spec's "authored scenario explicitly permits it" escape
  hatch (e.g. a scripted blackout that locks a stair).
- Two new review checks (same gate-the-contract severity):
  STAIR_VOLUME_INVADED (Rule 10 / acceptance criterion 10) -- volumes,
  objectives, loot, and cover/objective/loot/extraction markers may not
  occupy a stair's reserved footprint through its served span (stair-named
  furniture exempt); LOCKED_EGRESS_DOOR (s9.3 locked egress roulette) -- a
  door defaulting to locked (e.g. a vault) on the ONLY egress stair serving
  a floor is a hard error; with a backup egress stair it downgrades to a
  reliance warning.
- 12 new tests (72 total), including builder-id parity for door nodes and
  the meta escape-hatch overlay. Gate green; geometry untouched.

## [0.66.0] - Archetype profiles + weighted stair placement (spec Phase 3)

- New `stair_place.py`: the PLACEMENT side of what stairwell.py reviews.
  Ten archetype profiles from the placement spec s12 (residential_house,
  urban_storefront_narrow, restaurant_two_story, office_lowrise,
  office_midrise, hotel_corridor, apartment_corridor, school_wings,
  warehouse_mezzanine, parking_structure), each carrying stair count policy,
  preferred shape, primary/secondary candidate zones, service/convenience
  probabilities, separation factor, and s10 riser/width geometry defaults.
- Candidate zones are DETERMINISTIC anchors (s11.2, never random points):
  exterior corners, grade corridor-axis ends, central core edges, wing
  junctions (adjacent circulation rooms), rear service bands (rear = wall
  opposite the most-doored front), perimeter bays, and party-wall bands for
  narrow plates (aspect >= 1.8). Every rejected candidate carries its stated
  reason (s11.3 / acceptance criterion 14): does_not_fit_inside_shell,
  overlaps_protected_room, consumes_circulation,
  entrance_through_prohibited_room, no_ground_discharge,
  overlaps_existing_stair.
- Survivors are scored with the s11.4 weights verbatim (corridor connection,
  discharge, stack efficiency, separation, grid alignment, archetype fit,
  exterior visibility, minus usable-area damage, dead ends, route dependency).
  Two-stair buildings select the best PAIR (s11.5): separation valid, routes
  independent (reuses the Rule 7 chokepoint scan), coverage + separation
  bonuses -- never the two top individual scores.
- Proposals emit ready-to-paste Stairwell JSON with roles assigned
  (primary/secondary egress + optional seeded service/convenience extras --
  rolls on spec.seed, so the same spec proposes the same stairs forever), s10
  riser math (uniform risers near the profile target, run snapped to the
  0.5 m grid), and stack-serving story ranges. CLI:
  `python stair_place.py specs/x.json --archetype office_lowrise`
  (+ `--count`, `--write` for stair-less specs, `--write --replace` to
  overwrite deliberately; --replace ignores existing stairs in the math).
- LevelSpec gains optional `archetype` (SCHEMA 1.14.0 -> 1.15.0, enum of the
  ten profiles). When declared, stairwell.py adds STAIR_LOW_ARCHETYPE_FIT
  intel (s14.2) for any stair outside the profile's candidate zones.
- Showcased in `office.json`: declares `office_lowrise`, and its (0,0)
  center stair -- the spec's headline "random center stair" anti-pattern --
  now fires the fit warning, while `stair_place.py` proposes the corrected
  pair (corridor-end west + corner east, independent lobby/bullpen routes,
  both exec_suite-overlapping corners rejected with reasons). Geometry
  untouched; the warning is intel, gate stays green.
- 16 new tests (60 total), including the loop-closure test: a stair_place
  proposal must pass stairwell.check with zero errors. Gate green.

## [0.65.0] - Stairwell systems: stairs become semantic egress systems

- Implements Phases 1-2 of docs/stairwell_placement_spec.md (new doc, folded in
  from the proposal): a stair is no longer an isolated mesh but a SYSTEM with a
  role, a vertical stack, a per-floor approach, and a ground discharge route.
- New pure analyzer `stairwell.py` in the validate chain (after navigability).
  Severity follows the house rule -- gate the declared contract, warn the rest:
  a stair with an EGRESS role (`primary_egress` / `secondary_egress` /
  `exterior_egress`) gates HARD on route findings; unclassified and non-egress
  stairs get identical findings as warnings, so every pre-0.65 spec gates
  exactly as before. Codes match the placement spec s14 verbatim.
- Checks (room-graph resolution, a proxy like navigability, never the truth):
  approach on every served floor (`STAIR_NO_CORRIDOR_CONNECTION`), prohibited
  approach rooms incl. enclosure-neighbor analysis for role-"stairwell" rooms
  (`STAIR_ACCESS_THROUGH_PROHIBITED_ROOM`), grade discharge route to an
  exterior door or outdoor ground (`STAIR_NO_GROUND_DISCHARGE`, classified
  direct_exterior / exit_passage / lobby, multi-turn routes warn), egress-pair
  separation `max(8.0 m, diagonal x separation_factor)`
  (`REQUIRED_STAIRS_TOO_CLOSE`), single-room route dependence via articulation
  scan (`REQUIRED_ROUTES_SHARE_SINGLE_CHOKEPOINT`), declared-stack alignment
  (`STAIR_NOT_STACKED`), plus intel warns for basement continuation through
  grade (Rule 8) and doors sitting over treads (Rule 4, footprint approx).
- Authoring: `Stairwell` gains optional `id`, `role`, `stack_id`; LevelSpec
  gains `separation_factor` (0.33 sprinklered default, 0.50 conservative).
  SCHEMA 1.14.0. All additive -- old specs untouched, geometry byte-identical.
- gameplay.json gains a `stair_systems` section (placement spec s13 subset:
  identity, role, stack, floors served, footprint polygon, approach per floor,
  discharge route) derived by `stairwell.derive()`, plus a `STAIRSYS_<ID>`
  marker empty at each stair base for the post-import.
- Showcased in `corner_deli_heist_01.json` (`main_stack` -> primary_egress;
  its Rule 8 basement-shaft warning fires as intended). 17 new tests
  (44 total). Gate green.

## [0.64.0] - Teller line + safe deposit boxes: the rest of the bank fixtures

- New `teller` and `safe_deposit` opening kinds — the bank lobby teller line and
  the vault-room box wall. Both are SOLID barriers (like `window`), not carved
  portals like `vault`: they bake a solid piece filling the span (a `TELLERLINE`
  / `SAFEDEPOSIT` slot) so the greybox stays sealed, and Zoo's `teller_line` /
  `safe_deposit_boxes` modules (Zoo 0.18/0.19) swap in.
- Each infers an interactive fixture (`interactives.py`): `teller` -> a
  `teller_window` (intact/shattered, intact blocks / shattered passable);
  `safe_deposit` -> a `safe_deposit_boxes` wall (intact/drilled, solid in both —
  per-box loot is gameplay's granularity, not the wall's art state). Neither
  carries `state_geometry`, so the break/drill state reuses the base art and Zoo
  defers it until a shattered-glass / drilled-box art pass — same as a broken
  window. Emitted into both contracts with a stable position id + a socket
  marker, like every fixture.
- Authoring: `{ "kind": "teller", "pos": ... }` (default 2.0 x 3.0 m, floor-to-
  ceiling) and `{ "kind": "safe_deposit", "pos": ... }` (default 2.0 x 2.4 m).
  `Opening.kind` + schema enum gain both (SCHEMA 1.12.0 -> 1.13.0). Navigability
  treats them as solid (barriers, not connections), like a window.
- Showcased in `bank.json`: a lobby teller line (story 0) and a vault-room
  deposit-box wall (basement, beside the vault door + breach). 3 new tests
  (23 total). Gate green.

## [0.63.0] - Vault door: the first bank interactive fixture

- New `vault` opening kind — the heist vault portal. It infers a `vault_door`
  interactive fixture (via `interactives.py`): states `[locked, unlocked, open,
  breached]`, default `locked`, with the transition graph unlock/lock/open/close
  plus `breach` from either closed state. Emitted into both contracts sharing one
  stable id, like every other fixture.
- state_geometry maps each state to the Zoo module that backs it —
  `{locked: vault_door, unlocked: vault_door, open: doorway, breached: breach}` —
  so Zoo builds the closed armored door (`vault_door` species, 0.17.0), reuses
  `doorway` for the open passage and `breach` for the blown state, and defers
  `unlocked` (identical art to `locked` today) to the resolver's base fallback.
  The vault door is thus a doorway/breach at its other states, exactly like a
  breachable wall is a wall's breached state.
- Baking: a vault opening carves the wall and, being closed by default (locked),
  fills the portal with a solid armored panel (`VAULTDOOR` piece, role
  `vault_door`) in both the modular and non-modular shells — the greybox reads
  shut and blocks. A `VAULT_DOOR_*` socket marker is emitted for Godot scene
  swap, parity with door/breach.
- Authoring: `{ "kind": "vault", "pos": ..., "tag": "main_vault" }`. Defaults
  1.4 x 2.3 m with a 0.15 m raised threshold lip (matches Zoo's vault_door
  frame). `Opening.kind` + schema enum gain `vault` (SCHEMA 1.11.0 -> 1.12.0).
- Navigability treats a vault as a connection (the vault room is entered through
  it, so it's not flagged isolated); sightline/cover audits still treat the
  closed door as solid. Showcased in `bank.json` (basement: crack the vault
  door or blow the adjacent breach). 3 new tests (20 total). Gate green.
- Fixes the VERSION text file (was stale at 0.61.0 while HEAD was tagged
  v0.62.0) to track KIT_VERSION again.

## [0.62.0] - Roof: authorable, swappable, collision-retaining

- The top-story ceiling slab that `_slabs()` already bakes becomes a first-class
  surface you can author, dress, and add after the greybox passes. New spec
  fields (additive, defaults reproduce 0.61.0 byte-for-byte): `roof`
  (`solid` = today | `open` = drop the roof VISUAL for top-down authoring but
  KEEP collision so grenades/projectiles still bounce | `none` = no cap),
  `roof_mode` (`footprint` | `per_room`), `roof_thick`, and `Room.roofed`
  (per-room open-air opt-out).
- `_slabs()` now splits the roof's visual from its collision (the collision box
  is emitted regardless of `roof` visual mode) and, when modular, ALWAYS emits a
  roof swap-slot so the art pass has a hook even in `open` mode.
- New pure module `roofs.py` (`roof_slots`, no bpy, like `lights.py` /
  `interactives.py`) derives the roof slot(s): one over the footprint, or one per
  top-story room honoring `Room.roofed`. `slots.json` gains `role: "roof"`,
  `facing: "up"` records. `test_roofs.py` (4 tests).
- Consumers (Godot loader / Zoo / Lot) key on these: hide-mesh/keep-collision
  toggle, roof/skylight art modules, site roofline merge. See docs/ROOF_PLAN.md.
- Roof derivation reads only frozen structure (footprint, story_height, room
  bounds); it never re-solves layout, so a passed greybox stays byte-identical
  below the roof. `slot_manifest_version` 1.1.0 → 1.2.0;
  `SCHEMA_VERSION` 1.10.0 → 1.11.0; `KIT_VERSION` 0.61.0 → 0.62.0.

## [0.61.0] - Interactive fixtures: networked doors + breachable walls

- New `interactives.py` (pure + tested): turns an authored opening into a
  replicable STATE MACHINE `(id, states[], default, transitions[])` — the entire
  networked surface. It describes STATE, never synchronization, so it stays
  network-solution agnostic (server snapshot / event-RPC / lockstep / rollback).
  Doors/garages infer a `door` (`closed`/`open`); a `breach` opening infers a
  `breach_wall` (`intact`/`breached`) carrying `state_geometry {intact: wall,
  breached: breach}`; a window is interactive only when authored `breakable`.
- Emitted into BOTH contracts, sharing one id: `slots.json` slots gain an
  art-facing `interactive` block (Zoo builds a `_<state>` art variant per state;
  the breach reframe means a breachable wall is the `breached` STATE of a wall
  slot, not a standalone module), and `gameplay.json` gains an `interactives`
  array (the netcode-facing machine: id, slot_ref, transform, states, default,
  transitions, reversible). The game spawns one replicated node per id.
- Stable ids derive from the fixture's PLACE (`sha1(building, wall, story, kind,
  round(pos,4))`), never an array index — the geometry pass re-sorts openings by
  position, so an index-based id would break saved/replicated references on a
  re-greybox. slot_ref reconstructs the same `{wall}_open{k}` the emitter names.
- Authoring: new optional `Opening.breakable` and `Opening.interactive` (None |
  false | dict override, merged over the inference). `interactive: false` forces
  a fixture off; a dict authors a custom machine. Schema `$defs.opening` gains
  the two optional props (SCHEMA_VERSION 1.9.0 -> 1.10.0, additive/back-compat).
- slot_manifest_version 1.0.0 -> 1.1.0. docs/INTERACTIVES.md (shared with the
  zoo repo), plus interactive sections in SLOT_MANIFEST / GAMEPLAY_JSON_CONTRACT
  / AUTHORING. test_interactives.py (11 tests, no Blender). Validated on
  primos_pizza -> 13 fixtures (11 doors incl. a garage, 2 soft-wall breaches),
  all unique position-derived ids.

## [0.60.0] - lights.json: the lighting contract (Lux bridge)
- New light-anchor emitter (lights.py, pure + tested): derives one fluorescent
  ceiling row per room (along the longer axis, at story ceiling height) and one
  area light per window opening (sized + facing inward), and writes
  <name>.lights.json next to the gameplay/slot manifests. Typed anchors say
  WHERE a light belongs and WHAT kind; Lux instances a rig per anchor and tunes
  it from the active preset. Output-only, no level.schema.json change.
- Optional spec `lights` list for authored overrides (replaces a derived anchor
  by id; absent by default, so existing specs are unaffected).
- docs/LIGHT_MANIFEST.md; test_lights.py (5 tests, no Blender needed).

## [0.59.0] - primos_pizza: the showcase spec + an audit marker-room fix
- specs/primos_pizza.json + NOTES.md: "Primo's Pizza & Social Club" -- a
  1997 Delco pizzeria with the card room and cash count upstairs, authored
  as the kit's proof-of-concept building. Every feature in one spec
  (basement->roof, switchback stair, cellar/dumbwaiter/roof ladders,
  breachable roof hatch, parapet, all opening kinds incl. two soft walls,
  rarity, objective/loot/extraction/camera/patrol markers, secure +
  extraction zones, 25 authored volumes) and every gate green: check.py
  0 errors / 0 warnings, combat_audit --rules all 0 HIGH / 0 MED / 0 INFO
  with zero audit_accepts. The count room has three ways in and each is a
  different plan: the count door (loud), the club soft wall (breach), the
  kitchen dumbwaiter ladder (quiet). NOT WALKED -- checklist in NOTES.md.
- combat_audit fix: _objective_rooms resolved objective markers by
  guessing story 0, so an upstairs objective claimed the room BELOW it
  too (primos' count room claimed the kitchen). Markers' own "room" field
  now wins; otherwise the story derives from z. Preset sweep unchanged.

## [0.58.0] - Genre rule packs: PayDay 2 / Ready or Not / L4D2 grammars
`combat_audit --rules auto|all|heist,cqb,flow` layers three measurable
design grammars over the core audit. Full doc: docs/DESIGN_RULES.md.

- HEIST (PayDay 2): H_ONE_ROUTE interior-disjoint routes to each objective
  (one route = one crew plan); H_NO_HOLDOUT drill-defense room at/next to
  the objective (2-3 coverable entries, >= 12 m^2, cover); H_CARRY_PINCH
  bag-carry exfil on a width-filtered graph (>= 1.2 m route to a >= 1.4 m
  exterior egress; stairs carry bags, ladders don't); H_NO_STEALTH
  camera/patrol marker presence (INFO).
- CQB (Ready or Not): door feed classification (corner-fed vs center-fed)
  with C_FEED_MONOTONE census; C_NO_PIE threshold standoff on the approach
  side; C_NAKED_ROOM / C_BLIND_ROOM first-slice threshold visibility via
  2-D raycast against >= 0.9 m solids, judged on the BEST door into each
  hot room (the team picks its threshold; band ~35-97%).
- FLOW (L4D2): F_FLAT_RHYTHM compression/release along the golden path;
  F_BRANCH_OVERLOAD decision-point degree; F_ARENA_STARVED horde ingress
  (>= 3 ways in) for finale rooms always and objective/fortifiable rooms in
  survival/assault modes ONLY -- heist drill rooms are exempt because the
  heist grammar wants 2-3 entries there and the rules would fight;
  F_FEW_HORDE_SPAWNS director choice (INFO).
- `--rules auto` picks packs by spec mode. Pack findings respect
  audit_accept (the accept filter now runs LAST over all findings,
  including AXIS_SWAP and sightline reuse).
- Calibration: threshold visibility nudges the vantage into the room and
  never counts a blocker the vantage stands inside (the walked gas_station
  passes the CQB pack clean, which is the calibration story again).
- Sweep with packs on: 0 HIGH / 2 MED across 14 presets. The two are real
  design findings, reported not auto-fixed: office/exec_suite funnels
  through one spine (H_ONE_ROUTE) and warehouse has no drill holdout
  (H_NO_HOLDOUT). Both have concrete fixes listed in DESIGN_RULES.md.

## [0.57.0] - Roof hygiene: parapets where roofs are stood on or seen
Every building already gets a roof (the top slab caps it; facades too). The
gap was parapets, in two tiers:

- Tactical: auto_shop (1.0 m) and pawn_shop (0.9 m) have roof ladders --
  players stand up there. The parapet lip turns a naked kill platform into
  a fighting position with edge cover, and kills the fall-off QA hazard.
  (police_station and corner_deli already had both.)
- Skyline/consistency: rowhome (0.7 m cornice line, matching facade_rowhome
  so mixed blocks read as one street), office (1.1 m commercial band),
  warehouse (0.8 m big-box band), parking_garage (1.1 m on the capped roof
  slab -- the upper deck itself is an enclosed level by design, no interior
  barrier needed).
- specs/gs_auto_shop.json gets the parapet too (that glb is being rebuilt
  for the 0.56.0 axis fix anyway).

Deliberately NOT touched: gas_station (fine as-is) and suburban_safehouse
-- a flat roof + parapet would make a Delco single-family read as a
commercial box. The right fix there is a gable/pitched-roof primitive,
which the kit does not have yet; that is a real builder feature (inclined
roof planes, gable end walls, slab interaction) and should be its own
build-and-walk pass, not a volume hack.

## [0.56.0] - The combat-audit fix batch: presets sweep 0 HIGH / 0 MED
Addresses every finding from the 0.55.0 audit. Enriched presets (the
shipping path) now sweep clean: 4 HIGH / 49 MED -> 0 / 0. Raw recipes keep
their 20 pre-furnishing KILLBOX MEDs by design -- architecture is the
recipe, cover is enrichment.

### The big one: nine axis-swapped partitions in five presets
A new lint (now permanent in combat_audit as AXIS_SWAP, HIGH) caught
partitions authored with X/Y swapped: the built wall bisected rooms and
every door on it opened within a single room. Fixed in auto_shop (story 1),
corner_deli (stories 0 and 1, four walls), pawn_shop (story 1), and
suburban_safehouse (three walls). This single bug class was the root cause
behind the window-only manager_office, the one-door deli_counter, and the
pawn_shop apartment / auto_shop upper_storage dead ends. specs/
gs_auto_shop.json (generated from the buggy preset, and WALKED with the bug
in it) got the same flip + door widening -- rebuild its glb.

### Door hygiene
~24 openings widened across 10 presets: all sub-nav 0.9/1.0 m doors to
1.1-1.2 m (they NAV-warned on every generation), and one >=1.4 m opening
into every objective room (alley_entry/deli counter 1.4, armory 1.4,
apartment_hall/manager office 1.4, count_room 1.4, exec_s 1.4, safe_room
1.4, booth_e 1.4, compound suite 1.5, safehouse attic breach 1.5,
rowhome/pawn/safehouse front doors, compound rear_service 1.5, ...).

### Vertical: eleven ladders across seven presets
Every VERT_DEAD_END story pair that SHOULD have a second link got a ladder
(auto_shop, casino 0->1, corner_deli basement, office x2 shaft, pawn_shop
-> apartment, police_station, rowhome x2 rear shaft, safehouse x2 shaft).
Placements are clearance-verified in code against partitions, volumes,
stairs, ladders, and door approaches on BOTH stories, and objective/vault
rooms are excluded so no ladder bypasses a designed breach.

### audit_accept: intended designs, recorded
New optional spec key (schema + loader + audit support):
"audit_accept": [{"code", "room"?, "why"}] downgrades a finding to INFO
with the author's reason attached. Applied where the audit was right to ask
but the design is deliberate: casino vault one-breach climax, casino/bank
vault-basement single stairs, bank's unfurnished roof story, rowhome's
period-tight interior doors.

### seed_cover: kill boxes furnished at enrichment
level_design.enrich() gains a first pass that CREATES cover volumes (the
old cover_from_volumes only tagged existing ones) in combat-intent rooms
>=30 m^2 with zero waist-high solids. Deterministic (spec seed + room id),
idempotent, role-keyed archetypes (desks/cabinets in offices, shelf runs in
storage, crates in bays, counters/planters in public floors), 2-4 pieces,
clearance-checked against walls, door approaches, stairs, ladders,
objectives, and loot. Clears all 20 KILLBOX flags on the shipping path.

### tactical: open-plan adjacency
build_graph now connects same-story rooms sharing >=1.2 m of unwalled edge
-- a lobby flowing into a bullpen is one space, not a dead end. Fixed the
office ground_bullpen false HIGH and improves route intel everywhere.

### combat_audit
- Audits presets ENRICHED by default (the shipping path); --raw for recipes.
- AXIS_SWAP lint (HIGH) permanent.
- Honors audit_accept (room-scoped or code-wide).

WALK BEFORE SHIPPING LEVELS: the axis flips move real walls, the ladders
and seeded cover are new geometry, and none of it has been walked. Suggested
first walks: auto_shop, corner_deli, suburban_safehouse (most changed).

## [0.55.0] - `combat_audit.py`: "will it FIGHT well?" as a repeatable check
The existing gates answer buildable/reachable/sane; this one audits the
structure 4-player co-op FPS combat lives on. Report-only (never fails a
build) -- deliberate designs like a one-breach vault are why it reports
instead of gates.

- Metrics: route-graph loops (cyclomatic) + articulation chokepoints +
  non-utility dead ends (outdoor rooms exempt, mirroring the 0.54 tactical
  rule); entry-face spread (ONE_FACE = no exterior flank); per-objective-room
  opening count + widest width (single-file objectives flagged) + BFS entry
  depth; vertical links per story pair (one stair = the floor plays as a
  siege); cover census (any solid >= 0.6 m counts -- crates, counters,
  pillars, the vault box); cramped combat rooms; sightline-intent
  mismatches reused from sightlines.py.
- `--all-presets` / `--all` / `--preset X` / single spec path; `--json` for
  machine use. Facades skipped.
- First sweep results (July 2026): presets 4 HIGH / 49 MED, shipped specs
  11 HIGH / 53 MED. Patterns: empty combat rooms (20x KILLBOX), one stair
  per story (10x), single-file objective doors (8x, incl. seven 0.9 m
  doors below the nav minimum), a dead-end objective (office
  ground_bullpen), two legacy ONE_FACE specs. gas_station -- the one
  walked-and-iterated preset -- audits clean, which is the calibration
  story in one line. Full findings + prioritized fix plan in the audit
  report (delivered separately; regenerate anytime with --all-presets).

# Changelog

**Deli Counter** — a spec-driven Blender level kit for Godot 4.

All notable changes to the kit. Bump `KIT_VERSION` in `version.py` with each
entry. See that file for the versioning convention.

## [0.54.0] - Outdoor rooms join the route graph + the gas-station-corner spec set
The `gas_station` preset's declared `forecourt` room false-flagged as
AI-unreachable: the tactical checker modeled every room as interior, so an
outdoor staging room (a forecourt, yard, or lot apron) could never be an entry
and never got a graph edge. Fixed in the checker, not the preset — outdoor
rooms are legitimate authoring.

- `tactical.build_graph`: exterior door/garage/breach openings now connect the
  room just inside the wall to a declared room just OUTSIDE it (probe mirrors
  `_entry_rooms`). The gas station's front doors genuinely link sales floor ->
  forecourt in route intel, approaches, and funnel analysis.
- `tactical._entry_rooms`: a grade-level room lying (essentially, <10% area
  overlap) outside the footprint is open ground — reachable from outside by
  definition, so it is itself an entry room. Kills the forecourt NAV-ERROR.
- Both changes are strictly additive (only ever ADD entries/edges), so no
  existing spec can newly fail.
- New spec set for the Lot `gs_heist` site (gas-station street corner, per the
  level requirements doc): `gs_corner_station` (gas_station preset + a carved
  restroom/utility closet in the stockroom SE corner + the two 1.0 m doors
  widened to 1.2 m for the nav agent — validates 0 errors, 0 isolated rooms,
  10 usable entries), `gs_auto_shop` (auto_shop preset, `--rarity very_rare`,
  its safe objective flipped to `required: false` — it is this site's OPTIONAL
  side score), `gs_facade_rowhome` + `gs_facade_storefront` (facade shells for
  Lot's street wall).

## [0.53.0] - Two vertical heist presets: `auto_shop` + `pawn_shop`
First presets authored against the fixed stairs (0.51) and ladders (0.52) -- each
is multi-storey with a comfortable stair AND a roof-access ladder, so they double
as walk-tests for both traversal fixes.

- `auto_shop` (26x18, 2 storeys): open ground service bay (roll-up door, lifts,
  parts racks) + an upper office holding the safe, joined by a ~36deg stair; a
  roof-access ladder off the upper floor for a flank/escape. Medium-range
  industrial set-piece. Objective = crack the office safe; extract via the bay.
- `pawn_shop` (16x14, 2 storeys): glass-front shop floor with display-case cover
  + a back safe room, an upper storage/apartment up a ~35deg stair, roof ladder
  for escape. Tight close-quarters safe job in a small footprint.
- Both use run = story_height*1.4 so the stair ramp sits at a comfortable ~35deg
  (no steep warning), and both place a ladder 1->roof to exercise the 0.52 climb
  volume. Registry is now 17 presets. Both validate clean (0 errors/0 warnings);
  interior doors widened to 1.1 m to clear the nav-agent proxy.

## [0.52.0] - Climbable ladders (climb volume + harness climb logic)
The other half of the traversal fix: ladders you can actually climb. Same root
cause as stairs -- a solid rung catches a capsule on the way up -- so the fix is
the ladder equivalent of the stair ramp: stop fighting the mesh, drive traversal
off a volume.

- DC (`_ladders`): rungs + rails are now VISUAL ONLY (collision removed). Each
  ladder emits a climb-volume anchor -- a `LADDER_<i>` marker carrying meta
  (climb_height, width, depth, facing) -- alongside the slab hole it already cut.
  Ladders still count as vertical access in validation (spec-graph connectivity
  is unchanged), so the reachability gate still holds.
- Addon post-import: `LADDER_*` now builds an `Area3D` climb volume (group
  "ladder", sized from the meta with a 1 m dismount lip on top) instead of a
  bare marker. `DeliLevel.ladders(tree)` returns them.
- Harness player (`template/player.gd`): real ladder climbing. Overlap a ladder
  volume to enter climb mode -- move along where you look (look up + forward to
  ascend, down to descend, level + forward to step off at the top), gravity off
  so no input clings in place, Space drops off. This is a reference climb for the
  test rig; wire your own controller to the same `ladder` group + meta.
- WHY a volume and not geometry: unlike a stair (a slope you can walk), a vertical
  ladder can't be traversed by any pure-geometry trick -- climbing is necessarily
  a controller mechanic. DC's job is the WHERE (the climb volume); the HOW lives
  in the player, same contract as objectives/breaches.
- GEOMETRY/ANCHOR CHANGE -> KIT_VERSION 0.51.0 -> 0.52.0; addon plugin 0.18.5 ->
  0.18.6 (post-import + player + DeliLevel). Rebuild buildings with ladders to
  pick up the visual-only geometry + climb-volume marker.

## [0.51.0] - Stairs you can WALK up (smooth ramp collider, not boxy risers)
Fixes the long-standing "stairs don't work — you stick on them and have to jump"
problem, which hit every multi-story building.

- ROOT CAUSE: each stair step shipped its own box collider, so a CharacterBody3D
  caught on every riser. FIX: the visual steps stay stepped, but COLLISION is now
  a single smooth incline (a thin convex ramp at the flight's pitch, tilted like
  `_ramps` does) under the steps. Any controller walks straight up — no per-step
  catching, no jump, and no player-script step logic required. Switchback legs get
  one ramp each (reversed legs tilt the other way); landings keep their flat
  collider. `_stairs()` in deli_counter.py.
- PITCH MATTERS: the ramp only walks if the flight is under the controller's
  floor_max_angle (Godot default 45deg). A short `run` against a tall story can
  exceed that. NEW steep-stair warning in tactical.py (mode-agnostic): warns past
  ~38deg (steep), flags >=44deg as not climbable, and suggests run >=
  story_height*1.4 (~35deg). Same wrapper also makes the existing steep-RAMP
  warning fire for heist/survival specs (it was assault-only before).
- Preset audit: most stairs are ~42deg (walkable but steep) at the default run 4;
  corner_deli (run 5.5) is a comfortable 31deg; rowhome (run 3.0) is 45deg and
  needs a longer run or a controller step-up. Lengthen runs toward
  story_height*1.4 for a nicer climb.
- GEOMETRY/COLLISION CHANGE -> KIT_VERSION 0.50.0 -> 0.51.0. Existing built .glbs
  must be REBUILT to pick up the ramp collider (regenerating a spec isn't enough —
  the geometry is baked in Blender).

## [0.50.0] - Facade shells: non-enterable filler-building presets (`facade_*`)
New `facade` building type + a starter family of presets for the filler
buildings that wall a street and channel the player toward the real heist
buildings (pairs with Lot's `blocker`, which can now point at a facade .glb).

- `facade_rowhome`, `facade_storefront`, `facade_industrial` (names carry
  "facade" so it's unmistakable they aren't enterable). Each returns a solid
  exterior SHELL: walls + roof/parapet + collision + a theme, and nothing else.
- New spec field `facade: true`. The builder runs exterior-only passes (slabs,
  exterior, parapets, materials) and skips all interior + tactical passes
  (partitions, stairs, rooms, markers, objectives, loot, zones, nav). It emits
  no gameplay data; `validate.py` skips the tactical/guard/enterability/
  navigability analyzers for a facade (a shell legitimately has no objective).
  `presets.make` skips enrichment for facades.
- Non-enterable by construction: `auto_exterior` builds a sealed solid shell
  with no door/window holes. `modular: true` is on, so the walls are art-pass
  swap slots — resolve them later into brick + windows + a stoop/glazing, and
  reuse the same shell up and down a block. The shells are deliberately cheap
  (heavy instancing for the 4-player netcode).
- Schema: `facade` boolean added (SCHEMA_VERSION 1.8.0 -> 1.9.0). All existing
  presets and specs are byte-identical; this is purely additive.

## [0.49.0]
### Changed — build better levels, not validate them better
- **Heist is the default mode.** DELCO-style play is a PAYDAY-flavored 4-player PvE
  co-op heist loop, not a PvP-symmetric shooter, so a fresh building is a heist by
  default. All presets except `hospital` (survival) now default to `mode="heist"`, and
  `LevelSpec.mode` itself defaults to `"heist"`. `--mode assault` still produces the
  symmetric attacker/defender variant for tools users who want it.
- **`level_design.py` — felt-space enrichment, applied by construction.** `make()` now
  runs every finished spec through `level_design.enrich()` (pass `enrich=False` for the
  raw recipe). The layer is additive, idempotent, and never touches geometry — it only
  appends anchors:
  - **Cover cadence from real geometry.** Cover-like volumes (counters, aisles, racks,
    desks…) that had no cover marker are tagged as engagement points, so contested rooms
    reach a readable 3-5 (capped per room — the thesis lesson is *don't over-cover*). This
    also fixes heist branches that rebuilt the marker list and silently dropped cover, and
    gives objective rooms holdout cover they previously lacked.
  - **Callout landmarks.** One `landmark` anchor at the centroid of each major zone
    (objective / entry / loot / safe / vault / staging) so a crew can read and call the
    space at a glance (Foreman: landmarks first; thesis: distinct callout areas).
### Added
- **`staging` room role + `landmark` marker type** — both free-string vocab (no schema or
  dataclass change). `deli_counter_postimport.gd` routes `LANDMARK_*` → group `landmark`
  and `STAGING_*` → group `staging`.
- **gas_station: the forecourt is now a `staging` zone.** Making the pump court a real
  room means the pumps register as approach cover and the crew gets a screened regroup
  before the glass front. Result (sightlines diff): exposed crew approach **39 m → 22.5 m**,
  the back-office objective room gains holdout cover, and three callout landmarks
  (FORECOURT / SALES_FLOOR / BACK_OFFICE) appear. This is the worked exemplar of the new
  layer on the one preset that's been walked; the other eleven get the same enrichment by
  construction and deeper per-building tuning as they're walked.
### Migration
- Five committed example specs omitted `mode` and so relied on the old `assault` default
  (`bank`, `warehouse`, `kitbash_demo`, `rarity_demo`, `rowhouse_raid`). They're now pinned
  to `mode="assault"` so the default flip doesn't silently reclassify the frozen demos.
  `specs/CATALOG.md` regenerated. Committed example specs stay frozen; regenerate your own
  working specs via `new_level` to pull the enrichment.

## [0.48.1]
### Fixed
- **Loader crash on `vertical_links` with `meta`.** `VerticalLink` was the only spec
  dataclass missing the `meta` field that Marker/Objective/LootSpawn/Zone all have, so any
  spec whose `vertical_links` carried `meta` (e.g. a multi-story heist spec) crashed
  `spec_from_dict` -> `validate`/`catalog --check` -> the whole pre-commit gate. Added
  `meta: Optional[dict] = None` to `VerticalLink`. No other change.

## [0.48.0]
### Added
- **sightlines.py -- tactical geometry intel (offline, bpy-free).** Reads the same
  wall/partition/opening/volume geometry the floorplan draws, casts 2D rays at eye height,
  and reports the metrics that catch gameplay problems in a greybox BEFORE you build/walk:
  - **death lane** -- the longest unobstructed sightline on a floor (the angle that
    dominates fights near it).
  - **exposed run** -- the longest stretch of the spawn->objective approach with no cover
    marker within reach (where you get caught in the open).
  - **weak cover** -- cover markers with clear line of sight from attacker spawns (cover
    that isn't really cover).
  - **intent mismatch** -- a room's authored `combat_range` vs the sightlines its geometry
    actually produces (a "close" room that plays "long").
  - **objective entries** -- independent ways into the objective room (1 = a funnel).
  INTEL only -- never fails a build; a GUIDE to authoring better-playing buildings. Runs
  inside validate/check per spec and writes annotated `<name>.sightlines<story>.svg` overlays
  next to the floorplans (death lane in red, exposed approach in orange, weak cover ringed).
  CLI: `python sightlines.py <spec.json> [outdir]`.

## [0.47.1]
### Fixed
- **Stairs / ramps / hatches: invisible collision capping the upper floor.** Floor and
  ceiling slabs were built with the spec default `convex` collision. Stairwell/ramp/hatch
  holes are boolean-cut from the slab mesh, but a CONVEX hull fills the hole straight back
  in on import -- so you saw the opening yet hit an invisible collider at the top of the
  stairs and could not reach the next floor. Slabs now use `trimesh` collision (`-colonly`)
  so the cut hole survives. Affects EVERY multi-story build (foundry-type specs, `office`,
  `parking_garage`, any spec with stairs/ramps/hatches). Rebuild affected levels to pick it up.

## [0.47.0]
### Fixed
- **Modular .tscn/instancing path: greybox wall remainders now fit.** The slot emit
  (`_record_wall_slot`) wrote `scale [1,1,1]` for every slot, so the `wallEnd` remainder
  slots (23 in a typical build, ~16 distinct sizes) all referenced one `wallEnd_greybox_01`
  at one fixed size -- which a single instanced mesh cannot fill. The BAKED path was fine
  (it generates each box at exact size); the `.tscn` path would show overlaps + gaps.
  Remainder slots now emit against a **unit (1x1x1) module** with the size carried as a
  per-slot `scale = fit.dims`; one module fills every remainder exactly. Full walls,
  doorways, and windows are untouched -- they stay exact-fit (`scale [1,1,1]`) so themed
  art is never stretched. (Proven in-engine: unit box x fit.dims reproduces the baked shell 1:1.)
### Changed
- docs/ASSET_SWAP_CONTRACT.md: documented the one exception to "modules are never scaled" --
  greybox `wallEnd` filler is authored as a unit cube and scaled per slot.
### Module-authoring note
- Author `wallEnd_greybox_01.glb` as a **1 m cube centered at origin** (not a fixed-width
  strip). All other greybox/themed modules stay authored at their real dimensions.

## [0.46.0]
### Added
- Three new presets, bringing the library to **twelve**:
  - **gas_station** — heist convenience store (sales floor + market aisles + stockroom + manager office safe) fronted by a pump forecourt under a lit canopy; modeled on the walked fuel_stop layout.
  - **office** — multi-story corporate tower: glass-curtain-wall block, central stair/elevator core serving every floor, open bullpen floors, top-floor executive suite as the objective (assault: holdable; heist: exec safe + server pull). `floors`/`basement` parametric.
  - **parking_garage** — enclosed multi-level deck linked by a drivable ramp + pedestrian stair core, structural column grid, sealed perimeter with vehicle openings as entries, glassed attendant booth objective. `floors` parametric (min 2).
  All three are registered for `new_level.py --list` / `describe.py`, validate clean, pass `check.py`, and are indexed in `specs/CATALOG.md`. Each fills a genuine genre gap (fuel / corporate / vehicle-structure) rather than a variation of the existing nine.
### Notes
- These pass the **offline gates** (reachability, enterability, objective-room >=2 access, step/slope, poly budget, IP guard) but each still needs a **build + in-engine walk** before it's trusted — the offline checks are a proxy, not the authority.
- gas_station's canopy columns/pumps and parking_garage's column grid are emitted as repeated **volumes**; per docs/AUTHORING.md they're the textbook candidates to promote to a single placed asset (`placements`) at art-pass time.

## [0.45.3]
### Changed (docs only)
- README: added a **"Concepts (the vocabulary)"** section right after the thesis
  — the preset -> spec -> build -> model pipeline plus the catalog as an index,
  with plain-language definitions and an analogy, so a newcomer isn't decoding
  preset/spec/catalog/mode/volume from context. No builder/geometry change.

## [0.45.2]
### Changed (docs only)
- README: added a **"Using it in your game"** section — the output-file contract
  (.glb / .gameplay.json / .manifest.json / .slots.json), the import-time
  marker->group mapping, and the `DeliLevel` runtime API with a worked GDScript
  example (spawn players, wire objectives, breach a panel). This documents the
  anchors->your-netcode handoff the tool's thesis rests on, which existed in code
  but was never shown.
- README: surfaced the conceptual workflow up front with a "How to build with it
  (read this first)" pointer to docs/AUTHORING.md, right after the thesis.
- No builder/geometry change.

## [0.45.1]
### Changed (docs only)
- docs/AUTHORING.md: reframed the closing "two levers" section as **one invariant
  (collision/nav live on the greybox) and one convention (a fixed width palette)**
  -- they read as a property to rely on and a habit to adopt once, not a pair of
  per-building toggles. No builder/geometry change.

## [0.45.0]
### Added — authoring guide + the volumes->placements best-practice example
- `docs/AUTHORING.md`: the canonical "how to build good buildings" guide. Covers
  the golden rule (an art pass never touches collision/nav), the
  structure / repeated-prop / one-off bucket model (match the primitive to the
  job), why that discipline gets you fun + dress-ability + VRAM sharing at once,
  what instances vs not, the build->walk->art-pass loop, and a worked example
  converting the fuel-station pumps from `volumes` to instanced `placements`.
- `assets/props/make_pump_greybox.py`: Blender recipe authoring the two greybox
  prop assets (pump 1.0x1.2x1.4, island 1.6x8.0x0.3) for that worked example.
- README links the authoring guide from the Instancing section.
- No builder/geometry change: existing specs build identically; this is docs +
  a reusable recipe.

## [0.44.0]
### Added — art-pass fields are first-class on the spec; modular default-on for new specs
- `LevelSpec` (and the JSON schema) gain first-class optional fields: `modular`,
  `module`, `theme`, `state`, `module_library`. Each defaults to `null` and falls
  back to its `DC_*` env var when unset, so the builder reads spec-first then env
  and existing specs that omit them still rebuild byte-identical. A spec can now
  declare `"modular": true` (and a theme/state/library) reproducibly without env
  vars.
- `new_level.py` writes `"modular": true` into generated specs by default, so
  fresh work is art-pass-ready out of the box; `--monolith` opts out to the
  one-solid-box-per-wall path. Existing/hand-authored specs are unaffected.
- Decision (vs flipping the global default): modular stays OFF when unspecified
  to preserve byte-identical output; "default-on" lives at the new-spec on-ramp
  and the explicit field, not in a silent global change.

## [0.43.1]
### Docs + repo hygiene (no builder/geometry change — output identical to 0.43.0)
- README: new "Instancing & memory (shared meshes)" section — documents that
  modular segments, resolver modules, and repeated `placements` of an asset all
  share one mesh datablock (one glTF mesh / N nodes -> one Godot `Mesh` / N
  `MeshInstance3D` -> one geometry + texture in VRAM). Notes the caveat that
  procedural `volumes` are NOT shared (author repeated props as placements/modules
  to instance them) and that this is resource/VRAM sharing, not MultiMesh
  single-draw-call instancing.
- Relocated the reusable baked-path test-module recipe to
  `docs/themes/gasstation/make_wall_module.py` (writes to `DC_MODULE_LIB`; names
  its mesh datablock so it's not "Cube"), sibling to make_gasstation_modules.py.
- `.gitignore`: ignore one-off walk scratch (`/phase4_walk.*`, `/resolver_check.py`,
  `/make_wall_module.py`, `/walk_test.gd`, root-anchored so the tracked recipe is
  unaffected) and the `/dc-modules/` test library.

## [0.43.0]
### Added — state-aware module variants (full kit-naming convention)
- The resolver and `theme_swap.gd` now honor the canonical kit name
  `<type>_<descriptor>_<variant>[_w<cm>][_<state>].glb`. A `_<state>` token
  (e.g. `damaged`, `weathered`) selects a state variant, chosen via `DC_STATE`
  (baked) or the `theme_swap` node's `state` property (live). State is cosmetic
  to resolution: it's recorded in the slot manifest `current_ref`, and on the
  `.tscn` path the overlay gets `dc_state` metadata for game code to act on.
- Precedence, per kit (active theme then greybox), most specific first:
  `…_w<cm>_<state>` -> `…_w<cm>` -> `…_<state>` -> `…`.
- `theme_swap.gd` width-token detection tightened to `w`+digits so a non-width
  4th token is never mistaken for a width.
- Strictly additive / backward compatible: with no `_<state>` files and no
  `DC_STATE`, resolution is identical to 0.42. `docs/ASSET_SWAP_CONTRACT.md`
  updated to the implemented grammar (width + state; `wallEnd` noted as a role,
  not a sizemod).

## [0.42.0]
### Added — addon distribution + automated releases
- `package.py --addon` builds a **drop-in Godot addon zip**
  (`dist/deli_counter-godot-addon-<plugin>.zip`) rooted at `addons/deli_counter/`,
  so a new user unzips it at their project root and enables the plugin — no need
  to clone the whole tool repo. (`package.py` with no args still builds the full
  source zip.)
- Release workflow (`.github/workflows/release.yml`): on a version tag (`v*`) it
  validates, builds the full source zip and the addon zip, and publishes them as
  a GitHub Release. README documents installing the addon from a Release.

### Editor addon (plugin 0.18.5) — carried into this release
- Harness `player.gd`: WASD works with zero Input-Map setup (reads keys directly;
  still prefers dedicated `move_*` actions if defined).
- Harness `level_test.gd`: F4 navmesh bake fixed — parses the level's STATIC
  COLLIDERS (walls import as collision, not visual meshes), bakes from them, and
  renders a visible overlay with a HUD poly count.
- Single source of truth: removed the vestigial duplicate copies at `godot/` root
  (`godot/template/`, `godot/deli_counter_postimport.gd`, `godot/deli_level.gd`);
  `godot/addon/deli_counter/` is the only copy. Docs updated.

### Validation
- Walked the modular/resolver pipeline in-engine (Godot 4.7): deterministic build,
  collision, navmesh, and the baked resolver placing a module with correct rotation
  + collision (`_instance_module`) all confirmed on `fuel_stop_heist`. The `.tscn`
  + `theme_swap.gd` live-theming path is implemented but not yet walked — flagged
  experimental in the README.

## [0.41.0]
### Editor addon (plugin 0.18.5) + repo consolidation
- Test harness `player.gd`: WASD now works with zero Input-Map setup (reads
  W/A/S/D and arrows directly; still prefers dedicated `move_*` actions if a
  project defines them). Previously WASD was dead unless you hand-added actions.
- Test harness `level_test.gd`: F4 navmesh bake fixed — it baked an empty mesh
  (the level wasn't a source). Now parses the level's STATIC COLLIDERS (walls
  import as -convcolonly collision, not visual meshes), bakes from them, and
  renders the result as a visible overlay with a HUD poly count.
- Single source of truth for the addon: removed the vestigial duplicate copies
  at `godot/` root (`godot/template/`, `godot/deli_counter_postimport.gd`,
  `godot/deli_level.gd`). The self-contained `godot/addon/deli_counter/` is now
  the only copy. Docs updated to stop referencing the removed paths.

### Added — dims-aware module variants (per-width art-pass modules), both paths
- **Baked path** (`deli_counter.py`): `_resolve_module` now takes the slot
  `width` and tries a width-specific module first —
  `<type>_<theme>_<style>_w<cm>.glb` (cm = round(width*100)) — falling back to
  the generic `<type>_<theme>_<style>.glb`, then greybox. The slot manifest's
  `current_ref` records the actual resolved stem.
- **Primary path** (`godot/addon/deli_counter/theme_swap.gd`): the game-side
  overlay now carries a width token through the lookup. It parses the greybox
  module stem (`type_kit_style` or `type_kit_style_wNN`) and resolves the themed
  variant width-specific-first, then generic, then leaves greybox. So per-width
  theming works whether you ship a baked GLB or theme a live `.tscn`.
- Why: the resolver/overlay is type-keyed and instances modules at authored size
  (never scaled), so one generic file only fits slots whose width matches it —
  fine for uniform `wall` tiles, but mixed-width openings/remainders need
  per-width modules. (Alternative to authoring many widths: keep specs on a fixed
  opening-width palette so one module per type fits everywhere.)
- Strictly additive / backward compatible: no `_w<cm>` files present (or no theme
  set) -> byte-identical to 0.40.0. No schema change. Themed modules remain
  VISUAL-ONLY (greybox owns collision) and live in the Godot project
  (`res://art/zoo/`), not this repo.
- PARKED pending the in-engine walk of the 0.35–0.40 modular arc — do not tag
  until `_instance_module` rotation/collision is verified in Blender first.

## [0.40.0]
### Added — zoo generator (`build.py --zoo`)
- Generate a Godot "zoo" scene from a folder of module GLBs: every module knolled
  on a grid, each with a billboarded name label, plus scale references (a 2 m cube
  and a 1.8 m player pillar) so you read real scale at a glance instead of
  guessing from asset-browser thumbnails. The in-game asset catalogue from the
  gym/zoo/museum workflow.
- `python build.py --zoo --zoo-dir art\zoo --tscn-res-root res://art/zoo` ->
  `build/zoo.tscn`. Needs no Blender and no spec -- it's a pure layout over the
  folder. New `zoo_export.py` (bpy-free, also runnable standalone:
  `python zoo_export.py art/zoo`).
- A team/dev documentation artifact, not a mission shell -- DC generates it, the
  editor consumes it. Same instancing model as `--format tscn` (one PackedScene
  per module, reused), so editing a module updates its zoo entry too.

## [0.39.0]
### Added — Godot scene output (`--format tscn`)
- A second way to emit a building: instead of one baked `.glb`, write a Godot
  `.tscn` that **instances** the module GLBs -- one node per slot, each
  referencing `res://<root>/<ref>.glb`, positioned by the slot transform. Because
  every instance points at the one `PackedScene` resource, editing a module
  updates every instance in the editor (native Godot prefab behaviour) -- and the
  building scene instantiates into a mission scene as a unit.
- Both outputs read the **same slot manifest**, so the baked `.glb` and the
  `.tscn` never disagree about what goes where. New `tscn_export.py` is **bpy-free**
  and runs as a post-build step over `<name>.slots.json` (no Blender needed for
  the serialization itself).
- Usage: `build.py <spec> --format glb,tscn` (or `tscn` alone -- forces a `glb`
  build so the manifest exists). `--tscn-res-root res://art/zoo` (or
  `DC_TSCN_RES_ROOT`) sets where the module GLBs live in your project. Requires a
  modular build (`DC_MODULAR=1`) so slots exist; transforms convert Blender Z-up ->
  Godot Y-up to match the baked export.
- Baked-GLB path unchanged; this is purely additive.

## [0.38.0]
### Added — module resolver (the art-pass swap, at build time)
- When a **module library** is configured (`spec.module_library` /
  `DC_MODULE_LIB`) and a **theme** is set (`spec.theme` / `DC_THEME`), the
  modular emitter resolves each wall and opening slot to an authored module —
  `<type>_<theme>_<style>.glb`, falling back to `<type>_greybox_<style>.glb` —
  and **instances that module** at the slot transform instead of generating a
  box. Nothing resolves → it generates the greybox box as before, so the art
  pass is **progressive** (cover roles one at a time; uncovered roles stay grey).
- Modules are imported **once** and instanced via the shared-mesh cache (one mesh
  in VRAM), with visual and collision parts routed to their collections by the
  node-name suffix — so an opening module keeps its authored aperture collision
  rather than a sealing convex hull. Placement (rotation) comes from the slot's
  `rot_y`; modules are authored origin-centered.
- The slot manifest records the **resolved** ref (`wall_gasstation_01`) and a new
  `coverage` block (per role/kit: theme / greybox / generated) — the art-pass
  progress meter.
- **Opt-in and reversible:** no `module_library` → resolver off, geometry
  byte-identical to 0.37.0. This is the swap happening at DC build time, in
  Blender, producing the themed building GLB directly.


- The modular build now emits a **slot manifest**: one record per swappable
  module — every wall segment, every opening, and every placement — written as a
  sidecar next to the `.glb` / `.gameplay.json`. Each slot carries `slot_id`,
  `role`, `size_mod`, `style`, `current_ref` (the greybox module there now),
  `kit_axis` (`theme` for structural, `material` for props), a `transform`
  (translation + `rot_y` degrees + scale), and a `fit` block (dims, pivot,
  openings, collision) a themed replacement must match. See
  `docs/SLOT_MANIFEST.md`.
- This is the concrete **art-pass input**: lock the building, then author
  `<type>_<theme>_<style>.glb` files and the manifest is the work list +
  swap recipe (resolve `role`→theme module, fall back to greybox, instance).
  Wall modules and openings come from the modular emitter; placements (kitbash)
  are recorded too, so the manifest describes the **whole** building — grey and
  kitbash alike — uniformly.
- **Output-only — no geometry change.** The `.glb` is byte-identical to 0.36.0;
  this adds a sidecar (written only when the modular emitter produced slots) and
  threads a non-geometric `record_slot` flag through the wall emitter.


- Identical pieces now link a **single mesh datablock** instead of duplicating
  geometry, so the glTF export carries one mesh + N nodes. Godot imports that as
  one `Mesh` resource instanced by N `MeshInstance3D`s — one mesh and one texture
  in VRAM (the rest are just transforms), and editing the shared module updates
  every instance. New `share_key` on `_box` / `_col_box`; a shared module is
  baked to **real size** (object scale stays 1) so an art pass on the module
  isn't stretched differently per instance.
- **Modular walls:** repeated full-width wall segments collapse to one shared
  visual mesh + one shared collider (keyed by role + dims). Unique span
  remainders and opening pieces keep their own meshes. Only active on the opt-in
  modular path; the boolean wall path and any non-modular spec export
  byte-identically to 0.35.0.
- **Placements (durable reuse):** `_placements` now imports + joins each asset
  **once** and links the cached mesh for every later placement (was: a fresh
  import per instance). Author a wall/prop module as its own `.glb`, place it N
  times, art-pass the source file — the art pass persists across DC regeneration
  and is reused across every building, with one mesh/texture in VRAM. Fixes the
  per-placement duplication noted in 0.34.1.


- New `_emit_wall_run` decomposes each wall run into separate named pieces — a
  row of solid wall segments plus one piece per opening — instead of one
  boolean-cut box. Each piece is a matched visual+collision pair (a swap slot),
  so a fixed themed prefab can replace it 1:1 in the art pass.
- `[wall][doorway][wall]` / `[wall][window][wall]`: openings are their own
  pieces with `surface_roles` `doorway` / `window` / `breach` (wall segments
  stay `wall`). Doors leave the aperture void (walkable); windows get a sealed
  full-thickness pane so the shell stays exactly as sealed as before (vaulting
  is still game code — enterability semantics unchanged); breaches keep the
  removable `BREACHPANEL`.
- `module` (default 2.0 m) tiles each solid span into whole module segments + an
  end remainder. Set `module <= 0` for opening-decomposition only (no tiling).
- **OFF by default.** Enable per-spec (`spec.modular` / `spec.module`) or via the
  `DC_MODULAR=1` / `DC_MODULE=2.0` env vars (no spec_types change needed to try
  it). Existing specs rebuild byte-identical. `_exterior` and `_partitions` route
  to the new emitter only when modular is on; otherwise the boolean path is
  untouched.
- NOTE: to drive modular from a spec JSON, add `modular: bool` + `module: float`
  to `LevelSpec` / the schema (not included here — the builder reads them
  defensively via `getattr`, and the env vars work today regardless).

## [0.34.1]
### Fixed — walls now support any number of openings (multi-door / multi-breach)
- `_wall_collision` only resolved the FIRST passable opening on a wall. Any
  additional opening on the same wall had its hole cut in the visual mesh but
  left solid behind it — so it read as a doorway you couldn't walk through.
  This silently broke two real cases: a wall with **two doors** (only one was
  enterable) and a wall with a **door + a breach** (the breach was a dead hole).
  Found by walking a gas-station model with two front entrances.
- The collision now carves a void for every door/garage/breach on a wall, with
  a jamb between each, a lintel above each, and a sill wall below windowed
  openings. Every door on a wall is now walkable.
- Every `breach` opening now gets its own removable `BREACHPANEL` (visual +
  collision) filling the hole, so the shell reads **solid** in the greybox and
  the panel is what game code deletes to open the breach. Previously only a
  lone first-opening breach was panelled. Breaches remain a deliberate authoring
  choice — the kit never adds them on its own; a plain building has none.
- Geometry-output change (PATCH): rebuilt `.glb`s differ for any level whose
  walls carry more than one opening (most presets). Walk-test affected levels.

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
