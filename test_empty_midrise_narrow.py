"""The narrow mid-rise Empties: the blocks that fit between the mission's buildings (0.217.0, factory roadmap 241).

Level Factory 0.201.0 fills an urban street's near frontage between the mission's own buildings, a 4 m passage
kept beside each. On urban_row_001's three candidates (cold run 9288) the rooms left were 12.67 m, 11.35, 7.33,
6.70 and none -- and the narrowest of the six mid-rises measures 15.3 m, so nothing stood (the factory's
`docs/findings/urban_street/near_room.py`). Real streets carry two- and three-bay buildings between the wide
blocks; `EMPTY_MIDRISE_NARROW` is three, 12.0, 10.0 and 6.3 m wide (12.3, 10.3 and 6.6 as built, a wall's
thickness more), four to six storeys, under the six's prefix so the urban street draws them with the rest.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets   # noqa: E402

NARROW = presets.EMPTY_MIDRISE_NARROW


def _built(name):
    return presets.empty_midrise(name=name, **NARROW[name])


def _load(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_the_narrow_three_are_narrower_and_lower_than_the_six():
    widths = sorted(a["width"] for a in NARROW.values())
    assert widths == [6.3, 10.0, 12.0], widths
    assert max(widths) < min(a["width"] for a in presets.EMPTY_MIDRISES.values())
    assert sorted(a["floors"] for a in NARROW.values()) == [4, 5, 6]
    assert not set(NARROW) & set(presets.EMPTY_MIDRISES)
    assert len({a["seed"] for a in list(NARROW.values()) + list(presets.EMPTY_MIDRISES.values())}) == 9


def test_every_narrow_block_is_the_preset_s_own_output_under_the_family_s_prefix():
    for name in NARROW:
        assert name.startswith("gs_midrise_") and not name.startswith("gs_empty_"), name
        assert _load(name) == json.loads(json.dumps(_built(name))), name


def test_a_narrow_block_is_an_empty_with_its_windows_in_the_family_s_rhythm():
    for name, a in NARROW.items():
        s = _built(name)
        assert s["facade"] is True and s["auto_exterior"] is True and s["roof_material"] == "tar", name
        assert {w["wall"] for w in s["ext_walls"]} == {"S", "N"}, name
        for w in s["ext_walls"]:
            pos = sorted(o["pos"] for o in w["openings"])
            spacing = (pos[1] - pos[0]) * a["width"]
            assert 2.8 <= spacing <= 3.4, (name, w["wall"], w["story"], spacing)
        doors = sorted((w["wall"], w["story"], o["tag"]) for w in s["ext_walls"] for o in w["openings"]
                       if o["kind"] == "door")
        assert doors == [("N", 0, "back_door"), ("S", 0, "front_door")], (name, doors)


def test_the_two_bay_floor_leaves_the_six_as_they_were():
    """`bays` floors at two, not three: no block of the six has fewer than five, so their specs stand."""
    for name, a in presets.EMPTY_MIDRISES.items():
        assert round(a["width"] / presets.MIDRISE_BAY) >= 5, name
        assert _load(name) == json.loads(json.dumps(presets.empty_midrise(name=name, **a))), name
