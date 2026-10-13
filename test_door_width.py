"""Every walkable door is at least the contract's `min_door_width_m` (0.214.0, factory roadmap 197).

`agent_contract.json`'s door minimum is 1.25 m. The library built 200 walkable doors under it -- 13 at 1.0 m, 74
at 1.1 and 113 at 1.2, 47 of those width-less and so at this builder's own default, then 1.2 -- and the presets
wrote 61 more (the factory's `docs/findings/door_widths/`). The walker, 2026-10-13: widen the doors, keep 1.25,
and call it out in the contract. These hold the rule where a door comes from: a library spec, the width-less
default, a preset made as Level Factory makes one, a built shell, and the contract's own text. An Empty's doors
are shut and nothing walks through them; one door is KEPT narrow by name (`migrate_door_width.KEPT`), and the
landing door stairs-first generation punches stays `stair_core._PUNCH_DOOR_W`, named in the contract.

Runs without Blender. On 0.213.0 the migration module does not exist and this module fails to import; the
width-less default, the contract's text and the stairs-first case below fail on 0.213.0 by themselves.
"""
import copy
import glob
import inspect
import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract        # noqa: E402
import level_design          # noqa: E402
import migrate_door_width    # noqa: E402
import presets               # noqa: E402
import stair_core            # noqa: E402
from spec_types import Opening   # noqa: E402

MIN = agent_contract.min_door_width()


def _library():
    """The library's specs, as `layout_lint --all` reads them: Level Factory's `lf_*` transients left out."""
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        with open(p, encoding="utf-8") as fh:
            yield json.load(fh)


def _doors(d):
    for w in (d.get("ext_walls") or []) + (d.get("partitions") or []):
        for o in w.get("openings") or []:
            if o.get("kind") == "door":
                yield o


def _resolved(o):
    return Opening(kind="door", pos=0.0, width=o.get("width")).resolved()["width"]


def _narrow(spec):
    return [(o.get("tag"), _resolved(o)) for o in _doors(spec)
            if _resolved(o) < MIN - 1e-9 and (spec.get("name"), o.get("tag")) not in migrate_door_width.KEPT]


def test_the_width_less_door_is_the_contract_s():
    """FAILS ON 0.213.0: a width-less door resolved to 1.2."""
    assert Opening(kind="door", pos=0.0).resolved()["width"] == MIN


def test_every_door_width_the_code_writes_reads_the_contract(monkeypatch):
    """ONE CHANGE TO A BODY, NOT SIX EDITS (the walker, 2026-10-13: "so we can make singular changes when we
    know the size of characters in the game"). The door widths this builder's code writes are asked of the
    contract, not spelt beside it -- so a contract with other numbers gets other doors. Asked of a stand-in
    contract here, since the module-level ones (`presets.DOOR_W`, the staff door, the punched landing door)
    are read once, at import, from the contract in force; those three are checked against it below."""
    stand_in = {k: dict(v) for k, v in agent_contract.contract().items()}
    stand_in["clearances"]["min_door_width_m"] = 1.4
    monkeypatch.setattr(agent_contract, "_cache", stand_in)
    assert Opening(kind="door", pos=0.0).resolved()["width"] == 1.4
    monkeypatch.undo()
    assert presets.DOOR_W == MIN
    assert level_design._STAFF_DOOR_WIDTH == MIN
    assert stair_core._PUNCH_DOOR_W == agent_contract.min_corridor_width() < MIN


def test_no_walkable_door_in_the_library_is_under_the_minimum():
    narrow = [(d["name"], tag, w) for d in _library() if not d.get("facade") for tag, w in _narrow(d)]
    assert not narrow, narrow


def test_the_kept_door_is_named_and_still_narrow():
    """A KEPT door is a recorded exception, not a forgotten one: it exists, it carries its reason, and it is
    still under the minimum -- when its stair moves and it widens, this asks for the entry to go."""
    lib = {d["name"]: d for d in _library()}
    for (spec, tag), why in migrate_door_width.KEPT.items():
        widths = [_resolved(o) for o in _doors(lib[spec]) if o.get("tag") == tag]
        assert len(widths) == 1 and widths[0] < MIN and why, (spec, tag, widths)


def _calls(name):
    """What Level Factory's adapter can hand a preset: a mode, a floor count, a basement where it takes one
    (`new_level.py --mode --floors --basement/--no-basement`). Every enterable preset takes all three modes and
    one to four floors; a refusal fails the test rather than being skipped."""
    calls = [dict(mode=m) for m in ("heist", "assault", "survival")]
    calls += [dict(mode="heist", floors=f) for f in (1, 2, 3, 4)]
    if "basement" in inspect.signature(presets.REGISTRY[name]).parameters:
        calls += [dict(mode="heist", basement=b) for b in (True, False)]
    return calls


@pytest.mark.parametrize("name", sorted(n for n in presets.REGISTRY if not presets.REGISTRY[n]().get("facade")))
def test_a_preset_made_as_level_factory_makes_it_writes_no_narrow_door(name):
    for kwargs in _calls(name):
        spec = presets.make(name, seed=9104, **kwargs)
        assert not _narrow(spec), (name, kwargs, _narrow(spec))


def test_the_migration_leaves_an_empty_and_a_kept_door_alone_and_is_idempotent():
    empty = {"name": "x", "facade": True,
             "ext_walls": [{"wall": "S", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.0}]}]}
    assert migrate_door_width.migrate(copy.deepcopy(empty)) == []
    spec, tag = next(iter(migrate_door_width.KEPT))
    kept = {"name": spec, "ext_walls": [{"wall": "S", "story": 0,
                                         "openings": [{"kind": "door", "pos": 0.0, "width": 1.2, "tag": tag}]}]}
    assert migrate_door_width.migrate(copy.deepcopy(kept)) == []
    plain = {"name": "y", "ext_walls": [{"wall": "S", "story": 0,
                                         "openings": [{"kind": "door", "pos": 0.1, "width": 1.1}]}]}
    assert len(migrate_door_width.migrate(plain)) == 1
    assert plain["ext_walls"][0]["openings"][0] == {"kind": "door", "pos": 0.1, "width": MIN}
    assert migrate_door_width.migrate(plain) == []


