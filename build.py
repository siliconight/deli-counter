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


def _spec_mode(spec_path):
    try:
        import json
        with open(spec_path, "r", encoding="utf-8") as f:
            return json.load(f).get("mode")
    except Exception:
        return None


def build_one(blender, spec_path, out_paths):
    """out_paths: list of output file paths (one per format)."""
    runner = os.path.join(HERE, "_run_in_blender.py")
    joined = ";".join(out_paths)
    cmd = [blender, "--background", "--python", runner, "--",
           spec_path, joined]
    env = os.environ.copy()
    # Production profile: a pvp_heist configuration must always emit its
    # art-pass slot manifest (slots.json) — the Zoo kit contract depends on
    # it — so the modular emitter is forced on for pvp_heist builds.
    if _spec_mode(spec_path) == "pvp_heist":
        env.setdefault("DC_MODULAR", "1")
    print(f"[build] {os.path.basename(spec_path)} -> "
          f"{', '.join(os.path.basename(p) for p in out_paths)}")
    result = subprocess.run(cmd, env=env)
    ok = result.returncode == 0
    # persist validation evidence next to the outputs (spec-level chain);
    # a build without stored proof is not a production build.
    if ok:
        try:
            import evidence
            out_dir = os.path.dirname(out_paths[0]) or os.path.join(HERE, "build")
            evidence.write_reports(spec_path, out_dir)
        except SystemExit:
            pass
        except Exception as ex:
            print(f"[build] WARNING: evidence reports not written ({ex})")
    return ok


def _emit_tscn(build_dir, name, res_root):
    """Write <name>.tscn from the slot manifest the build produced. The manifest
    only exists for a modular build, so skip (with a note) otherwise."""
    slots_json = os.path.join(build_dir, name + ".slots.json")
    if not os.path.exists(slots_json):
        print(f"[build] no slot manifest for {name} -- run a modular build "
              f"(DC_MODULAR=1) to emit a .tscn; skipping")
        return False
    import tscn_export
    out = os.path.join(build_dir, name + ".tscn")
    tscn_export.tscn_from_manifest(slots_json, out, res_root)
    print(f"[build] scene -> {out}")
    return True


def _out_paths(build_dir, name, formats, explicit_out):
    if explicit_out:
        return [explicit_out]
    return [os.path.join(build_dir, f"{name}.{fmt}") for fmt in formats]


#: Level Factory writes one spec per mission candidate into `specs/`, named
#: `lf_<mission>_<seed>`. Those are WORKSPACE TRANSIENTS, not library
#: archetypes -- `catalog.py` has excluded them since roadmap 73 and
#: `building_library.index` refuses the ids outright, for the same reason.
#: `--all` did not, and it is the one place that turns a spec into geometry.
#:
#: MEASURED 2026-09-06. A `presets.py` edit fossilised the library by mtime, so
#: `build.py --all` was run as the freshness gate instructs -- and it built 33
#: transients into `build/`, where the nav gate then gated them like archetypes.
#: Three of the six shells that failed traversal were transients from a cold run
#: earlier the same day, and they blocked the commit that the rebuild existed to
#: unblock. The library has never tracked an `lf_*` shell: `.gitignore` excludes
#: `build/*.glb`, and 0 of them were ever committed.
_TRANSIENT_PREFIX = "lf_"


#: Shells whose stairs do not traverse a baked navmesh. NOT BUILT, which is
#: the whole mechanism: no `.glb` means `nav_gate --all` has nothing to gate,
#: and no `manifest.json` means the lot pool stops offering them -- the CLI
#: already reports that path as "excluded from the lot for a missing
#: manifest". One list, and the three consequences follow.
#:
#: QUARANTINE RATHER THAN DELETION, deliberately. The spec stays on disk, the
#: reason is written down beside the id, and re-admitting one is deleting a
#: line here after `python nav_gate.py build/<name>.glb` passes. Removing the
#: specs instead would lose the evidence and make the fix unverifiable.
#:
#: ROADMAP 113. Measured 2026-09-07 from the gate's own island data rather
#: than reasoned from source geometry -- `docs/NAV_GATE_FINDINGS.md` records
#: four mechanisms proposed by static measurement here and refuted by their
#: own data. The shape is the same in all three: the stair ramp bakes as
#: DISCONNECTED FRAGMENTS with a hole part-way up, so the lower and upper
#: endpoints land on different islands and the pathfinder correctly refuses.
#: These are dense hand-authored interiors, the same population as `cr_deli`,
#: which broke at the FOOT of its flight and now passes after a rebuild.
#: TWO OF THE ORIGINAL THREE WERE RE-ADMITTED IN 0.105.0, which is the
#: mechanism working as intended: `night_pawn` and
#: `cbp_town_finale_midbalanced_schemafixed` had a wall standing where their
#: stair goes (roadmap 114), and once the geometry stopped doing that both
#: passed `nav_gate` and their lines came out of this dict. The spec that
#: remains is a DIFFERENT defect, so it stays.
_QUARANTINE = {
    "primos_pizza":
        "stair_0 no_path -- lower island y -2.90..0.10, upper y 1.00..3.55: "
        "a 0.90 m gap. The flight runs through ext_col_0_N_lintel1, the "
        "EXTERIOR wall: the stair sits at y 4.5 with run 5.2, so its reserved "
        "rectangle reaches y 7.9 in a building whose north face is at y 7.0. "
        "Roadmap 115 -- the stair has to move or shorten; cutting the shell "
        "to let it out would breach the envelope",
}


