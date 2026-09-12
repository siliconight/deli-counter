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
    (("crate", "pallet", "col_", "pillar", "column", "stack", "pump",
      "cart", "planter", "canopy", "kiosk", "vault"), None),
    (("teller",), "teller_line"),
    (("counter", "reception", "station", "island", "cage", "bar_"), "counter"),
    (("desk", "cubicle"), "desk"),
    (("cabinet", "locker"), "filing_cabinet"),
    (("shelf", "shelving", "rack", "stock"), "shelving"),
    (("vending",), "vending_machine"),
    (("atm",), "atm"),
    (("hvac", "roof_unit"), "hvac_unit"),
    (("tank",), "water_tank"),
    (("seat", "bench", "waiting"), "chair"),
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
