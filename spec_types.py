"""
spec_types.py  --  pure-Python spec dataclasses (no bpy)
========================================================
The vocabulary you describe a building in. Importable outside Blender, so
validation and loading work in normal Python; only the builder needs bpy.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal

Axis = Literal["X", "Y"]           # which way a wall runs
Wall = Literal["N", "S", "E", "W"] # exterior wall, +Y/-Y/+X/-X
Collision = Literal["convex", "trimesh", "none"]

# Collision strategy for an imported (kitbashed) asset:
#   convex  -> auto convex hull of the asset (default; fast, single shape)
#   box     -> axis-aligned bounding box (cheapest)
#   file    -> use the asset's separate low-poly collision file (Asset.collision_file)
#   trimesh -> use the asset mesh itself as concave collision (static only, costly)
#   none    -> visual only, no collision
AssetCollision = Literal["convex", "box", "file", "trimesh", "none"]


@dataclass
class Asset:
    """A registered kitbash source model in the asset library.

    Files are vendored under assets/ in the repo and referenced by a stable
    `id`. Placements refer to assets by id, so moving/renaming a file is a
    one-line change here, not across every placement.
    """
    id: str
    file: str                              # path relative to assets/ (e.g. "props/crate.glb")
    fmt: Literal["glb", "gltf", "obj", "blend"] = "glb"
    collision: "AssetCollision" = "convex"  # default strategy for this asset
    collision_file: Optional[str] = None    # low-poly mesh, used when collision="file"
    # blend-only: name of the object/collection to append from the .blend
    blend_object: Optional[str] = None


@dataclass
class Placement:
    """One instance of an asset placed in the level. Multiple placements can
    reference the same asset id (instanced kitbashing)."""
    asset: str                             # Asset.id
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    # rotation in degrees about each axis (applied X, then Y, then Z)
    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0
    # uniform scale, or per-axis if scale_xyz given
    scale: float = 1.0
    scale_xyz: Optional[tuple[float, float, float]] = None
    # override the asset's default collision for this placement (optional)
    collision: Optional["AssetCollision"] = None
    name: Optional[str] = None             # optional instance name suffix


@dataclass
class Opening:
    """A door or window cut into a wall."""
    kind: Literal["door", "window", "garage", "breach"] = "door"
    # position along the wall's run, as a fraction -0.5..0.5 of wall length
    pos: float = 0.0
    width: Optional[float] = None    # m; defaults per kind
    height: Optional[float] = None   # m; defaults per kind
    sill: Optional[float] = None     # m off floor; defaults per kind
    # 'breach' = soft/destructible panel: collision tagged so you can swap it
    # out at runtime for the breaching mechanic.

    def resolved(self):
        d = dict(width=self.width, height=self.height, sill=self.sill)
        defaults = {
            "door":   dict(width=1.2, height=2.2, sill=0.0),
            "window": dict(width=1.6, height=1.4, sill=1.0),
            "garage": dict(width=3.5, height=3.0, sill=0.0),
            "breach": dict(width=1.5, height=2.2, sill=0.0),
        }[self.kind]
        for k, v in defaults.items():
            if d[k] is None:
                d[k] = v
        return d


@dataclass
class ExtWall:
    """An exterior wall on one side of one story, with its openings."""
    wall: Wall
    story: int
    openings: list[Opening] = field(default_factory=list)


@dataclass
class Partition:
    """An interior wall. Local coords, centered on building origin."""
    story: int
    axis: Axis                       # "X" runs east-west, "Y" runs north-south
    pos: float                       # offset (m) on the perpendicular axis
    start: float                     # start coord (m) along axis
    end: float                       # end coord (m) along axis
    openings: list[Opening] = field(default_factory=list)


@dataclass
class Stairwell:
    """Straight or switchback run connecting a range of stories."""
    x: float
    y: float
    from_story: int
    to_story: int
    width: float = 1.6
    run: float = 4.0
    style: Literal["straight", "switchback"] = "switchback"
    cut_slabs: bool = True           # punch holes in slabs it passes through


@dataclass
class SlabHole:
    """Rectangular opening in a story's floor slab (atrium, shaft, hatch)."""
    story: int
    x: float
    y: float
    size_x: float
    size_y: float


@dataclass
class Volume:
    """A solid box: vault, pillar, machine, crate stack, ramp. Generic prop."""
    name: str
    x: float
    y: float
    z: float
    size_x: float
    size_y: float
    size_z: float
    collision: Collision = "convex"
    visual: bool = True


@dataclass
class Parapet:
    story: int                       # roof level = top story index
    height: float = 1.0
    thick: float = 0.2


@dataclass
class LevelSpec:
    name: str = "level"
    seed: int = 1999
    grid: float = 0.5

    footprint_x: float = 24.0
    footprint_y: float = 18.0
    story_height: float = 3.5
    n_stories: int = 3
    has_basement: bool = False

    wall_thick: float = 0.3
    floor_thick: float = 0.3
    collision: Collision = "convex"  # default for walls/slabs

    ext_walls: list[ExtWall] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)
    stairs: list[Stairwell] = field(default_factory=list)
    slab_holes: list[SlabHole] = field(default_factory=list)
    volumes: list[Volume] = field(default_factory=list)
    parapets: list[Parapet] = field(default_factory=list)

    # kitbashing: a library of source models + their placed instances
    assets: list[Asset] = field(default_factory=list)
    placements: list[Placement] = field(default_factory=list)
    # where vendored asset files live, relative to the spec file
    assets_dir: str = "../assets"

    # if no ext_walls are specified, auto-generate solid exterior walls
    auto_exterior: bool = True


