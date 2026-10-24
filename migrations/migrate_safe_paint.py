#!/usr/bin/env python3
"""
migrate_safe_paint.py  --  a stored safe is painted steel (0.267.0)
==================================================================
One-shot, idempotent migration over specs/*.json, lf_ specs excepted. Every volume whose material `_prop_material`
now names from its name differs from the one stored only by `metal` -> `metal_painted` -- the safes, the one row this
release moved -- is repainted, and the spec's palette declares `metal_painted` the way `_prop_material` does. No other
volume is touched.

    python migrations/migrate_safe_paint.py            # write specs/
    python migrations/migrate_safe_paint.py --check    # report only
"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import level_design  # noqa: E402


def main():
    check = "--check" in sys.argv
    specs = vols = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        n = 0
        for v in d.get("volumes") or []:
            if v.get("material") != "metal":
                continue
            if level_design._prop_material(dict(d), str(v.get("name", ""))) != "metal_painted":
                continue
            if "safe" not in str(v.get("name", "")).lower():
                continue
            v["material"] = "metal_painted"
            n += 1
        if n:
            level_design._declare_material(d, "metal_painted", level_design._PROP_ACOUSTIC["metal_painted"])
            specs += 1
            vols += n
            if not check:
                io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[safe_paint] %d spec(s), %d safe(s) painted%s" % (specs, vols, " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
