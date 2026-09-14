#!/usr/bin/env python3
"""
migrate_club_rooms.py  --  the strip clubs are furnished as strip clubs
=======================================================================
One-shot, idempotent, over the `strip_club_*` specs in specs/. Their
hand-authored `stage` (8 x 4 x 0.8, 7 x 3.5 x 0.8) and `bar_run` volumes
routed to no species and shipped as grey boxes; 0.132.0's `strip_club`
recipe places a stage authored to the ceiling and a bar of its own, so the
authored pair is REMOVED (recorded here, by name), the furnished volumes are
stripped and the rooms refurnished (`migrate_furnish_recipes.migrate`), and
`level_design.dress_club_rooms` sets the surfaces. Every other spec is
`migrate_furnish_recipes.py`'s business, run after this for the same release
(leather booths, vending variants).

    python migrate_club_rooms.py            # write specs/
    python migrate_club_rooms.py --check    # report only
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402
import migrate_furnish_recipes as mig  # noqa: E402

#: The authored volumes the recipe replaces, per spec. Named, not matched:
#: an authored volume is removed only when this table says so.
AUTHORED_REPLACED = {
    "strip_club_a01": ("stage", "bar_run"),
    "strip_club_a02": (),
    "strip_club_a03": ("stage",),
}


def migrate(d):
    """(authored removed, furnished removed, added, fields dressed)."""
    gone = AUTHORED_REPLACED.get(d.get("name"), ())
    before = len(d.get("volumes") or [])
    d["volumes"] = [v for v in d.get("volumes") or [] if v["name"] not in gone]
    removed_authored = before - len(d["volumes"])
    removed, added = mig.migrate(d)          # runs furnish -> dress_club_rooms
    dressed = level_design.dress_club_rooms(d)   # idempotent: 0 after furnish
    return removed_authored, removed, added, dressed


def main():
    check = "--check" in sys.argv
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "strip_club_*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        if not level_design._strip_club_building(d.get("name")):
            continue
        before = json.dumps(d, sort_keys=True)
        ra, r, a, dressed = migrate(d)
        print(f"[club_rooms] {d['name']}: -{ra} authored, -{r} furnished, "
              f"+{a} refurnished, {dressed} field(s) dressed after furnish")
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")


if __name__ == "__main__":
    main()
