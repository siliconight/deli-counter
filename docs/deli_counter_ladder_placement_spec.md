# Deli Counter Ladder Placement and Access Specification

**Status:** Proposed generation and validation specification  
**Target:** Deli Counter building shell generation  
**Engine target:** Godot 4.7  
**Primary outputs:** `shell.glb` and `shell.gameplay.json`

## 1. Purpose

This document defines how Deli Counter should place fixed ladders, roof-access ladders, service ladders, rooftop connectors, and legacy fire-escape ladders so they feel like intentional parts of a real building.

The central rule is:

> A ladder is a specialized connection between two usable surfaces. It must have a defined purpose, a safe approach, a safe transition at the top, and enough surrounding clearance to be climbed.

Deli Counter should never treat a ladder as decoration attached to an empty exterior wall. The ladder, lower approach, climbing volume, upper landing, guards, parapet transition, access controls, and connected route should be generated and validated as one system.

This specification is intended to create architecturally believable game spaces. It is not a substitute for review by an architect, fire protection engineer, occupational safety specialist, accessibility specialist, or local code official.

---

## 2. Critical Clarification: Ladders Are Usually Not Primary Building Egress

A permanent vertical ladder is generally not a normal means of egress from an occupied space in a modern building.

In practical terms:

- A roof-access ladder usually exists so maintenance personnel can reach equipment or inspect the roof.
- A service ladder may connect maintenance platforms, mezzanines, catwalks, pits, or mechanical levels.
- A rooftop connector may bridge two roof elevations.
- A legacy fire escape may include ladders, but the occupiable part is normally a stair and platform system.
- A drop ladder may form the final segment from a fire-escape platform toward the ground in some existing buildings.
- A bare vertical ladder should not be generated as the only normal escape route for a populated modern floor.

For Deli Counter, every ladder must carry an explicit classification:

```text
not_egress
service_access
maintenance_access
roof_access
rooftop_connector
legacy_secondary_escape
fire_escape_termination
special_gameplay_route
```

The generator must not silently count a ladder as an ordinary exit stair.

---

## 3. What Deli Counter Must Understand

### 3.1 Fixed ladder

A permanently attached ladder mounted to a wall, structure, equipment frame, shaft, or platform.

### 3.2 Roof-access ladder

A ladder used to reach a roof from the ground, an intermediate platform, an interior service space, or a roof hatch.

### 3.3 Service ladder

A ladder used by maintenance or operations personnel to reach equipment, catwalks, mezzanines, pits, tanks, machinery, or restricted technical areas.

### 3.4 Rooftop connector ladder

A short ladder connecting two roof surfaces at different elevations, such as a main roof and a raised mechanical penthouse roof.

### 3.5 Fire escape

An exterior escape system usually composed of platforms, balconies, and stairs attached to an existing building. A ladder may be one component, but should not be treated as the entire system.

### 3.6 Fire-escape ladder

A ladder associated with an existing approved fire escape. It may connect platforms or provide the final descent toward grade.

### 3.7 Drop ladder or counterbalanced ladder

A ladder stored above ground level that can be lowered from a fire-escape platform during an emergency. It should not permanently block sidewalks, alleys, doors, or vehicle circulation.

### 3.8 Through ladder

A ladder whose climber passes between extended side rails onto the upper landing.

### 3.9 Side-step ladder

A ladder whose climber steps sideways from the ladder onto a platform or roof.

### 3.10 Roof hatch ladder

An interior fixed ladder terminating at a roof hatch. The hatch, landing zone, guard condition, and opening direction are part of the ladder system.

### 3.11 Parapet crossover

A condition where the ladder reaches the exterior face of a parapet and the climber must safely cross over the parapet to the roof surface. This may require a platform, step-through opening, inside ladder segment, or crossover stairs.

### 3.12 Ladder landing

The stable surface from which the user mounts or dismounts the ladder. Both the lower and upper ends require a valid landing condition.

### 3.13 Climbing volume

The clear 3D space occupied by a person using the ladder, including approach, body clearance, hand clearance, mount, and dismount space.

---

## 4. Foundational Generation Rules

These rules should be treated as invariants unless a building archetype explicitly overrides them.

### Rule 1: Assign the ladder a role before generating geometry

The generator must answer the following before creating a ladder:

1. What two surfaces does it connect?
2. Who is expected to use it?
3. Is it public, staff-only, maintenance-only, emergency-only, or gameplay-only?
4. Does it count as egress?
5. Is the upper surface walkable and connected to another route?
6. Is the ladder exposed to fall hazards, weather, vehicles, or security concerns?

A ladder without a role should not be generated.

### Rule 2: A ladder must connect two real, traversable surfaces

Every ladder requires:

- A lower mount surface.
- An upper dismount surface.
- A continuous climbing path between them.
- A valid route leading to the lower surface.
- A valid route leading away from the upper surface.

Reject ladders that terminate:

- Against a blank wall.
- Under an overhang with no opening.
- At a parapet with no crossover.
- On a roof section marked non-walkable.
- At an inaccessible ledge.
- Inside a sealed shaft.
- Below a hatch that cannot open.
- Above a cluttered or blocked lower landing.
- On a decorative facade element with no usable platform.

### Rule 3: Exterior ladders usually belong on service-facing building edges

Preferred exterior locations include:

- Rear facades.
- Side facades.
- Alleys.
- Service yards.
- Loading-area edges outside vehicle paths.
- Courtyards used for building services.
- Walls near rooftop mechanical equipment.
- Walls adjoining existing maintenance platforms.

Lower preference locations include:

- Main public facades.
- Directly beside the principal entrance.
- Shopfront display walls.
- Prominent ceremonial elevations.
- Residential bedroom windows.
- Areas intended for uninterrupted public circulation.

A front-facade ladder is allowed when justified by building type, industrial character, historic configuration, or deliberate gameplay design.

### Rule 4: The lower approach must be intentional and usable

The bottom of the ladder requires a stable approach zone.

The lower landing should:

