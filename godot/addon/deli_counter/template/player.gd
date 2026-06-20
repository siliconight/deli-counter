extends CharacterBody3D
## deli_counter player controller (test harness)
## ----------------------------------------------------------------------------
## A walk + mouselook body sized to the Deli Counter scale guidelines (1.8 m
## capsule, eye at ~1.6 m), with stair-stepping so it can actually climb the
## generated stairs (Godot's CharacterBody3D has no built-in step handling).
##
## Input: uses dedicated actions move_forward/back/left/right if you've defined
## them (recommended), and falls back to the built-in ui_* arrow keys so it
## still runs in a fresh project with zero setup.

@export var speed: float = 4.5
@export var sprint_speed: float = 7.0
@export var jump_velocity: float = 5.0
@export var mouse_sensitivity: float = 0.003
@export var gravity: float = 18.0
## Max height the player can step up in one move. Generated stairs rise
## ~0.18 m/step, so 0.4 m clears them with wide margin. Keep below ~0.6 m or
## you'll climb things you shouldn't.
## NOTE: this is a lightweight raycast-probe step-up — fine for walk-testing.
## For a production controller, prefer a body_test_motion step-up (see
## godot/README.md "Stairs and player traversal"): it's more robust on edges,
## walls, and slopes. The harness player is a test rig, not a shipping char.
@export var max_step_height: float = 0.4

var _pitch: float = 0.0
@onready var _camera: Camera3D = $Camera3D


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var mm := event as InputEventMouseMotion
		rotate_y(-mm.relative.x * mouse_sensitivity)
		_pitch = clamp(_pitch - mm.relative.y * mouse_sensitivity, -1.4, 1.4)
		if _camera:
			_camera.rotation.x = _pitch
	if event.is_action_pressed("ui_cancel"):
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _move_axis() -> Vector2:
	# dedicated actions if present, else fall back to ui_* (arrow keys)
	if InputMap.has_action("move_left"):
		return Vector2(
			Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
			Input.get_action_strength("move_back") - Input.get_action_strength("move_forward"))
	return Vector2(
		Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left"),
		Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up"))


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	elif Input.is_key_pressed(KEY_SPACE):
		velocity.y = jump_velocity

	var axis := _move_axis()
	var dir := (transform.basis * Vector3(axis.x, 0.0, axis.y)).normalized()
	var spd := sprint_speed if Input.is_key_pressed(KEY_SHIFT) else speed
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd

	_move_with_stairs(delta)


func _move_with_stairs(delta: float) -> void:
	# Normal move first. If grounded and blocked by something short enough to be
	# a step, lift onto it and continue (CharacterBody3D has no step handling).
	move_and_slide()

	if not is_on_floor():
		return

	var blocked := false
	for i in get_slide_collision_count():
		var col := get_slide_collision(i)
		if absf(col.get_normal().y) < 0.1:  # near-vertical surface = step/wall
			blocked = true
			break
	if not blocked:
		return

	var horiz := Vector3(velocity.x, 0.0, velocity.z)
	if horiz.length() < 0.01:
		return
	var fwd := horiz.normalized() * 0.35

	var space := get_world_3d().direct_space_state
	var from := global_position + Vector3.UP * max_step_height + fwd
	var to := from - Vector3.UP * (max_step_height + 0.05)
	var q := PhysicsRayQueryParameters3D.create(from, to)
	q.exclude = [get_rid()]
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return
	var step_top_y: float = hit["position"].y
	var rise := step_top_y - global_position.y
	if rise > 0.02 and rise <= max_step_height:
		# snap onto the step and nudge forward past its riser
		global_position.y = step_top_y + 0.02
		global_position += horiz.normalized() * (speed * delta * 0.5)
