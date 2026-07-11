# Deli Counter Stair and Stairwell Placement Specification

**Status:** Proposed generation and validation specification  
**Target:** Deli Counter building shell generation  
**Engine target:** Godot 4.7  
**Primary outputs:** `shell.glb` and `shell.gameplay.json`

## 1. Purpose

This document defines how Deli Counter should generate staircases and stairwells that feel like real parts of a building rather than stairs inserted wherever floor space happens to be available.

The central rule is:

> A stairwell is a continuous vertical circulation and egress system. It must be planned before rooms are finalized, connect to believable circulation on every served floor, and terminate in a safe, legible route out of the building.

Deli Counter should never treat a stair as an isolated mesh. It should treat the stair, enclosure, landings, doors, corridor connections, vertical stack, and ground-floor discharge as one connected system.

This specification is intended to create architecturally believable game spaces. It is not a substitute for review by an architect, fire protection engineer, accessibility specialist, or local code official.

---

## 2. What Deli Counter Must Understand

Deli Counter should distinguish between the following elements.

### 2.1 Stair

The physical runs, treads, risers, handrails, guards, and landings used to move between elevations.

### 2.2 Stairwell

The vertical volume containing the stair. A stairwell normally occupies a consistent footprint through multiple floors.

### 2.3 Stair enclosure

Walls and doors that separate an egress stair from the surrounding building. An enclosed stair should behave as a protected circulation volume rather than as an ordinary room.

### 2.4 Stair entrance

The floor-level door, opening, vestibule, or lobby through which a person enters the stair system.

### 2.5 Stair discharge

The route from the bottom of an egress stair to the exterior or another safe destination. A stair is incomplete until this route exists.

### 2.6 Convenience stair

An open stair used for normal movement, presentation, or visual connection. It may complement an egress stair, but should not automatically replace protected exit stairs.

### 2.7 Service stair

A stair associated with loading, kitchens, staff areas, maintenance, storage, or back-of-house circulation. It still needs a believable route and cannot simply end inside a locked utility room.

---

## 3. Foundational Generation Rules

These rules should be treated as invariants unless a building archetype explicitly overrides them.

### Rule 1: Place vertical circulation before subdividing the floor plate

The generator should reserve stair cores after the exterior shell, structural grid, entrances, and major circulation spine are established, but before all rooms are packed.

Recommended order:

1. Generate building footprint and floor elevations.
2. Identify public entrances, service entrances, and possible exterior discharge faces.
3. Establish structural grid and major circulation axes.
4. Determine required stair roles and approximate count.
5. Place vertical stair stacks.
6. Connect stairs to primary corridors or circulation spaces.
7. Subdivide remaining space into rooms.
8. Validate travel paths, door clearances, discharge, and route independence.

### Rule 2: Stack stairwells vertically

A multi-floor stairwell should retain the same or nearly the same XY footprint on every floor it serves.

Allowed variation:

- Minor wall offsets caused by structure.
- A transfer landing or short offset at a mechanical floor.
- A ground-floor discharge passage that turns toward an exterior wall.
- A stair that begins or ends at a designated level.

Disallowed default behavior:

- The stair teleports laterally between floors.
- Each floor receives an independently positioned staircase.
- Upper-floor stairs end on a ceiling or roof slab without a valid termination.
- The stair footprint overlaps rooms differently on every floor.

### Rule 3: Every occupied floor must have a valid approach to the stair

A stair entrance should normally connect from one of the following:

- A primary corridor.
- An elevator or circulation lobby.
- A public common area.
- A protected vestibule.
- A service corridor for a designated service stair.
- A dwelling interior for a private residential stair.

A required stair should not normally be accessed only through:

- A bathroom.
- A storage room.
- A closet.
- A mechanical room.
- A private office.
- A kitchen work line.
- A bedroom belonging to another unit.
- A locked tenant space that blocks other occupants.
- An objective room that may become inaccessible during gameplay.

### Rule 4: Every stair entrance needs a landing

A floor or landing must exist at the top and bottom of each stair run. Doors may not open directly onto a tread or into the path of a descending player.

For Deli Counter's default plausible commercial profile:

