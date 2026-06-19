"""
_run_in_blender.py  --  executed INSIDE Blender by build.py
============================================================
Not meant to be run in normal Python. build.py invokes:
    blender --background --python _run_in_blender.py -- <spec> <out>

It can also be run manually in Blender's Scripting workspace: set SPEC_PATH
and OUT_PATH below, then Alt+P.
"""

import sys
import os

# ---- manual-fallback defaults (used only if no `--` args are passed) -------
SPEC_PATH = ""   # e.g. r"C:\deli_counter\specs\bank.json"
OUT_PATH = ""    # e.g. r"C:\deli_counter\build\bank.glb"
# ----------------------------------------------------------------------------


def _parse_argv():
    argv = sys.argv
    if "--" in argv:
        extra = argv[argv.index("--") + 1:]
        spec = extra[0] if len(extra) >= 1 else SPEC_PATH
        out = extra[1] if len(extra) >= 2 else OUT_PATH
        return spec, out
    return SPEC_PATH, OUT_PATH


def main():
    spec_path, out_path = _parse_argv()
    if not spec_path:
        raise SystemExit("No spec path. Pass it after -- or set SPEC_PATH.")

    here = os.path.dirname(os.path.abspath(spec_path))
    pkg = os.path.dirname(os.path.abspath(__file__))
    for p in (pkg, here):
        if p not in sys.path:
            sys.path.append(p)

    from spec_loader import load_spec
    from deli_counter import build, export, write_gameplay_json

    spec = load_spec(spec_path)
    builder = build(spec, base_dir=os.path.dirname(os.path.abspath(spec_path)))
    # out_path may be a semicolon-separated list of targets (multi-format)
    written = []
    if out_path:
        for target in out_path.split(";"):
            target = target.strip()
            if not target:
                continue
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            export(target)
            written.append(target)
        # tactical companion json next to the first output
        g = builder.gameplay
        if written and (g["markers"] or g["rooms"] or g["vertical_links"]
                        or g["objectives"] or g["loot"] or g["zones"]):
            base = os.path.splitext(written[0])[0]
            write_gameplay_json(builder, base + ".gameplay.json")
        _write_manifest(spec_path, written)


def _write_manifest(spec_path, written):
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
        "built_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "outputs": [os.path.basename(p) for p in written],
    }
    if written:
        base = os.path.splitext(written[0])[0]
        mpath = base + ".manifest.json"
        with open(mpath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"[deli_counter] manifest -> {mpath}")


if __name__ == "__main__":
    main()
