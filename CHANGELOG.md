## [0.95.0] - 2026-08-22

Roadmap item 46, step 4 -- the fields the pipe was built to feed. Now that
interactives ship to the handoff package (0.94.0 + lot/dispatch/LF), the
game finally reads what decides whether a thing shatters, splinters or
dents. "Populating them before the pipe is connected is decorating a
disconnected pipe" -- the pipe is connected; this is the water.

### Added
- `spec_loader._derive_opening_defaults`, run once at spec load: openings
  the author left bare get the values every authored spec already writes by
  hand (measured across all specs, nothing invented: window pane -> glass
  16/16; breach material -> host wall's material, explicit or palette
  default, 12/12; breach_class from material -- soft_wall on
  drywall/wood/glass 10/10, reinforceable on brick_ext/concrete 2/2).
  AUTHORED VALUES ALWAYS WIN, an unknown material derives no breach_class
  (a null stays honest where a guess would lie), and door/garage/vault/
  teller/safe_deposit fixtures stay untouched until a vocabulary for their
  own materials exists. Measured on pvp_station_ref: 9 windows and 2
  breaches go from null to annotated; mansion_a02 and the LF demo specs
  likewise.
- The interactive machines carry `material` / `breach_class` as ADVISORY
  fields (INTERACTIVES.md), stamped in `derive_interactive` and shipped in
  the gameplay entry -- so dispatch's interactives.json answers "what does
  a charge do here" without joining back to openings. setdefault: an
  authored override that sets either always wins. The slot view stays
  art-only.
- `tactical.py` warns on an UNRECOGNIZED breach_class, not just a missing
  one. Found the defect it guards against while building this: an
  LF-generated spec authored "reinforced" where floorplan.py reads
  == "reinforceable" -- one letter of vocabulary drift and the breach never
  got the treatment its author asked for. An unknown value is worse than
  none; it LOOKS annotated.
- `test_opening_defaults.py`: eleven checks pinning the law, the authored
  precedence, the honest nulls, and the machine/gameplay carry.

## [0.94.0] - 2026-08-22

### Added
- `themed_tscn` now instances EVERY interactive state, not just the default:
  a non-default state whose geometry differs (per `interactive.state_geometry`)
  rides as a HIDDEN sibling -- `<slot_id>_<state>`, `visible = false`, same
  transform -- so the shipped scene finally contains what the game's state
  machine swaps TO. The resolver, `state_variant_stems`, is the composer-side
  mirror of `zoo_keeper.core.kit.slot_variants`: same species rule (unmapped
  state -> the slot's own type), same deferral (state sharing the default's
  species is identical art today -- doors get no variant, exactly as the kit
  builds none), same style law (variants follow the style the BASE resolved
  to, style-01 fallback included; greybox-fallback slots get no variants).
  On cr_deli: 11 hidden variants (3 window `_broken`, 8 breach_wall
  `_breached`, 0 door), all six distinct variant modules landing as real
  ext_resources so `portable_building`'s bundling regex carries them into
  `art/zoo/` unchanged.
- Both siblings carry `metadata/interactive_id` (the stable gameplay.json id)
  and `metadata/interactive_state`, so netcode finds the pair without parsing
  node names -- names are for humans; metadata is the contract
  (docs/INTERACTIVES.md). The runtime swap is: flip visibility, toggle
  collision per `collision_per_state`, art already loaded. A late joiner is
  told which sibling is visible, nothing else.
- Stats/CLI report `state_variants` placed and `state_variants_missing`
  (state differs but its module is not in the library) -- progressive art
  stays honest about what it skipped.

### Changed
- The z-fight gate skips `visible = false` node blocks: a parked state
  variant is coplanar with its visible default BY DESIGN, and a mesh that
  does not render cannot flicker. The gate measures what renders at rest.
  The skip happens before the block's GLB is opened, and the new test baits
  it with a malformed variant GLB so a regression fails loudly.

## [0.93.0] - 2026-08-22

### Changed
- The `window` interactive machine now carries
  `state_geometry {"intact": "window", "broken": "window_broken"}`. It never
  had one because no broken-window species existed, so a breakable window's
  `broken` state was deferred forever and the resolver rendered intact glass
  on a pane the gameplay layer said was gone. zoo 0.48.0 added the species;
  with this block, a kit build on a manifest whose window authors
  `breakable: true` emits `window_<theme>_<style>_w<cm>_broken.glb`
  (measured on a 1.1 m test slot through zoo's builder: both variants
  built, PASS).
