"""
floors.py  --  pure floor/ceiling slot derivation (no bpy), mirroring roofs.py
=============================================================================
``Builder._slabs()`` bakes one slab per storey and gives the MESH a role --
``"ceiling"`` for the top cap, ``"floor"`` for the rest -- but only the roof
ever became a SWAP SLOT. So every interior floor and ceiling in every building
shipped as bare greybox while the rest of the pipeline was ready for them:

* Zoo has ``recipes/floor.py`` and ``recipes/ceiling.py``.
* Zoo's genome declares ``concrete / tile / carpet / wood / dirt`` for floors
  and ``concrete / plaster / ceiling_tile / drywall / metal`` for ceilings,
  with a style block for each.
* Pixelcoat builds ``wood_``, ``carpet_``, ``tile_``, ``plaster_``,
  ``ceiling_tile_`` and ``drywall_`` packs for the theme.

Three layers ready and nothing asking. Measured on a shipped manifest, the slot
roles were ``roof 1, wall 299, doorway 10, breach 3, window 6`` -- no floor, no
ceiling, so the art pass had nothing to swap.

ONE SLAB IS TWO SURFACES. A slab's top face is the floor of the storey above it
and its underside is the ceiling of the storey below. Slotting it once would
force both to share a material, and a wood floor implies a wood ceiling under
it, which is not a building. So each occupied storey gets TWO slots: a floor
skin lying on the slab below it and a ceiling skin hanging under the slab above
it.

NEITHER SKIN IS COPLANAR WITH THE SLAB. The floor skin sits fully ON the slab's
top face and the ceiling skin fully UNDER the next slab's underside, so no pair
of faces shares a plane. ``_slabs`` already documents what coincident faces cost
here -- an inset slab left a band at the perimeter belonging to neither surface,
and every interior partition z-fought the roof. Sitting proud is 2 cm of offset
and no fight.

COLLISION STAYS WITH THE SLAB. Skins are ``"none"``; DC's trimesh slab is
authoritative, exactly as facade covers leave the greybox collision alone. A
floor skin that carried its own collision would put a second walkable surface
2 cm above the first.

Transforms are raw spec/Blender Z-up coords, same as the wall and roof slots.
"""

FLOOR_SLOT_ROLE = "floor"
CEILING_SLOT_ROLE = "ceiling"
FLOOR_GREYBOX_REF = "floor_greybox_01"
CEILING_GREYBOX_REF = "ceiling_greybox_01"

#: How thick a swap skin is. Thin enough to read as a surface rather than a
#: slab, thick enough to clear the geometry it lies on without z-fighting.
SKIN_THICK = 0.02

#: Room role -> floor material. OPINIONS WITH REASONS, not derived facts, and
#: the first place to edit when a building should read differently:
#:
#:   public_entry   a gaming floor is carpeted -- real ones carpet to deaden
#:                  sound and hide wear, and it reads instantly as "front of
#:                  house".
#:   safe_room      the same front-of-house read: a hospital lobby, a bank
#:                  hall. Carpet says "you are meant to be here".
#:   connector      circulation takes the traffic; tile is what a concourse
#:                  gets and it changes underfoot from the carpet either side.
#:   route_node     a ward, an office bay, a sales floor: the rooms a route
#:                  passes through. Hard-wearing tile, like the corridor.
#:   open_floor     a hall. Tile for the same reason.
#:   loot_room      an office with something in it: carpet, like the offices
#:                  around it, so the loot is not announced by the floor.
#:   finale         the set piece. Wood, the one floor nothing else gets.
#:   fortifiable    back-of-house. Concrete says "not for customers".
#:   objective_room the money rooms are the plainest; a vault floor is a slab.
#:   vault          a slab, by definition.
#:   utility        plant rooms are poured concrete, painted at best.
#:   staging        a loading dock, a prep area: concrete.
#:   stairwell      concrete; the flight itself is (roadmap 144).
#:
#: THE RULE THE TWO MAPS OBEY: for every role, the floor and the ceiling are
#: DIFFERENT materials, and neither is the material a partition wears
#: (drywall, in every preset that has partitions). Walked on cold run 9005
#: (2026-09-11): a ward whose floor, walls and ceiling all wore concrete read
#: as generated -- "the floor, side and ceiling shouldn't all be the same
#: texture; it looks good when they are different but uniform in some way".
#: Uniform by ROLE, different by SURFACE. `test_floors` asserts the rule
#: over both maps so a later edit cannot quietly break it.
#:
#: Every material named here is guaranteed a style by `FINISH_PALETTE` below.
#: Before that guarantee, `carpet`, `tile` and `ceiling_tile` were absent from
#: every authored palette, so `skin_style.style_for` fell through to the
#: default and hand them all concrete's style -- concrete's Pixelcoat pack and
#: concrete's module filename. On the shell walked above: 7 of 9 floors and
#: 9 of 9 ceilings at style 1, the two `ceiling_tile` ceilings included.
#:
#: A room carrying its own ``floor_material`` / ``ceiling_material`` (or
#: ``material``, for both) overrides this. Unknown roles fall back to the spec
#: default, so a new role never fails -- it just looks ordinary.
FLOOR_BY_ROLE = {
    "public_entry": "carpet",
    "safe_room": "carpet",
    "connector": "tile",
    "route_node": "tile",
    "open_floor": "tile",
    "loot_room": "carpet",
    "finale": "wood",
    "fortifiable": "concrete",
    "objective_room": "concrete",
    "vault": "concrete",
    "utility": "concrete",
    "staging": "concrete",
    "stairwell": "concrete",
}

