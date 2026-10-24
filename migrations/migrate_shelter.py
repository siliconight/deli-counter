#!/usr/bin/env python3
"""
migrate_shelter.py  --  run the shelter pass over the library (0.249.0)
=======================================================================
Idempotent migration over specs/*.json (the factory's roadmap 283), and the
remedy `test_storey_shelter.test_the_library_is_a_fixed_point_of_the_shelter_pass`
names when a later change leaves a library combat room with nothing to fight
from.

NOTHING RAN THE SHELTER PASS OVER THE LIBRARY. `level_design.seed_cover`
gives a combat room ONE piece at `shelter_height()` when nothing in it breaks
a sightline, but it runs inside `enrich`, and `enrich` runs in `presets.make`
-- `build.py` builds a library spec's JSON as it stands. The guarantee was
tested on presets alone (`test_every_combat_room_big_enough_to_seed_has_shelter`).
A library room was sheltered when furnish happened to stand a tall piece in
it, and a refurnish could take that away with nothing to notice. Measured on
0.248.0's library, eleven rooms of nine specs the pass fills, attributed one
by one (the factory's patches/dc_storey_shelter/):

  * Three read sheltered only by something on another storey -- the float
    window and the storey-blind markers 0.249.0 closes. final_stand's
    stair_core by a cover_high marker two storeys up (z 7.6); rowhouse_raid's
    kitchen by a 1.80 m shelf run on the floor above (its foot at 3.20);
    twin_a01's front_left_1 by a cover_high marker on the ground floor under it.
  * Three were sheltered by furnish's own lockers and shelf runs until a
    refurnish moved them: rail_station_a02's vault_approach (0.204.0),
    rowhouse_raid's basement_vault (0.234.0), warehouse_a01's back_corridor
    (0.131.0).
  * Five were never sheltered in any committed version, by either test:
    cbp_town_finale_midbalanced_schemafixed's main_concourse and
    club_ring_overlook, freight_terminal_a02's gantry_control,
    parking_garage_a02's attendant_booth, primos_pizza's rear_hall.

A spec the pass adds to is then stripped and refurnished
(`migrate_furnish_recipes.migrate`): furnish counts what a room already holds,
and a shelter piece is one more, so the library stays a fixed point of
furnish as well as of this pass. `seed_cover` is additive and idempotent, so
a second run adds nothing.

    python migrations/migrate_shelter.py            # write specs/
    python migrations/migrate_shelter.py --check    # report only; exit 1 if any room would be filled
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402


def migrate(d):
    """Run the shelter pass on one spec dict in place, and refurnish it if the
    pass added anything. Returns the names the pass added."""
    if not d.get("rooms"):
        return []
    before = {v.get("name") for v in d.get("volumes") or []}
    if not level_design.seed_cover(d):
        return []
    added = [v["name"] for v in d["volumes"] if v.get("name") not in before]
    migrate_furnish_recipes.migrate(d)
    return added


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    specs = pieces = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        added = migrate(d)
        if not added:
            continue
        specs += 1
        pieces += len(added)
        print(f"[shelter] {os.path.basename(p)}: " + ", ".join(added))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    verb = "would get" if check else "got"
    print(f"[shelter] {specs} spec(s) {verb} {pieces} shelter piece(s)")
    return 1 if check and pieces else 0


if __name__ == "__main__":
    sys.exit(main())