- `collision_per_state.broken` is now `False` for windows, matching
  breach_wall's breached state. The advisory used to claim a shot-out
  window still blocks, which contradicted both the art (the opening is
  passable; the frame carries its own collision, exactly as breach keeps
  its lintel) and the consumers (the lasertag destructible drops pane
  collision on break). Advisory stays advisory -- the game's destructible
  layer owns the actual toggle.

### Notes
- A window is interactive ONLY when its opening authors `breakable: true`,
  unchanged -- no existing spec changes meaning. The chain this completes:
  DC emits the machine and the stable id -> Zoo builds the intact and
  `_broken` art plus `glass_shard` debris, all skinned by the same
  Pixelcoat glass pack as the pane -> the game replicates the state enum
  per id (lasertag's `LT_DestructibleSync` is one such consumer, per the
  ownership table in docs/INTERACTIVES.md).

## [0.92.0] - 2026-08-21

### Added
- `navgate_baseline.json` and `test_navgate_population.py`. nav_gate reports
  `markers: 0 checked -- reachability UNJUDGED` for a shell with no marker whose
  type ends in `_spawn`, and the exit code is deliberately unchanged, so that set
  could grow with nothing failing. It is now frozen: a new entrant fails, and a
  shell that gets fixed must be removed or the test says so.

### Corrected
- A prior note recorded "3/135 shells fail, 18 have no spawn marker". Measured
  from the per-shell results: 3 stair failures is right
  (`cbp_town_finale_midbalanced_schemafixed`, `night_pawn`, `primos_pizza`), but
  the unjudged set is 17, not 18, and five of its members were never named --
  `cr_pawn`, `gs_auto_shop`, `gs_facade_rowhome`, `gs_facade_storefront`,
  `lf_art_probe_001_5017`.
- 16 shells report `navigable: null` against 17 unjudged. That is not an
  inconsistency: `night_pawn` also fails the stair gate, and `navigable` is a
  conjunction, so a stair failure forces `False` without marker state mattering.
  Recorded in the baseline as explained rather than filed as a defect.

### Notes
- WHAT THIS DOES NOT CERTIFY: it says nothing about whether these shells SHOULD
  have spawn markers. Twelve of the seventeen carry `RECORDED, NOT EXPLAINED`.
  Only `gs_facade_*` (facade-only, no interior) and `lf_art_probe_001_5017` (a
  probe artifact) are classified, and those from their names alone.
- The per-shell `.navgate.json` files live in `build/`, which is not committed,
  so the sweep SKIPS in a clean checkout. The baseline's own integrity is
  asserted there instead, so a clean checkout never reports a green sweep of
  nothing.

## [0.91.0] - the unresolved flag gets a reader

`_resolve_material` has always marked a material the spec does not declare
`"unresolved": True`. Nothing ever read that flag. It was set in one place
and consumed in none, so the condition it detects has been invisible for as
long as it has existed -- and it is not an edge case.

Measured over 142 specs: `ceiling_tile` and `tile` are missing from ALL of
them, `carpet` from 137.

### Added
- The build now prints unresolved materials, with the consequence spelled
  out rather than left to be inferred.

### What that condition actually costs
An undeclared material falls back to `default_material` -- and the fallback
is not only acoustic. `skin_style.style_for` falls back the same way, so the
material inherits the default's STYLE. Style selects the Pixelcoat pack and
goes into the module filename. 410 of 574 (building, plate material) pairs
resolve to style 1.

So a carpet floor, a tile floor and a concrete floor in one building have
been getting the same acoustics, the same skin and, when their dimensions
match, the same file. That last one surfaced first, as 19 stem collisions in
Zoo, and looked like a naming-law problem for most of a session.

### Not fixed here, deliberately
Adding `carpet`, `tile` and `ceiling_tile` to `presets._PALETTE` and
migrating the 139 existing specs is the actual fix. It is held back because
the palette's `acoustic` names ("Concrete", "Drywall", "Glass", "Metal",
"Wood") are consumed by gool, nothing validates them, and inventing
"Carpet" would fail silently downstream -- the same class of defect this
entry exists to end. It also changes how every interior in the project
looks, which deserves a session where it can be looked at.

## [0.90.0] - the prop stem mirror gains depth and height

