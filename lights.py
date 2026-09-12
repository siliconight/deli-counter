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

#: Metres between ceiling fixtures. 4.0, up from 3.0 (2026-08-24): census #4
#: left exactly 9 meshes over the per-mesh budget of 8, every one a b0/b1/b4
#: floor or slab tile at 9-10 lights -- dense-room lamp COUNT, not range or
#: geometry, was the residue (ranges were already drop-derived and the tiles
#: budget-sized). A quarter fewer lamps per row puts those tiles under 8,
#: and the wider pools read more like a 90s interior than an office grid --
#: the look this palette is chasing anyway. If a room reads too dark, raise
#: rig energy in Lux; density is a budget number first.
_TARGET_SPACING = 4.0

#: The 90s below-grade rule (roadmap 57's palette, first entry): a basement or
#: an objective room -- a vault, a count room -- does not get an office
#: ceiling row. It gets sparse bare bulbs, one moody pool per this many square
#: metres, hanging on a cord below the slab. Lux reads the `pendant` type as a
#: warm incandescent omni with a tight, drop-derived range.
_PENDANT_AREA = 25.0    # m^2 of room per bare bulb
_PENDANT_CORD = 0.6     # metres of cord between slab underside and bulb
#: Density guardrails, added after census #5 measured the first law's
#: failure: area/25 alone gave the arena's 275 m^2 skybox suite ELEVEN
#: bulbs 1.5 m apart -- a chandelier row, not a moody cellar, and every
#: ceiling tile under it blew the per-mesh budget. Bulbs are capped per
#: room and never packed tighter than a real cord spacing; a big room is
#: supposed to have dark corners -- that is what "moody" MEANS.
_PENDANT_MAX = 5        # bulbs per room, however big the room
_PENDANT_MIN_SPACING = 3.5   # metres between bulbs, minimum
_MAX_FIXTURES = 5       # cap a single room's row
_CEILING_GAP = 0.1      # hang fixtures this far below the ceiling PLANE

#: A ceiling row must not put a lamp INSIDE a partition. Walked 2026-09-11 on
#: cold run 9005's hospital as "light inside the wall": nine lamp points on
#: that shell sat at -0.150 m, the partition centreline exactly -- the lobby
#: and ward rows at x = +-8.0 crossing the ward partitions, and the roof's
#: bulb row lying ALONG the y = 0 spine (roadmap 143). A row laid across a
#: room's length at its derived spacing lands on a partition whenever the
#: partitions fall on that spacing, which the library's rooms happened not
#: to and this hospital's do (`tools/anchor_wall_probe.py`: 2,422 library
#: lamp points, none inside a wall; this shell, 9 of 35).
#:
#: The clearance a lamp CENTRE keeps from a wall's CENTRELINE is derived,
#: not chosen: half the wall (the caller's `wall_thick`, 0.30 on 18,469 of
#: the shipped wall slots) + half the fixture across the row + an air gap.
#: The fixture is Zoo's `fluorescent_fixture` troffer, `depth` default 0.3
#: (0.2..0.6) in its genome; the gap is `_CEILING_GAP`, the same air the
#: row already keeps below the ceiling plane. 0.15 + 0.15 + 0.10 = 0.40 m
#: for a 0.30 wall.
_FIXTURE_DEPTH = 0.3
_FIXTURE_GAP = _CEILING_GAP


def wall_clearance(wall_thick):
    """Lamp-centre to wall-centreline clearance, metres (derivation above)."""
    return float(wall_thick) * 0.5 + _FIXTURE_DEPTH * 0.5 + _FIXTURE_GAP


