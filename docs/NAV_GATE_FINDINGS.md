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
