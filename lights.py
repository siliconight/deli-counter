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
_CEILING_GAP = 0.1      # mount fixtures this far below the ceiling

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


def derive_light_anchors(rooms, openings, story_height):
    """Derive default light anchors: one fluorescent ceiling row per interior
    room, one area light per window opening, a wall pack over every exterior
    door, and one storefront sign."""
    anchors = []
    for r in rooms or []:
        c = r.get("center")
        bounds = r.get("bounds")
        if not c or not bounds:
            continue
        ceiling_z = round(c[2] + story_height - _CEILING_GAP, 3)
        rot, count, spacing = _row_for_bounds(bounds)
        anchors.append({
            "id": "%s_ceiling" % r.get("id", "room"),
            "type": "fluorescent",
            "source": "derived",
            "pos": [round(c[0], 3), round(c[1], 3), ceiling_z],
            "rot_y": rot,
            "room": r.get("id"),
            "row": {"count": count, "spacing": spacing},
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
                         authored=None, theme=None):
    """Full `<name>.lights.json` manifest. `authored` is an optional list of
    hand-placed anchors; an authored anchor replaces a derived one with the
    same id (auto defaults + spec overrides, like props)."""
    anchors = derive_light_anchors(rooms, openings, story_height)
    if authored:
        by_id = {a["id"]: a for a in anchors}
        for a in authored:
            a = dict(a)
            a.setdefault("source", "authored")
            by_id[a["id"]] = a
        anchors = list(by_id.values())
    return {
        "light_manifest_version": LIGHT_MANIFEST_VERSION,
        "building_id": building_id,
        "theme": theme or "greybox",
        "space": ("Blender Z-up, meters; rot_y = degrees about up; "
                  "pos is the fixture location"),
        "rig_library": "lux",
        "anchors": anchors,
    }
