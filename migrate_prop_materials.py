#!/usr/bin/env python3
"""
migrate_prop_materials.py  --  every placed piece names what it is made of
==========================================================================
One-shot, idempotent migration over specs/*.json for the walker's readability
rule (cold run 9048): "it should look like a 3d object that looks different
from the ground and wall so I can see them from a distance". A volume with no
`material` wears the building's `default_material` -- the wall skin -- so a
crate stack or a planter is a box in the wall's own texture.

`level_design` now writes a material on every piece `seed_cover` and
`furnish` place (`_prop_material`: metal for safes, tanks, lockers, vaults;
wood otherwise). This gives the pieces ALREADY in the library the same answer.
Measured before it ran: 78 volumes without a material in 18 specs, 29 of them
`crate_stack`, 10 `planter_box`, 9 `counter_island`.

Architecture keeps the wall: a volume whose name says it is part of the
building (`_ARCHITECTURE`) is left alone. `lf_*` specs are Level Factory's
per-run transients and are skipped.

    python migrate_prop_materials.py            # write specs/
    python migrate_prop_materials.py --check    # report only; exit 1 if any
    python migrate_prop_materials.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402

#: Name fragments of volumes that are part of the building, not placed in it.
_ARCHITECTURE = ("mezz", "wall", "column", "pillar", "stair", "ramp", "ledge",
                 "platform", "beam", "slab", "parapet")


def unmaterialled(spec):
    return [v for v in spec.get("volumes") or []
            if not v.get("material")
            and not any(a in v.get("name", "").lower() for a in _ARCHITECTURE)]


def main():
    check = "--check" in sys.argv
    root = os.path.join(HERE, "specs")
    if "--dir" in sys.argv:
        root = sys.argv[sys.argv.index("--dir") + 1]
    specs = pieces = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        todo = unmaterialled(d)
        if not todo:
            continue
        specs += 1
        pieces += len(todo)
        if check:
            continue
        for v in todo:
            v["material"] = level_design._prop_material(d, v["name"])
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, indent=1) + "\n")
    verb = "need a material" if check else "given a material"
    print(f"[prop_materials] {specs} spec(s), {pieces} volume(s) {verb}")
    return 1 if check and pieces else 0


if __name__ == "__main__":
    sys.exit(main())
