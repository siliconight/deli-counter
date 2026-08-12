# Nav traversal gate: first authoritative run

**2026-08-05.** `nav_gate.py --all` against 103 built shells with
`DC_GODOT=C:\Godot\4.7\Godot_v4.7-stable_win64_console.exe` (4.7.stable).
This is the first time the gate has ever run. Every prior "stairs
classified, oriented, physically clean; all occupied stories reachable"
came from `stairwell.py` / `navigability.py` reasoning about geometry,
never from a baked navmesh.

First run:

```
103 shells, 0 gate errors
121 stairs checked:  111 ok, 10 no_path
  7 shells FAILED traversal
 19 on-mesh unreachable markers across 11 shells (warn-only, so invisible)
```

## ROOT CAUSE: `build/` was two weeks stale

**Not a bug in the stairs. Not a bug in the bake settings.** The shells in
`build/` were older than the code that produces them.

```
build/mansion_a01.glb                          built 2026-07-21
stairwell.ramp_foot_extension (fixes this)   written 2026-07-29
```

**CORRECTION, later the same day.** The stale-build diagnosis holds -- a
rebuild fixed six of the seven shells -- but the attribution below to
`ramp_foot_extension` is WRONG and is kept only so the reasoning is
inspectable. Measured after the rebuild, `mansion_a01`'s ramp is
geometrically IDENTICAL to the pre-rebuild one: span 4.172 x 3.982 against
4.180 x 3.982, incline length 5.518 against 5.519, and the same +0.191 m lip
at BOTH ends. The stair went from `no_path` to `ok` with the ramp unchanged,
so something else in the build between 2026-07-21 and 2026-08-05 is what
fixed it. The 0.191 m lip is also not the discriminator: mansion carries it
at both ends and passes, while `cr_deli` reaches its floors properly at every
foot (-0.039 m) and fails on a +0.210 m head.

What the islands actually say, post-rebuild:

```
mansion_a01  165 polys,  2 islands  [163 @ -3.65..4.15] [2 @ 7.9]   -> connected
cr_deli      544 polys, 10 islands  [107 @ -3.0..0.30] [186 @ 0.30..0.45]
                                    [184 @ 0.60..6.90] + six fragments
             cr_deli_stair_0: lower on island 2, upper on island 3
```

cr_deli breaks at **y 0.30-0.60**, near the FOOT of the ground-to-first
flight, not at the head. The 186-poly island sitting in that band is most
likely counter and shelf tops -- it is a dense hand-authored deli, and
mansion is sparse. That is a different failure from the one described below
and it has not been diagnosed. It needs the navmesh looked at in Godot rather
than inferred from source geometry; four mechanisms were proposed from static
measurement here and all four were refuted by their own data.

`ramp_foot_extension` exists precisely for this failure, and its docstring
names it exactly:

> "The ramp is set half a step proud of the flight so its surface rides the
> step nosings. That is correct along the run and wrong where the run meets
> the floor... The result is a riser at the first step -- the exact thing a
> smooth ramp exists to remove... the ramp has to reach the floor rather
> than hover above it."

Measured on the shipped (pre-fix) `mansion_a01`: the collision ramp's top
surface stood **+0.191 m** proud of the floor at both ends. The effective
climb is `floor(agent_max_climb / cell_height) * cell_height` =
`floor(0.15/0.15) * 0.15` = **0.15 m** -- Godot floors it to whole voxels,
which `agent_contract.json` already documents. 0.191 > 0.15, so Recast
refused to join the ramp to the floor and the basement became its own
island.

Confirmed by rebuilding that one shell with the bake parameters untouched:

```
before rebuild:  stair mn01_stair_dn: no_path    markers 0/2    (climb 0.15 cell 0.10)
after  rebuild:  stair mn01_stair_dn: ok         markers 1/2    (climb 0.15 cell 0.10)
```

The remaining unreachable marker is `extraction_DRIVE` at snap 2.6 m -- an
exterior marker outside the baked building, which is benign (see Markers
below).

### Why the climb sweep pointed at 0.30

Walking `agent_max_climb` on the stale shell: 0.15, 0.18, 0.19, 0.20, 0.25
all produce byte-identical navmeshes and fail; 0.30 passes, adding exactly
2 polygons. That is the voxel flooring, not a property of the stair --
0.15..0.29 all quantise to one 0.15 m voxel, and the 0.191 m lip needs two.
The threshold measured the fossil correctly; the fossil was the problem.

### Three explanations that were tested and refuted

Recorded because each cost a round of work, and because "it must be X" was
wrong three times before measurement settled it.

1. **Stair steepness (rise:run).** Refuted: the steepest stairs in the
   library pass (`bt01_stair_n`, 1.18 ratio) while gentler ones fail
   (`mn01_stair_dn`, 0.95). In `apartment_walkup_a01` the wider, gentler
   switchback fails and the narrow straight run passes.
