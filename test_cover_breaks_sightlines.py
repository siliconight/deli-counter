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
    breaks the pair. Returning a number there would invent a crossing.

    The body has to be tall enough to CONTAIN a 1.5 m aim point, or the
    containment check refuses first and this stops testing what it says."""
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps({
        "characters": {"player": {"radius_m": 0.35, "height_m": 2.4,
                                  "chest_height_m": 1.5}},
        "sightlines": {"crew_sight_height_m": 1.4,
                       "enemy_sight_height_m": 1.5,
                       "aim_height_m": 1.5}}), encoding="utf-8")
    _reload_contract(monkeypatch, path)
    with pytest.raises(ValueError, match="never cross"):
        AC.cover_break_height()


# ---- the aim point belongs to a body -----------------------------------------

def test_the_aim_point_is_a_property_of_the_body(tmp_path, monkeypatch):
    """`aim_height_m` was settable and derived from nothing: 1.0 m is where a
    1.8 m body's chest is, and no field said so. A studio stating a 2.05 m
    character got an eye that followed and an aim point that did not."""
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps({
        "characters": {"player": {"radius_m": 0.45, "height_m": 2.05,
                                  "chest_height_m": 1.13}},
        "sightlines": {"crew_sight_height_m": 1.85,
                       "enemy_sight_height_m": 1.85,
                       "aim_height_m": 1.13}}), encoding="utf-8")
    _reload_contract(monkeypatch, path)
    assert AC.chest_height() == pytest.approx(1.13)
    assert AC.cover_break_height() == pytest.approx((1.85 + 1.13) / 2.0)


def test_an_aim_point_outside_its_own_body_is_refused(tmp_path, monkeypatch):
    """THE FAILURE THIS PREVENTS, and it is not a rounding complaint. LOS is
    granted only when the ray cast AT this height hits the target body first,
    so an aim point above the capsule misses -- nothing ever sees anything and
    the report is full of zeroes that read like a map problem. A 1.0 m
    character aimed at a fixed 1.0 m is aimed at the top of its own head."""
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps({
        "characters": {"player": {"radius_m": 0.35, "height_m": 1.0,
                                  "chest_height_m": 1.0}},
        "sightlines": {"crew_sight_height_m": 0.9,
                       "enemy_sight_height_m": 0.9, "aim_height_m": 1.0}}),
        encoding="utf-8")
    _reload_contract(monkeypatch, path)
    with pytest.raises(ValueError, match="outside the body's own capsule"):
        AC.chest_height()


def test_the_two_copies_of_the_aim_point_must_agree(tmp_path, monkeypatch):
    """It is carried in `sightlines` as well, because the crossing needs all
    three numbers in one place. A value carried twice is a value that rots, so
    the body decides and the copy is checked against it."""
    path = tmp_path / "agent_contract.json"
    path.write_text(json.dumps({
        "characters": {"player": {"radius_m": 0.35, "height_m": 1.8,
                                  "chest_height_m": 1.0}},
        "sightlines": {"crew_sight_height_m": 1.6,
                       "enemy_sight_height_m": 1.6, "aim_height_m": 1.2}}),
        encoding="utf-8")
    _reload_contract(monkeypatch, path)
    with pytest.raises(ValueError, match="one body, one aim point"):
        AC.cover_break_height()


def test_the_shipped_aim_point_sits_in_the_shipped_body():
    """The contract as it stands, not a fixture."""
    player = AC.contract()["characters"]["player"]
    assert (float(player["radius_m"]) <= AC.chest_height()
            <= float(player["height_m"]) - float(player["radius_m"]))
    # And it is where a standing body's centre of mass is: about 0.55 of
    # stature, so 0.55 * 1.8 = 0.99, ratified at 1.0.
    assert AC.chest_height() == pytest.approx(
        0.55 * float(player["height_m"]), abs=0.02)


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


class _Thing:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _room_of(*heights):
    """A 10x10 combat room furnished with solids of the given heights.

    A FIXTURE RATHER THAN A PRESET, and it did not start that way: this
    asserted against `suburban_safehouse`, which had six such rooms, and 0.112
    left the corpus with none. A check that can only be written while the
    defect is present stops being a check the moment somebody fixes it.
    """
    room = _Thing(id="r", bounds=(0.0, 0.0, 10.0, 10.0), story=0,
                  combat_range="medium", role="")
    volumes = [_Thing(name="crate_%d" % i, x=2.0 + i, y=5.0, z=h / 2.0,
                      size_x=1.0, size_y=1.0, size_z=h)
               for i, h in enumerate(heights)]
    return _Thing(rooms=[room], volumes=volumes, markers=[],
                  story_height=3.5), room


def test_furniture_alone_does_not_credit_a_room():
    """A room of 0.95 m crates counts as covered for "is it bare" and not for
    "can it be fought in". Before the split it counted for both."""
    spec, room = _room_of(0.95, 0.95, 1.05)
    assert CA._cover_in_room(spec, room) == 3          # furnished
    assert CA._cover_in_room(spec, room, CA.COVER_BREAK_H) == 0   # unfightable


def test_one_piece_over_the_crossing_is_enough_to_credit_it():
    """What the shelter pass adds, and why one piece is the fix rather than a
    raise of all the furniture."""
    spec, room = _room_of(0.95, 0.95, LD.shelter_height())
    assert CA._cover_in_room(spec, room, CA.COVER_BREAK_H) == 1


def test_the_corpus_has_no_room_that_cannot_be_fought_in():
    """WAS 39 OF 91 (0.111.0), IS 0 (0.112.0). The regression guard, and the
    direction it guards has flipped: the finding used to be evidence that the
    corpus had the defect, and is now evidence that it does not."""
    flagged = []
    for name in sorted(P.REGISTRY):
        if P.make(name, enrich=False).get("facade"):
            continue
        res = CA.audit(spec_from_dict(P.make(name, enrich=True)), name=name)
        flagged += [(name, f[2]) for f in res["findings"]
                    if f[1] == "COVER_ALL_LOW"]
    assert flagged == [], flagged


def test_every_combat_room_big_enough_to_seed_has_shelter():
    """The producer's side of the same claim, asked of the volumes rather
    than of the audit. Rooms below `_SEED_MIN_AREA` are exempt on purpose --
    a small bare room still reads fine -- and so is one where nothing fits,
    which keeps its finding rather than getting a crate in a doorway."""
    missing = []
    for name in sorted(P.REGISTRY):
        raw = P.make(name, enrich=False)
        if raw.get("facade"):
            continue
        d = P.make(name, enrich=True)
        for r in d.get("rooms", []):
            if not r.get("combat_range"):
                continue
            x0, y0, x1, y1 = r["bounds"]
            if (x1 - x0) * (y1 - y0) < LD._SEED_MIN_AREA:
                continue
            if not LD._room_has_shelter(d, r):
                missing.append((name, r["id"]))
    # Named rather than counted: a room that cannot hold shelter is a fact
    # about that room, and the list is how somebody finds out which.
    assert missing == [], missing


def test_the_shelter_pass_is_idempotent():
    """`enrich` promises additive and idempotent. A shelter piece that
    re-seeded on every run would multiply on every re-enrich."""
    import copy
    d = P.make("hospital", enrich=True)
    again = copy.deepcopy(d)
    report = LD.enrich(again)
    assert report == {"cover_seeded": 0, "cover_added": 0, "landmarks_added": 0}
    assert len(again["volumes"]) == len(d["volumes"])


def test_shelter_is_taller_than_the_height_cover_starts_working_at():
    """Two ends of one question. At the crossing a solid works at exactly one
    position on the line and a producer has to land on it; at the taller eye
    the whole line works, which is what a producer should build to."""
    assert LD.shelter_height() > AC.cover_break_height()
    assert LD.shelter_height() == pytest.approx(max(
        AC.contract()["sightlines"]["crew_sight_height_m"],
        AC.contract()["sightlines"]["enemy_sight_height_m"]))


def test_the_killbox_remedy_does_not_recommend_furniture():
    """The advice on the neighbouring finding said "two or three 0.9-1.2 m
    volumes fix it" -- heights that leave both sides a free shot. A remedy
    that reproduces the defect it is fixing is worse than none."""
    import inspect
    src = inspect.getsource(CA.audit)
    start = src.index('"KILLBOX"')
    assert "0.9-1.2 m volumes fix it." not in src[start:start + 600]
