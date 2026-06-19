<p align="center">
  <img src="assets/branding/logo.png" alt="Deli Counter" width="480">
</p>

# Deli Counter — a Blender level kit for Godot 4

_Stack a level like a sandwich: layer the parts, serve the whole._

Spec-driven Blender level generator. You describe a building as a JSON
spec; the kit builds a monolithic compound in Blender 4.x with a separate
collision proxy and exports it for your game. Levels can also **kitbash** from
existing models — layering imported assets into the generated shell.

```
prompt  ->  specs/<name>.json  ->  build.py  ->  build/<name>.{glb,obj,gltf}  ->  Godot
```

The whole thing is designed to live in source control and stay
self-documenting as the level set grows toward real game models.

## Layout

```
deli_counter/
  deli_counter.py     core builder (needs Blender's bpy)
  spec_types.py       spec dataclasses (pure Python, no bpy)
  spec_loader.py      JSON/YAML -> LevelSpec
  version.py          KIT_VERSION / SCHEMA_VERSION (stamped into manifests)
  build.py            CLI: drives Blender headless        (normal Python)
  validate.py         check a spec without Blender         (normal Python)
  catalog.py          generate specs/CATALOG.md            (normal Python)
  check.py            validate + catalog gate for CI       (normal Python)
  _run_in_blender.py  executed inside Blender by build.py
  schema/
    level.schema.json JSON Schema (editor autocomplete + validation)
  specs/
    bank.json         worked example: 2-story bank + basement vault
    warehouse.json    worked example: single tall warehouse
    CATALOG.md        auto-generated level index (do not hand-edit)
  build/              outputs (binaries gitignored, manifests tracked)
  README.md  CHANGELOG.md  .gitignore
```

## Export formats

| Format | Ext | Use | In source control |
|---|---|---|---|
| glTF binary | `.glb` | Engine-ready. Godot reads collision tags on import. Single file. | gitignored (regenerable) |
| glTF separate | `.gltf` + `.bin` + textures | Web / AR/VR, more granular | gitignored |
| Wavefront OBJ | `.obj` + `.mtl` | Static archival; text, diffs well | gitignored |

Pick one or several:

```
python build.py specs/bank.json                 # glb (default)
python build.py specs/bank.json -f glb,obj      # both
python build.py specs/bank.json -f gltf
python build.py --all -f glb,obj                # every spec, both formats
```

**OBJ caveat:** OBJ has no node-name convention, so Godot's OBJ importer
ignores the `-colonly` collision tags. Use **GLB for the Godot pipeline**
(collision wired automatically) and OBJ as the static/interchange/archival
format. Both come from the same build.

## One-time setup

- Blender 4.x. The CLI finds it via `--blender`, `$BLENDER`, or `PATH`.
- Optional: `pip install jsonschema` (full validation), `pip install pyyaml`
  (YAML specs).

## The build commands

```
python validate.py specs/bank.json    # fast check, no Blender
python build.py specs/bank.json        # -> build/bank.glb (+ manifest)
python build.py --all -f glb,obj       # rebuild everything, two formats
```

### Manual fallback (GUI)

1. Blender 4.x -> Scripting workspace.
2. Open `_run_in_blender.py`, set `SPEC_PATH` (and `OUT_PATH`) to absolute
   paths, Alt+P.

## Source-control workflow

The repo is the source of truth; built models are regenerable artifacts.

**Tracked:** all `.py`, `schema/`, `specs/*.json`, `specs/CATALOG.md`,
`CHANGELOG.md`, and `build/*.manifest.json`.

**Ignored:** `build/*.glb|gltf|obj|mtl|bin` — regenerate with `build.py`.
(To ship a frozen release model, whitelist it explicitly in `.gitignore`.)

**Every build writes a manifest** (`build/<name>.manifest.json`) recording
kit version, schema version, a spec content hash, timestamp, and the formats
produced. So any model is traceable to the exact spec + kit version that
made it — even though the binary itself isn't committed.

**Before committing a spec change**, run the gate:

```
python catalog.py     # refresh CATALOG.md
python check.py        # validate all specs + confirm catalog is current
```

`check.py` exits non-zero on failure, so it drops straight into a pre-commit
hook or CI job. Neither needs Blender.

### Versioning

`version.py` holds `KIT_VERSION`. Bump it when builder output changes, record
the change in `CHANGELOG.md`. Convention: MAJOR = schema break, MINOR = new
feature (old specs unchanged), PATCH = geometry fix.

## Import into Godot 4

Drop the `.glb` into the project. The importer reads collision suffixes:

- `-convcolonly` -> `StaticBody3D` + `ConvexPolygonShape3D`
- `-colonly`     -> `StaticBody3D` + `ConcavePolygonShape3D` (trimesh)

`VISUAL` meshes import with no collision. `breach` openings produce a tagged
`*_BREACHPANEL` (visual + collision) to swap for a destructible body.

## Writing a spec

JSON matching `schema/level.schema.json`. The `$schema` key in each example
gives editor autocomplete. Coordinates: origin at building center,
ground-floor slab top at `z=0`, `+X` east, `+Y` north, `+Z` up, meters.

Top-level: `name`, `seed`, `grid`, `footprint_x/y`, `story_height`,
`n_stories`, `has_basement`, `wall_thick`, `floor_thick`, `collision`,
`auto_exterior`.

Features: `ext_walls` (+ `openings`: door/window/garage/breach),
`partitions`, `stairs` (auto-cut slab holes), `slab_holes`, `volumes`
(vaults/counters/cover/mezzanines), `parapets`. Same spec + same `seed`
always builds the same level. See `specs/CATALOG.md` for what's in each level.

## Kitbashing — composing levels from existing models

Levels aren't limited to generated primitives. A spec can pull in external
model assets and place instances of them, baked into the monolithic level
alongside the generated geometry.

Two spec sections:

- **`assets`** — a library of source models, each with a stable `id`:
  ```json
  { "id": "crate", "file": "props/crate.obj", "fmt": "obj", "collision": "convex" }
  ```
- **`placements`** — instances referencing an asset `id`, with transform:
  ```json
  { "asset": "crate", "x": -6, "y": -4, "z": 0, "rot_z": 15, "scale": 1.5 }
  ```

Multiple placements can reuse one asset id. Asset files are **vendored under
`assets/`** and committed — see `assets/README.md`. Formats: `.glb`
(preferred), `.obj` (+ `.mtl`), `.blend` (appended; set `blend_object` to
pick one object).

**Collision for imported models** is the key choice. Each asset declares a
default strategy; a placement can override it:

- `convex` (default) — auto convex hull. Fast, one shape. Best for most props.
- `box` — axis-aligned bounding box. Cheapest.
- `file` — a separate low-poly mesh (`collision_file`). For concave shapes a
  hull can't capture.
- `trimesh` — the asset mesh itself, concave. Static, costly.
- `none` — visual only.

Imported collision gets the same `-convcolonly` / `-colonly` tags as
generated geometry, so Godot wires it up on GLB import. `validate.py` checks
every placement points at a defined asset and that vendored files exist —
before Blender ever launches. See `specs/kitbash_demo.json` for a worked
example.

## Iterating toward real models

1. Describe a building -> a new `specs/<name>.json`.
2. `validate.py` -> `build.py` -> open the `.glb` in Godot, walk it.
3. Tweak the spec (move walls, add entries, resize) and rebuild — deterministic.
4. As the builder gains fidelity (materials, prefab props, destructible
   pieces), bump `KIT_VERSION` and rebuild all levels with `--all`.
5. `catalog.py` + `check.py` keep the repo self-describing and consistent.
