"""
material_kind.py  --  pure spec-material -> skin-KIND mapping (no bpy)
=====================================================================
A spec names its surfaces the way a builder would: `brick_ext`, `stone_ext`,
`storefront_glass`, `canopy_steel`. Those names are load-bearing HERE -- they
key the acoustic table and, through `skin_style.material_styles`, the skin
STYLE index -- and they are meaningless to the art pass, which resolves a
Pixelcoat pack by a fixed vocabulary of material KINDS.

MEASURED BEFORE WRITING THIS (2026-09-13, across all 281 specs): the library
names 25 distinct materials in 6,716 surface references, and 16 of the 25 are
not kinds the resolver knows -- 326 references in all. `find_pack` returns
None for those and `make_material` falls back to a FLAT colour, so the 131
surfaces that say `brick_ext` are exactly the ones that never get brick. The
spec that tries hardest to say what it is made of is the one that renders
untextured.

WHY A MAP AND NOT A RENAME. Renaming `brick_ext` to `brick` in 288 specs
would move the style index of every surface in every building (styles are the
1-based ORDER of the spec's `materials` list) and would collapse acoustic
entries that differ. The descriptive name stays; only the KIND emitted on the
slot changes.

TARGET VOCABULARY. The right-hand side is `zoo_keeper.core.skins.KNOWN_KINDS`.
It is duplicated here as a literal rather than imported, because Zoo is a
separate repo and DC must build without it; `tests/test_material_kind.py`
asserts every value is in the list below AND that the list is complete for
this library, so a kind invented here fails rather than resolving to nothing.
"""

#: `zoo_keeper.core.skins.KNOWN_KINDS` as of Zoo 0.88.0 (`velvet`), plus the
#: four club kinds Pixelcoat 0.42.0 draws and Zoo is adding beside this
#: release (`carpet_club`, `wallpaper_club`, `wood_stained`, `paint_block`).
#: Kept here so the test can refuse a target this repo made up; update
#: deliberately. `test_material_kind` pins it to Zoo's list when that repo is
#: beside this one.
SKIN_KINDS = (
    "laminate", "wood", "metal", "plastic", "leather", "rubber",
    "canvas", "carbon", "glass", "glass_facade", "paper",
    "concrete", "plaster", "brick", "stone", "tile", "drywall",
    "siding", "shingle",
    "ceiling_tile", "carpet", "dirt", "tar",
    "velvet",
    "gravel", "vegetation", "foliage",
    "metal_painted", "metal_bare",
    "carpet_club", "wallpaper_club", "wood_stained", "paint_block",
    # a cocktail table's cloth (Zoo 0.89.0): object-owned like velvet
    "cloth",
    # THE CARD SHOP'S TWO SURFACES (Zoo 0.95.0, Pixelcoat 0.44.0). Both are
    # a printed 4 ft sheet and both are separate kinds so they resolve their
    # own pack: `wood_panel` is the reference's lower-wall panelling at a
    # 8 in score pitch, `slatwall` the 3 in grooved melamine the blister
    # hooks hang from. Absent from this tuple, a slot asking for either is
    # an unmapped id -- and Zoo 0.95.0's whole second half is about a kind
    # that reached no mesh and said nothing.
    "wood_panel", "slatwall",
)