def _g(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def partition_rects(partitions, wall_thick, pieces=None):
    """Interior walls as world XY rects: ``[{story, x0, y0, x1, y1}]``.

    ``partitions`` are spec `Partition`s (or dicts with the same keys): an
    ``axis`` ("X" runs along x at y = ``pos``; "Y" along y at x = ``pos``)
    and a ``start``..``end`` span. ``pieces`` is the builder's
    ``_partition_pieces`` -- ``{index: [(lo, hi), ...]}`` -- the spans that
    were actually built after the envelope and the stairwell voids trimmed
    them; a partition with no entry is taken at its authored span. The
    thickness is the caller's, the same number the wall emitters build to.
    """
    t = float(wall_thick) * 0.5
    out = []
    for i, p in enumerate(partitions or ()):
        spans = (pieces or {}).get(i) if pieces else None
        if not spans:
            a, b = float(_g(p, "start")), float(_g(p, "end"))
            spans = [(min(a, b), max(a, b))]
        pos = float(_g(p, "pos"))
        for lo, hi in spans:
            lo, hi = float(lo), float(hi)
            if str(_g(p, "axis")) == "X":
                r = (lo, pos - t, hi, pos + t)
            else:
                r = (pos - t, lo, pos + t, hi)
            out.append({"story": int(_g(p, "story", 0) or 0),
                        "x0": round(r[0], 4), "y0": round(r[1], 4),
                        "x1": round(r[2], 4), "y1": round(r[3], 4)})
    return out


def _band(w, clear):
    """The keep-out rect around a wall: ``clear`` either side of its
    CENTRELINE across the thin axis (``clear`` already holds half the wall,
    see `wall_clearance`), and the same air past each end face along it."""
    hx, hy = (w["x1"] - w["x0"]) * 0.5, (w["y1"] - w["y0"]) * 0.5
    cx, cy = (w["x0"] + w["x1"]) * 0.5, (w["y0"] + w["y1"]) * 0.5
    if hx <= hy:                      # thin in x: runs along y
        ex, ey = clear, hy + max(clear - hx, 0.0)
    else:                             # thin in y: runs along x
        ex, ey = hx + max(clear - hy, 0.0), clear
    return (cx - ex, cy - ey, cx + ex, cy + ey)


def _colinear_shift(bounds, rot, walls, clear):
    """Where a partition runs ALONG the row -- its band contains the row's
    line over at least half the row's length -- the row is not crossing a
    wall, it is lying in one, and no point-wise nudge can save it. The
    partition has divided the room into two spaces; the row moves to the
    centre of the larger one (equal: the positive side). Returns the new
    perpendicular coordinate, or None when no wall is colinear.

    One row, one side, on purpose: the other side stays unlit and the
    caller reports the shift so a re-walk can judge whether that space
    wanted its own row -- which is a room-splitting question for the spec,
    not a lighting one.
    """
    minx, miny, maxx, maxy = bounds
    along_x = abs(rot) < 45.0
    if along_x:
        perp, lo, hi, a0, a1 = (miny + maxy) / 2.0, miny, maxy, minx, maxx
    else:
        perp, lo, hi, a0, a1 = (minx + maxx) / 2.0, minx, maxx, miny, maxy
    row_len = max(a1 - a0, 1e-9)
    for w in walls or ():
        b = _band(w, clear)
        if along_x:
            p0, p1, s0, s1 = b[1], b[3], w["x0"], w["x1"]
        else:
            p0, p1, s0, s1 = b[0], b[2], w["y0"], w["y1"]
        if not (p0 <= perp <= p1):
            continue
        overlap = min(s1, a1) - max(s0, a0)
        if overlap < 0.5 * row_len:
            continue
        wc = (p0 + p1) / 2.0
        below, above = wc - lo, hi - wc
        side = (wc, hi) if above >= below else (lo, wc)
        return round((side[0] + side[1]) / 2.0, 3)
    return None

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
#
# PROUD OF THE FACE, NOT OF THE CENTRELINE. An opening's (x, y) is the wall's
# centreline -- measured 2026-09-11 over 425 exterior doors in 125 shipped
# buildings, every one at 0.000 from its wall's centre -- and these offsets
# were added to that point directly, so a pack's emitter landed ON the face
# of a 0.30 m wall (0.025 m inside a 0.35 m one) and a sign's face plane
# 0.05 m proud of it. Zoo builds both fixtures on the promise written above:
# the wall pack's 0.22 m body is centred on the anchor with an arm reaching
# 0.15 m back to the wall plane, the sign's 0.18 m cabinet hangs entirely
# behind its face. So half the pack and most of the cabinet were inside the
# wall -- the "hanging light half-buried at a wall/ceiling junction" that
# roadmap 85 was raised on. `tools/anchor_wall_probe.py` is the instrument:
# wall_pack clearance to the nearest wall read median 0.000 / min -0.025,
# sign 0.050, across 334 packs and 91 signs. Half the wall's thickness is
# added now, so the constants mean what they say.
_WALL_PACK_OUT = 0.15   # emitter proud of the wall FACE
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


def _row_runs(centre, rot, count, spacing, voids, walls=None, clear=0.0,
              report=None):
    """Split a ceiling row into contiguous RUNS that miss every ceiling void
    and step every lamp point off the partitions it would otherwise hang in.

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

    ``walls`` are `partition_rects` on this storey and ``clear`` is
    `wall_clearance`. A point whose centre lands within ``clear`` of a
    wall's band is NUDGED along the row to the nearer edge of that band,
    provided the landing is clear of every wall and void and no further than
    half a spacing away (so it stays inside the room, whose row is inset by
    half a spacing from its bounds). A nudged point is its own run -- a run's
    points are equally spaced by contract, and the nudge breaks that. A
    point with nowhere to go is DROPPED and counted, not silently kept in
    the wall. ``report`` (a dict) receives the counts.
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

    bands = [_band(w, clear) for w in (walls or ())]

    def _walls_at(x, y):
        # strict: a point exactly `clear` from the centreline is clear
        return [b for b in bands if b[0] < x < b[2] and b[1] < y < b[3]]

    along_x = abs(rot) < 45.0
    max_shift = (spacing if spacing > 0.0 else _TARGET_SPACING) * 0.5
    rep = report if report is not None else {}
    rep.setdefault("nudged", 0)
    rep.setdefault("dropped", 0)

    tagged = []
    for x, y in pts:
        if _in_void(x, y):
            tagged.append((x, y, "void"))
            continue
        hit = _walls_at(x, y)
        if not hit:
            tagged.append((x, y, "ok"))
            continue
        cands = []
        for (bx0, by0, bx1, by1) in hit:
            cands += ([(bx0, y), (bx1, y)] if along_x
                      else [(x, by0), (x, by1)])
        cands = [(cx, cy) for cx, cy in cands
                 if not _walls_at(cx, cy) and not _in_void(cx, cy)
                 and abs(cx - x) + abs(cy - y) <= max_shift + 1e-9]
        if cands:
            cx, cy = min(cands, key=lambda c: abs(c[0] - x) + abs(c[1] - y))
            tagged.append((round(cx, 3), round(cy, 3), "nudged"))
            rep["nudged"] += 1
        else:
            tagged.append((x, y, "dropped"))
            rep["dropped"] += 1

    runs, cur = [], []
    for x, y, kind in tagged:
        if kind == "ok":
            cur.append((x, y))
            continue
        if cur:
            runs.append(cur)
            cur = []
        if kind == "nudged":
            runs.append([(x, y)])
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


def _storefront_sign(openings, wall_thick):
    """The building's one derived sign: above the widest door on the facade
    with the most windows. A facade with windows and a door is a storefront;
    a building with no exterior windows gets no derived sign (a foundry's
    service doors aren't signage — authored anchors can always add one).
    Deterministic: window count, then door width, then wall name.

    ``wall_thick`` is the wall the door is in; the face plane goes
    ``_SIGN_OUT`` beyond that wall's FACE, half a thickness out from the
    opening's centreline coordinate."""
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
    out = float(wall_thick) * 0.5 + _SIGN_OUT
    return {
        "id": "%s_sign" % d["wall"],
        "type": "sign",
        "source": "derived",
        "pos": [round(float(d.get("x", 0.0)) + ox * out, 3),
                round(float(d.get("y", 0.0)) + oy * out, 3),
                round(_opening_top(d) + _SIGN_RISE, 3)],
        "rot_y": rot,
        "wall": d["wall"],
        "size": [w, _SIGN_H],
        "reacts_to_alarm": True,
    }, d


def derive_light_anchors(rooms, openings, story_height, *, cap_thick,
                         wall_thick, ceiling_voids=None, partitions=None,
                         report=None):
    """Derive default light anchors: one fluorescent ceiling row per interior
    room, one area light per window opening, a wall pack over every exterior
    door, and one storefront sign.

    `cap_thick` is the thickness of the slab capping a storey -- either a float,
    or a callable taking the storey index (top storeys can be capped by a roof
    of different thickness than a floor). It is REQUIRED and has no default on
    purpose: a default of zero would silently reproduce the defect it exists to
    fix, and this kit does not ship guards that pass by omission.

    `wall_thick` is the exterior wall's thickness, and is required for the
    same reason: the facade emitters are placed proud of the wall FACE, and
    an opening's coordinate is the wall's centreline, so without it the pack
    and sign land inside the wall they hang on (see `_WALL_PACK_OUT`).

    `partitions` are `partition_rects` -- the interior walls as world rects
    with a storey -- and are optional the way `ceiling_voids` are: a caller
    that has none gets rows laid across the room as before, and must say so.
    With them, a row steps off every partition it would cross and moves off
    any it would lie along (`_row_runs`, `_colinear_shift`). `report`, a
    dict, receives the counts: nudged, dropped, rows_shifted.
    """
    anchors = []
    rep = report if report is not None else {}
    rep.setdefault("rows_shifted", 0)
    clear = wall_clearance(wall_thick)
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
        # Below grade, or guarding the take: bare bulbs instead of the office
        # row. Same run machinery (a stairwell still splits the line around
        # its hole), different type, density and hang -- see _PENDANT_AREA.
        moody = story < 0 or bool(r.get("objective"))
        if moody:
            w = bounds[2] - bounds[0]
            d = bounds[3] - bounds[1]
            long_axis = max(w, d)
            count = max(1, min(int(round((w * d) / _PENDANT_AREA)),
                               _PENDANT_MAX,
                               int(long_axis / _PENDANT_MIN_SPACING) or 1))
            spacing = round(long_axis / count, 3)
        lamp_z = round(ceiling_z - _PENDANT_CORD, 3) if moody else ceiling_z
        # A row is laid across the whole room; a stairwell punched through the
        # ceiling is a hole in the middle of it. Split around the holes on this
        # storey -- see `_row_runs`.
        holes = [v for v in (ceiling_voids or ())
                 if int(v.get("story", story)) == story]
        rects = [(v["x0"], v["y0"], v["x1"], v["y1"]) for v in holes]
        walls = [w for w in (partitions or ()) if int(w["story"]) == story]
        # A partition ALONG the row (the hospital roof's y = 0 spine under a
        # row laid at y = 0) is not a crossing: the row moves to the larger
        # side of it before any point is judged.
        rx, ry = c[0], c[1]
        shifted = _colinear_shift(bounds, rot, walls, clear)
        if shifted is not None:
            if abs(rot) < 45.0:
                ry = shifted
            else:
                rx = shifted
            rep["rows_shifted"] += 1
        runs = _row_runs([rx, ry, lamp_z], rot, count, spacing, rects,
                         walls=walls, clear=clear, report=rep)
        base_id = ("%s_bulbs" if moody else "%s_ceiling") % r.get("id", "room")
        for i, (pos, n, sp) in enumerate(runs):
            anchors.append({
                # A single surviving run keeps the ORIGINAL id: splitting is
                # the exception, and a room that never had a hole must not get
                # a renamed anchor (ids are how authored overrides bind).
                "id": base_id if len(runs) == 1 else "%s_%d" % (base_id, i),
                "type": "pendant" if moody else "fluorescent",
                "source": "derived",
                "pos": pos,
                "rot_y": rot,
                "room": r.get("id"),
                "row": {"count": n, "spacing": sp},
                # DROP: metres from this lamp down to its own room's floor.
                # Lux derives the omni RANGE from it (>= 0.19), because a
                # flat range is wrong at both ends: at 8.0 a lamp claimed a
                # per-mesh light-budget slot on tiles two rooms away through
                # the walls (roadmap 54's brightness grid), and at a flat
                # 4.5 the arena's ~5.7 m hall had lit ceilings over a
                # PITCH-BLACK floor -- attenuation reaches hard zero at the
                # range, so no energy value lights a floor the range does
                # not reach. Only this kit knows the room's height; the
                # anchor carries it so the rig never has to guess. A pendant
                # hangs on its cord, so its drop is measured from the BULB.
                "drop": round(lamp_z - c[2], 3),
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
    sign = _storefront_sign(openings, wall_thick)
    sign_door = None
    if sign:
        anchor, sign_door = sign
        anchors.append(anchor)

    pack_out = float(wall_thick) * 0.5 + _WALL_PACK_OUT
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
            "pos": [round(float(d.get("x", 0.0)) + ox * pack_out, 3),
                    round(float(d.get("y", 0.0)) + oy * pack_out, 3),
                    round(_opening_top(d) + _WALL_PACK_RISE, 3)],
            "rot_y": rot,
            "wall": wall,
            "reacts_to_alarm": True,
        })
    return anchors


def build_light_manifest(building_id, rooms, openings, story_height,
                         *, cap_thick, wall_thick, authored=None, theme=None,
                         ceiling_voids=None, partitions=None, report=None):
    """Full `<name>.lights.json` manifest. `authored` is an optional list of
    hand-placed anchors; an authored anchor replaces a derived one with the
    same id (auto defaults + spec overrides, like props)."""
    anchors = derive_light_anchors(rooms, openings, story_height,
                                   cap_thick=cap_thick, wall_thick=wall_thick,
                                   ceiling_voids=ceiling_voids,
                                   partitions=partitions, report=report)
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
