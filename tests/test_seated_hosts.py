"""A piece that seats somebody stands with its chair (0.252.0, the factory's roadmap 284), moved to where its chair fits
rather than taken away (0.256.0).

Measured on 0.251.0's library: 255 dining tables, 51 with no chair, because their recipe seats `randint(0, 4)` and
clearance refused the rest; 41 of 263 desks with no chair, though a desk seats one, because the desk stood whether or
not its chair cleared; 4 of 46 cocktail tables likewise. The walker's guide (`docs/reference/
Lived_In_Levels_Clear_Navigation_4P_PVE_1999_PA.md` at the factory root, section 8) builds a room's clusters from what
belongs together; a table with no chair is half of one.

A host the room left with no chair is seated LAST, when the room is furnished, so nothing else furnish drew in the room
moves: one chair from the host's own stream, tucked and then pushed in, kept off any route the room reserves. A host no
chair fits beside moves to the nearest spot where one does, it and its chair off the room's routes (0.256.0; the
walker, of 0.252.0 taking away 24 desks and a dining table: a desk with no room for its chair is moved, not removed).
Refuted first and kept (the factory's `patches/dc_table_chairs/`): such a host moved to its next spot WHEN IT WAS
PLACED, with every host's chairs from its own stream and a dining table drawing one to four -- the library re-drawn,
routes over 10 % 28 -> 40 and three more closed to the bake.
"""
import copy
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import level_design as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    off everywhere): the rescue seats hosts the rooms left chairless, moves or takes away the hosts no chair fits beside
    -- only those, each chairless without the rescue -- and every other piece stands where it stood. On 0.251.0 there
    is no rescue, and nothing differs."""
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
        moved = {n for n in set(a) & set(b) if a[n] != b[n]}
        seated_off = {(cm.group("tag"), cm.group("seq")) for n in b for cm in [CHAIR.match(n)] if cm}
        assert all(CHAIR.match(n) for n in added), sorted(added)
        assert all(HOST.match(n) for n in gone | moved), sorted(gone | moved)
        assert not [n for n in moved if (HOST.match(n).group("tag"), HOST.match(n).group("seq")) in seated_off], name
        rescued += len(added) + len(gone) + len(moved)
    assert rescued, "no host was seated, moved or taken away: the rescue did nothing"


def test_a_host_no_chair_fits_beside_is_moved_where_one_does(monkeypatch):
    """THE WALKER, 2026-10-21, of a desk with no room for its chair: moved, not removed. 0.252.0 took a desk away from
    office's exec_suite and one from landmark_hall_a01's curator_band. Furnished from bare, each host the rescue moves
    stands in its own room with its chair, both off the room's routes (`protected_routes`, asked of the room
    unfurnished; a centimetre each side for the record's rounding), and takes no width from any two of the room's route
    endpoints that it leaves under two abreast (`room_necks`, the room with and without the host and its chair). On
    0.255.0 no host moves."""
    moved = 0
    two = L.two_abreast_width() / 2.0
    for name in ("office", "landmark_hall_a01"):
        d0 = L.unfurnished(_load(name))
        on = copy.deepcopy(d0)
        L.furnish(on)
        with monkeypatch.context() as m:
            for k in SEATED:
                m.setitem(L._PIECES[k], "must_seat", False)
            off = copy.deepcopy(d0)
            L.furnish(off)
        hosts_off = {v["name"]: v for v in off["volumes"] if HOST.match(str(v.get("name") or ""))}
        rooms = {L._room_tag(r): r for r in on["rooms"]}
        for v in list(on["volumes"]):
            n = str(v.get("name") or "")
            g = HOST.match(n)
            w = hosts_off.get(n)
            if not g or w is None or (v["x"], v["y"]) == (w["x"], w["y"]):
                continue
            moved += 1
            room = rooms[g.group("tag")]
            x0, y0, x1, y1 = room["bounds"]
            assert x0 < v["x"] < x1 and y0 < v["y"] < y1, n
            seats = [c for c in on["volumes"] for cm in [CHAIR.match(str(c.get("name") or ""))]
                     if cm and (cm.group("tag"), cm.group("seq")) == (g.group("tag"), g.group("seq"))]
            assert seats, n
            ways = L.protected_routes(L.unfurnished(on), room)
            for p in [v] + seats:
                assert not L.on_protected_route(ways, p["x"], p["y"], p["size_x"] - 0.02, p["size_y"] - 0.02), \
                    p["name"]
            without = dict(on, volumes=[c for c in on["volumes"] if c is not v and not any(c is s for s in seats)])
            before, after = L.room_necks(without, room), L.room_necks(on, room)
            assert before, n
            for q, b in before.items():
                assert q in after and not (after[q] < b - 1e-9 and after[q] < two), (n, q, b, after.get(q))
    assert moved == 2, moved
