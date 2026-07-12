#!/usr/bin/env python3
"""
audit_specs.py  --  content-coherence audit across all specs (no Blender)
=========================================================================
Schema validation proves a spec is well-FORMED; this proves its vertical-
circulation content is COHERENT. Complements check.py (which runs the gate
per spec) with cross-cutting structural checks the gate doesn't do:

  1. trapped floors -- an interior upper-story room no stair/ladder/vlink reaches
  2. out-of-range spans -- a stair/ladder whose story span leaves the building
  3. derivation completeness -- every derived ladders[] entry has its full
     runtime contract (route_nodes, nav_link, authority, ai, combat, ...)
  4. egress invariant -- no ladder ever counts as primary egress or public
     circulation (ladder spec s2), across every spec

Exit non-zero if any hard finding is present; warnings are printed but do not
fail. Run: python3 audit_specs.py [--strict]
"""

import argparse
import glob
import json
import sys

import spec_loader
import ladder
import stairwell


def _reach(spec):
    """Set of stories reachable from grade by any circulation element."""
    reached = {0}
    for st in spec.stairs:
        if st.from_story is not None and st.to_story is not None:
            reached.update(range(min(st.from_story, st.to_story),
                                 max(st.from_story, st.to_story) + 1))
    for ld in spec.ladders:
        reached.update(range(min(ld.from_story, ld.to_story),
                             max(ld.from_story, ld.to_story) + 1))
    for vl in getattr(spec, "vertical_links", []):
        if vl.from_story is not None and vl.to_story is not None:
            reached.update(range(min(vl.from_story, vl.to_story),
                                 max(vl.from_story, vl.to_story) + 1))
        elif vl.story is not None:
            reached.add(vl.story)
    return reached


def audit_spec(f):
    """Return (hard_findings, soft_findings) for one spec file."""
    name = f.replace("specs/", "").replace("specs\\", "")
    hard, soft = [], []
    raw = json.load(open(f, encoding="utf-8"))
    spec = spec_loader.load_spec(f)
    n = spec.n_stories

    # 1. trapped floors (skip facade-only shells with no interior)
    if not raw.get("facade"):
        reached = _reach(spec)
        for r in spec.rooms:
            if r.story >= 1 and r.story not in reached:
                hard.append(f"{name}: room '{r.id}' on story {r.story} is not "
                            f"reached by any stair/ladder/vertical_link "
                            f"(reached stories {sorted(reached)})")

    # 2. out-of-range spans
    lo_bound = -1 if raw.get("has_basement") else \
        min([r.story for r in spec.rooms], default=0)
    for st in spec.stairs:
        if st.from_story is None or st.to_story is None:
            continue
        hi = max(st.from_story, st.to_story)
        lo = min(st.from_story, st.to_story)
        if hi > n or lo < lo_bound:
            hard.append(f"{name}: stair '{getattr(st, 'id', '?')}' spans "
                        f"{lo}->{hi}, outside [{lo_bound},{n}]")
    for ld in spec.ladders:
        hi = max(ld.from_story, ld.to_story)
        if hi > n:
            hard.append(f"{name}: ladder '{getattr(ld, 'id', '?')}' top story "
                        f"{hi} exceeds n_stories {n}")

    # 3 + 4. derivation completeness + egress invariant
    for d in ladder.derive(spec):
        for req in ("id", "role", "route_nodes", "nav_link", "authority",
                    "ai", "combat", "traversal_component"):
            if not d.get(req):
                hard.append(f"{name}: ladder '{d.get('id')}' is missing "
                            f"derived block '{req}'")
        if d.get("counts_as_primary_egress") \
                or d.get("counts_as_public_circulation"):
            hard.append(f"{name}: ladder '{d['id']}' violates the never-egress "
                        f"invariant (ladder spec s2)")
        nl = d.get("nav_link", {})
        if nl and nl.get("start_position") == nl.get("end_position"):
            hard.append(f"{name}: ladder '{d['id']}' nav_link is zero-length "
                        f"(start == end)")

    # soft: analyzer warnings (content-quality nits, not failures)
    le, lw, _ = ladder.check(spec)
    se, sw, _ = stairwell.check(spec)
    for w in lw + sw:
        soft.append(f"{name}: {w.split(':', 1)[0].strip()}")
    # any analyzer ERROR here would already fail the gate, but surface it
    for e in le + se:
        hard.append(f"{name}: analyzer error {e.split(':', 1)[0].strip()}")

    return hard, soft


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any soft finding (warning) exists too")
    ap.add_argument("--glob", default="specs/*.json")
    args = ap.parse_args()

    all_hard, all_soft = [], []
    files = sorted(f for f in glob.glob(args.glob)
                   if not f.endswith(".md"))
    for f in files:
        try:
            hard, soft = audit_spec(f)
        except Exception as ex:
            all_hard.append(f"{f}: audit crashed -- {ex}")
            continue
        all_hard.extend(hard)
        all_soft.extend(soft)

    print(f"audited {len(files)} spec(s)")
    if all_hard:
        print(f"\n{len(all_hard)} HARD finding(s):")
        for h in all_hard:
            print(f"  X {h}")
    if all_soft:
        print(f"\n{len(all_soft)} content-quality warning(s):")
        for s in all_soft:
            print(f"  ! {s}")
    if not all_hard and not all_soft:
        print("clean: no structural or content issues")
    elif not all_hard:
        print("\nno hard findings -- warnings are authoring nits, gate stays green")

    fail = bool(all_hard) or (args.strict and bool(all_soft))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
