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
KIT_VERSION = "0.45.1"

# Schema version is separate: bump when level.schema.json changes shape.
SCHEMA_VERSION = "1.8.0"
