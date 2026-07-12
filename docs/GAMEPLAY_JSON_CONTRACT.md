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

### stair_systems Phase-5 fields (kit 0.68+)

- `facing` -- cardinal rotation of the whole stair about its anchor ("N" =
  the pre-0.68 ascent-along-+Y convention).
- `exterior` -- an exterior stair tower (spec s8.4): `approach` is empty,
  `door_nodes` are facade doors per served floor, and `discharge` is
  `{"type": "exterior_tower", "destination": "site"}`.
- `channels` -- 2 for scissor stairs (two independent opposite-direction
  flights sharing one shaft; `congestion.clear_width_m` is per channel), else 1.
- `roof_access` -- the stair tops out past the last occupied story; the slab
  hole is cut when `cut_slabs` is on, the bulkhead/hatch is authored art.
- `transfer_floor` -- present on declared stack members that shift footprint
  at that story; the review verified (or could not verify) the walk between
  them there.

## ladders (kit 0.69+)

One entry per ladder, derived by `ladder.py` (see
docs/deli_counter_ladder_placement_spec.md s14). A ladder is a specialized
connection between two usable surfaces, and -- unlike a stair -- is NEVER
ordinary building egress:

```json
{
  "id": "ladder_roof_rear_01", "role": "roof_access",
  "ladder_type": "fixed_vertical", "placement_mode": "exterior_wall",
  "lower_surface": "service_yard", "upper_surface": "roof",
  "lower_anchor": [12.4, 0.0, 0.0], "upper_anchor": [12.4, 0.0, 5.6],
  "climb_height_m": 5.6, "direction": "bidirectional",
  "access_class": "staff_restricted",
  "egress_classification": "not_egress",
  "counts_as_primary_egress": false,
  "counts_as_secondary_escape": false,
  "counts_as_public_circulation": false,
  "transition": { "type": "roof_hatch_exit" },
  "geometry": { "clear_width_m": 0.5, "rung_spacing_m": 0.3, "climb_rect": [...] },
  "fall_protection": { "required": false, "type": "none" },
  "access_control": { "type": "locked_hatch" },
  "route_nodes": { "lower_approach": [...], "lower_mount": [...],
                   "climb_start": [...], "climb_end": [...],
                   "upper_dismount": [...], "upper_route": [...] },
  "gameplay": { "player_traversable": true, "ai_traversable": true,
                "server_authoritative_state": true, "interaction_required": true,
                "mount_anchor_id": "ladder_roof_rear_01_mount",
                "dismount_anchor_id": "ladder_roof_rear_01_dismount",
                "occupancy_limit": 1 }
}
```

Rules of the road for consumers:

- `egress_classification` is `not_egress` for every role except the two escape
  roles (legacy_secondary_escape / fire_escape_termination) that explicitly set
  `counts_as_secondary_escape`. Never route ordinary occupant egress over a
  ladder, and never add one to the required-exit count.
- `route_nodes` are the six traversal nodes (spec s13.1); the post-import wires
  a nav-link between `lower_mount` and `upper_dismount`, keyed to the
  `<ID>_MOUNT` / `<ID>_DISMOUNT` empties in the GLB.
- `interaction_required` is true whenever `access_control` is present (a locked
  hatch / gate must be operated before traversal).
- `gameplay.meta` (via `Ladder.meta`) overlays these defaults for authored
  cases, same pattern as `Stairwell.meta`.

### ladders Phase-3 notes (kit 0.71+)

- An interior roof-hatch ladder (placement_mode interior/shaft, upper_surface
  roof, transition roof_hatch_exit) is validated against spec s8: it must
  originate in a service room (mechanical/utility/janitor/back-of-house), its
  dismount disc must be clear of rooftop equipment, and a parapeted roof edge
  must not collide with the hatch cover swing. A roof ladder rising from an
  objective/public room is a ROOF_HATCH_BLOCKED error -- if the intent is a
  gameplay rooftop route, classify it special_gameplay_route, not roof_access.
- ladder_place.py --mode hatch proposes these: it picks a top-floor service
  room and rises from that room's story to the roof.

### ladders Phase-6 runtime blocks (kit 0.72+)

Each ladder now carries the Godot 4.7 runtime contract (spec s17). The ladder
object is DATA; the gameplay/network layer is authoritative over it.