def _spec_paths() -> list:
    """Every authored spec in specs/, excluding transients and quarantine.

    The transient rule and prefix are `catalog._library_specs`'s, deliberately:
    two tools disagreeing about what counts as a library spec is how a
    transient ends up in a gate.
    """
    out = []
    for pattern in ("*.json", "*.yaml", "*.yml"):
        out += glob.glob(os.path.join(HERE, "specs", pattern))
    keep = []
    for p in sorted(out):
        stem = os.path.splitext(os.path.basename(p))[0]
        if stem.startswith(_TRANSIENT_PREFIX) or stem in _QUARANTINE:
            continue
        keep.append(p)
    return keep


def _report_quarantine() -> None:
    """Say what is being left out, every time. A silent exclusion is how a
    shell stays broken for a month without anybody deciding that it should."""
    for name in sorted(_QUARANTINE):
        print(f"[build] QUARANTINED (roadmap 115): {name} -- "
              f"{_QUARANTINE[name]}")


def _watch_loop(blender, build_dir, formats, single_spec=None, interval=1.0):
    """Poll specs/ mtimes and rebuild changed specs on save. Stdlib only — no
    watchdog dependency. Watches a single spec if given, else every spec in
    specs/. Ctrl-C to stop. New specs that appear while watching are picked up."""
    import time

    def current_specs():
        if single_spec:
            return [single_spec]
        return _spec_paths()

    mtimes = {}
    # seed mtimes WITHOUT building, so we only react to changes from here on
    for sp in current_specs():
        try:
            mtimes[sp] = os.path.getmtime(sp)
        except OSError:
            pass
    target = (os.path.basename(single_spec) if single_spec
              else f"{len(mtimes)} spec(s) in specs/")
    print(f"[watch] watching {target} — save a spec to rebuild it, Ctrl-C to stop")
    try:
        while True:
            time.sleep(interval)
            for sp in current_specs():
                try:
                    mt = os.path.getmtime(sp)
                except OSError:
                    continue
                if sp not in mtimes:
                    print(f"[watch] new spec: {os.path.basename(sp)}")
                if mtimes.get(sp) != mt:
                    mtimes[sp] = mt
                    name = os.path.splitext(os.path.basename(sp))[0]
                    outs = _out_paths(build_dir, name, formats, None)
                    ok = build_one(blender, sp, outs)
                    print(f"[watch] {'rebuilt' if ok else 'FAILED'} "
                          f"{os.path.basename(sp)} — waiting for next change")
    except KeyboardInterrupt:
        print("\n[watch] stopped")


def main():
    ap = argparse.ArgumentParser(description="Build levels from specs.")
    ap.add_argument("spec", nargs="?", help="path to a .json/.yaml spec")
    ap.add_argument("--out", help="explicit output path (single format, "
                    "overrides --format)")
    ap.add_argument("--format", "-f", default="glb",
                    help="comma-separated formats: glb,gltf,obj (default glb)")
    ap.add_argument("--all", action="store_true",
                    help="build every spec in specs/")
    ap.add_argument("--watch", action="store_true",
                    help="watch specs/ and rebuild on save (a spec path limits "
                         "the watch to that one); Godot auto-reimports the .glb")
    ap.add_argument("--blender", help="path to the Blender executable")
    ap.add_argument("--tscn-res-root", default=os.environ.get(
        "DC_TSCN_RES_ROOT", "res://"),
        help="res:// root where the module GLBs live in your Godot project "
             "(for --format tscn). e.g. res://art/zoo")
    ap.add_argument("--zoo", action="store_true",
        help="generate a zoo .tscn (every module knolled with scale refs + "
             "labels) from --zoo-dir and exit")
    ap.add_argument("--zoo-dir", default="art/zoo",
        help="local folder of module .glb files to lay out for --zoo")
    args = ap.parse_args()

    formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]
    valid = {"glb", "gltf", "obj", "tscn"}
    bad = set(formats) - valid
    if bad:
        sys.exit(f"Unknown format(s): {', '.join(bad)}. Use glb, gltf, obj.")

    build_dir = os.path.join(HERE, "build")
    os.makedirs(build_dir, exist_ok=True)

    # --zoo needs no Blender or spec: it just lays out a folder of module GLBs.
    if args.zoo:
        import zoo_export
        out = os.path.join(build_dir, "zoo.tscn")
        try:
            zoo_export.zoo_from_dir(args.zoo_dir, args.tscn_res_root, out)
            print(f"[build] zoo -> {out}")
            sys.exit(0)
        except FileNotFoundError as e:
            print(f"[build] {e}")
            sys.exit(1)

    blender = find_blender(args.blender)
    if not blender:
        sys.exit("Blender not found. Set $BLENDER, use --blender, or add it "
                 "to PATH.")

    # .tscn is not a Blender export -- it's a serialization of the slot manifest
    # the build writes. Strip it from the formats Blender handles; emit it after.
    want_tscn = "tscn" in formats
    formats = [f for f in formats if f != "tscn"]
    if want_tscn and not formats:
        formats = ["glb"]   # still need a geometry build so slots.json is written

    if args.watch:
        _watch_loop(blender, build_dir, formats,
                    single_spec=args.spec if args.spec else None)
        return

    if args.all:
        specs = _spec_paths()
        _report_quarantine()
        if not specs:
            sys.exit("No specs found in specs/")
        ok = True
        for sp in specs:
            name = os.path.splitext(os.path.basename(sp))[0]
            outs = _out_paths(build_dir, name, formats, None)
            ok = build_one(blender, sp, outs) and ok
            if want_tscn:
                _emit_tscn(build_dir, name, args.tscn_res_root)
        sys.exit(0 if ok else 1)

    if not args.spec:
        ap.error("provide a spec path or --all")

    name = os.path.splitext(os.path.basename(args.spec))[0]
    outs = _out_paths(build_dir, name, formats, args.out)
    ok = build_one(blender, args.spec, outs)
    if want_tscn:
        _emit_tscn(build_dir, name, args.tscn_res_root)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
