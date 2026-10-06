#!/usr/bin/env python3
"""
migrate_stale_pieces.py  --  move every piece that stands where a stair is
==========================================================================
One-shot, idempotent migration over specs/*.json for `layout_lint` L23 (a
piece over a slab opening or in a stair's walk on its own storey). Every
placement pass clears a piece of the stairs when it places it and is
idempotent by name, so a piece placed before a stair lengthened or widened is
never asked again; this asks once, now.

Each piece is moved by `level_design.reseat_piece`: the nearest place in its
room, clear of the stairs and the other pieces, out of any door's approach
it was not already in, and -- for a piece `seed_cover` placed -- only where
the seeder would put one. Pieces frozen in `stale_pieces_baseline.json` are
left alone: each needs a look before it moves. `lf_*` specs are Level
Factory's per-run transients and are skipped.

THEN THE SPEC IS REFURNISHED, so it stays a fixed point of furnish
(`test_club_fixtures`). `furnish` lays a room's furniture around what already
stands in it, so moving deli_a01's counter islands changes where its upper
hall's counter, vending machine and chairs go: the first run of this, which
did not refurnish, failed that test on deli_a01. A piece the refurnish
itself leaves over an opening is reported.

    python migrate_stale_pieces.py                # write specs/
    python migrate_stale_pieces.py --check        # report only; exit 1 on any to move
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint   # noqa: E402
import level_design  # noqa: E402
import migrate_club_rooms        # noqa: E402
import migrate_furnish_recipes   # noqa: E402


def main():
    check = "--check" in sys.argv
    frozen = json.load(open(os.path.join(HERE, "stale_pieces_baseline.json"),
                            encoding="utf-8"))["stale_pieces"]
    moved, unresolved = [], []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-len(".json")]
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        todo = [x["name"] for x in layout_lint.stale_pieces(d)
                if x["name"] not in frozen.get(name, [])]
        if not todo:
            continue
        if check:
            moved += [(name, n, None) for n in todo]
            continue
        changed = False
        for n in todo:
            r = level_design.reseat_piece(d, n)
            if r is None:
                unresolved.append((name, n))
            elif r != (0.0, 0.0):
                moved.append((name, n, r))
                changed = True
        if changed:
            if d.get("rooms"):
                (migrate_club_rooms.migrate if name.startswith("strip_club_")
                 else migrate_furnish_recipes.migrate)(d)
            left = [x["name"] for x in layout_lint.stale_pieces(d)
                    if x["name"] not in frozen.get(name, [])]
            unresolved += [(name, n + " (after the refurnish)") for n in left]
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    for name, n, r in moved:
        print(f"  {name} {n}: " + ("to move" if r is None else
                                   f"x {r[0]:+g} m, y {r[1]:+g} m"))
    for name, n in unresolved:
        print(f"  {name} {n}: NO PLACE within reach -- left where it was")
    print(f"[stale_pieces] {len(moved)} piece(s) "
          f"{'to move' if check else 'moved'}, {len(unresolved)} unresolved")
    return 1 if (check and moved) or unresolved else 0


if __name__ == "__main__":
    sys.exit(main())
