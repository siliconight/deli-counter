"""
prop_species.py  --  what a placement's NAME says it is (pure, no bpy)
======================================================================
Roadmap 44, from the inside. Every volume a spec authors is named for what
it is -- ``teller_counter``, ``desk_manager_office``, ``nurse_station``,
``aisle_shelf`` -- and every one reached Zoo as slot role ``prop``, which
Zoo builds as a box wearing the slot's material. Zoo has the species the
names ask for (``desk``, ``counter``, ``shelving``, ``teller_line``,
``filing_cabinet``, ``vending_machine``, ``atm``, 56 in all) and nothing
routed a name to one. The walker's framing: "the blocks should really just
be placeholders until they are replaced by something more diegetic."

THIS IS THE HINT, NOT THE DECISION. Deli Counter knows the name; Zoo knows
whether the species can be built at the slot's size (its genome's ranges).
So the slot carries ``species`` as a hint, Zoo builds that species when the
dims fall in its range and the plain ``prop`` box otherwise, and the stem
names which one it built (``prop_desk_...`` vs ``prop_...``), on both sides
-- ``themed_tscn.module_stem`` and ``zoo_keeper.core.kit.module_stem``, the
usual mirror.

MEASURED 2026-09-11 over 1,443 placements in 176 specs: 721 name a species
Zoo has; the species FITS 142 of them today (desk 82, counter 54, shelving
6); the rest are RUNS (an 8 m teller counter, a 7 m shelf aisle) that only
the box builds until the run species exist (roadmap 44, step 3). 394 are
boxes by nature (crate stacks, columns, pallets) and stay unhinted; 328
name things no species exists for (pumps, carts, planters, kiosks).

Keywords are matched against the lowercased name in table order, first hit
wins, so ``teller_counter`` is a teller line before it is a counter. Names
that are boxes by nature (``crate``, ``col_``; ``pallet`` until 0.131.0) are listed with
``None`` so a later keyword cannot claim them.
"""

