extends SceneTree
## deli_counter import gate -- the coordinate round-trip's ENGINE leg (Godot 4)
## ----------------------------------------------------------------------------
## roundtrip.py proves the contract survives export by re-importing the GLB in
## Blender. THIS script proves it survives the crossing that actually matters:
## Godot's own glTF import. Same manifest "expected" block, same tolerance
## table, so the two legs can never drift apart.
##
##   godot4 --headless --script godot/addon/deli_counter/import_gate.gd -- \
##       build/<name>.glb [out.json]
##
## Reads build/<name>.manifest.json next to the glb. Checks (GI-* codes):
##   GI-SCALE    every imported Node3D at unit positive scale
##   GI-BOUNDS   visual AABB matches expected bounds (Z-up -> Y-up converted)
##   GI-ORIGIN   geometry straddles the building origin; ground at y <= tol
##   GI-MARKERS  marker empties land within tolerance of expected positions
##
## Coordinate contract (docs/COORDINATE_CONTRACT.md): expectations are
## recorded in spec/Blender Z-up space; the glTF crossing maps
## (x, y_north, z_up) -> Godot (x, z_up, -y_north). This script converts the
## EXPECTATIONS and compares in Godot space -- the import itself is what is
## under test, so nothing on the imported side is "corrected".
##
## Exit code 0 = pass, 1 = tolerance breach, 2 = bad input.
## Writes <name>.godot_import.json (or the given out path).

const TOL_BOUNDS := 0.02        # m -- keep in sync with roundtrip.py TOLERANCES
const TOL_MARKER := 0.05
const TOL_FLOOR := 0.02
const TOL_SCALE := 0.0001

var _exit_code := 0


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 1:
		printerr("[import-gate] usage: godot4 --headless --script import_gate.gd -- shell.glb [out.json]")
		_exit_code = 2
		quit(_exit_code)
		return
	var glb_path: String = args[0]
	var out_path: String = args[1] if args.size() > 1 else \
		glb_path.get_basename() + ".godot_import.json"

	var result := _run(glb_path)
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(result, "  "))
		f.close()
	print("[import-gate] wrote %s" % out_path)
	quit(_exit_code)


func _run(glb_path: String) -> Dictionary:
	var result := {"glb": glb_path, "ok": false, "checks": [], "error": ""}

	var man_path := glb_path.get_basename() + ".manifest.json"
	var man_text := FileAccess.get_file_as_string(man_path)
	if man_text.is_empty():
		result["error"] = "no manifest next to glb: " + man_path
		_exit_code = 2
		return result
	var man: Variant = JSON.parse_string(man_text)
	if man == null or not man.has("expected"):
		result["error"] = "manifest has no 'expected' block -- rebuild with >= 0.79"
		_exit_code = 2
		return result
	var expected: Dictionary = man["expected"]

	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(glb_path, state)
	if err != OK:
		result["error"] = "cannot load glb (%d)" % err
		_exit_code = 2
		return result
	# NOTE: the scene is inspected WITHOUT entering the tree -- in 4.7
	# --script mode, nodes added during _initialize are not inside the tree
	# yet, so global transforms read as identity. All walks below accumulate
	# transforms manually and never query global state.
	var level := doc.generate_scene(state)

	# -- GI-SCALE ------------------------------------------------------------
	var bad_scale: Array = []
	_walk_scales(level, bad_scale)
	if bad_scale.is_empty():
		_ok(result, "GI-SCALE", "all nodes at unit positive scale")
	else:
		_fail(result, "GI-SCALE", "%d node(s) violate the unit-scale contract: %s"
			% [bad_scale.size(), str(bad_scale.slice(0, 8))])

	# -- GI-BOUNDS (Z-up expected -> Y-up godot) -----------------------------
	var lo_b: Array = expected["bounds_min"]
	var hi_b: Array = expected["bounds_max"]
	# x stays; godot y = blender z; godot z = -blender y (range flips)
	var exp_lo := Vector3(lo_b[0], lo_b[2], -hi_b[1])
	var exp_hi := Vector3(hi_b[0], hi_b[2], -lo_b[1])
	var aabb: Variant = _visual_aabb(level)
	if aabb == null:
		_fail(result, "GI-BOUNDS", "no visual meshes in imported scene")
	else:
		var box: AABB = aabb
		var got_lo: Vector3 = box.position
		var got_hi: Vector3 = box.position + box.size
		var worst := 0.0
		for i in 3:
			worst = maxf(worst, absf(got_lo[i] - exp_lo[i]))
			worst = maxf(worst, absf(got_hi[i] - exp_hi[i]))
		if worst > TOL_BOUNDS:
			_fail(result, "GI-BOUNDS",
				"imported bounds drift %.1f cm (max %.0f cm): got %s..%s expected %s..%s"
				% [worst * 100.0, TOL_BOUNDS * 100.0, got_lo, got_hi, exp_lo, exp_hi])
		else:
			_ok(result, "GI-BOUNDS", "bounds drift %.2f mm within %.0f cm"
				% [worst * 1000.0, TOL_BOUNDS * 100.0])

		# -- GI-ORIGIN -------------------------------------------------------
		var straddle := got_lo.x <= 0.0 and 0.0 <= got_hi.x \
			and got_lo.z <= 0.0 and 0.0 <= got_hi.z
		var ground_ok := got_lo.y <= TOL_FLOOR
		if straddle and ground_ok:
			_ok(result, "GI-ORIGIN", "origin at footprint-center, ground at y<=tol")
		else:
			_fail(result, "GI-ORIGIN",
				"imported geometry does not straddle the origin/ground: %s..%s"
				% [got_lo, got_hi])

	# -- GI-MARKERS ----------------------------------------------------------
	var empties := {}
	_collect_empties(level, empties, Transform3D.IDENTITY)
	var exp_markers: Array = expected.get("markers", [])
	var missing := 0
	var drifted: Array = []
	for m in exp_markers:
		var mname := str(m.get("name", m.get("type", "?")))
		var p: Array = m["pos"]
		var want := Vector3(p[0], p[2], -p[1])
		var got: Variant = _match_empty(empties, mname)
		if got == null:
			missing += 1
			continue
		var d: float = 0.0
		for i in 3:
			d = maxf(d, absf((got as Vector3)[i] - want[i]))
		if d > TOL_MARKER:
			drifted.append([mname, snappedf(d, 0.0001)])
	if exp_markers.is_empty():
		pass
	elif missing == exp_markers.size():
		_ok(result, "GI-MARKERS",
			"no marker empties in GLB (%d live in gameplay.json only -- authoritative per contract)"
			% exp_markers.size())
	elif drifted.is_empty():
		_ok(result, "GI-MARKERS", "%d marker empty(ies) within %.0f cm%s"
			% [exp_markers.size() - missing, TOL_MARKER * 100.0,
			   (" (%d in gameplay.json only)" % missing) if missing > 0 else ""])
	else:
		_fail(result, "GI-MARKERS", "%d marker(s) drifted beyond %.0f cm: %s"
			% [drifted.size(), TOL_MARKER * 100.0, str(drifted.slice(0, 10))])

	result["ok"] = _exit_code == 0
	print("[import-gate] %s: %s" % [glb_path.get_file(),
		"PASS" if result["ok"] else "FAIL"])
	level.free()    # silence RID-leak chatter at exit
	return result


