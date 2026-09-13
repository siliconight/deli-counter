#!/usr/bin/env python3
"""
migrate_teller_enclosure.py  --  lock the staff side of every teller line
=========================================================================
One-shot, idempotent migration over specs/*.json for the walker's request
(cold run 9048): "this bank teller booth should connect and be locked to the
public... a section where only employees can be there and enter/exit".
`level_design.enclose_teller_lines` does the work and `enrich` now runs it for
every preset; this gives the specs already in the library the same answer.
Run it BEFORE furnishing, so furniture clears the new walls and doors. `lf_*`
specs are Level Factory's per-run transients and are skipped.

    python migrate_teller_enclosure.py            # write specs/
    python migrate_teller_enclosure.py --check    # report only
    python migrate_teller_enclosure.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402


def main():
    check = "--check" in sys.argv
    root = os.path.join(HERE, "specs")
    if "--dir" in sys.argv:
        root = sys.argv[sys.argv.index("--dir") + 1]
    enclosed = left = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(p)
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        before = json.dumps(d, sort_keys=True)
        report = level_design.enclose_teller_lines(d)
        for r in report:
            print(f"  {name} {r['volume']}: "
                  f"{'enclosed' if r['enclosed'] else 'left open'} -- {r['why']}")
            enclosed += r["enclosed"]
            left += not r["enclosed"]
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    print(f"[teller_enclosure] {enclosed} teller line(s) "
          f"{'to enclose' if check else 'enclosed'}, {left} left open")
    return 0


if __name__ == "__main__":
    sys.exit(main())