2. **Visual treads burying the ramp.** The theory was that the bake ate
   both the ramp collider and the 19 visual tread boxes, and the treads --
   sitting ~0.10 m above the ramp -- became the walkable surface, forcing
   connection by 0.20 m risers. Refuted directly: a collision-only bake
   produced a **byte-identical** navmesh, 165 polys and the same three
   islands. The visual meshes are coincident with the colliders and
   contribute nothing.
3. **A 0.20 m flip threshold.** Predicted from the 0.191 m lip; wrong,
   because Godot floors `walkableClimb` to whole `cell_height` voxels. The
   actual flip is 0.30.

## Markers: 19 real findings hidden in a warn-only section

Markers are warn-only by design, which is right for most of what they
report, but the section lumps two very different things together. The snap
distance separates them cleanly, and `SNAP_MAX` (2.0 m, from
`agent_contract.qa.snap_max_m`) is already the natural boundary -- the
observed gap sits exactly there:

```
snapped <= 1.5m, no path:  0.1 0.1 0.1 0.1 0.2 0.3 0.3 0.5 0.5 0.6 0.6 0.7 0.7 1.0 1.0 1.0 1.2 1.2 1.4
                                              (nothing between 1.4 and 2.1)
snapped  > 1.5m, no path:  2.1 2.3 2.4 2.5 2.6 2.9 3.1 3.6
```

- **snap > SNAP_MAX -- 94 occurrences, benign.** Almost all `extraction_*`:
  STREET, EXIT, YARD, LOT, DRIVE. Exterior markers outside the single
  building whose navmesh was baked. Nothing to fix.
- **snap <= SNAP_MAX -- 19 occurrences, real.** The marker landed *on* the
  navmesh (0.1 m is 10 cm) and still had no path from spawn: an objective on
  a disconnected island. 14 `objective_*`, 2 `loot_*`, 1 `patrol_point_*`,
  2 `extraction_*`.

These share the stale-build cause -- `mansion_a01`'s `objective_A` went from
unreachable to reachable on rebuild with nothing else changed. **Worth
re-checking after the full rebuild**; any that survive are genuine.

Distinguishing the two in the gate's own output is a real improvement and is
NOT yet implemented.

## Two places a skip still reads as a pass

Neither is fixed, both are one-liners, and both should wait until the
rebuilt sweep is green so that turning them on does not just block commits:

1. `check.py` calls `nav_gate.py --all` with no `--require`, so a missing
   Godot binary exits 0. This is why `All checks passed.` was printed for
   months against a gate that never baked anything.
2. `nav_gate.verdict()` returns `True` for a skipped shell.

## What was changed in this pass

- **`build_freshness.py` (new).** Compares every `build/*.glb` against the
  mtime of the modules baked into it and fails when a shell is older. This
  is the actual lesson: the gate did not skip, it ran thoroughly against
  stale inputs and reported with full confidence. `check.py` already does
  this for `CATALOG.md`; this is the same idea for the artefacts every
  downstream gate reads.
- **`nav_gate.gd` fallbacks were stale.** They read `climb 0.5` and
  `cell 0.15` -- the values from *before* both 2026-07 contract changes --
  under a comment claiming "fallbacks equal the ratified values". Now 0.15
  and 0.10, and `_envf` prints a WARNING when a fallback is used at all,
  since that means the contract never reached the bake.
- **`nav_gate.py` swallowed a missing contract.** `except Exception: env =
  None` silently dropped `nav_env()` and let the bake run on those stale
  fallbacks. It now errors.
- **The `[nav-gate] bake:` line is surfaced.** It existed all along inside
  `result["stdout"]` and was discarded, which is why "which numbers did this
  bake use" was unanswerable from the gate's output.
- **Collision-only bake: tried and reverted.** Restricting the feed to
  `-colonly` nodes was a no-op on the failing shell and did move others
  (`warehouse_a02` 222 -> 209 polys). Changing what every navmesh in the
  project is built from, with nothing to show for it, was not justified.

## Open

**Q1. 26 shells report no stair entries at all.** No `skipped` status and no
"rebuild with >= 0.76" note appears anywhere, so these have no traversable
stair systems declared in their `gameplay.json` rather than stairs the gate
declined to check. Plausible for `gas_station_a01/a02/a03`, `cr_gas`,
`gas_street` -- single storey. Needs checking for `airport_terminal_a01`,
`bank_tower_a03`, `casino_a01`, `courthouse_a03`, `arena_a02`,
`brewery_a03`, `freight_terminal_a01`: a bank tower with no stair system
would mean the gate passed it by examining nothing. **Unverified.**

**Q2. `cr_gas` and `gas_street` report byte-identical results** (298 polys,
same four markers, same snaps). Likely one spec is a copy of the other.

**Q3. A content fingerprint would beat mtime.** `build_freshness.py`
compares modification times, which a fresh clone can trip. Recording a hash
of the geometry sources into each shell's manifest at build time would be
exact; worth doing when `build.py` next changes.