- Clear stair width: `1.20 m` preferred.
- Minimum generated landing width: at least the stair width.
- Minimum generated landing depth: `max(stair_width, 1.20 m)`.
- Typical egress door clear width: `0.90 m`.
- Door threshold and landing should be at the same elevation.
- Door swing must not consume the full usable landing.
- Maintain a clear standing and turning zone on the floor side of the door.

These are game-generation defaults, not universal legal dimensions.

### Rule 5: The bottom of the stair must lead somewhere safe and legible

An egress stair must resolve to one of the following:

1. A door directly to the exterior.
2. A short, protected exit passage leading to an exterior door.
3. A clearly legible lobby discharge condition with an unobstructed route to a visible exterior door.

The discharge route must not require occupants to:

- Re-enter the main hazard area.
- Pass through a locked room.
- Move through storage or back-of-house clutter.
- Cross an active loading bay without a protected pedestrian path.
- Climb another stair before reaching the exterior.
- Guess which of several unmarked doors reaches safety.

### Rule 6: Redundant stairs must be meaningfully separated

When a generated building has two egress stairs, Deli Counter should not place them side by side, behind the same doorway, or inside the same vulnerable room.

For code-informed plausibility, use the following candidate test:

```text
required_separation = floor_plate_diagonal * separation_factor
```

Default factors:

- Conservative non-sprinklered approximation: `0.50`.
- Sprinklered approximation: `0.33`.
- Game-friendly minimum for compact shells: never less than `8.0 m`, unless the archetype is explicitly small and single-stair eligible.

This is a placement heuristic. Final legal separation depends on occupancy, construction, sprinkler protection, jurisdiction, and adopted code edition.

### Rule 7: Redundant routes must remain independently usable

Two stair doors do not create two meaningful exits if both routes depend on the same choke point.

Reject layouts where:

- Both stairs are reached only through the same small room.
- Both stair approaches share the same dead-end corridor for most of their length.
- One locked door disables access to both stairs.
- Both stairs discharge into the same enclosed back room.
- A single gameplay breach, collapse, fire volume, or scripted lock blocks both routes.

### Rule 8: A stair continuing below the discharge floor must clearly interrupt descent

If the same shaft continues into a basement, the player should not naturally continue downward when trying to exit at grade.

Generate one or more of the following:

- A wall or barrier at the discharge landing.
- A change in orientation.
- A clearly separate basement door.
- Strong exit signage and lighting toward the exterior.
- A landing configuration that makes the exterior route visually dominant.

### Rule 9: Elevators do not replace stairs

Elevators may be grouped with stairs in a building core, but the generator should not count an elevator as an ordinary required egress route.

### Rule 10: Stair volume is reserved space, not leftover space

Once a stair stack has been accepted, room packing may not invade:

- Stair runs.
- Landings.
- Required door clearances.
- Headroom volumes.
- Handrail and guard clearances.
- Stair enclosure walls.
- Discharge passages.
- Navigation and AI traversal corridors.

---

## 4. Where Stairs Actually Tend to Exist

Building codes often define performance requirements rather than prescribing one universal location. Real stair placement is shaped by circulation, structural efficiency, floor-plate geometry, occupancy, fire separation, and the need to reach the exterior.

Deli Counter should use weighted archetype patterns rather than one universal placement rule.

## 4.1 Small detached commercial building

Examples:

- Small retail building.
- Restaurant.
- Neighborhood office.
- Standalone clinic.
- Two-story mixed-use storefront.

Common placement patterns:

- Near the rear or side wall, especially for a service or upper-floor access stair.
- Immediately behind the public sales floor, connected to a back corridor.
- Along a party wall or property-line wall in narrow urban buildings.
- Near the main entrance when the upper floor has public access.
- One public stair plus a remote rear egress stair in larger two-story buildings.

Preferred Deli Counter logic:

- Favor a perimeter-adjacent stair because it simplifies exterior discharge.
- Connect the stair to a rear or side circulation path.
- Do not place the only stair in the center of the retail floor unless it is intentionally a public convenience stair and a valid egress strategy also exists.

## 4.2 Narrow urban storefront or row building

