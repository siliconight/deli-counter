# Nav traversal gate: first authoritative run

**2026-08-05.** `nav_gate.py --all` against 103 built shells with
`DC_GODOT=C:\Godot\4.7\Godot_v4.7-stable_win64_console.exe` (4.7.stable.official).
This is the first time the gate has ever run. Every prior
"stairs classified, oriented, physically clean; all occupied stories
reachable" came from `stairwell.py` / `navigability.py` reasoning about
geometry, never from a baked navmesh.

```
103 shells, 0 gate errors
121 stairs checked:  111 ok, 10 no_path
  7 shells FAILED traversal
 13 shells affected once marker findings are included
 26 shells contain no stair entries at all  (see Q1)
```

## ROOT CAUSE: `agent_max_climb` 0.5 -> 0.15

Isolated on `mansion_a01` by running the gate script directly, which bypasses
`nav_env()` and so lets the bake numbers actually be varied:

| cell | climb | result |
|---|---|---|
| 0.15 | **0.50** | 142 polys, 2 islands, **both stairs ok** |
| 0.10 | **0.50** | 171 polys, 2 islands, **both stairs ok** |
| 0.10 | **0.15** | 165 polys, 3 islands, `mn01_stair_dn` **no_path** |

The third row is what `nav_gate.py` runs, because `nav_env()` injects the
ratified contract numbers. Cell size changes the poly count and nothing else;
**climb is the only variable that changes the verdict.** At climb 0.50 the
basement joins the main mass as one 140-poly island spanning y -3.65..4.15.
At 0.15 it splits off as its own 34-poly island and the stair has no path.

`agent_contract.json` records the change and, in the same field, the
assumption that made it look safe:

> `agent_max_climb_derivation`: "Was 0.5. ... Set to exactly one cell_height
> voxel (0.15) ... **Stairs are unaffected: Deli Counter gives them a smooth
> ramp collider rather than per-step boxes, so they connect by
> agent_max_slope, not by climb.**"

That last sentence is what needs re-examining. The bake runs
`PARSED_GEOMETRY_MESH_INSTANCES`, and on every one of the 103 shells the
primary parse returns nothing and falls through to the manual feed:

```
[nav-gate] parse produced 0 polys (588 MeshInstance3D in tree); retrying with manual mesh feed
```

So the geometry reaching the baker is **mesh instances**. If a stair's
surviving mesh is stepped treads rather than a ramp, it connects by `climb`
over its risers — and 0.15 refuses a riser that 0.50 allowed. That would
explain why dimensionally identical stairs pass in one shell and fail in
another, which no geometric property does (see the ruled-out table below).

**Not yet confirmed:** that the 10 failing stairs specifically lack ramp
geometry in their GLB while the 111 passing ones have it. That is the next
thing to check, and it decides the fix:

- if the ramps are missing -> fix the stair build so the contract's claim
  becomes true; do not touch `agent_max_climb`
- if the ramps are present -> the claim is wrong for another reason and the
  climb number needs revisiting, but reverting to 0.5 re-permits the 0.16 m
  kerb that the 2026-07-28 change existed to stop

The same fragmentation explains the marker findings below. One root cause,
two symptoms: an unwalkable stair (the gate fails) and an unreachable
objective (the gate only warns).

### Geometry is NOT the discriminator

Tested and refuted. Rise:run, shape, clear width and role all fail to
separate pass from fail:

```
status   stair             shape       rise   run  ratio  width
ok       bt01_stair_n      straight    4.60  3.90   1.18   1.60   steepest, passes
no_path  mn01_stair_dn     straight    3.80  4.00   0.95   1.60   gentler, fails
ok       a02_stair_e       straight    3.60  4.00   0.90   1.60   near-identical, passes
ok       aw01_stair_dn     straight    3.20  4.00   0.80   1.60
no_path  aw01_stair_up     switchback  3.20  4.00   0.80   3.20   wider+gentler, fails
```

Failures cluster by SHELL, not by stair dimension.

## Finding 1 — 10 stairs a player cannot walk up

| shell | polys | stairs |
|---|---|---|
| `apartment_walkup_a01` | 207 | `aw01_stair_up` |
| `construction_site_a02` | 114 | `cs02_stair_n`, `cs02_stair_s` |
| `country_club_a01` | 132 | `cc01_stair_n`, `cc01_stair_s` |
| `cr_deli` | 544 | `cr_deli_stair_0` |
| `mansion_a01` | 165 | `mn01_stair_dn` |
| `mansion_a03` | 214 | `mn03_stair_dn`, `mn03_stair_dn2` |
| `pawn_shop_a01` | 166 | `pw01_stair_0` |

## Finding 2 — 19 unreachable markers hidden in a warn-only section

Markers are warn-only by design, and the design is right for *most* of what
it reports — but it is currently lumping two very different things together.
The snap distance separates them, and the distribution is cleanly bimodal
with an empty gap:

