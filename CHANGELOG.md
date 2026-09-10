## [0.111.1] - 2026-09-10

The derivation follows the evaluator, which is what it was built to do.

### Changed
- `agent_contract.json`'s `sightlines` block re-derived against Laser Tag
  0.20.0 (roadmap 131), which gave every body ONE eye: crew 1.4 -> 1.6, enemy
  1.5 -> 1.6, aim unchanged at 1.0, so the crossing moves 1.2222 -> 1.3000.
  `level_design._COVER_HIGH_Z` and `combat_audit.COVER_BREAK_H` follow with no
  edit, and `_DEFAULTS` moves with the file because
  `test_every_fallback_equals_the_ratified_value` catches it otherwise -- which
  it did, on the first run after the contract changed.
- The block's `unreconciled` note becomes `resolved`. It recorded four
  disagreeing heights; reading the rest of Laser Tag's call sites found seven,
  and 0.20.0 collapsed them to one per body.

### Not changed
**The corpus flags the same 39 of 91 combat rooms at 1.3000 as at 1.2222**,
because nothing in it stands between 1.20 m and 1.40 m. That is the same
clustering 0.111.0 measured, and it means the two tools disagreeing about this
number by 8 cm had never once changed a verdict -- which is exactly why it went
unnoticed for as long as it did.

## [0.111.0] - 2026-09-10

Cover is measured against the firefight instead of against furniture.

### Added
- `agent_contract.json` grows a `sightlines` block, and `agent_contract.py` a
  `cover_break_height()` that DERIVES from it. A sightline is two lines: each
  side sights from its own eye at the other's chest, so one descends while the
  other climbs, and a solid tall enough to break one can sit under the other.
  Half a broken sightline is not half a fix -- Laser Tag stamps first contact
  on the first shot by *either* side, so the free shot that remains starts the
  clock exactly where it was. The shortest solid that breaks both is where the
  lines cross: `h = a - (a - c)^2 / (a + b - 2c)` = 1.2222 m, from the crew's
  1.4 m sight, the enemy's 1.5 m, and the 1.0 m chest both aim at. When the
  two sides sight from the same height it reduces to `(a + c) / 2`, which is
  the form `lot/site_cover.MIN_COVER_HEIGHT` already derives.

  The value is stored in the JSON and RECOMPUTED on read; a stored figure that
  disagrees with its own inputs by more than a millimetre raises rather than
  being quietly preferred. It is deliberately absent from `_DEFAULTS`, because
  a copy there would merge into every contract that omits it -- a studio
  setting its own sight heights would inherit ours, and the derivation would
  then be refused for disagreeing with a number that studio never wrote.

- `combat_audit` reports `COVER_ALL_LOW`: a combat room with cover in it,
  none of which breaks a sightline. Distinct from `KILLBOX` on purpose.
  KILLBOX says the room is bare and reads as obviously wrong to anyone who
  opens it; this one looks finished -- crates, desks, a counter, modelled and
  lit -- and every solid is short enough that both sides shoot over the top.
  It is the failure that survives a look at the screen, which is why it needed
  a number rather than an eye. **39 of the 91 combat rooms in the shipped
  presets, and every combat room in `pawn_shop` and `suburban_safehouse`.**

### Fixed
- `_COVER_HIGH_Z` was a chosen 1.4, which put the high/low boundary 0.18 m
  above the height where cover starts working and called the gap "low cover".
  Now derived. On the shipped corpus this moves exactly one piece
  (`compound/boss_desk`, 1.20 m) -- the authored heights already cluster
  either side of the crossing, with nothing at all between 1.10 and 1.20, so
  the corpus was split by this number and had no way to say so.
- `_room_has_cover` carried a fourth hand-written `0.6` instead of reading
  `_COVER_MIN_Z`, and would have gone stale the first time the constant moved.
- `combat_audit`'s `COVER_MIN_H` comment claimed "taller solids block sight =
  also cover", which is true of a 2 m shelf and false of the 0.9 m crate the
  threshold admits. Two questions were being asked of one number.
- The `KILLBOX` remedy advised "two or three 0.9-1.2 m volumes fix it" --
  heights that leave both sides a free shot. A remedy that reproduces the
  defect it is fixing is worse than none.

### Not changed, on purpose
- `_COVER_MIN_Z` stays 0.6 and low furniture keeps its `cover_low` marker. A
  0.9 m crate is a thing in the room, it reads as life, and a consuming game
  that implements crouch gets real shelter from it. Nothing in THIS toolchain
  crouches -- `characters.player.crouch_height_m` has no consumer in Laser Tag
  or Lot -- so what the new finding reports is that the EVALUATOR sees a bare
  room, not that the shipped game does.
- `_SEED_ARCHETYPES` heights are untouched. Seven of the nine pieces Deli
  Counter creates as cover stand below the crossing height, which is now
  reported per room rather than silently raised: how much of a room should be
  shelter and how much should be life is a design call, and the over-cover
  thesis this module is built on argues against answering it by raising
  everything.

### Measured
- 14 non-facade presets, on `combat_audit`'s basis (any solid over 0.6 m with
  a footprint of 0.3 m or more): 177 solids, 100 of them (56%) below the
  crossing height; 39 of 91 combat rooms furnished entirely below it.
- A narrower first pass counted only NAME-TAGGED furniture and reported 43 of
  91. It was wrong: it missed `parking_garage`, whose combat rooms are covered
  by structural columns that no name hint matches, and called two of them
  bare. Recorded rather than dropped.
- `test_cover_breaks_sightlines.py`: 11 tests, all 11 verified failing against
  the pre-fix modules. Full suite 648 passed, 2 skipped.

### Unreconciled, recorded in the contract
- FOUR heights describe one firefight and no two agree.
  `characters.player.eye_height_m` is 1.6 and `LT_PlayerPill.tscn` puts the
  Camera3D there, so the crew SHOOTS from 1.55 (the muzzle marker) and decides
  what it can SEE from 1.4 -- a body whose own muzzle sits 0.15 m above its
  visibility probe. The enemy sees from 1.5 and shoots from 1.3. Which of
  these moves is Laser Tag's call, not this file's, and moving one would move
  the crossing under a measurement taken this week.

## [0.110.1] - 2026-09-08

The contract says which radius is a body's, and its own fallbacks stop lying.

### Fixed
- `agent_contract.py`'s `_DEFAULTS` had drifted from `agent_contract.json` on
  the two keys the contract's own derivation notes record as REFUTED:
  `agent_max_climb_m` stood at 0.5 (the value that permitted a 0.49 m stringer
  four walkers parked against) and `cell_size_m` at 0.15 (which capped the
  connected slope at 45 deg against a stated 55, failing eight path proofs as
  disjoint islands). The module's docstring promises every fallback equals the
  ratified value; it had not since those values moved.

  INERT UNTIL IT IS NOT. With the contract present the JSON wins and the
  fallbacks are never read, which is why this survived unseen. The failure
  path is a missing, unreadable or partial contract: `nav_env()` then exports
  DC_NAV_CLIMB=0.5 and DC_NAV_CELL=0.15, and `nav_gate.gd` reads those with
  `_envf(name, fallback)` -- a PRESENT environment variable beats the fallback
  behind it. The GDScript copy was corrected when the values moved (`d7d1f70`)
  and this one was not, so the copy that was fixed gets overwritten by the
  copy that was not, and "degrades gracefully" means degrading to a navmesh
  measured to disconnect.

