"""Light anchors -- Deli Counter's lighting contract (`<name>.lights.json`).

Companion to the slot/gameplay manifests: derive WHERE lights belong and WHAT
kind they are from the rooms and openings the build already computed, and hand
that to the renderer (Lux) which decides how they look. Same philosophy as the
rest of the kit: bake the static shell, emit the placement as typed anchors.

Pure -- operates on the gameplay dicts, so it runs and tests outside Blender.
See docs/LIGHT_MANIFEST.md for the schema.
"""

LIGHT_MANIFEST_VERSION = "1.3.0"

#: A FUEL CANOPY (v1.3) is an exterior deck on columns and it is the light
#: source for the forecourt under it -- in every reference the walker
#: supplied, the tarmac is lit by the canopy and not by street lighting.
#: These are the volume names the specs author (`gas_station.json`:
#: `canopy_roof` 24 x 10 x 0.4 at z 5.0, six `canopy_col` 0.4 x 0.4 x 5.0).
_CANOPY_DECK = "canopy_roof"
_CANOPY_COL = "canopy_col"
#: Washes under one canopy: two, plus one per this much deck, to four. A
#: canopy is not a room -- there are no walls to bounce off -- so the pools
#: read as pools, which is what a forecourt at night looks like.
_CANOPY_WASH_BASE = 2
_CANOPY_WASH_PER_AREA = 150.0
_CANOPY_WASH_MAX = 4
#: The lamp grid hangs this far below the soffit. Zoo's `canopy_lights`
#: stands its lenses proud of the deck by the same amount for the same
#: reason -- a lit face flush with the deck it sits in is a coplanar pair.
_CANOPY_DROP = 0.02
#: Grade, when a canopy has no columns to measure it from. Authored decks
#: always do; this is the floor under a hand-placed one.
_CANOPY_GRADE = 0.0

