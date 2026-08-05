"""Light anchors -- Deli Counter's lighting contract (`<name>.lights.json`).

Companion to the slot/gameplay manifests: derive WHERE lights belong and WHAT
kind they are from the rooms and openings the build already computed, and hand
that to the renderer (Lux) which decides how they look. Same philosophy as the
rest of the kit: bake the static shell, emit the placement as typed anchors.

Pure -- operates on the gameplay dicts, so it runs and tests outside Blender.
See docs/LIGHT_MANIFEST.md for the schema.
"""

LIGHT_MANIFEST_VERSION = "1.1.0"

# outward wall facing (from the wall-name suffix) -> rot_y that points the
# window's area light INWARD, in degrees about up (rot_y 0 == +X).
_INWARD_ROT = {"W": 0.0, "S": 90.0, "E": 180.0, "N": 270.0}

_TARGET_SPACING = 3.0   # metres between ceiling fixtures
_MAX_FIXTURES = 5       # cap a single room's row
_CEILING_GAP = 0.1      # hang fixtures this far below the ceiling PLANE

# The ceiling of a storey is the UNDERSIDE of the slab that caps it, which is
# one slab-thickness below the next storey's floor. Deriving a fixture height
# from `floor + story_height` alone puts it on the wrong side of that slab:
# measured 2026-08-02 on `category5_baie_dore_001`, all 28 fluorescent anchors
# sat at 3.90 / 7.90 / -0.10 -- 0.10 below the floor ABOVE, and so buried 0.20 m
# inside a 0.30 m slab, invisible from either room and lighting a void. Nothing
# else in the manifest had this shape: windows, wall packs, signs and
# streetlights were all placed correctly. It was the ceiling-mounted type alone,
# and every one of them.
#
# `Building._cap_thick` is the one place that rule lives -- the wall emitters
# already subtract it ("One rule, one place, because both wall emitters need it
# and two copies drift"). This module is a third consumer that needed it and did
# not have it, so `cap_thick` is passed IN rather than recomputed here.

# v1.1 facade lights. Emitters sit PROUD of the wall, in free air, so the
# lamp Lux spawns is never inside the hardware Zoo bakes: the sign's pos is
# its FACE plane (cabinet hangs behind it, toward the wall), the wall pack's
# pos is under the wedge's overhang (body hangs above it, against the wall).
_WALL_PACK_OUT = 0.15   # emitter proud of the wall face
_WALL_PACK_RISE = 0.25  # emitter above the door head
_SIGN_OUT = 0.2         # sign FACE plane proud of the wall
_SIGN_RISE = 0.35       # sign centre above the door head
_SIGN_PAD = 0.8         # sign width beyond the door width
_SIGN_H = 0.6           # sign height
_DOOR_KINDS = ("door", "garage")


def _row_for_bounds(bounds):
    """A ceiling row runs along the room's longer axis. Returns
    (rot_y, count, spacing)."""
    minx, miny, maxx, maxy = bounds
    dx, dy = maxx - minx, maxy - miny
    if dx >= dy:
        length, rot = dx, 0.0
    else:
        length, rot = dy, 90.0
    count = max(1, min(_MAX_FIXTURES, round(length / _TARGET_SPACING)))
    spacing = round(length / count, 3) if count > 1 else 0.0
    return rot, count, spacing


def _row_runs(centre, rot, count, spacing, voids):
    """Split a ceiling row into contiguous RUNS that miss every ceiling void.

    A FIXTURE MUST BE MOUNTED TO SOMETHING. A hole is not a surface, and a
    fluorescent hanging in a stairwell opening reads as a bug on sight --
    measured on ``art_probe_001`` seed 5017, one of twenty sat at
    ``x -10.50, y 6.50`` -- inside the ``ceiling_manager_office`` void, which
    the shipped slot manifest puts at ``x -13.0..-9.0, y 4.2..9.3``.
    Deterministic, not a seed artefact: the row is laid across the whole
    ceiling and the void was never subtracted from it.

    SPLIT, DO NOT DROP. A run that stops short of a stairwell and resumes past
    it is what a real ceiling does, and it is the same call
    ``openings.apply`` already makes for conduit -- shorten rather than
    delete, because deleting the run removes light from the part of the room
    that still has a ceiling. So this returns a LIST of (pos, count, spacing)
    and the caller emits one anchor per run.

    ``voids`` are world XY rects ``(x0, y0, x1, y1)``. Returns the row
    unchanged when there are none -- but the CALLER must say out loud that it
    had none, because "no voids supplied" and "no voids hit" are different
    facts and only one of them is a pass.
    """
    cx, cy, cz = centre
    if count <= 1 or spacing <= 0.0:
        pts = [(cx, cy)]
    else:
        dx, dy = (1.0, 0.0) if abs(rot) < 45.0 else (0.0, 1.0)
        start = -(count - 1) * 0.5 * spacing
        pts = [(cx + (start + i * spacing) * dx,
                cy + (start + i * spacing) * dy) for i in range(count)]

    def _in_void(x, y):
        return any(x0 <= x <= x1 and y0 <= y <= y1
                   for (x0, y0, x1, y1) in (voids or ()))

    runs, cur = [], []
    for x, y in pts:
        if _in_void(x, y):
            if cur:
                runs.append(cur)
                cur = []
            continue
        cur.append((x, y))
    if cur:
        runs.append(cur)

    out = []
    for run in runs:
        n = len(run)
        mx = sum(p[0] for p in run) / n
        my = sum(p[1] for p in run) / n
        out.append(([round(mx, 3), round(my, 3), cz], n,
                    spacing if n > 1 else 0.0))
    return out


