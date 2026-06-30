@tool
extends EditorScenePostImport
## deli_counter_postimport.gd
## ----------------------------------------------------------------------------
## Post-import hook for Deli Counter GLB levels. Attach it to a .glb via the
## Import dock: select the .glb, in the Import tab set
##   "Import Script" -> res://addons/deli_counter/deli_counter_postimport.gd
## then Reimport. It runs in the editor at import time and rewrites the
## imported scene tree so markers/sockets/breach panels become game nodes.
##
## What it does (driven by node-name prefixes baked by the kit, plus the
## companion <name>.gameplay.json when present next to the .glb):
##   ATTACKER_SPAWN_*  -> Marker3D in group "attacker_spawn"
##   DEFENDER_SPAWN*   -> Marker3D in group "defender_spawn"
##   OBJECTIVE_*       -> Marker3D in group "objective" (+ meta from json)
##   CAMERA_SOCKET_*   -> Marker3D in group "camera_socket"
##   DOOR_SOCKET_*     -> Marker3D in group "door_socket" (swap a door scene in)
##   BREACH_PANEL_*    -> StaticBody3D kept, added to group "breach_panel"
##                        with metadata so a breach can free/replace it
##   HATCH_*           -> Marker3D in group "hatch"
##   LADDER_*          -> Area3D climb volume in group "ladder"
##   NAV_REGION_*      -> Marker3D in group "nav_region" (room center)
##   COVER_LOW_* / COVER_HIGH_* -> Marker3D in group "ai_cover"
##   LANDMARK_*        -> Marker3D in group "landmark" (callout/orientation anchor)
##   STAGING_*         -> Marker3D in group "staging" (screened regroup before contest)
##
## Collision is already handled by the glTF importer via the -convcolonly /
## -colonly suffixes on the COLLISION meshes; this script does NOT touch those.
##
## Customize freely: the SCENE_FOR_TAG map lets you instance your own door /
## objective / camera scenes instead of leaving plain Marker3D placeholders.

# Optionally instance project scenes for certain marker types. Leave a value
# empty ("") to keep a plain Marker3D placeholder in the right group.
const SCENE_FOR_TAG := {
	"door_socket": "",      # e.g. "res://scenes/props/Door.tscn"
	"objective":   "",      # e.g. "res://scenes/gameplay/Objective.tscn"
	"camera_socket": "",    # e.g. "res://scenes/gameplay/SecurityCamera.tscn"
}

# Map of node-name prefix -> (group, marker_kind). Order matters: longer/more
# specific prefixes first.
const PREFIX_RULES := [
	["ATTACKER_SPAWN_", "attacker_spawn"],
	["DEFENDER_SPAWN",  "defender_spawn"],
	["OBJECTIVE_",      "objective"],
	["CAMERA_SOCKET_",  "camera_socket"],
	["DOOR_SOCKET_",    "door_socket"],
	["BREACH_PANEL_",   "breach_panel"],
	["HATCH_",          "hatch"],
	["LADDER_",         "ladder"],
	["NAV_REGION_",     "nav_region"],
	["COVER_LOW_",      "ai_cover"],
	["COVER_HIGH_",     "ai_cover"],
	["LANDMARK_",       "landmark"],
	["STAGING_",        "staging"],
]


func _post_import(scene: Node) -> Node:
	var gameplay := _load_gameplay_json()
	var meta_by_name := {}
	if gameplay.has("markers"):
		for m in gameplay["markers"]:
			if m is Dictionary and m.has("name"):
				meta_by_name[String(m["name"]).to_upper()] = m

	var converted := 0
	# collect first; we mutate the tree as we go
	var all_nodes: Array[Node] = []
	_gather(scene, all_nodes)

	# Capture each marker's global transform NOW, while every node is still in
	# the tree. Reading global_transform during/after mutation throws
	# !is_inside_tree() and returns identity (markers would snap to origin).
	var xforms := {}
	for node in all_nodes:
		if node is Node3D:
			xforms[node] = (node as Node3D).global_transform

	for node in all_nodes:
		var upper := node.name.to_upper()
		for rule in PREFIX_RULES:
			var prefix: String = rule[0]
			var group: String = rule[1]
			if upper.begins_with(prefix):
				var xf: Transform3D = xforms.get(node, Transform3D.IDENTITY)
				_convert_node(node, group, meta_by_name.get(upper, {}), scene, xf)
				converted += 1
				break

	print("[deli_counter] post-import: converted %d marker node(s)" % converted)
	return scene


