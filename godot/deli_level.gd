extends Node
class_name DeliLevel
## DeliLevel — runtime helper for querying a Deli Counter level.
## ----------------------------------------------------------------------------
## After the post-import script tags marker nodes into groups, use these static
## helpers from game code to find spawns, objectives, cover, and to breach a
## panel. Nothing here is mandatory — it's a thin convenience layer over the
## groups the import script assigns.
##
## Example:
##   var spawns := DeliLevel.attacker_spawns(get_tree())
##   var obj    := DeliLevel.objectives(get_tree())
##   DeliLevel.breach(some_breach_panel)   # opens a soft wall

static func _in_group(tree: SceneTree, group: String) -> Array[Node]:
	var out: Array[Node] = []
	for n in tree.get_nodes_in_group(group):
		out.append(n)
	return out

static func attacker_spawns(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "attacker_spawn")

static func defender_spawns(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "defender_spawn")

static func objectives(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "objective")

static func camera_sockets(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "camera_socket")

static func door_sockets(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "door_socket")

static func breach_panels(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "breach_panel")

static func hatches(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "hatch")

static func cover_points(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "ai_cover")

static func nav_regions(tree: SceneTree) -> Array[Node]:
	return _in_group(tree, "nav_region")


## Breach a soft wall/floor panel: free the static panel so the opening is
## passable. Optionally spawn debris or a replacement body. Returns the
## panel's global position so callers can spawn VFX there.
static func breach(panel: Node, replacement: PackedScene = null) -> Vector3:
	var pos := Vector3.ZERO
	if panel is Node3D:
		pos = (panel as Node3D).global_position
	if replacement != null:
		var inst := replacement.instantiate()
		var parent := panel.get_parent()
		if parent != null:
			parent.add_child(inst)
			if inst is Node3D:
				(inst as Node3D).global_position = pos
	panel.queue_free()
	return pos


## Read the gameplay metadata an import attached to a node (tag, breach_class,
## material, room, etc.). Returns {} if none.
static func meta_of(node: Node) -> Dictionary:
	var d := {}
	for key in node.get_meta_list():
		d[key] = node.get_meta(key)
	return d
