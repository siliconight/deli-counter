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
"""

ROOF_SLOT_ROLE = "roof"
GREYBOX_REF = "roof_greybox_01"


def _slot(sid, story, cx, cy, cz, sx, sy, ft, room=None):
    return {
        "slot_id": sid, "role": ROOF_SLOT_ROLE, "size_mod": "full", "style": 1,
        "current_ref": GREYBOX_REF, "kit_axis": "theme",
        "wall": None, "story": story, "facing": "up", "room": room,
        "transform": {"translation": [round(cx, 4), round(cy, 4), round(cz, 4)],
                      "rot_y": 0, "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [round(sx, 4), round(sy, 4), round(ft, 4)],
                "pivot": "center", "openings": [], "collision": "trimesh"},
    }


def roof_slots(spec, story, cz, ft):
    """Return the roof swap-slots for the top story.

    spec  -- a LevelSpec (reads footprint_x/y, roof_mode, rooms).
    story -- top story index (roof level).
    cz    -- slab center Z (raw Blender coords).
    ft    -- roof thickness.

    "footprint" -> one slot over the whole plan.
    "per_room"  -> one slot per top-story room with room.roofed (open-air rooms
                   opt out).
    """
    if getattr(spec, "roof_mode", "footprint") == "per_room":
        out = []
        for r in spec.rooms:
            if r.story == story and getattr(r, "roofed", True):
                b = r.bounds
                out.append(_slot(f"roof_{r.id}", story,
                                 (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0, cz,
                                 b[2] - b[0], b[3] - b[1], ft, room=r.id))
        return out
    return [_slot("roof_footprint", story, 0.0, 0.0, cz,
                  spec.footprint_x, spec.footprint_y, ft)]
