"""The staff side of a teller line is its own room behind locked doors.

The walker, cold run 9048: "this bank teller booth should connect and be
locked to the public... a section where only employees can be there and
enter/exit". `level_design.enclose_teller_lines`.

    python -m pytest test_teller_enclosure.py -q
"""
import contextlib
import copy
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import interactives  # noqa: E402
import layout_lint  # noqa: E402
import level_design as LD  # noqa: E402
import presets  # noqa: E402


def _bank():
    with contextlib.redirect_stdout(io.StringIO()):
        return presets.make("bank", enrich=False)


def test_the_bank_preset_encloses_its_teller_line_behind_two_locked_doors():
    d = _bank()
    report = LD.enclose_teller_lines(d)
    assert [r["enclosed"] for r in report] == [True], report
    room = [r for r in d["rooms"] if r["id"] == "teller_staff_0"][0]
    assert room["role"] == "staff_only"
    # the teller line runs x -6..6 at y -2; the wall behind it is y = 2
    assert room["bounds"] == [-6.0, -2.0, 6.0, 2.0], room
    doors = [o for p in d["partitions"] for o in p.get("openings", [])
             if str(o.get("tag", "")).startswith("staff_door")]
    assert len(doors) == 2
    for o in doors:
        m = interactives.derive_interactive("bank", "int_0_x", 0, "door",
                                            o["pos"], override=o["interactive"])
        assert m["default"] == "locked" and m["access"] == "staff", m
        assert {"event": "unlock", "from": "locked", "to": "closed"} in m["transitions"]


def test_enrich_encloses_it_and_adds_no_lint_failure():
    raw = _bank()
    before = set(layout_lint.gate(copy.deepcopy(raw))[0])
    with contextlib.redirect_stdout(io.StringIO()):
        d = presets.make("bank")
    assert any(r["id"] == "teller_staff_0" for r in d["rooms"])
    assert not (set(layout_lint.gate(d)[0]) - before)


def test_it_is_idempotent():
    d = _bank()
    LD.enclose_teller_lines(d)
    again = copy.deepcopy(d)
    assert LD.enclose_teller_lines(again) == []
    assert again == d


def test_a_line_it_cannot_close_is_left_open_with_the_reason():
    with open(os.path.join(HERE, "specs", "credit_union_a01.json"),
              encoding="utf-8") as f:
        d = json.load(f)
    report = LD.enclose_teller_lines(copy.deepcopy(d))
    assert [r["enclosed"] for r in report] == [False]
    assert "1.10 m deep" in report[0]["why"], report


def test_the_library_banks_are_enclosed():
    for name in ("bank_branch_a02", "bank_branch_a03", "bank_job"):
        with open(os.path.join(HERE, "specs", name + ".json"),
                  encoding="utf-8") as f:
            d = json.load(f)
        assert any(r["id"].startswith("teller_staff") for r in d["rooms"]), name
