#!/usr/bin/env python3
"""
migrate_deposit_lining.py  --  a bank's deposit vault lined with boxes (0.288.0)
==============================================================================
One-shot, idempotent migration over specs/*.json. `level_design.line_deposit_vaults` lines every partition round a
vault an authored deposit wall faces with deposit openings, and furnish makes that room a `bank_deposit` -- the boxes
and a viewing table, no money racks. The library is a fixed point of its furnishing pass, so a spec it lines is then
refurnished (`migrate_furnish_recipes.migrate`); no other spec is touched.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrations/migrate_deposit_lining.py            # write specs/
    python migrations/migrate_deposit_lining.py --check    # report only; exit 1 if any would change
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    changed = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if "rooms" not in d or not level_design.deposit_vault_ids(d):
            continue
        before = json.dumps(d, indent=1) + "\n"
        n = level_design.line_deposit_vaults(d)
        migrate_furnish_recipes.migrate(d)
        after = json.dumps(d, indent=1) + "\n"
        if after == before:
            continue
        changed += 1
        print(f"[deposit_lining] {os.path.basename(p)}: {n} unit(s) on {sorted(level_design.deposit_vault_ids(d))}")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(after)
    print(f"[deposit_lining] {changed} spec(s) {'would change' if check else 'lined'}")
    return 1 if check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
