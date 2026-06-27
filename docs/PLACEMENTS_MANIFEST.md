# PLACEMENTS_MANIFEST.md

> **Status (as of 0.35.0): design spec — NOT yet implemented.** The shipped modular geometry lives in `docs/WALL_SEGMENTATION.md`; this document describes the intended direction (slot keys / manifest / themed-prefab swap) that builds on it.

`placements.json` emission spec — Deli Counter

**Status:** proposed · default-on emission · **zero change to the baked `.glb`**

---

## Purpose

An output-only manifest recording **every discrete piece the builder places**, with its
transform, the node name that `surface_roles` keys on, part type, and `building_id` — captured
*before* the pieces are joined into the baked shell.

It is the cheap keystone for a prefab art pass: it exposes data the builder already computes and
currently throws away at the join step. On its own it changes nothing about the shipped geometry.
Downstream, it's the prerequisite for an instanced bake target, a prefab-swap art pass, per-part
Patina/vertex-nuance targeting, and seam-aware composition in Lot.

## Principle alignment

- **WE MAKE MODELS NOT LEVELS** — the manifest is recipe metadata, not networked gameplay state.
- **INTEL never fails** — emission only. No new gate. (One optional non-blocking reconciliation
  WARN, below.)
- **Modular / optional** — the monolith path ignores it; consumers opt in.
- **Offline / deterministic** — stable order + rounded floats → byte-identical output for a given
  seed+spec, same guarantee as the baked shell.

---

## Where it emits (against the current builder)

`deli_counter.py` already builds discrete parametric pieces and then joins them. The per-piece
transform exists at creation time and is discarded at the join. The change is a collector: as each
piece is created, append a record; after the join **and** the existing `gameplay.json` emit, write
`placements.json`.

Emission sites = the sites the builder already spawns geometry at, which are also already the sites
that produce `surface_roles`, rarity stamps, and enterability openings — so the collector hangs off
the existing per-piece code path:

- exterior walls `N` / `S` / `E` / `W`
- partitions (`axis` `X`/`Y` at `pos`)
- floor / ground plane
- stair flights + landings
- ladders (rails + rungs as one logical piece)
- openings: door / window / breach (already stamped for rarity + enterability)
- *(future)* arbitrary-z platforms / mezzanines — roadmap **I-3**

---

## Record shape

```json
{
  "manifest_version": "1.0.0",
  "schema_version": "1.9.0",
  "level": "corner_deli",
  "building_id": "corner_deli",
  "space": "<MUST match gameplay.json markers — see Coordinate conventions>",
  "units": "meters",
  "placements": [
    {
      "id": "wall_n_0",
      "node": "WALL_N",
      "part_type": "wall_exterior",
      "facing": "N",
      "building": "corner_deli",
      "instancing": "mesh",
      "transform": {
        "position": [0.0, 1.5, -4.0],
        "rotation_euler_deg": [0.0, 0.0, 0.0],
        "scale": [8.0, 3.0, 0.2]
      },
      "dims": [8.0, 3.0, 0.2],
      "openings": ["door_0"]
    },
    {
      "id": "door_0",
      "node": "DOOR_SOCKET_0",
      "part_type": "opening_door",
      "building": "corner_deli",
      "instancing": "mesh",
      "transform": {
        "position": [0.0, 1.0, -4.0],
        "rotation_euler_deg": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0]
      }
    },
    {
      "id": "gas_pump_3",
      "node": "PROP_GAS_PUMP_3",
      "part_type": "prop_gas_pump",
      "building": "corner_deli",
      "instancing": "multimesh",
      "instance_group": "gas_pump",
      "transform": {
        "position": [4.0, 0.0, 2.5],
        "rotation_euler_deg": [0.0, 90.0, 0.0],
        "scale": [1.0, 1.0, 1.0]
      },
      "instance": {
        "color": [0.82, 0.80, 0.74, 1.0],
        "custom_data": [0.31, 0.0, 0.0, 0.0]
      }
    }
  ]
}
```

`node` is the **join key** — keep `surface_roles` (node→role) authoritative and reference it by
node name rather than copying the role onto every record (one source of truth). `dims` and
`openings` are optional but make fixed-size-prefab fit checks and "which opening is cut into which
wall" trivial downstream.

