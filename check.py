#!/usr/bin/env python3
"""
check.py  --  the source-control gate (no Blender needed)
=========================================================
Runs everything that can be checked without launching Blender:
  1. validate every spec (schema + loader)
  2. confirm CATALOG.md is up to date

Use as a pre-commit hook or CI step. Exits non-zero on any failure.

    python check.py
"""

import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def run(args):
    return subprocess.run([sys.executable] + args, cwd=HERE).returncode


def main():
    rc = 0
    print("== validating specs ==")
    rc |= run(["validate.py", "--all"])
    print("== auditing spec content coherence ==")
    rc |= run(["audit_specs.py"])
    print("== stair regression sweep (quick) ==")
    rc |= run(["stair_regression.py", "--quick"])
    print("== nav traversal gate (built shells; needs Godot 4) ==")
    rc |= run(["nav_gate.py", "--all"])
    print("== checking catalog freshness ==")
    rc |= run(["catalog.py", "--check"])
    if rc == 0:
        print("\nAll checks passed.")
    else:
        print("\nChecks failed. See output above.")
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
