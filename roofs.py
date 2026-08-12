"""
roofs.py  --  pure roof-slot derivation (no bpy), like lights.py / interactives.py
==================================================================================
The top-story ceiling slab is baked by deli_counter.Builder._slabs(); this module
derives the art-pass SWAP SLOTS for it so Zoo can dress the roof (flat membrane,
parapets, rooftop units, skylights). Kept pure so the derivation is unit-tested
without Blender. See docs/ROOF_MANIFEST.md.

Transforms are raw spec/Blender Z-up coords, same as the wall slots; rot_y is
degrees about up. A roof slot is a wall slot laid flat: facing "up", rot_y 0,
center pivot, unit scale (themed art is exact-fit, never stretched).

THE ROOF CARRIES THE SLAB'S HOLES, and until 2026-08-09 it did not. A roof slot
is not a skin: its `fit.dims` is the slab's real thickness and its collision is
`trimesh`, so the themed module IS a collider spanning the whole plan. A floor
or ceiling skin that forgot a void is a cosmetic fault; a roof that forgets one
is a wall. Measured on `bank_branch_a04`: Deli Counter cut the roof-slab hole
exactly where `ladder_geom.through_hole` says (verified in `slab_col_2-colonly`,
corners 15.45/16.55/-10.90), the art pass laid `roof_rockay_01_w4000.glb` over
it with no void, and the walk bot's ladder stalled against a collider named
`Roof` at the slab underside -- a ladder rising a full storey into solid roof.
Every gate passed, because every gate checks the slab and none checks what is
laid on it.
"""

ROOF_SLOT_ROLE = "roof"
GREYBOX_REF = "roof_greybox_01"


def _slot(sid, story, cx, cy, cz, sx, sy, ft, room=None, style=1,
          material=None, voids=None):
    return {
        "slot_id": sid, "role": ROOF_SLOT_ROLE, "size_mod": "full",
        "style": style, "material": material,
        "current_ref": GREYBOX_REF, "kit_axis": "theme",
        "wall": None, "story": story, "facing": "up", "room": room,
        "transform": {"translation": [round(cx, 4), round(cy, 4), round(cz, 4)],
                      "rot_y": 0, "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [round(sx, 4), round(sy, 4), round(ft, 4)],
                "pivot": "center", "openings": [], "collision": "trimesh",
                # Rectangular holes in the PLATE's own x/y, cut by
                # core.arch.plate_parts -- the same key and the same shape
                # `floors._slot` emits, and named `voids` for the reason stated
                # there: `openings` is the WALL contract, a hole in a standing
                # slab's x/z, and the two are not the same shape.
                "voids": list(voids or ())},
    }


def roof_slots(spec, story, cz, ft):
    """Return the roof swap-slots for the top story.

    spec  -- a LevelSpec (reads footprint_x/y, roof_mode, rooms, slab_holes).
    story -- top story index (roof level).
    cz    -- slab center Z (raw Blender coords).
    ft    -- roof thickness.

    "footprint" -> one slot over the whole plan.
    "per_room"  -> one slot per top-story room with room.roofed (open-air rooms
                   opt out).

    ORDER OF CALL IS PART OF THE CONTRACT. `spec.slab_holes` is appended DURING
    the build by `_stairs`, `_ladders`, `_ramps` and `_vertical_links`, so this
    must be called after them -- `Builder._record_roof_slots` sits beside
    `_record_slab_slots`, after `_slab_holes_cut`, for exactly that reason. It
    used to be called from `_slabs()`, the first build step, where
    `slab_holes` is always empty and a roof could not have carried a hole even
    if it had asked for one.
    """
    # roof skin style follows the spec's default material (skin_style.py) --
    # same axis every other slot varies on.
    import skin_style
    # The clip is floors' -- one definition of "which holes land on this rect",
    # imported rather than restated, the same rule `ladder_geom` states for the
    # hole itself. `room_voids` clips to the rect it is handed and never reads
    # its `room` argument, so it is already the general function this needs.
    from floors import room_voids
    mat = getattr(spec, "default_material", None)
    mapping = skin_style.material_styles(
        [m.id for m in getattr(spec, "materials", [])])
    style = skin_style.style_for(mat, mapping, mat)
    if getattr(spec, "roof_mode", "footprint") == "per_room":
        out = []
        for r in spec.rooms:
            if r.story == story and getattr(r, "roofed", True):
                b = r.bounds
                cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
                sx, sy = b[2] - b[0], b[3] - b[1]
                out.append(_slot(f"roof_{r.id}", story, cx, cy, cz,
                                 sx, sy, ft, room=r.id,
                                 style=style, material=mat,
                                 voids=room_voids(spec, r, story,
                                                  cx, cy, sx, sy)))
        return out
    return [_slot("roof_footprint", story, 0.0, 0.0, cz,
                  spec.footprint_x, spec.footprint_y, ft,
                  style=style, material=mat,
                  voids=room_voids(spec, None, story, 0.0, 0.0,
                                   spec.footprint_x, spec.footprint_y))]
