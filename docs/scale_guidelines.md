# Level scale guidelines

Practical, meter-based size targets for blocking out levels with Deli Counter.
These are production targets for blockouts, collision, navigation, AI pathing,
and multiplayer testing — not measurements from any specific game. They map
onto the kit's two modes plus a third "co-op route" style you can build with
the same primitives.

Everything is in **meters**. Deli Counter already uses meters with a 0.5 m
default grid, so these drop straight into specs.

## Player scale (all modes)

Author spaces around a human-sized player, slightly exaggerated so movement,
combat, AI, and 4-player body-blocking feel good.

| Element | Size |
|---|---|
| Player height / standing capsule | 1.8 m |
| Eye height | 1.55–1.65 m |
| Capsule radius | 0.35–0.45 m |
| Crouch height | 1.1–1.25 m |
| Doorway height | 2.2 m |
| Doorway width — min / comfortable / double | 0.9–1.1 / 1.2–1.5 / 1.8–2.8 m |

Deli Counter's opening defaults already sit in these bands (door 1.2 m × 2.2 m,
garage 3.5 m, window 1.6 m × 1.4 m). The validator's 0.8 m minimum opening
width keeps passages traversable.

## Grid and structural sizes

| Use | Grid |
|---|---|
| Fine detail | 0.125 m |
| Prop / blockout nudge | 0.25 m |
| Main layout (Deli Counter default) | 0.5 m |
| Large structural | 1.0 m |
| Room module | 2.0 m or 4.0 m |

Wall thickness 0.15–0.25 m (kit default `wall_thick` 0.3 m is close; drop to
0.2 m for a tighter look). One floor ≈ 3 m; the kit's `story_height` of
3.2–3.6 m in the examples lines up.

## Mode targets

### assault (tactical building)

Competitive, dense, attackers outside / defenders inside, vertical pressure,
breachable routes. **Best first canvas: 96 × 96 m.**

| Size | Footprint | Floors | Rooms |
|---|---|---|---|
| Small | 45–70 m sq | 2–3 | 18–30 |
| Medium | 70–110 m sq | 2–4 | 30–55 |
| Large | 110–160 m sq | 3–5 | 55–90 |

Room sizes: closet 2×3, bathroom 3×3, small office 3×4, bedroom/security 4×5,
kitchen 5×7, classroom 6×8, medium lobby 8×10, atrium 12×16, objective room
6×8, **objective room pair 12×16**, garage/warehouse 14×20, roof 20×30,
outdoor staging strip 8–20 m deep.

Layout targets: 2–4 exterior entry sides, 6–12 breach/entry points, 2–4
stairs/vertical routes, 2–3 defender rotation loops, 2–4 soft walls near the
objective, 2–4 floor/ceiling pressure points, 3–5 defender anchors, 3–5
attacker lanes. **Design around objective *clusters*** (two ~6×8 rooms + a
2×4 connector, ~20×25 m footprint, ~8 m of vertical control) rather than one
giant objective room.

### heist (crew objective box)

Smaller than a route map but dense and reusable — players loop through the
same spaces completing objectives, moving loot, and escaping. **Best first
canvas: 128 × 128 m.**

| Size | Footprint | Floors | Vertical | Route |
|---|---|---|---|---|
| Small | 40–80 m sq | 1–2 | 0–8 m | 150–350 m |
| Medium | 80–140 m sq | 2–4 | 0–15 m | 300–700 m |
| Large | 150–250 m sq | 3–6 | 0–25 m | 700 m–1.5 km |

Room sizes: small office 3×4, manager office 5×6, security 4×5, storage 5×8,
small lobby 8×10, main lobby 15×25, vault 8×12, large vault 12×20, parking
30×50, escape/extraction 10×15. A good heist has: casing/entry area, public
area, restricted staff area, security room, objective room, loot/vault/stash,
a bag-movement route, a secondary route, responder entry points, a holdout
area, and an escape route.

### co-op route (forward survival path)

Not a separate Deli Counter mode, but buildable with the same primitives: a
forward-moving journey through connected spaces. **Best first canvas:
256 × 256 m.** The core question is route *length*, not objective density.

| Type | Path length | Footprint |
|---|---|---|
| Tight interior | 200–400 m | 80 × 150 m |
| Street / neighborhood | 400–800 m | 150 × 300 m |
| Finale / arena | 100–300 m path | 50–100 m sq arena |

Spaces: hallway min 2 m, 4-player hallway 3–4 m, combat hallway 4–6 m, small
room 5×5, medium 10×12, large combat 20×30, alley 3–5 m, residential street
8–12 m, big street 14–20 m.

## Recommended first prototype

For a first production-ready level that exercises verticality, doors,
interiors, combat spaces, and tactical routing, start with an **assault**
canvas:

| Attribute | Target |
|---|---|
| Canvas | 96 × 96 m |
| Main building | 60 × 60 m |
| Floors | 3 |
| Vertical range | 12–16 m |
| Outdoor ring | 10–15 m |
| Interior spaces | 30–45 |
| Objective clusters | 3 |
| Stairs | 2 primary + 1 secondary |
| Exterior entry points | 8–12 |
| Soft-wall panels | 20–40 |
| Soft floor/ceiling zones | 8–16 |
| Players | 4 (scalable to 5v5) |

## Acceptance criteria

A blockout is ready for testing when it meets the bar Deli Counter's validator
already enforces and a few things you confirm in-engine:

- Meter scale; player capsule fits all intended paths.
- **Every floor has at least two meaningful routes.**
- **Objective spaces have both attack and defense options.**
- Doors, windows, stairs, and vertical routes placed intentionally with
  consistent dimensions.
- Playable in greybox without decoration; clear bounds without relying on
  invisible walls.
- Navmesh builds across floors; AI reaches objective/combat zones from spawns;
  multiplayer spawns valid; stable framerate in greybox.

The kit's `validate.py` checks the structural half of this (routes per floor,
objective access paths, reachability, opening widths); the in-engine half
(navmesh, AI, framerate) is the Godot-side check.
