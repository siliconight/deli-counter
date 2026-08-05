# Stairs and the art pass

**Status:** diagnosed, not implemented. Design decision recorded below.
**Measured:** 2026-08-05, on `art_probe_001` seed 5017 (lot-demo-ws).

## The report

Stairs render as untextured white boxes in a fully themed scene. They have
done so in every themed build.

## What is actually wrong

Nothing is broken. The capability was never built, at **either** end of the
pipeline, and two separate green checks made that hard to see.

### 1. Deli Counter draws stairs but never records them

Stair geometry is emitted at ten sites, every one of them tagging the mesh
`role="stair"`:

| function            | lines                    |
|---------------------|--------------------------|
| `_stairs`           | 1339, 1382, 1392, 1442   |
| `_stair_l_shaped`   | 1471, 1486, 1495         |
| `_stair_spiral`     | 1539, 1553               |
| `_fire_escapes`     | 1755                     |

A mesh role is not a swap-slot. Every other surface family has a recorder:

    _record_wall_slot        3 references
    _record_slab_slots       2 references
    _record_roof_slots       2 references
    _record_stair_slots      0 references      <-- does not exist

The manifest confirms it. 213 slots on the probe build:

    wall 185   window 10   doorway 7   floor 4   ceiling 4   breach 2   roof 1
    slots mentioning "stair": 0

So Zoo is never asked to build anything for a staircase, `kit.plan_kit`
never plans a module, and `themed_tscn` keeps the greybox visual because
there is nothing to put in its place. The white boxes are correct behaviour
for a manifest that does not mention stairs.

This is the third instance of one shape. Kitbashed placements were recorded
from the start; `Volume`s were drawn and not recorded until 2026-08-05
(`2d34853`, 11 vault/counter meshes rendering white); stairs are the same
omission again, and the largest one left.

### 2. Zoo has nothing to fill a stair slot with

49 species in `zoo_keeper/genome/species/`. There is a `stair_rail` — a
dressing prop that sits *beside* a staircase — and no `stair`. Emitting the
slot alone would produce a planned module with no recipe behind it.

Both ends need work. Doing either alone changes nothing visible.

## Why the stair regression suite is green, and is not lying

`stair_regression.py --quick` reports 48/48:

    every variant: stairs classified, oriented, physically clean;
    all occupied stories reachable.

That suite asks whether a staircase is *walkable*. It has never had an
opinion on whether one is *skinned*, because until now skinning a staircase
was not a thing this pipeline did. The sweep and the screenshot are not in
conflict; they answer different questions. Worth stating plainly, because
"the stair tests pass" was reasonable grounds to look somewhere else.

## Decision: SKIN IN PLACE, do not swap

Stairs are the only geometry in the building with a dedicated traversal
contract — `stair_regression.py`, `test_stair_clearance.py`,
`test_stair_containment.py`, and `nav_gate.py` all defend it. That makes
them the highest-risk swap in the art pass, and the risk is not symmetric:

* **Skin in place** — Zoo lays thin tread and riser plates ON the existing
  stair, `collision: "none"`, and the greybox visual is **kept** underneath.
  If the skin is misaligned you see a slightly wrong surface. The thing you
  walk on never changed.

* **Full module swap** (rejected) — the greybox visual is dropped and a
  generated staircase stands in, collider retained. Now what you SEE and
  what you WALK ON are two meshes free to disagree. That is the
  invisible-collision failure mode (`aaef3bc`) re-appearing somewhere new,
  and on the one system where being wrong means falling through the world.

* **Material only** (rejected) — zero risk and near-zero benefit; stairs
  stay flat-shaded boxes with no nosing or stringer relief, reading as
  greybox next to a dressed wall.

Note this makes stairs the FIRST slot family whose greybox visual survives
the swap. `strip_greybox_base` currently drops the visual for any slot that
got a module. That rule needs a per-role exception, and the exception must
be explicit rather than inferred from geometry — an inferred one is how the
`VAULT` / `VAULTLEDGE_0` substring bug got in.

## Implementation sketch, for whoever picks this up

1. **DC** — `_record_stair_slots(...)`, called from the build sequence
   beside the existing recorders (NOT from inside `_stairs`; see the note
   on `_record_slab_slots` about ordering — the recorders that ran too
   early read state their producers had not written yet). One slot per
   flight. `fit` carries `{steps, rise, run, width}`; `collision: "none"`;
   the 12 universal slot keys and nothing else.

2. **Zoo** — `stair` species + recipe building `steps` tread plates and
   `steps` riser plates from those numbers. `SKIN_THICK`, no collision.
   Mirror `floor.py`, which is 490 bytes and does exactly this shape of job
   for a slab.

3. **Composer** — `strip_greybox_base` gains an explicit keep-list of roles
   whose visual survives; `stair` is its first and only member.

4. **Tests** — the liveness kind, not the does-not-raise kind: assert the
   manifest CONTAINS stair slots on a multi-storey preset, and assert the
   composed scene's stair node count is unchanged after theming. A test
   that only checks "no exception" would stay green through the exact
   omission documented here.

## Open questions

* Spiral stairs (`_stair_spiral`) have curved treads. A rectangular plate
  per tread will not fit them. Either the species takes an angle per step,
  or spirals are explicitly out of scope for v1 and say so out loud rather
  than quietly producing wrong plates.
* `_fire_escapes` emits `role="stair"` too, but it is exterior steel, not
  interior finish. It probably wants a different style tag than an interior
  flight, and should not silently inherit the room's material.
