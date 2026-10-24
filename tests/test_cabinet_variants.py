"""Two video poker cabinets in one room are two different machines (0.231.1, the factory's roadmap 196).

A fixture's variant is its name's crc32 modulo the species' count, so two cabinets in one room can draw the same
machine: cold run 9326 showed deli_a01's customer floor with one machine twice, and the library held six such
rooms, all delis. The cabinet is now `distinct`, which moves a variant off the one its room already shows and never
moves a placement. This reads the library as it is.

Run: python -m pytest -q tests/test_cabinet_variants.py
"""
import collections
import glob
import json
import re
from pathlib import Path

import level_design as L

HERE = Path(__file__).resolve().parent.parent
KEY = "video_poker_store"
NAME = re.compile(r"^%s_(r[0-9a-f]{8})_\d+$" % KEY)


def test_no_room_holds_one_machine_twice():
    clashes = []
    for path in sorted(glob.glob(str(HERE / "specs" / "*.json"))):
        if Path(path).name.startswith("lf_"):
            continue
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
        by_room = collections.defaultdict(list)
        for v in spec.get("volumes") or []:
            m = NAME.match(str(v.get("name", "")))
            if m:
                by_room[m.group(1)].append(int(v.get("variant", 0) or 0))
        clashes += [(Path(path).name, tag, vs) for tag, vs in by_room.items() if len(set(vs)) < len(vs)]
    assert clashes == []


def test_the_cabinet_is_distinct():
    assert L._PIECES[KEY]["distinct"] is True