func _gather(node: Node, out: Array[Node]) -> void:
	for child in node.get_children():
		out.append(child)
		_gather(child, out)


func _convert_node(node: Node, group: String, meta: Dictionary, root: Node, xform: Transform3D) -> void:
	# Breach panels stay as their StaticBody3D (they have collision); we just
	# tag them and attach metadata so a breach can replace/free them at runtime.
	if group == "breach_panel":
		node.add_to_group("breach_panel")
		_apply_meta(node, meta)
		return

	# Ladders become a climb VOLUME, not a plain marker: an Area3D the player
	# overlaps to enter climb mode. Sized from the marker meta (climb_height +
	# footprint), with a lip above the top floor so you can climb off the edge.
	if group == "ladder":
		var area := Area3D.new()
		area.name = node.name
		area.add_to_group("ladder")
		area.monitoring = true
		area.monitorable = true
		var ch: float = float(meta.get("climb_height", 3.0))
		var w: float = maxf(float(meta.get("width", 0.5)) + 0.8, 1.0)
		var d: float = float(meta.get("depth", 0.15)) + 1.0
		var cs := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(w, ch + 1.0, maxf(w, d))   # +1 m dismount lip on top
		cs.shape = box
		cs.position = Vector3(0.0, ch * 0.5, 0.0)     # marker sits at the base
		area.add_child(cs)
		var p := node.get_parent()
		p.add_child(area)
		_set_owner_recursive(area, root)
		area.global_transform = xform
		_apply_meta(area, meta)
		node.queue_free()
		return

	# If a project scene is mapped for this tag, instance it at the marker's
	# transform and replace the placeholder; otherwise keep a Marker3D.
	var scene_path: String = SCENE_FOR_TAG.get(group, "")

	var replacement: Node3D
	if scene_path != "" and ResourceLoader.exists(scene_path):
		var packed := load(scene_path) as PackedScene
		replacement = packed.instantiate() as Node3D
	else:
		replacement = Marker3D.new()

	replacement.name = node.name
	replacement.add_to_group(group)

	var parent := node.get_parent()
	parent.add_child(replacement)
	# CRITICAL: owner must be the returned scene root, or the node is silently
	# dropped from the saved import (Godot EditorScenePostImport behavior).
	# Set it AFTER add_child, and set owner on any instanced children too.
	_set_owner_recursive(replacement, root)
	# xform was captured before any tree mutation, so it's the real position.
	replacement.global_transform = xform
	_apply_meta(replacement, meta)
	node.queue_free()


func _set_owner_recursive(node: Node, root: Node) -> void:
	if node == root:
		return
	node.owner = root
	for child in node.get_children():
		_set_owner_recursive(child, root)


func _apply_meta(node: Node, meta: Dictionary) -> void:
	# stash the raw gameplay metadata so game code can read it off the node
	for key in meta.keys():
		if key == "name":
			continue
		node.set_meta(String(key), meta[key])


func _load_gameplay_json() -> Dictionary:
	# The companion file sits next to the source .glb as <name>.gameplay.json.
	var src := get_source_file()  # e.g. res://levels/rowhouse_raid.glb
	if src == "":
		return {}
	var base := src.get_basename()  # strips .glb
	var json_path := base + ".gameplay.json"
	if not FileAccess.file_exists(json_path):
		return {}
	var f := FileAccess.open(json_path, FileAccess.READ)
	if f == null:
		return {}
	var text := f.get_as_text()
	var parsed = JSON.parse_string(text)
	if typeof(parsed) == TYPE_DICTIONARY:
		return parsed
	return {}