### Fixed
- **`themed_tscn.module_stem` mirrors zoo 0.39.0.** A `prop` slot's stem now
  carries `_d<cm>` and `_h<cm>`, because a prop is free on all three axes and
  width alone named two different solids the same file.

  This file's own docstring is why it moves in the same patch: *"THE MIRROR OF
  `zoo_keeper.core.kit.module_stem`, and the two must change together. Neither
  side parses a stem; both CONSTRUCT it from the same slot, so they agree only
  by being kept identical."*

  Verified across every slot in the shipped corpus: **9,185 of 9,185 produce
  identical stems on both sides.** Measured on 52 of 136 buildings, 15 (28%)
  were affected before the fix; `cr_gas` had a 0.9x10.0x1.8 counter and a
  0.9x0.9x1.0 cube on one `prop_delco_04_w90`.

- `VOLUME_ROLES = ("prop",)` added, mirroring `zoo_keeper.core.kit`.

### Notes
- Wall, doorway and window filenames are unchanged. Only `role == "prop"` slots
  resolve to a new stem -- 84 across the sampled buildings, asserted.
- Existing built prop GLBs fall back to greybox until rebuilt, which is the
  progressive art path behaving as intended.

## [0.89.0] - Stairs a nav agent can actually walk

Seven of 135 shells failed `nav_gate --all` on stair traversal. Four are
fixed and engine-confirmed; the mechanism turned out to be the same number
in every case -- a Godot nav agent bakes at radius 0.40 and needs 0.80 m of
clear width, and each of these left less.

- **check.py:** `build_freshness.py` now runs BEFORE the nav gate. That gate
  grades the shells in `build/`, and a stale shell does not make it answer
  weakly, it makes it answer wrongly with full confidence. On 2026-08-12
  every shell in `build/` was 4.2 days behind the code; a ladder that
  `patch_dc_roof_voids.py` had already fixed still climbed into a solid roof.
- **layout_lint.py L17 (NEW, FAIL):** a volume must not narrow a stair flight
  below `AGENT_DIAMETER` (0.80 m). Footprint comes from
  `stair_core._core_of`, the same reservation the stair placer uses, so the
  lint and the placer cannot disagree about where a stair is. Deliberately
  narrow: measured across the specs to hand it fires on 1 of 8 failing stairs
  and 0 of 8 passing ones. Three wider rules were tested and rejected --
  "volume overlaps the stair well" flags a vault and a power cabinet that
  both bake fine. A lint that fails working buildings gets switched off, and
  then it protects nothing.
- **specs/office.json:** `elevator_block`, a 2.0 x 2.0 x 3.0 m solid, was
  authored at (0.0, 0.0) -- the exact coordinates of `office_stair_0`. It
  left 0.60 m of a 3.20 m flight. Moved to x 3.6. `nav_gate`: no_path -> ok,
  markers 0/1 -> 1/1 reachable.
- **specs/cr_deli.json, corner_deli_heist_01.json, night_deli.json:** three
  clones of one authored deli. A switchback's two runs meet at the stair's
  own x and `office_stair_door` was centred on that seam, so each run got
  half a 1.20 m door -- 0.60 m, against 0.80 m needed. Widened to 2.40 m.
  `cr_deli` now bakes as ONE island, y -3.00..6.90, 483 polys, which is the
  signature every passing shell has.
- **specs/night_deli.json:** the door fix moved its break up a floor rather
  than closing it. `planter_box_upper_hall_1` (z 3.30..4.20) left 0.76 m on
  the ascending run -- four centimetres short. Moved clear, along with its
  derived `AUTO_PLANTER_BOX_UPPER_HALL_1` cover marker, which would otherwise
  have sent bots to take cover behind nothing in a stairwell.

Still failing and NOT fixed here: `night_pawn` (1.00 m runs, and a story-1
wall with no opening over the flight), `primos_pizza` (undiagnosed), and
`cbp_town_finale_midbalanced_schemafixed`, whose first floor bakes as ten-plus
fragments plus 32 slivers across 63 islands -- a floor that failed to be a
surface, which no amount of moving furniture fixes.

## [0.88.0] - Material-driven skin styles (why only one Pixelcoat skin showed)

Style -- the axis Zoo/Pixelcoat vary skins on (module stems are
{type}_{theme}_{style:02d}_...) -- was pinned to 1 at every DC slot
emission site AND flattened by the composer's global --style flag, so
every building funnelled Pixelcoat's whole library through ONE skin.

- **skin_style.py (NEW, bpy-free):** material -> style mapping, 1-based
  spec.materials order. A surface's skin follows its MATERIAL (brick_ext
  vs drywall vs metal), deterministic and stable across rebuilds. Slots
  now carry both `style` and `material`.
