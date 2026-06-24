# Importing a Deli Counter level into Godot 4

This is the first time a generated level meets the engine, so it's written as a
checklist with verification points. Do them in order; each checkpoint tells you
what "working" looks like before you move on.

## 0. Produce the GLB (in Blender, on your machine)

You've already confirmed the build runs. Either:

- **Headless:** `python build.py specs/stop_n_go.json` → writes
  `build/stop_n_go.glb` **and** `build/stop_n_go.gameplay.json`, or
- **Manual:** in `_run_in_blender.py` set `OUT_PATH` to
  `r"C:\deli_counter\build\stop_n_go.glb"` and Run Script.

**Checkpoint 0:** both `stop_n_go.glb` and `stop_n_go.gameplay.json` exist in
`build/`. The companion JSON must travel with the GLB — the import script reads
it for marker metadata.

## 1. Put the files in your Godot project

Copy **both** files into your project, in the same folder, e.g.:

```
res://levels/stop_n_go.glb
res://levels/stop_n_go.gameplay.json
```

Also copy the addon scripts once:

```
res://addons/deli_counter/deli_counter_postimport.gd
res://addons/deli_counter/deli_level.gd
```

**Checkpoint 1:** Godot's FileSystem dock shows the `.glb` with a small scene
icon and no import error badge. If it shows an error, open the Import dock and
read it — usually a missing companion file or a path typo.

## 2. First import — geometry and collision only

Click the `.glb` in the FileSystem dock, then the **Import** tab (next to
Scene, top-right). Leave the import script unset for now. Click **Reimport**.

Double-click the `.glb` to open it (or right-click → New Inherited Scene).

**Checkpoint 2 — this is the big one.** You should see:
- The building geometry (the VISUAL meshes).
- Under it, `StaticBody3D` nodes with `CollisionShape3D` children — these came
  from the `-convcolonly` / `-colonly` suffixes the kit baked. **This is the
  proof the collision pipeline works end to end.** If you see collision shapes,
  the core promise of the tool is real.
- The marker empties (`ATTACKER_SPAWN_A`, `OBJECTIVE_A`, etc.) as plain
  `Node3D`s — not converted yet, that's step 3.

If there are **no** collision shapes: the glTF importer didn't honor the
suffixes. Check that the COLLISION objects kept their `-convcolonly` names
through export (open the GLB's node list). This is the most likely thing to
need a fix — tell me and I'll adjust the suffix handling.

## 3. Second import — run the marker conversion script

Select the `.glb` → **Import** tab → set **Import Script** to
`res://addons/deli_counter/deli_counter_postimport.gd` → **Reimport**.

Watch the Output panel. You should see:
`[deli_counter] post-import: converted N marker node(s)`

**Checkpoint 3:** open the scene again. The marker empties are now `Marker3D`
nodes in gameplay groups. Verify with a quick script in any scene:

```gdscript
func _ready() -> void:
    print(get_tree().get_nodes_in_group("attacker_spawn"))
    print(get_tree().get_nodes_in_group("objective"))
```

If those arrays are populated, the gameplay layer survived import. If the
converted nodes are **missing** after reimport (the known Godot owner gotcha),
that's the bug the script's `_set_owner_recursive` is meant to prevent — tell
me and I'll dig in.

## 4. Drop it in a level scene

Create a scene (e.g. `Main.tscn`) and instance the imported `.glb` as a child.
Add a `DirectionalLight3D`, a `WorldEnvironment`, and a player/camera. Walk
into it. Collision should stop you at the walls; you should fit through the
doorways (they're 2.2 m; you're ~1.8 m).

**Checkpoint 4:** you can walk the level, collision holds, doorways clear.
That's a playable greybox.

## What's verified vs. not

- **Verified by you reaching Checkpoint 2–4:** the export → import → collision →
  marker pipeline. That's the whole reason the tool exists.
- **Not yet built:** a ready-made level scene template (player controller,
  lighting, navmesh bake, debug collision view). That's the natural next piece
  once this import is confirmed — it shouldn't be built against an unproven
  import, which is why it's deferred until you've done step 4.

## Acoustic surfaces (gool)

If the spec defined materials, `stop_n_go.gameplay.json` has a `surfaces` array
mapping collision-node names to acoustic materials. See `README.md` here for
the `material_for_node` autoload pattern that feeds gool's
`IAudioGeometryQuery`. That's independent of the steps above — it reads the
same JSON. (Optional — omit materials or build with `--no-audio` and there's
nothing to wire.)

## Import-step audit — what's automated vs. manual

A quick honest inventory of every step in the spec → walkable loop, so nothing
stays tribal knowledge:

| Step | Status |
|------|--------|
| Collision bodies (StaticBody3D + shapes from `-convcolonly`/`-colonly`) | **Automatic** — Godot's glTF importer, with "Use Name/Node Type Suffixes" on (default). No action. |
| Marker conversion (empties → grouped Node3D, transforms preserved) | **Automatic** — `deli_counter_postimport.gd`, assigned as the .glb's Import Script (the plugin's "Assign import script" / Set up & Play does this). |
| Marker-snap-to-origin bug (global_transform during tree mutation) | **Fixed in postimport** (captures transforms before mutating). No action. |
| Stair slab-hole sizing (player stuck near top) | **Fixed in the builder** (hole extends past the top landing). No action. |
| Assigning the import script + reimport | **One-time setup**, automated by the plugin. Manual only if you import by hand (set Import Script on the .glb, Reimport). |
| `OUT_PATH` in `_run_in_blender.py` (GUI Blender path only) | **Manual config**, only when building via the Blender GUI instead of `build.py`. `build.py` handles paths itself. |
| UID load error after dropping in a new .glb | **Occasional manual:** if Godot shows a UID/load error on a freshly-replaced .glb, **Project → Reload Current Project** clears it. This is a Godot resource-cache quirk, not a Deli Counter step — the "↻ Rebuild last level" dock button's `scan()` + `reimport_files()` avoids it in the normal loop. |

Net: in the normal plugin loop (Pick → Set up & Play, then **↻ Rebuild last
level** after each spec edit) there are **no manual steps**. The only manual
touch is the rare UID-cache reload, and that's a Godot quirk with a one-click
menu fix, now documented rather than tribal.

## Fast iteration loop

Once a level is imported once:

1. `python build.py specs/<name>.json --watch` in a terminal — rebuilds the
   `.glb` every time you save the spec (stdlib polling, no extra deps).
2. Edit the spec, save. The `.glb` regenerates; Godot auto-reimports it.
3. Hit **↻ Rebuild last level** in the dock — reimports the fresh geometry and
   replays, no file picker. Spec-edit to playtest in one click.