### Added
- `test_agent_contract.py` -- asserts every key `_DEFAULTS` and the JSON share
  holds the same value, pins the shared-key count so an empty intersection
  cannot pass for free, and exercises the missing-contract path through
  `nav_env()` directly. The guard is the fix; the two numbers are just today's
  instance of it. Verified to FAIL on the pre-fix state before being kept.

- `characters.player.radius_note` -- says plainly that a BODY is built from
  0.35 and that `nav_bake.agent_radius_m` (0.4) is a bake parameter with
  "fattest navigating character + 0.05 safety" folded in, with a matching
  pointer added to `nav_bake.note`. This confusion has now caused two defects:
  `clearances.unassisted_step_max_m` was once derived from the bake radius and
  recorded 0.117 while the gate enforcing it reported 0.103, and Laser Tag's
  evaluation pill was built at 0.40, running every door-width test against a
  proxy 14% fatter than the character it stood for (roadmap 123).

  The existing warning was real but buried inside
  `clearances.unassisted_step_derivation`, findable only by someone reading
  the step-height maths -- not by someone asking what radius to build a
  character at. `characters.player` has no reader in this repo at all; it is
  read by Level Factory, for consumers. The note belongs where they look.

## [0.110.0] - 2026-09-07

A building can step. Roadmap 116, the first massing move the pipeline has
ever been able to make.

### Added
- `Setback` on `LevelSpec`, and `setbacks.py` -- the per-storey footprint,
  which is the single source everything asks. `story` names the LOWEST storey
  an inset applies to and carries upward until a higher setback overrides it,
  so one entry steps a building once and two step it twice. Insets are
  per-side, so a side left at 0.0 stays flush: a street frontage holds the
  building line while the rear and sides step back.

  `footprint_x` / `footprint_y` KEEP THEIR MEANING. 24 source files read them,
  `lot/preview.py` and `lot/site_layout_lint.py` among them, and those place
  the building on a site and must know its widest extent. Setbacks only ever
  subtract, so those two remain the base footprint and therefore the maximum.

  OPT-IN, AND VERIFIED BY HASH: with no setback every expression collapses to
  what was there before. `night_pawn.glb` rebuilt bit-for-bit identical across
  the change, with only the manifest's `built_utc` moving.

- `layout_lint` L20 refuses a setback that cannot be built: deeper than the
  footprint, thinner than the storey's own two walls, at or below the base
  storey, or above the roof. The builder would happily emit all four.

- `specs/setback_demo.json` and `test_setbacks.py` (13 tests).

### Changed
- `_exterior`, `_slabs`, `_parapets` and `roofs.record` take the storey's own
  extent. An asymmetric inset MOVES the storey's centre, so each reads the
  centre rather than assuming zero -- a wall placed at +/- half a size would
  be in the wrong place.

  A SLAB CAPS THE STOREY BELOW IT, so it takes that storey's extent. That is
  what turns a setback into a walkable roof terrace with a real collider
  rather than a ledge the upper wall stands on the edge of, and it is the
  whole argument for changing the mass instead of adding a layer on top.
  Verified by raycast in the physics world on `setback_demo`: the strip beyond
  the inset reports a floor at z 4.00 on `slab_col_1` with 8 m of clear air
  above it -- open sky -- while a control point inside the upper storey
  reports the same floor with 3.70 m of head. It is a terrace, not a texture.

- `partition_bounds.clamp_partition_span` and `partition_spans` accept the
  storey's `extent`. The half-extent form cannot express an asymmetric
  setback: a storey inset 4 m from the north face alone runs -7..3, not +/-5,
  and a symmetric bound would let a wall poke out of the stepped facade AND
  cut it short at the face that did not move.

- `layout_lint` L13 and L19 measure against the storey's own facade, and the
  2D floorplan draws each storey on its own line.

### Measured
```
                        fill-Y  fill-X  masses
setback_demo             0.927   0.852       2
warehouse_a02 (twin)     1.000   1.000       1
```

The library baseline stays 127 shells at min 1.000, mean 1.000, because
nothing else opts in yet. `tools/massing.py` is the check.

## [0.109.0] - 2026-09-07

`fit.dims` means one thing now. Roadmap 119.

### Fixed
- `_record_wall_slot` records MODULE-LOCAL dims instead of world ones. The
  manifest carried two frames in one field, written by two sibling functions
  forty lines apart: `_record_opening_slot` has always put the opening WIDTH
  first regardless of which axis the wall runs on -- the module's own frame,
  waiting on `rot_y` -- while this function passed the world size straight
  through. On a N/S wall the two coincide, which is why it survived. On an E/W
  wall the world reading puts the wall's THICKNESS in `dims[0]`.

  Both consumers already expect the local reading: `zoo_keeper.kit.plan_kit`
  takes `dims[0]` as the module width, and `circulation.doorway_volume`
  unpacks `(width, thickness, height)`.

  MEASURED ACROSS EVERY MANIFEST BEFORE THE CHANGE. Every full wall segment in
  the library has a true run length of 2.00 m, so `_resolve_module` -- which
  correctly asks by `clen` -- requests `w200` 14704 times. `plan_kit`, reading
  `dims[0]`, derived w200 for 9106 and w30/w35/w25 for the other 5598:

  ```
  _resolve_module asks for   w200 x 14704
  plan_kit derived           w200 x 9106, w30 x 4819, w35 x 713, w25 x 66
  phantom                    5598 of 14704 full wall slots (38%)
  ```

  Those 5598 asked Zoo to author wall modules at names nothing can resolve.
  `cold-7001-ws` shipped 48 of 120 wall modules that way -- e.g.
  `wall_rockay_01_w35`, authored with `dims [0.35, 2.0, 3.7]`: a panel 35 cm
  wide and TWO METRES deep, built, packaged, and never placed.

  THE GEOMETRY WAS NEVER WRONG, and that is worth stating plainly because the
  numbers look alarming. Module resolution goes through `clen`, so the right
  module was always chosen and the right wall was always built. What this cost
  was Zoo authoring time, package size, and -- the part that matters most --
  the accuracy of the ONE report that says which modules a theme still needs.
  That report was 38% wrong on walls, and item 112's theme-coverage decisions
  read it.

  `scale` rides along, since it is derived from `dims` for `wallEnd`
  remainders: a unit box scaled by LOCAL dims and then turned by `rot_y` lands
  correctly, where world dims turned by `rot_y` would not.

