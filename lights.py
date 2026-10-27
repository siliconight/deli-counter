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
#: THE LANES (0.167.0). Pump islands are the volumes named this, and a gap
#: between them -- or between the outer island and the deck's edge -- is a
#: lane when it is at least this wide: a car's width and a door's swing. A
#: wash hangs over each lane, because the pumps' faces face the lanes.
_PUMP_ISLAND = "pump_island"
_CANOPY_LANE_MIN = 2.4
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
#: AN OPENING SHOWS WHERE IT GOES (0.261.0). The walker, 2026-10-23, of a stair opening onto deli_a03's basement read
#: pitch black from above: "you should be able to see into holes to know you can go forward into them". A moody room
#: keeps its bare bulbs and its dark corners, but the LANDING of every opening into it -- a stair's foot, the floor
#: under a hole, a ladder's base (`opening_landings`) -- gets a fluorescent over it, the light an ordinary room is
#: lit by, so the place a way leads to reads from the way in. Measured before: the stairs land in cold storage at
#: luma p50 10, the vault p50 3, against the stairwell above at 74 (`tools/light_check.py`).
_LANDING_OFF_HOLE = 0.6   # metres past a hole's edge a landing lamp hangs, so it is mounted to ceiling, not air
_PENDANT_CORD = 0.6     # metres of cord between slab underside and bulb
#: THE COUNTER'S WARM ACCENT (0.160.0). The walker, 2026-09-29: "add the warm
#: counter accent", from their 1990s lighting reference on the convenience
#: store at night -- "cooler light on the aisles and a warmer or more
#: saturated accent at the counter". One bare bulb on the pendant's cord over
#: the centre of each volume whose name CARRIES one of these -- the gas
#: stations' `register_counter` and the delis' `front_register_counter`, the
#: substring rule `prop_species` uses -- in a room lit by a fluorescent row
#: (not a club room, not a moody one). Lux (>= 0.59.0) lights it warm, at a
#: troffer's level, scaled with the wash; Zoo builds `pendant_fixture` for it.
_COUNTER_VOLUMES = ("register_counter",)
#: Density guardrails, added after census #5 measured the first law's
#: failure: area/25 alone gave the arena's 275 m^2 skybox suite ELEVEN
#: bulbs 1.5 m apart -- a chandelier row, not a moody cellar, and every
#: ceiling tile under it blew the per-mesh budget. Bulbs are capped per
#: room and never packed tighter than a real cord spacing; a big room is
#: supposed to have dark corners -- that is what "moody" MEANS.
_PENDANT_MAX = 5        # bulbs per room, however big the room
#: A PUBLIC ROOM IS LIT TO SELL THINGS, whatever a heist wants from it
#: (0.154.0). The rule above means a vault and a count room; a mode that
#: marks a store's sales floor the objective made it a cellar -- measured:
#: `gas_station_a02` and `fuel_stop_heist`, the library's only two
#: objective rooms with a public role, had five bare bulbs over the sales
#: floor, the room the walker's night photographs show glowing out through
#: the storefront. They keep the fluorescent row the other seven stores'
#: sales floors have.
_LIT_ROLES = ("public_entry",)
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

#: ROWS LAID TO THE WORK, ON THE CEILING'S GRID (0.206.0, roadmap 229). The
#: walker, 2026-10-10: fixtures should "not always be in a perfect line, so
#: it looks a little less robotic". Counted over the 131 shipped manifests,
#: 513 of 513 fluorescent rows stood on their room's centreline along its
#: longer axis, 303 of them at the five-lamp cap with lamps 3.0 to 11.6 m
#: apart, because one rule lit every room from its bounds alone. A real
#: ceiling is laid to what is under it. WOOD's shop rule (the walker's
#: references, `docs/reference/INDOOR_FIXTURE_PLACEMENT_GUIDE.md` in the
#: factory): with A the height from the work surface to the fixture, rows
#: stand at most 1.5 x A apart and the outer row within half of that of the
#: wall -- so a room wider than 1.5 x A takes a second row, and a 24 x 24 ft
#: shop under a 9 ft ceiling takes three. The work surface is the room's: a
#: desk where the furnish seeds desks, a counter or a shelf where it sells
#: or serves, the floor in a hall, a stockroom, a bay or a home. Words from
#: the furnish's own archetypes (`level_design._SEED_ARCHETYPES`), matched
#: on the room's role and id.
_WORK_PLANE = (
    (("office", "manager", "exec", "admin", "suite", "booking", "clinic",
      "exam", "reception", "teller"), 0.75),
    (("sales", "retail", "shop_floor", "counter", "kitchen", "food", "bar",
      "lounge", "cafe", "diner", "deli"), 1.0),
)
_WORK_PLANE_FLOOR = 0.0
#: A residence-like ROOM inside any building takes the home rule (0.206.1):
#: cold run 9229's deli hung three rows of four over its `apartment_hideout`,
#: an office ceiling on a bedsit, because the rule keyed on the building.
_HOME_WORDS = ("apartment", "hideout", "bedroom", "living", "flat", "bedsit")
#: A HOME IS LIT A ROOM AT A TIME (0.207.1): one ceiling fixture a bay the
#: size of an ordinary room (the guide's "by room": a pendant or flush mount
#: over the sink, one pendant in a bedroom; docs/reference/
#: INDOOR_FIXTURE_PLACEMENT_GUIDE.md in the factory). A home's room within
#: one bay keeps its one fixture at its centre; a bigger one -- cold run
#: 9232's 21 x 16 m hideout, dark at both ends under one troffer -- takes
#: a grid of bays at this spacing, the fixtures at the bays' centres.
_HOME_SPACING = 7.0
#: ROWS OVER THE AISLES (0.207.0, roadmap 229). In a room organised by its
#: shelving -- a selling floor's gondolas, a stockroom's or a warehouse's
#: racks -- the ceiling is laid to the AISLES between the runs, not across
#: the room: a fixture over a gondola lights its top shelf and leaves the
#: aisle beside it to spill. The room's shelf volumes (`_SHELF_WORDS` on the
#: volume's name, standing on the floor) are projected across the room's
#: long axis, the spans merged, and every gap at least an aisle wide
#: (`level_design.island_aisle_width`, the contract's door width, 1.25 m) is
#: a LANE; each lane takes WOOD's rows within its own width, so the open
#: band beside one wall run is still lit as a floor (`_lanes_for_room`,
#: `_rows_for_room`). Only in a room whose words say it sells or stores
#: (`_AISLE_ROOM_WORDS`): an office with a shelf unit against the wall keeps
#: its tile grid, which is what an office is. Counted over the furnished
#: library before the change (`docs/findings/fixture_rows/aisle_census.py`):
#: 514 of 702 rooms carry a shelf volume, 293 of them with two or more lanes.
_SHELF_WORDS = ("shelf", "gondola", "rack", "pack_wall")
_AISLE_ROOM_WORDS = ("sales", "retail", "shop_floor", "aisle", "market", "store",
                     "stock", "storage", "ware", "parts", "supply", "cellar", "bond")