Examples:

- Main-street shop with apartments above.
- Narrow bar or restaurant.
- Mixed-use masonry row building.

Common placement patterns:

- Along one side wall.
- Behind the storefront and beside a narrow entrance passage.
- At the rear, beside a service yard or alley.
- In a compact central bay when both front and rear spaces must be preserved.

Preferred Deli Counter logic:

- Align the stair with a long party wall.
- Preserve a direct path from upper floors to either the street or rear yard.
- For mixed use, separate the residential stair entrance from the ground-floor commercial tenant where plausible.

## 4.3 Office building

Common placement patterns:

- One stair integrated into a central core with elevators, restrooms, shafts, and service rooms.
- A second stair at the remote side or end of the floor plate.
- Two stairs on opposite sides of a central elevator core.
- Stairs at opposite corridor ends in a long rectangular floor plate.

Preferred Deli Counter logic:

- Establish a primary corridor loop or spine.
- Connect stairs to the primary circulation network.
- Allow one stair to be core-adjacent.
- Push the second stair toward a remote perimeter, wing end, or opposite core edge.
- Avoid placing both stair doors inside the same elevator lobby unless the separation and route-independence rules remain satisfied.

## 4.4 Hotel, dormitory, or apartment building

Common placement patterns:

- Stairs at opposite ends of a double-loaded corridor.
- Stairs spaced along a long corridor.
- One stair near a central lobby and one at a remote end.
- Compact stairs embedded in a central core for smaller buildings.

Preferred Deli Counter logic:

- Build the resident corridor first.
- Place stair doors directly on or immediately adjacent to that corridor.
- Favor corridor-end stairs for long bars and L-shaped wings.
- Do not route common egress through an individual dwelling or guest room.
- Stack the stair without shifting between floors.

## 4.5 School or institutional building

Common placement patterns:

- At ends of major corridors.
- At intersections between wings.
- Near exterior walls for direct discharge.
- Additional stairs serving assembly spaces, gyms, auditoriums, or multi-level classroom wings.

Preferred Deli Counter logic:

- Treat each wing as a circulation branch.
- Place stairs at wing ends and major junctions.
- Ensure a player can leave a wing without returning to the center of the building.
- Avoid creating a single central stair that all wings depend on.

## 4.6 Warehouse or industrial building

Common placement patterns:

- At perimeter walls or corners.
- Adjacent to office pods inside the warehouse.
- Directly serving mezzanines.
- In exterior stair towers.
- Near service and production circulation, while remaining clear of equipment hazards.

Preferred Deli Counter logic:

- Favor direct exterior discharge.
- Keep stair approaches clear of machinery, pallet storage, loading positions, and vehicle lanes.
- Use industrial or service stairs only where the archetype allows them.
- Do not use ladders as ordinary floor-to-floor occupant circulation.

## 4.7 Parking structure

Common placement patterns:

- At perimeter corners.
- In stair and elevator towers.
- At pedestrian arrival points.
- In open or naturally ventilated enclosures where allowed by the building type.

Preferred Deli Counter logic:

- Place stairs where pedestrians can reach them without walking through the center of vehicle ramps.
- Connect the bottom landing to a sidewalk, lobby, or protected pedestrian route.
- Give stair towers strong vertical visibility from the garage floor.

## 4.8 House or townhouse

Common placement patterns:

- Near the main entry.
- In a central hall.
- Along a side wall.
- Between front and rear rooms.
- Against a shared party wall in townhouses.

Preferred Deli Counter logic:

- Private residential stairs may be open and integrated with living space.
- Do not apply full commercial stair enclosure logic to every house.
- Maintain believable circulation at top and bottom.
- Avoid stairs that rise into the middle of a bedroom or terminate against furniture.

---

## 5. Stair Roles Deli Counter Should Generate

Each stair must receive an explicit role.

