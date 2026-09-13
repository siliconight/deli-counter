#!/usr/bin/env python3
"""
migrate_stair_pitch.py  --  lengthen every flight a body cannot climb
=====================================================================
One-shot, idempotent migration over specs/*.json (see `stair_pitch.py` for the
rule and the measurement behind it). `lf_*` specs are Level Factory's per-run
transients and are regenerated on every run, so they are skipped.

    python migrate_stair_pitch.py            # write
    python migrate_stair_pitch.py --check    # report only; exit 1 if any flight is too steep
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import stair_pitch  # noqa: E402


def main():
    check = "--check" in sys.argv
    lengthened = reseated = specs = 0
    unresolved = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if d.get("facade") or not d.get("stairs"):
            continue
        if check:
            n = len(stair_pitch.lengthen(json.loads(json.dumps(d))))
            if n:
                specs += 1
                lengthened += n
            continue
        r = stair_pitch.make_walkable(d)
        if not r["lengthened"]:
            continue
        specs += 1
        lengthened += len(r["lengthened"])
        reseated += len(r["reseated"])
        unresolved += [(os.path.basename(p), s) for s in r["unresolved"]]
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "too steep" if check else "lengthened"
    print(f"[stair_pitch] {specs} spec(s), {lengthened} flight(s) {verb}, "
          f"{reseated} re-seated, {len(unresolved)} unresolved {unresolved}")
    return 1 if (check and lengthened) or unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
