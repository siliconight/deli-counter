"""
make_gasstation_modules.py  --  VISUAL-ONLY theme stubs for the PRIMARY path
=============================================================================
Run inside Blender. Emits visual-only stub GLBs (no collision -- greybox owns
collision; theme_swap.gd overlays these) into your Godot project's module
library, with dims-aware width-token names.

Art-pass each stub's mesh in place, keep the name + pose, re-export.
"""

import bpy
import os

# ============================ CONFIG ========================================
# Point at your Godot project's module library (NOT the Deli Counter repo):
OUT_DIR = r"C:\Projects\delco_dangerous\art\zoo"   # = res://art/zoo

WALL_THICK   = 0.3
STORY_HEIGHT = 4.2
MODULE_WIDTH = 2.0

EMIT_WALL      = True
WINDOW_WIDTHS  = [1.2, 2.0, 2.4, 3.0]
DOORWAY_WIDTHS = [1.1, 1.2, 1.4, 1.8]
DOOR_HEIGHT    = 2.2
# ============================================================================


def _box(name, cx, cy, cz, dx, dy, dz):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.scale = (dx, dy, dz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.name = name                       # VISUAL only -- no collision suffix
    return obj


def _export(objs, filename):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    path = os.path.join(OUT_DIR, filename)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format='GLB')
    print(f"[gasstation] wrote {path}")


def _clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def _tok(w):
    return f"w{int(round(w * 100))}"


def make_wall():
    _clear()
    v = _box("wall", 0, 0, 0, MODULE_WIDTH, WALL_THICK, STORY_HEIGHT)
    _export([v], "wall_gasstation_01.glb")


def make_doorway(w):
    """Visual frame only: a header (lintel) + thin jambs. Door void stays open;
    collision is the greybox module's job."""
    _clear()
    floor = -STORY_HEIGHT / 2.0
    door_top = floor + DOOR_HEIGHT
    lintel_h = (STORY_HEIGHT / 2.0) - door_top
    objs = []
    if lintel_h > 0.05:
        objs.append(_box("doorway_lintel", 0, 0, door_top + lintel_h / 2.0,
                         w, WALL_THICK, lintel_h))
    objs.append(_box("doorway_jambL", -(w / 2 - 0.05), 0, 0, 0.1, WALL_THICK, STORY_HEIGHT))
    objs.append(_box("doorway_jambR",  (w / 2 - 0.05), 0, 0, 0.1, WALL_THICK, STORY_HEIGHT))
    _export(objs, f"doorway_gasstation_01_{_tok(w)}.glb")


def make_window(w):
    """Visual pane only (sealed look); greybox owns the collision."""
    _clear()
    v = _box("window", 0, 0, 0, w, WALL_THICK, STORY_HEIGHT)
    _export([v], f"window_gasstation_01_{_tok(w)}.glb")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if EMIT_WALL:
        make_wall()
    for w in WINDOW_WIDTHS:
        make_window(w)
    for w in DOORWAY_WIDTHS:
        make_doorway(w)
    print("[gasstation] done ->", OUT_DIR)


if __name__ == "__main__":
    main()
