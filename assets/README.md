# assets/ — vendored kitbash source models

Source models that levels compose from, committed to the repo so a checkout
builds without external downloads. Specs reference these by a stable `id`
(see a spec's `assets` array), not by path, so you can move/rename a file
here and only update one line.

## Layout

```
assets/
  props/        small placeable objects (crates, barrels, furniture)
  structures/   larger building chunks (towers, walkways, modules)
  collision/    optional low-poly collision meshes (for collision="file")
```

(Subfolders are a convention, not enforced — `Asset.file` is any path
relative to this folder.)

## Formats (in order of preference)

- **`.glb`** — preferred. Self-contained: geometry + materials + textures in
  one file. `fmt: "glb"`.
- **`.obj`** (+ `.mtl` + texture files) — universal but multi-file; vendor
  the `.mtl` and any referenced textures next to the `.obj`. `fmt: "obj"`.
- **`.blend`** — most capable, least portable; appended (not linked) so the
  data is baked in. Set `fmt: "blend"` and optionally `blend_object` to pick
  one object. Heavier; use only when you need Blender-specific data.

## Collision

Each asset declares a default `collision` strategy; a placement can override
it:

- `convex` (default) — auto convex hull of the asset. Fast, one shape. Best
  for most props in a 4-player FPS.
- `box` — axis-aligned bounding box. Cheapest.
- `file` — use a separate low-poly mesh (`collision_file`, also under
  assets/). For concave shapes a hull can't capture (archways, U-shapes).
- `trimesh` — the asset mesh itself as concave collision. Static, costly;
  avoid for anything players collide with often.
- `none` — visual only.

## Conventions

- Model origin at the base center where practical, so `z` in a placement is
  the floor height.
- Units in meters, +Z up, to match the generated geometry.
- Keep source models reasonably low-poly; this kit bakes everything into one
  monolithic level mesh.

## Licensing

Only commit assets you have the right to redistribute. Note the source and
license of each third-party asset (a `SOURCES.md` here is a good habit).