- **deli_counter / roofs:** all slot emission sites derive style from the
  surface material (walls, openings, roofs; props keep default).
  category5 rebuild: 210 concrete / 45 glass / 50 drywall / 16 metal.
- **themed_tscn:** `resolve_slot_ref()` is THE shared resolution -- the
  slot's own style wins, with fallback to the style-01 module (a partial
  kit degrades to fewer skins, never to greybox). Composer, base-strip
  and placement gate all resolve through it; when they disagreed,
  fallback modules landed over unstripped greybox walls and the z-fight
  gate caught the 530-pair explosion before it shipped (the gates paying
  for themselves same-day). `style_fallback_to_01` is tracked in the
  portable manifest.
- `test_skin_style.py`: 6 tests (mapping, fallback chain, per-slot style
  precedence, style-01 degradation vs greybox); wired into check.py.

Styled kits materialize on the next zoo kit build (the slots now demand
styles 1..N with materials attached); until then packages render style 01
everywhere, tracked by the manifest metric.

## [0.87.0] - Ladder traversability locked in: lint + unit gates

Ladders now have the same can't-regress protection as the partition clamp
and the z-fight gate: one pure module owns the geometry, the pre-commit
gate lints and unit-tests it, and the compose refuses to ship without it.

- **ladder_geom.py (NEW, bpy-free):** single source of truth for the
  approach-biased through-hole and the solid face plane;
  deli_counter._ladders now cuts and collides via it (rebuilt output
  verified byte-identical to walk-tested 0.86.0).
- **layout_lint L14/L15:** L14 (FAIL) an interior/shaft ladder whose climb
  hole overshoots the footprint -- the climb dead-ends into the exterior;
  L15 (WARN) a partition crosses the hole on the story the climb surfaces
  into. Exterior-wall/platform ladders exempt. Corpus baseline: 125 specs,
  0 findings (the rule immediately caught -- and correctly exempted -- the
  two exterior fire-escape terminations).
- **check.py:** the gate now opens with the fast pure-geometry unit suites
  (partition_bounds, zfight_gate, ladder_bake, ladder_geom -- 34 tests,
  sub-second) so the contracts run on every commit, not just in CI.
- **Level Factory compose driver:** ladder hard gate -- gameplay ladders
  without baked climb volumes fail the compose (rc 4), same policy as the
  z-fight gate. "[compose] ladder gate [OK]: n/n climb volume(s) baked".

## [0.86.0] - Ladders: solid from both sides, passable at the top

Walk-testing 0.85.x ladders surfaced two more gaps, both fixed at the
source so every DC building carries them:

- **deli_counter:** each ladder now emits a thin COLLISION plane at its
  face for the full climb height (ladder{n}_plane) -- a ladder is solid
  geometry from both sides, and only the approach-side climb volume makes
  it traversable. The rungs/rails stay visual-only as designed.
- **deli_counter:** the cut_slabs through-hole is biased onto the APPROACH
  side (1.3 m along the approach, width + 0.6 across) instead of a
  symmetric width + 0.6 square: the climb volume holds a capsule ~0.5 m
  off the face, and the old symmetric cut jammed it against the rim so a
  body could never actually pass through to the upper floor.
- **Level Factory walk preview:** while-latched TOP EXIT -- once the body
  has climbed high enough that its feet clear the upper floor, pressing
  away steps off onto it (previously +Z wish always read as climb-down,
  so the top was unreachable). Climb snap distance tuned to 0.5 m, clear
  of the new collision plane.

## [0.85.1] - Ladders latch only from the approach side

A ladder's climb must engage only on the face a climber mounts from; from
behind it is just a solid object. The walk controller now refuses to latch
when the player is on the back half-space (local Z < 0) of the climb
volume -- the ladder's own static collision applies there, and pressing
"toward" it can no longer pull a body through onto the climb plane.
Contract doc updated to state the side rule explicitly.

## [0.85.0] - Climbable ladders: the ladder climb contract

Ladders in composed packages were visible geometry plus a point marker --
nothing a player could climb. Now every DC build (and every LF `--art`
level) ships each ladder CLIMBABLE, with no state and no scripts in the
package: the content declares the climb volume, the host game's controller
implements movement. docs/LADDER_CLIMB_CONTRACT.md is the contract.

