"""A piece that seats somebody stands with its chair (0.252.0, the factory's roadmap 284).

Measured on 0.251.0's library: 255 dining tables, 51 with no chair, because their recipe seats `randint(0, 4)` and
clearance refused the rest; 41 of 263 desks with no chair, though a desk seats one, because the desk stood whether or
not its chair cleared; 4 of 46 cocktail tables likewise. The walker's guide (`docs/reference/
Lived_In_Levels_Clear_Navigation_4P_PVE_1999_PA.md` at the factory root, section 8) builds a room's clusters from what
belongs together; a table with no chair is half of one.

A host the room left with no chair is seated LAST, when the room is furnished, so nothing else furnish drew in the room
moves: one chair from the host's own stream, tucked and then pushed in, kept off any route the room reserves; a host no
chair fits beside goes. Refuted first and kept (the factory's `patches/dc_table_chairs/`): such a host moved to its
next spot, with every host's chairs from its own stream and a dining table drawing one to four -- the library re-drawn,
routes over 10 % 28 -> 40 and three more closed to the bake.
"""
import copy
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SEATED = sorted(k for k, p in L._PIECES.items() if p.get("seats"))
HOST = re.compile(r"^(?P<key>%s)_(?P<tag>r[0-9a-f]{8})_(?P<seq>\d+)$" % "|".join(sorted(SEATED, key=len,
                                                                                        reverse=True)))
CHAIR = re.compile(r"^[a-z_]+?_(?P<tag>r[0-9a-f]{8})_(?P<seq>\d+)_\d+$")


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _must_seat(key):
    """A piece the room may not leave chairless: its seats ask one or more, or it says so (a dining table)."""
    p = L._PIECES[key]
    return bool(p.get("must_seat")) or p["seats"][1] >= 1


def test_a_dining_table_must_seat_one_and_its_draw_is_unchanged():
    """The dining table's draw stays none to four -- so a room's sequence is 0.251.0's to the draw -- and it may not
    stand with none."""
    assert L._PIECES["table_dining"]["seats"] == ("table", 0, 4)
    assert L._PIECES["table_dining"]["must_seat"] is True
    assert L._PIECES["table_count"]["must_seat"] is False


def test_every_piece_that_must_seat_somebody_stands_with_its_chair():
    """THE LIBRARY AS SHIPPED. Every dining table, desk, cocktail table, counter and machine the room may not leave
    chairless stands with one chair at least -- a chair grouped with its host by the host's number,
    `<seat>_<room tag>_<host number>_<j>`. A counting table, which may seat none, is not asked."""
    hosts, bare = 0, []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        found, chairs = {}, set()
        for v in d.get("volumes") or []:
            m = HOST.match(str(v.get("name") or ""))
            if m and _must_seat(m.group("key")):
                found[(m.group("tag"), m.group("seq"))] = v["name"]
            m = CHAIR.match(str(v.get("name") or ""))
            if m:
                chairs.add((m.group("tag"), m.group("seq")))
        hosts += len(found)
        bare += [(name, n) for k, n in found.items() if k not in chairs]
    assert hosts > 400, "the library stands %d pieces that must seat: the test asks nothing" % hosts
    assert not bare, bare[:20]


def test_seating_a_chairless_host_moves_nothing_the_room_drew(monkeypatch):
    """train_yard_a01, office and airport_terminal_a01, furnished from bare with the rescue and without it (`must_seat`
    off everywhere): the rescue seats hosts the rooms left chairless and takes away the hosts no chair fits beside, and
    every other piece stands where it stood. On 0.251.0 there is no rescue, and nothing differs."""
    rescued = 0
    for name in ("train_yard_a01", "office", "airport_terminal_a01"):
        d0 = L.unfurnished(_load(name))
        on = copy.deepcopy(d0)
        L.furnish(on)
        with monkeypatch.context() as m:
            for k in SEATED:
                m.setitem(L._PIECES[k], "must_seat", False)
            off = copy.deepcopy(d0)
            L.furnish(off)
        a = {v["name"]: (v["x"], v["y"]) for v in on["volumes"]}
        b = {v["name"]: (v["x"], v["y"]) for v in off["volumes"]}
        added = set(a) - set(b)
        gone = set(b) - set(a)
        assert all(CHAIR.match(n) for n in added), sorted(added)
        assert all(HOST.match(n) for n in gone), sorted(gone)
        assert all(a[n] == b[n] for n in set(a) & set(b)), name
        rescued += len(added) + len(gone)
    assert rescued, "no host was seated or taken away: the rescue did nothing"