### Changed
- Every shell's `.slots.json` is rewritten: wall slots on E/W walls now report
  `dims` with the run length first. `tools/massing.py` applies `rot_y` to
  match.

## [0.108.0] - 2026-09-07

A stair may not reserve ground outside its own building. Roadmap 115, and the
quarantine is empty.

### Added
- `layout_lint.stair_bounds_findings` -- L19 (FAIL). The stair half of L14,
  and a FAIL for the same reason that one is: L13's partition version is
  advisory because `_partitions` CLAMPS an out-of-bounds wall at build time,
  so the shipped geometry is already right. NOTHING CLAMPS A STAIR. It builds
  exactly where it was authored and the shell wall stays put, so the flight
  runs into it.

  IT MEASURES TO THE WALL'S INNER FACE, `footprint / 2 - wall_thick / 2`, and
  that is the whole point rather than a detail. `footprint_x / 2` is where the
  exterior wall is CENTRED, so a flight reaching exactly that already buries
  half a wall thickness of itself in solid. The first repair of
  `primos_pizza` moved the stair until it overshot the centreline by 0.00 --
  at which moment the centreline reading returned ZERO findings across all
  162 specs and the face reading returned one: the stair that was supposed to
  have just been fixed, still 0.15 m inside the north wall.

  An exterior stair is exempt: it stands outside the shell against a facade by
  design (spec s8.4).

  Measured across all 162 specs when written: ONE stair in one spec. It is not
  a rule looking for work.

- `test_stair_bounds.py` -- 7 tests, pinning the captured case, the failed
  first repair, the exemption, and the fact that no other spec trips it.

### Fixed
- `specs/primos_pizza.json` -- the stair moves from y 4.5 to 3.9 and its run
  shortens from 5.2 to 4.0. It now clears the north wall's inner face by
  0.15 m of real margin rather than sitting tangent to it, clips no partition,
  and pitches at 38.7 degrees.

  THE PITCH IS CHECKED BECAUSE SHORTENING A RUN STEEPENS A FLIGHT.
  `nav_bake.agent_max_slope_deg` is 55 and `CharacterBody3D.floor_max_angle`
  -- what a body actually stands on -- is 45, and `CLAUDE.md` records 20 of 38
  buildings already emitting 45.0-51.3 degrees. 38.7 sits in the same band as
  `walkup_siege`, which walks fine.

  The alternative was rejected on measurement: keeping `run` at 5.2 and only
  moving the stair puts its foot across the storey-0 partition at y 1.0, which
  would clip that wall and drop the door in it. Fixing a stair by deleting a
  door is not a fix.

- `primos_pizza` comes out of the roadmap-113 quarantine, which is now EMPTY.
  All three shells were re-admitted by fixing the generator rather than the
  shells. The dict is kept, with the history in its comment, because the next
  shell that fails traversal belongs there with its reason beside its id.

## [0.107.0] - 2026-09-07

The wall-over-void rule reaches ramps, not just stairs. Roadmap 117, the half
of it the library actually exercises.

### Fixed
- `_partitions` clips against RAMPS as well as stairs and authored holes.
  One function --
  `stairwell.wall_voids` -- now answers "what may a wall on this storey not
  stand ON or IN", so the builder, the 2D plan and the egress contract each
  make ONE call instead of unioning two dictionaries at three separate sites,
  and a fourth producer cannot be remembered at two of them and forgotten at
  the third.

  MEASURED PER PRODUCER ACROSS ALL 162 SPECS BEFORE ANY GEOMETRY MOVED,
  because a count that cannot be attributed cannot be checked afterwards:

  ```
  producer        walls    specs   doors lost
  ramp cut            3        3            2
  ramp footprint      1        1            0
  ladder hole         0        0            0
  vertical link       0        0            0
  ```

  A RAMP NEEDS THE SAME TWO KEYS A STAIR DOES, and that was the open question
  when 117 was filed. Its cut and its footprint are DIFFERENT rectangles --
  the cut sits half a run along the ascent axis, at the head of the climb --
  and `cbp_town`'s `int_0_1` stands in the footprint and in no cut. A rule
  written from cuts alone would have left a wall across a ramp.

  LADDERS AND `floor_hole`/`hatch` LINKS ARE DELIBERATELY NOT INCLUDED. Both
  open a slab, so the same argument reaches them, and a first cut of this
  change did include both. The count above is why they came back out: nothing
  in 162 specs stands a wall over either, so shipping those arms would have
  changed geometry on an argument alone -- with no case to check the result
  against, and no way to tell a correct rule from a wrong one. They go in with
  the spec that needs them and the count that shows it. A test pins the
  decision so it does not drift back in.

  (A ladder would take its through-hole only, never its footprint: it is
  mounted flat against a wall on purpose, so reserving the air in front of it
  would delete the wall it hangs on. Recorded because it is the part that is
  easy to get wrong later.)

- `Builder._ramps` takes its slab cut from `stairwell.ramp_hole` instead of
  spelling the rectangle inline. Two spellings of one rectangle is how a wall
  gets clipped against a hole the builder does not make.

### Added
- `stairwell.wall_voids`, `ramp_hole`, `ramp_footprint_rect`.
- 4 more tests in `test_wall_over_void.py` (28 total): the ramp's two
  rectangles, the wall that exposed this, `wall_voids` as a superset of the
  two calls it replaced, and the deliberate absence of the ladder and
  vertical-link arms.

## [0.106.0] - 2026-09-07

The two passes that CONSUME a partition learn that it can be built in pieces.
0.105.0 changed the geometry and left them reading the authored wall.

### Fixed
- `stairwell._door_nodes` derives a door's interactive id from the piece the
  door is actually in. The docstring has always promised "the SAME stable id
  the builder bakes", and a split breaks both halves of the derivation: the
  wall NAME (piece 1 bakes as `int_1_1p1`) and the POSITION (measured from
  that piece's centre, not the authored run's).

  MEASURED ON THE SHIPPED 0.105.0 BUILD of `night_pawn`: 3 of its 4 door
  nodes named an interactive that appears in no baked set. One of the three
  was the door in the middle of the staircase, which is not built at all. A
  door that survives in no piece is now SKIPPED -- a route through a doorway
  that was not built is not a route -- and an egress contract citing a node
  that does not exist reads as satisfied, which is worse than citing none.
  After: 3 nodes, 0 mismatches.

- `floorplan` draws a partition in pieces, from the same `partition_bounds`
  call, each in its own frame with its openings remapped. A doorway keeps its
  world position and one that fell in a removed part is not drawn, exactly as
  it is not built.

  A CORRECTION TO WHAT 0.105.0's NOTES CLAIMED: `_wall_and_openings` has
  always clamped the drawn extent to the footprint via `tx.hx`/`tx.hy`, so the
  plan and the builder never disagreed about the envelope -- only about the
  voids. It drew a wall ruled straight across its own OPEN TO BELOW hatch.

  The check that says so computes BOTH rectangles from floorplan's own
  transform rather than scraping the SVG: the first version regex-matched
  nothing and reported a clean bill of health over zero rows. Isolated against
  the old drawing it finds one overlap 33.6 px wide, the full width of
  night_pawn's shaft, so it owns exactly this change and can actually fail.