def test_the_library_is_the_migration_s_fixed_point():
    """Nothing left for the migration to do: a spec it would still change was not migrated."""
    assert [d["name"] for d in _library() if migrate_door_width.narrow_doors(d)] == []


def test_the_contract_calls_the_change_out():
    """The walker's ask: the change is written into the contract, beside the number -- the minimum as a design
    number over the bake's own, and the doors that widened and the two that did not."""
    clear = agent_contract.contract()["clearances"]
    assert "DESIGN MINIMUM" in clear["derivation"]
    note = clear["min_door_width_note"]
    for phrase in ("0.214.0", "migrate_door_width", "kitchen_stairs", "_PUNCH_DOOR_W"):
        assert phrase in note, phrase


def test_the_contract_says_what_one_change_to_a_body_moves():
    """`re_derive_when`: the body and the bake numbers that start a re-derivation, the library's written
    widths and the migration that re-widens them, and the one body-sized number that does not follow yet."""
    when = agent_contract.contract()["clearances"]["re_derive_when"]
    for phrase in ("characters.player.radius_m", "nav_bake.cell_size_m", "migrate_door_width",
                   "stairwell.LANDING_DEPTH", "vault_room.APERTURE"):
        assert phrase in when, phrase


def test_the_derivation_is_worked_at_the_contract_s_own_bake():
    """The derivation was worked at a 0.15 m cell for a year after the bake moved to 0.10. The formula at the
    contract's own radius and cell must be the figure the text gives, and at or under the minimum -- so the
    next change to the bake fails here until the text is re-derived."""
    nav = agent_contract.contract()["nav_bake"]
    radius, cell = float(nav["agent_radius_m"]), float(nav["cell_size_m"])
    need = 2.0 * math.ceil(radius / cell - 1e-9) * cell + 2.0 * cell
    assert need <= MIN + 1e-9, (need, MIN)
    assert ("= %.2f" % need) in agent_contract.contract()["clearances"]["derivation"], need


def test_stairs_first_reads_a_width_less_door_at_the_width_it_builds():
    """FAILS ON 0.213.0. `stair_core._punch_door` asks whether a landing's crossing is already doored, and read
    a width-less door at a literal 1.2 while the builder builds it at the contract's minimum. A width-less door
    centred 0.61 m short of the crossing: at 1.2 its side stops 0.01 m short and a second door is punched
    beside it; at 1.25 it reaches 0.015 m in, and the crossing is doored. A 1.2 m door, written, is not."""
    land = [5.0, 1.0, 6.3, 3.0]

    def partition(width=None):
        door = {"kind": "door", "pos": 4.39 / 10.0 - 0.5}
        if width is not None:
            door["width"] = width
        return {"axis": "X", "pos": 2.0, "start": 0.0, "end": 10.0, "story": 0, "openings": [door]}

    assert stair_core._PUNCH_DOOR_W < MIN, "the punched door is named in the contract as under the minimum"
    width_less = partition()
    assert stair_core._punch_door(width_less, land, 0.2) is False
    assert len(width_less["openings"]) == 1
    written = partition(width=1.2)
    assert stair_core._punch_door(written, land, 0.2) is True
    assert written["openings"][-1]["width"] == stair_core._PUNCH_DOOR_W


def test_a_crossing_exactly_the_door_s_width_is_punched(monkeypatch):
    """FAILS ON 0.213.0. A crossing as wide as the door is not too short for it. Spelt 6.1 - 5.0, a 1.1 m
    crossing is 1.0999999999999996, and the check refused a 1.1 m door by 4e-16 -- while two of the 20
    crossings `stair_regression` makes are 1.1000000000000014 and were punched by 1.4e-15."""
    monkeypatch.setattr(stair_core, "_PUNCH_DOOR_W", 1.1)
    land = [5.0, 1.0, 6.1, 3.0]
    assert land[2] - land[0] < 1.1, "the case is the float window or it tests nothing"
    part = {"axis": "X", "pos": 2.0, "start": 0.0, "end": 10.0, "story": 0, "openings": []}
    assert stair_core._punch_door(part, land, 0.2) is True
    assert part["openings"][0]["width"] == 1.1


def _library_shells():
    """(spec name, built `gameplay.json`) for each enterable library spec built here. `build/` also keeps
    builds of specs no longer in the library (`fuel_stop_heist3`, `fuel_stop_heist4` on the machine this was
    written on), and `gameplay.json` is not tracked, so the library is the list, not the directory."""
    for d in _library():
        if d.get("facade"):
            continue
        gp = os.path.join(HERE, "build", d["name"] + ".gameplay.json")
        if os.path.exists(gp):
            yield d["name"], gp


def test_every_built_shell_s_doors_are_wide_enough():
    """The builder's own record of what it cut. Skips where the library is not built."""
    shells = list(_library_shells())
    if not shells:
        pytest.skip("deli_counter/build holds no library shell; nothing built to read")
    narrow = []
    for name, gp in shells:
        with open(gp, encoding="utf-8") as fh:
            ops = json.load(fh).get("openings") or []
        narrow += [(name, o.get("tag"), o["width"]) for o in ops
                   if o.get("kind") == "door" and float(o["width"]) < MIN - 1e-9
                   and (name, o.get("tag")) not in migrate_door_width.KEPT]
    assert not narrow, narrow[:10]
