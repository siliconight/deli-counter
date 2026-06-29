"""
make_pump_greybox.py  --  greybox kitbash assets for the placements example
===========================================================================
Authors two greybox prop assets for the volumes -> instanced-placements worked
example in docs/AUTHORING.md. Run in Blender (Scripting -> Run Script) or
headless:

    & $env:BLENDER --background --python assets\props\make_pump_greybox.py

Writes origin-centered VISUAL-ONLY boxes (no collision child needed -- the
placement path generates the collider from the asset's `collision` strategy):

    pump_greybox.glb         1.0 x 1.2 x 1.4 m   (the pump)
    pump_island_greybox.glb  1.6 x 8.0 x 0.3 m   (the concrete island)

These are GREYBOX stand-ins: an artist later replaces these two files with
themed pump / island models at the same dims, and every placement instances the
new art -- one mesh + one texture in VRAM, art-passed once. Authored in Blender
so the Blender<->glTF up-axis round-trip is symmetric and the dims come back
exactly (width=X, depth=Y, height=Z).
"""

import bpy
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
PARTS = {
    "pump_greybox": ("pump", (1.0, 1.2, 1.4)),
    "pump_island_greybox": ("pump_island", (1.6, 8.0, 0.3)),
}


def _fresh():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def _box(name, dx, dy, dz):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.scale = (dx, dy, dz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.name = name
    obj.data.name = name          # name the mesh datablock too (no "Cube")
    return obj


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, (objname, (dx, dy, dz)) in PARTS.items():
        _fresh()
        obj = _box(objname, dx, dy, dz)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        out = os.path.join(OUT_DIR, f"{fname}.glb")
        bpy.ops.export_scene.gltf(filepath=out, use_selection=True,
                                  export_format='GLB')
        print(f"[pump greybox] wrote {out}")


if __name__ == "__main__":
    main()
