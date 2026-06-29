#!/usr/bin/env python3
"""
package.py  --  build a versioned release zip of Deli Counter
=============================================================
Produces dist/deli_counter-<KIT_VERSION>.zip from the working tree, excluding
build artifacts, caches, and the dist/ folder itself. The version comes from
version.py so the zip name always matches the code.

    python package.py            # -> dist/deli_counter-<KIT_VERSION>.zip (full source)
    python package.py --addon    # -> dist/deli_counter-godot-addon-<plugin>.zip (drop-in)
    python package.py --check    # print what version would be packaged

The full zip unpacks to the repo contents at top level (no nested folder). The
--addon zip is rooted at `addons/deli_counter/` so it unzips straight into a
Godot project. Both are built by the release workflow on a version tag.
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
    # build/ is regenerated output: keep only .gitkeep and manifests, drop
    # everything else (binaries, floorplan SVGs, etc.)
    if parts and parts[0] == "build":
        base = os.path.basename(relpath)
        if base == ".gitkeep" or base.endswith(".manifest.json"):
            return True
        return False
    if relpath.lower().endswith(".pyc"):
        return False
    return True


ADDON_DIR = os.path.join(HERE, "godot", "addon", "deli_counter")


def _addon_version():
    """Read the editor plugin version from plugin.cfg (versions separately
    from KIT_VERSION)."""
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(ADDON_DIR, "plugin.cfg"))
    return cfg["plugin"]["version"].strip().strip('"')


def build_addon_zip():
    """Build a DROP-IN Godot addon zip: contents are rooted at
    `addons/deli_counter/...` so a user unzips it at their Godot PROJECT ROOT
    and the plugin lands at res://addons/deli_counter/ — then enable it in
    Project Settings -> Plugins. No need to clone the whole tool repo."""
    ver = _addon_version()
    dist = os.path.join(HERE, "dist")
    os.makedirs(dist, exist_ok=True)
    out = os.path.join(dist, f"deli_counter-godot-addon-{ver}.zip")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(ADDON_DIR):
            dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
            for fn in files:
                if fn.endswith(".pyc"):
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, ADDON_DIR)
                arc = os.path.join("addons", "deli_counter", rel)
                z.write(full, arc)
                n += 1
    print(f"Wrote {out} ({n} files)")
    print("Unzip at your Godot project root, then enable Deli Counter in "
          "Project Settings -> Plugins.")


def main():
    if "--check" in sys.argv:
        print(f"{KIT_NAME} {KIT_VERSION}")
        return

    if "--addon" in sys.argv:
        build_addon_zip()
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
