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

# Test files this gate CANNOT run, each with the reason it cannot. Anything
# not listed here is gated. Keep this list as short as the truth allows --
# every entry is a thing nobody is checking before a commit.
BLENDER_ONLY = [
    ("test_failing_fixtures.py",
     "imports bmesh -- needs a real Blender interpreter, not plain python"),
]


def run(args):
    return subprocess.run([sys.executable] + args, cwd=HERE).returncode


def main():
    rc = 0
    print("== unit suites (everything that runs without Blender) ==")
    # EVERY test_*.py except the ones that genuinely need Blender.
    #
    # This used to be a hand-written list of six files. The repo has 27, and
    # 26 of them run without bpy in 2.4 seconds TOTAL -- so the list was not
    # buying speed, it was buying blind spots. `test_lights.py` sat ungated
    # from the day it was written; `test_pvp_heist.py` was RED for twelve
    # days while the commit hook reported "All checks passed", because the
    # opposing-spawn sightline gate had been dead since 1c344a8 and nothing
    # here looked at it.
    #
    # Opt-OUT, not opt-in. A new pure test file is gated the moment it lands,
    # with nobody having to remember to add it. Excluding one is a deliberate
    # act that has to be written down below, with a reason.
    skipped = []
    args = ["-m", "pytest", "-q"]
    for f, why in BLENDER_ONLY:
        if os.path.exists(os.path.join(HERE, f)):
            args += ["--ignore=" + f]
            skipped.append((f, why))
    rc |= run(args)
    # Say the exclusions out loud every run. A quiet denylist becomes a
    # permanent one.
    for f, why in skipped:
        print(f"   NOT GATED: {f} -- {why}")
    print("== validating specs ==")
    rc |= run(["validate.py", "--all"])
    print("== auditing spec content coherence ==")
    rc |= run(["audit_specs.py"])
    print("== layout guard rails (LAYOUT_RULES.md) ==")
    rc |= run(["layout_lint.py", "--all"])
    print("== stair regression sweep (quick) ==")
    rc |= run(["stair_regression.py", "--quick"])
    # BEFORE the nav gate, deliberately. That gate grades the shells in
    # build/, and a stale shell does not make it answer weakly -- it makes it
    # answer wrongly with full confidence. `build_freshness.py` was written on
    # 2026-08-05 after `nav_gate --all` reported ten unwalkable stairs across
    # seven shells, every one a fossil, and its docstring proposed exactly this
    # wiring: "check.py already runs catalog.py --check to confirm CATALOG.md
    # is not stale. This is the same idea one directory over, for the artefacts
    # every downstream gate reads."
    #
    # It was not wired in, and on 2026-08-12 every shell in build/ was 4.2 days
    # behind the code. A ladder that `patch_dc_roof_voids.py` had already fixed
    # still climbed into a solid roof, because Zoo dressed a roof slot baked
    # three days before that slot could express a hole. Named first here so the
    # cause is read before the symptom.
    print("== build freshness (are the shells older than the code?) ==")
    rc |= run(["build_freshness.py"])
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