func _ok(result: Dictionary, code: String, msg: String) -> void:
	result["checks"].append({"code": code, "ok": true, "msg": msg})
	print("[import-gate]   ok   %s: %s" % [code, msg])


func _fail(result: Dictionary, code: String, msg: String) -> void:
	result["checks"].append({"code": code, "ok": false, "msg": msg})
	print("[import-gate]   FAIL %s: %s" % [code, msg])
	_exit_code = 1


func _walk_scales(node: Node, bad: Array) -> void:
	if node is Node3D:
		var s: Vector3 = (node as Node3D).scale
		if s.x <= 0.0 or s.y <= 0.0 or s.z <= 0.0 \
				or absf(s.x - 1.0) > TOL_SCALE or absf(s.y - 1.0) > TOL_SCALE \
				or absf(s.z - 1.0) > TOL_SCALE:
			bad.append(node.name)
	for c in node.get_children():
		_walk_scales(c, bad)


func _node_mesh(node: Node) -> Mesh:
	## a runtime glTF load can yield MeshInstance3D OR ImporterMeshInstance3D
	## (4.6+); read the mesh by property and normalize to a renderable Mesh
	var mv: Variant = node.get("mesh")
	if mv == null:
		return null
	if mv is Mesh:
		return mv
	if mv is ImporterMesh:
		return (mv as ImporterMesh).get_mesh()
	return null


func _visual_aabb(node: Node) -> Variant:
	var boxes: Array = []
	_collect_aabbs(node, boxes, Transform3D.IDENTITY)
	if boxes.is_empty():
		return null
	var merged: AABB = boxes[0]
	for i in range(1, boxes.size()):
		merged = merged.merge(boxes[i])
	return merged


func _collect_aabbs(node: Node, boxes: Array, xform: Transform3D) -> void:
	var x := xform
	if node is Node3D:
		x = xform * (node as Node3D).transform
	var mesh: Mesh = _node_mesh(node)
	if mesh != null and not ("colonly" in node.name.to_lower()):
		boxes.append(x * mesh.get_aabb())
	for c in node.get_children():
		_collect_aabbs(c, boxes, x)


func _collect_empties(node: Node, out: Dictionary, xform: Transform3D) -> void:
	# a glTF "empty" imports as a mesh-less Node3D; record its ACCUMULATED
	# position (never global_position -- the scene is not in the tree)
	var x := xform
	if node is Node3D:
		x = xform * (node as Node3D).transform
		if _node_mesh(node) == null and node.get_child_count() >= 0 \
				and node.get_class() == "Node3D":
			out[node.name] = x.origin
	for c in node.get_children():
		_collect_empties(c, out, x)


func _match_empty(empties: Dictionary, mname: String) -> Variant:
	var want := mname.to_lower()
	for ename in empties:
		var e := str(ename).to_lower()
		if e == want or want in e:
			return empties[ename]
	return null