- `stairwell.derive` / `_door_nodes` take the pieces the builder actually
  emitted, instead of re-deriving them. Two derivations of one fact agreed on
  880 of the library's 882 door nodes and disagreed on 2: `slab_openings`
  reads `spec.slab_holes`, and the builder APPENDS to that list during the
  build, so `_partitions` asks before `_ramps` does its work and the gameplay
  pass asks after. `foundry_heist_vertical`'s `int_0_4` came back split for
  one caller and whole for the other. One derivation and a handoff cannot
  drift. The wall over that ramp is a real defect and is filed as roadmap 117
  rather than fixed here -- it needs the same per-producer count 114 made
  before it changes any geometry.

### Added
- `partition_bounds.piece_name` -- piece 0 keeps the authored name; later
  pieces take a `p<k>` suffix. It lives in the shared module because three
  passes in three processes have to agree on it, and a fourth spelling of
  "p1" is how an egress contract starts pointing at a node that is not there.
- 5 more tests in `test_wall_over_void.py` (24 total), covering the name, the
  door-node agreement, the skipped door, and the plan.

## [0.105.0] - 2026-09-07

A wall standing where a stair goes made the stair unwalkable, in fourteen of
the library's 129 shells.

### Fixed
- `_partitions` now clips every interior wall against the slab holes it
  stands over AND the flights it stands in. Two spellings of one sentence,
  and only fixing both makes a stair walkable:

  - a wall on storey k over a hole in storey k's slab stands on nothing --
    and where that hole is a stairwell, it is also a ceiling one storey
    height above the flight climbing through it;
  - a wall on storey k inside the footprint of a flight that CLIMBS THROUGH
    storey k is a wall across a staircase, and its own slab is intact, so the
    first rule never looks at it.

  `_partitions` runs BEFORE `_stairs`, so `spec.slab_holes` is empty when the
  walls are drawn and neither question can be asked from it. Both are answered
  from `stairwell.slab_openings`, which re-derives a flight's rectangle from
  the spec, and from the new `stairwell.stair_footprints`, which keys THE SAME
  rectangle at the storey whose air the flight occupies rather than the slab
  it cuts. The rectangle moved into `stairwell.flight_rect` so the two keys
  cannot drift; getting that off-by-one wrong is exactly what the first
  version of this fix got wrong.

  MEASURED ON `night_pawn`, one change at a time:

  ```
                              navmesh island 0     stair_0
  before                        y 0.19 .. 1.54     no_path
  clipped against its own hole  y 0.19 .. 2.89     no_path   (+1.35 m)
  clipped against the flight    one island         ok
  ```

  Found by raycasting UP from every tread after six static hypotheses had
  been refuted: `int_col_1_1_seg6` sat 2.05 m above tread 6, where the bake
  quantises the ratified 2.0 m agent to `ceil(2.0/0.15) * 0.15 = 2.10`. The
  control is `cr_pawn`, which carries a byte-identical partition, places its
  stair clear of it, passes, and whose treads see the 3.2-6.0 m of clear air
  that `night_pawn`'s now see too. The remaining 0.6 m was found by a second
  probe down the travel axis: `int_col_0_0_open1_lintel` at z 3.15, a
  storey-0 door lintel with the ramp running through it.

  THE CENTRELINE DECIDES, not the wall's thickness band. A stair's hole is
  oversized on purpose -- `width + 0.8` across, 0.3 m behind the bottom step
  and 0.8 m past the top -- so a band test would delete an enclosure wall
  seated flush against the shaft it encloses.

- Four doors authored inside a stairwell or an atrium void are no longer
  built, and each prints a named WARNING instead of vanishing. `night_pawn`'s
  `int_0_0` had one at world x 5.6, opening into the middle of a staircase.
  The void they sat in is a full-height gap, so nothing becomes less passable.

- `night_pawn` and `cbp_town_finale_midbalanced_schemafixed` come out of the
  roadmap-113 quarantine: `nav_gate` reports `ok` for `night_pawn`'s stair and
  for all four of `cbp_town`'s. `primos_pizza` stays quarantined -- it has no
  partition anywhere near its stair, and the same probe found its flight
  running through `ext_col_0_N_lintel1`, the EXTERIOR wall, because the stair
  is placed so its reserved footprint leaves the envelope. Roadmap 115.

### Added
- `partition_bounds.hole_cuts` / `subtract` / `partition_spans` /
  `remap_opening` -- the shared derivation, in the module whose docstring
  already claimed to be the single source of truth for a wall's built extent.
- `stairwell.flight_rect` / `stair_footprints`.
- `test_wall_over_void.py` -- 19 tests, no Blender, pinning the captured case
  and the `cr_pawn` control.

## [0.104.0] - 2026-09-06

`hospital` declared no zones and no objectives in any mode but `survival`, so
the first mission that ever asked for it failed every candidate.

### Fixed
- `presets.hospital` -- the non-survival branch now declares an extraction
  zone and an objectives list. `spec["zones"]` was assigned ONLY inside
  `if mode == "survival"`, so in `heist`, `assault` and `pvp_heist` the spec
  carried neither, and those are exactly the two things a heist scorecard
  reads.

  FOUND BY COLD RUN 6. `mercy_annex_001` asked for `archetype: hospital` and
  all three candidates failed `deli_generate`:

  ```
  TACTICAL-WARN:  heist level has no objectives defined
  TACTICAL-ERROR: heist level has no extraction zone
  errors: 1   warnings: 1        (exit=1)
  The generated spec has validation issues. This is a preset bug --
  please report it
  ```

  That last line was right, and it is the only reason this was found at all:
  `hospital` is one of fourteen presets in a seventeen-preset registry that no
  brief had ever requested.

  THE FIRST DIAGNOSIS WAS WRONG AND IS RECORDED HERE SO IT IS NOT REPEATED.
  The obvious reading is "hospital yields zero objectives", and a probe of all
  17 presets confirmed it is the only one that does -- but objectives are a
  WARNING. The fatal error was the missing EXTRACTION ZONE, which the same
  probe missed because it read the wrong key: extraction is declared in
  `zones[kind == "extraction"]`, not in a top-level field. Reading the failure
  log twice is what caught it.

  THE FIX REUSES WHAT THE PRESET ALREADY HAD rather than inventing a level.
  The survival branch already defines `helipad_extract`, and the docstring
  already says the team "reaches a rooftop helipad holdout ... to extract", so
  the helipad is the way out in both modes. The capture objective is the one
  the branch's own `ROOFTOP` marker already describes -- the room was retagged
  `objective_room` and the marker emitted, and only the spec-level list was
  missing, which is why the retag looked sufficient.

  `survival` is UNCHANGED: 0 objectives is correct for a survival run, which
  has a finale rather than objectives.

  VERIFIED through the real generator, not just the library: `python
  new_level.py --preset hospital --mode heist --seed 9002` exits 0 and
  validates, where it exited 1 before. Across modes, objectives / extraction
  zones now read survival 0/1, heist 1/1, assault 1/1.

