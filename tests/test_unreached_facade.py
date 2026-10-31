"""A storey nobody reaches is a facade (0.295.0; the factory's roadmap 79, the facade planner, and the walker's slice).

The slice's bank, bank_branch_a02, has an upper storey with no room and no stair, and stood two 1.6 m windows on each
of its 30 m and 22 m faces -- a warehouse's rhythm on a bank -- glazed clear onto an empty box.
`facade_plan.unreached_storeys` finds such a storey; `compose_unreached` lays its faces' untagged windows on equal
bays of the builder's grid; the emitter paints them as an office after hours (`empty_panes.OFFICE`), the way an
Empty's windows are painted, because nobody can see out of them and nothing stands behind them.

FAIL ON 0.294.0: there is no `unreached_storeys`, `compose_unreached` or `OFFICE`, and the bank's spec still carries two
windows a face upstairs. The spec tests read the spec alone, so they fail for that reason and not for an import.
"""
import copy
import json
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import spec_loader   # noqa: E402


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _cut(d, story):
    """{side: openings of `side` on `story` in metres from the wall's centre, as the builder cuts them}."""
    s = spec_loader.spec_from_dict(d)
    out = {}
    for w in s.ext_walls:
        if w.story == story:
            run = s.footprint_x if w.wall in ("N", "S") else s.footprint_y
            out[w.wall] = sorted(round(round(o.pos * run / s.grid) * s.grid, 3) for o in w.openings)
    return out


def test_the_banks_upper_storey_stands_on_equal_three_metre_bays():
    cut = _cut(_spec("bank_branch_a02"), 1)
    assert cut["S"] == cut["N"] == [-13.5, -10.5, -7.5, -4.5, -1.5, 1.5, 4.5, 7.5, 10.5, 13.5]
    assert cut["E"] == cut["W"] == [-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0]


def test_its_ground_floor_is_untouched():
    """The ground floor is where play is: its doors, its storefront and its breach stay as authored."""
    d = _spec("bank_branch_a02")
    ground = [w for w in d["ext_walls"] if w["story"] == 0]
    assert [len(w["openings"]) for w in ground] == [3, 1, 1, 1]
    assert ground[0]["openings"][0]["tag"] == "main_entry"


def test_only_a_storey_nobody_reaches_is_one():
    import facade_plan
    assert facade_plan.unreached_storeys(spec_loader.spec_from_dict(_spec("bank_branch_a02"))) == [1]
    # every other multi-storey building in the library has a room or a stair up
    for name in ("bank", "bank_branch_a04", "deli_a01", "office"):
        assert facade_plan.unreached_storeys(spec_loader.spec_from_dict(_spec(name))) == [], name


def test_a_stair_or_a_room_up_makes_it_reached():
    import facade_plan
    d = _spec("bank_branch_a02")
    stair = dict(d["stairs"][0], from_story=0, to_story=1, id="up")
    reached = copy.deepcopy(d)
    reached["stairs"].append(stair)
    assert facade_plan.unreached_storeys(spec_loader.spec_from_dict(reached)) == []
    roomed = copy.deepcopy(d)
    roomed["rooms"].append({"id": "office_up", "story": 1, "bounds": [-14.0, -10.0, 14.0, 10.0]})
    assert facade_plan.unreached_storeys(spec_loader.spec_from_dict(roomed)) == []


def test_composing_is_idempotent_and_keeps_tagged_windows():
    import facade_plan
    d = _spec("bank_branch_a02")
    before = json.dumps(d, sort_keys=True)
    assert facade_plan.compose_unreached(d) == [("S", 1, 10, 10), ("N", 1, 10, 10), ("E", 1, 7, 7), ("W", 1, 7, 7)]
    assert json.dumps(d, sort_keys=True) == before
    tagged = copy.deepcopy(d)
    tagged["ext_walls"][4]["openings"][0]["tag"] = "sniper_perch"
    facade_plan.compose_unreached(tagged)
    assert [o.get("tag") for o in tagged["ext_walls"][4]["openings"]].count("sniper_perch") == 1


def test_the_library_is_migrated():
    r = subprocess.run([sys.executable, os.path.join(HERE, "migrations", "migrate_unreached_facade.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_office_table_paints_only_states_zoo_has():
    import empty_panes
    assert sum(w for _, w in empty_panes.OFFICE) == 100
    assert all(s in empty_panes.STATES for s, _ in empty_panes.OFFICE)
    assert not {s for s, _ in empty_panes.OFFICE} & set(empty_panes.NO_AC)
    got = {empty_panes.choose("bank_branch_a02", 2101, "ext_1_S_open%d" % i, 1, office=True) for i in range(60)}
    assert got <= {s for s, _ in empty_panes.OFFICE} and len(got) > 3


def test_the_emitter_paints_an_unreached_storeys_windows_without_fixtures():
    src = open(os.path.join(HERE, "deli_counter.py"), encoding="utf-8").read()
    assert re.search(r"office = \(role == \"window\" and not getattr\(self\.s, \"facade\", False\)\s+"
                     r"and story in self\._unreached\(\)\)", src)
    assert 'vacant=getattr(self.s, "vacant", False), office=office)' in src
    assert "if not office:\n                    slot.update(empty_panes.fixtures(" in src


def test_a_painted_window_derives_no_light():
    """A window's area light stands for the street through the glass into its room; behind a painted pane there is
    no room. The bank's built lights keep its ground floor's windows and derive none upstairs -- the drape's rule."""
    lights = json.load(open(os.path.join(HERE, "build", "bank_branch_a02.lights.json"), encoding="utf-8"))
    anchors = lights["anchors"] if isinstance(lights, dict) else lights
    windows = [a for a in anchors if a.get("type") == "window"]
    assert windows and all(float(a["pos"][2]) < 3.6 for a in windows), [a["id"] for a in windows]
    src = open(os.path.join(HERE, "lights.py"), encoding="utf-8").read()
    assert 'if o.get("story") in (painted_storeys or ()):' in src
