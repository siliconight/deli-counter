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
  "building_id": "corner_deli_heist_01",
  "rarity": "legendary",
  "rarity_color": { "tier": "legendary", "rank": 4, "color_name": "gold",
                    "hex": "#FFD700", "rgb": [1.0, 0.8431, 0.0] },
  "markers": [ ... ],
  "rooms": [ ... ],
  "vertical_links": [ ... ],
  "openings": [ ... ],
  "interactives": [ ... ],
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

**`building_id`** — stable id the server keys `is_revealed` (and any per-run
rarity roll) on. For a single Deli Counter build it equals `level`; every opening
and door-socket anchor carries the same value (as `building`), so any entry point
resolves to this one building. In a Lot compound each building keeps its own id.

**`rarity`** / **`rarity_color`** — OPTIONAL building rarity. `rarity` is the
tier string (`common` / `uncommon` / `rare` / `very_rare` / `legendary`) or
`null` when the spec declares none. `rarity_color` is the resolved colour record
for that tier — `{ "tier", "rank", "color_name", "hex", "rgb": [r,g,b] }`, with
`rgb` in Godot's 0..1 range — or `null`. **This is the single source of truth for
the building's rarity** (tier strings match the proposal's server enum:
`COMMON`/`UNCOMMON`/`RARE`/`VERY_RARE`/`LEGENDARY`). It is a contract value, not a
baked effect: the reveal (light/sound/HUD when an entry is registered) is game
code that reads this. **Every** opening below carries the same colour so any entry
the game registers pops it. The five tiers and their canonical colours live in
`rarity.py`; see `docs/RARITY.md` for the wiring, the multi-entry model, and the
baked-vs-server-rolled distinction. Buildings with no declared rarity emit `null`
for both — treat that as "no rarity."

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
"pos", "width", "height" }`. Each opening also carries a `"building"` id. When the
building has a rarity, **every** opening additionally carries `"rarity"` and
`"rarity_color"` matching the top-level values — because the proposal treats a
door, window, or wall breach as a valid entry attempt, so any of them must
resolve to the building's rarity. The game decides which openings count as entry
points (it has `kind`, `breach_class`, `vaultable`, `reinforceable`); the kit just
guarantees each one knows its building and rarity.

**`interactives`** — fixtures whose state all players must agree on (doors,
breachable walls, breakable windows), one per interactive opening. Each is a
replicable **state machine**: `{ "id", "kind", "slot_ref", "transform",
"states": [...], "default", "transitions": [{event,from,to}], "reversible"?,
"source", "building" }`. `id` is a **stable, position-derived** handle (not an
array index — see `docs/INTERACTIVES.md`) that matches the `interactive.id` on
the same slot in `slots.json`. This is the **entire networked surface**: it
describes STATE, never synchronization, so it maps onto any netcode (server
snapshot / event-RPC / lockstep / rollback). The game spawns one replicated node
per `id` and drives which art variant renders; `reversible` is advisory. Doors
and breach openings are interactive by inference; a window only when authored
`breakable`. Empty when the building has no interactive openings. See
`docs/INTERACTIVES.md` for the full contract.

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

## stair_systems (kit 0.65+; gameplay/network semantics 0.67+)

One entry per stair, derived by `stairwell.py` (see
docs/stairwell_placement_spec.md, section 13). This is the egress contract a
mission layer (Dispatch) must respect when locking doors or placing blockers:

```json
{
  "id": "main_stack", "stack_id": null, "role": "primary_egress",
  "shape": "switchback", "enclosure": "protected",
  "floors_served": [-1, 0, 1],
  "footprint_polygon": [[-16.4, 6.25], ...],
  "clear_width_m": 1.4,
  "approach": [ { "floor": 0, "room": "stairwell", "room_role": "connector" } ],
  "discharge": { "floor": 0, "type": "direct_exterior", "room": "stairwell",
                 "via": [], "destination": "stairwell", "route_hops": 0 },
  "door_nodes": [ { "floor": 0, "kind": "door", "wall": "int_0_3",
                    "pos": 0.2, "interactive": "lvl:if:ab12cd34",
                    "default_state": "closed", "connects_from": "corridor",
                    "discharge_door": false } ],
  "egress": { "counts_as_exit": true, "independence_group": "route_stairwell",
              "paired_with": "stair_b" },
  "gameplay": { "network_authority": "server", "replicate_door_state": true,
                "allow_random_lock": false,
                "egress_side_always_openable": true,
                "fire_door": true, "self_closing": true,
                "ai_route_cost_multiplier": 1.15,
                "congestion": { "clear_width_m": 1.4,
                                "max_agents_abreast": 2,
                                "two_way_passable": true } }
}
```

Rules of the road for consumers:

- `door_nodes[].interactive` is the SAME stable id as the `interactives`
  array entry -- one replicated node covers both contracts.
- `allow_random_lock: false` means mission randomization may NOT lock any of
  this stair's doors. To lock one anyway, the scenario must be authored:
  `Stairwell.meta.gameplay` overlays these defaults, and the validator only
  tolerates a locked egress door when another egress stair serves the floor.
- `independence_group` differs between stairs whose grade routes do not share
  a destination; a mission blocker that severs one group must leave another
  group's routes untouched.
- `congestion` is AI intel (route cost, agents abreast), advisory like
  `reversible` on interactives -- never an instruction to the netcode.
