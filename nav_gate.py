#!/usr/bin/env python3
"""
nav_gate.py  --  run the headless Godot stair-traversal gate
============================================================
The offline analyzers (stairwell.py, navigability.py) are PROXIES; the
authoritative answer to "can a body walk this stair?" is the engine's own
navmesh. This wrapper runs godot/addon/deli_counter/nav_gate.gd headlessly
against a BUILT shell:

    python nav_gate.py build/bank_job.glb
    python nav_gate.py --all                # every build/*.glb with gameplay.json
    python nav_gate.py --all --require      # missing Godot = failure (CI)

For every traversable stair system in <name>.gameplay.json the gate bakes a
navmesh (same agent as the F4 harness bake) and proves a path between the
stair's lower and upper nav endpoints; the polygon graph is undirected, so
the reverse direction is the same proof. Markers get the documented F5
connectivity check as a warn-only section.

Godot discovery: $DC_GODOT, then godot4 / godot / godot4-headless /
godot-headless on PATH. A Godot 3.x binary is refused (the addon and this
gate are Godot 4 API). Without a usable binary the gate SKIPS with a note --
pass --require to turn a skip into a failure (CI environments with Godot
installed should).

Shells built before v0.76 carry no nav_endpoints; their stairs report
"skipped (rebuild with >= 0.76)".
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GATE_GD = os.path.join(HERE, "godot", "addon", "deli_counter", "nav_gate.gd")
_CANDIDATES = ("godot4", "godot", "godot4-headless", "godot-headless")


def find_godot(env=None):
    """Path to a usable Godot 4 binary, or (None, reason)."""
    env = env if env is not None else os.environ
    tried = []
    names = [env["DC_GODOT"]] if env.get("DC_GODOT") else list(_CANDIDATES)
    for name in names:
        path = name if os.path.sep in name else shutil.which(name)
        if not path or not os.path.exists(path):
            tried.append(f"{name}: not found")
            continue
        try:
            out = subprocess.run([path, "--version"], capture_output=True,
                                 text=True, timeout=30)
            version = (out.stdout or out.stderr).strip().splitlines()[0] \
                if (out.stdout or out.stderr).strip() else ""
        except Exception as ex:                       # noqa: BLE001
            tried.append(f"{name}: {ex}")
            continue
        if version.startswith("4."):
            return path, version
        tried.append(f"{name}: version '{version}' is not Godot 4")
    return None, "; ".join(tried)


def run_gate(glb_path, gameplay_path=None, godot=None, timeout=300):
    """Run the gate for one built shell. Returns the result dict (parsed
    from the gate's out.json) with an added 'exit_code', or a dict with
    'skipped' set when no Godot 4 binary is available."""
    if gameplay_path is None:
        gameplay_path = os.path.splitext(glb_path)[0] + ".gameplay.json"
    if not os.path.exists(glb_path):
        raise FileNotFoundError(glb_path)
    if not os.path.exists(gameplay_path):
        raise FileNotFoundError(gameplay_path)
    if godot is None:
        godot, why = find_godot()
        if godot is None:
            return {"skipped": True,
                    "reason": f"no Godot 4 binary ({why}); the offline "
                              f"review remains a proxy until this gate runs"}
    out_path = os.path.splitext(glb_path)[0] + ".navgate.json"
    cmd = [godot, "--headless", "--script", GATE_GD, "--",
           glb_path, gameplay_path, out_path]
    try:
        from agent_contract import nav_env
        env = nav_env()
    except Exception:                                  # noqa: BLE001
        env = None
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, env=env)
    result = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                result = json.load(f)
        except (OSError, json.JSONDecodeError):
            result = {}
    result.setdefault("glb", glb_path)
    result["exit_code"] = proc.returncode
    result["stdout"] = proc.stdout
    if proc.returncode not in (0, 1):     # 2/etc = the gate itself broke
        result.setdefault("error", (proc.stderr or proc.stdout or
                                    "gate crashed").strip()[:500])
    return result


def verdict(result):
    """(ok, lines) human summary for one gate result."""
    if result.get("skipped"):
        return True, [f"SKIP: {result['reason']}"]
    lines = []
    ok = result.get("exit_code") == 0 and result.get("ok", False)
    if result.get("error"):
        return False, [f"gate error: {result['error']}"]
    lines.append(f"navmesh polys: {result.get('navmesh_polys', '?')}")
    for st in result.get("stairs", []):
        lines.append(f"stair {st.get('id')}: {st.get('status')} "
                     f"({st.get('detail', '')})")
    mk = result.get("markers") or {}
    if mk.get("checked"):
        lines.append(f"markers: {mk.get('reachable', 0)}/{mk['checked']} "
                     f"reachable from spawn")
        for u in mk.get("unreachable", []):
            lines.append(f"  unreachable: {u}")
    return ok, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("glb", nargs="?", help="a built shell .glb")
    ap.add_argument("--all", action="store_true",
                    help="gate every build/*.glb that has a gameplay.json")
    ap.add_argument("--require", action="store_true",
                    help="treat a missing Godot binary as failure (CI)")
    args = ap.parse_args()

    godot, info = find_godot()
    if godot is None:
        msg = f"nav-gate: no Godot 4 binary ({info})"
        if args.require:
            print(f"FAIL: {msg}")
            sys.exit(1)
        print(f"NOTE: {msg}; skipping the traversal gate. The offline "
              f"review is a proxy -- install Godot 4 (or set DC_GODOT) to "
              f"run the authoritative check.")
        sys.exit(0)
    print(f"nav-gate: using {godot} ({info})")

    if args.all:
        targets = [g for g in sorted(glob.glob(os.path.join(HERE, "build",
                                                            "*.glb")))
                   if os.path.exists(os.path.splitext(g)[0]
                                     + ".gameplay.json")]
    elif args.glb:
        targets = [args.glb]
    else:
        ap.error("pass a .glb or --all")
        return

    failed = 0
    for glb in targets:
        print(f"\n== {os.path.basename(glb)} ==")
        result = run_gate(glb, godot=godot)
        ok, lines = verdict(result)
        for line in lines:
            print(f"  {line}")
        if not ok:
            failed += 1
    print()
    if failed:
        print(f"nav-gate: {failed}/{len(targets)} shell(s) FAILED traversal")
        sys.exit(1)
    print(f"nav-gate: {len(targets)} shell(s) passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
