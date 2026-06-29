@tool
extends Node3D
##
## theme_swap.gd  —  greybox → theme visual swap (GAME-SIDE, not part of Deli Counter).
##
## Attach this to the root of a building scene that DC emitted with
## `--format tscn` (its children are instanced greybox module scenes). Set the
## `theme` property and it overlays themed art on each module that has a variant,
## leaving anything un-themed as greybox.
##
## The principle it enforces: GREYBOX IS THE FUNCTION (collision + nav), ART IS
## COSMETIC. For each greybox module, this HIDES the greybox visual and overlays
## the themed visual, but KEEPS the greybox collision untouched. So an art pass
## can never change whether the level works — only how it looks.
##
## Convention: themed modules are authored as VISUAL-ONLY GLBs (no -convcolonly
## collision nodes) named `<type>_<theme>_<style>.glb`, e.g. wall_gasstation_01.glb.
## They share the greybox module's origin/pose so they line up.
##
## Editing a themed .glb updates every instance live — native Godot propagation,
## no Deli Counter rebuild.

@export var theme: String = "greybox":
	set(value):
		theme = value
		if is_inside_tree():
			apply_theme()

@export_dir var library_path: String = "res://art/zoo"

const _OVERLAY_GROUP := "_dc_theme_overlay"


func _ready() -> void:
	apply_theme()


func apply_theme() -> void:
	revert()                                  # clear any previous overlay
	if theme == "" or theme == "greybox":
		return
	for module in get_children():
		var src: String = module.scene_file_path
		if not src.ends_with(".glb"):
			continue
		var parts := src.get_file().get_basename().split("_")   # type_kit_style
		if parts.size() < 3:
			continue
		var themed := "%s/%s_%s_%s.glb" % [
			library_path, parts[0], theme, parts[parts.size() - 1]]
		if not ResourceLoader.exists(themed):
			continue                          # no theme art -> stays greybox
		_set_meshes_visible(module, false)    # hide greybox visual (keep collision)
		var overlay: Node = (load(themed) as PackedScene).instantiate()
		overlay.add_to_group(_OVERLAY_GROUP)
		_strip_collision(overlay)             # cosmetic only; greybox owns collision
		module.add_child(overlay)
		# owner left null on purpose: overlay is generated, not saved into the scene


func revert() -> void:
	if is_inside_tree():
		for n in get_tree().get_nodes_in_group(_OVERLAY_GROUP):
			if is_ancestor_of(n):
				n.queue_free()
	for module in get_children():
		_set_meshes_visible(module, true)


func _set_meshes_visible(node: Node, vis: bool) -> void:
	for c in _walk(node):
		if c is MeshInstance3D:
			c.visible = vis


func _strip_collision(node: Node) -> void:
	for c in _walk(node):
		if c is StaticBody3D or c is CollisionShape3D:
			c.queue_free()


func _walk(node: Node) -> Array:
	var out: Array = []
	for c in node.get_children():
		out.append(c)
		out.append_array(_walk(c))
	return out