- **portable_building:** `splice_ladder_contract()` bakes, per ladder in
  the gameplay export, an `Area3D` in group `ladder_area3d` at the base
  anchor, yawed so +Z faces the APPROACH side (the Source-style community
  convention -- third-party climb controllers work unmodified), with a
  full-height BoxShape3D catch volume (width + 0.6 x height + 1.0 x 0.8 m
  deep), a `TopOfLadder` child at the step-off height, and
  `climb_height`/`facing` metadata. Sub_resources are spliced before the
  first node and load_steps is kept consistent. The manifest records
  `ladder_climb_volumes`.
- **Level Factory walk preview:** `player_walk.gd` gains CS:S-style ladder
  physics -- all judgments relative to the ladder via its transform
  inverse; climb = (wish_up + wish_into)/sqrt(2), so looking 45 degrees up
  the ladder is the fastest climb, looking away descends, and strafing
  into the ladder stacks with forward (ladder boost). Deliberate mount
  (press toward the ladder near its plane, or arrive over the top), clean
  bottom/top exits, Space jumps off the face.
- `test_ladder_bake.py`: 6 tests pin the bake (group/orientation per
  facing, base-anchor conversion, top marker, splice parse order,
  no-ladder no-op).

## [0.84.0] - Z-fight gate + flicker-free compose

The composed art pass shipped coplanar surfaces: the roof module cohabited
the greybox top slab's exact volume (the flickering ceiling), and
full-story-height wall modules put their up-facing caps in the story
planes, coplanar with slab tops (flickering stripes along wall lines).
Invisible grey-on-grey; glaring once themed. Fixed at the composer, and
now impossible to ship: a coplanar-surface gate fails any compose that
would flicker.

- **portable_building:** `roof_covered_nodes()` resolves the greybox
  surface a ROOF SWAP replaces geometrically (the top slab's name carries
  no slot id, so the name-based strip could never find it) and
  `strip_greybox_base(..., drop_nodes=...)` drops it; the roof module now
  truly swaps the slab instead of cohabiting it.
- **themed_tscn:** wall-family modules (wall / doorway / window / breach)
  sink `SLAB_CAP_SINK` (4 mm) on placement -- their story-plane caps
  separate from the slab tops by more than the gate tolerance, below
  perception. Free-standing fixture roles and the roof stay untouched.
- **zfight_gate (NEW):** box-level coplanar-surface gate, pure geometry +
  pygltflib, no bpy. Flags same-plane same-facing overlapping face pairs
  with real interpenetration; abutments never flag; entombed pairs (fully
  buried in a third solid, alone or by joint cover) are suppressed as
  intel -- no camera can see them. Wired into `build_package()`
  (`zfight_check` in the portable manifest); LF's compose driver fails the
  job on findings. `test_zfight_gate.py`: 12 unit tests pin the rules.

## [0.83.1] - Partition footprint clamp (recorded retroactively)

Interior partitions authored past the footprint (a Y-wall given the X
half-width, etc.) rendered walls poking through the exterior shell.
`partition_bounds.clamp_partition_span` is now the single source of truth:
the builder clamps at build time (openings repositioned or dropped,
in-bounds partitions byte-identical), layout_lint L13 reports overshoot as
an advisory WARN, and four presets (casino_tower, suburban_safehouse,
corner_deli, rowhome) had their authored extents corrected.
`test_partition_bounds.py` covers clamp/lint agreement.

## [0.83.0] - Phase 4 Mega-Structures: 25 configs / 8 new families -> 100/36

Library complete: 100 configurations / 36 families, every one engine-green.
BOTH waves first-pass clean (13/13 + 12/12 nav & import, ZERO batch
iterations, zero post-engine fixes). New families: STADIUM (Citizens Bank
Park / Lincoln Financial / Subaru chassis + premium club level), ARENA
(Xfinity), CASINO (Rivers, gaming-floor cage), MARKET_HALL (Reading
Terminal), AIRPORT_TERMINAL (PHL), BANK_TOWER (Center City), LANDMARK_HALL
(Independence / Liberty Bell), TRAIN_YARD (SEPTA yard).

- **p4lib venue template:** the mature pattern book as a parametric factory
  (grand S hall + N service band + secure room at ground_west / basement /
  story1), with the tall-stair run rule and a new stair_margin() clearance
  rule (half-run + landing + 2.2 m approach) baked in -- straight tall
  flights can no longer hug a wall by construction.
- Venue shells ship as heist-relevant service interiors (concourse, cage
  line, count room, suite level); the full bowl is site-scale dressing
  downstream, per the levels-as-input boundary.

