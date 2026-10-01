"""Every sign over a door names its business (0.165.0).

Cold run 9120's FLAPPHAS walk: the lit box over the gas station's door was
blank, and so was every derived sign in the library -- Zoo painted a face
only from a sign pack, and no theme ships one. Zoo 1.37.0 paints the name
from the anchor's `business`; this holds that every sign anchor the library
builds carries it, and that it is the identity a club's neon is keyed on, so
the door and the neon name the same club.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design  # noqa: E402
import lights  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def test_every_library_sign_names_the_building_it_is_on():
    seen = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        with open(p, encoding="utf-8") as f:
            spec = json.load(f)
        lp = os.path.join(HERE, "build", spec["name"] + ".lights.json")
        if not os.path.exists(lp):
            continue
        with open(lp, encoding="utf-8") as f:
            man = json.load(f)
        for a in man["anchors"]:
            if a["type"] == "sign":
                seen += 1
                assert a.get("business") == level_design.club_building_id(spec), (spec["name"], a)
    assert seen >= 100, seen


def test_the_stamp_reaches_authored_signs_and_keeps_their_own():
    rooms = [{"id": "shop", "story": 0, "bounds": [0, 0, 8, 6]}]
    openings = [{"kind": "door", "wall": "ext_0_S", "x": 4.0, "y": 0.0, "width": 1.2,
                 "height": 2.2, "sill": 0.0},
                {"kind": "window", "wall": "ext_0_S", "x": 1.5, "y": 0.0, "width": 1.6,
                 "height": 1.2, "z": 1.5}]
    authored = [{"id": "own_sign", "type": "sign", "pos": [1, 1, 3], "rot_y": 0.0,
                 "size": [2.0, 0.6], "business": "somebody_else"},
                {"id": "plain_sign", "type": "sign", "pos": [5, 1, 3], "rot_y": 0.0,
                 "size": [2.0, 0.6]}]
    man = lights.build_light_manifest("t", rooms, openings, 3.5, cap_thick=0.3, wall_thick=0.3,
                                      authored=authored, business="corner_deli")
    by = {a["id"]: a for a in man["anchors"] if a["type"] == "sign"}
    assert by["own_sign"]["business"] == "somebody_else"
    assert by["plain_sign"]["business"] == "corner_deli"
    derived = [a for a in by.values() if a.get("source") == "derived"]
    assert derived and all(a["business"] == "corner_deli" for a in derived)
    # and without a business nothing is stamped (the call sites that pass none)
    bare = lights.build_light_manifest("t", rooms, openings, 3.5, cap_thick=0.3, wall_thick=0.3)
    assert not any("business" in a for a in bare["anchors"])
