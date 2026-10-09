"""0.204.0 -- an indoor payphone asks for Zoo's `wall` form (roadmap 210).

Deli Counter stands payphones against walls -- an airport terminal's, a
funeral home's, a police station's (`level_design._piece("payphone", ...,
"wall")`) -- and asked for no form, so Zoo's `auto` built every one a booth
on a post, standing on the floor in front of the wall. Cold run 9212 shipped
two so. Zoo 1.88.0's `wall` form is the unit a lobby carries: no post, a line
conduit down the wall, a phone book on two rings under the shelf.

The piece asks for it; the refurnish (`migrate_furnish_recipes.py`, the L23
rule: a piece edit needs the library refurnished) writes it into every spec;
the build carries it into `slots.json`, which is the field Zoo's kit reads
(`kit.honour_dressing`). A field on a spec that never reached the slot would
be the knob with no effect this repo keeps finding, so the slots are held
too. On 0.203.0 the first three cases fail: the piece has no form, and the
39 payphones it placed in 38 specs, and their slots, ask for none.

THE PIECE'S PAYPHONES, NOT EVERY PAYPHONE. `primos_pizza` and
`strip_retail_a01` each carry one AUTHORED payphone, named plain `payphone`:
a 0.5 x 0.5 x 1.6 m slot standing 0.25 m off the dining room's back
partition, unrotated. The refurnish does not touch an authored volume, and a
wall unit there would hang a quarter of a metre off the wall, so those two
stay booths on their posts. Which payphones are the piece's is read off the
name the furnish pass writes (`migrate_furnish_recipes._GENERATED`).
"""
import glob
import json
import os
import re

import level_design

HERE = os.path.dirname(os.path.abspath(__file__))
#: Where the piece stands payphones today: 39 in 38 specs (0.204.0).
PAYPHONES = 39
#: A furnish-written payphone's name: the stem, the room's tag, a count.
PIECE_NAME = re.compile(r"^payphone_r[0-9a-f]{8}_\d+$")


def _spec_payphones():
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        for v in json.load(open(p, encoding="utf-8")).get("volumes") or []:
            if PIECE_NAME.match(str(v.get("name", ""))):
                out.append((os.path.basename(p), v))
    return out


def test_the_piece_asks_for_the_wall_form():
    p = level_design._PIECES["payphone"]
    assert p["where"] == "wall" and p["front"] is True
    assert p["form"] == "wall"


def test_every_payphone_in_the_library_asks_for_it():
    rows = _spec_payphones()
    assert len(rows) == PAYPHONES, len(rows)
    bad = [(f, v["name"], v.get("form")) for f, v in rows if v.get("form") != "wall"]
    assert not bad, bad[:5]


def test_the_form_reaches_the_slot_zoo_reads():
    rows = []
    for p in sorted(glob.glob(os.path.join(HERE, "build", "*.slots.json"))):
        for s in json.load(open(p, encoding="utf-8")).get("slots") or []:
            if s.get("species") == "payphone" and PIECE_NAME.match(str(s.get("slot_id", ""))):
                rows.append((os.path.basename(p), s))
    assert len(rows) == PAYPHONES, len(rows)
    bad = [(f, s["slot_id"], s.get("form")) for f, s in rows if s.get("form") != "wall"]
    assert not bad, bad[:5]


def test_nothing_else_the_piece_places_moved():
    """The form is dressing, not size: every payphone keeps the slot it had,
    so the refurnish moved nothing but the field (the 0.203.0 volumes' sizes,
    against the piece's one size)."""
    (size,) = level_design._PIECES["payphone"]["sizes"]
    for f, v in _spec_payphones():
        dims = sorted((v["size_x"], v["size_y"]))
        assert dims == sorted(size[:2]) and v["size_z"] == size[2], (f, v["name"], dims, v["size_z"])
