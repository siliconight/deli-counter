#!/usr/bin/env python3
"""
new_level.py  --  generate a level spec from a preset recipe
============================================================
The walk-up entry point. No Blender, no JSON hand-editing required:

    python new_level.py --preset bank --name my_bank
    python new_level.py --preset bank --name vault_job --mode heist --floors 3
    python new_level.py --list

Writes specs/<name>.json, validates it, and prints next steps. Edit the JSON
afterward to customize, or feed it straight to build.py.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import presets  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Generate a level spec from a preset.")
    ap.add_argument("--preset", help="recipe name (see --list)")
    ap.add_argument("--name", help="level name -> specs/<name>.json")
    ap.add_argument("--mode", default=None,
                    choices=["assault", "heist", "survival"],
                    help="tactical mode (default: the preset's own default)")
    ap.add_argument("--floors", type=int, default=None,
                    help="above-ground stories (default: the preset's own default)")
    ap.add_argument("--no-basement", action="store_true", help="omit the basement")
    ap.add_argument("--basement", action="store_true",
                    help="force-include a basement")
    ap.add_argument("--scale-ref", action="store_true",
                    help="add 1.8 m human proxies at spawns for a Blender scale check")
    ap.add_argument("--list", action="store_true", help="list available presets and exit")
    ap.add_argument("--force", action="store_true", help="overwrite if the spec exists")
    args = ap.parse_args()

    if args.list:
        print("Available presets:")
        for p in sorted(presets.REGISTRY):
            doc = (presets.REGISTRY[p].__doc__ or "").strip().split("\n")[0]
            print(f"  {p:14s} {doc}")
        return 0

    if not args.preset or not args.name:
        ap.error("both --preset and --name are required (or use --list)")

    # Only pass args the user actually set, so each preset's own defaults stand
    # (e.g. hospital defaults to survival/3 floors; bank to assault). Passing a
    # blanket --mode assault would wrongly override a survival-first preset.
    kwargs = {"name": args.name, "scale_ref": args.scale_ref}
    if args.mode is not None:
        kwargs["mode"] = args.mode
    if args.floors is not None:
        kwargs["floors"] = args.floors
    if args.no_basement:
        kwargs["basement"] = False
    elif args.basement:
        kwargs["basement"] = True

    try:
        spec = presets.make(args.preset, **kwargs)
    except KeyError as e:
        print(f"error: {e}")
        return 2

    specs_dir = os.path.join(HERE, "specs")
    os.makedirs(specs_dir, exist_ok=True)
    out = os.path.join(specs_dir, f"{args.name}.json")
    if os.path.exists(out) and not args.force:
        print(f"error: {out} already exists (use --force to overwrite)")
        return 2
    with open(out, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"wrote {out}")

    # validate immediately so the user knows it's buildable
    rel = os.path.join("specs", f"{args.name}.json")
    print("\nvalidating...")
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, "validate.py"), rel],
                       cwd=HERE)
    if r.returncode != 0:
        print("\nThe generated spec has validation issues (above). This is a "
              "preset bug — please report it; the spec was still written so "
              "you can inspect it.")
        return r.returncode

    # keep CATALOG.md in sync so the CI gate (check.py) stays green — a new
    # spec without a catalog refresh is the most common way the catalog goes
    # stale.
    cat = os.path.join(HERE, "catalog.py")
    if os.path.exists(cat):
        cr = subprocess.run([sys.executable, cat], cwd=HERE,
                            capture_output=True, text=True)
        if cr.returncode == 0:
            print("refreshed specs/CATALOG.md")
        else:
            print("note: couldn't refresh CATALOG.md automatically — "
                  "run `python catalog.py` before committing.")

    print(f"\nNext: build it ->  python build.py {rel}")
    print(f"      or open specs/{args.name}.json to customize.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