| Role | Purpose | Typical enclosure | Typical location |
|---|---|---|---|
| `primary_egress` | Main protected escape route | Enclosed | Core, corridor end, perimeter |
| `secondary_egress` | Remote alternate route | Enclosed | Opposite wing, remote perimeter |
| `public_convenience` | Normal public movement and visual connection | Open or partially enclosed | Lobby, atrium, sales floor |
| `service` | Staff, loading, maintenance, kitchen, back-of-house | Enclosed or utilitarian | Rear, side wall, service core |
| `private_residential` | Movement inside one dwelling | Usually open | Entry hall, central hall, side wall |
| `industrial_access` | Mezzanine or equipment access | Open industrial stair | Warehouse perimeter or work zone |
| `exterior_egress` | Outdoor protected route | Exterior | Side or rear facade, courtyard |

A `public_convenience` stair should not automatically satisfy the building's egress stair count.

---

## 6. Preferred Stair Shapes

## 6.1 Switchback or dogleg stair

Best default for commercial and institutional buildings.

Advantages:

- Compact rectangular footprint.
- Repeats cleanly through floors.
- Produces useful landings.
- Fits cores and corridor ends.
- Easy to enclose.

Suggested default footprint for a `1.20 m` stair:

```text
Approximate clear core interior: 3.0 m x 5.5 m
```

Actual size depends on floor-to-floor height, wall thickness, rail clearances, and landing configuration.

## 6.2 Straight-run stair

Use when:

- Floor-to-floor height is low.
- A long wall is available.
- The stair is architectural or industrial.
- A mezzanine is being served.

Avoid forcing a straight stair into an ordinary office core because the required horizontal run is often long.

## 6.3 L-shaped stair

Use when:

- Turning around a structural bay.
- Fitting into a corner.
- Connecting a lobby to an upper level.

## 6.4 Scissor stair

Do not generate by default.

Scissor stairs are compact and real, but they require more sophisticated enclosure, separation, wayfinding, and code interpretation. Add them only as an advanced authored archetype.

## 6.5 Spiral stair

Use only for:

- Decorative access.
- Private residential conditions.
- Restricted service access.
- Small mezzanines where explicitly allowed by the profile.

Do not use a spiral stair as Deli Counter's default public or egress stair.

## 6.6 Ladder

A ladder is not a staircase.

Use ladders for:

- Roof access.
- Maintenance platforms.
- Utility pits.
- Gameplay shortcuts.

Do not count a ladder as ordinary occupant egress.

---

## 7. Corridor and Stair Relationship

Federal circulation guidance treats stairs and elevators as building-core or common-space destinations connected by primary circulation. Deli Counter should reflect that relationship.

### 7.1 Valid relationships

```text
ROOMS -> PRIMARY CORRIDOR -> STAIR DOOR -> LANDING -> STAIR
```

```text
ROOMS -> CORRIDOR LOOP -> CORE LOBBY -> STAIR DOOR -> STAIR
```

```text
WAREHOUSE FLOOR -> MARKED PEDESTRIAN AISLE -> STAIR -> EXTERIOR
```

```text
APARTMENT -> COMMON CORRIDOR -> REMOTE STAIR A OR REMOTE STAIR B
```

### 7.2 Invalid relationships

```text
ROOMS -> STORAGE ROOM -> STAIR
```

```text
PUBLIC FLOOR -> KITCHEN LINE -> LOCKED STAFF DOOR -> STAIR
```

```text
CORRIDOR -> DOOR -> IMMEDIATE DOWNWARD TREAD
```

```text
UPPER FLOOR -> STAIR -> BASEMENT ONLY
```

```text
STAIR A + STAIR B -> SAME LOCKED VESTIBULE -> EXTERIOR
```

---

## 8. Ground-Floor Discharge Patterns

## 8.1 Direct exterior discharge

Preferred whenever the stair touches an exterior wall.

```text
UPPER FLOORS
     |
 [STAIR]
     |
[GROUND LANDING] -> [EXTERIOR DOOR] -> [SIDEWALK / YARD]
```

Generation requirements:

- Exterior door exists.
- Door is not blocked by props.
- Exterior landing exists.
- Exterior landing connects to traversable site space.
- The route does not discharge into a sealed courtyard.

## 8.2 Exit passage discharge

Use when the stair is internal.

```text
[STAIR] -> [PROTECTED PASSAGE] -> [VISIBLE EXTERIOR DOOR]
```

