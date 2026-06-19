extends Node3D
## deli_counter level test harness
## ----------------------------------------------------------------------------
## Drop a generated level .glb under this scene (or set `level_scene`) and press
## play to walk it. Provides the things you want when checking a blockout:
##   F1  toggle this help / HUD
##   F2  toggle debug collision view (see the collision shapes)
##   F3  toggle the SCALE_REF proxies if the level baked them
##   F4  bake a NavigationMesh over the level and show it
##   R   respawn the player at the first attacker/crew spawn (or origin)
##
## None of this ships in your game — it's a greybox testing rig. Keep your real
## player/UI elsewhere.

## Optionally assign a level scene (the imported .glb) in the inspector. If left
## empty, the harness uses the first child that looks like a level.
@export var level_scene: PackedScene
## Show collision shapes from startup. Runtime toggling of collision debug is
## unreliable in Godot, so this is set once at _ready(); for on/off while
## running, use the editor's Debug -> Visible Collision Shapes menu instead.
@export var show_collision_shapes: bool = false

@onready var _player: CharacterBody3D = $Player
@onready var _hud: Label = $HUD/Help

var _level: Node3D
var _nav_region: NavigationRegion3D


func _ready() -> void:
	# reliable: set before the scene starts simulating
	get_tree().debug_collisions_hint = show_collision_shapes
	if level_scene:
		_level = level_scene.instantiate()
		add_child(_level)
	else:
		# find an already-instanced level (any Node3D child that isn't player/light)
		for c in get_children():
			if c is Node3D and c != _player and not (c is Light3D) and not (c is Camera3D):
				_level = c
				break
	_update_hud()
	_respawn()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_F1:
				$HUD.visible = not $HUD.visible
			KEY_F3:
				_toggle_scale_ref()
			KEY_F4:
				_bake_navmesh()
			KEY_R:
				_respawn()


func _respawn() -> void:
	if not _player:
		return
	var spawn := _find_first_spawn()
	if spawn != Vector3.INF:
		_player.global_position = spawn + Vector3(0, 1.0, 0)
	else:
		_player.global_position = Vector3(0, 1.0, 0)
	_player.velocity = Vector3.ZERO


func _find_first_spawn() -> Vector3:
	for grp in ["attacker_spawn", "crew_spawn", "defender_spawn"]:
		var nodes := get_tree().get_nodes_in_group(grp)
		if nodes.size() > 0 and nodes[0] is Node3D:
			return (nodes[0] as Node3D).global_position
	return Vector3.INF


func _toggle_scale_ref() -> void:
	# SCALE_REF is excluded from export, but if a test glb included it, toggle it
	if not _level:
		return
	var node := _level.find_child("SCALE_REF", true, false)
	if node:
		node.visible = not node.visible


func _bake_navmesh() -> void:
	if not _level:
		return
	if _nav_region == null:
		_nav_region = NavigationRegion3D.new()
		var nm := NavigationMesh.new()
		nm.agent_radius = 0.4
		nm.agent_height = 1.8
		nm.cell_size = 0.25
		_nav_region.navigation_mesh = nm
		add_child(_nav_region)
	# bake using the level geometry as source
	_nav_region.bake_navigation_mesh()
	_update_hud()


func _update_hud() -> void:
	if _hud == null:
		return
	_hud.text = "\n".join([
		"DELI COUNTER — level test harness",
		"WASD/arrows move   mouse look   Shift sprint   Space jump   Esc free mouse",
		"F1 help   F3 scale proxies   F4 bake navmesh   R respawn",
		"collision view: editor Debug menu -> Visible Collision Shapes",
	])
