"""
make_wall_module.py  --  reusable recipe: one baked-path test module
====================================================================
A minimal authoring recipe for a single BAKED-path module, used to exercise the
resolver in-engine (it's how the 0.42 validation walk proved `_instance_module`).
Sibling to make_gasstation_modules.py, but a different job:

  - make_gasstation_modules.py  -> PRIMARY (.tscn) path: VISUAL-ONLY theme-kit
    modules (greybox keeps collision).
  - make_wall_module.py (this)  -> BAKED path: ONE module that REPLACES the
    generated box, so it carries its OWN collision (a `-convcolonly` child).

Run headless:  & $env:BLENDER --background --python docs\themes\gasstation\make_wall_module.py
or inside Blender (Scripting -> Run Script).

Emits wall_gasstation_01.glb (2.0 x 0.3 x 4.2 m), origin-centered, authored along
X (width=X, thickness=Y, height=Z in Blender), into DC_MODULE_LIB (the same folder
the resolver reads), falling back to C:\\dc-modules. Point a themed build at it:
    $env:DC_MODULAR="1"; $env:DC_MODULE="2.0"
    $env:DC_THEME="gasstation"; $env:DC_MODULE_LIB="C:\\dc-modules"
    python build.py specs\\fuel_stop_heist.json
The 66 uniform-width wall slots resolve to this module; everything else falls back
to generated greybox. To author a state variant, change the output name to e.g.
wall_gasstation_01_damaged.glb (DC_STATE=damaged then selects it).
"""

import bpy
import os

OUT_DIR = os.environ.get("DC_MODULE_LIB") or r"C:\dc-modules"
W, T, H = 2.0, 0.3, 4.2        # width(X) x thickness(Y) x height(Z)


def _box(name, dx, dy, dz):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.scale = (dx, dy, dz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.name = name
    obj.data.name = name           # name the mesh datablock too (avoids "Cube")
    return obj


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    visual = _box("wall", W, T, H)
    collide = _box("wall-convcolonly", W, T, H)   # convex collision sibling

    bpy.ops.object.select_all(action='DESELECT')
    visual.select_set(True)
    collide.select_set(True)
    out = os.path.join(OUT_DIR, "wall_gasstation_01.glb")
    bpy.ops.export_scene.gltf(filepath=out, use_selection=True, export_format='GLB')
    print(f"[wall module] wrote {out}")


if __name__ == "__main__":
    main()
