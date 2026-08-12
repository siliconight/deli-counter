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

The gate's JSON carries `stairs_ok` (every traversable stair proved a path),
`ok` (the same value, kept because things read it), and `navigable` -- the
overall answer, tri-state, null when no marker was checked. verdict() below
still passes/fails on the STAIRS alone; it prints the navigable state so that
a shell which traverses fine and cannot reach its objective stops reading
identically to one that can. Results written before that split carry `ok`
alone and are reported as unjudged rather than assumed.

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
    # An EXPLICIT DC_GODOT is trusted without a --version probe: the probe
    # spawns the Windows console wrapper + engine child, and on a loaded
    # machine (fresh Blender builds, AV scanning new files) it can blow the
    # 30 s timeout and SKIP a gate against a perfectly good binary. If the
    # path is wrong the gate run itself fails loudly -- nothing is masked.
    if env.get("DC_GODOT"):
        p = env["DC_GODOT"]
        if os.path.exists(p):
            return p, "DC_GODOT (explicit, unprobed)"
        return None, f"DC_GODOT set but not found: {p}"
    names = list(_CANDIDATES)
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
    # THE CONTRACT IS NOT OPTIONAL. `nav_env` overwrites every DC_NAV_* with
    # the ratified numbers from agent_contract.json, which is what makes the
    # gate's verdict mean something: an ad-hoc env var cannot quietly change
    # what got certified. Swallowing the import and passing env=None dropped
    # the bake back onto nav_gate.gd's own fallbacks -- and those are STALE
    # (climb 0.5, cell 0.15) against a comment claiming they match the
    # ratified values. A gate that silently bakes with pre-2026-07-28 numbers
    # is not a gate. If the contract cannot be loaded, say so and stop.
    try:
        from agent_contract import nav_env
        env = nav_env()
    except Exception as ex:                            # noqa: BLE001
        return {"glb": glb_path, "exit_code": 2, "ok": False,
                "error": "could not load agent_contract.nav_env (%s) -- "
                         "refusing to bake with nav_gate.gd's fallback "
                         "numbers, which are not the ratified ones" % ex}
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
    # SCOPE THE MARKERS HERE, not in the gate. `nav_gate.gd` reports what it
    # measured -- each marker's position, snap and reachability -- and this is
    # where those become a verdict, because a rule that lives only in GDScript
    # is a rule nothing can red-test. The manifest is rewritten so the file on
    # disk carries ONE `navigable`, the scoped one; the gate's own print of it
    # is provisional and says so.
    footprint = []
    try:
        with open(gameplay_path, "r", encoding="utf-8") as f:
            footprint = (json.load(f) or {}).get("footprint") or []
    except (OSError, json.JSONDecodeError, AttributeError):
        footprint = []          # scope_markers reports this as UNSCOPED
    if isinstance(result.get("markers"), dict):
        scoped, navigable, why = scope_markers(
            result["markers"], footprint,
            stairs_ok=bool(result.get("stairs_ok", result.get("ok", False))))
        result["markers"] = scoped
        result["navigable"] = navigable
        result["navigable_reason"] = why
        if os.path.exists(out_path):
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
            except OSError:
                # The verdict in memory is still correct; a manifest that could
                # not be rewritten is a stale file, not a wrong answer.
                print(f"[nav-gate] WARNING: could not rewrite {out_path} with "
                      f"the scoped verdict")
    result["exit_code"] = proc.returncode
    result["stdout"] = proc.stdout
    if proc.returncode not in (0, 1):     # 2/etc = the gate itself broke
        result.setdefault("error", (proc.stderr or proc.stdout or
                                    "gate crashed").strip()[:500])
    return result


#: Marker types the gate asks about. Mirrors the list in `nav_gate.gd`
#: `_check_markers`; kept here because the scoping reads the rows it emits.
SCOPE_TYPES = ("objective", "extraction", "loot", "patrol_point", "rescue")

