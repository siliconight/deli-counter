"""
skin_style.py  --  pure material->skin-style mapping (no bpy)
=============================================================
Single source of truth for HOW a surface's material picks its art-pass skin
STYLE, shared by the builder (slot emission), roofs.py, the composer and the
unit tests -- the partition_bounds / ladder_geom pattern.

The style index is the axis Zoo/Pixelcoat vary skins on (module stems are
``{type}_{theme}_{style:02d}_...``). Before this module, every emission site
hard-coded ``style: 1`` -- so every building funnelled Pixelcoat's whole
library through ONE skin. Now the style follows the MATERIAL the greybox
already assigns to each surface (brick_ext vs drywall vs metal ...), so skin
variety is intentional -- exteriors read as brick, interiors as drywall --
deterministic, and stable across rebuilds.

Mapping rule: styles are the 1-based ORDER of the spec's ``materials`` list.
Adding a new material appends a new style; reordering the list is a styling
decision. Unknown/absent materials map to the spec's default material, else
style 1 -- a spec with no materials behaves exactly as before.
"""


def material_styles(material_ids):
    """{material_id: style_index} -- 1-based, in list order, first wins."""
    out = {}
    for i, mid in enumerate(material_ids):
        if mid and mid not in out:
            out[mid] = i + 1
    return out


def style_for(material_id, mapping, default_material=None):
    """The skin style for a surface. Falls back: surface material ->
    default material -> style 1."""
    if material_id and material_id in mapping:
        return mapping[material_id]
    if default_material and default_material in mapping:
        return mapping[default_material]
    return 1
