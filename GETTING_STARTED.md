# Getting started — zero to a level you can walk

The five-minute path. Assumes Blender 4.x and Godot 4.x installed.

## 1. One-time setup

```
pip install jsonschema        # full spec validation (recommended)
python install_hooks.py       # pre-commit hook: auto-refreshes the catalog + gate
```

## 2. Generate a level (no JSON to write)

```
python new_level.py --list                              # see the preset recipes
python new_level.py --preset corner_deli --name my_lvl  # -> specs/my_lvl.json
```

Presets available: **bank**, **police_station**, **corner_deli**, **compound**.
Common flags: `--mode heist|assault`, `--floors N`, `--no-basement`,
`--scale-ref` (drops 1.8 m human proxies for a scale check).

## 3. Build the GLB (Blender)

The tool's core job: turn the spec into a Godot-ready `.glb` with collision and
gameplay markers baked in.

**Headless (if Blender is on PATH):**
```
python build.py specs/my_lvl.json        # -> build/my_lvl.glb + my_lvl.gameplay.json
```

**Manual (GUI):** open `_run_in_blender.py` in Blender's Scripting workspace,
set the CONFIG block (lines 26-28) to absolute paths, and Run Script:
```python
SPEC_PATH = r"C:\deli_counter\specs\my_lvl.json"
PKG_DIR   = r"C:\deli_counter"
OUT_PATH  = r"C:\deli_counter\build\my_lvl.glb"
```
> After unzipping a new version, **restart Blender** before rebuilding — it
> caches old modules and will otherwise run stale code.

You get two files in `build/`: the `.glb` (geometry + collision + marker
empties) and a `.gameplay.json` (the same markers as data — spawns, objectives,
loot, acoustic surfaces).

## 4. Into Godot — walk it

**Plugin path (fewest clicks):**
1. Copy `godot/addon/deli_counter/` into your project at
   `res://addons/deli_counter/` (one folder; `plugin.cfg` must sit directly in
   it, not nested).
2. **Project -> Project Settings -> Plugins** -> enable **Deli Counter**.
3. Drag both `my_lvl.glb` and `my_lvl.gameplay.json` into the project (keep them
   together, e.g. `res://levels/`).
4. In the **Deli Counter** dock: **Pick level .glb...** -> **Set up & Play >**.
   It assigns the import hook, builds a walkable test scene, and runs it.

**Manual path (always works):** set the `.glb`'s Import Script to
`res://addons/deli_counter/deli_counter_postimport.gd`, Reimport, open
`addons/deli_counter/template/level_test.tscn`, drag the `.glb` in as a child,
press F6. See `godot/IMPORT_GUIDE.md`.

Controls in the harness: WASD move, mouse look, Shift sprint, Space jump,
Esc free mouse, R respawn, F1 HUD, F4 bake navmesh.

## What the tool does and doesn't do

- **Does:** monolithic buildings on flat ground — walls, partitions, openings,
  stairs/ladders/ramps, slab holes, collision, gameplay markers, acoustic
  materials, kitbashed props. This is the proven core: it produces valid
  Godot-ready GLBs.
- **Doesn't (yet):** outdoor terrain, roads, parking lots, or multiple separate
  structures in open space. Those levels are hand-built in Blender for now.

## Next steps

- Hand-edit the generated JSON to customize — it matches `schema/level.schema.json`
  (the `$schema` key gives editor autocomplete).
- Full reference: **README.md**. Godot specifics: **godot/README.md**.
- Walk a rich level end-to-end with **godot/WALKTHROUGH_corner_deli.md**.