```
snapped <= 1.5m, no path:  0.1 0.1 0.1 0.1 0.2 0.3 0.3 0.5 0.5 0.6 0.6 0.7 0.7 1.0 1.0 1.0 1.2 1.2 1.4
                                              (nothing between 1.4 and 2.1)
snapped  > 1.5m, no path:  2.1 2.3 2.4 2.5 2.6 2.9 3.1 3.6
```

- **snap > 1.5 m — 94 occurrences, benign.** Almost all `extraction_*`:
  STREET, EXIT, YARD, LOT, DRIVE. These are exterior markers outside the
  single building whose navmesh was baked. Nothing to fix; warn-only is
  correct.
- **snap <= 1.5 m — 19 occurrences, real.** The marker landed *on* the
  navmesh (0.1 m is 10 cm) and still has no path from spawn. That is an
  objective on a disconnected island. 14 `objective_*`, 2 `loot_*`,
  1 `patrol_point_*`, 2 `extraction_*`.

Shells with an on-mesh unreachable marker: `construction_site_a02`,
`country_club_a01`, `cr_deli`, `cr_gas`, `deli_a02`, `deli_a03`,
`gas_station_a01`, `gas_street`, `mansion_a01`, `mansion_a03`,
`strip_retail_a01`.

Six shells cannot reach ANY marker from spawn: `construction_site_a02` (0/2),
`country_club_a01` (0/2), `cr_gas` (0/4), `gas_street` (0/4),
`mansion_a01` (0/2), `mansion_a03` (0/2). In those the spawn itself is
probably on a small island.

`cr_gas` and `gas_street` report byte-identical results (298 polys, same four
markers, same snaps) — likely the same building under two names.

## IMPORTANT: `check.py` is now red, and only because Godot was found

```python
rc |= run(["nav_gate.py", "--all"])          # check.py:45 -- no --require
```

`nav_gate` exits 1 when a shell fails traversal, and `check.py` ORs that in.
So:

- **`DC_GODOT` set** -> `check.py` FAILS (7 shells fail). Correct, and it
  will block commits until the 13 shells are dealt with.
- **`DC_GODOT` unset** -> `find_godot` returns None, `nav_gate` prints a NOTE
  and `sys.exit(0)`, and `check.py` prints `All checks passed.`

`DC_GODOT` was set for one PowerShell session only, so the second case is
still the default. Making it permanent (or adding `--require`) turns the
build red immediately. That is a scheduling decision, not a technical one.

## Two more places a skip reads as a pass

Worth fixing whatever is decided about the shells, because both hide the
absence of a check rather than the result of one:

1. `nav_gate.main()` — no `--require` in `check.py:45`, so a missing binary
   exits 0.
2. `nav_gate.verdict()` — `if result.get("skipped"): return True`. A skip is
   returned as OK.

## Open questions

**Q1. 26 shells report no stair entries at all.** No `skipped` status and no
"rebuild with >= 0.76" note appears anywhere in the run, so these have no
traversable stair systems declared in their `gameplay.json` rather than
stairs the gate declined to check. For `gas_station_a01/a02/a03`, `cr_gas`,
`gas_street` that is plausibly correct — single storey. For
`airport_terminal_a01`, `bank_tower_a03`, `casino_a01`, `courthouse_a03`,
`arena_a02`, `brewery_a03`, `freight_terminal_a01` it needs checking: a bank
tower with no stair system would mean the gate passed it by examining
nothing. **Unverified — do not treat either way as established.**

**Q2. Why does the navmesh fragment?** ANSWERED — `agent_max_climb` 0.15.
See the root-cause section above. What remains open is whether the failing
stairs lack ramp geometry in the GLB.

## Fixed in this pass

Neither of these fixes the 10 stairs; both stop the gate misreporting its
own configuration.

1. **`nav_gate.gd` fallbacks were stale.** They read `climb 0.5` and
   `cell 0.15` — the values from *before* both 2026-07 changes — under a
   comment claiming "fallbacks equal the ratified values". Now 0.15 and 0.10,
   and `_envf` prints a WARNING whenever a fallback is actually used, since
   that means the contract never reached the bake.
2. **`nav_gate.py` swallowed a missing contract.** `except Exception: env =
   None` silently dropped `nav_env()` and let the bake run on those stale
   fallbacks. It now returns an error instead. The captured
   `[nav-gate] bake: radius .. cell .. climb .. slope ..` line is also
   surfaced in the verdict — it existed all along inside `result["stdout"]`
   and was thrown away, which is why nobody could see which numbers a bake
   used.

Note the side effect: direct `--script` runs now bake at the ratified climb
0.15 too, so the accidental "it passes when run directly" behaviour that
exposed this is gone. That was never a workaround, only a symptom.

**Q3. Is `cr_gas` a duplicate of `gas_street`?** Identical output suggests
one spec is a copy of the other.
