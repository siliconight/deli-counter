# Aspiration: procedural composition (`compose` mode)

> Status: **aspiration / design note**, not built. Captured so the thinking
> isn't lost. Prerequisite: finish the 10 presets first (they ARE the module
> library — see "Sequencing").

## The idea

Procedurally assemble levels by kitbashing preset-derived **modules** together,
and use the existing tactical validator (`tactical.analyze()`) as the
accept/reject gate so every generated level is guaranteed playable.
Replayability falls out of the seed: same seed → same assembly, new seed →
a different *valid* assembly.

## Why this is safe to pursue (the multiplayer-shell framing)

Deli Counter generates the **static, replication-free shell** — geometry that's
identical on every client and never syncs (see the README thesis). That's
exactly why procedural composition here is tractable where most
procedural-multiplayer-level ideas are nightmares: **you're composing
deterministic shells, not game state.** Assembling buildings never touches
replication, never creates network traffic, never risks desync. The seed
guarantees determinism; the validator vets geometry; the hard multiplayer
problem is untouched because it lives in the marker/anchor layer the tool
doesn't own.

## Two interpretations — keep them separate

- **A — compose at the room/wing level (inside one building).** Assemble a
  monolithic building from room-modules: a lobby + a stair core + two wings +
  a roof. Output is still one static shell. **Fits the current primitive.**
  This is the tractable one; pursue first.
- **B — compose at the building level (a compound of structures).** Stitch
  whole presets across open space (a bank beside a precinct across a
  courtyard). Needs the **outdoor/ground-plane primitive the tool lacks** —
  same problem as roadmap L3/L5/L10's open-space levels. Separate, larger,
  later. Don't conflate with A.

## The architecture: generate-and-test with the validator as oracle

The classic failure of procedural generation is producing geometry that looks
fine but is unplayable (disconnected room, unreachable objective, finale you
can't get to). Deli Counter sidesteps it because the validator *already* does
reachability + mode-completeness analysis. So:

```
compose(seed, mode):
    rng = seed
    for attempt in range(MAX_TRIES):            # bounded — never spin forever
        layout = assemble_modules(rng, mode)    # pick + snap modules by seed
        spec   = layout_to_spec(layout)
        errors, warnings, scorecard = tactical.analyze(spec)
        if not errors and _mode_completable(scorecard):
            return spec                          # playable — emit it
        rng = derive_next(rng)                   # reseed, try again
    raise CouldNotComposePlayableLevel(seed)     # honest failure, not a bad level
```

You don't need a generator that's *provably* correct — you need a dumb
generator that proposes and the existing validator that *rejects the bad ones*.
The validator built for offline-independence becomes the quality gate for
procedural generation. **That's the moat:** anyone can write a generator; the
reason this one produces reliably-playable levels is that the thing which
*proves* a level playable already exists. Most projects bolt validation on at
the end and suffer — here it's built first, and we generate *into* it.

## The convergence risk (the one genuinely unproven thing)

If the assembler places modules randomly, it fails the reachability check
constantly and you burn thousands of seeds to find one playable level —
replayability dies on generation time. The fix: make the assembler
**mostly-correct by construction** (snap modules edge-to-edge so connectivity
is *likely*), and let the validator catch the *rare* failures, not filter 95%
garbage. Get that ratio right and it converges fast; get it wrong and it
thrashes. **This is the assumption worth a throwaway spike to prove** before
building the real thing.

## What a module needs (the real new design work)

Each module must declare:
- its **footprint** (bounds it occupies),
- its **connection edges** ("my north edge can attach to another module's south
  edge") — think Wave Function Collapse / jigsaw edge-compatibility,
- its **role** in the mode (a heist needs an objective module + extraction; a
  survival run needs a safe_room start + a finale).

The assembler picks compatible modules by seed, snaps edges, emits a spec.

## Sequencing — why presets come first

The 10 presets ARE the module library. Every preset finished teaches what a
reusable chunk looks like (what's a lobby, a stair core, an objective room).
You can't design connection rules for modules you haven't built. So:

1. **Now:** finish presets 5–10. Each is a data point for "what's a module."
   Author them *with seams in mind* even while still monolithic.
2. **Bridge:** refactor presets from monolithic spec-generators into
   compositions of room-modules (interpretation A — same output, assembled
   from parts).
3. **Payoff:** `compose` mode — pick modules by seed, assemble, run
   `tactical.analyze()` as the accept/reject gate, reseed until playable.
4. **Separate/later:** the outdoor/multi-building primitive (interpretation B),
   which unlocks procedural *compounds* and the stubborn L3/L5.

## Cheap next step available now

A throwaway spike (3 crude modules + assembler + reject-reseed loop) that
answers only one question: *does generate-and-test converge, or thrash?* A few
dozen disposable lines. Green-lights the aspiration or surfaces the hard
problem early — without waiting on the presets.
