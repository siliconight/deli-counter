# Circulation gate — dressing must never block the player

A dressed building is only a level if the player can still move through it:
mount every ladder, pass every doorway, walk every stair. The dressing pass
(Patina placing Zoo props) reasons about walls and clutter zones, not about
movement — so the **circulation gate** checks the finished package instead of
trusting the placement.

Source of truth: `circulation.py` (pure, bpy-free). Consumed by:

1. `portable_building.build_package` — when a dressing layer is bundled, the
   manifest gets a `circulation_check` block
   (`{ok, volumes, props, conflicts}`).
2. Level Factory's compose driver (`run_presentation_compose.py`) — a package
   with conflicts **fails the compose job (rc 6)**; the pipeline records a
   red, not a blocked level.
3. `test_circulation.py` — unit suite in `check.py`'s pre-commit set.

## The reserved volumes

All derived from data DC already exports — no new schema:

**Ladder climb volumes** — from `gameplay.markers[type=ladder]`
(`x, y, z, climb_height, width, facing`). The volume matches the climb
contract Area3D the composer bakes: `width + 0.6` across,
`climb_height + 1.0` tall, protruding `0.8 m` onto the approach side. A prop
inside it blocks the mount or dead-stops the climb.

**Doorway apertures** — from `slots[role=doorway]`: the aperture
(`openings[0]` width × height above sill) extended `0.6 m` past **both** wall
faces. A crate hard against either face of an open door blocks passage just
as surely as one inside the frame.

**Stair footprints** — from `gameplay.stair_systems[].footprint_polygon`
(the reserved rect `stairwell.py` derives). The whole vertical column is
reserved: a prop at any height inside the shaft is on a flight, on a landing,
or floating in the well — all wrong.

## Spaces

Volumes are computed in spec/Blender Z-up space (the space `slots.json` and
`gameplay.json` are written in). Prop AABBs come from the dressing GLB's
nodes (GLB/Godot Y-up). `circulation.to_godot_aabb` converts with the same
`(x, y, z) → (x, z, -y)` mapping `tscn_export` uses, so both sides compare in
GLB space.

## Tolerance

Intrusions shallower than `PEN_MIN = 0.02 m` (2 cm) are ignored — skirting
overlap and bevel-deep grazes are not blockages. `penetration` in a finding
is the smallest-axis overlap: how far the prop must move to clear.

## When the gate fails

The compose log lists the offending props:

```
[compose]   crate_07 intrudes 0.31m into ladder:ladder_0
[compose] ERROR: dressing blocks circulation -- see circulation_check ...
```

Fix by re-running the dressing pass (Patina owns placement); the gate is a
backstop, not a mover. If a finding is a false positive, tighten the volume
derivation in `circulation.py` — never bypass the gate per-package.
