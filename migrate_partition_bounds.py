#!/usr/bin/env python3
"""One-shot migration: clamp every authored spec's interior partitions to the
footprint on their running axis (0.83.x).

Specs generated before the 0.83.1/0.83.2 fix carry the old extents (a Y-wall
authored to the X half-width, etc.), so `layout_lint --all` flags them L13 even
though the presets and the build-time clamp are now correct. This brings the
checked-in fixtures in line with the corrected output. The diff is surgical --
only the out-of-bounds start/end values change.

LF pipeline artifacts (specs/lf_*.json) are left alone: they are transient build
inputs regenerated from the fixed presets on the next run, and are excluded from
the lint gate.

    python migrate_partition_bounds.py            # migrate specs/*.json in place
    python migrate_partition_bounds.py --dry-run  # report only, change nothing
"""
import glob
import json
import os
import sys

from partition_bounds import clamp_partition_span

HERE = os.path.dirname(os.path.abspath(__file__))


def _count_or_apply(path, apply):
    d = json.load(open(path, encoding="utf-8"))
    fx, fy = d.get("footprint_x"), d.get("footprint_y")
    if not fx or not fy:
        return 0
    n = 0
    for p in d.get("partitions", []):
        if "start" not in p or "end" not in p or "axis" not in p:
            continue
        lo, hi = clamp_partition_span(p["start"], p["end"], p["axis"], fx, fy)
        if lo != min(p["start"], p["end"]) or hi != max(p["start"], p["end"]):
            n += 1
            if apply:
                p["start"], p["end"] = lo, hi
    if apply and n:
        open(path, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
    return n


def main():
    dry = "--dry-run" in sys.argv
    total = files = 0
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue  # LF pipeline artifact; regenerated from fixed presets
        n = _count_or_apply(path, apply=not dry)
        if n:
            files += 1
            total += n
            verb = "would clamp" if dry else "clamped"
            print(f"  {verb} {n} partition(s): {os.path.basename(path)}")
    tag = "[dry-run] " if dry else ""
    print(f"\n{tag}{total} partition(s) across {files} spec(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