- Be level or nearly level.
- Be large enough to stand, turn, and begin climbing.
- Be reachable without stepping over equipment or debris.
- Remain outside a door swing.
- Remain outside an active vehicle lane unless protected.
- Avoid drainage channels, snow-dump zones, and standing-water areas.
- Avoid hot exhausts, transformers, fuel storage, and other hazards.
- Avoid placing the user's back directly into traffic.

For game generation, reserve a default lower clear zone of at least:

```text
width: 1.20 m
 depth: 1.20 m
height: 2.20 m
```

Larger zones are preferred where players, AI, or combat may use the ladder.

### Rule 5: The top transition must be generated as part of the ladder

The top of the ladder is not complete merely because the highest rung reaches the roof elevation.

Deli Counter must generate one of the following transition types:

```text
through_step_off
side_step_off
roof_hatch_exit
parapet_cut_through
parapet_crossover_platform
parapet_inside_ladder
platform_gate_entry
fire_escape_platform_entry
```

Each transition must include:

- A stable upper landing.
- Continuous handholds or extended side rails.
- A legal step-across distance for the selected profile.
- No forced jump.
- No collision with parapets, railings, ductwork, or hatch covers.
- Protection against walking directly into an opening where applicable.

### Rule 6: A roof edge cannot be treated as a landing by itself

If a ladder reaches a roof edge, the generator must determine whether the edge has:

- A parapet.
- A guardrail.
- A gate.
- A step-through opening.
- A crossover platform.
- A setback landing.

Reject a layout where the player climbs directly onto a narrow roof edge with no secure standing surface.

### Rule 7: Ladder openings and platform entrances need guarding

Where a ladder enters a platform, catwalk, hatch, or roof opening, Deli Counter should generate one of the following:

- A self-closing gate.
- An offset guard arrangement.
- A guarded hatch opening.
- A parapet cut-through with controlled passage.
- A protected side-step transition.

The generator should not leave an unguarded rectangular hole in a roof or platform.

### Rule 8: Preserve the full climbing clearance

The climbing volume must remain free of:

- Pipes.
- Ducts.
- Signs.
- Electrical boxes.
- Window projections.
- Drain leaders.
- Lights mounted at head height.
- Fire-escape stair undersides.
- Security cameras inside the body envelope.
- Decorative cornices.
- Rooftop equipment at the dismount point.

Room packing and facade dressing may not invade an accepted ladder clearance volume.

### Rule 9: Keep ladders away from doors and windows unless the relationship is intentional

Do not place a ladder:

- Directly in front of an outward-swinging door.
- Across an emergency exit door.
- Over an operable window.
- Where a window opens into the climbing path.
- Directly below a window air-conditioning unit.
- Where a falling object from a window is an obvious hazard.

A ladder may align with a fire-escape window only when the window is explicitly modeled as the access opening to a platform.

### Rule 10: Protect exterior ladders from vehicle impact

When a ladder is near a loading area, parking area, driveway, or alley traffic, Deli Counter should generate one or more of the following:

- Setback from the vehicle lane.
- Raised curb.
- Bollards.
- Guard posts.
- Protective alcove.
- Platform beginning above impact height.

Reject a ladder whose lowest rails occupy a vehicle swept path.

### Rule 11: Long climbs require an explicit fall-protection profile

For contemporary industrial or commercial profiles, a fixed ladder extending more than `7.3 m` above a lower level should not be generated as an unprotected uninterrupted climb.

The selected profile should add one or more of the following:

- Ladder safety rail.
- Personal fall-arrest attachment system.
- Rest platform.
- Offset ladder sections.
- Legacy cage or well for period-appropriate buildings.

Deli Counter should treat cages as a legacy or contextual visual feature, not as the default modern solution for every tall ladder.

### Rule 12: Exterior ladders require weather-aware placement

Avoid default placement:

- Directly below a roof scupper.
- Beneath gutter discharge.
- Inside a waterfall path from upper roofs.
- Where ice or snow would accumulate at the base.
- Immediately beside steam vents or hot exhaust.
- On a surface with no drainage.

For stylized or historical settings, these conditions may appear as authored hazards, but they should be tagged rather than accidental.

### Rule 13: Restricted ladders need access control

Maintenance and roof-access ladders should commonly include one of the following:

- Locked gate.
- Ladder guard cover.
- Locked hatch.
- Staff-only room.
- Elevated first rung.
- Removable lower section.
- Security enclosure.

The access-control method must not accidentally block a required egress route.

### Rule 14: A legacy fire-escape ladder must belong to a complete escape route

A fire-escape ladder is valid only when it connects to:

- An approved platform or balcony.
- A fire-escape stair system.
- A reachable access opening.
- A ground or lower platform termination.
- A route that does not end above an inaccessible fenced area.

Do not attach an isolated ladder to an upper-story window and label it a fire escape.

### Rule 15: A gameplay ladder still needs architectural logic

Deli Counter may generate special infiltration, escape, breach, or rooftop traversal ladders. These may be less code-like, but they must still explain:

- Who installed the ladder.
- Why the connected areas need access.
- Where a real user would mount and dismount.
- How the ladder is secured.
- Why it is accessible or restricted.

---

## 5. Where Ladders Actually Tend to Exist

Deli Counter should use weighted placement patterns based on building archetype, age, occupancy, roof configuration, service layout, and gameplay role.

## 5.1 Small detached commercial building

Examples:

- Restaurant.
- Convenience store.
- Small clinic.
- Neighborhood office.
- Standalone retail building.

Common ladder patterns:

- Exterior fixed ladder on a rear or side wall for roof equipment access.
- Interior service-room ladder to a roof hatch.
- Short exterior ladder from a low roof to a higher mechanical roof.
- Ladder near the kitchen, utility, or electrical service side, but clear of hot exhaust and grease discharge.

Preferred Deli Counter logic:

- Favor the rear service facade.
- Place near the rooftop equipment zone.
- Keep clear of the public entrance and customer parking path.
- Provide a lockable lower guard or staff-controlled access.
- Connect the roof landing to a walkable maintenance path.

## 5.2 Narrow urban storefront or row building

Examples:

- Main-street shop.
- Bar or restaurant.
- Mixed-use masonry row building.
- Small apartment over retail.

