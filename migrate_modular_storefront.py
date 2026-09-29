#!/usr/bin/env python3
"""
migrate_modular_storefront.py  --  a storefront is built from the kit
=====================================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.158.0: a
spec with a storefront (a storey-0 exterior wall of `storefront_glass`,
`deli_counter.STOREFRONT_MATERIALS`) builds MODULAR.

WHY. The storefront is a kit capability: Deli Counter tags a storefront
wall's full wall and door SLOTS `glazing: "storefront"` (0.153.0) and Zoo
(1.18.0) builds them as see-through glass; its reach (0.155.0), its spill
(0.156.0) and its light-budget tiles (0.157.0) all read those slots. A spec
that does not build modular emits no wall slots at all -- `_exterior` cuts
each wall as one box with holes -- so it has a storefront on paper and a
solid wall on screen. MEASURED on 0.157.0's build: fuel_stop_heist (mode
`heist`) and stop_n_go (mode `assault`) carried 51 and 17 slots, every one a
prop, and were named in `test_storefront_glazing.SHELL_WALLED` as the gap.
`modular` was unset in both, and `build.py` forces it on only for
`pvp_heist`; 302 of the library's specs set it themselves.

THE RULE: a spec with a storey-0 `storefront_glass` exterior wall and no
`modular` key gets `"modular": true`. A spec that says `false` is left as it
said and REPORTED -- that is a decision, not an omission.

    python migrate_modular_storefront.py            # write specs/
    python migrate_modular_storefront.py --check    # report only; exit 1 if any
    python migrate_modular_storefront.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

#: `deli_counter.STOREFRONT_MATERIALS`, read without importing the builder
#: (it imports bpy); `test_modular_storefront` holds the two equal.
STOREFRONT_MATERIALS = ("storefront_glass",)


def has_storefront(d):
    return any(int(w.get("story", 0) or 0) == 0 and w.get("material") in STOREFRONT_MATERIALS
               for w in d.get("ext_walls") or [])


def migrate(d):
    """True when this spec dict was changed (in place)."""
    if not has_storefront(d) or "modular" in d:
        return False
    d["modular"] = True
    return True


def refused(d):
    """A storefront spec that says it is NOT modular: left alone, reported."""
    return has_storefront(d) and d.get("modular") is False


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
        if refused(d):
            print(f"[modular] {os.path.basename(p)}: has a storefront and says modular: false -- left as it said")
        if not migrate(d):
            continue
        n += 1
        print(f"[modular] {os.path.basename(p)}: storefront -> modular: true")
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print(f"[modular] {n} spec(s) {'need' if check else 'given'} a modular build")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
