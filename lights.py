"""Light anchors -- Deli Counter's lighting contract (`<name>.lights.json`).

Companion to the slot/gameplay manifests: derive WHERE lights belong and WHAT
kind they are from the rooms and openings the build already computed, and hand
that to the renderer (Lux) which decides how they look. Same philosophy as the
rest of the kit: bake the static shell, emit the placement as typed anchors.

Pure -- operates on the gameplay dicts, so it runs and tests outside Blender.
See docs/LIGHT_MANIFEST.md for the schema.
"""

LIGHT_MANIFEST_VERSION = "1.0.0"

# outward wall facing (from the wall-name suffix) -> rot_y that points the
# window's area light INWARD, in degrees about up (rot_y 0 == +X).
_INWARD_ROT = {"W": 0.0, "S": 90.0, "E": 180.0, "N": 270.0}

_TARGET_SPACING = 3.0   # metres between ceiling fixtures
_MAX_FIXTURES = 5       # cap a single room's row
_CEILING_GAP = 0.1      # mount fixtures this far below the ceiling


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


def derive_light_anchors(rooms, openings, story_height):
    """Derive default light anchors: one fluorescent ceiling row per interior
    room, one area light per window opening."""
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