Common ladder patterns:

- Exterior roof-access ladder in a rear yard or alley.
- Short ladder between stepped roof elevations.
- Legacy fire escape on the rear facade or courtyard facade.
- Drop ladder from the lowest fire-escape platform.
- Interior hatch ladder within a rear service corridor or utility room.

Preferred Deli Counter logic:

- Favor the rear facade, alley, or light court.
- Align exterior ladder placement with party-wall roof geometry and stepped parapets.
- Keep the base out of trash storage, grease bins, and loading obstructions.
- If generating a fire escape, generate the full platform and stair hierarchy first.
- Treat any ladder as a component of the rear-service circulation network.

## 5.3 Office building

Common ladder patterns:

- Interior ladder to a restricted roof hatch.
- Service ladder within a mechanical penthouse.
- Short ladder between roof equipment platforms.
- Ladder inside a shaft or dedicated maintenance room.

Uncommon modern pattern:

- Bare public exterior ladder serving occupied office floors as an exit.

Preferred Deli Counter logic:

- Place ladders in building-service zones.
- Connect them to mechanical rooms, janitor areas, or roof-access corridors.
- Use locked hatches or controlled doors.
- Prefer stairs for normal rooftop access in larger buildings.

## 5.4 Hotel, dormitory, or apartment building

Common ladder patterns:

- Restricted roof-hatch ladder inside a service space.
- Short roof-to-roof connector ladder.
- Legacy exterior fire escapes on older urban buildings.
- Drop ladder or counterbalanced stair at the lowest fire-escape platform.

Preferred Deli Counter logic:

- Never use a maintenance ladder as the main resident exit.
- Place modern roof access away from private dwelling units where possible.
- When using a legacy fire escape, connect each served floor through a plausible window or door onto a platform.
- Keep platforms remote from easily accessed child-play areas unless secured.
- Resolve the lowest platform to grade.

## 5.5 School or institutional building

Common ladder patterns:

- Locked interior roof hatch in a maintenance room.
- Exterior ladder inside a secured service yard.
- Short ladders around rooftop mechanical platforms.

Preferred Deli Counter logic:

- Restrict public access.
- Avoid playgrounds, student courtyards, and public gathering zones.
- Place behind locked gates or inside staff-only rooms.
- Do not count ladders as student evacuation routes.

## 5.6 Warehouse or industrial building

Common ladder patterns:

- Exterior roof-access ladder near loading or maintenance zones.
- Interior ladders to catwalks and equipment platforms.
- Ladder sections between mezzanines.
- Tank, silo, conveyor, and machinery access ladders.
- Multiple offset sections with platforms on tall structures.

Preferred Deli Counter logic:

- Use the structural bay grid.
- Attach ladders to columns, walls, platforms, or equipment frames.
- Keep ladder bases out of forklift lanes.
- Add bollards or protected alcoves near traffic.
- Use fall-protection profiles for long climbs.
- Connect every upper platform to a real service destination.

## 5.7 Parking structure

Common ladder patterns:

- Maintenance ladder to roof equipment or signage.
- Ladder to elevator-overrun or service platforms.
- Restricted ladder inside a utility enclosure.

Uncommon pattern:

- Ladder used for normal occupant travel between parking decks.

Preferred Deli Counter logic:

- Use stairs and ramps for ordinary circulation.
- Keep service ladders behind barriers or doors.
- Protect exposed ladder bases from vehicles.

## 5.8 House or townhouse

Common ladder patterns:

- Attic access ladder.
- Portable escape ladder stored by an upper window.
- Exterior maintenance ladder that is temporary rather than fixed.
- Fixed ladder to a small roof deck in unusual or historic conditions.

Preferred Deli Counter logic:

- Do not generate a permanent exterior fire-escape ladder by default.
- Treat portable escape ladders as props, not permanent circulation.
- Use folding attic stairs or hatch access for attic spaces.
- Require explicit archetype or authored intent for a permanent roof ladder.

## 5.9 Factory, refinery, power, or process facility

Common ladder patterns:

- Dense service-ladder networks.
- Ladder access to tanks, vessels, pipe racks, catwalks, and towers.
- Caged legacy ladders.
- Modern safety-rail systems.
- Offset sections and rest platforms.

Preferred Deli Counter logic:

- Generate ladders from the equipment and platform graph, not from empty wall availability.
- Protect ladder approaches from active machinery.
- Preserve clear climbing envelopes through pipe and conduit dressing.
- Mark restricted and hazardous access.

## 5.10 Rooftop mechanical area

Common ladder patterns:

- Ladder from roof to raised equipment platform.
- Ladder over a parapet or screen wall.
- Ladder from main roof to penthouse roof.
- Ladder into a cooling-tower or service platform zone.

Preferred Deli Counter logic:

- Connect ladders to maintenance walkways.
- Avoid forcing users to step directly onto ducts or curbs.
- Provide gates or guards at platform openings.
- Avoid roof-edge mount and dismount zones without protection.

---

## 6. Ladder Roles Deli Counter Should Generate

### 6.1 Exterior roof-access ladder

**Purpose:** Reach a roof from grade or a service yard.  
**Typical location:** Rear or side facade.  
**Access:** Restricted or lockable.  
**Egress status:** Not egress.  
**Required connections:** Ground service path and roof maintenance path.

### 6.2 Interior roof-hatch ladder

**Purpose:** Reach a roof through a hatch.  
**Typical location:** Mechanical room, service corridor, janitor room, or dedicated shaft.  
**Access:** Restricted.  
**Egress status:** Not egress.  
**Required connections:** Interior service route, hatch opening, guarded roof-side landing.

### 6.3 Rooftop level-change ladder

**Purpose:** Connect two nearby roof elevations.  
**Typical location:** Against penthouse, parapet, or raised roof wall.  
**Access:** Maintenance or gameplay.  
**Egress status:** Normally not egress.  
**Required connections:** Walkable lower roof and walkable upper roof.

### 6.4 Equipment-platform ladder

**Purpose:** Reach machinery, catwalk, tank, sign, or equipment platform.  
**Typical location:** Industrial or rooftop service areas.  
**Access:** Restricted.  
**Egress status:** Not egress.  
**Required connections:** Service path and guarded upper platform.