#: Who is supposed to answer for a marker this bake cannot reach. Written into
#: every scoped manifest so that "deferred" is a record with an owner rather
#: than a check that quietly stopped running.
DEFERRED_TO = ("site assembly: Lot lays the ground and streets these markers "
               "stand on, so reachability for them is a site-scope question "
               "and no building bake can answer it")


def marker_is_exterior(row, footprint):
    """Is this marker outside the building? None when that cannot be decided.

    `gameplay.json` carries `footprint` and every marker's `x, y`, so this is
    arithmetic on data both manifests already hold. It replaces a snap-distance
    threshold, which CORRELATES with being outside the building without being
    that fact: over the 135-shell library the two classifiers disagree ten
    times, six of them dropping a real interior defect as benign.

    The boundary is inclusive -- a marker exactly on the footprint line is
    INSIDE. A building owns its own threshold, and the other convention would
    defer doorway markers to a scope that has no reason to care about them.
    """
    if not footprint or len(footprint) < 2:
        return None
    try:
        half_x = abs(float(footprint[0])) / 2.0
        half_y = abs(float(footprint[1])) / 2.0
        return (abs(float(row.get("x", 0.0))) > half_x + 1e-6
                or abs(float(row.get("y", 0.0))) > half_y + 1e-6)
    except (TypeError, ValueError):
        return None


def scope_markers(markers, footprint, stairs_ok=True):
    """(markers, navigable, reason) -- judge only what this bake can see.

    Returns a NEW markers dict. `checked`, `reachable` and `unreachable` are
    carried through untouched: 135 `.navgate.json` files and
    `library_census.py` read them, and narrowing those in place would silently
    change what every existing file means. The scoped answer arrives alongside
    them as `interior_*` and `exterior_deferred`.

    `navigable` is TRI-STATE and null is load-bearing in three distinct
    situations, all of which mean nothing was measured:

      * no `detail` rows -- the result predates this split;
      * no footprint -- there is no inside to be on the wrong side of;
      * every checked marker deferred -- `parking_garage` ships one marker and
        it is exterior, and reading that as "navigable" is how a shell with
        nothing in it becomes the library's best candidate.

    Defaulting any of those to "all interior" would restore the old verdict
    under a new name. Defaulting to "all exterior" would pass everything.
    """
    markers = dict(markers or {})
    rows = markers.get("detail")
    if not isinstance(rows, list):
        return markers, None, (
            "UNSCOPED: this result carries no per-marker detail, so nothing "
            "here knows which markers are inside the building -- re-run the "
            "gate to classify them")
    flags = [marker_is_exterior(r, footprint) for r in rows]
    if any(f is None for f in flags):
        return markers, None, (
            "UNSCOPED: gameplay.json carries no usable `footprint`, so inside "
            "and outside are undefined for this shell and no marker can be "
            "scoped")

    interior = [r for r, ext in zip(rows, flags) if not ext]
    exterior = [r for r, ext in zip(rows, flags) if ext]
    unreached = [r for r in interior if not r.get("reachable")]
    markers["interior_checked"] = len(interior)
    markers["interior_reachable"] = len(interior) - len(unreached)
    markers["interior_unreachable"] = [
        "%s (snap %.1fm)" % (r.get("name", "?"), float(r.get("snap") or 0.0))
        for r in unreached]
    markers["exterior_deferred"] = [
        {"name": r.get("name", "?"), "type": r.get("type", ""),
         "snap": r.get("snap"), "reachable": bool(r.get("reachable"))}
        for r in exterior]
    markers["scope_note"] = DEFERRED_TO

    tail = ("; %d deferred to site scope (%s)"
            % (len(exterior), ", ".join(r.get("name", "?")
                                        for r in exterior[:4]))
            if exterior else "")
    if not stairs_ok:
        return markers, False, (
            "a stair is not traversable, so this shell cannot be walked "
            "whatever its markers say" + tail)
    if not interior:
        # TWO different ways to have measured nothing, and they are not the
        # same fact. `warehouse` has no spawn marker at all, so the gate
        # checked zero markers; `parking_garage` checks one and it is on the
        # street. Both are unjudged, and a manifest that describes the first
        # as "every checked marker is outside the building" is telling the
        # next reader something untrue about the shell.
        if not rows:
            return markers, None, (
                "UNJUDGED: no marker was checked at all (no spawn marker, or "
                "nothing of a checked type) -- nothing asked whether this "
                "shell connects")
        return markers, None, (
            "UNJUDGED: every checked marker is outside the building, so this "
            "bake measured nothing about it" + tail)
    if unreached:
        return markers, False, (
            "%d of %d interior marker(s) unreachable from spawn: %s"
            % (len(unreached), len(interior),
               ", ".join(markers["interior_unreachable"][:4])) + tail)
    return markers, True, (
        "stairs traverse and all %d interior marker(s) reachable from spawn"
        % len(interior) + tail)