### Known
Nothing checks that a registry entry produces a spec that validates. This one
was found by spending seven minutes of a cold run on it, and eleven presets
that no brief has requested remain unexercised. A probe over
`presets.REGISTRY` would cost seconds -- Level Factory roadmap 111.

### Also fixed, because the hospital fix could not be committed without it
`presets.py` is a geometry source, so editing it made all 139 built shells
stale by mtime and `build_freshness` refused the commit. The mandatory
`build.py --all` rebuild then let the pre-commit gate reach checks the stale
library had been hiding, and it failed `nav-gate: 6/159 shell(s) FAILED
traversal`. Attributing all six before touching any of them -- CLAUDE.md's own
rule -- split them into two unrelated causes.

- `build.py --all` and `--watch` now skip Level Factory's workspace
  transients. LF writes one spec per mission candidate into `specs/` as
  `lf_<mission>_<seed>`; `catalog.py` has excluded that prefix since roadmap
  73 and `building_library.index` refuses the ids, but `build.py` -- the one
  command that turns a spec into geometry -- had no such rule. It built 33 of
  them into `build/`, where the nav gate gated them like archetypes, and three
  (`lf_mercy_annex_001_9002`, `_9103`, `_9204`, from cold run 6 earlier the
  same day) failed traversal and blocked the commit the rebuild existed to
  unblock. Same rule, same prefix, same reason as `catalog.py`.

- THREE SHELLS QUARANTINED, and the quarantine says so on every `--all`.
  `night_pawn`, `primos_pizza` and
  `cbp_town_finale_midbalanced_schemafixed` have stairs that do not traverse a
  baked navmesh. Not built, which is the whole mechanism: no `.glb` for the
  gate to gate, and no `manifest.json`, so the lot pool stops offering them
  through the path the CLI already reports as "excluded from the lot for a
  missing manifest".

  MEASURED from the gate's own island data rather than reasoned from source
  geometry -- `docs/NAV_GATE_FINDINGS.md` records four mechanisms proposed by
  static measurement here and refuted by their own data. The shape is the same
  in all three: the ramp bakes as DISCONNECTED FRAGMENTS with a hole part-way
  up. `night_pawn` leaves a 1.95 m gap between islands at y 0.19..1.54 and
  y 3.49..3.79, with 2-poly crumbs stranded at y 1.24 and y 2.29..2.89;
  `primos_pizza` a 0.90 m gap. That is a DIFFERENT shape from August's
  finding, where `cr_deli` broke at the FOOT of its flight -- and `cr_deli`
  now passes, so the rebuild fixed the case that doc left open.

  NOT NEW: `NAV_GATE_FINDINGS.md` already listed `primos_pizza` among fifteen
  shells with markers on disconnected islands, "every one of them currently
  reports `passed`". What changed is that the stair check fails now the shells
  are built with current code.

  The specs stay on disk and the reason is written beside each id, so
  re-admitting one is deleting a line in `_QUARANTINE` after
  `python nav_gate.py build/<name>.glb` passes. Tracked as Level Factory
  roadmap 113.

## [0.103.1] - 2026-09-05

The catalogue indexed Level Factory's transients, and that was the one thing
standing between a gate-clean art pass and a package (roadmap 73).

### Fixed
- `catalog.py` skips `specs/lf_*.json`. Those are Level Factory's transient
  inputs for a running pipeline, not this library's content --
  `.gitignore:49` already excludes them and none is tracked.

  WHY IT WAS EXPENSIVE, and it is not about a noisy catalogue.
  `specs/CATALOG.md` IS tracked, `new_level.py` refreshes it after every spec
  write, and Level Factory folds a tool repo's dirty-TRACKED-file hash into
  the build fingerprint (`packages/adapters/sdk.py:_read_git_commit`, whose
  docstring excludes untracked files precisely so pipeline writes cannot bust
  the cache). Indexing lf_ specs therefore routed the one tracked file the
  pipeline touches straight into the fingerprint.

  MEASURED, before and after. One `new_level.py --preset bank` moved the
  revision from

      099a9cdc9dffac4c68aae6ccb9c6c87c04006304
   to 099a9cdc9dffac4c68aae6ccb9c6c87c04006304+dirty.cbd2f89b2b4fe547

  with `specs/CATALOG.md` the only dirty tracked file. After this change the
  same write leaves the revision byte-identical.

  THE CONSEQUENCE IT CAUSED. One `deli_generate` job changed the revision its
  own siblings key on, so every later job cache-missed -- including jobs the
  functional shell lock had just fingerprinted. `cold_7003` recorded the
  timing: lock approved 12:06:31.899, `deli_generate` re-evaluated at
  12:06:33.247 and `lot_assemble` at 12:06:38.478, 1.3 and 6.6 seconds later.
  The re-runs moved the gameplay-anchor and interactive registries,
  `verify_no_drift` reported both changed after the art pass, and the export
  was refused. `collision_fingerprint` never drifted -- the level's shape was
  never the problem.

  Cold runs 1, 2 and 3 all failed to produce a gated package; 3 failed here.

- CATALOG.md regenerated: 153 -> 129 levels, the 24 removed all `lf_`.

### Not bumped
`KIT_VERSION` stays 0.103.0. It names the BUILDER that stamps a model, and
`catalog.py` builds nothing -- the same reason 0.101.1 and 0.101.2 shipped
without moving it. Every manifest in `build/` correctly continues to record
the kit that produced it.

## [0.103.0] - 2026-09-04

`new_level.py` grows `--seed`. Every recipe pins its own seed as a literal --
casino_tower 1989, bank 1999, fifteen of them, years -- and nothing could
override it, so two callers asking for the same preset got the same building
forever. Level Factory was one of those callers: five candidates of a mission
produced five byte-identical shells (roadmap item 69).

### Added
- `new_level.py --seed N` and `presets.make(seed=N)`. The seed is injected
  between the recipe and the seed-consuming passes, which is the only place it
  works: `_finish_stairs` rolls the probabilistic extras on `spec.seed` and
  `level_design.enrich` seeds each room's cover on
  `f"{seed}:{room_id}:seed_cover"`, so a seed written into a finished spec
  changes the number the builder prints and nothing about the geometry.
  `stair_regression.generate()` has injected at this exact point since it was
  written; this exposes the same lever on the CLI.

### Measured, and it is narrower than the flag sounds
Seven presets, two seeds each, level name held constant so ids do not move:

    preset            stairs   ladders   volumes   markers
    casino_tower         0/1       0/1      8/14      8/23
    bank                 0/2       0/0      8/11      8/14
    warehouse            0/0       0/0      7/13      7/17
    hospital             0/2       0/0      8/18      8/22
    pawn_shop            0/1       0/2       2/6       4/9
    office               0/1       0/2      0/10      0/12
    parking_garage       0/1       0/0      0/25      0/12