### 6.5 Pit or shaft ladder

**Purpose:** Enter and exit a maintenance pit, trench, or shaft.  
**Typical location:** Utility, industrial, or garage service areas.  
**Access:** Restricted.  
**Egress status:** Not normal building egress.  
**Required connections:** Guarded floor opening, controlled access, clear pit floor.

### 6.6 Legacy fire-escape ladder

**Purpose:** Connect fire-escape platforms or provide final descent.  
**Typical location:** Rear or courtyard facade of an existing older building.  
**Access:** Emergency or secondary escape.  
**Egress status:** Legacy secondary escape only when the selected building profile allows it.  
**Required connections:** Fire-escape platform system and valid termination.

### 6.7 Drop ladder

**Purpose:** Extend from an elevated fire-escape platform toward grade during emergency use.  
**Typical location:** Lowest exterior fire-escape platform.  
**Access:** Emergency-only.  
**Egress status:** Fire-escape termination in limited legacy profiles.  
**Required connections:** Deployable state, clear descent area, reachable ground.

### 6.8 Special gameplay ladder

**Purpose:** Alternate route, infiltration path, escape path, rooftop shortcut, or vertical combat connection.  
**Typical location:** Any location with believable service or access logic.  
**Access:** Configurable.  
**Egress status:** Explicitly authored.  
**Required connections:** Valid traversal anchors and route graph.

---

## 7. Exterior Wall Placement Logic

### 7.1 Preferred wall segments

Candidate wall segments should receive positive weight when they:

- Face a rear yard, alley, or service court.
- Are adjacent to a maintenance room.
- Align with rooftop equipment.
- Provide a direct uninterrupted vertical run.
- Have clear lower and upper landing areas.
- Avoid public entrances and primary windows.
- Allow guards, gates, or access-control hardware.
- Are structurally plausible attachment surfaces.

### 7.2 Wall segments to avoid

Reject or heavily penalize wall segments that:

- Contain a door in the climbing zone.
- Contain an operable window in the climbing zone.
- Face a narrow public sidewalk without a controlled base condition.
- Occupy a fire-lane clear zone.
- Intersect vehicle swept paths.
- Sit beneath a scupper or roof drain.
- Sit beside high-temperature exhaust.
- End below a large cornice with no pass-through.
- Lead to a roof edge with no upper landing.
- Intersect signage or facade-mounted equipment.
- Are too close to exposed electrical equipment.

### 7.3 Facade attachment zone

Once a candidate wall is selected, reserve a vertical facade strip containing:

- Ladder rails and rungs.
- Wall brackets.
- Climbing clearance.
- Lower standing zone.
- Upper transition zone.
- Access guard or gate.
- Optional safety rail or legacy cage.
- Maintenance collision buffer.

No decorative pass may place assets inside this reserved strip.

---

## 8. Interior Roof-Hatch Placement Logic

### 8.1 Preferred interior rooms

A roof-hatch ladder should normally originate in:

- Mechanical room.
- Electrical or utility room where safe.
- Dedicated roof-access room.
- Service corridor alcove.
- Janitor or maintenance room.
- Back-of-house circulation zone.

### 8.2 Rooms to avoid

Do not place a maintenance roof ladder in:

- Public lobby.
- Bathroom stall.
- Kitchen cook line.
- Bedroom.
- Classroom.
- Patient room.
- Retail sales aisle.
- Private office used as the only route.
- Storage room whose shelving blocks access.
- Exit stair enclosure unless the selected design explicitly permits and supports it.

### 8.3 Hatch logic

The generator must reserve:

- Ladder climbing volume.
- Hatch opening volume.
- Hatch swing or lifting volume.
- Clear dismount zone above.
- Guard or gate condition on the roof.
- Weather curb and roof opening frame.

Reject hatches where:

- The cover collides with a parapet or equipment.
- The climber emerges beneath ductwork.
- The hatch opens into a roof-edge fall zone.
- The ladder is offset from the opening without a platform.
- The service room door swing blocks the ladder base.

---

## 9. Fire-Escape Placement Logic

### 9.1 Generate the platform system before the ladder

For a legacy fire escape, use this order:

1. Identify served occupied floors.
2. Identify valid exterior access openings.
3. Place floor-level platforms.
4. Connect platforms with stairs where possible.
5. Add guards and rails.
6. Select the termination method at the lowest platform.
7. Add a ladder only where the profile justifies it.
8. Validate the full route to grade.

### 9.2 Valid access openings

A fire-escape platform should connect through:

- A dedicated exterior door.
- A window explicitly sized and tagged for escape access.
- A corridor-end opening in an existing-building profile.

The access opening must not be hidden behind permanent furniture, kitchen equipment, bars that cannot release, or a locked private room serving unrelated occupants.

### 9.3 Lowest-platform termination

Preferred terminations:

- Stair to grade.
- Counterbalanced stair.
- Deployable stair.

Limited legacy termination:

- Approved ladder serving a low occupant load under the selected existing-building profile.

Deli Counter should treat the ladder termination as the exception, not the default.

### 9.4 Fire-escape base zone

The landing area below a deployable ladder or stair must remain clear of:

- Fences.
- Locked gates with no release.
- Dumpsters.
- Parked vehicles.
- Basement areaways.
- Spiked railings.
- Roof projections.
- Deep window wells.
- Active loading operations.

---

## 10. Geometry Defaults for Plausible Fixed Ladders

The following are Deli Counter defaults informed by common U.S. fixed-ladder criteria. They are not universal legal dimensions.

```text
rung_spacing_min:           0.25 m
rung_spacing_max:           0.36 m
rung_spacing_preferred:     0.30 m
fixed_ladder_clear_width:   0.41 m minimum
preferred_gameplay_width:   0.50 m
rung_center_to_wall:        0.18 m minimum
climbing_side_clearance:    0.76 m preferred
side_clearance_each_side:   0.38 m preferred
rail_extension_above_top:   1.10 m preferred
lower_clear_zone_width:     1.20 m
lower_clear_zone_depth:     1.20 m
upper_clear_zone_width:     1.20 m
upper_clear_zone_depth:     1.20 m
```