#: (keywords, species). Order matters.
PROP_SPECIES = (
    # INTERIOR SPECIES (Zoo 0.84.0), each placed IMMEDIATELY AHEAD of the
    # row that would claim its names first, as that release's entry lists
    # them -- and no further up, because a row moved higher than it needs to
    # be steals names from the rows it jumps. `booth` at the top of this
    # table took `booth_desk` (four parking-garage and one broadcast desk)
    # from `desk`; caught by listing every authored name each new keyword
    # re-routes before the rows were placed. Here: `box_stack` holds `stack`
    # and `cartons` holds `cart`, both in the box row; `dust_sheet` and
    # `booth_seat` go before the chair row (whose `seat` takes
    # `booth_seat`), `pool_table` before `table`, `furnace` before `tank`.
    # What they re-route among the library's authored (not furnished)
    # volumes, measured: `box_stack` x2 (box), `boiler` x3 (box),
    # `booth_seating_*` x4 (chair), `*sofa*` x6 (box).
    (("carton", "banker", "file_box", "box_stack"), "carton_stack"),
    # A PALLET IS NO LONGER A BOX BY NATURE: Zoo has built `pallet_stack`
    # since before this row, and `pallet` sat in the box row below, so the
    # interior furnishing survey found it "routes to a plain box". Ahead of
    # that row because `pallet_stack` holds `stack`. It re-routes 11 authored
    # volumes; the 4.5 x 2.5 loading stacks are past the genome's 1.8 x 1.5
    # and Zoo still builds them as the box, saying so.
    (("pallet",), "pallet_stack"),
    (("crate", "col_", "pillar", "column", "stack", "pump_island",
      "cart", "planter", "canopy", "kiosk", "vault"), None),
    # MINTED 2026-09-12 by zoo/tools/new_species.py (roadmap 150): the
    # first species the library asked for by name (42 `pump` placements,
    # 1.0 x 1.2 x 1.4, metal) and nobody had drawn. A placeholder box
    # today, counted as a pump in every report until its recipe is shaped.
    (("pump",), "pump"),
    # A TELLER LINE IS A GLASS BARRIER OVER A COUNTER, one service window
    # per station (the walker's references, 2026-09-12): Zoo's
    # `teller_line`. The volumes were authored waist-high for a day and
    # routed to `counter`; they are now authored as the full line (2.4 m)
    # and any still at counter height fall to `counter` by Zoo's alternate
    # rule, said in the kit index.
    (("teller",), "teller_line"),
    # THE CLUB SPECIES (Zoo 0.88.0), each ahead of the row that would claim
    # its names and no higher. `bar_` in the counter row takes `bar_stool`,
    # `bar_tv` and `stage_bar_r...` (the tag's `r` follows `bar_`), so the
    # stage, the stool and the TV stand ahead of it; `stool` is also in the
    # chair row and `cocktail`/`club_chair` in the table and chair rows,
    # which come later anyway. Measured re-routes among authored volumes:
    # `stage` x2 (`strip_club_a01`, `_a03`, both the club stage, box before)
    # and nothing else -- `center_field_tv_truck_cover` carries `tv` but
    # neither `bar_tv` nor `wall_tv`.
    (("club_stage", "stage", "pole_stage", "runway"), "club_stage"),
    (("bar_stool", "barstool", "stool"), "bar_stool"),
    (("bar_tv", "wall_tv"), "crt_tv"),
    # THE CLUB'S GAME AND ITS VICE (Zoo 0.91.0): the chalk-score dartboard
    # cabinet and the pull-knob cigarette machine, ahead of the counter row
    # and the cabinet row (`dart_cabinet`). No keyword is a bare "board" or
    # "machine": `scoreboard_*` (5 authored volumes in
    # `cbp_town_finale_midbalanced_schemafixed`) would be
    # taken by the one, and the vending machine is not a cigarette machine.
    # Measured re-routes among authored volumes: none.
    (("dartboard", "dart_board", "dart_cabinet"), "dartboard"),
    (("cigarette",), "cigarette_machine"),
    # THE BACK BAR (Zoo 0.92.0), and it has to stand AHEAD of the counter
    # row below: that row holds `bar_`, and `back_bar_r1d196568_2` carries
    # `bar_` in the middle of its name, so read in the old order every back
    # bar in the library would have been built as a counter -- 2.4 m tall,
    # which the counter genome tops out at 1.2 m short of, so it would not
    # even have fallen back to a box quietly. Measured re-routes among
    # authored (not furnished) volumes: none -- no spec names a volume
    # `back_bar` today, and the club room CALLED `back_bar` in
    # `strip_club_a03` is a room, not a volume.
    (("back_bar", "backbar", "bar_back"), "back_bar"),
    # THE CARD SHOP (Zoo 0.95.0). Five species, and the block stands here
    # for two of them: `folding_table` carries `table` and `folding_chair`
    # carries `chair`, so below those two rows neither keyword could ever
    # fire -- the same defect `cubicle` had above. The other three are
    # claimed by nothing at any height and sit here only to keep the five
    # together.
    #
    # WHAT THIS RE-ROUTES, MEASURED over the 336 specs in `specs/`, by name
    # and then by whether Zoo's genome can build the size:
    #
    #   `display_case`  12 volumes, all routed to a plain box today.
    #                   SIX of them (2.4 x 0.9 x 1.0) fall inside the
    #                   genome and become real glass showcase counters; the
    #                   other six do not -- five at 2.4 x 1.2 x 1.4 and one
    #                   at 8.0 x 2.0 x 2.2 are over the 1.25 m height cap
    #                   (and the last over the 6.0 m width), so Zoo builds
    #                   the box and says so. A hint, not a decision.
    #   `pack_wall`, `showcase`, `pennant`, `folding_table`,
    #   `folding_chair`                                   0 volumes each.
    #
    # `gondola` IS DELIBERATELY NOT A KEYWORD HERE, though Zoo's genome
    # lists it. The eight `gondola_*` volumes in this library are
    # supermarket aisles 1.0-1.2 m deep; `pack_wall`'s genome depth is
    # 0.35-0.60, so every one of them would route to the species by name
    # and fall straight back to the box on depth. A keyword whose every
    # match cannot be built is noise in eight reports, not a routing.
    # Measured: 1.0x5.0x1.6 (2), 1.0x6.0x1.6 (4), 1.2x8.0x1.6 (2).
    (("display_case", "showcase"), "display_case"),
    (("pack_wall",), "pack_wall"),
    (("pennant",), "pennant_row"),
    (("folding_table",), "folding_table"),
    (("folding_chair",), "folding_chair"),
    # THE FLAT ART (Zoo 0.98.0), the other half of the card shop's density.
    # Four species whose whole cost is texture -- a saturated room is 948
    # triangles of art and 2.392 MiB of decoded images.
    #
    # WHAT THIS RE-ROUTES, MEASURED over every spec in `specs/` before the
    # rows were written, against Zoo's full keyword lists for all four:
    # **nothing**. No authored volume in the library carries `poster`,
    # `banner`, `hanger`, `aisle_sign` or any of their spellings, so these
    # rows claim only what `level_design`'s own fixtures write.
    #
    # THREE OF ZOO'S KEYWORDS ARE DELIBERATELY NOT HERE, on `gondola`'s
    # precedent one block up. `mobile` would claim a mobile home or a mobile
    # crane the day either is authored, and a hanging painted board is not
    # either; `banner` and `sign` are left in their compound forms for the
    # same reason -- `scoreboard`, `sign_post` and `sign_box` are already
    # names in this library and a bare keyword is how one of them gets
    # quietly rebuilt as a poster. A keyword whose match would be wrong is
    # worse than one that never fires, because it fires silently.
    (("poster", "wall_poster", "set_poster", "art_print", "framed_print",
      "picture_frame"), "poster"),
    (("hanging_banner", "cloth_banner", "print_banner", "wall_banner",
      "banner_sign"), "hanging_banner"),
    (("ceiling_hanger", "ceiling_sign", "drop_sign", "hanging_model"),
     "ceiling_hanger"),
    (("aisle_sign", "section_sign", "hanging_sign", "aisle_header",
      "overhead_sign"), "aisle_sign"),
    # A CUBICLE BANK IS NOT A DESK (Zoo 0.93.0). It had to stand ahead of the
    # desk row, which held `cubicle` and took all ten of them: the desk genome
    # reaches 12 m wide and 6 m deep, so an 8.0 x 6.0 x 1.2 m cubicle farm
    # FITS it -- it did not fall back to a box, it built as desk geometry at
    # that size, four 8 m tops butted edge to edge over the depth
    # (`desk.py`'s rows), a raft with no aisle. The walker, cold run 9060,
    # 2.68 m from `office_stepped`'s `cubicles_w_0_col`: "these desks are too
    # close to each other?".
    #
    # AND AHEAD OF THE COUNTER ROW, which is further up than the rule above
    # wants and is not a choice: `workstation_bank` carries `station`, so
    # below the counter row that keyword could never fire and the species
    # would answer to one name instead of two -- a keyword that cannot match
    # is the same defect as a parameter nothing reads. What the jump
    # re-routes, measured over the 132 library specs: nothing. The only names
    # carrying `cubicle` are the 10 `cubicles_*` volumes in `office` and
    # `office_stepped` (all 8.0 x 6.0 x 1.2, all `drywall`), none of them
    # carries a keyword from any row between here and `desk`, and no spec
    # names a volume `workstation_bank`.
    (("cubicle", "workstation_bank"), "cubicle_bank"),
    (("counter", "reception", "station", "island", "cage", "bar_",
      "workbench", "tool_bench"), "counter"),
    (("desk",), "desk"),
    (("cabinet", "locker"), "filing_cabinet"),
    (("shelf", "shelving", "rack", "stock"), "shelving"),
    (("vending",), "vending_machine"),
    (("atm",), "atm"),
    (("hvac", "roof_unit"), "hvac_unit"),
    (("furnace", "boiler", "water_heater", "heater"), "furnace"),
    (("tank",), "water_tank"),
    (("dust_sheet", "sheeted", "draped", "covered_"), "dust_sheet"),
    (("booth", "banquette", "sofa", "couch", "settee", "loveseat"),
     "booth_seat"),
    (("club_chair", "tub_chair", "lounge_chair"), "club_chair"),
    (("neon", "club_sign"), "neon_sign"),
    (("chair", "seat", "bench", "waiting"), "chair"),
    (("pool", "billiard"), "pool_table"),
    (("cocktail", "club_table", "highboy"), "cocktail_table"),
    (("table",), "table"),
    (("safe",), "drop_safe"),
    # Species Zoo builds that no name reached (the survey's list). Keywords
    # are whole words a furnishing name carries; `bin` alone is not one,
    # because `cabinet` contains it. `payphone` re-routes the two authored
    # `payphone` volumes, 0.5 m wide and below the genome's 0.525, so Zoo
    # still builds those as the box.
    (("barrel", "drum"), "water_barrel"),
    (("litter_bin", "trash_can"), "litter_bin"),
    (("grill", "griddle"), "flat_top_grill"),
    (("stanchion",), "queue_stanchion"),
    (("payphone",), "payphone"),
)


