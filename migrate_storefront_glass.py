#!/usr/bin/env python3
"""
migrate_storefront_glass.py  --  a store's shop front is a storefront
====================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.153.0 /
Zoo 1.18.0: a `storefront_glass` wall's full wall and door slots are tagged
`glazing: "storefront"` and built as see-through glass (the walker,
2026-09-28: "yes, make the storefront see-through glass").

MEASURED FIRST: six specs name `storefront_glass` (card_shop_a01,
fuel_stop_heist, gas_station_a02, gas_station_a03, stop_n_go -- and the
preset's own recipe for the stores it makes). The five stores the
`gas_station` preset built -- cr_gas, gas_station, gas_station_a01,
gas_street, gs_corner_station -- call their shop front `glass`, the word
every bank and tower uses for an opaque curtain wall. Their shop front is a
storefront, so it says so; `glass` elsewhere is untouched.

THE RULE: a convenience store (`migrate_slush_machine.is_store`) whose
storey-0 exterior wall is `glass` gets `storefront_glass`, declared in its
palette with the preset's acoustics. Furnishing reads the wall's KIND, which
is `glass_facade` either way, so no room is refurnished.

    python migrate_storefront_glass.py            # write specs/
    python migrate_storefront_glass.py --check    # report only; exit 1 if any
    python migrate_storefront_glass.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import migrate_slush_machine  # noqa: E402

STOREFRONT = {"id": "storefront_glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05}


def migrate(d):
    """``[wall letters changed]`` for one spec dict, in place."""
    if not migrate_slush_machine.is_store(d):
        return []
    changed = []
    for w in d.get("ext_walls") or []:
        if int(w.get("story", 0) or 0) == 0 and w.get("material") == "glass":
            w["material"] = STOREFRONT["id"]
            changed.append(w.get("wall"))
    if changed and not any(m.get("id") == STOREFRONT["id"] for m in d.get("materials") or []):
        d.setdefault("materials", []).append(dict(STOREFRONT))
    return changed


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    n = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        walls = migrate(d)
        if not walls:
            continue
        n += 1
        print(f"[storefront] {os.path.basename(p)}: wall(s) {','.join(walls)} -> storefront_glass")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print(f"[storefront] {n} spec(s) {'need' if check else 'given'} a storefront")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
