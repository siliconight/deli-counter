#!/usr/bin/env python3
"""
migrate_den_drapes.py  --  a den's windows are drawn shut
==========================================================
One-shot, idempotent migration over specs/*.json for Deli Counter 0.205.0:
every window of a strip club hangs Zoo's `window_drape` (>= 1.91.0) on its
room side, by `level_design.plan_den_drapes` -- the rule `furnish` runs on a
generated spec, applied to the authored ones, whose furnishing is baked in.

The walker, 2026-10-09, walking club_block_014 (roadmap 219, note 2): "the
windows in any 'den of sin' building should have curtains or drapes or
blinds So people outside can't see in, and you keep the streetlight light
out of the club".

A drape already there is replaced by the rule's; one the rule no longer asks
for is removed; a new one goes in before the pieces `furnish` wrote, the
window poster's reason (`migrate_window_poster`): a refurnish keeps every
other volume in order and appends its own.

    python migrate_den_drapes.py            # write specs/
    python migrate_den_drapes.py --check    # report only; exit 1 if any
    python migrate_den_drapes.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402


def migrate(d):
    """``changed`` for one spec dict, in place."""
    want = level_design.plan_den_drapes(d)
    vols = d.get("volumes") or []
    names = {v["name"] for v in want}
    keep = [v for v in vols if not (str(v.get("name", "")).startswith(level_design.DRAPE_NAME)
                                    and v.get("name") not in names)]
    changed = len(keep) != len(vols)
    at_name = {v.get("name"): i for i, v in enumerate(keep)}
    tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
    at = max((i + 1 for i, v in enumerate(keep)
              if not migrate_furnish_recipes.furnished_by_this_pass(v, tags)), default=0)
    for v in want:
        i = at_name.get(v["name"])
        if i is None:
            keep.insert(at, v)
            at += 1
            changed = True
        elif keep[i] != v:
            keep[i] = v
            changed = True
    if want:
        had = len(d.get("materials") or [])
        level_design._declare_material(d, *level_design.DRAPE_MATERIAL)
        changed = changed or len(d.get("materials") or []) != had
    if changed:
        d["volumes"] = keep
    return changed


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    n = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not migrate(d):
            continue
        n += 1
        got = [v for v in d.get("volumes") or [] if str(v.get("name", "")).startswith(level_design.DRAPE_NAME)]
        print(f"[den_drapes] {os.path.basename(p)}: {len(got)} drape(s): "
              + ", ".join(f"{v['name']} at ({v['x']}, {v['y']}, {v['z']}) "
                          f"{v['size_x']} x {v['size_y']} x {v['size_z']}" for v in got))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, indent=1) + "\n")
    print(f"[den_drapes] {n} spec(s) {'need' if check else 'given'} their drapes")
    return 1 if check and n else 0


if __name__ == "__main__":
    sys.exit(main())