Generation requirements:

- Passage is reserved and cannot become a room.
- Passage width is never less than the stair approach width.
- No storage alcoves or objective blockers occupy the passage.
- The exterior door is visually legible from the stair termination or after one simple turn.

## 8.3 Lobby discharge

Use selectively for larger public or office buildings.

```text
[STAIR] -> [LOBBY EDGE] -> [CLEAR PATH] -> [MAIN EXTERIOR DOOR]
```

Generation requirements:

- The path is short, obvious, and unobstructed.
- The lobby cannot be a maze.
- Furniture placement preserves the route.
- Security gates do not block egress.
- The exterior exit is visually identifiable.

## 8.4 Exterior stair tower

```text
[FLOOR CORRIDOR] -> [DOOR] -> [EXTERIOR STAIR TOWER] -> [GRADE]
```

Use for industrial, parking, older urban, or explicitly authored profiles.

---

## 9. Door and Landing Logic

Deli Counter must test both the closed and fully open door state.

### 9.1 Door placement requirements

- The door connects to a landing, never directly to a tread.
- The landing remains traversable when the door is open.
- The door leaf does not intersect the stair run, railing, wall, or another door.
- The door does not trap a player between the door leaf and guardrail.
- The floor-side approach has enough room for AI and player navigation.
- Egress doors are openable from the egress side in gameplay logic unless the mission intentionally represents a noncompliant or hostile condition.

### 9.2 Preferred swing behavior

For generated egress stairs:

- Prefer doors swinging into the stair only when sufficient landing area remains and the profile supports it.
- Prefer discharge doors swinging toward the exterior or direction of egress.
- Never allow the open door to erase the only path across a landing.

### 9.3 Gameplay door states

Each stair door should define:

- `default_state`
- `lockable`
- `egress_side_always_openable`
- `breachable`
- `fire_door`
- `self_closing`
- `network_authority`
- `nav_link_state`

Required egress routes should not be randomly locked by mission generation unless another valid route remains and the authored scenario explicitly permits it.

---

## 10. Geometry Defaults for Plausible Commercial Stairs

These values are recommended generation defaults for visual and gameplay plausibility.

```yaml
stair_profile: commercial_default
clear_width_m: 1.20
riser_height_m: 0.17
tread_depth_m: 0.28
max_risers_per_flight: 12
landing_min_width_m: 1.20
landing_min_depth_m: 1.20
door_clear_width_m: 0.90
headroom_min_m: 2.10
handrail_height_m: 0.91
guard_height_m: 1.07
```

For a floor-to-floor height of approximately `3.2 m`, expect roughly 19 risers. A switchback stair would normally divide these into two flights with an intermediate landing.

Deli Counter should calculate the exact riser count so every riser in a flight is uniform.

```text
riser_count = round(floor_to_floor_height / target_riser_height)
actual_riser_height = floor_to_floor_height / riser_count
```

Reject the candidate if `actual_riser_height` falls outside the selected profile's acceptable range.

---

## 11. Candidate Placement Algorithm

## 11.1 Inputs

- Building footprint polygon.
- Number of floors.
- Floor-to-floor heights.
- Building archetype.
- Occupancy density estimate.
- Structural grid.
- Public entrances.
- Service entrances.
- Exterior faces available for discharge.
- Major rooms and protected rooms.
- Required number of independent vertical routes.
- Sprinkler profile or separation factor.

## 11.2 Candidate zones

Generate candidate stair zones from:

1. Exterior corners.
2. Ends of primary corridor axes.
3. Sides of central service or elevator cores.
4. Wing junctions.
5. Rear service zones.
6. Perimeter structural bays.
7. Party-wall bands in narrow urban buildings.

Do not start with random points sampled across the whole floor plate.

## 11.3 Candidate rejection tests

Reject a candidate before scoring if:

- It cannot stack through required floors.
- It overlaps a protected major room.
- It cannot fit runs, landings, walls, and door clearances.
- It has no valid corridor approach.
- It has no valid ground discharge solution.
- It creates unusable headroom.
- It intersects an elevator shaft or major utility shaft.
- It forces the stair entrance through a prohibited room type.
- It blocks the only circulation spine.
- It creates an exterior door below grade without an areaway or exterior route.

