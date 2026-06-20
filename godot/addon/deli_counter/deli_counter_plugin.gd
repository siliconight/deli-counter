@tool
extends EditorPlugin
## deli_counter_plugin.gd
## ----------------------------------------------------------------------------
## Editor plugin that removes the manual per-level file shuffle. Adds a dock
## with buttons to:
##   - pick a level .glb under res://
##   - assign the post-import marker-conversion script to it and reimport (so
##     you never touch the Import tab)
##   - build a fresh test scene from the harness template, instance the level,
##     open it, and (optionally) run it
##
## Install: copy this addon folder to res://addons/deli_counter/, then enable
## "Deli Counter" in Project Settings -> Plugins.
##
## Everything here runs in the editor (@tool). It writes a test scene under
## res://deli_counter_tests/ so it never clobbers your own scenes.

const POSTIMPORT_SCRIPT := "res://addons/deli_counter/deli_counter_postimport.gd"
const HARNESS_SCENE := "res://addons/deli_counter/template/level_test.tscn"
const TEST_DIR := "res://deli_counter_tests"

var _dock: Control
var _level_path_label: Label
var _selected_glb: String = ""
var _status: Label


func _enter_tree() -> void:
	_dock = _build_dock()
	add_control_to_dock(DOCK_SLOT_LEFT_UR, _dock)


func _exit_tree() -> void:
	if _dock:
		remove_control_from_docks(_dock)
		_dock.queue_free()
		_dock = null


func _build_dock() -> Control:
	var root := VBoxContainer.new()
	root.name = "Deli Counter"
	root.add_theme_constant_override("separation", 6)

	var title := Label.new()
	title.text = "Deli Counter"
	title.add_theme_font_size_override("font_size", 16)
	root.add_child(title)

	var hint := Label.new()
	hint.text = "Pick a level .glb, then set it up and play."
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(hint)

	var pick_btn := Button.new()
	pick_btn.text = "Pick level .glb…"
	pick_btn.pressed.connect(_on_pick_pressed)
	root.add_child(pick_btn)

	_level_path_label = Label.new()
	_level_path_label.text = "(no level selected)"
	_level_path_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_level_path_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	root.add_child(_level_path_label)

	root.add_child(HSeparator.new())

	var import_btn := Button.new()
	import_btn.text = "1. Assign import script + reimport"
	import_btn.pressed.connect(_on_assign_import_pressed)
	root.add_child(import_btn)

	var build_btn := Button.new()
	build_btn.text = "2. Build test scene"
	build_btn.pressed.connect(_on_build_scene_pressed)
	root.add_child(build_btn)

	var play_btn := Button.new()
	play_btn.text = "Set up & Play  ▶"
	play_btn.tooltip_text = "Does both steps above, opens the test scene, and runs it."
	play_btn.pressed.connect(_on_setup_and_play_pressed)
	root.add_child(play_btn)

	root.add_child(HSeparator.new())

	_status = Label.new()
	_status.text = ""
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(_status)

	return root


func _set_status(msg: String, ok: bool = true) -> void:
	if _status:
		_status.text = msg
		_status.add_theme_color_override(
			"font_color", Color(0.5, 0.9, 0.5) if ok else Color(0.95, 0.5, 0.5))
	print("[deli_counter plugin] " + msg)


func _on_pick_pressed() -> void:
	var fd := EditorFileDialog.new()
	fd.file_mode = EditorFileDialog.FILE_MODE_OPEN_FILE
	fd.access = EditorFileDialog.ACCESS_RESOURCES
	fd.add_filter("*.glb", "glTF binary level")
	fd.file_selected.connect(_on_glb_selected)
	get_editor_interface().get_base_control().add_child(fd)
	fd.popup_centered_ratio(0.6)


func _on_glb_selected(path: String) -> void:
	_selected_glb = path
	_level_path_label.text = path
	# warn if the gameplay.json companion is missing
	var companion := path.get_basename() + ".gameplay.json"
	if not FileAccess.file_exists(companion):
		_set_status("Picked. Note: %s not found next to the .glb — markers "
			% companion.get_file() + "won't carry metadata.", false)
	else:
		_set_status("Picked %s." % path.get_file())


func _ensure_selected() -> bool:
	if _selected_glb == "":
		_set_status("Pick a level .glb first.", false)
		return false
	return true


func _on_assign_import_pressed() -> bool:
	if not _ensure_selected():
		return false
	# Edit the .import file so the glb uses our post-import script, then reimport
	var import_file := _selected_glb + ".import"
	if not FileAccess.file_exists(import_file):
		_set_status("No .import for this .glb yet — let Godot import it once, "
			+ "then try again.", false)
		return false
	var cfg := ConfigFile.new()
	var err := cfg.load(import_file)
	if err != OK:
		_set_status("Couldn't read %s (err %d)." % [import_file.get_file(), err], false)
		return false
	# the glTF importer reads params/import_script/path
	cfg.set_value("params", "import_script/path", POSTIMPORT_SCRIPT)
	cfg.save(import_file)
	# ask the editor to reimport this resource
	get_editor_interface().get_resource_filesystem().reimport_files([_selected_glb])
	_set_status("Assigned import script and reimported %s." % _selected_glb.get_file())
	return true


func _on_build_scene_pressed() -> String:
	if not _ensure_selected():
		return ""
	if not ResourceLoader.exists(HARNESS_SCENE):
		_set_status("Harness scene missing at %s — is the template folder "
			% HARNESS_SCENE + "installed?", false)
		return ""
	# make the tests dir
	if not DirAccess.dir_exists_absolute(TEST_DIR):
		DirAccess.make_dir_recursive_absolute(TEST_DIR)

	# load harness, instance it, add the level as a child of its Main root
	var harness: PackedScene = load(HARNESS_SCENE)
	var root := harness.instantiate()

	var level_scene: PackedScene = load(_selected_glb)
	if level_scene == null:
		_set_status("Couldn't load %s as a scene." % _selected_glb.get_file(), false)
		return ""
	var level := level_scene.instantiate()
	level.name = _selected_glb.get_file().get_basename()
	root.add_child(level)
	# The level is an INSTANCED scene (a GLB). To save it into the test scene,
	# set the owner on the instance node ONLY — its children come along as part
	# of the instance and must NOT have their owners reassigned (doing so is the
	# fragile pattern that drops nodes on pack; see Godot issues #32179/#90823).
	# The earlier bug was the opposite: the level node had no owner at all, so
	# pack() dropped it and you got the bare harness (ground + light, no level).
	level.owner = root

	# pack and save it
	var out_path := "%s/test_%s.tscn" % [TEST_DIR, level.name]
	var packed := PackedScene.new()
	var pack_err := packed.pack(root)
	if pack_err != OK:
		_set_status("Failed to pack test scene (err %d)." % pack_err, false)
		return ""
	var save_err := ResourceSaver.save(packed, out_path)
	if save_err != OK:
		_set_status("Failed to save test scene (err %d)." % save_err, false)
		return ""
	get_editor_interface().get_resource_filesystem().scan()
	_set_status("Built test scene: %s" % out_path)
	return out_path


func _on_setup_and_play_pressed() -> void:
	if not _ensure_selected():
		return
	_on_assign_import_pressed()
	var scene_path := _on_build_scene_pressed()
	if scene_path == "":
		return
	get_editor_interface().open_scene_from_path(scene_path)
	# play_current_scene runs whatever scene is open in the editor; we just
	# opened the test scene, so this runs it. (Avoids relying on
	# play_custom_scene, which isn't available on all 4.x versions.)
	get_editor_interface().play_current_scene()
	_set_status("Playing %s" % scene_path.get_file())
