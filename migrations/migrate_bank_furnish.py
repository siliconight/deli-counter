#!/usr/bin/env python3
"""
migrate_bank_furnish.py  --  a bank's lobby furnished as the comps, a vault's cash cart (0.281.0)
================================================================================================
One-shot, idempotent migration over specs/*.json. Furnish gives a bank's public room the `bank_lobby` recipe -- a check
desk mid-floor, waiting chairs, an ATM, a queue; none of the general lobby's vending, cigarettes, payphone or sofa --
and every `vault` room a cash cart beside its count table. The library is a fixed point of its furnishing pass, so
every spec with a room of either kind is refurnished (`migrate_furnish_recipes.migrate`); no other spec is touched.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrations/migrate_bank_furnish.py            # write specs/
    python migrations/migrate_bank_furnish.py --check    # report only; exit 1 if any would change
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "migrations"))

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402

KINDS = ("bank_lobby", "bank_vault")


def _touched(d):
    b = level_design.club_building_id(d)
    return any(level_design._room_kind(r, b) in KINDS for r in d.get("rooms") or [])


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
        after = json.dumps(d, indent=1) + "\n"
        if after == before:
            continue
        changed += 1
        names = [str(v.get("name", "")) for v in d["volumes"]]
        print(f"[bank_furnish] {os.path.basename(p)}: {sum(n.startswith('check_desk') for n in names)} check desk(s), "
              f"{sum(n.startswith('cash_cart') for n in names)} cash cart(s)")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(after)
    verb = "would change" if check else "refurnished"
    print(f"[bank_furnish] {changed} spec(s) {verb}")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
