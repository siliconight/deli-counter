extends CharacterBody3D
## deli_counter player controller (test harness)
## ----------------------------------------------------------------------------
## A walk + mouselook body sized to the Deli Counter scale guidelines (1.8 m
## capsule, eye at ~1.6 m), with stair-stepping so it can actually climb the
## generated stairs (Godot's CharacterBody3D has no built-in step handling).
##
## Input: WASD and arrow keys both work with zero setup. If you define dedicated
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

## Vertical climb speed on ladders (m/s). You climb along where you LOOK: look up
## + hold forward to ascend, look down to descend, look level + forward to step
## off at the top. No input = cling in place (gravity is off on the ladder).
## Press Space to let go and drop. The post-import builds the ladder Area3D
## climb volumes (group "ladder"); see deli_counter_postimport.gd.
@export var climb_speed: float = 3.0

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
	# Respect dedicated actions if the project defined them...
	if InputMap.has_action("move_left"):
		return Vector2(
			Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
			Input.get_action_strength("move_back") - Input.get_action_strength("move_forward"))
	# ...otherwise read WASD AND arrow keys directly, so both work with zero setup.
	var x := 0.0
	var y := 0.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): x += 1.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):  x -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):  y += 1.0
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):    y -= 1.0
	return Vector2(x, y)


func _physics_process(delta: float) -> void:
	# On a ladder volume? Climb instead of walking (Space drops off).
	if _current_ladder() != null and not Input.is_key_pressed(KEY_SPACE):
		_climb(delta)
		return

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


func _current_ladder() -> Area3D:
	# The ladder climb volumes are Area3Ds in the "ladder" group (built by the
	# post-import from each LADDER_ marker). We're "on" one if our body overlaps.
	for a in get_tree().get_nodes_in_group("ladder"):
		if a is Area3D and self in (a as Area3D).get_overlapping_bodies():
			return a
	return null


func _climb(delta: float) -> void:
	# Move along the camera's look direction: look up + forward to ascend, look
	# down to descend, look level + forward to step off at the top. Gravity is
	# off here so no input means you cling in place instead of sliding down.
	var axis := _move_axis()           # axis.y < 0 == forward (W / up-arrow)
	var wish := -axis.y                # forward press -> +1
	var look := -_camera.global_transform.basis.z if _camera else -transform.basis.z
	velocity = look * wish * climb_speed
	# small strafe so you can line up with the hole at the top
	velocity += transform.basis.x * axis.x * (speed * 0.5)
	move_and_slide()