def _wall_facing(wall_name):
    if not wall_name:
        return None
    tok = str(wall_name).rsplit("_", 1)[-1].upper()
    return tok if tok in _INWARD_ROT else None


def _outward(facing):
    """(rot_y, unit_vector) pointing OUT of the building for a wall facing."""
    import math
    rot = (_INWARD_ROT[facing] + 180.0) % 360.0
    a = math.radians(rot)
    return rot, (math.cos(a), math.sin(a))


def _opening_top(o):
    """Top of an opening: sill + height when the builder recorded a sill
    (doors sit on it), else centre + half height."""
    h = float(o.get("height", 2.2))
    sill = o.get("sill")
    if sill is not None:
        return float(sill) + h
    return float(o.get("z", 0.0)) + h / 2.0


def _exterior_doors(openings):
    return [o for o in openings or []
            if o.get("kind") in _DOOR_KINDS
            and _wall_facing(o.get("wall")) is not None]


def _storefront_sign(openings):
    """The building's one derived sign: above the widest door on the facade
    with the most windows. A facade with windows and a door is a storefront;
    a building with no exterior windows gets no derived sign (a foundry's
    service doors aren't signage — authored anchors can always add one).
    Deterministic: window count, then door width, then wall name."""
    win_walls = {}
    for o in openings or []:
        if o.get("kind") == "window" and _wall_facing(o.get("wall")):
            win_walls[o["wall"]] = win_walls.get(o["wall"], 0) + 1
    if not win_walls:
        return None
    doors = _exterior_doors(openings)
    best = None
    for d in doors:
        wall = d.get("wall")
        wins = win_walls.get(wall, 0)
        if wins <= 0:
            continue
        key = (wins, float(d.get("width", 0.0)), str(wall))
        if best is None or key > best[0]:
            best = (key, d)
    if best is None:
        return None
    d = best[1]
    facing = _wall_facing(d["wall"])
    rot, (ox, oy) = _outward(facing)
    w = round(float(d.get("width", 1.1)) + _SIGN_PAD, 3)
    return {
        "id": "%s_sign" % d["wall"],
        "type": "sign",
        "source": "derived",
        "pos": [round(float(d.get("x", 0.0)) + ox * _SIGN_OUT, 3),
                round(float(d.get("y", 0.0)) + oy * _SIGN_OUT, 3),
                round(_opening_top(d) + _SIGN_RISE, 3)],
        "rot_y": rot,
        "wall": d["wall"],
        "size": [w, _SIGN_H],
        "reacts_to_alarm": True,
    }, d


