@tool
extends EditorScript
## Deli Counter — parts-kit MeshLibrary generator
## =============================================================================
## OPTIONAL companion to the baked .glb pipeline. Generates a MeshLibrary of
## generic, grid-aligned modular pieces (wall / doorway / floor / stair /
## counter…) so you can hand-greybox a fresh blockout in a GridMap, by hand, in
## the editor — separate from and complementary to the deterministic baked
## shells the tool's main pipeline produces.
##
## This does NOT change the core: the .glb is still the primary, replication-
## free output. This is a second artifact for a different workflow (sketching a
## layout by eye on a grid) for anyone who wants it; ignore it otherwise.
##
## Dimensions follow the kit's scale guidelines: 0.5 m main grid, 1.0 m
## structural, 3 m story height, 0.2 m wall thickness, 2.2 m doorways.
##
## HOW TO RUN: open this file in the Godot script editor and File > Run (or
## Ctrl+Shift+X). It writes deli_counter_kit.meshlib next to this script. Then
## add a GridMap node, set its Mesh Library to that file, set Cell Size to
## (1, 1, 1) — or (0.5, 3, 0.5) to match the fine grid — and paint.
##
## Built in-engine (not hand-packed) so the mesh + collision data is always
## valid — Godot serializes it via ResourceSaver.

const STORY_H := 3.0
const WALL_T := 0.2
const CELL := 1.0          # base structural cell the modules are sized around
const DOOR_H := 2.2
const DOOR_W := 1.2

func _run() -> void:
	var lib := MeshLibrary.new()
	var id := 0

	# --- floor / ceiling tile: 1x1 m slab, thin ---
	id = _add_box(lib, id, "floor_1x1", Vector3(CELL, WALL_T, CELL),
		Vector3(0, WALL_T / 2, 0))

	# --- solid wall segment: 1 m wide, full story tall ---
	id = _add_box(lib, id, "wall_1m", Vector3(CELL, STORY_H, WALL_T),
		Vector3(0, STORY_H / 2, 0))

	# --- half wall / railing: 1 m wide, 1.1 m tall (cover height) ---
	id = _add_box(lib, id, "wall_half_1m", Vector3(CELL, 1.1, WALL_T),
		Vector3(0, 0.55, 0))

	# --- doorway wall: 1 m wide wall with a 1.2 m x 2.2 m hole, as 3 boxes
	#     (left jamb, right jamb, lintel). Approximated to one structural cell;
	#     for a wider opening, paint two side-by-side. ---
	id = _add_doorway(lib, id, "wall_door_1m")

	# --- window wall: 1 m wide wall with a mid-height opening ---
	id = _add_window(lib, id, "wall_window_1m")

	# --- pillar: 0.4 m square column, full story ---
	id = _add_box(lib, id, "pillar", Vector3(0.4, STORY_H, 0.4),
		Vector3(0, STORY_H / 2, 0))

	# --- counter / low shelf unit: 1 m x 0.6 m x 1.0 m (deli-counter scale) ---
	id = _add_box(lib, id, "counter_unit", Vector3(CELL, 1.0, 0.6),
		Vector3(0, 0.5, 0))

	# --- stair module: a full-story switchback-free straight flight that fits
	#     one structural cell in plan, rising STORY_H over its run ---
	id = _add_stair(lib, id, "stair_flight")

	# --- crate / cover block: 1 m cube ---
	id = _add_box(lib, id, "crate_1m", Vector3(CELL, CELL, CELL),
		Vector3(0, CELL / 2, 0))

	var out := (get_script() as Script).resource_path.get_base_dir() \
		+ "/deli_counter_kit.meshlib"
	var err := ResourceSaver.save(lib, out)
	if err == OK:
		print("[meshlib_kit] wrote %s with %d items" % [out, lib.get_item_list().size()])
	else:
		push_error("[meshlib_kit] save failed: %d" % err)


func _box_mesh(size: Vector3) -> BoxMesh:
	var m := BoxMesh.new()
	m.size = size
	return m


## adds a single-mesh item with a box collision matching the mesh
func _add_box(lib: MeshLibrary, id: int, name: String, size: Vector3,
		offset: Vector3) -> int:
	lib.create_item(id)
	lib.set_item_name(id, name)
	var mesh := _box_mesh(size)
	# bake the offset into the mesh via a wrapping ArrayMesh transform isn't
	# directly possible on BoxMesh; instead offset the collision + rely on the
	# GridMap cell origin. For simplicity the box is centered; offset is applied
	# to the collision shape transform below.
	lib.set_item_mesh(id, mesh)
	lib.set_item_mesh_transform(id, Transform3D(Basis(), offset))
	var shape := BoxShape3D.new()
	shape.size = size
	lib.set_item_shapes(id, [shape, Transform3D(Basis(), offset)])
	return id + 1


