"""0.278.0 -- a supermarket's shelves sell what the markers over them say.

The walker's grocery comps (the factory's docs/reference/GROCERY_STORE_COMPS.md); in the walker's level the
supermarket's gondolas sold the convenience store's chips under markers that said CEREAL and CANNED VEG. Zoo 1.133.0's
`snack_gondola` form `grocery` sells, on each face, one of the 24 categories the markers print: face -Y of the
gondola on line v the second category of lane v - 1, face +Y the first of lane v (`grocery_faces`). So furnish makes
every gondola of a supermarket's floor that form, the variant of its line, its module's +Y toward the higher lane
(`stock_supermarket_gondolas`). Lane j's marker is variant j: its two categories are then the +Y face of line j and the
-Y face of line j + 1.

FAILS ON 0.277.0: `stock_supermarket_gondolas` and `_gondola_lines` do not exist, and the library's gondolas are the
snack form.
"""
import copy
import glob
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import level_design as L  # noqa: E402


def _supermarkets():
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        b = L.club_building_id(d)
        for r in d.get("rooms") or []:
            if L.is_supermarket_floor(r, b):
                out.append((os.path.basename(p), d, r))
    return out


def test_the_library_has_supermarkets_to_hold():
    names = {n for n, _d, _r in _supermarkets()}
    assert {"supermarket_a01.json", "supermarket_a02.json", "supermarket_a03.json"} <= names


def test_every_gondola_is_the_grocery_form_of_its_line_turned_to_the_lane_after():
    for name, d, r in _supermarkets():
        along_y, lines = L._gondola_lines(d, r)
        assert len(lines) >= 2, name
        want = 90.0 if along_y else 0.0
        for n, line in enumerate(lines):
            for v in line["vols"]:
                assert v.get("form") == "grocery", (name, v["name"])
                assert int(v.get("variant", 0) or 0) == n % L._GROCERY_LINES, (name, v["name"], n)
                assert abs(L._plus_y_plan(v) - want) < 1e-6, (name, v["name"], L._plus_y_plan(v))


def test_a_lanes_marker_and_the_faces_either_side_of_it_agree():
    """Lane j between line j and line j + 1: its marker is variant j, the +Y face of line j sells its first
    category and the -Y face of line j + 1 its second -- variants j and j + 1. Every lane of the library takes a
    marker, which that pairing needs (a skipped lane would renumber the markers after it)."""
    for name, d, r in _supermarkets():
        _along, lines = L._gondola_lines(d, r)
        markers = L.aisle_markers(d, r)
        assert len(markers) == len(lines) - 1, (name, len(markers), len(lines))
        hung = sorted((v for v in d["volumes"] if str(v.get("name", "")).startswith("aisle_sign_")
                       and v.get("form") == "grocery"), key=lambda v: int(v.get("variant", 0) or 0))
        assert [int(v.get("variant", 0) or 0) for v in hung] == list(range(len(lines) - 1)), name
        for j in range(len(lines) - 1):
            lo = {int(v.get("variant", 0) or 0) for v in lines[j]["vols"]}
            hi = {int(v.get("variant", 0) or 0) for v in lines[j + 1]["vols"]}
            assert lo == {j} and hi == {j + 1}, (name, j, lo, hi)


def test_stocking_is_a_fixed_point_and_turns_a_backward_gondola():
    _name, d, r = next(s for s in _supermarkets() if s[0] == "supermarket_a02.json")
    d = copy.deepcopy(d)
    assert L.stock_supermarket_gondolas(d, r) == 0
    along_y, lines = L._gondola_lines(d, r)
    v = lines[1]["vols"][0]
    v["rot_z"] = (float(v.get("rot_z", 0.0) or 0.0) + 180.0) % 360.0
    v["variant"] = 7
    v.pop("form")
    assert L.stock_supermarket_gondolas(d, r) == 1
    assert v.get("form") == "grocery" and int(v.get("variant", 0) or 0) == 1
    assert abs(L._plus_y_plan(v) - (90.0 if along_y else 0.0)) < 1e-6
    assert L.stock_supermarket_gondolas(d, r) == 0


def test_the_slots_carry_the_form_and_the_line():
    """What Zoo is asked for: the slot records the volume's form and variant, and the turn that points +Y at the
    lane after."""
    name, d, r = next(s for s in _supermarkets() if s[0] == "supermarket_a01.json")
    _along, lines = L._gondola_lines(d, r)
    by_name = {v["name"]: n for n, line in enumerate(lines) for v in line["vols"]}
    p = os.path.join(HERE, "build", "supermarket_a01.slots.json")
    if not os.path.exists(p):
        pytest.skip("supermarket_a01 is not built")
    slots = json.load(open(p, encoding="utf-8"))["slots"]
    got = {s["slot_id"]: s for s in slots if s["slot_id"] in by_name}
    assert set(got) == set(by_name), name
    for sid, n in by_name.items():
        assert got[sid]["form"] == "grocery" and got[sid]["variant"] == n, (sid, got[sid]["form"], got[sid]["variant"])
        assert got[sid]["transform"]["rot_y"] == 90.0, (sid, got[sid]["transform"]["rot_y"])
