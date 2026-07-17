extends SceneTree
## deli_counter nav gate -- headless stair traversal proof (Godot 4)
## ----------------------------------------------------------------------------
## The AUTHORITATIVE answer to "can a body actually walk this stair?", run
## without opening the editor:
##
##   godot4 --headless --script godot/addon/deli_counter/nav_gate.gd -- \
##       build/<name>.glb build/<name>.gameplay.json [out.json]
##
## Loads the built shell at runtime, bakes a navmesh with the same agent
## parameters as the F4 harness bake, then for every traversable stair system
## proves a polygon-graph path lower_endpoint <-> upper_endpoint. The polygon
## graph is undirected, so the reverse direction is proven by the same query;
## both endpoints must also SNAP onto the navmesh (an off-mesh endpoint is a
## landing that didn't bake -- exactly the failure this gate exists to catch).
## As a secondary section it checks every gameplay marker is reachable from
## the first spawn (the documented F5 harness check, headless).
##
## Exit code 0 = every traversable stair passes; 1 = failures; 2 = bad input.
## Machine-readable results go to out.json (default: alongside the glb).
##
## Coordinates: gameplay.json is authored in level space (Z-up, +Y north).
## The glTF export converts to Godot's Y-up as (x, y, z) -> (x, z, -y); this
## script applies the same conversion to every endpoint and marker.
##
## Stairs built before v0.76 carry no nav_endpoints in gameplay.json and are
## reported as "skipped (rebuild with >= 0.76)" -- rebuild the shell to gate.

const AGENT_RADIUS := 0.4        # keep in sync with level_test.gd / NAVMESH_CHECK.md
const AGENT_HEIGHT := 1.8
const AGENT_MAX_CLIMB := 0.5
const CELL_SIZE := 0.25
const SNAP_MAX := 2.0            # m; endpoint farther than this from the mesh = off-navmesh

var _exit_code := 0


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 2:
		printerr("[nav-gate] usage: godot4 --headless --script nav_gate.gd -- shell.glb gameplay.json [out.json]")
		_exit_code = 2
		quit(_exit_code)
		return
	var glb_path: String = args[0]
	var gp_path: String = args[1]
	var out_path: String = args[2] if args.size() > 2 else glb_path.get_basename() + ".navgate.json"

	var result := _run(glb_path, gp_path)
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(result, "  "))
		f.close()
	print("[nav-gate] wrote %s" % out_path)
	quit(_exit_code)


func _run(glb_path: String, gp_path: String) -> Dictionary:
	var result := {"glb": glb_path, "ok": false, "stairs": [], "markers": {},
				   "navmesh_polys": 0, "error": ""}

	var gp_text := FileAccess.get_file_as_string(gp_path)
	if gp_text.is_empty():
		result["error"] = "cannot read gameplay.json"
		_exit_code = 2
		return result
	var gp: Variant = JSON.parse_string(gp_text)
	if gp == null:
		result["error"] = "gameplay.json is not valid JSON"
		_exit_code = 2
		return result

	# -- load the built shell at runtime ------------------------------------
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(glb_path, state)
	if err != OK:
		result["error"] = "cannot load glb (%d)" % err
		_exit_code = 2
		return result
	var level := doc.generate_scene(state)
	root.add_child(level)

	# -- bake a navmesh over everything the glb carries ----------------------
	# A runtime GLTF load has no import-time colliders, so parse MESH
	# INSTANCES (the -colonly collision meshes are still real meshes here;
	# the stair collision RAMPS bake as clean inclines).
	var nm := NavigationMesh.new()
	nm.agent_radius = AGENT_RADIUS
	nm.agent_height = AGENT_HEIGHT
	nm.agent_max_climb = AGENT_MAX_CLIMB
	nm.cell_size = CELL_SIZE
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_MESH_INSTANCES
	var src := NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nm, src, level)
	NavigationServer3D.bake_from_source_geometry_data(nm, src)
	result["navmesh_polys"] = nm.get_polygon_count()
	if nm.get_polygon_count() == 0:
		result["error"] = "navmesh baked 0 polygons"
		print("[nav-gate] FAIL: navmesh baked 0 polygons -- nothing walkable")
		_exit_code = 1
		return result
	print("[nav-gate] navmesh: %d polys" % nm.get_polygon_count())

	var graph := _poly_graph(nm)

	# -- stairs: prove lower <-> upper --------------------------------------
	var failures := 0
	var systems: Array = gp.get("stair_systems", [])
	for sysd in systems:
		var rep := {"id": sysd.get("id", "?"), "role": sysd.get("role"),
					"status": "skipped", "detail": ""}
		if sysd.get("role") == "decorative_nontraversable":
			rep["detail"] = "decorative: never traversable by contract"
			result["stairs"].append(rep)
			continue
		var eps: Variant = sysd.get("nav_endpoints")
		if eps == null or eps.get("lower") == null or eps.get("upper") == null:
			rep["detail"] = "no nav_endpoints (rebuild with >= 0.76)"
			result["stairs"].append(rep)
			continue
		var lo := _to_godot(eps["lower"])
		var hi := _to_godot(eps["upper"])
		var lo_hit := _snap(nm, lo)
		var hi_hit := _snap(nm, hi)
		if lo_hit["dist"] > SNAP_MAX or hi_hit["dist"] > SNAP_MAX:
			rep["status"] = "off_navmesh"
			rep["detail"] = "snap lower %.2fm upper %.2fm (max %.1f)" % [
				lo_hit["dist"], hi_hit["dist"], SNAP_MAX]
			failures += 1
		elif _connected(graph, lo_hit["poly"], hi_hit["poly"]):
			rep["status"] = "ok"
			rep["detail"] = "path lower<->upper (undirected polygon graph)"
		else:
			rep["status"] = "no_path"
			rep["detail"] = "endpoints on disjoint navmesh islands"
			failures += 1
		result["stairs"].append(rep)
		print("[nav-gate] stair %s: %s -- %s" % [rep["id"], rep["status"], rep["detail"]])

	# -- markers: the documented F5 check, headless (secondary, warn-only) ---
	result["markers"] = _check_markers(gp, nm, graph)

	if failures > 0:
		print("[nav-gate] FAIL: %d stair(s) not traversable" % failures)
		_exit_code = 1
	else:
		result["ok"] = true
		print("[nav-gate] all traversable stairs pass in both directions")
	return result


