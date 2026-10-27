"""A bank's lobby hangs its printed offers, and its teller line names the bank (0.283.0, the factory's roadmap 321).

The walker's bank list: "the rate board and posters", the bank's name over the line, a number on every window (the
factory's docs/reference/BANK_INTERIOR_COMPS.md). Zoo 1.137.0 paints both: `poster_wall` form `bank` and
`teller_line` form `bank`, whose sixteen variants are the four bank names in the sign's four colourways.

FAILS ON 0.282.0: no piece is `poster_wall_bank`, and no teller line carries a form.
"""
import copy
import importlib
import json
import os
import re
import sys

import pytest

import level_design

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(HERE, "build")


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _library():
    for f in sorted(os.listdir(os.path.join(HERE, "specs"))):
        if f.endswith(".json") and not f.startswith("lf_"):
            try:
                yield f[:-5], _spec(f[:-5])
            except ValueError:
                continue


def _zoo(module):
    from test_furnish import ZOO
    if not os.path.isfile(os.path.join(ZOO, "zoo_keeper", "core", module.split(".")[-1] + ".py")):
        pytest.skip("zoo %s not found at %s (set DC_ZOO_ROOT; Zoo >= 1.137.0)" % (module, ZOO))
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module("zoo_keeper.core." + module)


def test_the_bank_poster_run_is_a_bank_lobby_fixture_of_zoos_bank_family():
    p = level_design._PIECES["poster_wall_bank"]
    assert p["form"] == "bank" and p["where"] == "wall" and p["collision"] == "none"
    assert "poster_wall_bank" in level_design._RECIPES["bank_lobby"]["fixtures"]
    assert not any("poster_wall_bank" in (r.get("fixtures") or ())
                   for k, r in level_design._RECIPES.items() if k != "bank_lobby")


def test_the_run_is_the_height_zoo_hangs_a_bank_sheet_in():
    PWF = _zoo("poster_wall_forms")
    if "bank" not in PWF.LAYOUT:
        pytest.skip("Zoo before 1.137.0 has no bank family")
    band = PWF.band_height("bank")
    sheet, gap = PWF.PA.SIZES_M["bank"][0], PWF.LAYOUT["bank"][0]
    for w, d, h in level_design._PIECES["poster_wall_bank"]["sizes"]:
        assert abs(h - band) < 1e-9, (w, h, band)
        # each width holds a whole run, its last sheet not wasted
        n = int((w + gap) // (sheet + gap))
        assert n >= 2 and w - (n * sheet + (n - 1) * gap) < 0.05, (w, n)


def test_every_library_bank_lobby_hangs_its_offers():
    seen = 0
    for name, d in _library():
        b = level_design.club_building_id(d)
        lobbies = [r for r in d.get("rooms") or [] if level_design._room_kind(r, b) == "bank_lobby"]
        if not lobbies:
            continue
        runs = [v for v in d["volumes"] if str(v.get("name", "")).startswith("poster_wall_bank")]
        assert runs, name
        assert all(v.get("form") == "bank" for v in runs), name
        seen += 1
    assert seen >= 6, seen


def _lines(d):
    return [v for v, _s, _a in level_design._teller_lines(d)]


def test_every_library_teller_line_names_its_bank():
    """Every line in a building whose sign is a bank's is form `bank`, in the
    variant `bank_teller_variant` gives its business; nothing else is."""
    dressed = 0
    for name, d in _library():
        b = level_design.club_building_id(d)
        lines = _lines(d)
        bankish = bool(set(re.split(r"[^a-z]+", b.lower())) & set(level_design._BANK_SIGN_WORDS))
        for v in d.get("volumes") or []:
            if v in lines and bankish:
                assert v.get("form") == "bank", (name, v["name"])
                assert int(v.get("variant", 0)) == level_design.bank_teller_variant(b), (name, v["name"])
                dressed += 1
            elif "teller" in str(v.get("name", "")):
                assert v.get("form") != "bank", (name, v["name"])
    # bank, bank_branch_a02-a04, bank_job, credit_union_a01
    assert dressed >= 6, dressed


def test_the_tower_desks_are_not_lines():
    d = _spec("bank_tower_a01")
    assert not _lines(d)
    assert not any(v.get("form") == "bank" for v in d["volumes"] if "teller" in v["name"])


def test_dressing_twice_changes_nothing():
    d = copy.deepcopy(_spec("bank_branch_a02"))
    assert level_design.dress_bank_teller_lines(d) == 0
    for v in _lines(d):
        v.pop("form", None)
        v.pop("variant", None)
    assert level_design.dress_bank_teller_lines(d) == len(_lines(d)) == 1
    assert level_design.dress_bank_teller_lines(d) == 0


def test_the_line_reads_the_name_and_colours_over_the_door():
    """The cross-check `bank_teller_variant` exists for: Zoo's sign over each
    library bank's door and the board its line paints say the same bank in
    the same colours."""
    TF = _zoo("teller_line_forms")
    SN = _zoo("storefront_names")
    checked = 0
    for name, d in _library():
        if not _lines(d):
            continue
        b = level_design.club_building_id(d)
        sign = SN.sign_for(b)
        if sign["kind"] != "bank":
            continue
        v = level_design.bank_teller_variant(b)
        assert v == TF.variant_for(b), name
        said = TF.bank_said(v)
        assert said["text"] == sign["text"] and tuple(said["colours"]) == tuple(sign["colours"]), name
        checked += 1
    assert checked >= 6, checked


def test_the_built_slot_asks_zoo_for_the_bank_form():
    for name in ("bank_branch_a02", "bank_branch_a03", "bank_branch_a04"):
        path = os.path.join(BUILD, name + ".slots.json")
        if not os.path.isfile(path):
            pytest.skip("%s is not built (build.py --all)" % name)
        slots = json.load(open(path, encoding="utf-8"))
        slots = slots.get("slots", slots) if isinstance(slots, dict) else slots
        tellers = [s for s in slots if s.get("species") == "teller_line"]
        assert tellers, name
        want = level_design.bank_teller_variant(level_design.club_building_id(_spec(name)))
        for s in tellers:
            assert s.get("form") == "bank" and int(s.get("variant") or 0) == want, (name, s.get("slot_id"))
