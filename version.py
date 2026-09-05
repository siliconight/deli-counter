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
# 0.102.0: exterior runs inset by half a wall thickness and a `wallEnd` post
# seats each corner (roadmap 58) -- collision and visuals both move, so a
# rebuilt .glb differs, which is the bump condition stated above.
# 0.102.1: a span's remainder is computed once, not twice by two routes that
# can straddle the sliver threshold -- geometry correction, so a rebuilt .glb
# differs on the affected spans.
# 0.103.0: `--seed`. THE DOCSTRING'S BUMP CONDITION IS NOT MET AND THIS BUMPS
# ANYWAY, which is worth stating rather than leaving for the next reader to
# wonder about. Geometry is UNCHANGED for every existing spec -- measured, not
# assumed: gas_station rebuilt byte-identical .glb, .slots.json and
# .gameplay.json across the change, with only `built_utc` moving. It bumps
# because the alternative is the drift this block was written to end (0.80.0
# stamped while VERSION read 0.95.0), and because from here output is
# SEED-DEPENDENT: the same preset at two seeds is two different buildings, so
# a manifest that cannot name the kit cannot explain why two models from one
# preset differ.
KIT_VERSION = "0.103.0"

# Schema version is separate: bump when level.schema.json changes shape.
SCHEMA_VERSION = "1.21.1"