The seed moves seeded cover and the markers derived from it. It moves NO
stairs and NO ladders on any preset tested, and on `office` and
`parking_garage` it moves nothing at all -- `seed_cover` skips rooms with no
`combat_range` and rooms that already carry authored cover. A first reading of
the raw diff said stairs varied; that was the id string carrying the level
name, which the instrument itself had varied. Shell, rooms and partitions are
byte-identical across seeds.

So this closes "every candidate is the same file" and does not close "every
candidate is the same building". Building variety needs a different lever --
the preset, not the seed.

## [0.102.1] - 2026-08-25

0.102.0's one regression, found by the gate it shipped with and fixed on the
floats rather than on a theory. The corner change closed 988 of 988 open
corners across the library and introduced exactly ONE new sub-5 cm gap --
`strip_retail_a01 ext_1_N`, 0.050 m before `ext_1_N_open0`.

### Fixed
- `_wall_span` computes a span's remainder ONCE and uses that value for both
  the absorb decision and the emit decision. It was computed twice, by two
  algebraically identical expressions that are not identical in floating
  point: `L - n * M` carries the error of `b - a`, `b - (a + n * M)` carries
  the error of `a + n * M`. Instrumented and rebuilt, the offending span
  reported

      ext_1_N_seg6  a=-9.85 b=2.2 L=12.05 M=2.0 n=6
                    L - n*M = 0.05000000000000071  -> too big to absorb
                    b - x   = 0.04999999999999982  -> too small to emit
                    hole    = 0.04999999999999982

  with the control case two spans down the same run --

      ext_1_N_seg9  a=3.8 b=9.85 L=6.05 n=3
                    L - n*M = 0.04999999999999982  -> absorbed, no hole

  -- ruling out coincidence. A threshold asked of two spellings of one number
  has a blind window either side of it, and a piece that lands in the window
  is neither absorbed nor emitted; it is silently gone. The threshold itself
  is unchanged at 0.05 and `_seg_box` still refuses anything at or under it.
  What changed is that both questions are now asked of the same float.

### How it was found
`tools/envelope_continuity.py` predicted `ENV_RUN_GAP 1` for the rebuilt
library and the real rebuild read 2. The extra one was not written off: a
temporary probe (`patch_dc_span_probe.py`, applied and reverted byte-for-byte)
printed `repr()` of every near-threshold span, which is precisely the
precision the manifest's 4-decimal rounding was hiding. The first hypothesis
about this defect was REFUTED before it was confirmed -- reconstructed from
the manifest it looked as though both expressions agreed, because the span was
assumed to start after the previous module (a=0.15) when it actually starts at
the run's inset edge (a=-9.85) and covers six modules. The reconstruction was
wrong; the mechanism was right. Only the builder knew its own inputs.

### Predicted
`ENV_RUN_GAP` 2 -> 1 on a rebuilt library, the remaining one being the
pre-existing `auto_shop_a02` gap whose whole span is under the threshold and
so has no module to absorb into. `ENV_CORNER_OPEN` stays 0.

## [0.102.0] - 2026-08-24

Roadmap 58: the exterior envelope closes at its corners. Every run used to
end ON the perpendicular wall's centreline -- `_exterior` builds an N/S run
`footprint_x` long centred at zero, and the E/W walls sit at `+/- hx` -- so
the outer quadrant of every corner belonged to nobody: a re-entrant notch
`wall_thick/2` a side, full storey height, open on two faces and open to the
sky. MEASURED before anything moved, over every slot manifest in `build/`
with `tools/envelope_continuity.py` (new, factory root): **988 open corners
across 124 buildings, zero clean**, and the notch tracks the wall thickness
and nothing else -- 0.150 m on the 0.30 walls (812), 0.175 on the 0.35 (152),
0.125 on the 0.25 (24). Half the thickness at three thicknesses is a rule,
not a tolerance. The first candidate mechanism ("nobody owns the turn") is
confirmed; a themed module narrower than its slot and seg-boundary rounding
are both refuted -- runs are contiguous to 1e-6 and land on exact integers,
and rounding does not produce one value 988 times.

### Changed
- `_emit_wall_run` grows `inset` and `corners`, both defaulted OFF. It has
  two callers and only `_exterior` asks for either, so interior partitions
  are untouched by construction rather than by hope. `inset` pulls the SOLID
  spans back to the perpendicular wall's inner face; openings do NOT move
  with it, because they are placed in `_exterior` as a fraction of the full
  run and arrive already positioned. That is the whole reason the inset sits
  at this seam -- shortening the run itself would slide every door inward and
  change every building's gameplay anchors. Measured first: 0 of 1088
  exterior openings come within a half-thickness of their run's end, so no
  aperture lands in the pulled-back zone.
- `corners` seats one post at each end of the run, centred on the run's own
  end coordinate so it spans the perpendicular wall's full thickness. N/S
  owns the corner (`corners=(axis == 0)`): two runs meeting there must not
  both fill it, and one axis owning it makes the winner deterministic rather
  than arbitrary.
- `_wall_span` ABSORBS a trailing remainder at or under the 0.05 m sliver
  threshold into the last module instead of dropping it. Dropping a sliver
  does not tidy a run, it opens a hole in one -- and insetting shifts every
  tile boundary, so remainders that used to clear the threshold stop clearing
  it. Predicted over the library, the corner change alone takes run gaps from
  1 to 15 (twelve of 0.050 m, three of 0.025, every one beside an opening or
  a run end); with the remainder absorbed it stays at 1. This is the only
  part of the change that also reaches interior partitions, and it strictly
  closes gaps rather than opening them. The absorbed module is emitted
  `size_mod="end"` so it stays a scaled `wallEnd` unit box and mints no new
  stem in any kit.

### Costs nothing in the kit
The post is `size_mod="end"`, so `_slot_typename` returns `wallEnd` -- the one
species Deli Counter scales, a unit box sized per slot. Zoo's
`exact = typ != "wallEnd"` gives it unit treatment with no change in that
repo, no new stem, and no new `.glb` in any kit: one more instance of geometry
every kit already carries. Priced against the alternative, an exact-fit corner
would be 18 modules per theme per style (18 distinct thickness x storey-height
pairs in the library) against one.

Zoo HAS an authored corner -- `wallCorner`, recipe plus genome, dated
2026-07-14, never once requested (roadmap item 64). It is deliberately not
used here: an L cannot ride the unit-box scale, because scaling a leg scales
its thickness with it, so it is structurally exact-fit. Promoting these slots
to it later is one function in each repo, when there is art to justify the
18x.

### Predicted, not built
Verified by modelling the patched emitter against all 124 readable manifests
and re-running the gate: `ENV_CORNER_OPEN` 988 -> 0, `ENV_RUN_GAP` 1 -> 1
(the remaining one is the pre-existing `auto_shop_a02` gap, whose whole span
is under the threshold and so has no module to absorb into),
`ENV_PLACEMENT_DRIFT` 0. NOT run through Blender: `deli_counter.py` imports
`bpy`, so the suite and a real rebuild are still owed. The acceptance test is
that gate reading 0 on a rebuilt library.

