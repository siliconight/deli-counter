"""Sweep: does any built archetype park a prop in its own circulation?

`circulation.check_shell` gates one building at package time. This answers the
scope question that gate cannot: is a prop-in-a-stairwell one bad seed, or does
the library ship it? Run it over `deli_counter/build` (or any directory of
`<name>.glb` + `<name>.gameplay.json` pairs).

Written because the first building anyone pointed the check at -- art_probe_001
seed 5017 -- had VAULT 1.6 m inside a stair column, and one measurement is not
a rate.

    python sweep_stair_obstruction.py build [--json out.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import circulation


def pairs(root):
    """(<id>, glb, gameplay) for every built shell that carries both files.

    The id is the path RELATIVE to root, minus the extension -- not the
    basename. A Level Factory workspace names every generated shell
    ``shell.glb``, so a basename id collapses four different buildings into
    four rows all called "shell" and the report becomes unreadable exactly
    where the generated path is under test.
    """
    out = []
    for glb in sorted(glob.glob(os.path.join(root, "**", "*.glb"),
                                recursive=True)):
        gp = f"{glb[:-4]}.gameplay.json"
        if not os.path.isfile(gp):
            continue
        rel = os.path.relpath(glb[:-4], root).replace(os.sep, "/")
        out.append((rel, glb, gp))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default="build")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    found = pairs(args.root)
    if not found:
        print(f"no <name>.glb + <name>.gameplay.json pairs under {args.root}")
        return 3

    rows, dirty, no_props, no_vols = [], 0, 0, 0
    for bid, glb, gp_path in found:
        with open(gp_path, encoding="utf-8") as f:
            gp = json.load(f)
        try:
            r = circulation.check_shell(glb, None, gp)
        except Exception as ex:
            print(f"  {bid}: gate failed to run: {ex}")
            continue
        r["id"] = bid
        rows.append(r)
        if not r["ok"]:
            dirty += 1
        # A gate with no input is not a pass -- count both starvation modes
        # separately so a clean sweep cannot hide an empty one.
        if r["props"] == 0:
            no_props += 1
        if r["volumes"] == 0:
            no_vols += 1

    print(f"{len(rows)} built shells swept\n")
    for r in sorted(rows, key=lambda r: (r["ok"], r["id"])):
        if r["ok"]:
            continue
        print(f"  {r['id']}  ({r['props']} props, {r['volumes']} volumes)")
        for c in r["conflicts"]:
            print(f"      {c['prop']:28s} -> {c['volume']:34s} "
                  f"{c['penetration']:.2f} m")

    print(f"\n  shells with a prop in circulation : {dirty} of {len(rows)}")
    print(f"  shells with NO props to check     : {no_props}")
    print(f"  shells with NO volumes to check   : {no_vols}")
    if no_props or no_vols:
        print("  (those two are not passes -- the gate had nothing to compare)")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"root": os.path.abspath(args.root), "rows": rows},
                      f, indent=2, sort_keys=True)
        print(f"\nwrote {args.json}")
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())