#: The aisle's width when `level_design` cannot be asked: the contract's
#: `clearances.min_door_width_m`, the number `island_aisle_width` returns --
#: asked of the contract, which can always be asked (0.216.0; a literal 1.25).
_AISLE_MIN_FALLBACK = __import__("agent_contract").min_door_width()
#: A shelf stands on the floor; a sign hung over an aisle does not.
_SHELF_FOOT_MAX = 0.5
#: A merged shelf span wider than this is a FIELD of islands, not a run: the
#: deepest run in `level_design._PIECES` is 0.6 m and a twin island, two
#: backs meeting, 1.2 m (`level_design.island_depth`); the furnish stands a
#: selling room's islands down its middle band at shuffled positions along
#: it, and their spans overlap into a band 2 to 10 m wide (66 of the 98
#: shelved selling and storage rooms in the library; 32 have runs). A row
#: kept off such a band leaves the middle of the floor dark, so past this
#: the room is laid across as before.
_SHELF_SPAN_MAX = 2.0
#: WOOD: rows at most this times A apart.
_ROW_SPACING_OVER_A = 1.5
#: A room up to (1 + this) x B wide keeps one row: WOOD's half-spacing to the
#: wall is a shop's shadow-free bench rule, and a 4 m office under one row
#: of troffers is what an office is. The slack is taken off the row count's
#: fraction before it is rounded up.
_ROW_SLACK = 0.3
#: A room's rows across its width and its lamps are capped: the lamp count
#: was a budget number before the bake (`_TARGET_SPACING`, above), and the
#: cap keeps a 20 x 58 m hall at twelve lamps rather than forty until the
#: price of more is measured (roadmap 229). The row cap, `_MAX_FIXTURES`,
#: is unchanged.
_MAX_ROWS = 3
_MAX_LAMPS_ROOM = 12
#: A SELLING ROOM KEEPS A SHOP'S DENSITY, HOWEVER BIG IT IS (0.274.0). The
#: walker, 2026-10-26, in seed 9205's supermarket: "far too dark in teh super
#: market", and then the comps -- "shiny floor, bright lights, isles, glowing
#: freezer section" (the factory's docs/reference/GROCERY_STORE_COMPS.md: long
#: fluorescent runs 2 to 3 m apart, nothing in shadow). The room cap above
#: held every room to twelve lamps whatever its size, so the library's
#: selling floors were lit at a density that fell with their area: 13 to 34
#: m2 a lamp in the shops under 340 m2, 88 to 104 in the supermarkets and the
#: market halls, a quarter as bright for being four times bigger (the
#: factory's docs/findings/selling_hall_lights/census.py). A room whose id
#: sells (`floors.floor_by_use` == "tile", the same words that tile its
#: floor) takes its cap from its area instead -- one lamp a this many m2,
#: never fewer than twelve -- and its rows across and lamps along are
#: bounded by that cap alone; WOOD's spacing, unchanged, decides how many it
#: asks for. 25 m2 is the density the library's capped selling rooms of
#: 250 to 300 m2 already had (the delis' `market_aisles` 25.0, gas_station_a02
#: 23.0, convenience_store_a01 21.1, pharmacy_a01 26.4): a big store is lit
#: like a small one, not brighter. The lamps are baked (Lux bakes every
#: steady fluorescent static), so what more of them costs a frame is their
#: fixtures' draws -- priced in the same findings folder.
_SELLING_M2_PER_LAMP = 25.0
#: THE CEILING'S GRID. A fixture hangs from a joist or sits in a tile, so a
#: row's line is a multiple of the pitch from the building's origin, not
#: the room's centre: 0.6 m tiles over a desk or a counter, 0.4 m joists
#: everywhere else. The snap moves a line by half a pitch at most, and it
#: is the same in every build of a spec.
_CEILING_PITCH_TILE = 0.6
_CEILING_PITCH_JOIST = 0.4


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


def _colinear_shift(bounds, rot, walls, clear, line=None):
    """Where a partition runs ALONG the row -- its band contains the row's
    line over at least half the row's length -- the row is not crossing a
    wall, it is lying in one, and no point-wise nudge can save it. The
    partition has divided the room into two spaces; the row moves to the
    centre of the larger one (equal: the positive side). Returns the new
    perpendicular coordinate, or None when no wall is colinear.

    One row, one side, on purpose: the other side stays unlit and the
    caller reports the shift so a re-walk can judge whether that space
    wanted its own row -- which is a room-splitting question for the spec,
    not a lighting one. ``line`` (0.206.0) is the row's own perpendicular
    coordinate when it is not the room's centre.
    """
    minx, miny, maxx, maxy = bounds
    along_x = abs(rot) < 45.0
    if along_x:
        perp, lo, hi, a0, a1 = (miny + maxy) / 2.0, miny, maxy, minx, maxx
    else:
        perp, lo, hi, a0, a1 = (minx + maxx) / 2.0, minx, maxx, miny, maxy
    if line is not None:
        perp = line
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

#: A HOME HAS NO LIT SIGN (0.169.0). Zoo 1.37.0 paints a business's name on
#: the sign box, and a building of no kind gets its street number -- which
#: on a home is a lit cabinet over a front door, and a lit cabinet says
#: BUSINESS. The walker left the call here (2026-10-02). A building whose
#: identity carries one of these words, whole, derives no storefront sign;
#: its front door takes the wall pack every other exterior door takes, so
#: the door is still lit and the light count does not move.
RESIDENCE_WORDS = frozenset(("apartment", "walkup", "rowhouse", "twin", "mansion", "duplex",
                             "tenement"))


#: A BANK READS AS THE WALKER'S COMPS (0.280.0, the factory's roadmap 321;
#: docs/reference/BANK_INTERIOR_COMPS.md): "bright, even ceilings" in every
#: public room, the money "in hard rooms ... all lit by bare tubes". Measured
#: on bank_branch_a02 before (docs/findings/bank_interior/): its lobby one lamp
#: a 39 m2, a mean of 37 under the level's light; its vault floor under bare
#: bulbs, one a 55 m2, 30-40. A bank's public room (`public_entry`) takes a
#: selling room's lamp density (`room_caps`) and the bake-only reach
#: (`bake_reach`); its rooms below grade and over the take take ceiling rows
#: of tubes instead of the moody bulbs every other building's do.
_BANK_WORDS = ("bank",)


def is_bank(business):
    """Does ``business`` (`level_design.club_building_id`) name a bank? A
    whole word of it: `bank_branch_a02`, `bank_job`, `bank_tower_a01`."""
    import re
    words = set(re.split(r"[^a-z0-9]+", str(business or "").lower()))
    return bool(words & set(_BANK_WORDS))


def bank_public(r, business):
    """A bank's public room: its `public_entry` (lobby, banking hall)."""
    return is_bank(business) and (r or {}).get("role") == "public_entry"


def is_residence(business):
    """Does ``business`` (`level_design.club_building_id`) name a home?"""
    words = str(business or "").lower().replace("-", "_").replace(" ", "_").split("_")
    return bool(RESIDENCE_WORDS & set(words))


def _club_colour_start(room_id):
    import zlib
    return (zlib.crc32(str(room_id).encode("utf-8")) & 0xFFFFFFFF) % len(CLUB_COLOURS)


