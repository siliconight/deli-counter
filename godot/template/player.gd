extends CharacterBody3D
## deli_counter player controller (test harness)
## ----------------------------------------------------------------------------
## A minimal walk + mouselook body sized to the Deli Counter scale guidelines
## (1.8 m capsule, eye at ~1.6 m). It exists to *test* generated levels — walk
## the space, confirm scale and collision — not to be your shipping player.
##
## Bind your own input actions if you like; this falls back to the built-in
## ui_* actions (arrow keys) so it runs in a fresh project with no setup.

@export var speed: float = 4.5
@export var sprint_speed: float = 7.0
@export var jump_velocity: float = 5.0
@export var mouse_sensitivity: float = 0.003
@export var gravity: float = 18.0

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
		# toggle the mouse free/captured so you can click editor UI
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	elif Input.is_key_pressed(KEY_SPACE):
		velocity.y = jump_velocity

	var input := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	var dir := (transform.basis * Vector3(input.x, 0.0, input.y)).normalized()
	var spd := sprint_speed if Input.is_key_pressed(KEY_SHIFT) else speed
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	move_and_slide()