---

# Marker scope: the discriminator is geometry, not snap distance

**2026-08-08.** `marker_scope_census.py` over all 135 shells in `build/`.
Pure: `<id>.gameplay.json` and `<id>.navgate.json`, both already on disk.

The section above is right that most unreachable markers are benign exterior
ones, and it ends by saying the distinction "is a real improvement and is NOT
yet implemented". Between then and now it stayed unimplemented, and Level
Factory grew a themed-selection rule keyed on `markers.reachable == checked`.
That rule kept **6 of 134** shells. Not one of the six was kept for being a
better building:

```
parking_garage        has NO extraction marker at all
cr_garage             extraction placed INSIDE the building
bank_branch_a04       extraction 1.0 m outside -- snap landed on connected mesh
freight_terminal_a03  extraction 1.0 m outside -- same
pvp_station_ref       extraction 1.0 m outside -- same
gas_station_a02       extraction 2.0 m outside -- one of only two lucky at that range
```

A filter meant to select the buildings most ready to wear a theme selected the
two least finished ones and four geometric accidents. It was reverted.

## SNAP_MAX is a proxy, and it comes apart in both directions

The rule proposed above -- `snap > SNAP_MAX` means exterior and benign --
correlates with being outside the building without being the same fact.
Over every unreachable marker in the library, the two classifiers disagree
ten times:

```
corner_deli_heist_01  objective_SAFE       snap 2.6   INSIDE  -- snap rule drops a real defect
corner_deli_heist_01  loot_VAULT_CASH      snap 2.4   INSIDE  -- ditto
cr_deli               objective_SAFE       snap 2.6   INSIDE
cr_deli               loot_VAULT_CASH      snap 2.4   INSIDE
night_deli            objective_SAFE       snap 2.6   INSIDE
night_deli            loot_VAULT_CASH      snap 2.4   INSIDE
cr_gas                extraction_FORECOURT snap 1.2   OUTSIDE -- snap rule reports a benign one
gas_station           extraction_FORECOURT snap 1.2   OUTSIDE
gas_street            extraction_FORECOURT snap 1.2   OUTSIDE
gs_corner_station     extraction_FORECOURT snap 1.2   OUTSIDE
```

Six dropped defects is the expensive direction. A gate that declines to look
is the failure this file already records twice.

## The fact both manifests already hold

`gameplay.json` carries `footprint` and every marker's `x, y`. Inside-ness is
arithmetic, not inference:

```
exterior  ==  |x| > footprint[0]/2  or  |y| > footprint[1]/2
```

Measured over all 135 shells:

```
extraction OUTSIDE the footprint x UNREACHABLE      99
extraction OUTSIDE the footprint x reachable         8
extraction INSIDE  the footprint x reachable        11
extraction INSIDE  the footprint x UNREACHABLE       1
no extraction marker at all                         16
```

The 8 exterior-but-reachable are not better buildings either -- they are
buildings whose extraction sits closer to the wall than the bake's inset:

```
1.0 m outside:   0 unreachable,  4 reachable
2.0 m outside:  89 unreachable,  2 reachable
```

Deli Counter places `EXTRACTION_STREET` at a fixed 2.0 m beyond the south
wall on most templates, and the reported snap is that overhang plus a
constant ~0.6 m -- 50 shells read `overhang 2.0 -> snap 2.6`. The number is a
template constant, not 99 independent placements.

An extraction point stands on the street. Lot lays the street when it
assembles the site. A per-building navmesh cannot contain it, so asking a
building-scope bake whether it is reachable puts the question at a scope
where its subject does not exist. The answer is "no" 99 times and none of
those answers are about the building.

## What the verdict looks like with exterior markers excluded

Keeping UNJUDGED as its own state, because `checked == 0` is a question
nobody asked:

```
interior markers all reachable  103 shells   43 families
an interior marker unreachable   15 shells   14 families
no interior marker judged        17 shells   17 families
```

`final_stand` -- walked 2026-08-07 with a stair into a wall and an objective
nobody can reach -- is still refused, on both conditions. `pharmacy_a02`,
which stood up in the same walk, is still admitted. The corrected rule keeps
the true positive and drops 92 false ones.

The 15 are the signal that was buried: `office`, `deli_a02`, `gas_station_a01`,
`strip_retail_a01` and `primos_pizza` each have an objective or loot marker on
a disconnected island, and every one of them currently reports `passed`.

## Open

**Q4. Where does the exterior verdict get made?** Splitting the building-scope
check without building the site-scope one deletes a check rather than moving
it. Deferring `extraction_*` to "judged at site assembly" is only honest if
something at site assembly judges it. Undecided.

**Q5. `cr_garage` extracts INSIDE itself.** Its `EXTRACTION_VEHICLE` sits
2.0 m inside the footprint. That is reachable and therefore invisible to every
gate, but a heist you extract from without leaving the building is a design
question, not a nav one.
