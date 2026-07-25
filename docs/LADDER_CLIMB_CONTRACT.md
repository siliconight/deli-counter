# Ladder climb contract — composed packages

Every ladder in a DC building (and therefore in every Level Factory `--art`
level) ships **climbable**, not just visible. Unlike a door there is no
networked state — a ladder is pure geometry plus player intent — so the
contract is a *content* contract: the package declares each climbable volume,
and whatever player controller the host game runs implements the movement.
LF's walk preview ships a reference implementation.

## What the package carries

`portable_building.splice_ladder_contract` bakes, per ladder in the DC
gameplay export (`markers` of type `ladder`: base anchor, `climb_height`,
`width`, `facing`), into the composed scene:

```
Ladders/                                Node3D container
  Ladder_<id>                           Area3D
      groups   = ["ladder_area3d", "dc_ladder"]
      metadata = climb_height (m), facing ("N"/"S"/"E"/"W")
      origin   = the ladder BASE anchor
      basis    = yawed so the node's +Z axis points at the APPROACH side
                 (the face a climber mounts from)
    CollisionShape3D                    BoxShape3D
      size     = (width + 0.6, climb_height + 1.0, 0.8)
      offset   = (0, climb_height/2, +0.45)   # protrudes onto the approach
    TopOfLadder                         Node3D
      position = (0, climb_height − 0.2, 0)   # the step-off height
```

The **+Z = approach side** orientation and the `ladder_area3d` group follow
the widely-used Source-style Godot convention, so third-party climb
controllers written against that convention work on DC packages unmodified.
The area protrudes 0.8 m so a falling or walking body can actually catch it —
paper-thin volumes are glitchy to mount.

The greybox ladder geometry itself (rungs + collision) is unchanged: the
Area3D is additive, carries no collision layers beyond the default, and never
touches nav or the placement gate.

## What a controller does with it (reference: walk preview)

`level_factory/assets/godot/player_walk.gd::_handle_ladder_physics`,
CS:S-style. All judgments are **relative to the ladder** via
`global_transform.affine_inverse()`:

1. **Latch**: while overlapping an area in `ladder_area3d`. First contact only
   latches deliberately — pressing toward the ladder (−Z) within 0.6 m of its
   plane, or arriving over `TopOfLadder` — and **only from the approach side**
   (local Z ≥ 0). From behind, a ladder is just a solid object: its own static
   collision applies and the climb never engages. Brushing past never sticks.
2. **Move**: the key wish direction, made camera-relative then ladder-relative:
   `climb = (wish_up + wish_into) / √2` — so looking 45° up the ladder while
   pressing W is the fastest climb (the Source optimum), looking level away
   descends, looking down feeds descent, and strafing into the ladder stacks
   with forward (the classic ladder-boost). `wish.x` slides along the rungs.
3. **Snap**: each frame the player is held on the climb plane (+0.45 m off the
   face); gravity and ground/air movement are skipped entirely while latched.
4. **Release**: walking off the bottom (on floor, descending, near the base),
   over the top (moving away above `TopOfLadder`), or Space to jump off the
   face (`basis.z * jump_velocity * 1.5`).

## Guarantees — the enforcement stack

Ladder traversability is guarded at every layer, so it cannot silently
regress in new buildings or new tool versions:

1. **Single source of truth** — `ladder_geom.py` (pure, bpy-free) computes
   the through-hole (approach-biased, 1.3 m along / width + 0.6 across) and
   the solid face plane (thin, full climb height). The builder
   (`deli_counter._ladders`), the linter, and the tests all import it — the
   builder and its guards cannot drift apart (the `partition_bounds`
   pattern).
2. **Spec lint, in the pre-commit gate** — `layout_lint` L14 (FAIL): an
   interior/shaft ladder whose through-hole overshoots the footprint (the
   climb dead-ends into the exterior shell — wrong facing for its
   position). L15 (WARN): a partition on the story the climb surfaces into
   crosses the hole. Exterior-wall/platform ladders (fire escapes) are
   exempt — no slab cut is involved.
3. **Unit suites, in the pre-commit gate** — `check.py` now runs the fast
   pure-geometry suites first (`test_partition_bounds`, `test_zfight_gate`,
   `test_ladder_bake`, `test_ladder_geom`): hole bias per facing, climb
   column containment, plane clearance vs the snap distance, Area3D
   group/orientation/metadata of the bake, and pinned 0.86.0
   walk-verified values so output can't silently change.
4. **Compose hard gate** — LF's compose driver fails the job (rc 4) when the
   gameplay export carries ladders but the package baked fewer climb
   volumes ("[compose] ladder gate"). A level with unclimbable ladders can
   no longer ship as "composed", same policy as the z-fight gate.
5. **Manifest evidence** — `ladder_climb_volumes` in
   `portable_resource_manifest.json` records the count for review.

No state, no scripts in the package: recipient projects that ignore the
contract see solid, collidable ladder geometry — never a walk-through.