### 10.1 Through-ladder transition

Default step-across range:

```text
0.18 m to 0.30 m
```

Default rail opening at upper landing:

```text
0.61 m to 0.76 m
```

### 10.2 Side-step transition

Default step-across range:

```text
0.38 m to 0.51 m
```

### 10.3 Long-climb trigger

```text
fall_protection_trigger_height: 7.30 m
```

At or above this height, the selected modern profile should require a ladder-safety or fall-arrest representation.

### 10.4 Gameplay scaling allowance

To support readable first-person and third-person traversal, Deli Counter may widen the ladder and mount zones beyond code-informed minima.

Recommended gameplay defaults:

```text
rail_inside_width:           0.50 m
mount_capsule_width:         0.80 m
mount_zone_depth:            1.00 m
upper_dismount_zone_depth:   1.20 m
minimum_head_clearance:      2.20 m
```

Any gameplay enlargement should preserve the visual language of a fixed ladder.

---

## 11. Ladder Type Selection

### 11.1 Vertical fixed ladder

Use when:

- Space is constrained.
- Access is infrequent.
- The destination is maintenance-oriented.
- The climb is relatively short or has an appropriate fall-protection profile.

Do not use when:

- The route is for ordinary public circulation.
- Users must carry large loads.
- The destination has frequent traffic.
- The ladder would serve as the only occupied-floor exit.

### 11.2 Inclined ship ladder

Use when:

- A steep service connection is needed.
- More frequent access is expected than a vertical ladder supports.
- There is enough horizontal run.
- Handrails can be installed on both sides.

Treat it as a distinct traversal type, not as an ordinary stair.

### 11.3 Alternating-tread device

Use only for specialized service access and low-frequency occupancy profiles. It should not appear as a normal public stair.

### 11.4 Legacy caged ladder

Use when:

- The building era or industrial visual profile supports it.
- The ladder predates modern safety-rail expectations.
- The cage does not obstruct gameplay traversal.

Do not add cages automatically to every ladder.

### 11.5 Ladder with safety rail

Use for modern tall fixed ladders in industrial and commercial profiles.

The safety rail should:

- Run continuously through the climb.
- Avoid collision with rungs and mount transitions.
- Connect to a believable attachment point.
- Be represented visually even if player harness mechanics are abstracted.

### 11.6 Offset ladder sections

Use when:

- A climb is tall.
- Rest platforms are required by the selected profile.
- Industrial architecture supports multiple sections.

Each section must terminate at a real platform, then begin from a separate protected opening.

---

## 12. Candidate Placement Algorithm

## 12.1 Inputs

```text
building_archetype
building_age_profile
floor_polygons
roof_polygons
walkable_roof_regions
roof_elevations
parapet_segments
exterior_wall_segments
interior_service_rooms
mechanical_equipment_zones
service_yards
alleys
loading_zones
vehicle_swept_paths
public_entrances
exterior_doors
windows
roof_drains
exhaust_zones
electrical_hazard_zones
fire_escape_platforms
catwalks
maintenance_platforms
security_zones
gameplay_route_requests
```

## 12.2 Candidate generation

Generate ladder candidates from meaningful connection pairs rather than arbitrary walls.

Example connection pairs:

```text
service_yard -> main_roof
maintenance_room -> roof_hatch
main_roof -> penthouse_roof
main_roof -> equipment_platform
factory_floor -> catwalk
lower_fire_escape_platform -> ground
upper_fire_escape_platform -> lower_fire_escape_platform
parking_service_room -> sign_platform
```

For each connection pair:

1. Find adjacent or aligned host surfaces.
2. Calculate vertical climb height.
3. Select exterior, interior, or platform-mounted ladder type.
4. Generate lower approach volume.
5. Generate climbing volume.
6. Generate upper transition volume.
7. Test hazards and obstructions.
8. Score architectural fit.
9. Score gameplay usefulness.
10. Accept, revise, or reject.

## 12.3 Candidate rejection tests

Reject a candidate when any of the following is true:

- Lower landing is not reachable.
- Upper landing is not walkable.
- Host wall cannot support a plausible attachment.
- Climbing volume intersects a door or window.
- Climbing volume intersects fixed equipment.
- Bottom zone overlaps an active vehicle swept path without protection.
- Top transition requires a jump.
- Ladder reaches a parapet with no crossover solution.
- Roof hatch cannot open.
- Ladder dismount is inside an unguarded roof opening.
- Ladder is the only generated exit from a normally occupied modern floor.
- Exterior ladder terminates inside a locked fenced area with no onward route.
- Long climb lacks the required safety profile.
- Ladder base occupies the exterior discharge path of another exit.
- Fire-escape ladder is not connected to a platform system.
- Drop ladder deployment intersects parked vehicles, fences, or structures.
- Decorative assets already reserve the required wall area and cannot be moved.

## 12.4 Candidate scoring

Suggested scoring model:

```text
score =
    service_adjacency
  + destination_relevance
  + route_continuity
  + rear_or_side_facade_fit
  + clear_lower_landing
  + clear_upper_landing
  + structural_alignment
  + security_fit
  + gameplay_value
  - public_facade_penalty
  - door_window_conflict
  - vehicle_conflict
  - weather_hazard
  - utility_hazard
  - excessive_climb_penalty
  - visual_noise_penalty
```

Suggested weights:

```text
service_adjacency:          +20
destination_relevance:      +25
route_continuity:           +30
rear_or_side_facade_fit:    +12
clear_lower_landing:        +20
clear_upper_landing:        +25
structural_alignment:       +10
security_fit:               +8
gameplay_value:             +0 to +20
public_facade_penalty:      -12
door_window_conflict:       -40
vehicle_conflict:           -40
weather_hazard:             -15
utility_hazard:             -30
excessive_climb_penalty:    -5 to -25
visual_noise_penalty:       -5
```

Hard-rule failures should reject a candidate regardless of score.

## 12.5 Ladder count logic

Do not generate ladders merely to satisfy a density target.

