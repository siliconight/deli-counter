# Light Manifest Contract (`<name>.lights.json`)

The lighting companion to `.gameplay.json` and `.slots.json`. Deli Counter
emits **where a light belongs and what kind it is**; the renderer ([Lux](https://github.com/siliconight/lux))
decides how it looks. Same philosophy as the rest of the kit: bake the static
shell, emit the placement as typed anchors. Output-only — no `level.schema.json`
change; derived lights need zero authoring.

## File

```json
{
  "light_manifest_version": "1.0.0",
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
| `type` | yes | `fluorescent` \| `streetlight` \| `window` \| `sign` \| `sun`. Named after the real fixture; maps 1:1 to a Lux rig. |
| `source` | yes | `derived` (auto) or `authored` (spec-placed). |
| `pos` | yes | `[x, y, z]` — the fixture's actual location, at mount height. |
| `rot_y` | yes | Degrees about up — row axis, or a window's inward facing. |
| `room` | interior | The `gameplay.json` room id this light lights. |
| `row` | rows | `{count, spacing}` for repeated fixtures. |
| `size` | area lights | `[width, height]` for `window`/`sign` panels. |
| `reacts_to_alarm` | yes | Whether Lux drives it on mission phase / alarm pulse. |

## What Deli Counter derives

- **One `fluorescent` row per room** — at the room center, mounted just below
  the ceiling (`center.z + story_height`), running along the room's longer
  axis, fixture count scaled to the room's length. `reacts_to_alarm: true`.
- **One `window` area light per window opening** — at the opening center, sized
  to the opening, facing inward (from the wall's N/S/E/W suffix).
  `reacts_to_alarm: false`.

Exterior lights (`streetlight`) are added by **Lot** at the site level. The
`sun` is owned by Lux's preset / SkyMint.

## Authored overrides

A spec may set an optional `lights` list of explicit anchors (same shape). An
authored anchor replaces a derived one with the same `id` — auto defaults plus
hand-placed overrides, exactly like props. Absent by default, so existing specs
are unaffected.
