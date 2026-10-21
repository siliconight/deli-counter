#!/usr/bin/env python3
"""
migrate_ticket_queue.py  --  give every box office its ticket window and queue
==============================================================================
One-shot, idempotent migration over specs/*.json for the factory's roadmap 267
(the walker, 2026-10-20: "queue lanes to the box office", in retractable-belt
stanchions). `ticket_queue.queue_box_offices` does the work and `enrich` now
runs it for every preset, before cover and furniture; this gives the specs
already in the library the same answer. A library spec is already furnished, so
the queue is fitted round what stands there: nothing inside it, a corridor
round every line. `lf_*` specs are Level Factory's per-run transients and are
skipped.

    python migrate_ticket_queue.py            # write specs/
    python migrate_ticket_queue.py --check    # report only
    python migrate_ticket_queue.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ticket_queue  # noqa: E402


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
        report = ticket_queue.queue_box_offices(d)
        for r in report:
            print(f"  {name} {r['room']}: "
                  f"{'queued' if r['queued'] else 'left'} -- {r['why']}")
            queued += r["queued"]
            left += not r["queued"]
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    print(f"[ticket_queue] {queued} box office(s) "
          f"{'to queue' if check else 'queued'}, {left} left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