- `traversal_component` (s17.1): the reusable LadderTraversal component ref --
  mount/dismount triggers (the <ID>_MOUNT / <ID>_DISMOUNT empties), climb axis,
  direction, animation profile, occupancy/replication state, interaction
  permissions.
- `nav_link` (s17.2): an explicit off-mesh nav-link (NOT a baked walkable
  slope) with start/end, bidirectional (derived from direction), a per-type AI
  cost, agent_types, required_capability "climb", access_state, reservation.
  This is what AI pathfinding consumes.
- `authority` (s17.3): the server/client ownership split. server_owned =
  enabled/locked/deployed/obstructed/ai_reservation/objective_gating/
  player_transition_acceptance; client_owned = animation/camera/sound/effects/
  prediction. Present on every ladder so netcode reads it rather than assuming.
- `ai` (s17.4): can_use, one_at_a_time, may_attack_while_climbing,
  should_wait_for_agent, may_follow_to_roof, recover_if_blocked.
- `combat` (s17.5): weapons_allowed_while_climbing, can_be_interrupted,
  can_fall (tracks fall_protection), can_slide_down, can_be_destroyed,
  can_be_blocked, occupancy_limit -- data-driven, not hardcoded per mission.

Authored overrides: `Ladder.meta['combat']` overlays the combat block and
`Ladder.meta['gameplay']['occupancy_limit']` propagates to gameplay, combat,
and ai consistently.

## platforms (kit 0.73+)

Elevated walkable decks standing free of the story grid -- catwalks, equipment
platforms, mezzanine landings, rest platforms for offset ladder runs (ladder
spec s5.6/s6.4/s11.6). Emitted into gameplay.json so ladders and the game read
them as surfaces:

```json
{ "id": "main_catwalk", "x": 0.0, "y": 0.0, "z": 4.0,
  "size_x": 24.0, "size_y": 1.6, "role": "catwalk",
  "destination": "overhead_crane_rail", "guard_edges": ["N", "E", "W"] }
```

- `z` is an absolute deck-top height (not story-indexed), so a platform can sit
  at a mezzanine level between stories.
- A ladder addresses a platform as a surface by id in lower_surface /
  upper_surface; the climb endpoint pins to the platform's deck height.
- `guard_edges` are railed; leave the ladder-side edge OUT as the access gap
  (a fully-guarded platform a ladder enters warns LADDER_UNGUARDED_OPENING).
- `destination` names the real thing the platform serves; an equipment platform
  with no destination (and not a catwalk/mezzanine/rest deck) warns
  LADDER_TO_NOWHERE (s5.6: connect every upper platform to a real destination).
- ladder_place.py --mode equipment proposes floor->platform ladders from the
  platform graph, anchored off each platform's open edge, with an offset
  fall-protection profile for tall climbs.

## fire_escapes (kit 0.74+)

Legacy exterior fire-escape SYSTEMS (ladder spec s9), generated whole per s9.1
(the platform system before the ladder). Emitted into gameplay.json:

```json
{ "id": "rear_fire_escape", "wall": "N", "served_stories": [1, 2],
  "termination": "drop_ladder", "access": "window" }
```

- A stack of floor-level balcony platforms on one facade (`wall`), one per
  `served_stories` floor, connected by stair segments, guarded on the three
  open sides (the facade side is the access opening).
- `access` (window/door/corridor_end) is the opening each served floor
  connects through (s9.2); the review warns if the facade lacks it.
- `termination` (s9.3) is how the lowest platform reaches grade: stair_to_grade
  / counterbalanced_stair / deployable_stair (reach grade on their own), or
  drop_ladder (the legacy exception -- needs a linked Ladder with
  fire_escape_id and direction deploy_then_bidirectional).
- A fire-escape / drop Ladder references the system by fire_escape_id and by
  naming it as a surface (upper_surface); the climb endpoint pins to the lowest
  balcony. FIRE_ESCAPE_LADDER_ORPHANED gates a ladder whose fire_escape_id
  names no system; DROP_LADDER_NO_DEPLOYMENT_CLEARANCE gates a drop ladder
  deploying onto a dumpster/fence/vehicle/areaway (s9.4).
- ladder_place.py --mode fire_escape proposes the whole system (rear facade,
  served upper floors, termination by profile) for a legacy building profile.
