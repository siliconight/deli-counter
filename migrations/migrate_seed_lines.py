"""
migrate_seed_lines.py  --  a room's seeded pieces stand in one line (0.264.0)
=============================================================================
One-shot, idempotent migration over the library, specs/*.json, Level
Factory's lf_ specs excepted as `layout_lint --all` excepts them. The seeder
now lays a room's pieces in one line (`level_design._line_up`); this lays the
ones the library already stores the same way. The walker, walking cold run
9383, of deli_a03's stair landing: "layout of these tables doesn't seem to
have a rhyme or reason".

ONLY WHAT IS STORED, NEVER A RE-SEED. Replayed on the library, today's
`seed_cover` gives back its stored pieces in 7 of 128 specs and places 1,419
pieces where 75 are stored -- the rules for whether a room is seeded moved
after these specs were seeded. Re-seeding would change the cover of nearly
every room in the library; this changes where the stored pieces stand and
nothing else: the same pieces, kinds, heights and rooms.

ASKED AS THE SEEDER ASKS IT, BEFORE FURNISH (`migrate_seed_corridor`'s rule):
each spec is read without the volumes furnish wrote, and refurnished after
(`migrate_furnish_recipes.migrate`) when anything moved, so it stays a fixed
point of furnish. A room no line fits keeps its pieces, and is named.

    python migrations/migrate_seed_lines.py            # write specs/
    python migrations/migrate_seed_lines.py --check    # report only
"""
import collections
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import layout_lint               # noqa: E402
import level_design              # noqa: E402
import migrate_furnish_recipes   # noqa: E402
import migrate_seed_corridor     # noqa: E402


def _order(v):
    """The seeder's order: its shelter piece first, then by the index it drew."""
    name = v["name"]
    return -1 if name.endswith("_shelter") else int(name.rsplit("_", 1)[1])


def rooms_seeded(view):
    """``[(room, [pieces in the seeder's order])]`` for every room storing a seeded piece: a lone one
    stands on the room's line too (0.264.0)."""
    by_room = collections.OrderedDict()
    for v in view.get("volumes") or []:
        story = layout_lint.piece_story(view, v)
        if story is None:
            continue
        room = level_design._room_for_point(view, float(v["x"]), float(v["y"]), story)
        if level_design._seeded_cover(v, room):
            by_room.setdefault(room["id"], (room, []))[1].append(v)
    return [(room, sorted(vs, key=_order)) for room, vs in by_room.values()]


def migrate(d):
    """Line up every room's stored seeded pieces, then refurnish, in place.
    Returns ([lined room ids], [room ids no line fits])."""
    view = migrate_seed_corridor._view(d)
    building = level_design.club_building_id(d)
    lined, kept = [], []
    for room, pieces in rooms_seeded(view):
        before = [(v["x"], v["y"], v["size_x"], v["size_y"]) for v in pieces]
        # THE ROUTES THE ROOM HAS WITHOUT THESE PIECES (0.264.0), as `seed_cover`
        # asks them before it stands any: asked with them standing, the routes
        # bent round where they stood, and this migration's first draft lined
        # pawn_shop_a01's two crates onto the safe room's true route
        ids = {id(v) for v in pieces}
        bare = dict(view, volumes=[v for v in view["volumes"] if id(v) not in ids])
        routes = (level_design.protected_routes(level_design.unfurnished(bare), room)
                  if level_design.reserves_routes(view, room, building) else [])
        if not level_design._line_up(view, room, pieces, routes):
            kept.append(room["id"])
        elif [(v["x"], v["y"], v["size_x"], v["size_y"]) for v in pieces] != before:
            lined.append(room["id"])
    if lined:
        migrate_furnish_recipes.migrate(d)
    return lined, kept


def main():
    check = "--check" in sys.argv
    n_lined = n_kept = n_specs = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        if not d.get("rooms"):
            continue
        before = json.dumps(d, sort_keys=True)
        lined, kept = migrate(d)
        if not lined and not kept:
            continue
        n_specs += 1
        print("%-36s lined %s%s" % (os.path.basename(p)[:-len(".json")], ", ".join(lined) or "-",
                                    ("; NO LINE FITS, KEPT: %s" % ", ".join(kept)) if kept else ""))
        n_lined += len(lined)
        n_kept += len(kept)
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print("%d spec(s): %d room(s) lined, %d kept%s" % (
        n_specs, n_lined, n_kept, " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