## 11.4 Candidate scoring

Example weighted score:

```text
score =
    + 30 * corridor_connection_quality
    + 25 * discharge_quality
    + 20 * vertical_stack_efficiency
    + 15 * separation_from_other_stairs
    + 10 * structural_grid_alignment
    + 10 * archetype_fit
    +  5 * exterior_visibility
    - 20 * usable_area_damage
    - 20 * corridor_dead_end_penalty
    - 30 * route_dependency_penalty
    - 40 * gameplay_chokepoint_penalty
```

Each term should be normalized from `0.0` to `1.0`, except penalties.

## 11.5 Pair selection for two-stair buildings

Do not simply choose the two highest individual candidates.

Choose the best pair based on:

- Individual quality.
- Separation distance.
- Independent corridor approaches.
- Independent discharge routes.
- Coverage of different wings or regions.
- Resistance to a single blocked zone.

```pseudo
best_pair = null
best_pair_score = -INF

for stair_a in candidates:
    for stair_b in candidates after stair_a:
        if not separation_valid(stair_a, stair_b):
            continue
        if not routes_independent(stair_a, stair_b):
            continue
        if not discharge_pair_valid(stair_a, stair_b):
            continue

        pair_score = stair_a.score + stair_b.score
        pair_score += coverage_bonus(stair_a, stair_b)
        pair_score += separation_bonus(stair_a, stair_b)
        pair_score -= shared_chokepoint_penalty(stair_a, stair_b)

        if pair_score > best_pair_score:
            best_pair = [stair_a, stair_b]
            best_pair_score = pair_score
```

---

## 12. Building Archetype Profiles

Example profile fields:

```yaml
id: office_midrise
minimum_floors: 3
maximum_floors: 12
stair_count_policy: occupancy_and_floorplate
preferred_stair_shapes:
  - switchback
primary_stair_candidates:
  - central_core_edge
  - corridor_end
secondary_stair_candidates:
  - remote_perimeter
  - opposite_corridor_end
convenience_stair_probability: 0.15
service_stair_probability: 0.20
allow_open_primary_stair: false
prefer_direct_exterior_discharge: true
separation_factor: 0.33
```

Recommended initial profiles:

- `residential_house`
- `urban_storefront_narrow`
- `restaurant_two_story`
- `office_lowrise`
- `office_midrise`
- `hotel_corridor`
- `apartment_corridor`
- `school_wings`
- `warehouse_mezzanine`
- `parking_structure`

---

## 13. Data Model

Each stair system should exist as a semantic object in `shell.gameplay.json`.

```json
{
  "stair_systems": [
    {
      "id": "stair_a",
      "stack_id": "vertical_core_a",
      "role": "primary_egress",
      "shape": "switchback",
      "enclosure": "protected",
      "floors_served": [0, 1, 2, 3],
      "footprint_polygon": [
        [4.0, 8.0],
        [7.2, 8.0],
        [7.2, 13.6],
        [4.0, 13.6]
      ],
      "clear_width_m": 1.2,
      "door_nodes": [
        {
          "floor": 0,
          "door_id": "door_stair_a_00",
          "connects_from": "corridor_ground_west",
          "landing_id": "landing_stair_a_00"
        },
        {
          "floor": 1,
          "door_id": "door_stair_a_01",
          "connects_from": "corridor_01_west",
          "landing_id": "landing_stair_a_01"
        }
      ],
      "discharge": {
        "type": "direct_exterior",
        "floor": 0,
        "exterior_door_id": "exit_west_01",
        "safe_destination_id": "site_sidewalk_west",
        "route_clear": true,
        "route_visible": true
      },
      "egress": {
        "counts_as_exit": true,
        "egress_side_always_openable": true,
        "independence_group": "west_route",
        "paired_with": "stair_b"
      },
      "gameplay": {
        "network_authority": "server",
        "replicate_door_state": true,
        "allow_random_lock": false,
        "ai_route_cost_multiplier": 1.15
      }
    }
  ]
}
```

---

## 14. Validation Rules

