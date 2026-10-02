"""A home has a porch light over its door, not a lit sign (0.169.0).

Zoo 1.37.0 paints a name on every sign box and a building of no kind shows
its street number; on a home that is a lit cabinet over a front door. The
walker left the call here, 2026-10-02. Held: a residence derives no sign and
its front door takes a wall pack, in the same place a sign's door would have
gone without one; every other building is as it was; and the library's eight
homes built that way.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design  # noqa: E402
import lights  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

ROOMS = [{"id": "front_hall", "story": 0, "bounds": [0, 0, 8, 6]}]
OPENINGS = [{"kind": "door", "wall": "ext_0_S", "x": 4.0, "y": 0.0, "width": 1.2,
             "height": 2.2, "sill": 0.0},
            {"kind": "window", "wall": "ext_0_S", "x": 1.5, "y": 0.0, "width": 1.6,
             "height": 1.2, "z": 1.5}]


def _anchors(business):
    man = lights.build_light_manifest("t", ROOMS, OPENINGS, 3.5, cap_thick=0.3, wall_thick=0.3,
                                      business=business)
    return man["anchors"]


def test_the_words_are_whole_words():
    for b in ("apartment_walkup_a01", "rowhouse_raid", "twin_a01", "mansion_a03",
              "lf_block_7 apartment_walkup"):
        assert lights.is_residence(b), b
    for b in ("corner_deli", "gas_station_a02", "strip_club_a01 strip_club", "twinkle_bar",
              "courthouse_a01", "funeral_home_a01", None, ""):
        assert not lights.is_residence(b), b


def test_a_home_takes_a_wall_pack_where_a_shop_takes_a_sign():
    shop, home = _anchors("corner_deli"), _anchors("rowhouse_raid")
    assert [a["type"] for a in shop].count("sign") == 1
    assert [a["type"] for a in shop].count("wall_pack") == 0
    assert [a["type"] for a in home].count("sign") == 0
    packs = [a for a in home if a["type"] == "wall_pack"]
    assert len(packs) == 1 and packs[0]["wall"] == "ext_0_S"
    assert abs(packs[0]["pos"][0] - 4.0) < 1e-6           # over the same door
    # one anchor for one anchor, and nothing else moved
    assert len(home) == len(shop)
    rest = lambda a: [x for x in a if x["type"] not in ("sign", "wall_pack")]   # noqa: E731
    assert rest(home) == rest(shop)


def test_the_library_homes_have_no_sign_and_every_other_storefront_keeps_its_own():
    homes = signs = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        with open(p, encoding="utf-8") as f:
            spec = json.load(f)
        lp = os.path.join(HERE, "build", spec["name"] + ".lights.json")
        if not os.path.exists(lp):
            continue
        with open(lp, encoding="utf-8") as f:
            anchors = json.load(f)["anchors"]
        derived = [a for a in anchors if a["type"] == "sign" and a.get("source") == "derived"]
        if lights.is_residence(level_design.club_building_id(spec)):
            homes += 1
            assert derived == [], spec["name"]
            assert any(a["type"] == "wall_pack" for a in anchors), spec["name"]
        else:
            signs += len(derived)
    assert homes >= 8, homes
    assert signs >= 90, signs
