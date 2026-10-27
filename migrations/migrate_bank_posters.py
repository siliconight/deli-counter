#!/usr/bin/env python3
"""
migrate_bank_posters.py  --  a bank's printed offers and its name over the teller line (0.283.0)
==============================================================================================
One-shot, idempotent migration over specs/*.json. Furnish hangs a bank lobby's printed offers (Zoo 1.137.0's
`poster_wall` form `bank`, the `bank_lobby` recipe's `poster_wall_bank`) and makes a bank's teller line Zoo's
`teller_line` form `bank` in its door sign's variant (`level_design.dress_bank_teller_lines`). The library is a fixed
point of its furnishing pass, so every spec with a bank lobby or a teller line to dress is refurnished
(`migrate_furnish_recipes.migrate`); no other spec is touched.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrations/migrate_bank_posters.py            # write specs/
    python migrations/migrate_bank_posters.py --check    # report only; exit 1 if any would change
"""
import glob
import io
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "migrations"))

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402

def _touched(d):
    b = level_design.club_building_id(d)
    if any(level_design._room_kind(r, b) == "bank_lobby" for r in d.get("rooms") or []):
        return True
    # a credit union is no `bank_lobby` (`lights.is_bank` reads "bank") but its sign is a bank's, and so its line
    return level_design.dress_bank_teller_lines(copy.deepcopy(d)) > 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    changed = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not _touched(d):
            continue
        before = json.dumps(d, indent=1) + "\n"
        migrate_furnish_recipes.migrate(d)
        # ...and a spec with no rooms, which furnish never reaches: `bank`'s line is dressed all the same
        level_design.dress_bank_teller_lines(d)
        after = json.dumps(d, indent=1) + "\n"
        if after == before:
            continue
        changed += 1
        names = [str(v.get("name", "")) for v in d["volumes"]]
        lines = [v for v in d["volumes"] if v.get("form") == "bank" and "teller" in str(v.get("name", ""))]
        print(f"[bank_posters] {os.path.basename(p)}: {sum(n.startswith('poster_wall_bank') for n in names)} "
              f"poster run(s), {len(lines)} teller line(s) {[v.get('variant', 0) for v in lines]}")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(after)
    verb = "would change" if check else "refurnished"
    print(f"[bank_posters] {changed} spec(s) {verb}")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
