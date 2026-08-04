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
#:   connector      circulation takes the traffic; tile is what a concourse
#:                  gets and it changes underfoot from the carpet either side.
#:   fortifiable    back-of-house. Concrete says "not for customers".
#:   objective_room the money rooms are the plainest; a vault floor is a slab.
#:
#: A room carrying its own ``material`` overrides this. Unknown roles fall back
#: to the spec default, so a new role never fails -- it just looks ordinary.
FLOOR_BY_ROLE = {
    "public_entry": "carpet",
    "connector": "tile",
    "fortifiable": "concrete",
    "objective_room": "concrete",
}

#: Room role -> ceiling material. Ceilings differ from floors on purpose: a
#: suspended acoustic grid over a public room, hard plaster or bare concrete
#: behind the counter. Same override and fallback rules.
CEILING_BY_ROLE = {
    "public_entry": "ceiling_tile",
    "connector": "ceiling_tile",
    "fortifiable": "drywall",
    "objective_room": "concrete",
}


def cap_thick(spec, story, top):
    """Thickness of the slab that caps ``story``.

    The same rule as ``Builder._cap_thick``: the slab above the top occupied
    storey is the roof and may use ``roof_thick``. Duplicated deliberately --
    this module is pure and importing the Builder would drag bpy in -- and
    named the same so the pair is findable if either changes.
    """
    return ((getattr(spec, "roof_thick", None) or spec.floor_thick)
            if story + 1 == top else spec.floor_thick)


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


def _material(room, mapping, default):
    """A room's own material wins; then the role map; then the spec default."""
    own = getattr(room, "material", None)
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
    mapping = skin_style.material_styles(
        [m.id for m in getattr(spec, "materials", [])])
    out = []
    for r in getattr(spec, "rooms", []):
        s = int(getattr(r, "story", 0))
        if s >= top:
            continue          # nothing stands on the roof slab
        b = r.bounds
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        sx, sy = b[2] - b[0], b[3] - b[1]

        fmat = _material(r, FLOOR_BY_ROLE, default)
        out.append(_slot(
            "floor_%s" % r.id, FLOOR_SLOT_ROLE, FLOOR_GREYBOX_REF, s,
            cx, cy, s * spec.story_height + skin / 2.0, sx, sy, "up",
            room=r.id, style=skin_style.style_for(fmat, mapping, default),
            material=fmat,
            voids=room_voids(spec, r, s, cx, cy, sx, sy)))

        cmat = _material(r, CEILING_BY_ROLE, default)
        under = (s + 1) * spec.story_height - cap_thick(spec, s, top)
        out.append(_slot(
            "ceiling_%s" % r.id, CEILING_SLOT_ROLE, CEILING_GREYBOX_REF, s,
            cx, cy, under - skin / 2.0, sx, sy, "down",
            room=r.id, style=skin_style.style_for(cmat, mapping, default),
            material=cmat,
            voids=room_voids(spec, r, s + 1, cx, cy, sx, sy)))
    return out