def _club_colour(start, i):
    return CLUB_COLOURS[(start + 2 * i) % len(CLUB_COLOURS)]


def _front_bearing(v):
    """The compass bearing (N 0, E 90) a hinted volume's module front points
    at, by the rule the slot is recorded with: long side first, +90 when
    that side is y (`prop_species.long_axis_first`; a depth-long species when
    it is x, 0.245.0), then `rot_z`; the front is the module's -Y, so + 180.
    The same arithmetic as `level_design._front_turn`, asked the other way
    round, and the turn is the emitter's own (`prop_species.recorded_turn`)."""
    import prop_species
    turn = prop_species.recorded_turn(str(v.get("name", "")),
                                      float(v.get("size_x", 0.0)),
                                      float(v.get("size_y", 0.0)))
    return (turn + float(v.get("rot_z", 0.0) or 0.0) + 180.0) % 360.0


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


def _canopy_lanes(deck, volumes):
    """``[(x, y, pool)]``, one per LANE under ``deck``, or [] when no pump
    island stands under it.

    The islands' long axis is the lanes' direction; the lanes are the gaps
    ACROSS it -- between neighbouring islands, and between the outer islands
    and the deck's edge -- at least `_CANOPY_LANE_MIN` wide. A wash stands
    over each lane's centre, half way along the deck, and owns the lane's
    width by the deck's length that way. More lanes than `_CANOPY_WASH_MAX`
    keep the outermost two and the evenly spread rest, so the light budget on
    the forecourt ground holds whatever the deck."""
    cx, cy = float(deck.get("x", 0.0)), float(deck.get("y", 0.0))
    sx, sy = float(deck.get("size_x", 0.0)), float(deck.get("size_y", 0.0))
    isl = []
    for v in volumes or ():
        if not str(v.get("name", "")).startswith(_PUMP_ISLAND):
            continue
        vx, vy = float(v.get("x", 0.0)), float(v.get("y", 0.0))
        if abs(vx - cx) > sx / 2.0 or abs(vy - cy) > sy / 2.0:
            continue          # another forecourt's island
        isl.append(v)
    if not isl:
        return []
    # the islands run along y when they are longer in y: the lanes do too,
    # and are spaced across x
    along_y = sum(float(v.get("size_y", 0.0)) - float(v.get("size_x", 0.0)) for v in isl) >= 0
    if along_y:
        lo, hi, c_al, len_al = cx - sx / 2.0, cx + sx / 2.0, cy, sy
        spans = sorted((float(v["x"]) - float(v.get("size_x", 0.0)) / 2.0,
                        float(v["x"]) + float(v.get("size_x", 0.0)) / 2.0) for v in isl)
    else:
        lo, hi, c_al, len_al = cy - sy / 2.0, cy + sy / 2.0, cx, sx
        spans = sorted((float(v["y"]) - float(v.get("size_y", 0.0)) / 2.0,
                        float(v["y"]) + float(v.get("size_y", 0.0)) / 2.0) for v in isl)
    edges = [lo] + [e for a, b in spans for e in (a, b)] + [hi]
    gaps = [(edges[k], edges[k + 1]) for k in range(0, len(edges), 2)]
    gaps = [(a, b) for a, b in gaps if b - a >= _CANOPY_LANE_MIN]
    if len(gaps) > _CANOPY_WASH_MAX:
        keep = [round(k * (len(gaps) - 1) / (_CANOPY_WASH_MAX - 1.0))
                for k in range(_CANOPY_WASH_MAX)]
        gaps = [gaps[k] for k in sorted(set(keep))]
    out = []
    for a, b in gaps:
        mid, w = (a + b) / 2.0, b - a
        if along_y:
            out.append((mid, c_al, [round(w, 3), round(len_al, 3)]))
        else:
            out.append((c_al, mid, [round(len_al, 3), round(w, 3)]))
    return out


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

        # THE LIGHT. Over the LANES when pump islands stand under the deck
        # (0.167.0, `_canopy_lanes`): a pump's faces face its lanes, and a
        # wash over an island grazes them. Otherwise a few washes, along the
        # deck's long axis, inset so the pools land on the tarmac rather
        # than past the drip line.
        lanes = _canopy_lanes(deck, volumes)
        if lanes:
            spots = lanes
        else:
            n = _CANOPY_WASH_BASE + int((sx * sy) // _CANOPY_WASH_PER_AREA)
            n = max(_CANOPY_WASH_BASE, min(_CANOPY_WASH_MAX, n))
            span, across = (sx, True) if sx >= sy else (sy, False)
            step = span / float(n)
            spots = []
            for i in range(n):
                off = -span / 2.0 + step * (i + 0.5)
                spots.append((cx + off if across else cx, cy if across else cy + off,
                              [round(step, 3), round(min(sx, sy), 3)]))
        for i, (x, y, pool) in enumerate(spots):
            out.append({
                "id": "%s_wash_%d" % (name, i), "type": "canopy_wash",
                "source": "derived",
                "pos": [round(x, 3), round(y, 3), round(soffit, 3)],
                "rot_y": 0.0,
                # the pool this wash owns, so Lux need not divide the deck
                # itself and two canopies of different sizes light alike
                "size": pool,
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


def _storefront_reach(bounds, story, pos, rot, count, spacing, storefronts,
                      wall_thick):
    """Horizontal metres from a ceiling row to the storefront glass that
    walls its room, or 0.0 (0.155.0).

    A fluorescent's range is derived to the floor UNDER it (Lux's `drop +
    0.75`), and one row runs down a room's middle -- so in a 12 m deep store
    the floor at the glass, the part the street sees, is 6 m off to the side
    and outside every pool. `storefronts` are the storefront wall and door
    slots (`deli_counter.storefront_slot`) as ``{story, facing, x, y}`` at the
    wall's centreline, which is where a room's bounds sit; a slot walls this
    room when it lies on one of the room's edges (within a wall's thickness)
    and inside the room's span along it. For each such slot the distance is
    from the row's NEAREST lamp, measured across the wall -- a row parallel
    to the glass is its offset, a row running at the glass is its end lamp's
    -- and the row's reach is the largest of them: it must light the floor
    at every glass line it faces. Lux clamps the range, so a far wall costs
    no more than the clamp.
    """
    if not storefronts:
        return 0.0
    minx, miny, maxx, maxy = bounds
    tol = max(float(wall_thick), 0.05)
    # the rows are axis-aligned, and this is `_row_runs`' own reading of rot
    dx, dy = (1.0, 0.0) if abs(rot) < 45.0 else (0.0, 1.0)
    start = -(count - 1) * 0.5 * spacing if count > 1 else 0.0
    lamps = [(pos[0] + (start + i * spacing) * dx, pos[1] + (start + i * spacing) * dy)
             for i in range(max(1, count))]
    edge = {"S": (1, miny), "N": (1, maxy), "W": (0, minx), "E": (0, maxx)}
    reach = 0.0
    for sf in storefronts:
        if int(sf.get("story", 0) or 0) != story or sf.get("facing") not in edge:
            continue
        axis, line = edge[sf["facing"]]
        at = (float(sf["x"]), float(sf["y"]))
        along = at[1 - axis]
        lo, hi = (minx, maxx) if axis == 1 else (miny, maxy)
        if abs(at[axis] - line) > tol or not (lo - tol <= along <= hi + tol):
            continue
        reach = max(reach, min(abs(p[axis] - at[axis]) for p in lamps))
    return round(reach, 3)


#: THE STOREFRONT SPILL (0.156.0). The walker, 2026-09-29: "do the outward
#: spill next". A lamp's height over the pavement: the top of the storefront
#: glass, which is Zoo's `arch.SF_GLASS_TOP` (3.0 m over the floor) or its
#: `SF_HEAD_MIN` (0.4 m) under the storey's top when that is lower -- the two
#: numbers Zoo draws the glass with, so the light leaves where the glass ends.
_SPILL_HEAD = 3.0
_SF_HEAD_MIN = 0.4
#: How far out of the wall's face the source stands: a panel's standoff, the
#: window's (`_WALL_PACK_OUT` is the pack's own and larger).
_SPILL_OUT = 0.20


def _storefront_spans(bounds, story, storefronts, wall_thick):
    """``{facing: (line, lo, hi)}`` -- each storefront edge of this room: the
    wall's centreline coordinate and the glass's extent along it, clipped to
    the room (0.156.0). The same edge test as `_storefront_reach`; a slot's
    extent is its centre +/- half its width `w` (0 when a caller sends none).
    """
    minx, miny, maxx, maxy = bounds
    tol = max(float(wall_thick), 0.05)
    edge = {"S": (1, miny), "N": (1, maxy), "W": (0, minx), "E": (0, maxx)}
    spans = {}
    for sf in storefronts or ():
        if int(sf.get("story", 0) or 0) != story or sf.get("facing") not in edge:
            continue
        axis, line = edge[sf["facing"]]
        at = (float(sf["x"]), float(sf["y"]))
        along = at[1 - axis]
        lo, hi = (minx, maxx) if axis == 1 else (miny, maxy)
        if abs(at[axis] - line) > tol or not (lo - tol <= along <= hi + tol):
            continue
        half = float(sf.get("w", 0.0) or 0.0) * 0.5
        a0, a1 = max(lo, along - half), min(hi, along + half)
        f = sf["facing"]
        if f in spans:
            spans[f] = (spans[f][0], min(spans[f][1], a0), max(spans[f][2], a1))
        else:
            spans[f] = (at[axis], a0, a1)
    return spans


def room_on_edge(rooms, story, facing, x, y, wall_thick):
    """The id of the room one of whose exterior edges passes through
    (``x``, ``y``) on the side ``facing`` -- the room a wall slot at the wall's
    centreline stands in front of -- or None (0.159.0). The edge test is
    `_storefront_spans`'; along the edge the point must lie inside the room's
    own span, so a slot on a partition's line belongs to the first room."""
    tol = max(float(wall_thick or 0.3), 0.05)
    for r in rooms or []:
        b = r.get("bounds")
        if not b or int(r.get("story", 0) or 0) != int(story or 0):
            continue
        minx, miny, maxx, maxy = b
        edge = {"S": (1, miny), "N": (1, maxy), "W": (0, minx), "E": (0, maxx)}.get(facing)
        if edge is None:
            continue
        axis, line = edge
        at = (float(x), float(y))
        lo, hi = (minx, maxx) if axis == 1 else (miny, maxy)
        if abs(at[axis] - line) <= tol and lo - 1e-6 <= at[1 - axis] <= hi + 1e-6:
            return r.get("id")
    return None


def storefront_lit_rooms(rooms, storefronts, wall_thick, club_rooms=()):
    """Ids of the rooms lit from outside through storefront glass (0.157.0):
    a room with a fluorescent row -- not a club room, not below grade, not an
    objective that is not a public room (`derive_light_anchors`' own `moody`
    rule) -- one of whose edges is storefront glass (`_storefront_spans`).
    These are the rooms `derive_light_anchors` gives a `reach` and storefront
    spills, asked of the same tests, so the slot manifest can tag their
    floor and ceiling before the light manifest is written.
    """
    club = set(club_rooms or ())
    out = set()
    for r in rooms or []:
        bounds = r.get("bounds")
        if not r.get("center") or not bounds or r.get("id") in club:
            continue
        story = int(r.get("story", 0) or 0)
        moody = story < 0 or (bool(r.get("objective")) and r.get("role") not in _LIT_ROLES)
        if not moody and _storefront_spans(bounds, story, storefronts, wall_thick):
            out.add(r.get("id"))
    return out


def _spill_anchors(room_id, bounds, story, floor_z, storefronts, wall_thick,
                   head, drop, reach):
    """The storefront spill along each storefront edge of a room whose
    ceiling row reaches its glass (0.156.0): one lamp per `2 * head` of glass,
    evenly spaced, standing `_SPILL_OUT` off the wall's face at the glass's
    head, facing out. Lux (>= 0.57.0) throws each one out and down through a
    45-degree cone whose footprint is about 2.8 heads wide where its axis
    lands, so neighbours two heads apart overlap into a band.

    Each carries the room row's `drop` and `reach` -- Lux solves the spill's
    level from the floor that row lights -- and `head`, which the throw is
    measured from. One anchor per lamp, no `row`: a row runs along `rot_y`,
    and a spill's `rot_y` is its facing, across the row.
    """
    out = []
    spans = _storefront_spans(bounds, story, storefronts, wall_thick)
    off = float(wall_thick) * 0.5 + _SPILL_OUT
    for facing in sorted(spans):
        line, a0, a1 = spans[facing]
        span = a1 - a0
        n = max(1, int(round(span / (2.0 * head))))
        rot, (ox, oy) = _outward(facing)
        for i in range(n):
            along = a0 + span * (i + 0.5) / n
            x, y = (along, line) if facing in ("S", "N") else (line, along)
            out.append({
                "id": "%s_spill_%s_%d" % (room_id, facing, i),
                "type": "storefront_spill",
                "source": "derived",
                "pos": [round(x + ox * off, 3), round(y + oy * off, 3),
                        round(floor_z + head, 3)],
                "rot_y": rot,
                "room": room_id,
                "wall": facing,
                "head": head,
                "drop": drop,
                "reach": reach,
                "reacts_to_alarm": True,
            })
    return out


def _work_plane(r, residence):
    """The height over its floor of what a room's ceiling lights (0.206.0):
    a desk, a counter, or the floor itself. See `_WORK_PLANE`."""
    if residence:
        return _WORK_PLANE_FLOOR
    key = ((r.get("role") or "") + " " + (r.get("id") or "")).lower()
    for words, height in _WORK_PLANE:
        if any(w in key for w in words):
            return height
    return _WORK_PLANE_FLOOR


def _home_room(r, residence):
    """A home's room: by the building (`residence`) or by the room's own
    words (0.206.1, `_HOME_WORDS`)."""
    if residence:
        return True
    key = ((r.get("role") or "") + " " + (r.get("id") or "")).lower()
    return any(w in key for w in _HOME_WORDS)


def _ceiling_pitch(work_plane):
    """Tiles over a desk or a counter, joists everywhere else."""
    return _CEILING_PITCH_TILE if work_plane > 0.0 else _CEILING_PITCH_JOIST


def _snap(value, pitch):
    """``value`` moved to the nearest multiple of ``pitch`` from the origin."""
    return round(pitch * round(value / pitch), 3)


def room_caps(r, bounds, selling=False):
    """``(max_rows, max_fixtures, max_lamps)`` for a room's ceiling rows: the
    library's `_MAX_ROWS`, `_MAX_FIXTURES` and `_MAX_LAMPS_ROOM`, except in a
    room whose id sells -- or that the caller says is lit as one, ``selling``
    (a bank's public room, 0.280.0) -- whose lamps are one a
    `_SELLING_M2_PER_LAMP` of its floor and never fewer than `_MAX_LAMPS_ROOM`,
    bounding its rows and its lamps along alike (0.274.0)."""
    import floors
    if not selling and floors.floor_by_use((r or {}).get("id")) != "tile":
        return _MAX_ROWS, _MAX_FIXTURES, _MAX_LAMPS_ROOM
    minx, miny, maxx, maxy = bounds
    lamps = max(_MAX_LAMPS_ROOM, int((maxx - minx) * (maxy - miny) // _SELLING_M2_PER_LAMP))
    return lamps, lamps, lamps


def _rows_for_room(bounds, lamp_z, floor_z, work_plane, residence, lanes=None, caps=None):
    """The ceiling rows of a room (0.206.0, roadmap 229): along its longer
    axis as before, and across the shorter one as many as the work plane
    asks. With A the height from the work plane to the lamp and B = 1.5 x A
    (`_ROW_SPACING_OVER_A`), a band W wide takes ceil(W / B - `_ROW_SLACK`)
    rows, so the outer row stands near B / 2 of its edge; the lamps along
    each row at B, held to `_MAX_FIXTURES` a row and `_MAX_LAMPS_ROOM` a
    room by thinning every row alike. Each row's line is snapped to the
    ceiling's pitch (`_ceiling_pitch`) from the building's origin and kept a
    pitch inside its band. A home's room is one fixture at its centre while
    it is one bay (`_HOME_SPACING`), and a fixture a bay beyond that, at the
    bays' centres (0.207.1): a line of one is not a line, and a hall is not
    a bedsit.

    The BANDS are the room's whole width, or its `lanes` (0.207.0,
    `_lanes_for_room`): the aisles between its shelf runs, each laid as a
    floor of its own width, so a room with no shelving is laid exactly as
    before and a room organised by its shelving is lit between the runs. A
    lane too narrow to keep a pitch inside each edge takes its centre.
    Where the room's cap binds, rows across are traded for lamps along
    while the larger spacing shrinks (0.207.0, the long hall). `caps` is
    `room_caps`'s ``(max_rows, max_fixtures, max_lamps)``; without it the
    library's caps hold, as they always have.

    Returns ``[(rot_y, x, y, count, spacing)]``, the rows across in order."""
    minx, miny, maxx, maxy = bounds
    dx, dy = maxx - minx, maxy - miny
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    along_x = dx >= dy
    rot = 0.0 if along_x else 90.0
    length, width = (dx, dy) if along_x else (dy, dx)
    if residence:
        # a fixture a bay (0.207.1): WOOD's row rule at the bay's spacing, the
        # lines at the bays' centres, never snapped -- a home hangs its fixture
        # from the middle of the room; one bay is the one fixture it always was
        b = _HOME_SPACING
        n_rows = max(1, min(_MAX_ROWS, int(-(-(width / b - _ROW_SLACK) // 1))))
        count = max(1, min(_MAX_FIXTURES, int(round(length / b))))
        while n_rows * count > _MAX_LAMPS_ROOM and count > 1:
            count -= 1
        spacing = round(length / count, 3) if count > 1 else 0.0
        rows = []
        for k in range(n_rows):
            line = (cy if along_x else cx) + (k + 0.5) * width / n_rows - width / 2.0
            if along_x:
                rows.append((rot, round(cx, 3), round(line, 3), count, spacing))
            else:
                rows.append((rot, round(line, 3), round(cy, 3), count, spacing))
        return rows
    bands = list(lanes) if lanes else [(miny, maxy) if along_x else (minx, maxx)]
    max_rows, max_fixtures, max_lamps = caps or (_MAX_ROWS, _MAX_FIXTURES, _MAX_LAMPS_ROOM)
    a = max(lamp_z - floor_z - work_plane, 1.0)
    b = _ROW_SPACING_OVER_A * a
    # ceil of each band's width in spacings, less the slack: a band up to 1.3 B wide is one row
    per_band = [max(1, min(max_rows, int(-(-((hi - lo) / b - _ROW_SLACK) // 1))))
                for lo, hi in bands]
    count_ask = max(1, min(max_fixtures, int(round(length / b))))

    def _fit(rows_per_band):
        n = count_ask
        while sum(rows_per_band) * n > max_lamps and n > 1:
            n -= 1
        return n

    count = _fit(per_band)
    if count < count_ask:
        # THE LONG HALL (0.207.0): the cap binds, so WOOD's rule cannot hold
        # in both directions at once. Trade rows across for lamps along
        # while the LARGER of the two spacings shrinks, a row at a time from
        # the band that loses least by it: a 58 x 20 m hall is two rows of
        # five at 11.6 m along rather than three of four at 14.5, and a
        # 12 x 11 m office keeps its three of four, whose across spacing
        # (3.7 m) is the larger and would only grow. Nothing changes where
        # the cap does not bind.
        def _worst(rows_per_band, n_lamps):
            across = max((hi - lo) / n for (lo, hi), n in zip(bands, rows_per_band))
            along = length / n_lamps if n_lamps > 1 else length
            return max(across, along)

        best = (_worst(per_band, count), list(per_band), count)
        cur = list(per_band)
        while True:
            more = [i for i, n in enumerate(cur) if n > 1]
            if not more:
                break
            k = min(more, key=lambda i: (bands[i][1] - bands[i][0]) / (cur[i] - 1))
            cur[k] -= 1
            n_lamps = _fit(cur)
            worst = _worst(cur, n_lamps)
            if worst < best[0] - 1e-9:
                best = (worst, list(cur), n_lamps)
        per_band, count = best[1], best[2]
    n_rows = sum(per_band)
    spacing = round(length / count, 3) if count > 1 else 0.0
    pitch = _ceiling_pitch(work_plane)
    rows = []
    for (lo, hi), n in zip(bands, per_band):
        width = hi - lo
        centre = (lo + hi) / 2.0
        inner_lo, inner_hi = lo + pitch, hi - pitch
        for k in range(n):
            line = centre + (k + 0.5) * width / n - width / 2.0
            if inner_lo <= inner_hi:
                line = min(max(_snap(line, pitch), inner_lo), inner_hi)
            else:
                line = centre
            if along_x:
                rows.append((rot, round(cx, 3), round(line, 3), count, spacing))
            else:
                rows.append((rot, round(line, 3), round(cy, 3), count, spacing))
    return rows


def _lanes_for_room(r, bounds, floor_z, volumes, aisle):
    """The LANES between a room's shelf runs, across its long axis (0.207.0,
    roadmap 229): ``[(lo, hi)]`` in order, or None when the room is not
    organised by shelving. The room's words must say it sells or stores
    (`_AISLE_ROOM_WORDS`), and a shelf is a visible volume standing in it
    whose name carries one of `_SHELF_WORDS` and whose foot is on the floor
    (`_SHELF_FOOT_MAX`: a sign hung over an aisle is not a shelf). The
    shelves' spans across the room's long axis are clipped to the bounds and
    merged, and every gap between them and the bounds at least `aisle` wide
    is a lane. Shelving that leaves no lane returns [], and the room is laid
    across as before; so is a room whose merged spans are wider than a run
    is deep (`_SHELF_SPAN_MAX`), a field of staggered islands rather than
    parallel runs, which returns None. `volumes` are the room's visible
    volumes on its storey (`_volumes_in`)."""
    key = ((r.get("role") or "") + " " + (r.get("id") or "")).lower()
    if not any(w in key for w in _AISLE_ROOM_WORDS):
        return None
    minx, miny, maxx, maxy = bounds
    along_x = (maxx - minx) >= (maxy - miny)
    lo, hi = (miny, maxy) if along_x else (minx, maxx)
    spans = []
    for v in volumes or ():
        name = str(v.get("name", "")).lower()
        if not any(w in name for w in _SHELF_WORDS):
            continue
        foot = float(v.get("z", 0.0)) - float(v.get("size_z", 0.0)) / 2.0
        if foot - floor_z > _SHELF_FOOT_MAX:
            continue
        if along_x:
            c, s = float(v.get("y", 0.0)), float(v.get("size_y", 0.0))
        else:
            c, s = float(v.get("x", 0.0)), float(v.get("size_x", 0.0))
        a, b = max(lo, c - s / 2.0), min(hi, c + s / 2.0)
        if b > a:
            spans.append((a, b))
    if not spans:
        return None
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    # A FIELD OF ISLANDS IS NOT A RUN. The furnish stands a selling room's
    # islands down its middle band at shuffled positions along it, so their
    # spans across the room overlap into one band wider than any shelf is
    # deep; a row kept off that band would leave the middle of the floor
    # dark (the gas station's sales floor, 14 m between rows on the first
    # build). Past `_SHELF_SPAN_MAX` the room is laid across as before.
    if max(b - a for a, b in merged) > _SHELF_SPAN_MAX:
        return None
    edges = [lo] + [e for a, b in merged for e in (a, b)] + [hi]
    gaps = [(edges[k], edges[k + 1]) for k in range(0, len(edges), 2)]
    return [(round(a, 3), round(b, 3)) for a, b in gaps if b - a >= aisle - 1e-6]


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


#: THE NAME A DEN'S DRAPE CARRIES (0.205.0), `level_design.DRAPE_NAME`'s: a
#: window with one over it lets no light in (`_drapes_window`)
DRAPE_NAME = "window_drape"


def _drapes_window(v, o):
    """Does volume ``v``, a den's drape, hang over window opening ``o``? On the
    same stretch of the same wall: its centre along the wall within half its
    width of the opening's, within a metre of the opening's line across it,
    and its height spanning the opening's centre. ``o`` is a gameplay opening
    (``wall`` like ``ext_0_S``, its centre in x, y and z)."""
    side = str(o.get("wall", "")).rsplit("_", 1)[-1]
    if side in ("N", "S"):
        along, across, half = "x", "y", float(v.get("size_x", 0.0)) / 2.0
    elif side in ("E", "W"):
        along, across, half = "y", "x", float(v.get("size_y", 0.0)) / 2.0
    else:
        return False
    return (abs(float(v.get(along, 0.0)) - float(o.get(along, 0.0))) <= half
            and abs(float(v.get(across, 0.0)) - float(o.get(across, 0.0))) <= 1.0
            and abs(float(v.get("z", 0.0)) - float(o.get("z", 0.0)))
            <= float(v.get("size_z", 0.0)) / 2.0)


def opening_landings(spec):
    """Where every opening into a storey lands, in spec metres: [{story, x, y, kind}] -- a stair's lower end
    (`stairwell.stair_endpoints`), the floor under each hole in a slab that is not a stair's own
    (`axonometric._slab_holes`: authored holes, floor holes, hatches), a ladder's base. One entry a place: a hole
    named twice (as authored and as its link) is one landing."""
    import axonometric
    import stairwell
    out, seen = [], set()

    def add(story, x, y, kind):
        key = (int(story), round(float(x), 2), round(float(y), 2))
        if key not in seen:
            seen.add(key)
            out.append({"story": int(story), "x": round(float(x), 3), "y": round(float(y), 3), "kind": kind})
    for st in getattr(spec, "stairs", []) or []:
        for e in stairwell.stair_endpoints(st):
            if e["end"] == "lower":
                add(min(st.from_story, st.to_story), e["point"][0], e["point"][1], "stair")
    for s, rects in sorted(axonometric._slab_holes(spec).items()):
        for r, kind in rects:
            if kind != "stair" and not _own_hole(spec, s, r):
                add(s - 1, (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0, "hole")
    for ld in getattr(spec, "ladders", []) or []:
        add(min(ld.from_story, ld.to_story), ld.x, ld.y, "ladder")
    return out


def _own_hole(spec, s, r):
    """Whether the hole ``r`` in storey ``s``'s slab is a ladder's or a stair's OWN cut -- that opening, not a second
    one. The build cuts both into the slabs it lights from (`Builder`: `ladder_geom.through_hole` for a ladder, the
    stair's run for a stair), so read off a built spec each was counted twice -- deli_a03's basement corridor took a
    lamp for its ladder and another, at the same point, for the ladder's own hole. A ladder spanning that slab whose
    through-hole centre falls in it; a stair serving the storeys either side whose footprint overlaps it."""
    import ladder_geom
    import stairwell
    for ld in getattr(spec, "ladders", []) or []:
        lo, hi = sorted((ld.from_story, ld.to_story))
        if lo < s <= hi:
            hx, hy, _sx, _sy = ladder_geom.through_hole(ld.x, ld.y, ld.width, ld.facing)
            if r[0] - 1e-6 <= hx <= r[2] + 1e-6 and r[1] - 1e-6 <= hy <= r[3] + 1e-6:
                return True
    for st in getattr(spec, "stairs", []) or []:
        served = stairwell.floors_served(spec, st)
        if s in served and (s - 1) in served:
            f = stairwell.footprint_rect(st)
            if r[0] < f[2] and f[0] < r[2] and r[1] < f[3] and f[1] < r[3]:
                return True
    return False


def _landing_point(x, y, bounds, voids):
    """A landing lamp's point: over the landing, or -- where a hole is over it, as over a hole's own landing --
    just past the hole's edge on the side nearest the room's middle, so it hangs from ceiling. None when no side
    stands inside the room."""
    hit = [v for v in (voids or ()) if v[0] <= x <= v[2] and v[1] <= y <= v[3]]
    if not hit:
        return (x, y)
    x0, y0, x1, y1 = hit[0]
    cx, cy = (bounds[0] + bounds[2]) / 2.0, (bounds[1] + bounds[3]) / 2.0
    d = _LANDING_OFF_HOLE
    cands = [(x0 - d, (y0 + y1) / 2.0), (x1 + d, (y0 + y1) / 2.0), ((x0 + x1) / 2.0, y0 - d),
             ((x0 + x1) / 2.0, y1 + d)]
    cands = [p for p in cands if bounds[0] < p[0] < bounds[2] and bounds[1] < p[1] < bounds[3]
             and not any(v[0] <= p[0] <= v[2] and v[1] <= p[1] <= v[3] for v in voids)]
    if not cands:
        return None
    return min(cands, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)


def derive_light_anchors(rooms, openings, story_height, *, cap_thick,
                         wall_thick, ceiling_voids=None, partitions=None,
                         report=None, volumes=None, club_rooms=None,
                         storefronts=None, residence=False, landings=None,
                         bake_reach_rooms=None, selling_rooms=None, tube_rooms=None):
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
    tv_screens, storefront_rows.

    `storefronts` (0.155.0) are the storefront slots as ``{story, facing, x,
    y}``; a fluorescent row whose room they wall carries `reach`, the metres
    to that glass (`_storefront_reach`). Without them no anchor carries it.

    `landings` (0.261.0) are `opening_landings`: a moody room gets a
    fluorescent over each one inside it (see `_LANDING_OFF_HOLE`), appended
    last with the spills, so every anchor before it keeps its place.
    """
    anchors = []
    rep = report if report is not None else {}
    rep.setdefault("rows_shifted", 0)
    rep.setdefault("club_rooms", 0)
    rep.setdefault("tv_screens", 0)
    rep.setdefault("back_bars", 0)
    rep.setdefault("storefront_rows", 0)
    rep.setdefault("storefront_spills", 0)
    rep.setdefault("counter_accents", 0)
    rep.setdefault("rows_laid", 0)
    rep.setdefault("rows_over_aisles", 0)
    rep.setdefault("landing_lights", 0)
    spills = []
    clear = wall_clearance(wall_thick)
    club_ids = set(club_rooms or ())
    # The aisle behind a club bar, asked of the one function that derives
    # it (`level_design.bar_aisle_width`) rather than spelled again here.
    try:
        import level_design
        bar_aisle = level_design.bar_aisle_width()
        aisle_min = level_design.island_aisle_width()
    except Exception:                                    # noqa: BLE001
        bar_aisle = None
        aisle_min = _AISLE_MIN_FALLBACK
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
        # THE ROWS (0.206.0, roadmap 229): along the room's longer axis as
        # before, and across it as many as its work plane asks, each on the
        # ceiling's grid -- `_rows_for_room`. Below grade, or guarding the
        # take: bare bulbs on one centre row instead, unchanged -- the same
        # run machinery (a stairwell still splits a line around its hole),
        # different type, density and hang; see _PENDANT_AREA.
        moody = story < 0 or (bool(r.get("objective")) and r.get("role") not in _LIT_ROLES)
        # A BANK'S MONEY ROOMS ARE LIT BY TUBES (0.280.0, `tube_rooms`): the
        # comps' counting room and cage, not a moody cellar
        if moody and r.get("id") in (tube_rooms or ()):
            moody = False
        if moody:
            home = False          # a bare bulb below grade or over the take
            rot, count, spacing = _row_for_bounds(bounds)
            w = bounds[2] - bounds[0]
            d = bounds[3] - bounds[1]
            long_axis = max(w, d)
            count = max(1, min(int(round((w * d) / _PENDANT_AREA)),
                               _PENDANT_MAX,
                               int(long_axis / _PENDANT_MIN_SPACING) or 1))
            spacing = round(long_axis / count, 3)
            rows = [(rot, c[0], c[1], count, spacing)]
        else:
            home = _home_room(r, residence)
            # over the aisles between the room's shelf runs when it has them
            # (0.207.0, `_lanes_for_room`); a home's room has no aisles
            lanes = None if home else _lanes_for_room(r, bounds, c[2], in_room, aisle_min)
            rows = _rows_for_room(bounds, ceiling_z, c[2],
                                  _work_plane(r, home), home, lanes=lanes,
                                  caps=None if home else room_caps(
                                      r, bounds, selling=r.get("id") in (selling_rooms or ())))
            if lanes:
                rep["rows_over_aisles"] += 1
            rep["rows_laid"] += len(rows)
        lamp_z = round(ceiling_z - _PENDANT_CORD, 3) if moody else ceiling_z
        base_id = ("%s_bulbs" if moody else "%s_ceiling") % r.get("id", "room")
        # Each row is laid across the whole room; a stairwell punched through
        # the ceiling is a hole in the middle of it. Split around the holes on
        # this storey -- see `_row_runs`. A partition ALONG a row (the hospital
        # roof's y = 0 spine under a row laid at y = 0) is not a crossing: the
        # row moves to the larger side of it before any point is judged.
        runs = []
        for k, (rot, rx, ry, count, spacing) in enumerate(rows):
            shifted = _colinear_shift(bounds, rot, walls, clear,
                                      line=ry if abs(rot) < 45.0 else rx)
            if shifted is not None:
                if abs(rot) < 45.0:
                    ry = shifted
                else:
                    rx = shifted
                rep["rows_shifted"] += 1
            got = _row_runs([rx, ry, lamp_z], rot, count, spacing, rects,
                            walls=walls, clear=clear, report=rep)
            # The first row's one run keeps the ORIGINAL id: a split and a
            # second row are the exceptions, and a room that has neither must
            # not get a renamed anchor (ids are how authored overrides bind).
            # A split run is `<id>_<i>` as before; a further row is
            # `<id>_r<k>`, and its split runs `<id>_r<k>_<i>`.
            row_id = base_id if k == 0 else "%s_r%d" % (base_id, k)
            for i, (pos, n, sp) in enumerate(got):
                runs.append((pos, n, sp, rot,
                             row_id if len(got) == 1 else "%s_%d" % (row_id, i), spacing))
        room_reach = 0.0
        for pos, n, sp, rot, rid, row_sp in runs:
            anchors.append({
                "id": rid,
                # A HOME'S DOME (0.208.0, roadmap 229's species step): a home's
                # room hangs a flush-mount dome a bay (Zoo 1.98.0's hardware,
                # Lux 0.75.0's warm lamp under its bowl), not a 2 x 4 office
                # troffer; the rows are the home rule's, unchanged.
                "type": "pendant" if moody else ("dome" if home else "fluorescent"),
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
            # A ROW WALLED BY A STOREFRONT reaches the glass (0.155.0): the
            # walker, 2026-09-28, "do the glass first then the troffer reach".
            # Only a fluorescent -- a bulb's pool is moody on purpose -- and
            # only when there is glass to reach, so every other anchor is
            # byte-identical to 0.154.0's.
            if not moody:
                reach = _storefront_reach(bounds, story, pos, rot, n, sp,
                                          storefronts, wall_thick)
                if reach > 0.0:
                    anchors[-1]["reach"] = reach
                    rep["storefront_rows"] += 1
                    room_reach = max(room_reach, reach)
            # A ROW THAT BAKES TO THE NEXT LAMP (0.279.0): a room in
            # `bake_reach_rooms` -- a supermarket's selling floor -- stamps its
            # row's spacing as `bake_reach`, and Lux (>= 0.80.0) bakes the
            # lamp to the floor under the next one along while its live
            # range, the per-mesh claim, stays the drop rule. Measured on the
            # walker's level: the store's frame 38.5 -> 61.5 mean at x 1.6
            # range (the factory's docs/findings/black_gondola_ends/).
            # THE ROW'S spacing, not the run's (0.280.0): a row split round a
            # teller line's staff room leaves one-lamp runs whose own spacing
            # is 0, and they hang over the line
            if (not moody and not home and row_sp > 0.0
                    and r.get("id") in (bake_reach_rooms or ())):
                anchors[-1]["bake_reach"] = round(float(row_sp), 3)
        # THE STORE'S LIGHT ON THE PAVEMENT (0.156.0): a room whose row
        # reaches its storefront throws that light back out through the
        # glass. Collected here and appended LAST, so every anchor before it
        # keeps its place in the list.
        if room_reach > 0.0:
            head = min(_SPILL_HEAD, round(float(story_height) - _SF_HEAD_MIN, 3))
            got = _spill_anchors(r.get("id", "room"), bounds, story, c[2],
                                 storefronts, wall_thick, head,
                                 round(lamp_z - c[2], 3), room_reach)
            spills += got
            rep["storefront_spills"] += len(got)
        # THE COUNTER'S WARM ACCENT (0.160.0): one bulb over each register
        # counter in a room the fluorescents light. Appended LAST with the
        # spills, so every anchor before it keeps its place.
        if not moody:
            for k, v in enumerate(sorted((v for v in in_room
                                          if any(k in str(v.get("name", ""))
                                                 for k in _COUNTER_VOLUMES)),
                                         key=lambda v: str(v.get("name")))):
                bz = round(ceiling_z - _PENDANT_CORD, 3)
                spills.append({
                    "id": "%s_counter_accent%s" % (r.get("id", "room"), "_%d" % k if k else ""),
                    "type": "counter_accent",
                    "source": "derived",
                    "pos": [round(float(v["x"]), 3), round(float(v["y"]), 3), bz],
                    "rot_y": 0.0,
                    "room": r.get("id"),
                    "row": {"count": 1, "spacing": 0.0},
                    "drop": round(bz - c[2], 3),
                    "reacts_to_alarm": True,
                })
                rep["counter_accents"] += 1
        # THE LANDINGS (0.261.0): in a moody room, a fluorescent over every place an opening comes down into it
        if moody:
            mine = [g for g in (landings or ()) if int(g["story"]) == story
                    and bounds[0] <= g["x"] <= bounds[2] and bounds[1] <= g["y"] <= bounds[3]]
            for k, g in enumerate(mine):
                at = _landing_point(g["x"], g["y"], bounds, rects)
                if at is None:
                    continue
                for pos, _n, _sp in _row_runs([at[0], at[1], ceiling_z], 0.0, 1, 0.0, rects,
                                              walls=walls, clear=clear, report=rep):
                    spills.append({
                        "id": "%s_landing%s" % (r.get("id", "room"), "_%d" % k if k else ""),
                        "type": "fluorescent",
                        "source": "derived",
                        "pos": pos,
                        "rot_y": 0.0,
                        "room": r.get("id"),
                        "row": {"count": 1, "spacing": 0.0},
                        "drop": round(ceiling_z - c[2], 3),
                        "landing": g["kind"],
                        "reacts_to_alarm": True,
                    })
                    rep["landing_lights"] += 1
        # the room's box AFTER its row: a room's first anchor is its ceiling
        # light, as every reader of this list has assumed since v1.0
        anchors += screens
        anchors.append(_room_ambient(r, c[2], ceiling_z, None))

    # A DRAPED WINDOW LETS NO LIGHT IN (0.205.0). A den's windows are drawn
    # shut (`level_design.drape_den_windows`; the walker: "keep the
    # streetlight light out of the club"), so the area light that stands for
    # the street through the glass is not derived behind one. Counted before
    # the skip, so every other window on the wall keeps its id.
    drapes = [v for v in volumes or [] if str(v.get("name", "")).startswith(DRAPE_NAME)]
    win_n = {}
    for o in openings or []:
        if o.get("kind") != "window":
            continue
        wall = o.get("wall") or "win"
        win_n[wall] = win_n.get(wall, 0) + 1
        if any(_drapes_window(v, o) for v in drapes):
            rep["draped_windows"] = rep.get("draped_windows", 0) + 1
            continue
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
    # a residence (0.169.0) derives none: its front door is one more exterior
    # door to the wall-pack loop below
    sign = None if residence else _storefront_sign(openings, wall_thick)
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
    anchors += spills
    return anchors


def _bake_reach_rooms(rooms, business):
    """The rooms whose fluorescent rows bake to the next lamp (0.279.0): a
    supermarket's selling floor (`level_design.is_supermarket_floor`), the
    walker's "far too dark in the super market"."""
    if not business:
        return set()
    import level_design
    return ({r.get("id") for r in rooms or () if level_design.is_supermarket_floor(r, business)}
            | _selling_rooms(rooms, business))


def _selling_rooms(rooms, business):
    """The rooms lit at a selling room's density whatever their id says
    (0.280.0): a bank's public rooms (`bank_public`)."""
    return {r.get("id") for r in rooms or () if bank_public(r, business)}


def _tube_rooms(rooms, business):
    """The rooms below grade or over the take that are lit by tubes, not
    moody bulbs (0.280.0): every such room of a bank."""
    if not is_bank(business):
        return set()
    return {r.get("id") for r in rooms or ()}


def build_light_manifest(building_id, rooms, openings, story_height,
                         *, cap_thick, wall_thick, authored=None, theme=None,
                         ceiling_voids=None, partitions=None, report=None,
                         volumes=None, club_rooms=None, storefronts=None,
                         business=None, landings=None):
    """Full `<name>.lights.json` manifest. `authored` is an optional list of
    hand-placed anchors; an authored anchor replaces a derived one with the
    same id (auto defaults + spec overrides, like props). `volumes` and
    `club_rooms` are `derive_light_anchors`'s.

    `business` (0.165.0) is the building's identity,
    `level_design.club_building_id(spec)`: every `sign` anchor that does not
    name its own carries it, and Zoo's `sign_box` paints the business's name
    from it (`storefront_names`) -- until Zoo 1.37.0 every derived sign in
    the library was a blank lit box (cold run 9120)."""
    anchors = derive_light_anchors(rooms, openings, story_height,
                                   cap_thick=cap_thick, wall_thick=wall_thick,
                                   ceiling_voids=ceiling_voids,
                                   partitions=partitions, report=report,
                                   volumes=volumes, club_rooms=club_rooms,
                                   storefronts=storefronts,
                                   residence=is_residence(business),
                                   landings=landings,
                                   bake_reach_rooms=_bake_reach_rooms(rooms, business),
                                   selling_rooms=_selling_rooms(rooms, business),
                                   tube_rooms=_tube_rooms(rooms, business))
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
    if business:
        for a in anchors:
            if a.get("type") == "sign" and not a.get("business"):
                a["business"] = str(business)
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