#: Every material id this spec library uses, and the kind it resolves to.
#: A name missing from here is reported by `unmapped()` rather than passed
#: through -- a slot carrying a kind nothing can resolve is a flat grey wall
#: that looks like a styling choice.
KIND_BY_MATERIAL = {
    # already kinds
    "brick": "brick",
    "carpet": "carpet",
    "concrete": "concrete",
    "drywall": "drywall",
    "glass": "glass",
    "metal": "metal",
    "tile": "tile",
    "wood": "wood",
    # THE BUILDER'S OWN FINISHES, not the spec's. `floors.FINISH_PALETTE` is
    # appended to every spec's palette so a room role can name a floor and a
    # ceiling, and two of its seven ids appear in no spec file at all --
    # which is why scanning `specs/` missed them and the first twin build
    # printed 8 slots naming a material with no kind.
    "ceiling_tile": "ceiling_tile",
    "plaster": "plaster",
    # the late-1990s layer the art direction names: vinyl or aluminium lap
    # siding over an older shell, and a brown asphalt-shingle roof. Named
    # identically in the spec because there is no builder's synonym for
    # either -- a builder calls siding siding.
    "siding": "siding",
    "shingle": "shingle",
    # what the furnishing pass puts on a prop (0.131.0-0.132.0): a sofa's
    # upholstery, a stool's chrome column, a sign's painted backer
    "leather": "leather",
    "metal_bare": "metal_bare",
    "metal_painted": "metal_painted",
    # THE STRIP CLUB'S SURFACES (Pixelcoat 0.42.0, `level_design._CLUB_FINISHES`):
    # a medallion carpet with worn paths, burgundy flocked paper, muddy brown
    # paint over block. Named for what they are, so the id is the kind.
    "carpet_club": "carpet_club",
    "wallpaper_club": "wallpaper_club",
    "wood_stained": "wood_stained",
    "paint_block": "paint_block",
    "velvet": "velvet",
    # THE CARD SHOP'S SURFACES (Pixelcoat 0.44.0, `level_design`'s
    # `_CARD_SHOP_FINISHES` and the card-shop rows of `_PROP_MATERIALS`).
    # Named for what they are, so the id is the kind -- the same rule the
    # club's four follow. `carpet_tournament` is NOT here and must not be:
    # a pack directory is `<kind>_<theme>`, so the play area's carpet is
    # kind `carpet` and the `card_shop` THEME is what makes it the
    # tournament loop. Inventing a `carpet_tournament` kind would have
    # given it a pack no other theme could answer.
    "wood_panel": "wood_panel",
    "slatwall": "slatwall",
    # a felt pennant and a moulded folding chair, asking for their own
    # species' kind so Zoo's stem carries no `_m`
    "cloth": "cloth",
    "plastic": "plastic",
    # a ceiling hanger's painted board (Zoo 0.98.0), on the same terms: its
    # species' own default, so the stem carries no `_m`. `paper` was already
    # in `SKIN_KINDS` and had no row HERE, which is the exact shape of the
    # defect Zoo 0.95.0's second half is about -- a kind that reaches no mesh
    # and says nothing. It said something this time, because
    # `test_every_material_this_pass_writes_resolves_to_a_kind` asks
    # `unmapped()` of every id the pass writes.
    "paper": "paper",
    # masonry the builder named by where it sits rather than what it is
    "brick_ext": "brick",
    "stone_ext": "stone",
    # concrete by another name: a CMU wall, a poured wall and a stadium's
    # precast are one surface family to a texture pack
    "block_wall": "concrete",
    "poured_concrete": "concrete",
    "stadium_concrete": "concrete",
    # glazing. A storefront and a club front are aluminium-framed glazing
    # systems, which is what `glass_facade` is for; `security_glass` is a
    # thickness, not a surface.
    "storefront_glass": "glass_facade",
    "club_glass": "glass",
    "security_glass": "glass",
    # metal, split the way the kind vocabulary splits it: enamel over sheet
    # is a dielectric, bare and rusted sheet is a conductor
    "painted_steel": "metal_painted",
    "canopy_steel": "metal_painted",
    "cooler_panel": "metal_painted",
    "rusted_metal": "metal",
    # the rest
    "asphalt": "tar",
    "seat_plastic": "plastic",
    "turf": "vegetation",
    "wood_kiosk": "wood",
    "wood_pallet": "wood",
}


def kind_for(material_id, default=None):
    """The skin kind for a spec material id, or `default` when the id is not
    mapped. Never invents one: an unmapped id is a defect to report, not a
    guess to make."""
    if not material_id:
        return default
    return KIND_BY_MATERIAL.get(material_id, default)


def unmapped(material_ids):
    """The ids in `material_ids` this module has no kind for, sorted. Callers
    print this; they do not silently substitute."""
    return sorted({m for m in material_ids if m and m not in KIND_BY_MATERIAL})
