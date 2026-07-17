"""
_run_in_blender.py  --  executed INSIDE Blender by build.py
============================================================
Two ways to run this:

1. HEADLESS (build.py drives it):
       blender --background --python _run_in_blender.py -- <spec> <out>

2. MANUAL, to look at the model in Blender's viewport:
   - Open Blender 4.x, Scripting workspace, open this file.
   - Set the three paths in the CONFIG block below (at minimum SPEC_PATH
     and PKG_DIR).
   - Leave OUT_PATH = "" to just BUILD INTO THE VIEWPORT (no export) so you
     can orbit the model and inspect the VISUAL / COLLISION / MARKERS
     collections. Set OUT_PATH to also export a .glb.
   - Press Run Script (Alt+P).
"""

import sys
import os

# ============================ CONFIG (manual run) ===========================
# Point SPEC_PATH at the spec you want to build. PKG_DIR must be the folder
# that contains deli_counter.py / spec_loader.py (this package). It's set
# explicitly because Blender's text editor can't always resolve __file__.
SPEC_PATH = r""        # e.g. r"C:\deli_counter\specs\stop_n_go.json"
PKG_DIR   = r""        # e.g. r"C:\deli_counter"
OUT_PATH  = r""        # "" = viewport only; or e.g. r"C:\deli_counter\build\stop_n_go.glb"
# ============================================================================


def _parse_argv():
    argv = sys.argv
    if "--" in argv:
        extra = argv[argv.index("--") + 1:]
        spec = extra[0] if len(extra) >= 1 else SPEC_PATH
        out = extra[1] if len(extra) >= 2 else OUT_PATH
        return spec, out
    return SPEC_PATH, OUT_PATH


def _resolve_pkg_dir(spec_path):
    """Find the folder holding deli_counter.py. Prefer the explicit PKG_DIR;
    fall back to __file__'s dir, then the spec's parent's parent."""
    candidates = []
    if PKG_DIR:
        candidates.append(PKG_DIR)
    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    if spec_path:
        # specs usually live in <pkg>/specs/, so the pkg is one level up
        candidates.append(os.path.dirname(os.path.dirname(os.path.abspath(spec_path))))
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "deli_counter.py")):
            return c
    return candidates[0] if candidates else os.getcwd()


def main():
    spec_path, out_path = _parse_argv()
    if not spec_path:
        raise SystemExit(
            "No spec path. Set SPEC_PATH (and PKG_DIR) in the CONFIG block, "
            "or pass the spec after -- on the command line.")

    pkg = _resolve_pkg_dir(spec_path)
    here = os.path.dirname(os.path.abspath(spec_path))
    for p in (pkg, here):
        if p and p not in sys.path:
            sys.path.append(p)

    try:
        from spec_loader import load_spec
        from deli_counter import (build, export, write_gameplay_json,
                                  write_slot_manifest, write_light_manifest)
    except ImportError as e:
        raise SystemExit(
            f"Could not import the kit from '{pkg}'. Set PKG_DIR in the CONFIG "
            f"block to the folder containing deli_counter.py. ({e})")

    spec = load_spec(spec_path)
    builder = build(spec, base_dir=here)

    if not out_path:
        # viewport-only: the model is now in the scene. Nothing to export.
        print(f"[deli_counter] built '{spec.name}' into the viewport — "
              "inspect the VISUAL / COLLISION / MARKERS collections. "
              "Set OUT_PATH to also export a .glb.")
        return

    written = []
    for target in out_path.split(";"):
        target = target.strip()
        if not target:
            continue
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        export(target)
        written.append(target)
    # tactical companion json next to the first output
    g = builder.gameplay
    if written:
        base = os.path.splitext(written[0])[0]
        if (g["markers"] or g["rooms"] or g["vertical_links"]
                or g["objectives"] or g["loot"] or g["zones"] or g["surfaces"]):
            write_gameplay_json(builder, base + ".gameplay.json")
        # art-pass slot manifest (only when the modular emitter produced slots)
        if builder.slots:
            write_slot_manifest(builder, base + ".slots.json")
        # lighting contract (whenever there are rooms or windows to light)
        if g["rooms"] or any(o.get("kind") == "window"
                             for o in g.get("openings", [])):
            write_light_manifest(builder, base + ".lights.json")
    _write_manifest(spec_path, written, _expected_block(builder))


def _expected_block(builder):
    """Record the coordinate-contract EXPECTATIONS at build time, straight
    from the authoritative in-Blender scene: visual bounds, origin, floor
    elevations, marker positions. roundtrip.py re-imports the exported GLB
    and compares against this block (docs/COORDINATE_CONTRACT.md)."""
    try:
        import bpy
        from mathutils import Vector
        lo = [float("inf")] * 3
        hi = [float("-inf")] * 3
        vis = getattr(builder, "VISUAL", None)
        objs = vis.objects if vis is not None else []
        n = 0
        for ob in objs:
            if ob.type != "MESH":
                continue
            n += 1
            for c in ob.bound_box:
                w = ob.matrix_world @ Vector(c)
                for i in range(3):
                    lo[i] = min(lo[i], w[i])
                    hi[i] = max(hi[i], w[i])
        if not n:
            return None
        spec = builder.s
        g = builder.gameplay
        return {
            "space": "spec/Blender Z-up meters (see COORDINATE_CONTRACT.md)",
            "bounds_min": [round(v, 5) for v in lo],
            "bounds_max": [round(v, 5) for v in hi],
            "origin": [0.0, 0.0, 0.0],
            "story_height": spec.story_height,
            "floor_elevations": [round(i * spec.story_height, 5)
                                 for i in range(spec.n_stories)],
            "markers": [{"name": m.get("name", m.get("type")),
                         "type": m.get("type"),
                         "pos": [m.get("x", 0.0), m.get("y", 0.0),
                                 m.get("z", 0.0)]}
                        for m in g.get("markers", [])],
        }
    except Exception as ex:
        print(f"[deli_counter] WARNING: expected block not recorded ({ex})")
        return None


def _write_manifest(spec_path, written, expected=None):
    """Write a .manifest.json next to outputs: traces a model back to the
    exact spec content + kit version that produced it."""
    import json, hashlib, datetime
    try:
        from version import KIT_VERSION, SCHEMA_VERSION, KIT_NAME
    except Exception:
        KIT_VERSION = SCHEMA_VERSION = "unknown"
        KIT_NAME = "Deli Counter"
    with open(spec_path, "rb") as f:
        spec_bytes = f.read()
    spec_hash = hashlib.sha256(spec_bytes).hexdigest()[:16]
    manifest = {
        "kit_name": KIT_NAME,
        "kit_version": KIT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "spec": os.path.basename(spec_path),
        "spec_sha256_16": spec_hash,
        "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outputs": [os.path.basename(p) for p in written],
    }
    if expected is not None:
        manifest["expected"] = expected
    if written:
        base = os.path.splitext(written[0])[0]
        mpath = base + ".manifest.json"
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"[deli_counter] manifest -> {mpath}")


if __name__ == "__main__":
    main()
