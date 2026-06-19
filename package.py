#!/usr/bin/env python3
"""
package.py  --  build a versioned release zip of Deli Counter
=============================================================
Produces dist/deli_counter-<KIT_VERSION>.zip from the working tree, excluding
build artifacts, caches, and the dist/ folder itself. The version comes from
version.py so the zip name always matches the code.

    python package.py            # -> dist/deli_counter-0.5.0.zip
    python package.py --check    # print what version would be packaged

The zip unpacks to the repo contents at top level (no nested folder), matching
how the repo is laid out.
"""

import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from version import KIT_NAME, KIT_VERSION  # noqa: E402

# dirs pruned from the walk entirely
PRUNE_DIRS = {".git", "__pycache__", "dist"}
EXCLUDE_BUILD_BINARIES = (".glb", ".gltf", ".bin", ".obj", ".mtl")


def _included(relpath):
    parts = relpath.split(os.sep)
    # drop build/ binaries but keep build/.gitkeep and manifests
    if parts and parts[0] == "build":
        base = os.path.basename(relpath)
        if base == ".gitkeep" or base.endswith(".manifest.json"):
            return True
        if relpath.lower().endswith(EXCLUDE_BUILD_BINARIES):
            return False
    if relpath.lower().endswith(".pyc"):
        return False
    return True


def main():
    if "--check" in sys.argv:
        print(f"{KIT_NAME} {KIT_VERSION}")
        return

    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, f"deli_counter-{KIT_VERSION}.zip")

    # write a VERSION stamp into the package root
    with open(os.path.join(HERE, "VERSION"), "w", encoding="utf-8") as f:
        f.write(f"{KIT_NAME} {KIT_VERSION}\n")

    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(HERE):
            dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, HERE)
                if not _included(rel):
                    continue
                z.write(full, rel)
                n += 1
    print(f"Wrote {out} ({n} files)")


if __name__ == "__main__":
    main()