## 14.1 Hard errors

A shell must fail generation or baking when any of the following occurs:

- `STAIR_NOT_STACKED`
- `STAIR_INTERSECTS_ROOM`
- `STAIR_MISSING_TOP_LANDING`
- `STAIR_MISSING_BOTTOM_LANDING`
- `STAIR_DOOR_OPENS_ONTO_TREAD`
- `STAIR_DOOR_BLOCKS_LANDING`
- `STAIR_NO_CORRIDOR_CONNECTION`
- `STAIR_ACCESS_THROUGH_PROHIBITED_ROOM`
- `STAIR_NO_GROUND_DISCHARGE`
- `STAIR_DISCHARGE_BLOCKED`
- `STAIR_DISCHARGE_TO_SEALED_COURTYARD`
- `STAIR_HEADROOM_FAILURE`
- `STAIR_UNEVEN_RISERS`
- `STAIR_NAVMESH_DISCONNECTED`
- `REQUIRED_STAIRS_TOO_CLOSE`
- `REQUIRED_ROUTES_SHARE_SINGLE_CHOKEPOINT`
- `BASEMENT_CONTINUATION_NOT_INTERRUPTED`

## 14.2 Warnings

A shell may bake with a warning when:

- `STAIR_LOW_ARCHETYPE_FIT`
- `STAIR_EXCESSIVE_TRAVEL_DISTANCE`
- `STAIR_APPROACH_VISIBILITY_LOW`
- `STAIR_DISCHARGE_ROUTE_HAS_MULTIPLE_TURNS`
- `STAIR_REDUCES_ROOM_PACKING_EFFICIENCY`
- `STAIR_PAIR_COVERAGE_UNBALANCED`
- `CONVENIENCE_STAIR_MAY_BE_CONFUSED_WITH_EXIT`
- `SERVICE_STAIR_PUBLICLY_EXPOSED`
- `EXTERIOR_STAIR_WEATHER_EXPOSURE`

## 14.3 Gameplay validation

- Player capsule can traverse every run and landing.
- Two players can pass on default commercial stairs where intended.
- AI agents can enter, turn, descend, and exit without oscillation.
- Door animations do not collide with agents or railings.
- Nav links update when doors change state.
- A server-authoritative door state cannot strand clients inside the stair.
- Critical egress doors are never client-only objects.
- Objective placement cannot occupy required landings or discharge paths.
- Cover generation cannot block the minimum route width.

---

## 15. Bake-Time Behavior

## 15.1 `shell.glb`

Bake:

- Stair runs and treads.
- Landings.
- Enclosure walls.
- Door frames and door leaves.
- Handrails and guards.
- Collision geometry.
- Stair underside and headroom cutouts.
- Exterior discharge landing where applicable.
- Semantic node names for each stair component.

Suggested node naming:

```text
StairSystem_stair_a
  Enclosure
  Flight_00
  Landing_00
  Flight_01
  Landing_01
  Door_floor_00
  Door_floor_01
  Discharge
```

## 15.2 `shell.gameplay.json`

Bake:

- Stair system identity and role.
- Floors served.
- Entry and exit nodes.
- Door semantics and authority.
- Navigation links.
- Egress route graph.
- Discharge destination.
- Route independence groups.
- Validation results.
- Debug visualization metadata.

## 15.3 Debug overlays

Deli Counter should display:

- Stair stack footprints by floor.
- Approach paths in one color.
- Protected stair volume in another color.
- Discharge route to exterior.
- Stair-pair separation measurement.
- Shared choke points.
- Door swing arcs.
- Landing clearance boxes.
- Headroom failure volumes.
- Invalid room overlaps.

---

## 16. Anti-Patterns the Generator Must Prevent

### Random center stair

A stair appears in the middle of a floor because space was available, but no corridor, enclosure, or ground discharge was planned.

### Stair into a room

The stair exits directly into a bedroom, office, bathroom, storage room, or objective room without a valid common circulation route.

### Door onto steps

The stair door opens and the player immediately falls or steps down because no landing exists.

### Ground-floor dead end

The stair reaches the ground floor but terminates in a locked room, basement corridor, or internal wall.

