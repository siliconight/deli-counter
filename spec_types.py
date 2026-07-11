"""
spec_types.py  --  pure-Python spec dataclasses (no bpy)
========================================================
The vocabulary you describe a building in. Importable outside Blender, so
validation and loading work in normal Python; only the builder needs bpy.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Literal

Axis = Literal["X", "Y"]           # which way a wall runs
Wall = Literal["N", "S", "E", "W"] # exterior wall, +Y/-Y/+X/-X
Collision = Literal["convex", "trimesh", "none"]

# gool's AudioMaterial enum names. A Deli Counter material maps to one of
# these (so the game's audio raycaster can pass it straight to gool), OR
# supplies explicit absorption/damping floats for finer control.
AcousticMaterial = Literal[
    "Default", "Air", "Glass", "Wood", "Drywall",
    "Concrete", "Metal", "Curtain", "Foliage",
]

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
    kind: Literal["door", "window", "garage", "breach", "vault",
                  "teller", "safe_deposit"] = "door"
    # position along the wall's run, as a fraction -0.5..0.5 of wall length
    pos: float = 0.0
    width: Optional[float] = None    # m; defaults per kind
    height: Optional[float] = None   # m; defaults per kind
    sill: Optional[float] = None     # m off floor; defaults per kind
    # 'breach' = soft/destructible panel: collision tagged so you can swap it
    # out at runtime for the breaching mechanic.

    # --- optional tactical metadata (game-agnostic; ignored if unset) ---
    tag: Optional[str] = None              # e.g. "main_entry", "rear_access"
    breach_class: Optional[str] = None     # e.g. "soft_wall", "reinforceable"
    material: Optional[str] = None         # e.g. "drywall", "brick"
    vaultable: Optional[bool] = None       # window/low opening you can climb through
    reinforceable: Optional[bool] = None   # defenders can reinforce this
    # --- interactive fixture (networked state; see docs/INTERACTIVES.md) ---
    # Doors/garages and breach openings are interactive by INFERENCE (no
    # authoring needed). A window is interactive only when breakable=True.
    # `interactive` overrides the inference: False forces it off; a dict authors
    # a custom machine merged over the inferred one.
    breakable: Optional[bool] = None       # a window that can be broken/shot out
    interactive: Any = None                # None | False | dict override

    def resolved(self):
        d = dict(width=self.width, height=self.height, sill=self.sill)
        defaults = {
            "door":   dict(width=1.2, height=2.2, sill=0.0),
            "window": dict(width=1.6, height=1.4, sill=1.0),
            "garage": dict(width=3.5, height=3.0, sill=0.0),
            "breach": dict(width=1.5, height=2.2, sill=0.0),
            "vault":  dict(width=1.4, height=2.3, sill=0.15),
            "teller": dict(width=2.0, height=3.0, sill=0.0),
            "safe_deposit": dict(width=2.0, height=2.4, sill=0.0),
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
    material: Optional[str] = None   # palette id; overrides default_material


@dataclass
class Partition:
    """An interior wall. Local coords, centered on building origin."""
    story: int
    axis: Axis                       # "X" runs east-west, "Y" runs north-south
    pos: float                       # offset (m) on the perpendicular axis
    start: float                     # start coord (m) along axis
    end: float                       # end coord (m) along axis
    openings: list[Opening] = field(default_factory=list)
    material: Optional[str] = None   # palette id; overrides default_material


@dataclass
class Stairwell:
    """Straight or switchback run connecting a range of stories. Step count is
    derived from the floor height and target step_rise (so rise stays
    consistent regardless of story_height) unless n_steps is set explicitly.

    Semantic identity (all optional; see docs/stairwell_placement_spec.md):
    `role` opts the stair into the egress contract -- stairwell.py gates its
    route findings as hard errors instead of intel. `stack_id` groups stairs
    into one declared vertical stack that must chain and align (Rule 2)."""
    x: float
    y: float
    from_story: int
    to_story: int
    width: float = 1.6
    run: float = 4.0
    style: Literal["straight", "switchback"] = "switchback"
    cut_slabs: bool = True           # punch holes in slabs it passes through
    step_rise: float = 0.2           # target rise per step (m); game-feel default
    n_steps: Optional[int] = None    # override; else derived per floor
    id: Optional[str] = None         # stable id -> gameplay.json stair_systems
    role: Optional[str] = None       # primary_egress/secondary_egress/... (spec s5)
    stack_id: Optional[str] = None   # declared vertical stack membership (Rule 2)


@dataclass
class Ladder:
    """A vertical climb between two stories at (x,y). Pairs with a hatch/hole
    above. Generates rung geometry + side rails; cuts the slab it passes
    through. The player climbs at a fixed speed (game owns that)."""
    x: float
    y: float
    from_story: int
    to_story: int
    width: float = 0.5               # rail-to-rail (m)
    depth: float = 0.15              # rung depth off the wall (m)
    rung_spacing: float = 0.3        # vertical gap between rungs (m); exaggerated
    cut_slabs: bool = True
    facing: Literal["N", "S", "E", "W"] = "S"   # which way the climber faces


@dataclass
class Ramp:
    """An inclined walkable surface between two heights. Slope is derived from
    rise (story span) over run; flagged if it exceeds max_slope_deg (too steep
    to walk → should be stairs). Good for loot-carry / vehicle routes."""
    x: float
    y: float
    from_story: int
    to_story: int
    run: float = 8.0                 # horizontal length (m)
    width: float = 2.0
    axis: Literal["X", "Y"] = "Y"    # direction the ramp ascends
    thickness: float = 0.3
    cut_slabs: bool = True
    max_slope_deg: float = 30.0      # walkable ceiling; steeper warns in validate


@dataclass
class VaultLedge:
    """A waist-height ledge/low wall you can vault over within a floor (cover,
    counters, half-walls, window sills as obstacles). Solid box; the game
    treats sub-vault-height collision as vaultable."""
    x: float
    y: float
    story: int
    length: float = 2.0
    axis: Literal["X", "Y"] = "X"    # which way the ledge runs
    height: float = 1.1              # top height off floor (m); vaultable band
    thick: float = 0.2
    material: Optional[str] = None


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
    material: Optional[str] = None   # palette id; overrides default_material


@dataclass
class Parapet:
    story: int                       # roof level = top story index
    height: float = 1.0
    thick: float = 0.2


@dataclass
class Material:
    """An acoustic material in the level's palette. Deli Counter does NOT bake
    visual PBR (you texture in Godot); it writes this acoustic data into
    gameplay.json keyed by collision-node name, so the game's audio raycaster
    can hand the right material to gool's IAudioGeometryQuery on a wall hit.

    Specify EITHER `acoustic` (a gool AudioMaterial enum name) OR explicit
    `absorption`/`damping` floats (0..1). If both are given, the explicit
    floats win and `acoustic` is kept as a hint.
    """
    id: str
    acoustic: Optional["AcousticMaterial"] = None   # gool enum name
    absorption: Optional[float] = None              # 0..1 overall gain cut
    damping: Optional[float] = None                 # 0..1 HF rolloff


# ----------------------------------------------------------------------------
# TACTICAL GRAMMAR  --  optional gameplay layer (game-agnostic)
# ----------------------------------------------------------------------------

@dataclass
class Room:
    """A named tactical space on a story. bounds = [min_x, min_y, max_x, max_y]
    in level coords. Used for reachability/route validation and the scorecard,
    and emitted as a NAV_REGION marker for Godot."""
    id: str
    story: int
    bounds: list[float]                    # [min_x, min_y, max_x, max_y]
    role: Optional[str] = None             # "public_entry", "objective_room", "stairwell"...
    combat_range: Optional[str] = None     # "close", "medium", "long"
    fortifiable: Optional[bool] = None
    objective: bool = False                # convenience flag; role may also imply it
    roofed: bool = True                    # roof_mode="per_room": False = open-air (no roof slot)


@dataclass
class VerticalLink:
    """A designed vertical interaction connecting stories. 'stair' references
    an existing stairwell role; 'floor_hole'/'hatch' describe a vertical angle
    or drop point (these also cut the slab if cut_slab is true)."""
    kind: Literal["stair", "floor_hole", "hatch"] = "stair"
    role: Optional[str] = None             # "main_rotation", "vertical_angle"
    from_story: Optional[int] = None       # for stair
    to_story: Optional[int] = None
    story: Optional[int] = None            # for floor_hole / hatch
    x: Optional[float] = None
    y: Optional[float] = None
    size_x: Optional[float] = None
    size_y: Optional[float] = None
    breachable: Optional[bool] = None      # hatch
    cut_slab: bool = True                  # floor_hole/hatch punch the slab
    meta: Optional[dict] = None            # arbitrary extra data -> gameplay.json


@dataclass
class Marker:
    """A gameplay point baked into the GLB as a named empty AND written to the
    companion gameplay.json. type drives the node name prefix; Godot's import
    script maps these to game nodes.

    Common types: attacker_spawn, defender_spawn, objective, extraction,
    camera_socket, door_socket, breach_panel, cover_low, cover_high,
    patrol_point, loot, nav_region.
    """
    type: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rot_z: float = 0.0                     # facing, degrees
    id: Optional[str] = None               # suffix, e.g. "A" -> ATTACKER_SPAWN_A
    room: Optional[str] = None             # optional Room.id this belongs to
    meta: Optional[dict] = None            # arbitrary extra data -> gameplay.json


# ----------------------------------------------------------------------------
# HEIST GRAMMAR  --  PvE crew objectives, loot economy, extraction (mode=heist)
# ----------------------------------------------------------------------------

@dataclass
class Objective:
    """A heist task. Objectives are independent (completable in any order);
    set `required` to mark which must be done before extraction counts. Emitted
    as OBJECTIVE_<id> marker; interactable type drives Godot behavior."""
    id: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    kind: str = "interact"                 # "drill", "hack", "grab", "thermite", "interact"
    room: Optional[str] = None
    required: bool = True                  # must complete before extraction is valid
    duration: Optional[float] = None       # seconds (designer hint; game owns timing)
    meta: Optional[dict] = None


@dataclass
class LootSpawn:
    """A loot pickup. `value` is abstract bag/score value; `bags` how many
    carriable units it yields. Emitted as LOOT_<id> marker."""
    id: str
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    value: float = 1000.0
    bags: int = 1
    kind: str = "cash"                     # "cash", "gold", "art", "cargo", etc.
    room: Optional[str] = None
    meta: Optional[dict] = None


@dataclass
class Zone:
    """A volumetric gameplay region: secure/drop point for loot, or the
    extraction zone. bounds = [min_x, min_y, max_x, max_y]; spans the story.
    Emitted as <ZONE_TYPE>_ZONE_<id> marker with bounds in gameplay.json."""
    id: str
    kind: str = "extraction"               # "extraction", "secure", "drop"
    story: int = 0
    bounds: list[float] = field(default_factory=list)  # [minx,miny,maxx,maxy]
    meta: Optional[dict] = None


@dataclass
class LevelSpec:
    name: str = "level"
    seed: int = 1999
    grid: float = 0.5

    # tactical style: "assault" = symmetric attacker/defender breach play;
    # "heist" = PvE crew objectives + loot + extraction. Drives which
    # validation rules and scorecard apply. Default keeps old specs valid.
    mode: str = "heist"

    footprint_x: float = 24.0
    footprint_y: float = 18.0
    story_height: float = 3.5
    n_stories: int = 3
    has_basement: bool = False

    wall_thick: float = 0.3
    floor_thick: float = 0.3
    collision: Collision = "convex"  # default for walls/slabs

    # ROOF (the top-story ceiling slab, already baked by _slabs). Controls how
    # it presents; derivation reads only frozen structure, so changing it never
    # re-solves layout -- a passed greybox stays byte-identical below the roof.
    #   "solid" = today: baked visual + trimesh collision.
    #   "open"  = suppress the roof VISUAL for top-down authoring but KEEP
    #             collision (grenades/projectiles still bounce -- the fun-test view).
    #   "none"  = no top cap at all (visual + collision dropped).
    roof: str = "solid"
    # "footprint" = one slab over the whole plan (today). "per_room" = one roof
    # slot per top-story room, honoring Room.roofed (open-air rooms opt out).
    roof_mode: str = "footprint"
    roof_thick: Optional[float] = None   # None -> floor_thick

    # egress-pair separation heuristic (stairwell.py, Rule 6):
    # required = max(8.0 m, floor_plate_diagonal * separation_factor).
    # 0.33 = sprinklered approximation; 0.50 = conservative non-sprinklered.
    separation_factor: float = 0.33

    ext_walls: list[ExtWall] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)
    stairs: list[Stairwell] = field(default_factory=list)
    # author-declared intended designs the combat audit should report as
    # accepted instead of flagging: [{"code","room","why"}]
    audit_accept: list = field(default_factory=list)
    ladders: list[Ladder] = field(default_factory=list)
    ramps: list[Ramp] = field(default_factory=list)
    vault_ledges: list[VaultLedge] = field(default_factory=list)
    slab_holes: list[SlabHole] = field(default_factory=list)
    volumes: list[Volume] = field(default_factory=list)
    parapets: list[Parapet] = field(default_factory=list)

    # kitbashing: a library of source models + their placed instances
    assets: list[Asset] = field(default_factory=list)
    placements: list[Placement] = field(default_factory=list)
    # where vendored asset files live, relative to the spec file
    assets_dir: str = "../assets"

    # tactical grammar (all optional; plain building specs omit these)
    rooms: list[Room] = field(default_factory=list)
    vertical_links: list[VerticalLink] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)

    # heist grammar (mode="heist"): objectives, loot economy, zones
    objectives: list[Objective] = field(default_factory=list)
    loot: list[LootSpawn] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)

    # acoustic material palette (for gool). Surfaces reference by id; an
    # inline `material` on a wall/volume overrides. default_material applies
    # to any surface that names none.
    materials: list[Material] = field(default_factory=list)
    default_material: Optional[str] = None

    # if true, drop 1.8 m human-proxy capsules at each spawn marker into a
    # SCALE_REF collection — a quick visual scale check in Blender. Off by
    # default; the collection is separate so it never affects export.
    scale_ref: bool = False

    # if no ext_walls are specified, auto-generate solid exterior walls
    auto_exterior: bool = True

    # FACADE shell: a non-enterable filler building -- exterior shell + roof +
    # collision + theme ONLY. No interior (partitions/stairs/volumes), no
    # gameplay (rooms/markers/objectives/loot/zones), no nav. The build runs
    # exterior-only passes and emits no tactical data; the gameplay validators
    # are skipped (a shell legitimately has no objective). Pair with modular=True
    # so the walls are art-pass-ready swap slots -- the windows/brick come later
    # by resolving the slots, and the same shell is reused all over a block.
    facade: bool = False

    # --- art-pass pipeline (all optional; None = fall back to the matching
    # DC_* env var, so unset == byte-identical output). See README "Modular
    # walls" / "Theming the slots" and docs/ASSET_SWAP_CONTRACT.md. ---
    # decompose walls into named swap-slots (modular art-pass) instead of one
    # solid box per run. None -> DC_MODULAR env -> off. new_level.py writes
    # this true for new specs so fresh work is art-pass-ready by default.
    modular: Optional[bool] = None
    # module tile width (m) for tiling solid spans when modular. None ->
    # DC_MODULE env -> 2.0. <= 0 disables tiling (opening-decomposition only).
    module: Optional[float] = None
    # resolver theme/kit: slots resolve to <type>_<theme>_<style>...glb.
    # None -> DC_THEME env -> "greybox".
    theme: Optional[str] = None
    # optional model state (e.g. "damaged"); prefers a _<state> module variant.
    # None -> DC_STATE env -> none.
    state: Optional[str] = None
    # path to the module library (the zoo of swap modules), relative to the
    # spec. None -> DC_MODULE_LIB env -> resolver off (generate greybox boxes).
    module_library: Optional[str] = None

    # OPTIONAL anti-flatness pass (see --vertex-nuance). When true, the VISUAL
    # meshes get densified to ~grid edge length, hard edges beveled, and
    # procedural vertex colors baked (geometry-derived fake AO + height grime +
    # per-normal floor/wall/ceiling tint). COLLISION is never touched. Off by
    # default — the pure honest greybox stays the default output. Readability,
    # not beauty. Needs a vertex-color-reading material in Godot to display.
    vertex_nuance: bool = False

    # OPTIONAL building rarity (None | common | uncommon | rare | epic |
    # legendary). A single contract value, not a visual effect: when set, the
    # build stamps the tier and its one canonical colour onto gameplay.json's
    # top level and onto every breachable door/breach anchor, so a networked
    # door can "pop" the right colour when it opens. The reveal itself (light,
    # sound, HUD banner) is game code reading this value. None = no rarity
    # (current behaviour, no rarity fields emitted). See rarity.py / docs/RARITY.md.
    rarity: Optional[str] = None