#: Room role -> ceiling material. Ceilings differ from floors on purpose: a
#: suspended acoustic grid over a public room, hard plaster or bare concrete
#: behind the counter. Same override and fallback rules.
#:
#:   ceiling_tile   the dropped grid: every public and circulation room in a
#:                  1990s commercial building, wards and offices included.
#:   drywall        a hard flat ceiling behind the counter -- the one place a
#:                  ceiling may share the partitions' material, because a
#:                  fortifiable room's floor is concrete and the pair is
#:                  still two surfaces.
#:   plaster        the money rooms and the plant: a painted hard ceiling over
#:                  a slab floor. NOT concrete, which was the old answer and
#:                  made the vault a concrete box on every face.
#:   wood           nowhere. A wood ceiling is a lodge, not a building here.
CEILING_BY_ROLE = {
    "public_entry": "ceiling_tile",
    "safe_room": "ceiling_tile",
    "connector": "ceiling_tile",
    "route_node": "ceiling_tile",
    "open_floor": "ceiling_tile",
    "loot_room": "ceiling_tile",
    "finale": "plaster",
    "fortifiable": "drywall",
    "objective_room": "plaster",
    "vault": "plaster",
    "utility": "plaster",
    "staging": "plaster",
    "stairwell": "plaster",
}