THE FUNCTIONAL LOCK WILL FIRE. Collision moves on every building, which is
exactly what `functional_shell_locked` protects. Re-approval is correct here,
not a workaround.

## [0.101.2] - 2026-08-24

L18 graduates WARN -> FAIL, on two measurements rather than a mood. The
authored library lints clean (0.101.1's surgery, 129 specs at zero L18),
and the new built-output probe (`tools/door_split_probe.py`, the
running-tree instrument in the factory root) read ZERO walls inside 45
jamb-pair-derived apertures on the composed lot_demo_001 -- the sighting
that opened roadmap 59 was fixed en route by the week's rebuilds. Its
four findings were all `AreaPanel_Surface` sign quads hanging in exterior
doorway spans: item 55's blank cards, three of four still carrying
engine-generated names, not walls. From here a spec that splits a doorway
fails its build instead of waiting for a walker with a screenshot.

### Changed
- `layout_lint.py`: `door_split_findings` reports into FAILS;
  `test_door_split.py` pins the graduation the same way it pinned the
  WARN. Generator avoidance stays the right authoring-side fix when the
  gate fires -- the FAIL is the backstop, not the fix.

## [0.101.1] - 2026-08-24

Roadmap 59's library surgery: the 33 L18 findings the new lint measured
across 28 specs, fixed at the source. Every fix slides the OPENING clear
of the partition end (never shortens the partition -- that opens a gap
between rooms); the default is KEEP-SIDE minimal motion, so the aperture
stays in the room it already mostly served, with three recorded classes
of exception: (1) crossings where keep-side was nonsense for the opening
(07_police_station and pvp_station_ref's `garage_bay` opened into the
LOBBY; it belongs to the garage), (2) five dead-center collisions
direction-picked from room roles (a breach lands in teller circulation,
not inside the fortifiable security office; a dock belongs to brew_back,
not the taproom; self_storage's breach keeps cutting into `vault_unit`,
because cutting into the objective is what a breach is for), and (3) a
bounds veto that flips across the partition when keep-side would run past
the wall corner (none fired). The parking family's `vehicle_in` was
adjudicated a DEFECT, not a lane divider: the wall it hit separates the
attendant booth -- the OBJECTIVE room -- from the deck, so the 5 m bay
half-opened into the money booth. Verification per spec: full lint before
and after, zero L18 remaining, and not one non-L18 finding gained or
lost anywhere.

### Fixed
- 28 specs re-authored: gas family x5 (`front_entry_east` 5.12 -> 4.75),
  deli family (`loading_bay` -9.5 -> -9.95 x4, `alley_entry` 5.04 ->
  4.95 x4), parking family (`vehicle_in` -> deck-side clear x4 incl.
  cr_garage), and singles (07_police_station, bank_branch_a04,
  brewery_a03, construction_site_a03, credit_union_a03, final_stand x2,
  freight_terminal_a01 x2, mansion_a02, marina_a03, pawn_shop_a02,
  pvp_station_ref, self_storage_a01/_a02, supermarket_a01). Geometry
  corrections -- the PATCH bump condition; every rebuilt .glb with one of
  these openings differs.

## [0.101.0] - 2026-08-24

Roadmap 59 opens its lint. Sighted 2026-08-23 walking lot_demo_001: one
doorway divided into two squeeze-past channels by a partition's WallEnd
standing mid-aperture, a wall edge-on to the door. Every engine gate
passes it -- both channels traverse -- so the check belongs at spec level,
before the geometry exists.

### Added
- `layout_lint.py` L18 (WARN): no partition may terminate inside a
  doorway's aperture span plus a 0.3 m leaf margin, on the wall it meets --
  exterior and interior hosts alike. Endpoints are judged through
  `clamp_partition_span` (the builder's own bound), so the lint and the
  shipped geometry cannot disagree; a wall CROSSING the aperture line is
  deliberately exempt (a different defect with different owners). WARN
  first, on the stair-volume lint's reasoning: it must not red an
  in-flight certification -- it graduates to FAIL once the library lints
  clean, and the floorplan generator learns avoidance (nudge the opening
  along its wall, or stop the partition one bay short; never silently
  delete either). Eleven tests pin the geometry and the exemptions
  (`test_door_split.py`). Numbered L18 because the 0.9x changelog assigns
  L17 to the stair-volume lint, which is absent from today's
  layout_lint.py -- that absence is its own open question, and the slot
  stays reserved.
- Spec output unchanged for every building -- the MINOR definition's
  second half; KIT_VERSION stays coupled.

### Fixed
- The navgate population baseline stops grading Level Factory transients.
  `lf_*` shells are LF pipeline side inputs built into this library's
  `build/`, and the baseline was absorbing them one hand-written entry at
  a time -- nine were already listed when `lf_unlit_probe_001_5017`
  red-flagged the 0.100.0 adoption commit as a "newly unjudged shell".
  `test_navgate_population._live` now excludes the class (the same call
  `layout_lint.main()` already makes for `specs/lf_*.json`; LF grades its
  own missions with its own gates), and the nine dead `lf_` entries leave
  `navgate_baseline.json` -- unjudged 17 -> 8, every remaining entry an
  authored shell with its reason intact.

## [0.100.0] - 2026-08-24

Roadmap 54's residue, measured to its end. Census #7 -- the first run with
every light already at its floor-pool minimum range (Lux 0.23.0) -- left 6
meshes over the engine's 8-light budget, and the census's new margin
forensics priced the range trims that would clear them at 0.44-1.59 m:
more than any floor can pay (an office pool would shrink to ~1.3 m against
4 m row spacing). The residue is geometry, in two shapes, both here.

### Changed
- `floors.SLAB_TILE` 8.0 -> 5.0. A tile's claimant count scales with its
  collection rectangle, (tile + 2*range) per axis: at 8.0 x 6.8 an office
  tile sweeps ~260 m^2 of lamp-bearing plan at 4.4 m ranges and bound 9-10
  claimants; at 5.0 the rectangle shrinks ~35% and the worst measured tile
  scales to ~6 -- under budget with headroom for a bake wobble. Zoo's
  `PLATE_TILE` stays 8.0 ON PURPOSE: its plates measured within budget at
  census #7, and this constant is now derived from THIS kit's lamp
  density, not from a geometry law the repos share. Buildings wider than
  5 m re-tile, so every rebuilt .glb differs -- the MINOR bump condition.
- Parapet VISUALS route through `floors.slab_tiles` -- census #7 caught
  the arena's 52 m `parapet_N` binding 9 lights, the one greybox visual
  that had escaped the tile law entirely. Runs inside the tile keep their
  exact name (small buildings unchanged by a byte); collision stays ONE
  box per run, because a collider has no light budget.
- `polybudget` mirrors the parapet splits, and stops counting E/W parapet
  runs on footprints too narrow to hold them -- the builder never emitted
  those, so the flat "4 boxes" estimate overcounted exactly that case.

## [0.99.1] - 2026-08-24

### Fixed
- Pendant density guardrails. Census #5 measured the first law's failure:
  `area / 25` alone gave the arena's 275 m^2 skybox suite ELEVEN bulbs
  1.5 m apart -- a chandelier row, not a moody cellar -- and every ceiling
  tile under it blew the per-mesh budget the type was priced for. Bulbs
  now cap at `_PENDANT_MAX` (5) per room and never pack tighter than
  `_PENDANT_MIN_SPACING` (3.5 m). A big room is supposed to have dark
  corners; that is what "moody" means. Two tests pin it.

## [0.99.0] - 2026-08-24

Census #4 left exactly NINE meshes over the per-mesh budget of 8 -- every
one a b0/b1/b4 floor or slab tile at 9-10 lights. Ranges were already
drop-derived and the tiles budget-sized, so the residue was lamp COUNT in
dense rooms: rows at 3 m spacing put an office grid over every interior.

### Changed
- `_TARGET_SPACING` 3.0 -> 4.0. A quarter fewer lamps per row puts the
  last nine tiles under the engine default, and wider pools read more
  like a 90s interior than an office ceiling -- the direction the palette
  was already chasing (0.98.0). If a room reads too dark, raise rig
  energy in Lux; density is a budget number first, a look second.
- KIT_VERSION 0.99.0 (stays coupled).

## [0.98.0] - 2026-08-23

Roadmap 57's palette, first entry: 90s Philadelphia is not lit by one
fixture type. A basement or an objective room -- a vault, a count room --
with an office fluorescent row reads like an office.

### Added
- The below-grade rule in `lights.py`: rooms with `story < 0` or
  `objective: true` derive `pendant` anchors instead of the fluorescent
  row -- sparse bare bulbs, one pool per ~25 m^2 (`_PENDANT_AREA`), hanging
  `_PENDANT_CORD` = 0.6 m below the slab, with the drop measured from the
  BULB so the range rule still reaches the floor. Same run machinery: a
  stairwell still splits the line around its hole. Lux >= 0.20 reads the
  type as a warm incandescent with a tight clamp and a filament waver;
  older Lux skips it with a count, so the rollout cannot half-light a room.
- `test_pendant_lights.py`: basement and objective rooms go moody at any
  storey, ordinary rooms keep the row, density (50 m^2 -> 2 bulbs,
  16 m^2 -> 1), the cord hang, drop-to-own-floor, void splitting.
- KIT_VERSION 0.98.0 (stays coupled).

## [0.97.0] - 2026-08-23

Roadmap item 54, the lighting contract's turn. A flat lux light range was
wrong at both ends inside one day: 8.0 claimed per-mesh budget slots two
rooms away through walls (the brightness grid), and the 4.5 trim left the
arena's ~5.7 m hall with a lit ceiling over a PITCH-BLACK floor -- Godot's
attenuation reaches hard zero at the range, so no energy value lights a
floor the range does not reach. Only this kit knows a room's height.

### Added
- Every derived fluorescent ceiling anchor in `<name>.lights.json` carries
  `drop`: metres from the lamp down to its own room's floor
  (`ceiling_z - floor_z`, storey-local -- an upstairs lamp's drop is to ITS
  floor, not the ground). Lux >= 0.19 derives the omni range from it:
  `clamp(drop + 1.5, 4.5, 8.0)`, a floor pool ~sqrt(3 x drop) m wide in
  every room, tall halls included, without re-claiming the whole per-mesh
  budget. Windows and wall hardware carry no drop -- they meter their own
  mounting, and a drop on them would be a guess wearing a number.
- `test_light_drop.py`: drop reaches the room's own floor, storey-locality,
  split runs share one drop, non-ceiling anchors carry none.
- KIT_VERSION 0.97.0 (stays coupled to the release).

## [0.96.0] - 2026-08-23

Roadmap item 54, the Deli Counter half -- the greybox base ships
full-footprint `slab_<n>` visuals (34-52 m on the shipped buildings), and
Godot budgets positional lights PER MESH (engine default 8), so one slab was
one light budget for a whole storey. Zoo 0.49.0 tiles its plate modules; this
release tiles the slab visuals the stripped base keeps, so the composed scene
has no room-spanning plate left from either side.

### Changed
- `Builder._slabs` emits the slab VISUAL as light-budget-sized tiles
  (`slab_<n>_t<j>_<i>`, `floors.slab_tiles`, 8 m law shared with
  `core.arch.PLATE_TILE` in Zoo -- duplicated deliberately across repos and
  cross-named so the pair is findable). A footprint inside the tile emits
  the single `slab_<n>` byte-identically. COLLISION IS NOT TILED: the one
  trimesh slab stays authoritative, keeps its boolean-cut holes, and a
  collider has no light budget. Proven in-session on pvp_station_ref
  (34 x 26 m, 4 storeys): 80 visual tiles at 6.8 x 6.5 m, four collision
  slabs exactly as before.
- `Builder._slab_holes_cut` cuts EVERY matching slab piece that overlaps
  the cutter, not the first name match -- on tiles, `break`-on-first would
  cut whichever tile the collection listed first and leave the stairwell
  capped, the exact walkthrough-ceiling defect the cut exists to prevent.
  Matching is name-boundary safe (`slab_1` cannot claim `slab_10`'s tiles);
  a tile the cutter swallows whole is removed (with its `surface_roles`
  entry) rather than booleaned into an empty mesh node. Same
  pvp_station_ref build: the stairwell straddles `slab_1_t3_0`/`_t3_1`,
  the hatches land on `_t3_4` and `slab_2_t0_4`, all four cut, both holed
  collision slabs unchanged.
- `portable_building.roof_covered_nodes` matches by CONTAINMENT in the
  roof slot's box (grown 5 cm) instead of AABB equality: the top slab a
  themed roof replaces is now a tile set, and equality would find none of
  them -- the whole set would z-fight the themed module. An untiled slab
  is contained in its own box, so the single-node case still strips;
  walls stop under the thin slab volume and rooftop props stand above it,
  so nothing else can be eaten.
- `polybudget.estimate` mirrors the tile count per storey (hole cost
  charged once), so the estimator's piece count matches what the builder
  now emits.

### Added
- `test_slab_tiles.py`: byte-identity for small footprints, the arena
  footprint tiles to budget size, exact reassembly, boundary-safe unique
  suffixes, no slivers, tile <= 0 disables; roof strip containment --
  every tile of a themed roof covered, untiled slab still matches,
  walls/rooftop props/parapets stay, greybox-fallback roof keeps all
  tiles.

The item closes when the per-mesh light census
(`tools/mesh_light_census.py`, factory root) shows zero meshes over the
engine default of 8 on a recomposed package and level_factory deletes
`PER_OBJECT_CEILING`.

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

