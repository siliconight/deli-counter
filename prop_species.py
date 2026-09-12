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
that are boxes by nature (``crate``, ``col_``, ``pallet``) are listed with
``None`` so a later keyword cannot claim them.
"""

#: (keywords, species). Order matters.
PROP_SPECIES = (
    (("crate", "pallet", "col_", "pillar", "column", "stack", "pump_island",
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
    (("counter", "reception", "station", "island", "cage", "bar_",
      "workbench", "tool_bench"), "counter"),
    (("desk", "cubicle"), "desk"),
    (("cabinet", "locker"), "filing_cabinet"),
    (("shelf", "shelving", "rack", "stock"), "shelving"),
    (("vending",), "vending_machine"),
    (("atm",), "atm"),
    (("hvac", "roof_unit"), "hvac_unit"),
    (("tank",), "water_tank"),
    (("chair", "seat", "bench", "waiting"), "chair"),
    (("table",), "table"),
    (("safe",), "drop_safe"),
)


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
