#!/usr/bin/env python3
"""
migrate_ticket_queue.py  --  give every box office and teller line its queue
============================================================================
One-shot, idempotent migration over specs/*.json for the factory's roadmap 267
and 275 (the walker, 2026-10-20: "queue lanes to the box office", in
retractable-belt stanchions, "more common for banks and indoor common areas").
`ticket_queue.lay_queues` does the work and `enrich` runs it for every preset,
before cover and furniture; this gives the specs already in the library the
same answer, in the same order: the queue is fitted with the spec's FURNISHED
pieces set aside (`migrate_furnish_recipes.furnished_by_this_pass`, and the
patrol points furnish writes), carried into the spec, and the spec refurnished
(`migrate_furnish_recipes.migrate`), so furniture stands round the queue as it
does in a generated building and the library stays a fixed point of furnish.
A spec the rule lays nothing in is not touched. `lf_*` specs are Level
Factory's per-run transients and are skipped.

0.243.0 fitted arena_a02's queue round its furniture instead and refurnished
after; set aside, its furniture constrained nothing the queue's own limits did
not, and the queue is the same either way (the factory's
`patches/dc_teller_queue/arena_either_way.out.txt`).

    python migrations/migrate_ticket_queue.py            # write specs/
    python migrations/migrate_ticket_queue.py --check    # report only
    python migrations/migrate_ticket_queue.py --dir D    # another spec directory
"""
import copy
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import level_design  # noqa: E402
import migrate_furnish_recipes  # noqa: E402
import ticket_queue  # noqa: E402


def migrate(d):
    """Lay `d`'s queues as a generated building would have them, in place: ``[report]``."""
    tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
    bare = copy.deepcopy(d)
    bare["volumes"] = [v for v in bare.get("volumes") or []
                       if not migrate_furnish_recipes.furnished_by_this_pass(v, tags)]
    if bare.get("markers"):
        bare["markers"] = [m for m in bare["markers"]
                           if not migrate_furnish_recipes.marker_written_by_this_pass(m, tags)]
    report = ticket_queue.lay_queues(bare)
    if not any(r["queued"] for r in report):
        return report
    have = {v.get("name") for v in d.get("volumes") or []}
    d.setdefault("volumes", []).extend(v for v in bare["volumes"] if v.get("name") not in have)
    d["partitions"] = bare.get("partitions", d.get("partitions"))
    d["materials"] = bare["materials"]
    migrate_furnish_recipes.migrate(d)
    return report


def main():
    check = "--check" in sys.argv
    root = os.path.join(HERE, "specs")
    if "--dir" in sys.argv:
        root = sys.argv[sys.argv.index("--dir") + 1]
    queued = left = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(p)
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        before = json.dumps(d, sort_keys=True)
        report = migrate(d)
        for r in report:
            print(f"  {name} {r['room']}: "
                  f"{'queued' if r['queued'] else 'left'} -- {r['why']}")
            queued += r["queued"]
            left += not r["queued"]
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    print(f"[ticket_queue] {queued} queue(s) "
          f"{'to lay' if check else 'laid'}, {left} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
