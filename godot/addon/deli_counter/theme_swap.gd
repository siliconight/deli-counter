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

## Optional model state (e.g. "damaged", "weathered"). When set, a
## <type>_<theme>_<style>[_wNN]_<state>.glb variant wins over the stateless one,
## falling back to stateless, then greybox. Honors the kit-naming convention
## <type>_<descriptor>_<variant>[_w<cm>][_<state>].
@export var state: String = "":
	set(value):
		state = value
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
		# greybox stem is `type_kit_style` or `type_kit_style_wNN` (dims-aware).
		var parts := src.get_file().get_basename().split("_")
		if parts.size() < 3:
			continue
		var typ := parts[0]
		var style := parts[2]
		var wtok := ""
		# width token is `w` followed by digits (w180) — guard so a non-width
		# 4th token never gets mistaken for one.
		if parts.size() >= 4 and parts[3].begins_with("w") and parts[3].substr(1).is_valid_int():
			wtok = parts[3]
		# Most specific themed variant wins (modules are never scaled), then less
		# specific; nothing exists -> stays greybox. Order:
		#   w+state  ->  w  ->  state  ->  generic
		var base := "%s/%s_%s_%s" % [library_path, typ, theme, style]
		var candidates: Array[String] = []
		if wtok != "" and state != "":
			candidates.append("%s_%s_%s.glb" % [base, wtok, state])
		if wtok != "":
			candidates.append("%s_%s.glb" % [base, wtok])
		if state != "":
			candidates.append("%s_%s.glb" % [base, state])
		candidates.append("%s.glb" % base)
		var themed := ""
		for cand in candidates:
			if ResourceLoader.exists(cand):
				themed = cand
				break
		if themed == "":
			continue                          # no theme art -> stays greybox
		_set_meshes_visible(module, false)    # hide greybox visual (keep collision)
		var overlay: Node = (load(themed) as PackedScene).instantiate()
		overlay.add_to_group(_OVERLAY_GROUP)
		if state != "":
			overlay.set_meta("dc_state", state)   # pass-through for game code
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