def derive_light_anchors(rooms, openings, story_height, *, cap_thick,
                         ceiling_voids=None):
    """Derive default light anchors: one fluorescent ceiling row per interior
    room, one area light per window opening, a wall pack over every exterior
    door, and one storefront sign.

    `cap_thick` is the thickness of the slab capping a storey -- either a float,
    or a callable taking the storey index (top storeys can be capped by a roof
    of different thickness than a floor). It is REQUIRED and has no default on
    purpose: a default of zero would silently reproduce the defect it exists to
    fix, and this kit does not ship guards that pass by omission.
    """
    anchors = []
    for r in rooms or []:
        c = r.get("center")
        bounds = r.get("bounds")
        if not c or not bounds:
            continue
        story = int(r.get("story", 0) or 0)
        cap = float(cap_thick(story)) if callable(cap_thick) else float(cap_thick)
        # c[2] + story_height is the storey TOP -- the next floor's floor. The
        # ceiling is a slab lower.
        ceiling_z = round(c[2] + story_height - cap - _CEILING_GAP, 3)
        rot, count, spacing = _row_for_bounds(bounds)
        # A row is laid across the whole room; a stairwell punched through the
        # ceiling is a hole in the middle of it. Split around the holes on this
        # storey -- see `_row_runs`.
        holes = [v for v in (ceiling_voids or ())
                 if int(v.get("story", story)) == story]
        rects = [(v["x0"], v["y0"], v["x1"], v["y1"]) for v in holes]
        runs = _row_runs([c[0], c[1], ceiling_z], rot, count, spacing, rects)
        base_id = "%s_ceiling" % r.get("id", "room")
        for i, (pos, n, sp) in enumerate(runs):
            anchors.append({
                # A single surviving run keeps the ORIGINAL id: splitting is
                # the exception, and a room that never had a hole must not get
                # a renamed anchor (ids are how authored overrides bind).
                "id": base_id if len(runs) == 1 else "%s_%d" % (base_id, i),
                "type": "fluorescent",
                "source": "derived",
                "pos": pos,
                "rot_y": rot,
                "room": r.get("id"),
                "row": {"count": n, "spacing": sp},
                "reacts_to_alarm": True,
            })

    win_n = {}
    for o in openings or []:
        if o.get("kind") != "window":
            continue
        wall = o.get("wall") or "win"
        win_n[wall] = win_n.get(wall, 0) + 1
        facing = _wall_facing(wall)
        anchors.append({
            "id": "%s_window_%d" % (wall, win_n[wall]),
            "type": "window",
            "source": "derived",
            "pos": [round(o.get("x", 0.0), 3), round(o.get("y", 0.0), 3),
                    round(o.get("z", 0.0), 3)],
            "rot_y": _INWARD_ROT.get(facing, 0.0),
            "size": [o.get("width", 1.0), o.get("height", 1.0)],
            "reacts_to_alarm": False,
        })

    # v1.1: the storefront sign, then a wall pack over every other exterior
    # door. Both on building power (`reacts_to_alarm: true`) — cutting the
    # power kills the facade with the interiors, the classic heist beat.
    sign = _storefront_sign(openings)
    sign_door = None
    if sign:
        anchor, sign_door = sign
        anchors.append(anchor)

    pack_n = {}
    for d in _exterior_doors(openings):
        if d is sign_door:
            continue          # the sign cabinet occupies that spot
        facing = _wall_facing(d["wall"])
        rot, (ox, oy) = _outward(facing)
        wall = d["wall"]
        pack_n[wall] = pack_n.get(wall, 0) + 1
        anchors.append({
            "id": "%s_pack_%d" % (wall, pack_n[wall]),
            "type": "wall_pack",
            "source": "derived",
            "pos": [round(float(d.get("x", 0.0)) + ox * _WALL_PACK_OUT, 3),
                    round(float(d.get("y", 0.0)) + oy * _WALL_PACK_OUT, 3),
                    round(_opening_top(d) + _WALL_PACK_RISE, 3)],
            "rot_y": rot,
            "wall": wall,
            "reacts_to_alarm": True,
        })
    return anchors


def build_light_manifest(building_id, rooms, openings, story_height,
                         *, cap_thick, authored=None, theme=None,
                         ceiling_voids=None):
    """Full `<name>.lights.json` manifest. `authored` is an optional list of
    hand-placed anchors; an authored anchor replaces a derived one with the
    same id (auto defaults + spec overrides, like props)."""
    anchors = derive_light_anchors(rooms, openings, story_height,
                                   cap_thick=cap_thick,
                                   ceiling_voids=ceiling_voids)
    if authored:
        by_id = {a["id"]: a for a in anchors}
        for a in authored:
            a = dict(a)
            a.setdefault("source", "authored")
            aid = a["id"]
            # A row split around a ceiling void publishes `<base>_0`,
            # `<base>_1`, ... instead of `<base>` (see `_row_runs`). An
            # authored `<base>` means "I am placing this room's ceiling light
            # myself" -- so the split runs are SUPERSEDED, not joined by a
            # third fixture hanging next to them. Matching by id alone would
            # have missed them and lit the room twice, which is the failure
            # mode the split was added to avoid the mirror of.
            for k in [k for k in by_id
                      if k.startswith(aid + "_")
                      and k[len(aid) + 1:].isdigit()
                      and by_id[k].get("source") == "derived"
                      and by_id[k].get("type") == "fluorescent"]:
                del by_id[k]
            by_id[aid] = a
        anchors = list(by_id.values())
    return {
        "light_manifest_version": LIGHT_MANIFEST_VERSION,
        "building_id": building_id,
        "theme": theme or "greybox",
        "space": ("Blender Z-up, meters; rot_y = degrees about up; "
                  "pos is the fixture location -- for a ceiling row, hung "
                  "below the slab's underside, not below the floor above"),
        "rig_library": "lux",
        "anchors": anchors,
    }
