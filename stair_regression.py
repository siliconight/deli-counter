#!/usr/bin/env python3
"""
stair_regression.py  --  multi-seed proof of the stair contract (no Blender)
============================================================================
The generated-stair contract says every generated building has classified,
oriented, physically-clean vertical circulation. This sweep PROVES it instead
of asserting it: every multi-story preset is generated across N deterministic
seeds, in BOTH generation orders (the recipe's authored stairs, and
stairs-first core reservation), and each variant must satisfy:

  1. zero stairwell review errors (approach, discharge, enclosure, stacks,
     separation, entry/exit-faces-solid, landing reservations);
  2. every stair carries a role and an explicit facing;
  3. every generated-stamped stair has ZERO clearance findings;
  4. zero ladder review errors;
  5. zero navigability-proxy errors;
  6. every occupied story is reachable from grade (both directions -- the
     route graph's vertical edges are symmetric);
  7. the same seed yields byte-identical stairs (determinism).

    python stair_regression.py                 # default 10 seeds/preset
    python stair_regression.py --seeds 100     # the full proof
    python stair_regression.py --preset bank --seeds 25
    python stair_regression.py --quick         # 2 seeds; the check.py gate

Offline proxy resolution, stated plainly: this proves the SPEC contract.
The capsule-accurate truth is the headless Godot gate (nav_gate.py) run
against the built .glb.
"""

import argparse
import copy
import sys

import level_design
import ladder as ladder_mod
import navigability
import presets
import stair_core
import stairwell
from spec_loader import spec_from_dict

DEFAULT_SEEDS = 10


def _multi_story_presets():
    out = []
    for p in sorted(presets.REGISTRY):
        base = presets.REGISTRY[p]()
        if base.get("facade") or base.get("n_stories", 1) < 2:
            continue
        out.append(p)
    return out


def generate(preset, seed, stairs_first):
    """One deterministic variant: the recipe with `seed` injected before the
    seed-consuming passes (stair_place extras roll on it), finished exactly
    the way presets.make finishes."""
    spec = presets.REGISTRY[preset]()
    spec["seed"] = seed
    spec["name"] = f"sweep_{preset}_{seed}"
    presets._finish_stairs(spec)          # orientation before enrichment
    if not spec.get("facade"):
        level_design.enrich(spec)
    if stairs_first and spec.get("n_stories", 1) >= 2:
        arch = stair_core.DEFAULT_ARCHETYPE.get(preset)
        if arch is None:
            return None
        stair_core.core_first(spec, arch)
    presets._finish_stairs(spec)
    presets._finish_ladders(spec)
    return spec


def check_variant(spec):
    """Return a list of failure strings for one generated spec (empty=pass)."""
    fails = []
    sp = spec_from_dict(spec)

    serrs, _, _ = stairwell.check(sp)
    for e in serrs:
        fails.append(f"stairwell error: {e}")

    for i, st in enumerate(sp.stairs):
        sid = stairwell.stair_ident(st, i)
        if getattr(st, "role", None) not in stairwell.STAIR_ROLES:
            fails.append(f"{sid}: missing/unknown role {st.role!r}")
        if getattr(st, "facing", None) not in ("N", "E", "S", "W"):
            fails.append(f"{sid}: missing facing")
        if (getattr(st, "meta", None) or {}).get("generated_by"):
            for code, msg in stairwell.clearance_findings(sp, st, sid):
                fails.append(f"{sid}: {code} on a generated stair")

    lerrs, _, _ = ladder_mod.check(sp)
    for e in lerrs:
        fails.append(f"ladder error: {e}")

    nerrs, _, _ = navigability.check(sp)
    for e in nerrs:
        fails.append(f"navigability error: {e}")

    # every occupied story reachable from grade
    import audit_specs
    reached = audit_specs._reach(sp)
    occupied = {r.story for r in sp.rooms}
    for s in sorted(occupied - reached):
        fails.append(f"story {s} has rooms but no vertical circulation "
                     f"reaches it")
    return fails


def run(seeds=DEFAULT_SEEDS, preset=None, verbose=True):
    """Sweep. Returns (variants_run, failures) where failures is a list of
    (preset, mode, seed, message)."""
    targets = [preset] if preset else _multi_story_presets()
    failures, ran = [], 0
    for p in targets:
        for mode, stairs_first in (("authored", False), ("core_first", True)):
            baseline = None
            for k in range(seeds):
                seed = 1000 + 37 * k          # deterministic seed schedule
                spec = generate(p, seed, stairs_first)
                if spec is None:
                    continue
                ran += 1
                for msg in check_variant(spec):
                    failures.append((p, mode, seed, msg))
                if k == 0:
                    baseline = generate(p, seed, stairs_first)
                    if baseline["stairs"] != spec["stairs"]:
                        failures.append((p, mode, seed,
                                         "nondeterministic stairs"))
            if verbose:
                n = sum(1 for f in failures if f[0] == p and f[1] == mode)
                print(f"  {p:20s} {mode:10s} {seeds} seed(s): "
                      f"{'OK' if n == 0 else f'{n} FAILURE(S)'}")
    return ran, failures


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--preset", default=None)
    ap.add_argument("--quick", action="store_true",
                    help="2 seeds per preset (the check.py gate)")
    args = ap.parse_args()
    seeds = 2 if args.quick else args.seeds

    print(f"stair regression sweep: {seeds} seed(s) per preset per mode")
    ran, failures = run(seeds=seeds, preset=args.preset)
    print(f"\n{ran} variant(s) generated, {len(failures)} failure(s)")
    if failures:
        for p, mode, seed, msg in failures[:40]:
            print(f"  FAIL {p} [{mode}] seed={seed}: {msg[:140]}")
        sys.exit(1)
    print("every variant: stairs classified, oriented, physically clean; "
          "all occupied stories reachable.")
    sys.exit(0)


if __name__ == "__main__":
    main()
