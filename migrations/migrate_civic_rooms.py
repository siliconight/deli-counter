#!/usr/bin/env python3
"""
migrate_civic_rooms.py  --  the civic rooms refurnished as what they are (0.270.0)
=================================================================================
One-shot, idempotent migration over specs/*.json, lf_ specs excepted. Every spec holding a room of the four kinds
0.270.0 split out of `hall` -- chapel, courtroom, assembly, gallery (`level_design._ROOM_KINDS`) -- is refurnished
(`migrate_furnish_recipes.migrate`), then given, in the order they shipped, the passes the library is a fixed point of: the shelter pass
(`migrate_shelter`), the seeded pieces' corridor and their line (`migrate_seed_corridor`, `migrate_seed_lines`) and the
wall trim (`migrate_wall_crossing`). Those rooms' furniture was a dining hall's, and a chapel of pews is new input to
each: the first trial left three chapels short of shelter, the second a viewing wing's new shelter out of line. Measured on the twelve such specs before this was written: every volume outside those rooms is the
same after as before. A spec none of whose civic rooms still holds a piece only the old recipe stood (`OLD_STEMS`) is
already migrated and is not touched.

    python migrations/migrate_civic_rooms.py            # write specs/
    python migrations/migrate_civic_rooms.py --check    # report only
"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402
import migrate_seed_corridor  # noqa: E402
import migrate_seed_lines  # noqa: E402
import migrate_shelter  # noqa: E402
import migrate_wall_crossing  # noqa: E402

CIVIC = ("chapel", "courtroom", "assembly", "gallery")


def civic_rooms(d):
    return [r for r in d.get("rooms") or [] if level_design._room_kind(r, d.get("name")) in CIVIC]


#: What only the old `hall` recipe stood in these rooms: a room still holding one is not yet migrated.
OLD_STEMS = ("vending_", "table_dining_", "chair_waiting_", "cigarettes_", "litter_bin_")


def migrated(d, rooms):
    """Is every civic room clear of what the dining hall's recipe stood? Asked of the old pieces, not the new: a
    first version asked whether a room stood a pew or a case, and a gallery too small to hold either
    (landmark_hall_a01's 7.5 x 7.8 m artifact room) was refurnished on every run."""
    for r in rooms:
        tag = "_%s_" % level_design._room_tag(r)
        for v in d.get("volumes") or []:
            name = str(v.get("name", ""))
            if tag in name and name.startswith(OLD_STEMS):
                return False
    return True


def main():
    check = "--check" in sys.argv
    done = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        rooms = civic_rooms(d)
        if not rooms or migrated(d, rooms):
            continue
        done += 1
        if not check:
            migrate_furnish_recipes.migrate(d)
            migrate_shelter.migrate(d)
            migrate_seed_corridor.migrate(d)
            migrate_seed_lines.migrate(d)
            migrate_wall_crossing.migrate(d)
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("[civic_rooms] %d spec(s) refurnished%s" % (done, " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