#: THE CLUB SET (Lux 0.37.0): the anchor types a strip club room writes in
#: place of its fluorescent row, and the palette names Lux accepts on their
#: `color` -- an unknown name is REFUSED by the loader, never substituted,
#: so this list is Lux's `CLUB_COLOR_ORDER` byte for byte. A room's colours
#: start at crc32(room id) % 7 and step by two, so neighbouring washes differ
#: in hue and two clubs are not lit alike; deterministic.
CLUB_COLOURS = ("magenta", "hot_pink", "red", "violet", "blue", "cyan", "amber")
#: Washes per club room: three, plus one per this much floor, to five. A
#: wash pools on the floor under it (Lux: radius 1.25 x drop, 1.5-6 m), so
#: a 476 m2 main floor gets five pools and dark between them, which is what
#: "moody" means (the pendant rule's reasoning, above).
_CLUB_WASH_BASE = 3
_CLUB_WASH_PER_AREA = 200.0
_CLUB_WASH_MAX = 5
#: A stage light is two spots a stage-width apart at the ceiling, thrown at
#: the dancer's body over the platform, stepping through the palette every
#: this many seconds (Lux holds 75% of the period and crossfades the rest).
_STAGE_SPOTS = 2
_STAGE_SPOT_SPACING = 1.2
_STAGE_CYCLE_S = 4.0
_STAGE_TARGET_RISE = 0.5      # above the platform: a body, not the boards
_STAGE_THROW_BACK = 1.5       # the spots stand this far past the stage edge
_STAGE_SPOT_RADIUS = 1.5
#: The platform heights Zoo builds (`club_forms`): 0.8 m for `round` and
#: `runway`, the 1.18 m deck for `bar_stage`.
_STAGE_PLATFORM = {"bar_stage": 1.18}
_STAGE_PLATFORM_DEFAULT = 0.8
#: A neon's spill source stands this far proud of the sign's FACE, in free
#: air: Lux's omni sits AT the anchor and must never be inside the cabinet
#: (roadmap 139's lesson, restated for the club in Lux 0.37.0).
_NEON_OUT = 0.15
#: The rope light's spill: over a bar stage's deck, off the pole; just past a
#: round stage's lip at the rope's height.
_ROPE_OVER_DECK = 0.35
_ROPE_OFF_POLE = 0.5
_ROPE_LIP_OUT = 0.25
_ROPE_LIP_Z = 0.75
_ROPE_COLOUR = "amber"
#: A TV THAT IS ON (Zoo 0.90.0). The walker, after cold run 9057's club: the
#: CRTs should "have a light/glow from the screen as if they are on". Zoo
#: paints the picture and makes the glass emissive; a lit material lights
#: nothing round it in GL Compatibility, so the spill on the wall, the
#: bracket and the stools below is a `neon` anchor per set -- Lux's small
#: omni, range 0.5 x the longer `size` + 1.0 m (1.0-2.5), which at a 0.4 m
#: screen is 1.2 m: a pool round the set, not a room light. It stands this
#: far in front of the SLOT's front face, in free air (the set is tipped 8
#: degrees, so its screen's top edge is the slot's front plane).
_TV_SCREEN_OUT = 0.25
#: A tube's cold light; one of the two by crc32 of the anchor id.
_TV_COLOURS = ("cyan", "blue")
#: Only the set Zoo lights: `crt_tv`'s `bracket` form. A `stand` set is off.
_TV_SPECIES = "crt_tv"
_TV_LIT_FORM = "bracket"
#: THE BACK BAR'S PRACTICAL (Lux 0.39.0). Zoo 0.92.0 paints the bulbs
#: behind the glass shelves and the porthole's disc as emissive materials,
#: and a lit material lights nothing round it in GL Compatibility -- the
#: same finding as the TV screen, one release earlier. The spill is a
#: `back_bar` anchor per unit: a warm omni whose range is half the lit
#: face's diagonal plus the working aisle behind the bar.
#:
#: It stands this far in FRONT of the slot's front face, in free air: Lux's
#: omni sits AT the anchor and must never be inside the cabinet (roadmap
#: 139). 0.15 m is the neon's own number, and it is inside the aisle.
_BACKBAR_OUT = 0.15
_BACKBAR_SPECIES = "back_bar"
#: Zoo's `back_bar_forms`, mirrored, because Deli Counter cannot import Zoo
#: -- the same arrangement as `tv_screen_size` above, and `test_club_rooms`
#: pins it against Zoo's own numbers. The lower cabinet run's worktop is at
#: `min(COUNTER_H, h * COUNTER_SHARE)` plus `TOP_T`, the cornice takes
#: `CORNICE_H` off the top, and what is between them is the LIT FACE: the
#: glass shelves, their bulbs and the porthole.
_BACKBAR_COUNTER_H = 1.05
_BACKBAR_COUNTER_SHARE = 0.5
_BACKBAR_TOP_T = 0.04
_BACKBAR_CORNICE_H = 0.07
#: The screen's centre above the slot's centre, MEASURED off Zoo 0.90.0's
#: `crt_forms.plan_bracket` at the two sizes the club recipe places:
#: +0.0366 m at 0.6 x 0.55 x 0.5 and +0.0351 at 0.7 x 0.6 x 0.55.
_TV_SCREEN_RISE = 0.036
#: Zoo draws the set at a design height this much taller than the slot's
#: front before the tip, so the tipped bounds fit: 0.4236 m of front for a
#: 0.4 m one at 0.5 m, 0.4767 for 0.45 at 0.55 (the same 1.059 both).
_TV_TIP_GROWTH = 1.059

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


def _club_colour_start(room_id):
    import zlib
    return (zlib.crc32(str(room_id).encode("utf-8")) & 0xFFFFFFFF) % len(CLUB_COLOURS)


def _club_colour(start, i):
    return CLUB_COLOURS[(start + 2 * i) % len(CLUB_COLOURS)]


def _front_bearing(v):
    """The compass bearing (N 0, E 90) a hinted volume's module front points
    at, by the rule the slot is recorded with: long side first, +90 when
    that side is y (`prop_species.long_axis_first`), then `rot_z`; the
    front is the module's -Y, so + 180. The same arithmetic as
    `level_design._front_turn`, asked the other way round."""
    turned = float(v.get("size_y", 0.0)) > float(v.get("size_x", 0.0)) + 1e-9
    return ((90.0 if turned else 0.0) + float(v.get("rot_z", 0.0) or 0.0)
            + 180.0) % 360.0


