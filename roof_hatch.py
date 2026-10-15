"""roof_hatch.py -- the prop slot that stands around a roof ladder's opening (pure, no bpy).

Factory roadmap 170: a `hatch` vertical link on the roof slab cuts the slab and emits a `HATCH_<x>_<y>`
marker, and nothing in any tool put a lid on it -- 43 roof ladders in the library climb out through a
bare hole. This module derives, for every such link, ONE prop slot of species `roof_hatch` (Zoo 1.113.0:
a steel curb around the opening with a hinged lid) and its interactive state machine, so the opening
reads as a hatch somebody built and the game can shut it.

WHAT IT EMITS. A `prop` slot centred on the link, sized to the hole plus the curb (`CURB` a side) and
`HEIGHT` tall, standing on the roof slab's top face (`top * story_height`, where `_slabs` puts that
face). The slot carries the `hatch` machine from `interactives.py` -- `open` is the default, so the
ladder's `roof_hatch_exit` stays a route for every walker and the lid stands up out of the way;
`closed` is the game's to drive. The species owns its collision (`prop_species.SPECIES_OWNS_COLLISION`):
the greybox draws the slot's box for the swap to replace and emits no solid collider over the hole.

WHICH WAY THE LID OPENS. The slot is turned so its local -Y is the hinge side, local +Y the side the
climber's body occupies: `ladder.climb_rect` reserves the body's envelope `reach` along the ladder's
`facing`, so the lid is hinged on the far side from that and the climber steps off away from it. A hatch
with no ladder at its (x, y) faces north. Checked in frames, not assumed: see the factory's
`docs/findings/roof_openings_170/`.
"""
from __future__ import annotations

import interactives

SPECIES = "roof_hatch"
CURB = 0.08          # m; the curb stands this far outside the hole's edge, each side
HEIGHT = 0.2         # m; the curb's height above the slab -- a step-up, under the contract's 0.5
MATERIAL = "metal"
DEFAULT_HOLE = 1.5   # m; `_vertical_links` cuts a hatch with no size_x / size_y at this
_ROT = {"N": 0, "E": 90, "S": 180, "W": 270}


def rot_for(spec, link):
    """The slot's yaw: the ladder at the link's (x, y) says which way the climber's body lies."""
    for ld in getattr(spec, "ladders", None) or []:
        if abs(float(ld.x) - float(link.x)) < 1e-6 and abs(float(ld.y) - float(link.y)) < 1e-6:
            return _ROT.get(getattr(ld, "facing", None), 0)
    return 0


def roof_hatches(spec, style=1):
    """[(slot, gameplay_interactive, box_center, box_size)] for every hatch link on the roof slab.

    `style` is the skin style the builder resolved for `MATERIAL`. A hatch below the roof is a
    floor-to-floor opening, not a scuttle, and gets nothing here.
    """
    top = int(spec.n_stories)
    h_story = float(spec.story_height)
    out = []
    for v in getattr(spec, "vertical_links", None) or []:
        if getattr(v, "kind", None) != "hatch" or v.story is None or v.x is None:
            continue
        if int(v.story) < top or not getattr(v, "cut_slab", True):
            continue
        sx = float(v.size_x or DEFAULT_HOLE)
        sy = float(v.size_y or DEFAULT_HOLE)
        w, d = sx + 2 * CURB, sy + 2 * CURB
        z_top = top * h_story
        center = (float(v.x), float(v.y), z_top + HEIGHT / 2.0)
        size = (w, d, HEIGHT)
        slot_id = f"roof_hatch_{int(v.x)}_{int(v.y)}"
        rot = rot_for(spec, v)
        machine = interactives.derive_interactive(spec.name, slot_id, int(v.story), "hatch", 0.0)
        slot = {
            "slot_id": slot_id, "role": "prop", "size_mod": "full",
            "style": style, "material": MATERIAL, "species": SPECIES,
            "stock": None, "variant": 0, "form": None,
            "current_ref": "prop_greybox_01", "kit_axis": "material",
            "wall": None, "story": None, "facing": None,
            "transform": {"translation": [round(center[0], 4), round(center[1], 4),
                                          round(center[2], 4)],
                          "rot_y": float(rot), "scale": [1.0, 1.0, 1.0]},
            "fit": {"dims": [round(w, 4), round(d, 4), round(HEIGHT, 4)],
                    "pivot": "center", "openings": [], "collision": "none"},
            "interactive": interactives.slot_interactive(machine),
        }
        entry = interactives.gameplay_interactive(
            machine, slot_id,
            {"translation": [round(center[0], 3), round(center[1], 3), round(center[2], 3)],
             "rot_y": float(rot)},
            building=spec.name)
        out.append((slot, entry, center, size))
    return out