#: The FINISH PALETTE: every material the two maps can name, with the
#: acoustic descriptor it carries into `gameplay.json` when the authored
#: palette does not declare it. Appended AFTER the authored materials, in
#: this order, by `ensure_finish_palette` (called by the spec loader) -- so
#: an authored material keeps the style index it always had, every finish
#: gains one that exists, and two builds of one spec agree on the numbering.
#:
#: Acoustics are gool's enum (`spec_types.AcousticMaterial`), which has no
#: Carpet or Tile: carpet and an acoustic tile are `Curtain` (soft, absorbent
#: -- that is what the grid is for), tile is `Concrete` (a hard glossy
#: surface over a slab), plaster is `Drywall`. The absorption/damping floats
#: sit against the authored palette's own scale (concrete 0.7/0.6, glass
#: 0.1/0.05, metal 0.5/0.3): carpet and the grid above concrete, tile below
#: it. Opinions, like the maps; edit them here and nowhere else.
#:
#: concrete / drywall / wood repeat `presets._PALETTE` byte for byte, and a
#: test holds the two together, because a spec whose author dropped `wood`
#: from the palette still has a `finale` role to floor.
FINISH_PALETTE = (
    {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
    {"id": "drywall", "acoustic": "Drywall"},
    {"id": "wood", "acoustic": "Wood"},
    {"id": "carpet", "acoustic": "Curtain", "absorption": 0.85, "damping": 0.75},
    {"id": "tile", "acoustic": "Concrete", "absorption": 0.3, "damping": 0.2},
    {"id": "ceiling_tile", "acoustic": "Curtain", "absorption": 0.9, "damping": 0.8},
    {"id": "plaster", "acoustic": "Drywall", "absorption": 0.45, "damping": 0.4},
)


def missing_finish_materials(spec):
    """The `FINISH_PALETTE` entries the spec's own palette does not declare,
    in palette order. Pure: reads ``spec.materials``, writes nothing."""
    have = {m.id for m in getattr(spec, "materials", None) or ()}
    return [dict(m) for m in FINISH_PALETTE if m["id"] not in have]


def palette_ids(spec):
    """Material ids in STYLE order: the authored palette, then whatever the
    finish palette adds to it. This is the list `skin_style.material_styles`
    should be handed everywhere, and it is the same list whether or not
    `ensure_finish_palette` has run on the spec -- so a slot derived from a
    bare test spec and one derived from a loaded spec number their styles
    identically."""
    ids = [m.id for m in getattr(spec, "materials", None) or ()]
    return ids + [m["id"] for m in missing_finish_materials(spec)]


def ensure_finish_palette(spec):
    """Append the missing finish materials to ``spec.materials`` so the
    builder's material index, `validate`, and the gameplay materials list all
    see the palette the floor and ceiling slots draw from. Returns the ids
    added; idempotent. The list is rebound, not extended in place, because a
    spec class may share one default list between instances."""
    from spec_types import Material
    missing = missing_finish_materials(spec)
    spec.materials = list(getattr(spec, "materials", None) or ()) + [
        Material(**m) for m in missing]
    return [m["id"] for m in missing]


def cap_thick(spec, story, top):
    """Thickness of the slab that caps ``story``.

    The same rule as ``Builder._cap_thick``: the slab above the top occupied
    storey is the roof and may use ``roof_thick``. Duplicated deliberately --
    this module is pure and importing the Builder would drag bpy in -- and
    named the same so the pair is findable if either changes.
    """
    return ((getattr(spec, "roof_thick", None) or spec.floor_thick)
            if story + 1 == top else spec.floor_thick)


def ceiling_voids(spec):
    """Every slab hole as a WORLD XY rect, tagged with the storey whose
    CEILING it opens. For consumers that work per storey rather than per
    room skin -- the light manifest is the first.

    The storey shift is the same rule `room_voids` states above and must not
    be restated by the caller: a hole with ``story == s`` cuts the slab whose
    top face is the floor of storey s, so it opens the ceiling of storey
    ``s - 1``. Off by one here and a fluorescent row splits around the hole
    one flight up and sails straight through the real one, which on a walk
    looks exactly like no fix at all. One rule, one place, because two copies
    drift -- see `cap_thick`.

    World coords, not room-centred: a light row is placed from the room's own
    centre and has no skin to be relative to. Not clipped to any room either;
    a hole outside a room simply contains none of its fixtures.

    Deduped for the same reason `room_voids` dedupes -- a spec-authored hatch
    is appended a second time by `_vertical_links`, and a caller that reports
    "N voids subtracted" would be quoting a number that is not the number of
    holes.
    """
    out, seen = [], set()
    for hole in getattr(spec, "slab_holes", ()) or ():
        v = (int(getattr(hole, "story", 0)) - 1,
             round(float(hole.x) - float(hole.size_x) / 2.0, 4),
             round(float(hole.y) - float(hole.size_y) / 2.0, 4),
             round(float(hole.x) + float(hole.size_x) / 2.0, 4),
             round(float(hole.y) + float(hole.size_y) / 2.0, 4))
        if v in seen:
            continue
        seen.add(v)
        out.append({"story": v[0], "x0": v[1], "y0": v[2],
                    "x1": v[3], "y1": v[4]})
    return out


def room_voids(spec, room, slab_story, cx, cy, sx, sy):
    """The slab holes that fall inside a room, in the skin's own centred coords.

    ``spec.slab_holes`` is what ``Builder._slab_holes_cut`` boolean-subtracts
    from the slab: stairwells, ramps and hatches, each with ``story / x / y /
    size_x / size_y`` in world XY. A hole with ``story == s`` cuts the slab
    whose TOP face is the floor of storey s -- so it opens the floor of storey
    s and the ceiling of storey s-1, and the two skins ask for different
    stories.

    Without this a skin is a plain rectangle laid over a slab full of holes.
    The ceiling one caps the stairwell: you see ceiling above the staircase and
    you cannot climb it.
    """
    hx, hy = sx / 2.0, sy / 2.0
    out = []
    for hole in getattr(spec, "slab_holes", ()) or ():
        if int(getattr(hole, "story", 0)) != int(slab_story):
            continue
        x0 = float(hole.x) - float(hole.size_x) / 2.0 - cx
        x1 = float(hole.x) + float(hole.size_x) / 2.0 - cx
        y0 = float(hole.y) - float(hole.size_y) / 2.0 - cy
        y1 = float(hole.y) + float(hole.size_y) / 2.0 - cy
        # drop holes that miss this room entirely; the rest are clipped again
        # by core.arch.plate_voids, which also keeps a rim so the plate's outer
        # bbox still equals its authored dims.
        if x1 <= -hx or x0 >= hx or y1 <= -hy or y0 >= hy:
            continue
        out.append({"x0": round(x0, 4), "y0": round(y0, 4),
                    "x1": round(x1, 4), "y1": round(y1, 4)})
    # DEDUPE. A hatch authored in the spec is appended AGAIN by
    # `_vertical_links`, so `slab_holes` carries it twice and three plates came
    # out with the identical rect listed two times. The tiling unions them and
    # does not care, but `void_tag` hashes the list -- so the same hole listed
    # once and twice would name two different modules for identical geometry,
    # which is the collision this whole naming change exists to stop.
    seen, uniq = set(), []
    for v in out:
        k = (v["x0"], v["y0"], v["x1"], v["y1"])
        if k not in seen:
            seen.add(k)
            uniq.append(v)
    return uniq


#: Largest edge a slab's VISUAL mesh may have, in metres (roadmap 54). Godot's
#: GL Compatibility renderer lights at most `max_lights_per_object` positional
#: lights per MESH (engine default 8), so a full-footprint `slab_<n>` visual --
#: 34 to 52 m on the shipped buildings -- is one light budget for a whole
#: storey. That is the reason level_factory ships a per-object light cap at
#: all. Collision is NOT tiled: the one trimesh slab stays authoritative,
#: keeps its boolean-cut holes, and a collider has no light budget.
#:
#: WHY 5.0 AND NOT 8.0. 8.0 was the first cut and passed 4665 of 4679 meshes;
#: census #7 (2026-08-24, lot_demo_001, every fluorescent already trimmed to
#: its floor-pool minimum of drop + 1.0) measured the residue: office slab
#: tiles at 8.0 x 6.8 still bound 9-10 claimants. The count a tile collects
#: scales with its collection RECTANGLE, (tile + 2*range) per axis -- about
#: 260 m^2 of lamp-collecting area at 4.4 m ranges -- and the range trims
#: that would shed the rest (0.44-0.69 m, per the census's own margin
#: forensics) cost floor coverage Lux cannot pay. 5.0 shrinks the rectangle
#: ~35%, scaling the worst measured tile from 10 claimants to ~6: under the
#: budget with headroom for a bake wobble, while ranges stay at the minimum
#: that still lights floors. Zoo's `core.arch.PLATE_TILE` stays 8.0 ON
#: PURPOSE: its plates measured within budget at census #7 (the arena
#: cleared once ranges went drop-derived), and this number is derived from
#: THIS kit's lamp density, not from a geometry law the repos share -- do
#: not reconcile them casually (the VERSION/CHANGELOG rule).
SLAB_TILE = 5.0


def slab_tiles(sx, sy, tile=SLAB_TILE):
    """Cut a footprint into visual tiles: ``[(suffix, (dx, dy), (tx, ty))]``.

    Offsets are from the slab's own centre, so the Builder adds them to the
    slab centre it already computes. A footprint inside the tile on both axes
    returns the single ``("", (0, 0), (sx, sy))`` entry -- name and geometry
    byte-identical to what `_slabs` always emitted, so a corner store's GLB
    does not change by one byte.

    Equal division per axis (``ceil(extent / tile)`` cells), interior cut
    lines snapped to whole millimetres: no sliver tiles at an edge (item 41's
    fragmentation counter-pressure), and neighbours meet at the same rounded
    coordinate, so there are no micron cracks for a grazing light to pick out.
    """
    if not tile or tile <= 0.0:
        return [("", (0.0, 0.0), (sx, sy))]
    eps = 1e-6
    nx = int((sx - eps) // tile) + 1 if sx > tile + eps else 1
    ny = int((sy - eps) // tile) + 1 if sy > tile + eps else 1
    if nx == 1 and ny == 1:
        return [("", (0.0, 0.0), (sx, sy))]

    def edges(extent, n):
        lo = -extent / 2.0
        return ([lo] + [round(lo + extent * k / n, 3) for k in range(1, n)]
                + [lo + extent])

    xe, ye = edges(sx, nx), edges(sy, ny)
    out = []
    for j in range(ny):
        for i in range(nx):
            out.append((f"_t{j}_{i}",
                        (round((xe[i] + xe[i + 1]) / 2.0, 6),
                         round((ye[j] + ye[j + 1]) / 2.0, 6)),
                        (round(xe[i + 1] - xe[i], 6),
                         round(ye[j + 1] - ye[j], 6))))
    return out


def _slot(sid, role, ref, story, cx, cy, cz, sx, sy, facing, room=None,
          style=1, material=None, voids=None):
    return {
        "slot_id": sid, "role": role, "size_mod": "full",
        "style": style, "material": material,
        "current_ref": ref, "kit_axis": "theme",
        "wall": None, "story": story, "facing": facing, "room": room,
        "transform": {"translation": [round(cx, 4), round(cy, 4), round(cz, 4)],
                      "rot_y": 0, "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [round(sx, 4), round(sy, 4), round(SKIN_THICK, 4)],
                "pivot": "center", "openings": [], "collision": "none",
                # Rectangular holes in the PLATE's own x/y, cut by
                # core.arch.plate_parts. `openings` is the wall contract -- a
                # hole in a standing slab's x/z -- and the two are not the same
                # shape, so they get different names.
                "voids": list(voids or ())},
    }


def _material(room, surface, mapping, default):
    """A room's own per-surface material wins (``floor_material`` /
    ``ceiling_material``); then its ``material`` for both; then the role
    map; then the spec default."""
    own = (getattr(room, "%s_material" % surface, None)
           or getattr(room, "material", None))
    if own:
        return own
    return mapping.get(getattr(room, "role", None), default)


def slab_slots(spec, top, skin=SKIN_THICK):
    """Floor and ceiling swap-slots for every room, on every occupied storey.

    ``spec`` -- a LevelSpec (reads rooms, story_height, floor_thick,
    roof_thick, default_material, materials).
    ``top``  -- the top story index, the one ``_slabs`` treats as the roof.

    Per room rather than per footprint: the material vocabulary exists so the
    lobby can be carpet and the concourse tile, and one slot per storey would
    make that a per-BUILDING choice. Room bounds already carry the division.
    """
    import skin_style
    default = getattr(spec, "default_material", None)
    mapping = skin_style.material_styles(palette_ids(spec))
    out = []
    for r in getattr(spec, "rooms", []):
        s = int(getattr(r, "story", 0))
        if s >= top:
            continue          # nothing stands on the roof slab
        b = r.bounds
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        sx, sy = b[2] - b[0], b[3] - b[1]

        fmat = _material(r, "floor", FLOOR_BY_ROLE, default)
        out.append(_slot(
            "floor_%s" % r.id, FLOOR_SLOT_ROLE, FLOOR_GREYBOX_REF, s,
            cx, cy, s * spec.story_height + skin / 2.0, sx, sy, "up",
            room=r.id, style=skin_style.style_for(fmat, mapping, default),
            material=fmat,
            voids=room_voids(spec, r, s, cx, cy, sx, sy)))

        cmat = _material(r, "ceiling", CEILING_BY_ROLE, default)
        under = (s + 1) * spec.story_height - cap_thick(spec, s, top)
        out.append(_slot(
            "ceiling_%s" % r.id, CEILING_SLOT_ROLE, CEILING_GREYBOX_REF, s,
            cx, cy, under - skin / 2.0, sx, sy, "down",
            room=r.id, style=skin_style.style_for(cmat, mapping, default),
            material=cmat,
            voids=room_voids(spec, r, s + 1, cx, cy, sx, sy)))
    return out
