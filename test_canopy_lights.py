"""A fuel canopy's light anchors (pure -- no Blender).

Written 2026-09-26 after cold run 9080's package was measured: the forecourt
canopy was 22 x 13 m on six columns and every one of the 20 Lux fixture holders
within 45 m sat on the SHOP. The canopy volumes were authored and no light had
ever been derived from them.

Run:  python -m pytest test_canopy_lights.py
"""
import json
import os

import lights

#: `specs/gas_station.json` as authored: a 24 x 10 x 0.4 deck at z 5.0 on six
#: 5.0 m columns. Spelled here rather than loaded so a spec edit cannot
#: silently change what these tests claim to check.
DECK = {"name": "canopy_roof", "x": 0.0, "y": -18.0, "z": 5.0,
        "size_x": 24.0, "size_y": 10.0, "size_z": 0.4}
COLS = [{"name": "canopy_col_%d" % i, "x": x, "y": y, "z": 2.5,
         "size_x": 0.4, "size_y": 0.4, "size_z": 5.0}
        for i, (x, y) in enumerate(
            [(-10.0, -14.0), (0.0, -14.0), (10.0, -14.0),
             (-10.0, -22.0), (0.0, -22.0), (10.0, -22.0)], 1)]


def _anchors(volumes=None):
    return lights._canopy_anchors(volumes if volumes is not None
                                  else [DECK] + COLS)


def test_a_building_with_no_canopy_gets_no_canopy_anchors():
    """Every building that is not a fuel stop, which is most of them."""
    assert _anchors([]) == []
    assert _anchors([{"name": "wall_1", "x": 0, "y": 0, "z": 1.5,
                      "size_x": 4, "size_y": 0.3, "size_z": 3}]) == []


def test_the_deck_gets_exactly_one_hardware_anchor():
    """ONE anchor for the whole deck, because Zoo's `canopy_lights` lays the
    lamp grid inside it. One anchor per lamp would be two draw calls each."""
    hw = [a for a in _anchors() if a["type"] == "canopy_lights"]
    assert len(hw) == 1
    a = hw[0]
    assert a["size"] == [24.0, 10.0]          # the species' dimensions
    assert a["pos"][0] == 0.0 and a["pos"][1] == -18.0


def test_the_lit_face_hangs_below_the_soffit():
    """z = deck centre - half its thickness - the drop. A lit face flush with
    the deck it sits in is a coplanar pair, and this package already carries a
    PRESENTATION_ZFIGHT finding."""
    a = [x for x in _anchors() if x["type"] == "canopy_lights"][0]
    assert a["pos"][2] == round(5.0 - 0.2 - lights._CANOPY_DROP, 3) == 4.78
    assert lights._CANOPY_DROP > 0.0


def test_grade_comes_from_the_columns_and_not_from_zero():
    """A canopy's columns stand on the surface its light has to reach, so they
    are the one thing in the spec that knows where that surface is."""
    raised = [dict(c, z=3.0, size_z=5.0) for c in COLS]   # feet at +0.5
    a = [x for x in _anchors([DECK] + raised)
         if x["type"] == "canopy_lights"][0]
    assert a["drop"] == round(4.78 - 0.5, 3)
    # and the authored deck, whose columns stand at grade
    b = [x for x in _anchors() if x["type"] == "canopy_lights"][0]
    assert b["drop"] == 4.78


def test_a_canopy_with_no_columns_falls_back_to_grade_and_says_so():
    a = [x for x in _anchors([DECK]) if x["type"] == "canopy_lights"][0]
    assert a["drop"] == round(4.78 - lights._CANOPY_GRADE, 3)


def test_columns_of_another_canopy_do_not_set_this_one_s_grade():
    """Two fuel stops on one lot would otherwise share a floor."""
    far = [dict(c, x=c["x"] + 200.0, z=1.0, size_z=2.0) for c in COLS]
    a = [x for x in _anchors([DECK] + COLS + far)
         if x["type"] == "canopy_lights"][0]
    assert a["drop"] == 4.78


def test_the_washes_are_few_spread_and_inside_the_deck():
    """A few lights, not a grid: max_lights_per_object is 8 and every one of
    them would reach the forecourt ground mesh."""
    w = [a for a in _anchors() if a["type"] == "canopy_wash"]
    assert 2 <= len(w) <= lights._CANOPY_WASH_MAX
    xs = [a["pos"][0] for a in w]
    assert xs == sorted(xs)
    assert min(xs) > DECK["x"] - DECK["size_x"] / 2.0
    assert max(xs) < DECK["x"] + DECK["size_x"] / 2.0
    assert abs(min(xs) + max(xs)) < 1e-9          # symmetric about the deck
    for a in w:
        assert a["pos"][2] == 4.78                # at the soffit
        assert a["drop"] == 4.78


def test_the_washes_run_along_the_LONG_axis():
    """A deck twice as deep as it is wide should light down its length."""
    tall = dict(DECK, size_x=10.0, size_y=24.0)
    w = [a for a in _anchors([tall] + COLS) if a["type"] == "canopy_wash"]
    ys = [a["pos"][1] for a in w]
    assert len(set(a["pos"][0] for a in w)) == 1   # all on one x
    assert len(set(ys)) == len(w)                  # spread on y


def test_the_wash_count_rises_with_the_deck_and_stops():
    counts = []
    for sx in (6.0, 12.0, 24.0, 40.0, 80.0):
        deck = dict(DECK, size_x=sx)
        counts.append(len([a for a in _anchors([deck] + COLS)
                           if a["type"] == "canopy_wash"]))
    assert counts == sorted(counts)
    assert max(counts) <= lights._CANOPY_WASH_MAX
    assert min(counts) >= lights._CANOPY_WASH_BASE


def test_the_manifest_version_moved():
    """New anchor types are a schema change; a reader has to be able to tell."""
    assert lights.LIGHT_MANIFEST_VERSION == "1.3.0"


def test_the_authored_spec_still_produces_them():
    """The one test that reads the real spec: if `canopy_roof` is renamed or
    dropped, this fails rather than the forecourt going quietly dark."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "specs", "gas_station.json")
    spec = json.load(open(path, encoding="utf-8"))
    out = lights._canopy_anchors(spec.get("volumes") or [])
    kinds = [a["type"] for a in out]
    assert kinds.count("canopy_lights") == 1, kinds
    assert kinds.count("canopy_wash") >= 2, kinds