## doorway: left jamb + right jamb + lintel, as one merged ArrayMesh, with
## matching collision boxes
func _add_doorway(lib: MeshLibrary, id: int, name: String) -> int:
	lib.create_item(id)
	lib.set_item_name(id, name)
	var side := (CELL - DOOR_W) / 2.0      # width of each jamb
	var lintel_h := STORY_H - DOOR_H
	var parts := [
		# [size, center]
		[Vector3(side, STORY_H, WALL_T), Vector3(-(DOOR_W + side) / 2, STORY_H / 2, 0)],
		[Vector3(side, STORY_H, WALL_T), Vector3((DOOR_W + side) / 2, STORY_H / 2, 0)],
		[Vector3(DOOR_W, lintel_h, WALL_T), Vector3(0, DOOR_H + lintel_h / 2, 0)],
	]
	_set_multibox(lib, id, parts)
	return id + 1


## window: left jamb + right jamb + sill + lintel
func _add_window(lib: MeshLibrary, id: int, name: String) -> int:
	lib.create_item(id)
	lib.set_item_name(id, name)
	var win_w := 1.0
	var win_sill := 1.0
	var win_h := 1.2
	var side := (CELL - win_w) / 2.0
	var top := win_sill + win_h
	var parts := [
		[Vector3(side, STORY_H, WALL_T), Vector3(-(win_w + side) / 2, STORY_H / 2, 0)],
		[Vector3(side, STORY_H, WALL_T), Vector3((win_w + side) / 2, STORY_H / 2, 0)],
		[Vector3(win_w, win_sill, WALL_T), Vector3(0, win_sill / 2, 0)],
		[Vector3(win_w, STORY_H - top, WALL_T), Vector3(0, top + (STORY_H - top) / 2, 0)],
	]
	_set_multibox(lib, id, parts)
	return id + 1


## straight stair flight rising STORY_H over a 1-cell run, as stacked steps
func _add_stair(lib: MeshLibrary, id: int, name: String) -> int:
	lib.create_item(id)
	lib.set_item_name(id, name)
	var n := 16
	var step_h := STORY_H / n
	var run := CELL * 4.0          # a flight spans ~4 cells in plan
	var step_d := run / n
	var parts := []
	for i in range(n):
		var cz := -run / 2 + step_d * (i + 0.5)
		var cy := step_h * (i + 0.5)
		# each step is as tall as its position so it reads as a solid staircase
		parts.append([Vector3(CELL, step_h * (i + 1), step_d),
			Vector3(0, step_h * (i + 1) / 2, cz)])
	_set_multibox(lib, id, parts)
	return id + 1


## build one item's mesh + collision from a list of [size, center] boxes
func _set_multibox(lib: MeshLibrary, id: int, parts: Array) -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for p in parts:
		_append_box(st, p[0], p[1])
	st.generate_normals()
	var mesh := st.commit()
	lib.set_item_mesh(id, mesh)
	var shapes := []
	for p in parts:
		var shape := BoxShape3D.new()
		shape.size = p[0]
		shapes.append(shape)
		shapes.append(Transform3D(Basis(), p[1]))
	lib.set_item_shapes(id, shapes)


## append a box's 12 triangles to a SurfaceTool
func _append_box(st: SurfaceTool, size: Vector3, c: Vector3) -> void:
	var h := size / 2.0
	var v := [
		c + Vector3(-h.x, -h.y, -h.z), c + Vector3(h.x, -h.y, -h.z),
		c + Vector3(h.x, h.y, -h.z), c + Vector3(-h.x, h.y, -h.z),
		c + Vector3(-h.x, -h.y, h.z), c + Vector3(h.x, -h.y, h.z),
		c + Vector3(h.x, h.y, h.z), c + Vector3(-h.x, h.y, h.z),
	]
	var faces := [
		[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7],
		[1, 5, 6, 2], [4, 5, 1, 0], [3, 2, 6, 7],
	]
	for f in faces:
		st.add_vertex(v[f[0]]); st.add_vertex(v[f[1]]); st.add_vertex(v[f[2]])
		st.add_vertex(v[f[0]]); st.add_vertex(v[f[2]]); st.add_vertex(v[f[3]])
