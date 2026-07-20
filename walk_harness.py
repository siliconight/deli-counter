"""walk_harness.py -- wrap a portable building package in a THROWAWAY walk test
(self-contained FPS player + sun + sky) so you can WASD around the themed,
walkable building. Writes a SEPARATE walk copy; the handoff package stays clean
(no player, no addon).

    python walk_harness.py <package_dir> [--out <walk_dir>] [--spawn x y z]

Then open <walk_dir> as a Godot project and press F5.
Controls: WASD move, mouse look, Space jump, Esc toggles mouse capture.
"""
import argparse
import json
import os
import re
import shutil

PLAYER_GD = '''extends CharacterBody3D
# Self-contained FPS walker: no input map, no addon. WASD move, mouse look,
# Space jump, Esc toggles mouse capture.
@export var speed := 5.0
@export var jump_v := 4.5
@export var sens := 0.0025
var grav := 14.0
@onready var cam: Camera3D = $Camera3D

func _ready() -> void:
\tInput.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(e: InputEvent) -> void:
\tif e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
\t\trotate_y(-e.relative.x * sens)
\t\tcam.rotate_x(-e.relative.y * sens)
\t\tcam.rotation.x = clamp(cam.rotation.x, -1.4, 1.4)
\telif e is InputEventKey and e.pressed and e.keycode == KEY_ESCAPE:
\t\tInput.mouse_mode = Input.MOUSE_MODE_VISIBLE if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED else Input.MOUSE_MODE_CAPTURED

func _physics_process(dt: float) -> void:
\tif not is_on_floor():
\t\tvelocity.y -= grav * dt
\telif Input.is_key_pressed(KEY_SPACE):
\t\tvelocity.y = jump_v
\tvar dir := Vector3.ZERO
\tif Input.is_key_pressed(KEY_W): dir.z -= 1.0
\tif Input.is_key_pressed(KEY_S): dir.z += 1.0
\tif Input.is_key_pressed(KEY_A): dir.x -= 1.0
\tif Input.is_key_pressed(KEY_D): dir.x += 1.0
\tdir = transform.basis * dir
\tdir.y = 0.0
\tdir = dir.normalized()
\tvelocity.x = dir.x * speed
\tvelocity.z = dir.z * speed
\tmove_and_slide()
'''

WALK_TSCN = '''[gd_scene load_steps=7 format=3]

[ext_resource type="PackedScene" path="res://{bid}.tscn" id="1_b"]
[ext_resource type="Script" path="res://player.gd" id="2_p"]

[sub_resource type="CapsuleShape3D" id="cap"]
radius = 0.4
height = 1.8

[sub_resource type="ProceduralSkyMaterial" id="skym"]

[sub_resource type="Sky" id="sky"]
sky_material = SubResource("skym")

[sub_resource type="Environment" id="env"]
background_mode = 2
sky = SubResource("sky")
ambient_light_source = 3
tonemap_mode = 2

[node name="Walk" type="Node3D"]

[node name="Building" parent="." instance=ExtResource("1_b")]

[node name="Sun" type="DirectionalLight3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 0.5, 0.866, 0, -0.866, 0.5, 0, 30, 10)
shadow_enabled = true

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("env")

[node name="Player" type="CharacterBody3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {sx}, {sy}, {sz})
script = ExtResource("2_p")

[node name="Col" type="CollisionShape3D" parent="Player"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.9, 0)
shape = SubResource("cap")

[node name="Camera3D" type="Camera3D" parent="Player"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.6, 0)
'''


def _bid(pkg_dir):
    mf = os.path.join(pkg_dir, "portable_resource_manifest.json")
    if os.path.exists(mf):
        return json.load(open(mf, encoding="utf-8")).get("building_id", "building")
    for f in os.listdir(pkg_dir):
        if f.endswith(".tscn") and not f.endswith("_main.tscn"):
            return f[:-5]
    return "building"


def scaffold(pkg_dir, walk_dir, spawn=(0.0, 1.5, 0.0)):
    if os.path.exists(walk_dir):
        shutil.rmtree(walk_dir)
    shutil.copytree(pkg_dir, walk_dir)
    bid = _bid(pkg_dir)
    open(os.path.join(walk_dir, "player.gd"), "w", encoding="utf-8").write(PLAYER_GD)
    open(os.path.join(walk_dir, "walk.tscn"), "w", encoding="utf-8").write(
        WALK_TSCN.format(bid=bid, sx=spawn[0], sy=spawn[1], sz=spawn[2]))
    # point the project at the walk scene (keep everything else).
    pg = os.path.join(walk_dir, "project.godot")
    text = open(pg, encoding="utf-8").read()
    text = re.sub(r'run/main_scene="[^"]*"', 'run/main_scene="res://walk.tscn"', text)
    open(pg, "w", encoding="utf-8").write(text)
    return {"walk_dir": walk_dir, "building": bid, "spawn": list(spawn)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("package", help="portable building package dir")
    ap.add_argument("--out", default="", help="walk copy dir (default <package>_walk)")
    ap.add_argument("--spawn", nargs=3, type=float, default=[0.0, 1.5, 0.0],
                    help="player spawn x y z (Godot space; default center, 1.5 up)")
    a = ap.parse_args()
    out = a.out or (a.package.rstrip("/\\") + "_walk")
    info = scaffold(a.package, out, tuple(a.spawn))
    print(f"[walk] scaffolded {info['walk_dir']}  (building={info['building']}, "
          f"spawn={info['spawn']})")
    print(f"[walk] open that folder as a Godot project and press F5. "
          f"WASD move, mouse look, Space jump, Esc frees the mouse.")
