# Light Manifest Contract (`<name>.lights.json`)

The lighting companion to `.gameplay.json` and `.slots.json`. Deli Counter
emits **where a light belongs and what kind it is**; the renderer ([Lux](https://github.com/siliconight/lux))
decides how it looks. Same philosophy as the rest of the kit: bake the static
shell, emit the placement as typed anchors. Output-only — no `level.schema.json`
change; derived lights need zero authoring.

## File

```json
{
  "light_manifest_version": "1.2.0",
  "building_id": "gs_auto_shop",
  "theme": "delco",
  "space": "Blender Z-up, meters; rot_y = degrees about up; pos is the fixture location",
  "rig_library": "lux",
  "anchors": [ ... ]
}
```

## Anchor

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique, human-readable (`<room-or-wall>_<what>`). |
| `type` | yes | `fluorescent` \| `pendant` \| `streetlight` \| `window` \| `sign` \| `wall_pack` \| `sun`, the (v1.2) club set `club_wash` \| `stage_light` \| `neon` \| `room_ambient`, and (v1.3) the forecourt pair `canopy_lights` \| `canopy_wash`. Named after the real fixture; maps 1:1 to a Lux rig — and, for the hardware types, 1:1 to a Zoo fixture species (`zoo --fixtures`), which bakes the visible hardware at the same anchors. The club set bakes no hardware: the neon's glass and the stage's rope light are the prop's own (Zoo 0.88.0). |
| `source` | yes | `derived` (auto) or `authored` (spec-placed). |
| `pos` | yes | `[x, y, z]` — the fixture's actual location, at mount height. |
| `rot_y` | yes | Degrees about up — row axis, or a window's inward facing. |
| `room` | interior | The `gameplay.json` room id this light lights. |
| `row` | rows | `{count, spacing}` for repeated fixtures. |
| `size` | area lights | `[width, depth]` for `canopy_lights` (the whole deck, which is the Zoo species' dimensions) and for `canopy_wash` (the pool that wash owns); `[width, height]` for `window`/`sign`/`neon` panels; `[x, y, z]` for `room_ambient` — the room's wall-centreline box, floor to ceiling plane, centred on `pos`. |
| `drop` | interior | Metres from the anchor down to its room's floor (ceiling types, the club set). For the canopy pair it is the soffit down to GRADE, derived from the foot of the canopy's own columns rather than assumed to be zero. |
| `color` | club set | A name from Lux's palette: `magenta` `hot_pink` `red` `violet` `blue` `cyan` `amber`. Lux REFUSES an unknown name (not built, warned), never substitutes. `null` on a `room_ambient` means "the preset's own ambient, no tint" — Lux 0.37.0 refuses that too, which is the right outcome for an office until its per-room ambient lands. Absent on a `neon` at a sign: Lux picks by anchor id; `cyan` or `blue` on a TV's screen. |
| `target` | `stage_light` | `[x, y, z]` the spots are aimed at, same frame as `pos`. Required by Lux. |
| `radius` | `club_wash`, `stage_light` | Floor pool radius (wash) or the lit radius at the target (spot), metres. |
| `cycle_s` | `stage_light` | Seconds per colour as the spots step through the palette; 0 holds. |
| `reacts_to_alarm` | yes | Whether Lux drives it on mission phase / alarm pulse. |

## What Deli Counter derives

- **One `fluorescent` row per room** — at the room center, mounted just below
  the ceiling (`center.z + story_height`), running along the room's longer
  axis, fixture count scaled to the room's length. `reacts_to_alarm: true`.
  The row is split into runs around the ceiling voids (stairwells, hatches)
  and stepped off the partitions: a lamp that would hang inside a wall is
  nudged along the row to 0.40 m off the centreline (its own run), one
  with nowhere to go is dropped, and a row lying along a partition moves to
  the larger side of it (DC 0.116.0, roadmap 143).
- **One `window` area light per window opening** — at the opening center, sized
  to the opening, facing inward (from the wall's N/S/E/W suffix).
  `reacts_to_alarm: false`.
- **One `sign` per building (v1.1)** — above the widest door on the facade
  with the most windows (the storefront); no exterior windows, no derived
  sign. `pos` is the sign's FACE plane, 0.2 m proud of the wall, facing
  outward; `size` is the panel. `reacts_to_alarm: true` (building power).
- **One `wall_pack` per remaining exterior door (v1.1)** — doors and garage
  rollups, any story; the sign's door is skipped (the cabinet occupies it).
  `pos` sits 0.15 m proud of the wall and 0.25 m above the door head — in
  free air under the wedge, so Lux's downward spot is never inside the
  hardware Zoo bakes. `reacts_to_alarm: true`.

- **One `room_ambient` per room (v1.2)** — every room, every kind: `pos` the
  room's centre at mid-height, `size` its wall-centreline box from the floor
  to the ceiling plane (`[x, y, z]`, Deli Counter axes). Lux is moving to
  per-room ambient probes; this is the box it asked for. `color` is a
  palette name in a club room and `null` elsewhere. `reacts_to_alarm: false`.
- **The club set instead of a ceiling row (v1.2)**, in a strip club's club
  rooms (`level_design.is_strip_club_room`: a `strip_club` building's
  `main_floor`, `*_bar`, `vip_*`, `champagne_*`, `lounge`, `cabaret`...):
  - `club_wash` × 3–5 (`3 + area/200`, to 5), laid along the room's long
    axis and stepping side to side across the short one, each its own
    palette colour from `crc32(room) % 7` in steps of two; each point takes
    the same void-and-partition test a fluorescent lamp does. `radius` is
    the short side / 3, held to 1.5–6 m.
  - `stage_light` per stage volume: two spots (`row` 2 × 1.2 m) at the
    ceiling 1.5 m past the stage's edge on the room-centre side, `target`
    the stage centre 0.5 m above its platform (0.8 m; a `bar_stage` deck
    1.18 m), `cycle_s` 4.
  - `neon` at the stage's rope light: over a bar stage's deck 0.5 m off the
    pole and 0.35 m above the deck, or 0.25 m past a round stage's lip at
    0.75 m; `amber`. And one `neon` proud of each `neon_sign` volume's FACE
    by 0.15 m (in free air, never inside the cabinet), `rot_y` the sign's
    facing, `size` the sign's; no `color` (Lux picks by id; the glass's own
    colour is Zoo's, per name).
  - the `room_ambient` above, coloured.
  - no `fluorescent` and no `pendant`. The walker: "dark with colored
    lights". What still keeps a club room from reading dark — the preset's
    unshadowed sun, the environment's ambient share, depth fog — is
    measured in Lux 0.37.0 and is the preset's to change.

- **A `neon` in front of every TV that is on (DC 0.135.0, Zoo 0.90.0)** —
  in any room, club or not: every visible volume that routes to Zoo's
  `crt_tv` (`wall_tv`, `bar_tv`) with `form` `bracket`, the set Zoo lights
  with a ballgame. `id` `<volume name>_screen`; `pos` 0.25 m in front of the
  slot's front face along its facing, in free air, at the screen's height
  (the volume's centre + 0.036 m, measured off Zoo's plan); `rot_y` the
  facing; `size` the lit 4:3 face (`lights.tv_screen_size`, Zoo's
  `crt_forms.screen_size` mirrored: 0.395 × 0.297 m at the club's 0.6 m set,
  0.445 × 0.334 at 0.7 m), so Lux's neon range is 1.20–1.22 m; `color`
  `cyan` or `blue` by `crc32(id) % 2`; `drop` from the anchor to the floor.
  A `stand` set is off and gets none. In a club room it follows the club
  set; elsewhere it follows the room's ceiling light — the room's box stays
  its last anchor.

Emitters proud of the wall is the v1.1 contract with Zoo's fixture pass:
`pos` is always the EMITTER; hardware hangs around it (sign cabinet behind
the face plane, wall-pack body above the emitter, back to the wall).

Exterior lights (`streetlight`) are added by **Lot** at the site level. The
`sun` is owned by Lux's preset / SkyMint.

## The forecourt pair (v1.3)

A fuel canopy is an exterior deck on columns and it is the light source for the
tarmac under it: in every period reference the forecourt is lit by the canopy
and not by street lighting. Until v1.3 nothing derived a light from one.
Measured on cold run 9080's package -- a 22 x 13 m canopy on six columns, and
all 20 Lux fixture holders within 45 m sitting on the shop between world
x 58.7 and 81.3 while the canopy spanned 81 to 103.

It is deliberately TWO kinds, and the split is a performance decision:

| type | what it is | who builds it |
|---|---|---|
| `canopy_lights` | one anchor for the whole deck, `size` = its footprint | Zoo's `canopy_lights` species lays the lamp grid inside it, in two draw calls, and carries NO emitter marker |
| `canopy_wash` | two to four light positions under the deck, no hardware | Lux, from the manifest, the way `club_wash` is |

`max_lights_per_object` is 8 on GL Compatibility, and a literal 12-20 fixture
grid would put every one of those lights on the forecourt ground mesh -- the
surface that fills the frame when a player stands under it. So the lamps a
player SEES are emissive geometry that lights nothing, and the light they
appear to cast is a handful of washes. The walker's call, 2026-09-26, with the
three options and their costs put in front of them.

A building with no `canopy_roof` volume emits neither, which is every building
that is not a fuel stop.

## Authored overrides

A spec may set an optional `lights` list of explicit anchors (same shape). An
authored anchor replaces a derived one with the same `id` — auto defaults plus
hand-placed overrides, exactly like props. Absent by default, so existing specs
are unaffected.
