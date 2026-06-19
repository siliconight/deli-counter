# Godot integration

Turns a Deli Counter `.glb` into a playable level: collision is already wired
by the glTF importer (via the `-convcolonly` / `-colonly` suffixes), and these
scripts convert the baked marker nodes into game nodes.

## Files

- `deli_counter_postimport.gd` — an `EditorScenePostImport` hook. Runs at
  import time and rewrites the scene tree: marker empties become `Marker3D`
  nodes in gameplay groups (or instances of your own scenes), breach panels
  get tagged with metadata.
- `deli_level.gd` — a runtime helper (`class_name DeliLevel`) to query the
  level from game code (find spawns, objectives, cover; breach a panel).

## Install

1. Copy this folder into your Godot project, e.g.
   `res://addons/deli_counter/`.
2. Put the built `.glb` (and its `<name>.gameplay.json`, if generated) into
   the project, e.g. `res://levels/`.

## Wire up the import hook

1. Select the `.glb` in the FileSystem dock.
2. Go to the **Import** tab.
3. Set **Import Script** to
   `res://addons/deli_counter/deli_counter_postimport.gd`.
4. Click **Reimport**.

On reimport you'll see in the Output panel:
`[deli_counter] post-import: converted N marker node(s)`.

The companion `<name>.gameplay.json` is read automatically if it sits next to
the `.glb` (same basename) — its per-marker metadata is attached to the
matching nodes via `set_meta`.

## What the markers become

| Baked node prefix | Becomes | Group |
|---|---|---|
| `ATTACKER_SPAWN_*` | Marker3D | `attacker_spawn` |
| `DEFENDER_SPAWN*` | Marker3D | `defender_spawn` |
| `OBJECTIVE_*` | Marker3D (or your scene) | `objective` |
| `CAMERA_SOCKET_*` | Marker3D (or your scene) | `camera_socket` |
| `DOOR_SOCKET_*` | Marker3D (or your scene) | `door_socket` |
| `BREACH_PANEL_*` | kept StaticBody3D, tagged | `breach_panel` |
| `HATCH_*` | Marker3D | `hatch` |
| `NAV_REGION_*` | Marker3D (room center) | `nav_region` |
| `COVER_LOW_* / COVER_HIGH_*` | Marker3D | `ai_cover` |

Collision meshes (the `COLLISION` set) are left untouched — the glTF importer
already builds their `StaticBody3D` + shapes from the name suffixes.

## Instance your own scenes

Edit `SCENE_FOR_TAG` at the top of `deli_counter_postimport.gd` to swap in
project scenes instead of plain markers, e.g.:

```gdscript
const SCENE_FOR_TAG := {
    "door_socket": "res://scenes/props/Door.tscn",
    "objective":   "res://scenes/gameplay/Objective.tscn",
    "camera_socket": "",
}
```

Each instanced scene is placed at the marker's transform and added to the
group, with the gameplay metadata attached.

## Use it at runtime

```gdscript
func _ready() -> void:
    var spawns := DeliLevel.attacker_spawns(get_tree())
    var objs   := DeliLevel.objectives(get_tree())
    for panel in DeliLevel.breach_panels(get_tree()):
        var info := DeliLevel.meta_of(panel)   # {breach_class, material, ...}
        print(panel.name, info)

# later, when a player breaches a soft wall:
func _on_charge_detonated(panel: Node) -> void:
    var debris := preload("res://vfx/BreachDebris.tscn")
    var at := DeliLevel.breach(panel, debris)   # frees the panel, spawns VFX
```

## Notes

- These scripts target Godot 4.x. `EditorScenePostImport` and the glTF
  collision-suffix convention are both Godot 4 features.
- Verify behavior at runtime, not just by reading: reimport the `.glb`, load
  the level scene, and confirm the groups populate (`get_tree()
  .get_nodes_in_group("attacker_spawn")`). GDScript can't be checked outside
  the engine, so an in-editor reimport + a quick play test is the real test.

## Acoustic surfaces (gool bridge)

If a spec defines a `materials` palette, the `<name>.gameplay.json` carries a
`surfaces` array mapping each collision-node name to an acoustic material:

```json
"surfaces": [
  { "node": "int_col_0_0", "material": { "id": "drywall", "acoustic": "Drywall" } },
  { "node": "ext_col_0_N", "material": { "id": "brick_ext", "acoustic": "Concrete",
                                          "absorption": 0.7, "damping": 0.6 } }
]
```

In your `IAudioGeometryQuery::RaycastAudioOcclusion` implementation, take the
collision body you hit, read its node name, look it up in this map, and return
the corresponding `AudioMaterial` (the `acoustic` field maps directly to
gool's enum) or the explicit `absorption`/`damping` values. That way one
material tag in the spec drives the level's acoustics without hand-authoring
per-wall audio data in the engine.

A small autoload that loads the json once and exposes
`material_for_node(name)` is the usual pattern; the names match the collision
bodies the glTF importer creates from Deli Counter's `-convcolonly` nodes.