def _bearing_to_rot_y(bearing):
    """A compass bearing (clockwise from +Y) as this manifest's rot_y
    (degrees about up, 0 == +X): the direction (sin b, cos b) has angle
    atan2(cos b, sin b) = 90 - b from +X."""
    return round((90.0 - float(bearing)) % 360.0, 3)


def _canopy_grade(deck, volumes):
    """The tarmac under ``deck``: the foot of its own columns.

    DERIVED, NOT ASSUMED TO BE ZERO. A canopy's columns stand on the surface
    its light has to reach, so they are the one thing in the spec that knows
    where that surface is. A canopy with no columns falls back to grade and
    the caller gets a `drop` that is honest about the assumption.
    """
    feet = []
    for v in volumes or ():
        if not str(v.get("name", "")).startswith(_CANOPY_COL):
            continue
        # only columns that actually stand under this deck
        if abs(float(v.get("x", 1e9)) - float(deck.get("x", 0.0))) > \
                float(deck.get("size_x", 0.0)):
            continue
        if abs(float(v.get("y", 1e9)) - float(deck.get("y", 0.0))) > \
                float(deck.get("size_y", 0.0)):
            continue
        feet.append(float(v.get("z", 0.0)) - float(v.get("size_z", 0.0)) / 2.0)
    return min(feet) if feet else _CANOPY_GRADE


