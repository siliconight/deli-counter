#!/usr/bin/env python3
"""
migrate_roller_grill.py  --  a convenience store has its roller grill
====================================================================
One-shot, idempotent migration over specs/*.json for Zoo 1.17.0's
`roller_grill`: the hot dog roller grill on its bun cabinet. The walker,
2026-09-28: "do the roller grill next". The proposal
(docs/proposals/GAS_STATION_SHOP.md): "a roller grill is a customer-facing
display case at the till".

MEASURED FIRST: no spec in the library carries a `roller`, `hot_dog` or
`hotdog` volume; the only `grill` volumes are kitchen grills, which route to
`flat_top_grill` and stay.

THE RULE IS THE SLUSH MACHINE'S (`migrate_slush_machine.plan_station`,
generalised in 0.152.0): every convenience store (a `sales_floor` with
`gondola_aisle` volumes), against a solid wall of the sales floor, clear of
openings, `island_aisle_width()` from every authored volume -- so clear of
the slush station too, which this runs after -- no marker within 0.5 m,
facing the room. Nearest the REGISTER COUNTER's QUEUE -- a point `AHEAD` in
front of its customer face -- the till the proposal puts it at. MEASURED:
anchored on the counter's CENTRE, five stores put the grill on the west wall
north of the counter, behind the till where the clerk stands. Refused and reported when nothing fits, never forced. Each store given
one is refurnished so the library stays a fixed point of furnishing.

    python migrate_roller_grill.py            # write specs/
    python migrate_roller_grill.py --check    # report only; exit 1 if any
    python migrate_roller_grill.py --dir D    # another spec directory
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import migrate_slush_machine as S  # noqa: E402

NAME = "roller_grill"
#: Zoo's `roller_grill_forms.DC_SIZES[0]`: three columns of dogs and a bun
#: shelf under the hood.
WIDTH, DEPTH, HEIGHT = 1.0, 0.6, 1.4
ANCHORS = ("register_counter",)
#: Where a customer stands at the till: 1.5 m in front of the counter's face.
AHEAD = 1.5


def plan_grill(spec):
    return S.plan_station(spec, NAME, (WIDTH, DEPTH, HEIGHT), ANCHORS, AHEAD)


def migrate(d):
    return S.migrate(d, NAME, (WIDTH, DEPTH, HEIGHT), ANCHORS, AHEAD)


def main(argv=None):
    return S.main(argv, NAME, (WIDTH, DEPTH, HEIGHT), ANCHORS, "a roller grill", AHEAD)


if __name__ == "__main__":
    sys.exit(main())
