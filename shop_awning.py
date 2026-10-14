"""A corner shop's awning: where Zoo's `shop_awning` (>= 1.108.0) hangs over a corner block's storefront (0.219.0,
factory roadmap 241).

The comps: "Corners carry the life. The corner building has the shop at grade (lit, awning), homes above" (the
factory root's docs/reference/URBAN_MIDRISE_COMPS.md). Deli Counter 0.218.0 built the shop; this hangs the awning
over it, as `stoop.py` stands a rowhome's steps.

WHERE IT HANGS, in the building's frame (x along the front, y back into the house, z up, the front wall `S` with
its outer face at -(footprint_y + wall_thick) / 2):
  * across the front `MARGIN` short of either end, centred;
  * `DEPTH` out from the wall, its back `SINK` inside the wall's outer face -- Zoo's slope ends there, inside the
    wall, and its cheeks, 4 mm off the module's back (`shop_awning_forms.SINK`), 4 mm inside it too, so no face
    of the awning lies on the wall's;
  * its valance's bottom `CLEAR` over the storefront's head, the tallest ground-floor front opening's top, and its
    top `DROP` over that.

CHOSEN, not read: the comps give no dimension. A 1.2 m projection stays inside Level Factory's 2.0 m terrace
frontage, off the sidewalk; 0.85 m over a 2.4 m storefront puts its top under the first floor's sills. No collision:
Level Factory reads an Empty's street edge off its colliders, so the awning moves no line.

Pure: no Blender, so every number here is tested without a build.
"""
from __future__ import annotations

DEPTH = 1.2
DROP = 0.85
MARGIN = 0.3
CLEAR = 0.1
SINK = 0.008
#: Zoo's `shop_awning_forms.FORMS`, in its order (pinned by `test_corner_awning.py`)
FORMS = ("shed_red", "shed_green", "shed_navy", "shed_black")


def head(spec):
    """The storefront's head: the top of the tallest ground-floor front opening, in the building's z (the floor's
    walking surface `floor_thick / 2` over z = 0, as `_opening_to_hole` cuts it). None with no front opening."""
    tops = [spec.floor_thick / 2.0 + op.resolved()["sill"] + op.resolved()["height"]
            for w in spec.ext_walls if w.wall == "S" and w.story == 0 for op in w.openings]
    return max(tops) if tops else None


def plan(spec):
    """``{"form", "centre", "size"}`` for a spec whose `awning` names a form, else None. A form Zoo does not draw,
    or a front with no opening to hang over, is refused rather than dropped."""
    form = getattr(spec, "awning", None)
    if not form:
        return None
    if form not in FORMS:
        raise ValueError("awning %r is not one of %s" % (form, FORMS))
    top = head(spec)
    if top is None:
        raise ValueError("an awning over a front with no ground-floor opening")
    width = float(spec.footprint_x) - 2.0 * MARGIN
    face = -(float(spec.footprint_y) + float(spec.wall_thick)) / 2.0
    z0 = top + CLEAR
    centre = (0.0, face + SINK - DEPTH / 2.0, z0 + DROP / 2.0)
    return {"form": form, "centre": centre, "size": (width, DEPTH, DROP)}
