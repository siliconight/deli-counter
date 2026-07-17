#!/usr/bin/env python3
"""
migrate_stairs.py  --  bring a spec's stairs up to the universal contract
=========================================================================
As of v0.78 the physical stair findings (STAIR_ENTRY_FACES_SOLID,
STAIR_EXIT_FACES_SOLID, STAIR_LOWER/UPPER_LANDING_BLOCKED) are hard errors
for EVERY spec, authored or generated. This tool repairs an existing spec to
comply with the smallest possible change:

  1. try every facing at the authored position;
  2. then deterministic position nudges (grid of offsets by growing
     distance, each in all four facings), accepting the first candidate
     where the stair is physically clean, the whole spec's stairwell error
     count does not increase, and the stair neither lands on another
     stair's footprint nor consumes a protected room;
  3. finally classify any role-less stair via the presets finishing pass.

    python migrate_stairs.py specs/foo.json            # report only
    python migrate_stairs.py specs/foo.json --write
    python migrate_stairs.py --all --write

Deterministic: the same spec migrates the same way forever. A stair the
search cannot repair is reported for a human decision (that is a floorplan
problem, not an orientation problem).
"""

import argparse
import copy
import glob
import json
import os
import sys

import presets
import stairwell
from spec_loader import spec_from_dict

HERE = os.path.dirname(os.path.abspath(__file__))

_OFFSETS = [0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0,
            2.5, -2.5, 3.0, -3.0, 4.0, -4.0]
_FACINGS = ("N", "E", "S", "W")


def _errors(spec_dict):
    sp = spec_from_dict(spec_dict)
    errs, _, _ = stairwell.check(sp)
    return errs


def _stair_findings(spec_dict, i):
    sp = spec_from_dict(spec_dict)
    st = sp.stairs[i]
    return stairwell.clearance_findings(
        sp, st, stairwell.stair_ident(st, i))


def _protected_overlap(spec_dict, i):
    """Fraction of stair i's footprint overlapping protected rooms."""
    sp = spec_from_dict(spec_dict)
    st = sp.stairs[i]
    rect = stairwell.footprint_rect(st)
    area = max(1e-9, (rect[2] - rect[0]) * (rect[3] - rect[1]))
    ov = 0.0
    for r in sp.rooms:
        if r.objective or (r.role or "") == "objective_room":
            ov = max(ov, stairwell._overlap_area(rect, r.bounds))
    return ov / area


def _placement_sane(spec_dict, i, max_protected):
    """The repaired stair may not land on another stair, and may not eat
    MORE protected-room area than the authored placement already did (a
    stair authored inside the vault room stays a vault stair; a physical
    fix must not create a semantic mess elsewhere)."""
    sp = spec_from_dict(spec_dict)
    st = sp.stairs[i]
    rect = stairwell.footprint_rect(st)
    for j, other in enumerate(sp.stairs):
        if j != i and stairwell._rects_overlap(
                rect, stairwell.footprint_rect(other)):
            return False
    return _protected_overlap(spec_dict, i) <= max_protected + 0.01


def repair(spec_dict):
    """Repair every physically-failing stair in place. Returns
    (changes, unfixable): human-readable change strings and the ids the
    search could not fix."""
    changes, unfixable = [], []
    baseline = len(_errors(spec_dict))
    for i, sd in enumerate(spec_dict.get("stairs") or []):
        if not _stair_findings(spec_dict, i):
            continue
        sid = sd.get("id") or f"stair_{i}"
        ox, oy = sd["x"], sd["y"]
        of = sd.get("facing", "N")
        facings = [of] + [f for f in _FACINGS if f != of]
        max_protected = max(0.2, _protected_overlap(spec_dict, i))
        fixed = False
        for dist in sorted(set(abs(dx) + abs(dy) for dx in _OFFSETS
                               for dy in _OFFSETS)):
            for dx in _OFFSETS:
                for dy in _OFFSETS:
                    if abs(dx) + abs(dy) != dist:
                        continue
                    for f in facings:
                        sd["x"] = round(ox + dx, 2)
                        sd["y"] = round(oy + dy, 2)
                        sd["facing"] = f
                        if _stair_findings(spec_dict, i):
                            continue
                        if not _placement_sane(spec_dict, i, max_protected):
                            continue
                        if len(_errors(spec_dict)) > baseline:
                            continue
                        move = "" if (dx == 0 and dy == 0) \
                            else f", moved ({dx:+g}, {dy:+g})"
                        changes.append(f"{sid}: facing {of} -> {f}{move}")
                        fixed = True
                        break
                    if fixed:
                        break
                if fixed:
                    break
            if fixed:
                break
        if not fixed:
            sd["x"], sd["y"], sd["facing"] = ox, oy, of
            unfixable.append(sid)
        else:
            baseline = len(_errors(spec_dict))

    # classification: a migrated spec leaves with every stair roled/faced
    if not unfixable and any(not sd.get("role")
                             for sd in spec_dict.get("stairs") or []):
        presets._finish_stairs(spec_dict)
        presets._finish_ladders(spec_dict)
        changes.append("classified role-less stairs/ladders")
    return changes, unfixable


def migrate_file(path, write=False):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if d.get("facade") or not d.get("stairs"):
        return True, []
    before = len(_errors(d))
    if before == 0 and all(sd.get("role") for sd in d["stairs"]):
        return True, []
    changes, unfixable = repair(d)
    after = len(_errors(d))
    name = os.path.basename(path)
    for c in changes:
        print(f"  {name}: {c}")
    for u in unfixable:
        print(f"  {name}: UNFIXABLE {u} -- needs a floorplan decision")
    print(f"  {name}: stairwell errors {before} -> {after}")
    if write and not unfixable and after == 0:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
            f.write("\n")
        print(f"  {name}: written")
    return (not unfixable and after == 0), changes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec", nargs="?", help="one spec file")
    ap.add_argument("--all", action="store_true", help="migrate specs/*.json")
    ap.add_argument("--write", action="store_true",
                    help="write repaired specs back")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))) \
        if args.all else ([args.spec] if args.spec else [])
    if not files:
        ap.error("pass a spec or --all")
    ok = True
    for f in files:
        good, _ = migrate_file(f, write=args.write)
        ok &= good
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
