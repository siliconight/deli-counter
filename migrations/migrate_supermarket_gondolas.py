#!/usr/bin/env python3
"""
migrate_supermarket_gondolas.py  --  a supermarket's aisles are gondolas too
=============================================================================
One-shot, idempotent migration over specs/*.json (Deli Counter 0.272.0).

`migrate_store_gondolas.py` (0.149.0) made every store's aisles Zoo's
`snack_gondola` and left the supermarkets' `aisle_N` as boxes, because "a
supermarket aisle is not a snack aisle". The walker, walking seed 9205's
supermarket on 2026-10-26, met what that left: five 14 m dark blocks down the
sales floor, read with the rest of the room as "far too dark" and alongside
the ramp's bare slab as "doesn't look finished" (the factory's
docs/findings/walk_2026-10-26_panel/, L4 and L3). A shelved gondola stocked
with packaged goods reads as a store's aisle; a box does not.

THEY FIT THE SPECIES: the supermarkets' aisles are 1.4 x 14.0 x 2.0 m
(supermarket_a01) and 1.4 x 12.0 x 2.0 m (supermarket_a03); Zoo's
`snack_gondola` genome takes widths 1.2-14.0, depths 0.6-1.5 and heights
1.2-2.2. Grocery stock in place of snacks is a Zoo variant for later, not a
reason to keep a box.

A SUPERMARKET is a spec whose file name begins `supermarket`. Nothing in
either refers to an aisle by name outside its volume list (measured before
it ran), so the rename breaks no reference. `lf_*` specs are skipped.

    python migrations/migrate_supermarket_gondolas.py            # write specs/
    python migrations/migrate_supermarket_gondolas.py --check    # report only; exit 1 if any
    python migrations/migrate_supermarket_gondolas.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AISLE = re.compile(r"aisle_(\d+)")


def is_supermarket(path):
    return os.path.basename(path).startswith("supermarket")


def renames(spec):
    """``[(old, new)]``: every ``aisle_N`` volume to ``gondola_aisle_N``."""
    names = [v.get("name", "") for v in spec.get("volumes") or []]
    taken, out = set(names), []
    for n in names:
        m = _AISLE.fullmatch(n)
        if not m:
            continue
        new = "gondola_aisle_" + m.group(1)
        k = 2
        while new in taken:
            new = "gondola_aisle_%s_%d" % (m.group(1), k)
            k += 1
        taken.add(new)
        out.append((n, new))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    specs = count = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_") or not is_supermarket(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        todo = renames(d)
        if not todo:
            continue
        specs += 1
        count += len(todo)
        print(f"[supermarket_gondolas] {os.path.basename(p)}: " + ", ".join(f"{a} -> {b}" for a, b in todo))
        if check:
            continue
        m = dict(todo)
        for v in d["volumes"]:
            if v.get("name") in m:
                v["name"] = m[v["name"]]
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "need renaming" if check else "renamed"
    print(f"[supermarket_gondolas] {specs} supermarket spec(s), {count} aisle(s) {verb}")
    return 1 if check and count else 0


if __name__ == "__main__":
    sys.exit(main())
