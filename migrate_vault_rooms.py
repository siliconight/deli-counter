#!/usr/bin/env python3
"""
migrate_vault_rooms.py  --  a bank vault is a room behind a round door
=====================================================================
One-shot, idempotent migration over specs/*.json for the walker's "the bank
vault should absolutely be a hero piece" (walk 9052). `vault_room.enclose_vaults`
does the work and `level_design.enrich` runs it for every preset; this gives
the specs already in the library the same answer.

The library is already furnished, so the generator EVICTS the furniture and
cover it placed that stands on a new wall or in the door's swing (named in the
report), and this script then furnishes the new vault room alone -- every other
room keeps exactly what it had. `lf_*` specs are Level Factory's per-run
transients and are skipped.

    python migrate_vault_rooms.py            # write specs/
    python migrate_vault_rooms.py --check    # report only
    python migrate_vault_rooms.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402
import vault_room  # noqa: E402


def migrate(d):
    """Enclose every vault in one spec dict, in place, and furnish only the
    rooms it made. Returns (report, pieces_added)."""
    report = vault_room.enclose_vaults(d)
    made = {r["room"] for r in report if r["enclosed"]}
    added = 0
    if made:
        view = dict(d, rooms=[r for r in d.get("rooms") or []
                              if r.get("id") in made])
        view["volumes"] = d.setdefault("volumes", [])
        view["materials"] = d.setdefault("materials", [])
        added = level_design.furnish(view)
    return report, added


def main():
    check = "--check" in sys.argv
    root = os.path.join(HERE, "specs")
    if "--dir" in sys.argv:
        root = sys.argv[sys.argv.index("--dir") + 1]
    enclosed = left = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(p)
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        before = json.dumps(d, sort_keys=True)
        report, added = migrate(d)
        for r in report:
            print(f"  {name} {r['volume']}: "
                  f"{'enclosed' if r['enclosed'] else 'left'} -- {r['why']}")
            for m in r["moved"]:
                print(f"      moved {m}")
            for m in r["added"]:
                print(f"      added {m}")
            if r["evicted"]:
                print(f"      evicted {', '.join(r['evicted'])}")
            enclosed += r["enclosed"]
            left += not r["enclosed"]
        if added:
            print(f"      furnished the vault with {added} piece(s)")
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    print(f"[vault_rooms] {enclosed} vault(s) "
          f"{'to enclose' if check else 'enclosed'}, {left} left as volumes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
