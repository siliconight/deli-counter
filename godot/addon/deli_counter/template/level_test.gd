extends Node3D
## deli_counter level test harness
## ----------------------------------------------------------------------------
## Drop a generated level .glb under this scene (or set `level_scene`) and press
## play to walk it. Provides the things you want when checking a blockout:
##   F1  toggle this help / HUD
##   F2  toggle debug collision view (see the collision shapes)
##   F3  toggle the SCALE_REF proxies if the level baked them
##   F4  bake a NavigationMesh over the level and show it
##   F5  nav connectivity check: can an agent path from the player to every
##       gameplay marker? (bake with F4 first; see NAVMESH_CHECK.md)
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
var _nav_dbg: MeshInstance3D
var _nav_polys: int = -1


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
				_nav_check()
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
		add_child(_nav_region)
	var nm := NavigationMesh.new()
	nm.agent_radius = 0.4
	nm.agent_height = 1.8
	nm.agent_max_climb = 0.5
	nm.cell_size = 0.25
	# Walls/props import as -convcolonly COLLISION shapes (Godot strips their
	# visual mesh), so parse static colliders, not visual meshes — otherwise the
	# bake only sees the floor slab and produces one big empty quad.
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = 0xFFFFFFFF
	# A bare bake_navigation_mesh() finds nothing because the level isn't a child
	# of the region. Parse the level's geometry explicitly, then bake from it.
	var src := NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nm, src, _level)
	NavigationServer3D.bake_from_source_geometry_data(nm, src)
	_nav_region.navigation_mesh = nm
	_nav_polys = nm.get_polygon_count()
	_show_nav_debug(nm)            # render it ourselves so it shows without the debug flag
	_update_hud()


func _show_nav_debug(nm: NavigationMesh) -> void:
	if _nav_dbg:
		_nav_dbg.queue_free()
		_nav_dbg = null
	if nm.get_polygon_count() == 0:
		return
	var verts := nm.get_vertices()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in nm.get_polygon_count():
		var poly := nm.get_polygon(i)
		for k in range(1, poly.size() - 1):     # fan-triangulate the polygon
			st.add_vertex(verts[poly[0]])
			st.add_vertex(verts[poly[k]])
			st.add_vertex(verts[poly[k + 1]])
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.1, 0.8, 1.0, 0.45)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	st.set_material(mat)
	_nav_dbg = MeshInstance3D.new()
	_nav_dbg.mesh = st.commit()
	_nav_dbg.position.y += 0.05               # lift so it doesn't z-fight the floor
	add_child(_nav_dbg)


const _CHECK_GROUPS := ["objective", "extraction", "loot", "patrol_point",
		"rescue", "attacker_spawn", "defender_spawn", "crew_spawn"]
const _SNAP_MAX := 2.0


func _nav_check() -> void:
	## The documented F5 connectivity check (NAVMESH_CHECK.md): from the
	## player's position, can a nav agent path to every gameplay marker?
	## The headless twin of this lives in ../nav_gate.gd (CI runs that one).
	if _nav_region == null or _nav_polys <= 0:
		print("[nav-check] no navmesh -- press F4 to bake first")
		return
	var map: RID = get_viewport().get_world_3d().navigation_map
	var from: Vector3 = _player.global_position
	var checked := 0
	var reachable := 0
	var failures: PackedStringArray = []
	for grp in _CHECK_GROUPS:
		for node in get_tree().get_nodes_in_group(grp):
			if not (node is Node3D):
				continue
			var target: Vector3 = (node as Node3D).global_position
			checked += 1
			var path := NavigationServer3D.map_get_path(map, from, target, true)
			if path.is_empty():
				failures.append("%s (no path)" % node.name)
				continue
			var snap := path[path.size() - 1].distance_to(target)
			if snap > _SNAP_MAX:
				failures.append("%s (snap %.1fm, off-navmesh)" % [node.name, snap])
			else:
				reachable += 1
	print("[nav-check] %d/%d markers reachable by a nav agent from the player"
			% [reachable, checked])
	if failures.is_empty():
		print("[nav-check] all anchors reachable -- enemies can path through "
				+ "the building to every gameplay point.")
	else:
		print("[nav-check] UNREACHABLE: %s" % ", ".join(failures))
		print("[nav-check] -> an AI enemy could NOT path to those anchors. "
				+ "Check doorway widths, stair navmesh, and isolated rooms.")


func _update_hud() -> void:
	if _hud == null:
		return
	_hud.text = "\n".join([
		"DELI COUNTER — level test harness",
		"WASD/arrows move   mouse look   Shift sprint   Space jump   Esc free mouse",
		"F1 help   F3 scale proxies   F4 bake navmesh   R respawn",
		("navmesh: %d polys" % _nav_polys) if _nav_polys >= 0 else "navmesh: press F4 to bake",
		"collision view: editor Debug menu -> Visible Collision Shapes",
	])
