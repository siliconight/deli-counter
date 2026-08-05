# Working agreement: how to not infer past the measurement

Written 2026-08-06 after a session that found ten real defects and, along the
way, produced eight wrong explanations for them. The defects are fixed. This
is about the eight.

## The move that goes wrong

Every one of the eight was the same move: **find a correlation, name it a
cause, act on it before testing it.**

The cleanest illustration is two attempts at the same bug, hours apart.

**Went well.** The `agent_max_climb` sweep. The prediction was written down
first -- *"0.29 fails, 0.30 passes"* -- and then run. It flipped exactly
there, so the confirmation meant something. An earlier prediction of 0.20 had
failed the same way minutes before, and died instantly instead of becoming a
belief.

**Went badly.** The "visual treads bury the ramp" theory. It was plausible,
it explained the symptom, and a fix for it was written, tested for
correctness, committed, and described in the commit message as the cause --
all before any experiment that could refute it. The refuting experiment took
one command and produced a byte-identical navmesh. The theory was dead on
arrival and had already shipped.

## Five rules, each earning its place from a specific failure

**1. No fix for a mechanism until a stated prediction about that mechanism
survives a test.** The prediction has to be falsifiable in one run.
"This should improve things" is not one; "0.29 fails and 0.30 passes" is.
Would have killed three of the four stair theories before any code moved.

**2. Commit messages must not assert causes.** They are the most durable and
least revisable artifact in the repo. `d7d1f70`'s message states the
buried-treads cause as fact and will say so permanently; the correction lives
in a doc that message does not link to. Commits state what CHANGED and what
was MEASURED. Mechanisms belong in docs, where they can be edited when they
turn out to be wrong -- and they do.

**3. Record refuted theories with what killed them.** Cheap, and it works:
`NAV_GATE_FINDINGS.md` now stops the next reader re-running four dead ends.
A findings doc that lists only the conclusion throws away most of what the
work bought.

**4. Batch diagnostics.** Inference rate rises exactly when round-trips feel
expensive. Every mechanism question in this codebase needs a human at a
keyboard running Blender or Godot, so guessing feels cheaper than measuring.
It is not. One `foreach` sweep settled in a single command what four
exchanges of theory had not.

**5. Extra scrutiny when a finding fits the session's narrative.** The claim
that "every deli and gas station has an unreachable register" was fitting
data to the day's story -- *gates lie* -- rather than reading it. The real
explanation was a spawn convention working as designed. When something
confirms the theme too neatly, that is a reason to look harder, not to
publish.

## The structural piece

The pressure toward inference has a cause, and it is not impatience.

Work that could be run and tested directly -- `building_library`,
`layout_lint`'s rules, the presentation adapter's `plan_commands`,
`build_freshness` -- was right the first time and stayed right. Every
question that required a Blender build or a Godot bake was answered by
proposing a theory to a human and waiting, and those are the ones that went
wrong repeatedly.

So the highest-leverage investment is not discipline, it is **widening the
surface that can be checked without a bake**:

- Captured fixtures, like `testdata/strip_fixture.json` -- a real manifest
  replayed against pure logic. That test caught two opposite regressions in
  a rule that had already shipped wrong twice.
- Pulling decisions out of Blender/Godot into pure functions.
  `slot_owner_test`, `neighbour_pairs`, `marker_room_findings`,
  `stale_shells`, `_lot_archetypes` are all decisions that used to be
  entangled with a tool and are now testable in milliseconds.
- Printing the numbers a stage actually used. `nav_gate` computed
  `[nav-gate] bake: radius .. cell .. climb ..` for months into a captured
  buffer that was discarded, which is why "which numbers did this bake use"
  was unanswerable and had to be reasoned about instead.

Every one of those converts a future guess into a future measurement.

## The shortest version

Measure, then explain, then fix -- and keep the explanation somewhere it can
be corrected. When those come out of order, the fix is a coin flip and the
explanation outlives the correction.