Recommended logic:

```text
required_ladders = connection_requirements.count
optional_ladders = gameplay_or_archetype_requests.count
```

Typical output tendencies:

- Small commercial building: zero or one roof-access ladder.
- Narrow urban mixed-use building: zero or one roof-access ladder, plus optional legacy fire escape.
- Office building: usually one controlled roof-access route, often stair or hatch rather than exterior ladder.
- Warehouse: one or more roof, catwalk, and equipment ladders.
- Industrial plant: many ladders generated from platform topology.
- Residential house: usually none as permanent exterior features.

---

## 13. Route Graph Semantics

Every accepted ladder should become a directed or bidirectional traversal edge in the gameplay graph.

### 13.1 Required nodes

```text
lower_approach_node
lower_mount_node
climb_start_node
climb_end_node
upper_dismount_node
upper_route_node
```

Optional nodes:

```text
access_gate_node
hatch_interaction_node
rest_platform_node
drop_ladder_control_node
fall_protection_attach_node
```

### 13.2 Route direction

A ladder may be:

```text
bidirectional
up_only
down_only
deploy_then_bidirectional
scripted_direction
```

Examples:

- Standard service ladder: bidirectional.
- Drop ladder from fire escape: deploy then bidirectional.
- Escape-only folding ladder: down only until deployed.
- Broken gameplay ladder: scripted or disabled.

### 13.3 Egress graph exclusion

By default:

```text
counts_as_primary_egress = false
counts_as_accessible_egress = false
counts_as_public_circulation = false
```

Only an explicit legacy or authored profile may change `counts_as_secondary_escape` to `true`.

---

## 14. Data Model

Suggested `shell.gameplay.json` representation:

```json
{
  "ladders": [
    {
      "id": "ladder_roof_rear_01",
      "role": "roof_access",
      "ladder_type": "fixed_vertical",
      "placement_mode": "exterior_wall",
      "building_profile": "small_commercial_modern",
      "host_wall_id": "wall_rear_04",
      "lower_surface_id": "service_yard_01",
      "upper_surface_id": "roof_main_walkable_01",
      "lower_anchor": [12.4, 0.0, -8.1],
      "upper_anchor": [12.4, 5.6, -8.1],
      "climb_height_m": 5.6,
      "direction": "bidirectional",
      "access_class": "staff_restricted",
      "egress_classification": "not_egress",
      "counts_as_primary_egress": false,
      "counts_as_secondary_escape": false,
      "transition": {
        "type": "parapet_cut_through",
        "step_across_m": 0.24,
        "rail_extension_m": 1.1,
        "upper_gate": true
      },
      "geometry": {
        "clear_width_m": 0.5,
        "rung_spacing_m": 0.3,
        "rung_center_to_wall_m": 0.18,
        "climbing_clearance_m": 0.76
      },
      "fall_protection": {
        "required": false,
        "type": "none"
      },
      "access_control": {
        "type": "lockable_ladder_guard",
        "state": "locked"
      },
      "gameplay": {
        "player_traversable": true,
        "ai_traversable": true,
        "server_authoritative_state": true,
        "interaction_required": true,
        "mount_anchor_id": "ladder_roof_rear_01_mount",
        "dismount_anchor_id": "ladder_roof_rear_01_dismount"
      },
      "validation": {
        "lower_landing_valid": true,
        "upper_landing_valid": true,
        "climbing_volume_clear": true,
        "route_continuity_valid": true
      }
    }
  ]
}
```

### 14.1 Required fields

```text
id
role
ladder_type
placement_mode
lower_surface_id
upper_surface_id
lower_anchor
upper_anchor
climb_height_m
direction
access_class
egress_classification
transition.type
geometry.clear_width_m
geometry.rung_spacing_m
gameplay.player_traversable
validation state
```

### 14.2 Optional fields

```text
host_wall_id
host_structure_id
roof_hatch_id
fire_escape_id
platform_ids
parapet_id
fall_protection
access_control
weather_exposure
vehicle_protection
legacy_profile
network_state
animation_profile
```

---

## 15. Validation Rules

## 15.1 Hard errors

Deli Counter should fail the ladder bake when:

- `LADDER_NO_ROLE`: Ladder has no declared purpose.
- `LADDER_NO_LOWER_SURFACE`: Lower anchor is not on a usable surface.
- `LADDER_NO_UPPER_SURFACE`: Upper anchor is not on a usable surface.
- `LADDER_ROUTE_DISCONNECTED`: Lower or upper route does not connect onward.
- `LADDER_CLIMB_VOLUME_BLOCKED`: Geometry intersects the climb envelope.
- `LADDER_DOOR_CONFLICT`: Door swing intersects the ladder or mount zone.
- `LADDER_WINDOW_CONFLICT`: Operable window intersects the climbing zone.
- `LADDER_UNSAFE_TOP_TRANSITION`: No valid step-off or crossover exists.
- `LADDER_UNGUARDED_OPENING`: Platform or hatch opening has no guard solution.
- `LADDER_VEHICLE_CONFLICT`: Base occupies a vehicle path without protection.
- `LADDER_HAZARD_ZONE`: Ladder intersects an electrical, exhaust, heat, or equipment hazard.
- `LADDER_LONG_CLIMB_UNPROTECTED`: Required fall-protection profile is missing.
- `LADDER_INVALID_EGRESS`: Ladder is incorrectly counted as normal required egress.
- `FIRE_ESCAPE_LADDER_ORPHANED`: Fire-escape ladder has no fire-escape platform system.
- `DROP_LADDER_NO_DEPLOYMENT_CLEARANCE`: Deployable ladder cannot reach clear ground.
- `ROOF_HATCH_BLOCKED`: Hatch cannot open or be exited.
- `PARAPET_CROSSOVER_MISSING`: Ladder ends outside a parapet without a crossover.
- `LADDER_TO_NOWHERE`: Destination contains no meaningful platform, route, or equipment.

## 15.2 Warnings

Deli Counter should emit warnings when:

