"""
spec_loader.py  --  build a LevelSpec from a plain dict (JSON or YAML)
=======================================================================
Keeps level data out of code. A spec is a .json file (or .yaml if PyYAML is
installed); this module parses it into the heist_kit dataclasses.

The dict shape mirrors the dataclasses exactly -- see schema/level.schema.json
and specs/bank.json for the canonical structure.
"""

import json
import os

from spec_types import (
    LevelSpec, ExtWall, Opening, Partition, Stairwell,
    SlabHole, Volume, Parapet, Asset, Placement,
)


def _openings(raw):
    return [Opening(**o) for o in (raw or [])]


def spec_from_dict(d: dict) -> LevelSpec:
    """Convert a parsed dict into a LevelSpec. Raises KeyError/TypeError on
    malformed input -- run validate.py first for friendly error messages."""
    ext_walls = [
        ExtWall(wall=w["wall"], story=w["story"], openings=_openings(w.get("openings")))
        for w in d.get("ext_walls", [])
    ]
    partitions = [
        Partition(
            story=p["story"], axis=p["axis"], pos=p["pos"],
            start=p["start"], end=p["end"], openings=_openings(p.get("openings")),
        )
        for p in d.get("partitions", [])
    ]
    stairs = [Stairwell(**s) for s in d.get("stairs", [])]
    slab_holes = [SlabHole(**h) for h in d.get("slab_holes", [])]
    volumes = [Volume(**v) for v in d.get("volumes", [])]
    parapets = [Parapet(**p) for p in d.get("parapets", [])]
    assets = [Asset(**a) for a in d.get("assets", [])]
    placements = []
    for p in d.get("placements", []):
        p = dict(p)
        if isinstance(p.get("scale_xyz"), list):
            p["scale_xyz"] = tuple(p["scale_xyz"])
        placements.append(Placement(**p))

    top = {k: v for k, v in d.items() if k not in (
        "$schema",
        "ext_walls", "partitions", "stairs", "slab_holes", "volumes",
        "parapets", "assets", "placements",
    )}
    return LevelSpec(
        ext_walls=ext_walls, partitions=partitions, stairs=stairs,
        slab_holes=slab_holes, volumes=volumes, parapets=parapets,
        assets=assets, placements=placements, **top,
    )


def load_spec(path: str) -> LevelSpec:
    """Load a .json (always) or .yaml/.yml (if PyYAML available) spec file."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError:
                raise RuntimeError(
                    "YAML spec requires PyYAML (pip install pyyaml), "
                    "or convert the spec to .json."
                )
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    return spec_from_dict(data)
