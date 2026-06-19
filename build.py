#!/usr/bin/env python3
"""
build.py  --  CLI for the Deli Counter level kit
=========================================
Builds a level from a JSON/YAML spec by driving Blender in background mode,
then exports a .glb for Godot. This is the reproducible one-command path.

USAGE (from the levels/ folder)
--------------------------------
    python build.py specs/bank.json
    python build.py specs/bank.json --out build/bank.glb
    python build.py --all                 # build every spec in specs/
    python build.py specs/bank.json --blender "/path/to/blender"

It locates Blender via (in order): --blender flag, $BLENDER env var, PATH.

MANUAL FALLBACK (no CLI / want the GUI)
---------------------------------------
    1. Open Blender 4.x, Scripting workspace.
    2. Open _run_in_blender.py, set SPEC_PATH at the top, Run Script (Alt+P).
       (or open a spec and use the run snippet in the README)

HOW IT WORKS
------------
build.py itself runs in your normal Python. It shells out to:
    blender --background --python _run_in_blender.py -- <spec> <out>
The part after `--` is passed through to the in-Blender script.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_blender(explicit=None):
    if explicit:
        return explicit
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    found = shutil.which("blender")
    if found:
        return found
    # common Windows install path guesses (newest first)
    guesses = [
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
    ]
    for guess in guesses:
        if os.path.exists(guess):
            return guess
    return None


def build_one(blender, spec_path, out_paths):
    """out_paths: list of output file paths (one per format)."""
    runner = os.path.join(HERE, "_run_in_blender.py")
    joined = ";".join(out_paths)
    cmd = [blender, "--background", "--python", runner, "--",
           spec_path, joined]
    print(f"[build] {os.path.basename(spec_path)} -> "
          f"{', '.join(os.path.basename(p) for p in out_paths)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


def _out_paths(build_dir, name, formats, explicit_out):
    if explicit_out:
        return [explicit_out]
    return [os.path.join(build_dir, f"{name}.{fmt}") for fmt in formats]


def main():
    ap = argparse.ArgumentParser(description="Build levels from specs.")
    ap.add_argument("spec", nargs="?", help="path to a .json/.yaml spec")
    ap.add_argument("--out", help="explicit output path (single format, "
                    "overrides --format)")
    ap.add_argument("--format", "-f", default="glb",
                    help="comma-separated formats: glb,gltf,obj (default glb)")
    ap.add_argument("--all", action="store_true",
                    help="build every spec in specs/")
    ap.add_argument("--blender", help="path to the Blender executable")
    args = ap.parse_args()

    formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]
    valid = {"glb", "gltf", "obj"}
    bad = set(formats) - valid
    if bad:
        sys.exit(f"Unknown format(s): {', '.join(bad)}. Use glb, gltf, obj.")

    blender = find_blender(args.blender)
    if not blender:
        sys.exit("Blender not found. Set $BLENDER, use --blender, or add it "
                 "to PATH.")

    build_dir = os.path.join(HERE, "build")
    os.makedirs(build_dir, exist_ok=True)

    if args.all:
        specs = sorted(glob.glob(os.path.join(HERE, "specs", "*.json")) +
                       glob.glob(os.path.join(HERE, "specs", "*.yaml")) +
                       glob.glob(os.path.join(HERE, "specs", "*.yml")))
        if not specs:
            sys.exit("No specs found in specs/")
        ok = True
        for sp in specs:
            name = os.path.splitext(os.path.basename(sp))[0]
            outs = _out_paths(build_dir, name, formats, None)
            ok = build_one(blender, sp, outs) and ok
        sys.exit(0 if ok else 1)

    if not args.spec:
        ap.error("provide a spec path or --all")

    name = os.path.splitext(os.path.basename(args.spec))[0]
    outs = _out_paths(build_dir, name, formats, args.out)
    ok = build_one(blender, args.spec, outs)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
