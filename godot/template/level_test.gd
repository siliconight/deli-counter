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
			KEY_F5:
				_check_nav_connectivity()
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


## F5 -- NAVMESH CONNECTIVITY CHECK (the authoritative "can an AI enemy path
## to the player / objectives" answer). Bakes if needed, then for the player
## spawn and every gameplay marker, snaps to the navmesh and queries a path
## between the spawn and each marker. Reports which markers an agent can reach.
## This is what the offline navigability.py proxy approximates — this version
## is capsule-accurate truth from a real navmesh.
func _check_nav_connectivity() -> void:
	if _nav_region == null:
		_bake_navmesh()
	if _nav_region == null:
		print("[nav-check] no navmesh region; cannot check")
		return
	var map: RID = get_world_3d().navigation_map
	# gather targets: every marker empty under the level (spawns, objectives,
	# extraction, finale, etc.) -- these are the anchors an AI would path to.
	var targets: Array = []
	for n in _find_markers(_level):
		targets.append({"name": n.name, "pos": n.global_position})
	if targets.is_empty():
		print("[nav-check] no markers found to test against")
		return
	# use the player spawn (or player position) as the path origin
	var origin: Vector3 = _player.global_position if _player else Vector3.ZERO
	var origin_on_nav: Vector3 = NavigationServer3D.map_get_closest_point(map, origin)
	var ok := 0
	var fails: Array = []
	for t in targets:
		var tgt_on_nav: Vector3 = NavigationServer3D.map_get_closest_point(map, t["pos"])
		var path: PackedVector3Array = NavigationServer3D.map_get_path(
			map, origin_on_nav, tgt_on_nav, true)
		# a real path has >=2 points and actually reaches near the target
		var reached := path.size() >= 2 and path[path.size() - 1].distance_to(tgt_on_nav) < 1.0
		# also flag if the target is far from any navmesh surface (unreachable)
		var snap_dist := t["pos"].distance_to(tgt_on_nav)
		if reached and snap_dist < 2.0:
			ok += 1
		else:
			fails.append("%s (snap %.1fm, %s)" % [
				t["name"], snap_dist,
				"no path" if not reached else "off-navmesh"])
	print("[nav-check] %d/%d markers reachable by a nav agent from the player" % [
		ok, targets.size()])
	if fails.size() > 0:
		print("[nav-check] UNREACHABLE: " + ", ".join(fails))
		print("[nav-check] -> an AI enemy could NOT path to those anchors. "
			+ "Check doorway widths, stair navmesh, and isolated rooms.")
	else:
		print("[nav-check] all anchors reachable -- enemies can path through "
			+ "the building to every gameplay point.")
	_update_hud()


func _find_markers(node: Node) -> Array:
	## markers are Node3D/Marker3D empties whose names came from the spec.
	var out: Array = []
	for child in node.get_children():
		if child is Node3D and child.get_child_count() == 0 \
				and not (child is MeshInstance3D) and not (child is StaticBody3D):
			out.append(child)
		out.append_array(_find_markers(child))
	return out


func _update_hud() -> void:
	if _hud == null:
		return
	_hud.text = "\n".join([
		"DELI COUNTER — level test harness",
		"WASD/arrows move   mouse look   Shift sprint   Space jump   Esc free mouse",
		"F1 help   F3 scale proxies   F4 bake navmesh   F5 nav-reach check   R respawn",
		"collision view: editor Debug menu -> Visible Collision Shapes",
	])