def _canopy_anchors(volumes):
    """A fuel canopy's lights: one hardware grid, and a few washes.

    Emits nothing when no deck is authored, which is every building that is
    not a fuel stop. See `_CANOPY_DECK` above for why the split exists.
    """
    out = []
    for deck in volumes or ():
        name = str(deck.get("name", ""))
        if not name.startswith(_CANOPY_DECK):
            continue
        sx = float(deck.get("size_x", 0.0))
        sy = float(deck.get("size_y", 0.0))
        if sx <= 0.0 or sy <= 0.0:
            continue
        cx, cy = float(deck.get("x", 0.0)), float(deck.get("y", 0.0))
        soffit = (float(deck.get("z", 0.0))
                  - float(deck.get("size_z", 0.0)) / 2.0 - _CANOPY_DROP)
        grade = _canopy_grade(deck, volumes)

        # THE HARDWARE. One anchor for the whole deck: Zoo's `canopy_lights`
        # lays the grid inside it, in two draw calls, and carries no emitter
        # marker -- it glows and lights nothing.
        out.append({
            "id": "%s_lights" % name, "type": "canopy_lights",
            "source": "derived",
            "pos": [round(cx, 3), round(cy, 3), round(soffit, 3)],
            "rot_y": 0.0, "size": [round(sx, 3), round(sy, 3)],
            "drop": round(soffit - grade, 3), "reacts_to_alarm": True,
        })

        # THE LIGHT. A few washes, along the deck's long axis, inset so the
        # pools land on the tarmac rather than past the drip line.
        n = _CANOPY_WASH_BASE + int((sx * sy) // _CANOPY_WASH_PER_AREA)
        n = max(_CANOPY_WASH_BASE, min(_CANOPY_WASH_MAX, n))
        span, across = (sx, True) if sx >= sy else (sy, False)
        step = span / float(n)
        for i in range(n):
            off = -span / 2.0 + step * (i + 0.5)
            x = cx + off if across else cx
            y = cy if across else cy + off
            out.append({
                "id": "%s_wash_%d" % (name, i), "type": "canopy_wash",
                "source": "derived",
                "pos": [round(x, 3), round(y, 3), round(soffit, 3)],
                "rot_y": 0.0,
                # the pool this wash owns, so Lux need not divide the deck
                # itself and two canopies of different sizes light alike
                "size": [round(step, 3), round(min(sx, sy), 3)],
                "drop": round(soffit - grade, 3), "reacts_to_alarm": True,
            })
    return out


def _volumes_in(volumes, r, story_height):
    """The VISIBLE volumes standing in room `r` on its storey: centre inside
    the bounds, bottom within the storey. Invisible colliders (a stage's
    deck) are not fixtures and are skipped."""
    x0, y0, x1, y1 = r["bounds"]
    story = int(r.get("story", 0) or 0)
    floor = story * story_height
    out = []
    for v in volumes or ():
        if v.get("visual") is False:
            continue
        bottom = float(v.get("z", 0.0)) - float(v.get("size_z", 0.0)) / 2.0
        if not (floor - 0.05 <= bottom < floor + story_height - 0.05):
            continue
        if x0 <= float(v.get("x", 1e9)) <= x1 and y0 <= float(v.get("y", 1e9)) <= y1:
            out.append(v)
    return out


def _club_anchors(r, ceiling_z, floor_z, volumes, story_height, rects, walls,
                  clear, rep):
    """The club set for one room (Lux 0.37.0's four types), in place of its
    ceiling row. `volumes` are the room's visible volumes."""
    import math
    rid = r.get("id", "room")
    x0, y0, x1, y1 = r["bounds"]
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    along_x = w >= d
    long_side, short_side = (w, d) if along_x else (d, w)
    start = _club_colour_start(rid)
    drop = round(ceiling_z - floor_z, 3)
    out = []
    # WASHES along the long axis, stepping side to side across the short
    # one, each its own colour; each point through the same void and
    # partition test a fluorescent lamp gets (`_row_runs`, one point).
    n = min(_CLUB_WASH_MAX, _CLUB_WASH_BASE + int((w * d) // _CLUB_WASH_PER_AREA))
    step = long_side / n
    across = short_side / 4.0
    for i in range(n):
        u = -long_side / 2.0 + step * (i + 0.5)
        s = across if i % 2 == 0 else -across
        px, py = (cx + u, cy + s) if along_x else (cx + s, cy + u)
        runs = _row_runs([px, py, ceiling_z], 0.0, 1, 0.0, rects,
                         walls=walls, clear=clear, report=rep)
        if not runs:
            continue
        pos, _n, _sp = runs[0]
        out.append({
            "id": "%s_wash_%d" % (rid, i + 1), "type": "club_wash",
            "source": "derived", "pos": pos, "rot_y": 0.0, "room": rid,
            "color": _club_colour(start, i),
            "radius": round(min(6.0, max(1.5, short_side / 3.0)), 3),
            "row": {"count": 1, "spacing": 0.0},
            "drop": drop, "reacts_to_alarm": True,
        })
    # THE STAGE: spots thrown at the body over the platform, and the rope
    # light's spill. One set per stage volume in the room.
    stages = [v for v in volumes if "stage" in str(v.get("name", "")).lower()]
    ropes = 0
    for k, v in enumerate(stages):
        sx, sy = float(v["x"]), float(v["y"])
        vw, vd = float(v.get("size_x", 0.0)), float(v.get("size_y", 0.0))
        form = str(v.get("form") or "")
        platform = _STAGE_PLATFORM.get(form, _STAGE_PLATFORM_DEFAULT)
        dx, dy = cx - sx, cy - sy
        if math.hypot(dx, dy) < 0.5:
            # a stage in the middle of its room: throw from along the
            # room's long axis, the positive end
            dx, dy = (1.0, 0.0) if along_x else (0.0, 1.0)
        # the throw comes from the nearer axis, never a corner
        if abs(dx) >= abs(dy):
            ux, uy, half = (1.0 if dx > 0 else -1.0), 0.0, vw / 2.0
        else:
            ux, uy, half = 0.0, (1.0 if dy > 0 else -1.0), vd / 2.0
        px = sx + ux * (half + _STAGE_THROW_BACK)
        py = sy + uy * (half + _STAGE_THROW_BACK)
        px = min(max(px, x0 + clear), x1 - clear)
        py = min(max(py, y0 + clear), y1 - clear)
        suffix = "" if len(stages) == 1 else "_%d" % (k + 1)
        out.append({
            "id": "%s_stage%s" % (rid, suffix), "type": "stage_light",
            "source": "derived",
            "pos": [round(px, 3), round(py, 3), ceiling_z],
            # the row runs ACROSS the throw
            "rot_y": 90.0 if ux else 0.0,
            "room": rid, "color": _club_colour(start, 0),
            "target": [round(sx, 3), round(sy, 3),
                       round(floor_z + platform + _STAGE_TARGET_RISE, 3)],
            "radius": _STAGE_SPOT_RADIUS,
            "row": {"count": _STAGE_SPOTS, "spacing": _STAGE_SPOT_SPACING},
            "cycle_s": _STAGE_CYCLE_S, "drop": drop, "reacts_to_alarm": True,
        })
        ropes += 1
        if form == "bar_stage":
            # over the deck, off the pole that stands at its centre, a
            # hand above the rope that runs round the deck lip
            rx = sx + (0.0 if vw >= vd else _ROPE_OFF_POLE)
            ry = sy + (_ROPE_OFF_POLE if vw >= vd else 0.0)
            rz = floor_z + platform + _ROPE_OVER_DECK
        else:
            rx, ry = sx + ux * (half + _ROPE_LIP_OUT), sy + uy * (half + _ROPE_LIP_OUT)
            rz = floor_z + _ROPE_LIP_Z
        out.append({
            "id": "%s_stage_lip%s" % (rid, suffix), "type": "neon",
            "source": "derived",
            "pos": [round(rx, 3), round(ry, 3), round(rz, 3)],
            "rot_y": 90.0 if ux else 0.0, "room": rid,
            "color": _ROPE_COLOUR, "size": [round(max(vw, vd), 3), round(min(vw, vd), 3)],
            "row": {"count": 1, "spacing": 0.0},
            "drop": round(rz - floor_z, 3), "reacts_to_alarm": True,
        })
    # THE NAME IN NEON: a spill source proud of each sign's face. The
    # glass's own colour is Zoo's, per name; Lux picks the spill's by the
    # anchor id (`club_hash`), which is deliberate here -- no `color`.
    signs = [v for v in volumes if "neon" in str(v.get("name", "")).lower()]
    for k, v in enumerate(signs):
        b = math.radians(_front_bearing(v))
        fx, fy = math.sin(b), math.cos(b)
        depth = min(float(v.get("size_x", 0.0)), float(v.get("size_y", 0.0)))
        length = max(float(v.get("size_x", 0.0)), float(v.get("size_y", 0.0)))
        out.append({
            "id": "%s_neon_%d" % (rid, k + 1), "type": "neon",
            "source": "derived",
            "pos": [round(float(v["x"]) + fx * (depth / 2.0 + _NEON_OUT), 3),
                    round(float(v["y"]) + fy * (depth / 2.0 + _NEON_OUT), 3),
                    round(float(v.get("z", 0.0)), 3)],
            "rot_y": _bearing_to_rot_y(_front_bearing(v)), "room": rid,
            "size": [round(length, 3), round(float(v.get("size_z", 0.0)), 3)],
            "row": {"count": 1, "spacing": 0.0},
            "drop": round(float(v.get("z", 0.0)) - floor_z, 3),
            "reacts_to_alarm": True,
        })
    return out


def tv_screen_size(width, height):
    """``[w, h]`` of the lit 4:3 face Zoo puts on a bracket set of slot
    ``width`` x ``height``: Zoo 0.90.0's `crt_forms.screen_size` over the
    front its bracket leaves (the shelf's drop, 0.2 x height held to 0.06-
    0.10 m, below it) -- mirrored, because Deli Counter cannot import Zoo;
    `test_club_rooms` pins the two sizes this recipe places against Zoo's
    own numbers, to a percent."""
    tv_h = (float(height) - max(0.06, min(0.10, 0.2 * float(height)))) * _TV_TIP_GROWTH
    sh = min(0.70 * tv_h, 0.525 * float(width))
    return [round(sh * 4.0 / 3.0, 3), round(sh, 3)]


def back_bar_face(height):
    """``(z above the unit's base, lit height)`` of a back bar's lit face:
    the glass shelves between the lower run's worktop and the cornice.
    Zoo's `back_bar_forms` arithmetic, mirrored (see `_BACKBAR_COUNTER_H`).

    Returns the CENTRE of the face and its height, both in metres above the
    unit's own base -- the slot's bottom, not its centre."""
    h = float(height)
    counter = min(_BACKBAR_COUNTER_H, h * _BACKBAR_COUNTER_SHARE)
    lo = counter + _BACKBAR_TOP_T
    hi = h - _BACKBAR_CORNICE_H
    return round((lo + hi) / 2.0, 4), round(max(0.2, hi - lo), 4)


def _back_bar_anchors(r, floor_z, volumes, aisle=None):
    """A `back_bar` spill anchor in front of every back bar in room ``r``:
    ``<volume name>_niche``, `_BACKBAR_OUT` proud of the slot's front face
    on its facing, at the lit face's own height, `size` that face and
    `aisle` the working aisle behind the bar. ``volumes`` are the room's
    visible volumes. Deterministic."""
    import math
    import prop_species
    rid = r.get("id", "room")
    out = []
    for v in volumes:
        name = str(v.get("name", ""))
        if prop_species.species_for_name(name) != _BACKBAR_SPECIES:
            continue
        bearing = _front_bearing(v)
        b = math.radians(bearing)
        fx, fy = math.sin(b), math.cos(b)
        sx, sy = float(v.get("size_x", 0.0)), float(v.get("size_y", 0.0))
        width, depth = max(sx, sy), min(sx, sy)
        height = float(v.get("size_z", 0.0))
        rise, lit = back_bar_face(height)
        # the slot's centre is at height / 2 above its base
        z = float(v.get("z", 0.0)) - height / 2.0 + rise
        out_d = depth / 2.0 + _BACKBAR_OUT
        a = {
            "id": "%s_niche" % name, "type": "back_bar", "source": "derived",
            "pos": [round(float(v["x"]) + fx * out_d, 3),
                    round(float(v["y"]) + fy * out_d, 3), round(z, 3)],
            "rot_y": _bearing_to_rot_y(bearing), "room": rid,
            "size": [round(width, 3), lit],
            "row": {"count": 1, "spacing": 0.0},
            "drop": round(z - floor_z, 3), "reacts_to_alarm": True,
        }
        if aisle:
            a["aisle"] = round(float(aisle), 3)
        out.append(a)
    return out


def _tv_screen_anchors(r, floor_z, volumes):
    """A `neon` spill anchor in front of every lit TV in room ``r``:
    ``<tv id>_screen``, `_TV_SCREEN_OUT` proud of the slot's front face on
    its facing, at the screen's height, `size` the screen. ``volumes``
    are the room's visible volumes. Deterministic."""
    import math
    import zlib
    import prop_species
    rid = r.get("id", "room")
    out = []
    for v in volumes:
        name = str(v.get("name", ""))
        if prop_species.species_for_name(name) != _TV_SPECIES:
            continue
        if str(v.get("form") or "") != _TV_LIT_FORM:
            continue
        bearing = _front_bearing(v)
        b = math.radians(bearing)
        fx, fy = math.sin(b), math.cos(b)
        sx, sy = float(v.get("size_x", 0.0)), float(v.get("size_y", 0.0))
        width, depth = max(sx, sy), min(sx, sy)
        out_d = depth / 2.0 + _TV_SCREEN_OUT
        aid = "%s_screen" % name
        z = float(v.get("z", 0.0)) + _TV_SCREEN_RISE
        out.append({
            "id": aid, "type": "neon", "source": "derived",
            "pos": [round(float(v["x"]) + fx * out_d, 3),
                    round(float(v["y"]) + fy * out_d, 3), round(z, 3)],
            "rot_y": _bearing_to_rot_y(bearing), "room": rid,
            "color": _TV_COLOURS[(zlib.crc32(aid.encode("utf-8")) & 0xFFFFFFFF)
                                 % len(_TV_COLOURS)],
            "size": tv_screen_size(width, float(v.get("size_z", 0.0))),
            "row": {"count": 1, "spacing": 0.0},
            "drop": round(z - floor_z, 3), "reacts_to_alarm": True,
        })
    return out


def _room_ambient(r, floor_z, ceiling_z, colour):
    """The room's box for Lux's per-room ambient probe: `size` is the
    wall-centreline box (the bounds are centrelines) from the floor to the
    ceiling PLANE, `pos` its centre. `color` is a palette name in a club
    room and null elsewhere -- null means the preset's own ambient, not a
    tint, and Lux 0.37.0 refuses it rather than painting an office violet
    (its default when the field is absent)."""
    x0, y0, x1, y1 = r["bounds"]
    top = ceiling_z + _CEILING_GAP
    return {
        "id": "%s_ambient" % r.get("id", "room"), "type": "room_ambient",
        "source": "derived",
        "pos": [round((x0 + x1) / 2.0, 3), round((y0 + y1) / 2.0, 3),
                round((floor_z + top) / 2.0, 3)],
        "rot_y": 0.0, "room": r.get("id"),
        "size": [round(x1 - x0, 3), round(y1 - y0, 3), round(top - floor_z, 3)],
        "color": colour,
        "reacts_to_alarm": False,
    }


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
                         report=None, volumes=None, club_rooms=None):
    """Derive default light anchors: one fluorescent ceiling row per interior
    room, one area light per window opening, a wall pack over every exterior
    door, and one storefront sign. Every room also carries a `room_ambient`
    box (v1.2). A room named in `club_rooms` gets THE CLUB SET instead of a
    ceiling row: `club_wash` pools, a `stage_light` and a `neon` at each
    stage in it, a `neon` proud of each neon sign, a coloured `room_ambient`
    -- Lux 0.37.0's types, from `volumes` (the spec's volumes as dicts) --
    and no fluorescent. The walker: "dark with colored lights". In ANY room,
    a `neon` in front of each TV Zoo lights (`_tv_screen_anchors`), after
    the room's lights and before its box.

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
    dict, receives the counts: nudged, dropped, rows_shifted, club_rooms,
    tv_screens.
    """
    anchors = []
    rep = report if report is not None else {}
    rep.setdefault("rows_shifted", 0)
    rep.setdefault("club_rooms", 0)
    rep.setdefault("tv_screens", 0)
    rep.setdefault("back_bars", 0)
    clear = wall_clearance(wall_thick)
    club_ids = set(club_rooms or ())
    # The aisle behind a club bar, asked of the one function that derives
    # it (`level_design.bar_aisle_width`) rather than spelled again here.
    try:
        import level_design
        bar_aisle = level_design.bar_aisle_width()
    except Exception:                                    # noqa: BLE001
        bar_aisle = None
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
        holes = [v for v in (ceiling_voids or ())
                 if int(v.get("story", story)) == story]
        rects = [(v["x0"], v["y0"], v["x1"], v["y1"]) for v in holes]
        walls = [w for w in (partitions or ()) if int(w["story"]) == story]
        in_room = _volumes_in(volumes, r, story_height)
        screens = _tv_screen_anchors(r, c[2], in_room)
        rep["tv_screens"] += len(screens)
        if r.get("id") in club_ids:
            rep["club_rooms"] += 1
            club = _club_anchors(r, ceiling_z, c[2], in_room,
                                 story_height, rects, walls, clear, rep)
            anchors += club
            anchors += screens
            bars = _back_bar_anchors(r, c[2], in_room, aisle=bar_aisle)
            rep["back_bars"] += len(bars)
            anchors += bars
            anchors.append(_room_ambient(
                r, c[2], ceiling_z, _club_colour(_club_colour_start(r.get("id")), 0)))
            continue
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
        # the room's box AFTER its row: a room's first anchor is its ceiling
        # light, as every reader of this list has assumed since v1.0
        anchors += screens
        anchors.append(_room_ambient(r, c[2], ceiling_z, None))

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

    # v1.3: a fuel canopy, which is not in any room -- it stands outside the
    # building on its own columns, and until now nothing derived a light from
    # it. Before the wall packs, so a forecourt's anchors sit together.
    anchors += _canopy_anchors(volumes)

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
                         ceiling_voids=None, partitions=None, report=None,
                         volumes=None, club_rooms=None):
    """Full `<name>.lights.json` manifest. `authored` is an optional list of
    hand-placed anchors; an authored anchor replaces a derived one with the
    same id (auto defaults + spec overrides, like props). `volumes` and
    `club_rooms` are `derive_light_anchors`'s."""
    anchors = derive_light_anchors(rooms, openings, story_height,
                                   cap_thick=cap_thick, wall_thick=wall_thick,
                                   ceiling_voids=ceiling_voids,
                                   partitions=partitions, report=report,
                                   volumes=volumes, club_rooms=club_rooms)
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
