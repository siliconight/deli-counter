"""
spec_loader.py  --  build a LevelSpec from a plain dict (JSON or YAML)
=======================================================================
Keeps level data out of code. A spec is a .json file (or .yaml if PyYAML is
installed); this module parses it into the deli_counter dataclasses.

The dict shape mirrors the dataclasses exactly -- see schema/level.schema.json
and specs/bank.json for the canonical structure.
"""

import json
import os

from spec_types import (
    LevelSpec, ExtWall, Opening, Partition, Stairwell,
    SlabHole, Volume, Parapet, Asset, Placement,
    Room, VerticalLink, Marker, Objective, LootSpawn, Zone, Material,
    Ladder, Ramp, VaultLedge, Platform,
)


def _openings(raw):
    return [Opening(**o) for o in (raw or [])]


def spec_from_dict(d: dict) -> LevelSpec:
    """Convert a parsed dict into a LevelSpec. Raises KeyError/TypeError on
    malformed input -- run validate.py first for friendly error messages."""
    ext_walls = [
        ExtWall(wall=w["wall"], story=w["story"],
                openings=_openings(w.get("openings")),
                material=w.get("material"))
        for w in d.get("ext_walls", [])
    ]
    partitions = [
        Partition(
            story=p["story"], axis=p["axis"], pos=p["pos"],
            start=p["start"], end=p["end"], openings=_openings(p.get("openings")),
            material=p.get("material"),
        )
        for p in d.get("partitions", [])
    ]
    stairs = [Stairwell(**s) for s in d.get("stairs", [])]
    ladders = [Ladder(**l) for l in d.get("ladders", [])]
    ramps = [Ramp(**r) for r in d.get("ramps", [])]
    vault_ledges = [VaultLedge(**v) for v in d.get("vault_ledges", [])]
    platforms = [Platform(**p) for p in d.get("platforms", [])]
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

    rooms = [Room(**r) for r in d.get("rooms", [])]
    vertical_links = [VerticalLink(**v) for v in d.get("vertical_links", [])]
    markers = [Marker(**m) for m in d.get("markers", [])]
    objectives = [Objective(**o) for o in d.get("objectives", [])]
    loot = [LootSpawn(**l) for l in d.get("loot", [])]
    zones = [Zone(**z) for z in d.get("zones", [])]
    materials = [Material(**m) for m in d.get("materials", [])]

    top = {k: v for k, v in d.items() if k not in (
        "$schema",
        "ext_walls", "partitions", "stairs", "slab_holes", "volumes",
        "parapets", "assets", "placements",
        "rooms", "vertical_links", "markers",
        "objectives", "loot", "zones", "materials",
        "ladders", "ramps", "vault_ledges", "platforms",
    )}
    return LevelSpec(
        ext_walls=ext_walls, partitions=partitions, stairs=stairs,
        ladders=ladders, ramps=ramps, vault_ledges=vault_ledges,
        platforms=platforms,
        slab_holes=slab_holes, volumes=volumes, parapets=parapets,
        assets=assets, placements=placements,
        rooms=rooms, vertical_links=vertical_links, markers=markers,
        objectives=objectives, loot=loot, zones=zones,
        materials=materials, **top,
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
