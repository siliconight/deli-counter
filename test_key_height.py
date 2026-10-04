"""One module name, one geometry, in every building (0.176.0).

Zoo and `themed_tscn.resolve_themed_stem` name a wall, doorway or window by
its width, on the ground that the storey height is fixed. An Empty broke it
(0.175.2): 3.1 m walls below the roof storey, 2.8 m under the roof, one name,
one file -- the 2.8 m panel won and cold run 9148's side walls had a 0.3 m
strip at every storey line. `mark_height_keys` marks each slot whose name
covers two heights with `fit.key_height`; Zoo (>= 1.60.0) and the mirror then
add `_h<cm>`. Unmarked buildings keep every name.
"""
import glob
import json
import os
from collections import defaultdict

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))

import themed_tscn as tt   # noqa: E402


def _wall(h, sid="ext_0_S_seg0"):
    return {"slot_id": sid, "role": "wall", "size_mod": "full", "style": 1,
            "material": "brick", "material_in": "drywall",
            "fit": {"dims": [2.0, 0.3, h], "pivot": "center", "openings": [],
                    "collision": "convex"}}


def _stem(s):
    return tt.resolve_themed_stem(s, "delco_1997", 1, material=tt.stem_material(s))[0]


def test_a_name_that_covers_two_heights_is_marked_and_split():
    """FAILS ON 0.175.2: no such function, and one name for both."""
    marked = tt.mark_height_keys([_wall(3.1, "a"), _wall(2.8, "b")])
    assert all(s["fit"].get("key_height") for s in marked)
    assert len({_stem(s) for s in marked}) == 2
    assert {_stem(s).split("_m")[0] for s in marked} == {
        "wall_delco_1997_01_w200_h310", "wall_delco_1997_01_w200_h280"}


def test_one_height_is_left_alone():
    """The control: a building whose walls share a height keeps every name."""
    slots = [_wall(3.1, "a"), _wall(3.1, "b")]
    assert tt.mark_height_keys(slots) == slots
    assert _stem(slots[0]) == "wall_delco_1997_01_w200_mbrick_idrywall"


@pytest.mark.skipif(not os.path.isdir(os.path.join(HERE, "build")),
                    reason="no build/ to read")
def test_no_built_building_gives_two_geometries_one_name():
    """The general form, across the whole library as built: within a
    building, an exact-fit module name maps to exactly one set of dims. On
    0.175.2 this found 14 names, all in the 8 facade shells."""
    bad = []
    for f in sorted(glob.glob(os.path.join(HERE, "build", "*.slots.json"))):
        if os.path.basename(f).startswith("lf_"):
            continue
        with open(f, encoding="utf-8") as fh:
            slots = json.load(fh)["slots"]
        g = defaultdict(set)
        for s in slots:
            stem, unit = tt.resolve_themed_stem(s, "delco_1997", 1,
                                                material=tt.stem_material(s))
            if stem is None or unit:
                continue
            g[stem].add(tuple(round(float(v), 4) for v in s["fit"]["dims"][:3]))
        bad += ["%s: %s %s" % (os.path.basename(f), k, sorted(v))
                for k, v in g.items() if len(v) > 1]
    assert not bad, bad
