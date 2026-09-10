"""Cover height is derived from the firefight, not chosen (roadmap 130).

`_COVER_MIN_Z = 0.6` and `COVER_MIN_H = 0.6` were two spellings of one
chosen number, with a third copied inline into `_room_has_cover`, and all
three answered "is this waist-high furniture". Nothing anywhere answered the
question a shooting gallery actually asks, which is whether a solid stops the
two sides seeing each other -- and `combat_audit`'s own comment claimed the
first answered the second ("taller solids block sight = also cover"), which
is true of a 2 m shelf and false of the 0.9 m crate the threshold admits.

Measured on the 14 non-facade presets before the fix: 100 of 177 qualifying
solids (56%) stood below the height where the crew's sightline and the
enemy's cross, and 39 of 91 combat rooms were furnished entirely below it --
rooms that look built and lit and cannot be fought in, because both sides
shoot over everything in them.

THE TEST THAT MATTERS IS `test_the_break_height_is_derived_not_stored`.
Everything else guards the consumers.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agent_contract as AC             # noqa: E402
import combat_audit as CA               # noqa: E402
import level_design as LD               # noqa: E402
import presets as P                     # noqa: E402
from spec_loader import spec_from_dict   # noqa: E402


def _reload_contract(monkeypatch, path):
    monkeypatch.setenv("DC_AGENT_CONTRACT", str(path))
    monkeypatch.setattr(AC, "_cache", None)


# ---- the derivation ---------------------------------------------------------

def test_the_break_height_is_derived_not_stored(tmp_path, monkeypatch):
    """THE POINT OF THE ITEM. Move the evaluator's sight heights and the
    height at which cover works moves with them, with no constant to edit."""
    body = {"sightlines": {"crew_sight_height_m": 1.8,
                           "enemy_sight_height_m": 1.8,
                           "aim_height_m": 1.0}}
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    _reload_contract(monkeypatch, path)
    # Both sides sighting from the same height reduces to the midpoint, which
    # is the form `lot/site_cover.MIN_COVER_HEIGHT` derives.
    assert AC.cover_break_height() == pytest.approx(1.4)


def test_the_shipped_contract_agrees_with_its_own_inputs():
    """A stored value and a formula are two spellings of one quantity, and
    this file is hand-edited. `cover_break_height` recomputes and raises on a
    disagreement rather than quietly preferring one."""
    s = AC.contract()["sightlines"]
    a = float(s["crew_sight_height_m"])
    b = float(s["enemy_sight_height_m"])
    c = float(s["aim_height_m"])
    assert AC.cover_break_height() == pytest.approx(
        a - (a - c) ** 2 / (a + b - 2.0 * c))
    # 1.6 / 1.6 / 1.0 -> 1.3, from Laser Tag 0.20.0. It was 1.2222 when the
    # crew sighted from 1.4 and the enemy from 1.5; the number MOVING when the
    # evaluator's own heights moved is the derivation doing its job, and the
    # corpus flags the same 39 rooms either way because nothing in it stands
    # between 1.20 m and 1.40 m.
    assert AC.cover_break_height() == pytest.approx(1.3, abs=1e-4)


def test_a_stored_value_that_drifted_is_refused(tmp_path, monkeypatch):
    """The failure mode this replaces is silence: a hand-edited height that
    no longer follows from the heights above it, still being returned."""
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps({"sightlines": {
        "crew_sight_height_m": 1.4, "enemy_sight_height_m": 1.5,
        "aim_height_m": 1.0, "cover_break_height_m": 0.6}}), encoding="utf-8")
    _reload_contract(monkeypatch, path)
    with pytest.raises(ValueError, match="re-derive"):
        AC.cover_break_height()


def test_lines_that_never_cross_are_refused(tmp_path, monkeypatch):
    """Aiming at or above both eyes means no solid short enough to be cover
    breaks the pair. Returning a number there would invent a crossing."""
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps({"sightlines": {
        "crew_sight_height_m": 1.4, "enemy_sight_height_m": 1.5,
        "aim_height_m": 1.5}}), encoding="utf-8")
    _reload_contract(monkeypatch, path)
    with pytest.raises(ValueError, match="never cross"):
        AC.cover_break_height()


def test_a_missing_contract_degrades_to_the_ratified_value(tmp_path,
                                                           monkeypatch):
    """Same rule every other consumer of this contract follows: a build that
    refuses because a tool moved a file is worse than one that degrades."""
    _reload_contract(monkeypatch, tmp_path / "nope.json")
    assert AC.cover_break_height() == pytest.approx(1.3, abs=1e-4)


# ---- the consumers ----------------------------------------------------------

def test_high_cover_means_it_breaks_the_line():
    """`_COVER_HIGH_Z` was a chosen 1.4, which put the boundary 0.18 m above
    the height where cover starts working and called the gap "low"."""
    assert LD._COVER_HIGH_Z == pytest.approx(AC.cover_break_height())
    assert LD._COVER_HIGH_Z != 1.4


def test_the_two_questions_have_two_numbers():
    """Furniture and shelter are different claims. Collapsing them is the
    defect; keeping the furniture threshold is deliberate, because a low
    piece is still a thing in the room."""
    assert LD._COVER_MIN_Z < LD._COVER_HIGH_Z < LD._COVER_MAX_Z
    assert CA.COVER_MIN_H < CA.COVER_BREAK_H


def test_room_has_cover_reads_the_constant_not_a_copy():
    """The literal 0.6 was written out a fourth time inside `_room_has_cover`
    and would have gone stale the first time the constant moved."""
    import inspect
    src = inspect.getsource(LD._room_has_cover)
    code = "\n".join(line.split("#", 1)[0]
                     for line in src.splitlines())      # comments may say 0.6
    assert "_COVER_MIN_Z" in code
    assert "0.6" not in code


def test_furniture_alone_does_not_credit_a_room():
    """A room of 0.95 m crates counts as covered for "is it bare" and not for
    "can it be fought in". Before the split it counted for both."""
    spec = spec_from_dict(P.make("suburban_safehouse", enrich=True))
    room = next(r for r in spec.rooms
                if getattr(r, "combat_range", None)
                and CA._cover_in_room(spec, r) > 0
                and CA._cover_in_room(spec, r, CA.COVER_BREAK_H) == 0)
    assert CA._cover_in_room(spec, room) > 0


def test_the_corpus_reports_the_rooms_that_cannot_be_fought_in():
    """The finding exists and fires on the shipped presets rather than only
    on a fixture. 39 of 91 combat rooms when this was written; pinned as a
    floor, not an equality, so authoring cover does not fail the suite."""
    flagged = 0
    for name in sorted(P.REGISTRY):
        if P.make(name, enrich=False).get("facade"):
            continue
        res = CA.audit(spec_from_dict(P.make(name, enrich=True)), name=name)
        flagged += sum(1 for f in res["findings"] if f[1] == "COVER_ALL_LOW")
    assert flagged > 0, "the corpus had this defect when the check was written"


def test_the_killbox_remedy_does_not_recommend_furniture():
    """The advice on the neighbouring finding said "two or three 0.9-1.2 m
    volumes fix it" -- heights that leave both sides a free shot. A remedy
    that reproduces the defect it is fixing is worse than none."""
    import inspect
    src = inspect.getsource(CA.audit)
    start = src.index('"KILLBOX"')
    assert "0.9-1.2 m volumes fix it." not in src[start:start + 600]
