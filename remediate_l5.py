#!/usr/bin/env python3
r"""remediate_l5.py -- fix LAYOUT_RULES B1 violations in place.

Finds every PLAIN door that connects a public_entry room directly to an
objective room (layout_lint L5) and marks it reinforceable: the real-world
"staff only" steel door. Metadata-only: geometry is untouched; the flag flows
into the door's gameplay state machine on the next build.

    python remediate_l5.py            # dry run: list what would change
    python remediate_l5.py --write    # apply
"""
import glob
import json
import os
import sys

import layout_lint as LL

HERE = os.path.dirname(os.path.abspath(__file__))
WRITE = "--write" in sys.argv


def openings_between(spec, pub_ids, obj_ids):
    """yield (partition, opening) for plain doors linking a public room to an
    objective room, using the linter's own geometry model."""
    by_story = LL._rooms_by_story(spec)
    for part in spec.get("partitions", []):
        rooms = by_story.get(part.get("story", 0), [])
        for op in part.get("openings", []):
            if op.get("kind", "door") != "door" or op.get("reinforceable"):
                continue
            x, y = LL._opening_xy(spec, part, op, False)
            eps = 0.4
            pairs = []
            if part["axis"] == "X":
                pairs.append((LL._room_at(rooms, x, y - eps), LL._room_at(rooms, x, y + eps)))
                pairs.append((LL._room_at(rooms, y, x - eps), LL._room_at(rooms, y, x + eps)))
            else:
                pairs.append((LL._room_at(rooms, x - eps, y), LL._room_at(rooms, x + eps, y)))
                pairs.append((LL._room_at(rooms, y - eps, x), LL._room_at(rooms, y + eps, x)))
            for a, b in pairs:
                if not a or not b:
                    continue
                ids = {a["id"], b["id"]}
                if ids & pub_ids and ids & obj_ids:
                    yield part, op
                    break


def main():
    changed = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        spec = json.load(open(p))
        if spec.get("mode") != "pvp_heist":
            continue
        rooms = spec.get("rooms", [])
        pub = {r["id"] for r in rooms if r.get("role") == "public_entry"}
        obj = {r["id"] for r in rooms
               if r.get("objective") or r.get("role") == "objective_room"}
        if not pub or not obj:
            continue
        hits = list(openings_between(spec, pub, obj))
        if not hits:
            continue
        for part, op in hits:
            op["reinforceable"] = True
            if not op.get("tag"):
                op["tag"] = "secure_door"
        changed.append((os.path.basename(p), len(hits)))
        if WRITE:
            json.dump(spec, open(p, "w"), indent=1)
    for name, n in changed:
        print(f"{'FIXED' if WRITE else 'would fix'} {name}: {n} door(s) -> reinforceable")
    print(f"[remediate-l5] {len(changed)} specs, "
          f"{sum(n for _, n in changed)} doors {'written' if WRITE else '(dry run)'}")


if __name__ == "__main__":
    main()