### Twin stairs in one core with no independence

Two stairs exist numerically but are vulnerable to the same door, room, hazard, or discharge blockage.

### Non-stacked stairs

The stair shifts to a different location on each floor with no transfer logic.

### Stair as room filler

Room packing is completed first, then the generator cuts a stair through whatever rooms happened to occupy the selected area.

### Locked egress roulette

Mission randomization locks a required stair door without ensuring a valid alternate route.

### Stair to nowhere

The top run ends against a slab, or a roof stair lacks a roof door and landing.

### Basement trap

The visual path encourages evacuees to continue below grade rather than exit at the discharge level.

---

## 17. Minimum Acceptance Criteria

A generated multi-story building passes the stairwell system review when:

1. Stair roles are declared before room packing is finalized.
2. Every occupied floor has a connected route to every stair intended to serve that floor.
3. Each multi-floor stair occupies a continuous vertical stack.
4. Every stair door opens onto a valid landing.
5. Door swing does not eliminate the usable landing or navigation route.
6. Every required egress stair reaches the exterior through a direct door, protected passage, or clearly legible lobby route.
7. Two required stairs are meaningfully separated and do not depend on one shared choke point.
8. A stair continuing below grade includes a clear interruption at the exit-discharge level.
9. No required stair is accessed through a prohibited room.
10. No room, prop, cover node, objective, or breach point occupies the protected stair or discharge volume.
11. Player and AI navigation succeeds from every occupied floor to a safe exterior destination.
12. Door state and stair-critical interactions are represented in server-authoritative gameplay data.
13. The GLB and gameplay JSON contain matching stair IDs and floor connections.
14. The validator provides a clear failure reason for every rejected stair candidate.

---

## 18. Recommended Implementation Sequence

### Phase 1: Semantic stair stacks

- Add stair roles and stack IDs.
- Reserve vertical footprints.
- Generate switchback stairs.
- Connect each floor to a corridor.
- Require ground discharge.

### Phase 2: Egress graph validation

- Build route graphs from rooms to stairs to exterior destinations.
- Measure stair separation.
- Detect shared choke points.
- Validate alternate routes.

### Phase 3: Archetype profiles

- Add office, hotel, apartment, storefront, school, warehouse, and house rules.
- Add weighted candidate zones.
- Add public, service, and convenience stair distinctions.

### Phase 4: Gameplay and networking semantics

- Bake door authority and replicated state.
- Prevent mission randomization from invalidating required routes.
- Add AI route costs and congestion metadata.

### Phase 5: Advanced stair types

- Exterior towers.
- Scissor stairs.
- Atrium convenience stairs.
- Split-level buildings.
- Transfer floors.
- Roof and basement access.

---

## 19. Source and Standards Basis

This specification is informed by the following sources and concepts:

- International Building Code, Chapter 10, including exit separation, door landings, stair landings, interior exit stair openings, stair continuity, and exit discharge.
- U.S. Access Board guidance for stairways, doors, maneuvering clearance, and accessible circulation.
- National Fire Protection Association explanation of exit access, exit, and exit discharge as separate parts of a means of egress.
- U.S. General Services Administration and Whole Building Design Guide circulation guidance, which treats exit stairs and elevators as building-core or common-space destinations connected by primary circulation.
- National Institute of Standards and Technology research on stair geometry, landings, doors, occupant density, movement, and evacuation flow.
- OSHA exit-route guidance supporting separated alternate routes and unobstructed exit paths.

Local requirements vary. Deli Counter should expose dimensions, separation factors, door behavior, enclosure rules, and travel limits through configurable profiles rather than hard-coding one jurisdiction as universal truth.

---

## 20. Final Design Principle

Deli Counter should generate a building around its circulation and egress logic, not generate rooms first and force stairs into the leftovers.

A believable stairwell has:

- A reason to be where it is.
- A consistent vertical stack.
- A clear way in on every floor.
- Safe landings and door movement.
- A protected or believable circulation relationship.
- A clear way out at ground level.
- A meaningfully separate alternate route when redundancy is required.

When those conditions are present, the staircase will feel like part of the building rather than a procedural artifact.