- `LADDER_PUBLIC_FACADE`: Ladder is on a primary public elevation.
- `LADDER_NEAR_PUBLIC_ENTRANCE`: Base is close to a main entrance.
- `LADDER_NEAR_DRAINAGE`: Ladder is beneath a drain or scupper.
- `LADDER_SECURITY_EXPOSURE`: Restricted roof ladder is publicly accessible.
- `LADDER_LOW_GAMEPLAY_CLEARANCE`: Traversal zone meets technical minimum but may feel cramped.
- `LADDER_EXCESSIVE_HEIGHT`: Climb is unusually long for the archetype.
- `LADDER_NO_VISUAL_DESTINATION`: The connected destination is valid but visually unclear.
- `LADDER_BASE_CLUTTER_RISK`: Prop dressing may obstruct the lower approach.
- `LADDER_TOP_EDGE_RISK`: Upper landing is close to an unguarded roof edge.
- `LEGACY_FIRE_ESCAPE_PROFILE`: Layout depends on an existing-building exception.

## 15.3 Gameplay validation

For each player-traversable ladder, validate:

- Player capsule can reach the lower mount anchor.
- Player can align with the ladder without clipping.
- Mount animation clears nearby walls.
- Climb path is continuous.
- Dismount animation reaches a valid standing area.
- Camera does not pass through the host wall.
- Weapons or carried objects use the correct traversal state.
- Multiple players cannot permanently deadlock the route.
- AI can reserve, climb, and release the traversal edge.
- Falling or interruption returns the player to a valid state.
- Locked or deployed state replicates to all clients.

---

## 16. Bake-Time Behavior

## 16.1 `shell.glb`

The baked scene should include:

- Ladder rails.
- Rungs.
- Wall brackets or structural supports.
- Lower landing surface.
- Upper landing or platform.
- Parapet cut-through or crossover geometry.
- Guards or gates.
- Roof hatch and curb where applicable.
- Optional cage or safety rail.
- Bollards or protective structure where required.
- Fire-escape platform and deployment mechanism where applicable.
- Collision geometry.
- Traversal markers.

Semantic node naming example:

```text
Ladder_Roof_Rear_01
Ladder_Roof_Rear_01_Collision
Ladder_Roof_Rear_01_Mount
Ladder_Roof_Rear_01_Dismount
Ladder_Roof_Rear_01_ClimbPath
Ladder_Roof_Rear_01_LowerClearZone
Ladder_Roof_Rear_01_UpperClearZone
Ladder_Roof_Rear_01_Gate
```

## 16.2 `shell.gameplay.json`

The JSON should include:

- Ladder role and type.
- Connected surfaces.
- Mount and dismount anchors.
- Traversal direction.
- Access-control state.
- Egress classification.
- Fall-protection profile.
- Deployment state where applicable.
- Player and AI traversal permissions.
- Network ownership.
- Validation results.

## 16.3 Debug overlays

Deli Counter should provide overlays for:

```text
ladder role
lower approach zone
climbing volume
upper transition zone
connected route graph
egress inclusion or exclusion
hazard intersections
vehicle conflicts
roof-edge fall zones
access-control state
AI traversal direction
```

Recommended colors may be selected by the consuming project, but each semantic category should remain visually distinct.

---

## 17. Godot 4.7 Runtime Requirements

### 17.1 Traversal component

Each traversable ladder should instantiate or reference a reusable ladder traversal component containing:

- Mount trigger.
- Dismount trigger.
- Climb spline or axis.
- Direction restrictions.
- Animation profile.
- Occupancy or reservation state.
- Network replication state.
- Interaction permissions.

### 17.2 Navigation integration

Godot navigation should represent a ladder as an explicit off-mesh or custom navigation link rather than attempting to bake it as a walkable slope.

The link should expose:

```text
start_position
end_position
bidirectional
cost
agent_types
required_capability
access_state
reservation_state
```

### 17.3 Server authority

For online missions, the server should own:

- Ladder enabled or disabled state.
- Locked or unlocked state.
- Drop-ladder deployed state.
- Destruction or obstruction state.
- AI reservation.
- Objective gating.
- Player transition acceptance.

Clients may own:

- Local animation blending.
- Camera motion.
- Local sound playback.
- Cosmetic rung and hand effects.
- Non-authoritative traversal prediction.

### 17.4 AI behavior

AI should understand:

- Whether it can use ladders.
- Whether the ladder is one-at-a-time.
- Whether it may attack while climbing.
- Whether it should wait for another agent.
- Whether it may follow a player onto a roof.
- How to recover if the destination becomes blocked.

### 17.5 Combat behavior

Each ladder should declare:

```text
weapons_allowed_while_climbing
can_be_interrupted
can_fall
can_slide_down
can_be_destroyed
can_be_blocked
occupancy_limit
```

These are gameplay decisions, but they should be data-driven rather than hard-coded per mission.

---

## 18. Anti-Patterns the Generator Must Prevent

### Decorative ladder to nowhere

A ladder is attached to a wall but reaches no roof, hatch, platform, or equipment.

### Roof edge dismount

The player climbs onto a narrow unguarded edge with no standing area.

### Parapet dead end

The ladder reaches the outside of a parapet but provides no way to cross it.

### Door collision

An exterior door opens into the ladder or the player stands in the door swing to mount it.

### Window ladder

The ladder runs directly across windows without an intentional fire-escape relationship.

### Dumpster mount

The only way to reach the ladder is to climb over trash containers or service clutter.

### Forklift ladder

The ladder base sits in an active industrial vehicle lane.

### Drainpipe ladder

The ladder is directly under a scupper, gutter outlet, or roof-drain discharge.

### Bare-ladder primary exit

A modern occupied floor depends on a vertical ladder as its only normal escape route.

### Orphaned fire-escape ladder

A ladder is placed beneath an upper window with no platform, stairs, or complete route.

### Infinite climb

A tall ladder has no safety system, offset, or contextual explanation.

### Hatch collision

The roof hatch opens into the climber or cannot clear nearby equipment.

### Locked-route contradiction

A ladder is tagged as emergency egress but its gate or hatch is permanently locked.

### Multiplayer deadlock

Two players mount from opposite ends and become permanently stuck.

### AI teleport ladder

