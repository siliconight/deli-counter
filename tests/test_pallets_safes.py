"""The loading dock's pile is pallet stacks, and a safe is painted steel (0.267.0). The walker, walking cold run
9386: of deli_a03's stockroom, "not sure what this large boring wood block is" (finding 9), and of pharmacy_a01's drop
safe, "looks like a brown box" (finding 3)."""
import glob
import json
import os

import level_design
import presets

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: Zoo's `pallet_stack` genome, 1.122.0: what a stack may measure and still build as one (width, depth, height)
PALLET_FITS = ((0.84, 1.8), (0.7, 1.5), (0.665, 1.425))


def _fits(v):
    dims = (float(v["size_x"]), float(v["size_y"]), float(v["size_z"]))
    return all(lo - 1e-9 <= x <= hi + 1e-9 for x, (lo, hi) in zip(dims, PALLET_FITS))


import pytest


@pytest.mark.parametrize("sx,sy,n", [(4.5, 2.5, 6), (4.0, 3.0, 6)])
def test_the_pile_is_stacks_that_each_fit_and_no_body_passes_between(sx, sy, n):
    pile = presets.pallet_pile(12.0, 10.0, 0.0, sx, sy)
    assert len(pile) == n and all(_fits(v) for v in pile), [(v["size_x"], v["size_y"], v["size_z"]) for v in pile]
    uw, ud = pile[0]["size_x"], pile[0]["size_y"]
    xs = sorted({v["x"] for v in pile}); ys = sorted({v["y"] for v in pile})
    assert min(b - a for a, b in zip(xs, xs[1:])) - uw < 0.35   # a body is 0.7 m across
    assert min(b - a for a, b in zip(ys, ys[1:])) - ud < 0.35
    x0 = min(v["x"] - v["size_x"] / 2 for v in pile); x1 = max(v["x"] + v["size_x"] / 2 for v in pile)
    y0 = min(v["y"] - v["size_y"] / 2 for v in pile); y1 = max(v["y"] + v["size_y"] / 2 for v in pile)
    assert abs(x1 - x0 - sx) < 0.01 and abs(y1 - y0 - sy) < 0.01


def test_no_library_spec_keeps_the_one_block():
    """FAILS ON 0.266.0: eight library specs carry one block (six at 4.5 x 2.5, two at 4.0 x 3.0)."""
    held = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if not isinstance(d, dict):
            continue
        held += [os.path.basename(p) for v in d.get("volumes") or [] if v.get("name") == "loading_pallet_stack"]
    assert not held, held


def test_a_pile_counts_as_one_piece_of_what_its_room_holds():
    """FAILS ON 0.266.0 (no pile there). Counted as six, a deli's stockroom went without five pieces of its
    furniture when the library was refurnished around the stacks."""
    d = json.load(open(os.path.join(HERE, "specs", "deli_a01.json"), encoding="utf-8"))
    stacks = [v for v in d["volumes"] if str(v.get("name", "")).startswith("loading_pallet_stack_")]
    assert len(stacks) == 6, [v["name"] for v in stacks]
    s = stacks[0]
    room = [r for r in d["rooms"] if r["bounds"][0] <= s["x"] <= r["bounds"][2] and r["bounds"][1] <= s["y"] <= r["bounds"][3]
            and r.get("story", 0) == 0][0]
    with_pile = level_design._room_volume_count(d, room)
    d["volumes"] = [v for v in d["volumes"] if v not in stacks]
    assert with_pile == level_design._room_volume_count(d, room) + 1


def test_a_safe_is_painted_steel():
    """FAILS ON 0.266.0: `safe` fell to the `metal` row, the theme's street rust."""
    for name in ("safe_floor", "count_safe", "office_safe", "exec_safe"):
        assert level_design._prop_material({}, name) == "metal_painted", name
    assert level_design._prop_material({}, "tank_0") == "metal"


def test_no_stored_safe_wears_street_metal():
    """FAILS ON 0.266.0: the library's stored safes say `metal`."""
    rust = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if not isinstance(d, dict):
            continue
        rust += [(os.path.basename(p), v["name"]) for v in d.get("volumes") or []
                 if "safe" in str(v.get("name", "")).lower() and v.get("material") == "metal"]
    assert not rust, (len(rust), rust[:5])
