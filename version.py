"""
version.py  --  single source of truth for the kit version
==========================================================
Deli Counter -- a spec-driven Blender level kit for Godot 4.

Bump KIT_VERSION when the builder's geometry output changes in a way that
would alter existing levels (so a rebuilt .glb differs). Record what changed
in CHANGELOG.md. Every build manifest stamps this version, so any model in
source control is traceable to the exact kit that produced it.

Versioning convention (semver-ish for a geometry generator):
  MAJOR  spec schema breaks (old specs won't load)
  MINOR  new spec features, output unchanged for old specs
  PATCH  bug fixes / geometry corrections
"""

KIT_NAME = "Deli Counter"
# 0.96.0: the slab VISUAL is tiled to light-budget-sized meshes (roadmap 54),
# so a rebuilt .glb differs -- exactly the bump condition stated above. This
# stamp had drifted from the repo VERSION file (it sat at 0.80.0 while the
# file reached 0.95.0), which defeats "traceable to the exact kit that
# produced it"; re-coupled to the release number here.
KIT_VERSION = "0.96.0"

# Schema version is separate: bump when level.schema.json changes shape.
SCHEMA_VERSION = "1.21.1"
