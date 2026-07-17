#!/usr/bin/env python3
"""
godot_gate.py  --  run the headless Godot IMPORT gate (round-trip engine leg)
=============================================================================
roundtrip.py is the Blender leg; this wrapper runs
godot/addon/deli_counter/import_gate.gd -- the ENGINE leg of the coordinate
round-trip -- against built shells:

    python godot_gate.py build/bank_job.glb
    python godot_gate.py --all               # every build/*.glb with a manifest
    python godot_gate.py --all --require     # missing Godot = failure (CI)

Both legs consume the SAME manifest "expected" block, so they cannot drift.
Writes <name>.godot_import.json next to each glb. Godot discovery is shared
with nav_gate.py ($DC_GODOT, then godot4/godot on PATH; Godot 3.x refused).

Exit code: 0 = all pass (or skipped without --require), 1 = failures.
"""

import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

GATE_GD = os.path.join(HERE, "godot", "addon", "deli_counter", "import_gate.gd")


def run_one(godot, glb_path, timeout=180):
    out_path = os.path.splitext(glb_path)[0] + ".godot_import.json"
    cmd = [godot, "--headless", "--script", GATE_GD, "--", glb_path, out_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[godot-gate] {os.path.basename(glb_path)}: TIMEOUT")
        return False
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0 and proc.stderr:
        sys.stderr.write(proc.stderr)
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                return bool(json.load(f).get("ok"))
        except Exception:
            return False
    return proc.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("glb", nargs="?", help="a built .glb")
    ap.add_argument("--all", action="store_true",
                    help="every build/*.glb with a manifest")
    ap.add_argument("--require", action="store_true",
                    help="missing Godot binary = failure (CI)")
    args = ap.parse_args(argv)

    from nav_gate import find_godot
    godot, reason = find_godot()
    if godot is None:
        msg = f"[godot-gate] SKIP: no usable Godot 4 binary ({reason})"
        if args.require:
            print(msg + " -- --require set, failing")
            return 1
        print(msg)
        return 0

    targets = []
    if args.all:
        for g in sorted(glob.glob(os.path.join(HERE, "build", "*.glb"))):
            if os.path.exists(os.path.splitext(g)[0] + ".manifest.json"):
                targets.append(g)
    elif args.glb:
        targets = [args.glb]
    else:
        ap.error("give a glb path or --all")

    rc = 0
    for glb in targets:
        if not run_one(godot, glb):
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