def verdict(result):
    """(ok, lines) human summary for one gate result.

    The returned `ok` is the STAIR verdict and nothing more -- the same thing
    the gate's exit code means, unchanged. The reachability answer goes into
    `lines` as the gate's own tri-state `navigable`; promoting it to the
    return value is a separate decision with 107 of 137 shells behind it.
    """
    if result.get("skipped"):
        # NOTE: a skip still returns True here, and that is why `check.py`
        # printed "All checks passed" for months with this gate never having
        # baked anything. Changing it is a one-line edit; the reason it has
        # NOT been changed here is that 13 of 103 shells currently fail, so
        # flipping it now would block commits rather than inform anyone.
        # `--require` is the supported way to make a missing binary fail.
        # See docs/NAV_GATE_FINDINGS.md.
        return True, [f"SKIP: {result['reason']}"]
    lines = []
    # The gate prints `[nav-gate] bake: radius .. cell .. climb .. slope ..`
    # and this wrapper captured it into result["stdout"] and threw it away.
    # That is how a bake ran for months with numbers nobody could see.
    for ln in (result.get("stdout") or "").splitlines():
        if "bake:" in ln:
            lines.append(ln.strip().replace("[nav-gate] ", ""))
    # `ok` in the gate's JSON has always meant STAIRS ONLY, so read the key
    # that now says so. The fallback is not defensive habit: 137 .navgate.json
    # files sit in build/ that were written before the split and carry `ok`
    # alone, and re-running them all needs a Godot binary.
    stairs_ok = result.get("stairs_ok", result.get("ok", False))
    ok = result.get("exit_code") == 0 and stairs_ok
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
    else:
        lines.append("markers: 0 checked -- reachability UNJUDGED")
    # The scoped counts, when the result has them. Printed BESIDE the raw ones
    # rather than instead of them: 99 shells read "1 of 2 unreachable" and are
    # perfectly sound buildings, and the only way to see that from this output
    # is to see both numbers at once.
    if "interior_checked" in mk:
        lines.append(f"markers (interior): {mk.get('interior_reachable', 0)}/"
                     f"{mk['interior_checked']} reachable -- what this bake "
                     f"can actually judge")
        for u in mk.get("interior_unreachable", []):
            lines.append(f"  interior unreachable: {u}")
        for d in mk.get("exterior_deferred", []):
            lines.append(f"  deferred to site scope: {d.get('name')} "
                         f"(snap {d.get('snap')}m, outside the footprint)")
    # Say the tri-state out loud. Reading this output used to require noticing
    # that "markers: 0/1 reachable from spawn" sat one line under a verdict
    # that said the shell passed -- which is how 101 shells reported ok: true
    # with something unreachable in them.
    if "navigable" in result:
        nav = result["navigable"]
        word = "yes" if nav is True else ("NO" if nav is False else "UNJUDGED")
        why = result.get("navigable_reason") or ""
        lines.append(f"navigable: {word}" + (f" -- {why}" if why else ""))
    else:
        lines.append("navigable: UNJUDGED -- this result predates the "
                     "stairs/markers split; its `ok` means stairs only")
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