AI appears at the upper node without traversing or reserving the ladder.

---

## 19. Minimum Acceptance Criteria

A generated ladder is acceptable when all of the following are true:

1. The ladder has an explicit role.
2. It connects two valid surfaces.
3. The lower surface has a reachable and clear approach.
4. The upper surface has a stable dismount area.
5. The climbing volume is unobstructed.
6. Doors and windows do not collide with the ladder.
7. The top transition is explicitly resolved.
8. Platform and hatch openings are guarded where required.
9. Vehicle, weather, electrical, and exhaust hazards are checked.
10. Long climbs use the selected fall-protection profile.
11. The ladder is not incorrectly counted as ordinary required egress.
12. Legacy fire-escape ladders belong to a complete escape system.
13. The ladder route is represented in `shell.gameplay.json`.
14. Player traversal has valid mount and dismount anchors.
15. AI traversal is either supported or explicitly disabled.
16. Runtime state is server-authoritative for online missions.
17. Prop and facade passes cannot invade reserved ladder volumes.
18. Debug visualization proves the connected route and clearances.

---

## 20. Recommended Implementation Sequence

### Phase 1: Semantic ladder connections

- Add ladder roles.
- Require lower and upper surface references.
- Generate mount and dismount anchors.
- Add climbing clearance volumes.
- Reject ladders to nowhere.

### Phase 2: Exterior placement and roof transitions

- Add facade candidate scoring.
- Add parapet and roof-edge analysis.
- Add through and side-step transitions.
- Add lower and upper landing validation.
- Add door, window, and equipment conflict tests.

### Phase 3: Roof hatches and service access

- Generate interior service-room candidates.
- Add hatch opening and swing volumes.
- Add guarded roof openings.
- Add access-control semantics.

### Phase 4: Industrial ladders

- Add catwalk and equipment-platform graph generation.
- Add tall-climb fall-protection profiles.
- Add offset ladder sections and rest platforms.
- Add vehicle-impact protection.

### Phase 5: Legacy fire escapes

- Generate platform and stair systems first.
- Add access openings.
- Add lowest-platform termination logic.
- Add drop-ladder deployment state.
- Gate behind building-age and jurisdiction-inspired profiles.

### Phase 6: Gameplay and networking

- Add Godot 4.7 traversal components.
- Add AI navigation links.
- Add server-authoritative ladder states.
- Add occupancy and reservation handling.
- Add combat and interruption policies.

---

## 21. Suggested Configuration Profiles

### 21.1 `modern_small_commercial`

```yaml
allow_exterior_roof_ladder: true
allow_roof_hatch_ladder: true
allow_legacy_fire_escape: false
allow_ladder_as_egress: false
restrict_public_access: true
fall_protection_trigger_m: 7.3
prefer_rear_or_side_facade: true
```

### 21.2 `historic_urban_mixed_use`

```yaml
allow_exterior_roof_ladder: true
allow_roof_hatch_ladder: true
allow_legacy_fire_escape: true
allow_fire_escape_ladder_termination: conditional
allow_ladder_as_primary_egress: false
prefer_rear_courtyard_or_alley: true
```

### 21.3 `modern_office`

```yaml
allow_exterior_roof_ladder: conditional
allow_roof_hatch_ladder: true
allow_legacy_fire_escape: false
allow_ladder_as_egress: false
prefer_internal_service_access: true
restrict_public_access: true
```

### 21.4 `warehouse_industrial`

```yaml
allow_exterior_roof_ladder: true
allow_platform_ladders: true
allow_offset_sections: true
allow_legacy_cages: contextual
allow_ladder_as_public_circulation: false
require_vehicle_conflict_test: true
fall_protection_trigger_m: 7.3
```

### 21.5 `residential_house`

```yaml
allow_exterior_fixed_ladder: false
allow_portable_escape_ladder_prop: true
allow_attic_access_ladder: true
allow_legacy_fire_escape: false
```

### 21.6 `stylized_gameplay_override`

```yaml
allow_special_gameplay_ladder: true
require_architectural_rationale: true
require_valid_mount_and_dismount: true
allow_code_profile_override: true
mark_as_noncompliant_fiction: true
```

---

## 22. Source and Standards Basis

This specification uses the following sources as a code-informed baseline:

- International Building Code, Section 1011.16, which states that permanent ladders do not normally serve as part of the means of egress from occupied spaces and limits their use to specialized access conditions.  
  <https://codes.iccsafe.org/s/IBC2021P1/chapter-10-means-of-egress/IBC2021P1-Ch10-Sec1011.16>

- OSHA 29 CFR 1910.23, which provides general and fixed-ladder dimensional, clearance, transition, and use requirements.  
  <https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.23>

- OSHA 29 CFR 1910.28, which addresses fall protection for fixed ladders extending more than 24 feet above a lower level.  
  <https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.28>

- OSHA interpretation on guarding ladderway openings, which describes guardrail, gate, or offset protection at platform access points.  
  <https://www.osha.gov/laws-regs/standardinterpretations/2009-09-29>

- International Mechanical Code, Section 306.5, which provides criteria commonly used for permanent ladders accessing rooftop equipment.  
  <https://codes.iccsafe.org/s/IMC2024P1/chapter-3-general-regulations/IMC2024P1-Ch03-Sec306.5>

- International Fire Code existing-building provisions for fire-escape termination, including limited use of an approved fire-escape ladder for small occupant loads.  
  <https://codes.iccsafe.org/content/IFC2024V2.0/chapter-11-construction-requirements-for-existing-buildings>

Applicable requirements vary by jurisdiction, building use, building age, construction type, adopted code edition, workplace rules, and local approval. Deli Counter should expose profiles and validation evidence rather than claiming universal legal compliance.

---

## 23. Final Design Principle

> Do not ask, "Where can a ladder fit?" Ask, "What real access problem requires a ladder, and what complete route does that ladder create?"

A believable ladder begins at a usable approach, climbs through a protected clear volume, and ends at a stable connected destination. When a ladder is part of an escape system, the entire system must continue to safety. When it is only service access, Deli Counter must label it honestly and keep it out of the normal egress count.