func _to_godot(p: Array) -> Vector3:
	# level space (x, y_north, z_up) -> Godot (x, z_up, -y_north)
	return Vector3(p[0], p[2], -p[1])


func _poly_graph(nm: NavigationMesh) -> Array:
	## adjacency list: polys sharing a full edge are connected
	var edges := {}
	var adj: Array = []
	for i in nm.get_polygon_count():
		adj.append([])
	for i in nm.get_polygon_count():
		var poly := nm.get_polygon(i)
		for k in poly.size():
			var a := poly[k]
			var b := poly[(k + 1) % poly.size()]
			var key := "%d_%d" % [mini(a, b), maxi(a, b)]
			if edges.has(key):
				var j: int = edges[key]
				adj[i].append(j)
				adj[j].append(i)
			else:
				edges[key] = i
	return adj


func _snap(nm: NavigationMesh, p: Vector3) -> Dictionary:
	## nearest polygon by centroid; returns {poly, dist}
	var verts := nm.get_vertices()
	var best := -1
	var best_d := INF
	for i in nm.get_polygon_count():
		var poly := nm.get_polygon(i)
		var c := Vector3.ZERO
		for idx in poly:
			c += verts[idx]
		c /= poly.size()
		var d := p.distance_to(c)
		if d < best_d:
			best_d = d
			best = i
	return {"poly": best, "dist": best_d}


func _connected(adj: Array, a: int, b: int) -> bool:
	if a < 0 or b < 0:
		return false
	if a == b:
		return true
	var seen := {a: true}
	var queue := [a]
	while not queue.is_empty():
		var n: int = queue.pop_front()
		for m in adj[n]:
			if m == b:
				return true
			if not seen.has(m):
				seen[m] = true
				queue.append(m)
	return false


func _check_markers(gp: Variant, nm: NavigationMesh, graph: Array) -> Dictionary:
	var markers: Array = gp.get("markers", [])
	var spawn := Vector3.INF
	for m in markers:
		var t: String = str(m.get("type", ""))
		if t.ends_with("_spawn"):
			spawn = _to_godot([m.get("x", 0.0), m.get("y", 0.0), m.get("z", 0.0)])
			break
	if spawn == Vector3.INF:
		return {"checked": 0, "reachable": 0, "unreachable": []}
	var s_hit := _snap(nm, spawn)
	var checked := 0
	var reachable := 0
	var unreachable := []
	for m in markers:
		var t: String = str(m.get("type", ""))
		if not (t in ["objective", "extraction", "loot", "patrol_point", "rescue"]):
			continue
		checked += 1
		var p := _to_godot([m.get("x", 0.0), m.get("y", 0.0), m.get("z", 0.0)])
		var hit := _snap(nm, p)
		if hit["dist"] <= SNAP_MAX and _connected(graph, s_hit["poly"], hit["poly"]):
			reachable += 1
		else:
			unreachable.append("%s_%s (snap %.1fm)" % [t, str(m.get("id", "?")), hit["dist"]])
	print("[nav-check] %d/%d markers reachable by a nav agent from the spawn" % [reachable, checked])
	if not unreachable.is_empty():
		print("[nav-check] UNREACHABLE: %s" % ", ".join(unreachable))
	return {"checked": checked, "reachable": reachable, "unreachable": unreachable}
