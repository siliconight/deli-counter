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

## Stairs and player traversal

Deli Counter generates stairs as a run of individual step boxes (visual +
collision), with the step count derived from floor height. Godot's
`CharacterBody3D` has **no built-in stair-stepping** — a character walks into a
flat run of steps and stops dead unless the controller explicitly handles it.
This matters for the tool because a level can be geometrically perfect and
still feel un-walkable if the player controller doesn't step up.

### Step rise is well under any sane step-up budget

The builder targets `step_rise` (default 0.2 m) and rounds to an integer step
count, so the **actual rise per step lands around 0.18 m** across the floor
heights the presets use (3.3–3.8 m → ~0.18 m/step). That's comfortably under
the common step-up budgets:

| Budget (`MAX_STEP_UP`) | Our actual rise | Margin |
|---|---|---|
| 0.5 m (community-standard demo default) | ~0.18 m | ~0.32 m slack |
| 0.4 m (this repo's harness default) | ~0.18 m | ~0.22 m slack |

So any reasonable step-up algorithm clears our generated stairs easily. The
only way to exceed the budget is to hand-author a spec with a large explicit
`step_rise` or a tiny explicit `n_steps` — if you do that, keep the resulting
rise under your controller's `MAX_STEP_UP`, or no algorithm will save you.
**Recommended budget: 0.5 m.**

### Two ways to do the player stair-stepping

The harness `template/player.gd` ships a lightweight raycast-probe step-up so
the test player can climb generated stairs out of the box. It's adequate for
walk-testing. For your **production** controller, the more robust and
community-favored technique is a `body_test_motion` step-up — it tests the
whole collider (forward → up by `MAX_STEP_UP` → forward by the remainder →
back down onto the step) and checks the step's surface normal against
`floor_max_angle` so it won't climb a slope it shouldn't. Two well-known
references:

- **Separation-ray approach** — add a `SeparationRayShape3D` to the player,
  positioned forward and dropping from your max step height to the floor. The
  simplest method; some find it inconsistent in practice.
- **`stair_step_up()` from the Godot Stair-Step Demo**
  (`godotengine.org/asset-library/asset/2481`, MIT; credits Majikayo Games and
  Myria666's Quake-movement doc) — the body-test method above. Copy its
  `stair_step_up()` / `stair_step_down()` into your character script.

Deli Counter doesn't ship or mandate a production controller — it generates
the static stair geometry; your game owns the character. The harness player is
a test rig, not a shipping character.

### Physics-engine note (Jolt vs default)

The stair-step demo recommends **Jolt Physics** over Godot's default physics,
and the reason is relevant to walk-testing generated levels: default Godot
physics can (1) block a character from passing through small gaps that should
fit, and (2) push the character down slightly when walking into some objects,
which causes jitter and can make a *flat floor* get mis-detected as a step.
That second one can make a correctly-generated level feel subtly broken in a
way that looks like a geometry bug but isn't. If a level feels jittery or
"sticky" underfoot during a walk test, try switching the project to Jolt
before suspecting the geometry. This is a project/physics choice your game
makes — the tool doesn't depend on either backend.

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