`instancing` tells the bake target how to emit this piece — `mesh`, `gridmap`, or `multimesh` (see
next section). `instance_group` names the shared library item that all instances of one kind point
at (every `gas_pump` record shares `"instance_group": "gas_pump"`), and the optional `instance`
block carries per-instance variation (`color`, `custom_data`) so identical instances can still look
different. Both default to absent — when unset, the piece is a plain `mesh` and the manifest is
byte-identical to the pre-instancing output.

---

## Instancing triage + per-instance uniqueness

The single-vs-modular question is not a global switch; it's **per-`part_type` triage**, because the
memory/draw-call win and the lighting cost both depend on *which* Godot construct emits the piece.
The bake target reads `instancing` and routes accordingly:

- **`mesh`** — a regular `MeshInstance3D` (or merged into the static shell). Use for the bespoke
  structural envelope: walls, partitions, floor, stairs. Mostly unique, screen-dominant, and the
  only path that can take **per-instance baked lightmaps**. Default.
- **`gridmap`** — a cell in a `GridMap` / `MeshLibrary`. Use for grid-aligned modular building
  blocks. Godot batches by mesh, so repeated cells share one mesh + material in VRAM and collapse
  draw calls. Keeps the node hierarchy flat.
- **`multimesh`** — an instance in a `MultiMeshInstance3D`, keyed by `instance_group`. Use for
  repeated props/fixtures (gas pumps, shelving, light fixtures, repeated trim). One mesh + one
  texture loaded; every other instance is just a transform. This is the construct that actually
  delivers the "place one pump, store coordinates for the rest" win — **N independent
  `MeshInstance3D` nodes do not** (they share the resource in memory but reintroduce hierarchy
  clutter and don't guarantee draw-call batching).

**The lighting fork is the cost of instancing.** `gridmap` and `multimesh` geometry cannot receive
per-instance baked lightmaps (LightmapGI needs unique UV2 per surface; instances share the mesh).
So a piece marked `gridmap`/`multimesh` commits its lighting to real-time / SDFGI / vertex-color —
which suits DC's vertex-nuance aesthetic, but is a deliberate choice, not a default. Pieces that
must take baked lightmaps stay `mesh`. (Full rationale + the grid/pivot rules live in
`docs/ART_PASS_MODULAR.md`.)

**Per-instance uniqueness without breaking instancing.** `MultiMesh` exposes a per-instance color
buffer and a per-instance custom-data buffer. The `instance` block feeds those directly, so the
Patina / vertex-nuance variation rides on instance color instead of duplicating the mesh — uniqueness
*and* the instancing win at once. Values must be **deterministic** (seed-driven, rounded) like
everything else in the manifest, or byte-identical output breaks.

---

## Coordinate conventions (the one thing to verify against your real emit)

- Units meters, `1u = 1m = 1` Godot unit — matches DC.
- **Emit in the exact same space `gameplay.json` markers/footprint already use.** Do not invent a
  new space. The transforms captured from bpy are Blender Z-up; if your marker emit converts to
  Godot Y-up (or the plugin reparents markers under the imported building so they inherit the
  glTF axis conversion), the manifest has to match that *same* choice, using the *same* conversion
  code — not a second copy. If manifest space and marker space disagree, instanced bake and marker
  placement desync. Confirm against `docs/GAMEPLAY_JSON_CONTRACT.md` / the actual marker emit
  before wiring this.
- Transform = `position [x,y,z]` + `rotation_euler_deg [rx,ry,rz]` (diff-friendly) + `scale`. The
  instanced-bake consumer reconstructs a Godot `Transform3D` from euler using a documented axis
  order — pin that order in this doc once chosen.
- Round all floats to fixed precision (e.g. `1e-4`) for byte-identical output.

## Determinism

Emit records in the builder's existing deterministic creation/join order. No hash sorting, no
reliance on dict iteration order. Round all floats. Same seed + spec → byte-identical
`placements.json`.

## `building_id` keying

Reuse the v0.33.0 `building_id` already on openings and top-level. Every record carries `building`
so Lot's multi-building compose and the rarity `is_revealed[building_id]` keying line up. Single
build → `building == level`.

## Relationship to existing outputs (no duplication)

- **surface_roles** — authoritative for role. Records reference it by `node`; don't restate role
  in both.
- **footprint** — stays top-level (whole-building approach space for Lot); manifest is per-piece.
- **rarity** — stays on openings/top-level as today; not duplicated onto non-opening pieces.

## Carrier: sidecar vs `gameplay.json` key

**Recommended: a `placements.json` sidecar.** Keeps the thesis line clean — `gameplay.json` =
anchors for networked state (runtime contract); `placements.json` = art/bake recipe (authoring
metadata). Folding a `"placements"` key into `gameplay.json` gives one file but mixes the runtime
contract with authoring data; only do that if you specifically want a single artifact.

## Schema + versioning

- New `placements.schema.json`; bump build schema `1.8.0 → 1.9.0` (additive — manifest emission
  only).
- Manifest carries its own `manifest_version` so consumers (instanced bake, Patina, Lot) can gate
  on it independently of the build schema.

---

## Reference implementation sketch

`placements.py` — bpy-free, sibling to `spec_types.py`:

```python
from dataclasses import dataclass, field, asdict

@dataclass
class Placement:
    id: str
    node: str
    part_type: str
    building: str
    position: tuple
    rotation_euler_deg: tuple = (0.0, 0.0, 0.0)
    scale: tuple = (1.0, 1.0, 1.0)
    facing: str | None = None
    dims: tuple | None = None
    openings: list = field(default_factory=list)
    instancing: str = "mesh"               # "mesh" | "gridmap" | "multimesh"
    instance_group: str | None = None      # shared library item key (multimesh/gridmap)
    instance: dict | None = None           # {"color": [...], "custom_data": [...]} per-instance

def _r(p, nd=4):                      # byte-identical rounding
    return tuple(round(v, nd) for v in p)

class PlacementCollector:
    def __init__(self):
        self._items = []
    def add(self, **kw):
        kw["position"]          = _r(kw["position"])
        kw["rotation_euler_deg"] = _r(kw.get("rotation_euler_deg", (0.0, 0.0, 0.0)))
        kw["scale"]             = _r(kw.get("scale", (1.0, 1.0, 1.0)))
        self._items.append(Placement(**kw))
    def manifest(self, level, building_id, space, schema_version):
        def prune(d):                     # drop None / empty so optional fields don't bloat diffs
            return {k: v for k, v in d.items() if v not in (None, [], {})}
        return {
            "manifest_version": "1.0.0",
            "schema_version": schema_version,
            "level": level,
            "building_id": building_id,
            "space": space,
            "units": "meters",
            "placements": [prune(asdict(p)) for p in self._items],
        }
```

`instancing` defaults to `"mesh"` and `prune` keeps it (it's a non-empty string), so a record's mode
is always explicit. `instance_group` / `instance` are pruned when absent, so a building with no
instanced pieces produces a manifest free of those keys.

`deli_counter.py` (builder, bpy) — at each existing placement site:

```python
collector.add(
    id=f"wall_{facing.lower()}_{i}",
    node=obj.name,                 # same name surface_roles keys on
    part_type="wall_exterior",
    building=building_id,
    facing=facing,
    position=to_gameplay_space(obj.location),                 # REUSE the marker conversion
    rotation_euler_deg=tuple(math.degrees(a) for a in obj.rotation_euler),
    scale=tuple(obj.scale),
    dims=(width, height, thickness),
)
# ... after join + gameplay.json emit:
write_json(out_dir / "placements.json",
           collector.manifest(level, building_id, SPACE, SCHEMA_VERSION))
```

`to_gameplay_space()` is **not new code** — it's whatever transform your existing marker emit
already applies. If markers stay in Blender space, this is identity; if they're converted, call the
same function. That guarantee is the whole correctness story.

## Optional intel check (`check.py`)

Reconcile placement-record count against the count of objects joined into the shell. Mismatch →
**WARN** ("manifest/geometry drift"), never fail. Keeps the manifest honest without becoming a gate.

## Walk-to-verify

Nothing to walk for the manifest itself — it's metadata. The walk happens when a consumer
(instanced bake) *uses* it: seam collision, double-walls, transform round-trip. Same bug class as
the stair-overlap and ladder-collision finds — budget one walk when you build the bake target, not
when you add this.

---

## Downstream this unlocks

- **`--bake instanced`** — map `part_type` → prefab, instance each record at its transform; default
  stays monolith. Library starts as the greybox parts, so it works with zero art on day one.
- **Prefab art-pass swap** — replace library contents; every building reskins for free.
- **Patina / vertex-nuance** — per-part targeting instead of whole-mesh.
- **Lot** — piece-level approach + seam awareness across composed buildings.
