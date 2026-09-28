#!/usr/bin/env python3
"""
migrate_store_gondolas.py  --  a store's aisles are snack gondolas
==================================================================
One-shot, idempotent migration over specs/*.json for Zoo 1.13.0's
`snack_gondola`. The walker, 2026-09-28: "do the snack gondolas next".

`prop_species` routes `gondola_aisle` to the species. Two stores already name
their aisles so (gas_station_a02, fuel_stop_heist); the others do not, and
built them as plain boxes (`aisle_N`, 0.9 x 10.0 x 1.8, in the gas_station
family) or as bare shelving with nothing on it (`aisle_shelf_N`, 7.0 x 0.7 x
1.6, in gas_station_a03 and stop_n_go). This renames those to
`gondola_aisle_N`, keeping N.

ONLY IN A STORE: a spec is a store when it carries a `register_counter`
(Deli Counter 0.146.0's service counter) -- because the supermarkets also
name aisles `aisle_N` and a supermarket aisle is not a snack aisle.
MEASURED before it ran: no store spec refers to an aisle volume by name
anywhere outside its volume list, so the rename breaks no reference.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrate_store_gondolas.py            # write specs/
    python migrate_store_gondolas.py --check    # report only; exit 1 if any
    python migrate_store_gondolas.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_AISLE = re.compile(r"(?:aisle|aisle_shelf)_(\d+)")


def renames(spec):
    """``[(old, new)]`` for this spec, or ``[]`` when it is not a store."""
    names = [v.get("name", "") for v in spec.get("volumes") or []]
    if "register_counter" not in names:
        return []
    taken = set(names)
    out = []
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
        if os.path.basename(p).startswith("lf_"):
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
        print(f"[store_gondolas] {os.path.basename(p)}: " + ", ".join(f"{a} -> {b}" for a, b in todo))
        if check:
            continue
        m = dict(todo)
        for v in d["volumes"]:
            if v.get("name") in m:
                v["name"] = m[v["name"]]
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "need renaming" if check else "renamed"
    print(f"[store_gondolas] {specs} store spec(s), {count} aisle(s) {verb}")
    return 1 if check and count else 0


if __name__ == "__main__":
    sys.exit(main())
