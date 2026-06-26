# gameplay.json — the canonical companion contract

Every build emits `<name>.gameplay.json` next to the `<name>.glb`. **This file is
the formal contract** between Deli Counter and anything downstream — the Godot
importer, the Patina styling tool, your game code. The `.glb` carries geometry,
collision, and marker *nodes*; `gameplay.json` carries the *meaning* — what each
node is, where gameplay attaches, and how surfaces should be treated — so
consumers never have to parse node names or infer intent from geometry.

If a tool needs to know "what is this mesh" or "where does the objective go," the
answer is here, authoritatively. Do not infer it from geometry when this file
states it.

## Top-level shape

```json
{
  "level": "corner_deli_heist_01",
  "mode": "heist",
  "rarity": "legendary",
  "rarity_color": { "tier": "legendary", "rank": 4, "color_name": "yellow",
                    "hex": "#FFD700", "rgb": [1.0, 0.8431, 0.0] },
  "markers": [ ... ],
  "rooms": [ ... ],
  "vertical_links": [ ... ],
  "openings": [ ... ],
  "objectives": [ ... ],
  "loot": [ ... ],
  "zones": [ ... ],
  "materials": [ ... ],
  "surfaces": [ ... ],
  "surface_roles": { ... }
}
```

## Fields

**`level`** / **`mode`** — the spec name and one of `assault` / `heist` /
`survival`.

**`rarity`** / **`rarity_color`** — OPTIONAL building rarity. `rarity` is the
tier string (`common` / `uncommon` / `rare` / `epic` / `legendary`) or `null`
when the spec declares none. `rarity_color` is the resolved colour record for
that tier — `{ "tier", "rank", "color_name", "hex", "rgb": [r,g,b] }`, with
`rgb` in Godot's 0..1 range — or `null`. **This is the single source of truth
for the building's rarity.** It is a contract value, not a baked effect: the
reveal (light burst, sound cue, HUD banner when a networked door opens) is game
code that reads this. Every *breachable* opening below carries the same colour
so a door can pop it locally. The five tiers and their canonical colours live in
`rarity.py`; see `docs/RARITY.md` for the wiring. Older builds (and buildings
with no declared rarity) emit `null` for both — treat that as "no rarity."

**`markers`** — gameplay anchors. Each: `{ "name", "type", "x", "y", "z",
"room"? , "rot_z"? }`. Types include spawns (`attacker_spawn`,
`defender_spawn`, `survivor_spawn`, `horde_spawn`), `objective`, `loot`,
`extraction`, `rescue`, `cover_low`, `cover_high`, `camera_socket`,
`patrol_point`, and vertical-link anchors (e.g. `LADDER_*`). **These correspond
to Empty nodes in the `.glb`** — but downstream tools MUST treat this file as the
source of truth for marker placement, because a styling/re-export pass may not
preserve the Empty nodes. (See "Marker preservation" below.)

**`rooms`** — `{ "id", "story", "bounds": [x0,y0,x1,y1], "role", "combat_range" }`.

**`vertical_links`** — `{ "kind", "role", ... }` describing stairs / ladders /
ramps / floor-holes / hatches connecting stories.

**`openings`** — tagged doorways/windows/breaches: `{ "wall", "story", "kind",
"pos", "width", "height" }`. When the building has a rarity, each *breachable*
opening (`door` / `garage` / `breach` — the entries a squad reveals the building
through; windows are excluded) also carries `"rarity"` and `"rarity_color"`,
matching the top-level values, so a networked door instanced at that opening pops
the right colour without looking up the building root.

**`objectives`** / **`loot`** / **`zones`** — mode-specific gameplay data
(objective rooms, loot spawns with value, extraction/secure/drop zones).

**`materials`** / **`surfaces`** — the OPTIONAL acoustic bridge (for gool or any
audio engine). `materials` is the palette; `surfaces` maps collision-node name →
acoustic material. Empty when the spec defines no materials or was built
`--no-audio`. Ignore if your game has no acoustic engine.

**`surface_roles`** — **authoritative** node-name → surface role for VISUAL
meshes. One of: `floor`, `ceiling`, `wall`, `stair`, `ramp`, `ladder`, `prop`.
This exists so styling/texturing tools (Patina) and the vertex-nuance pass apply
the right treatment per surface **without guessing from geometry** — inference
from normals/coordinates is error-prone across Blender/glTF/world-axis
conventions (it misclassifies shelves as ceilings, slabs as walls, etc.). The
builder knows what it placed; this map records that knowledge.

```json
"surface_roles": {
  "slab_0": "floor",
  "slab_2": "ceiling",
  "ext_0_N": "wall",
  "stair0_0_3": "stair",
  "ladder0_rail_0_-1": "ladder"
}
```

Consumers: look up a node's role here first; only fall back to geometric
inference for a node absent from the map.

## Marker preservation (contract requirement)

A tool that re-emits the `.glb` (e.g. a styling pass) **must preserve the marker
Empty nodes**, OR it must document that it doesn't and that consumers should read
marker placement from this file. Either way, **`gameplay.json` remains valid and
authoritative for marker placement regardless of what happens to the `.glb`'s
Empty nodes.** This is the fallback that makes the pipeline robust: if markers are
ever dropped from the geometry, the game still has their positions here.

(Recommended: an integration test on any re-emitting tool that asserts the
marker set in its output `.glb` matches this file — or, if it intentionally drops
them, that it says so and the game reads from here.)

## Stability

`surface_roles` was added in kit 0.30.x. Consumers should treat unknown future
keys as optional and ignore them, and treat a missing `surface_roles` (older
builds) as "infer roles yourself." Additive changes only; existing fields won't
change shape without a `SCHEMA_VERSION` bump.