#: Species whose MODULE owns the volume's collision, so the greybox must not
#: also draw its box.
#:
#: Every other hinted volume is a solid roughly the size of its slot -- a
#: desk, a counter, a filing cabinet -- and the greybox's convex box is a
#: fair collider for it whether or not the art pass ever runs. A cubicle bank
#: is not: it is 8 x 6 m of which the middle 1.2 m is an AISLE, and the box
#: seals it. Measured in cold run 9060's composed shell,
#: `lot/office_stepped/site_base.glb` (building frame, m): the composer keeps
#: the greybox COLLIDER and drops its visual, so `cubicles_w_0_col-convcolonly`
#: stands x -14.000..-6.000, y 3.000..9.000, z 0.000..1.200 -- one solid box --
#: while the themed art beside it is the Zoo module. Whatever Zoo builds
#: inside that box, a body meets the box.
#:
#: So for these, `Builder._volumes` skips `_col_box` and the module's own
#: `-colonly` mesh is the collision. Two consequences, both deliberate:
#: the GREYBOX build of such a volume has no collider at all (it is a
#: drawing of a space, and a solid box is a worse lie about it than nothing),
#: and every planner that reads the SPEC volume -- `level_design`,
#: `vault_room`, `stairwell.stair_guards.solid_volumes` -- still sees
#: `collision: convex` and treats the footprint as occupied, which is what a
#: bank of screens is to a sightline and to a cover marker.
SPECIES_OWNS_COLLISION = frozenset({"cubicle_bank"})


def owns_collision(species):
    """Does this species' module carry the volume's collision itself?"""
    return species in SPECIES_OWNS_COLLISION


def species_for_name(name):
    """The species a placement's name asks for, or None (a box is fine)."""
    key = (name or "").lower()
    for words, species in PROP_SPECIES:
        if any(w in key for w in words):
            return species
    return None


def long_axis_first(size):
    """``(dims, rot_y)`` for a hinted volume: its long horizontal side as the
    module WIDTH, turned 90 degrees when that side is y.

    A recipe builds width along its local x, and Deli Counter authors an
    aisle shelf as 1.0 x 6.0 (deep along y) as readily as 6.0 x 1.0.
    Measured 2026-09-12: turning alone takes desks from 58 to 91 fits of
    153 and counters from 35 to 54 of 137. The slot's dims are what the
    stem and the plan are built from on both sides, so the turn happens
    HERE, once, at emission, and the composer's `_fit_rotation` finds the
    same 90 from the extents. Only hinted volumes are turned -- an unhinted
    box's slot stays byte for byte what it was.
    """
    sx, sy, sz = (float(size[0]), float(size[1]), float(size[2]))
    if sy > sx + 1e-9:
        return [sy, sx, sz], 90.0
    return [sx, sy, sz], 0.0
