# Navmesh connectivity check — "can enemies path to shoot you?"

This is the **authoritative** answer to whether AI enemies can navigate your
generated level. The offline `navigability.py` proxy (run by `validate.py`)
catches gross failures before Blender — narrow doorways, fully isolated rooms —
but it works at room-graph resolution and cannot see sub-room navmesh gaps,
slivers, or stairs that don't bake. A real navmesh can. Use this when you walk
the level in the test harness.

## What it tests

Navigation is a **gameplay-engine** concern, not something Deli Counter bakes
into the model — the tool produces the static shell, your game runs the AI. But
the *shell has to be navigable* for any AI to work, and that IS checkable. This
harness check confirms: from the player's position, a `NavigationAgent3D`-style
path exists across the baked navmesh to **every gameplay marker** (spawns,
objectives, extraction, finale, patrol points). If an enemy could path from the
player to an anchor, it can path the other way to shoot the player.

## How to use it

1. Open the level in the test harness (`level_test.tscn` with your `.glb`
   instanced, or via the Deli Counter plugin's "Set up & Play").
2. Press **F4** to bake a navmesh over the level geometry. You'll see the blue
   navmesh overlay on the walkable floor.
3. Press **F5** to run the connectivity check. Read the output in Godot's
   Output panel:

```
[nav-check] 12/12 markers reachable by a nav agent from the player
[nav-check] all anchors reachable -- enemies can path through the building
            to every gameplay point.
```

or, if something's wrong:

```
[nav-check] 10/12 markers reachable by a nav agent from the player
[nav-check] UNREACHABLE: objective_vault (snap 3.2m, off-navmesh),
            patrol_roof (snap 0.4m, no path)
[nav-check] -> an AI enemy could NOT path to those anchors. Check doorway
            widths, stair navmesh, and isolated rooms.
```

## Reading the failures

- **off-navmesh (high snap distance):** the marker sits far from any baked
  navmesh surface — usually a room the navmesh didn't cover (too small, walled
  off, or floor geometry didn't bake). The AI has no ground to stand on there.
- **no path:** the marker is on the navmesh but disconnected from the player's
  navmesh island — a doorway too narrow to bake through, or a stair that didn't
  generate a navmesh ramp. This is the classic "enemy stuck at the doorway."

## Tuning the agent

The bake uses `agent_radius = 0.4`, `agent_height = 1.8` (a typical humanoid).
If your game's enemies are a different size, edit `_bake_navmesh()` in
`level_test.gd` to match — a wider agent needs wider doors, and the offline
proxy's `AGENT_RADIUS` in `navigability.py` should match so the two checks
agree.

## Relationship to the offline proxy

| | offline `navigability.py` | this (F5) |
|---|---|---|
| runs | in CI, no engine | in Godot, needs a bake |
| resolution | room graph | real navmesh (capsule-accurate) |
| catches | narrow doors, isolated rooms | + slivers, stair gaps, sub-room holes |
| authority | pre-filter ("no obvious blocker") | truth ("navigable" / "not") |

Run the proxy on every commit; run F5 when you walk a level. A level that
passes both is one where enemies can genuinely path to the player.

## Headless automation: the stair traversal gate

The F5 check has a headless twin that needs no editor and no keypress —
`nav_gate.py` runs `godot/addon/deli_counter/nav_gate.gd` against a built
shell and its `gameplay.json`:

```
python nav_gate.py build/bank_job.glb     # one shell
python nav_gate.py --all                  # every built shell
python nav_gate.py --all --require        # CI: missing Godot = failure
```

For every traversable stair system it bakes a navmesh (same agent
parameters as F4) and proves a path between the stair's `nav_endpoints`
(lower ↔ upper; the polygon graph is undirected, so the reverse direction
is the same proof), plus the marker connectivity section above. Generation
fails when traversal fails: `check.py` runs `nav_gate.py --all` as a gate
step wherever a Godot 4 binary is available (`$DC_GODOT` or `godot4` /
`godot` on PATH; Godot 3 binaries are refused). Without Godot the step
notes the skip — the offline analyzers remain proxies until the gate runs.

Shells built before v0.76 carry no `nav_endpoints` and report
"skipped (rebuild with >= 0.76)".
