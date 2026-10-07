"""migrate_seed_corridor.py  --  every seeded piece leaves a body's width (0.195.0)
===================================================================================
One-shot, idempotent migration over the library, specs/*.json, Level
Factory's lf_ specs excepted as `layout_lint --all` excepts them. The seeder's
rule now asks that a piece standing on the floor leave `min_corridor_width`
(1.1 m) to every wall, stair reserve and standing volume
(`level_design._seed_clear`, `corridor`). Measured before this shipped: 40 of
the library's 69 seeded pieces did not, among them the two crate stacks that
cut deli_a01's up-stair off from its stairwell's door.

ASKED AS THE SEEDER ASKS IT, BEFORE FURNISH. Cover is placed first and
furniture after (`level_design.enrich`, "the order is load-bearing"), so each
spec is read without the volumes furnish wrote. A failing piece goes to the
nearest place the rule allows (`level_design.reseat_piece(..., corridor=True)`)
or, when nothing within reach answers, is DROPPED and named: a room where
nothing fits keeps its finding rather than a crate jammed into a passage,
which is `seed_cover`'s own rule. Then furnish runs again
(`migrate_furnish_recipes.migrate`), so every spec stays a fixed point of it.
A pass repeats until nothing fails, because one piece's move can free or
crowd another's place (seeded pieces stand 2.2 m apart).

    python migrate_seed_corridor.py            # write specs/
    python migrate_seed_corridor.py --check    # report only
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint               # noqa: E402
import level_design              # noqa: E402
import migrate_furnish_recipes   # noqa: E402


def _view(d):
    """The spec as the seeder sees it: without the volumes furnish wrote.
    The volume dicts are the spec's own, so a move made here is made there."""
    tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
    vols = [v for v in d.get("volumes") or []
            if not migrate_furnish_recipes.furnished_by_this_pass(v, tags)]
    return dict(d, volumes=vols)


def failing(d):
    """Names of the seed_cover pieces the corridor rule refuses where they stand."""
    view = _view(d)
    vols = view["volumes"]
    bad = []
    for v in vols:
        story = layout_lint.piece_story(view, v)
        if story is None:
            continue
        room = level_design._room_for_point(view, float(v["x"]), float(v["y"]), story)
        if not level_design._seeded_cover(v, room):
            continue
        without = dict(view, volumes=[o for o in vols if o is not v])
        placed = [(float(o["x"]), float(o["y"])) for o in vols
                  if o is not v and level_design._seeded_cover(o, room)]
        half = max(float(v["size_x"]), float(v["size_y"])) / 2.0
        if not level_design._seed_clear(without, room, float(v["x"]), float(v["y"]),
                                        placed, half=half, corridor=True):
            bad.append(v["name"])
    return sorted(bad)


def migrate(d, passes=4):
    """Move or drop every failing seeded piece, then refurnish, in place.
    Returns ([(name, (dx, dy))], [dropped names], [still failing])."""
    moved, dropped = [], []
    for _ in range(passes):
        bad = failing(d)
        if not bad:
            break
        view = _view(d)
        for name in bad:
            r = level_design.reseat_piece(view, name, corridor=True)
            if r is None:
                view["volumes"] = [v for v in view["volumes"] if v.get("name") != name]
                d["volumes"] = [v for v in d["volumes"] if v.get("name") != name]
                dropped.append(name)
            elif r != (0.0, 0.0):
                moved.append((name, r))
    if moved or dropped:
        migrate_furnish_recipes.migrate(d)
    return moved, dropped, failing(d)


def main():
    check = "--check" in sys.argv
    n_moved = n_dropped = n_specs = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        if not d.get("rooms"):
            continue
        before = json.dumps(d, sort_keys=True)
        moved, dropped, left = migrate(d)
        if not moved and not dropped and not left:
            continue
        n_specs += 1
        print("%-36s moved %d, dropped %d%s" % (
            os.path.basename(p)[:-len(".json")], len(moved), len(dropped),
            ("; STILL FAILING %s" % left) if left else ""))
        for name, (dx, dy) in moved:
            print("    moved    %-40s %+6.2f %+6.2f" % (name, dx, dy))
        for name in dropped:
            print("    DROPPED  %s (nothing within reach answers)" % name)
        n_moved += len(moved)
        n_dropped += len(dropped)
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    print("%d spec(s): %d moved, %d dropped%s" % (
        n_specs, n_moved, n_dropped, " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
