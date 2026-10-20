"""A facade's composition, decided where its openings are chosen (0.238.0; the factory's roadmap 79 and its
`docs/proposals/FACADE_PLANNER.md`).

Measured on the library before this (the factory's `docs/findings/facade_census_79/`): of the 169 first-storey openings
in the 52 multi-storey buildings a themed lot can draw, 28 stood over a ground-floor opening. The upper storeys had been
authored mirrored about each face's centre and the ground floors for the rooms behind them. `facade_plan` holds the
Empties' two rows, which compose already, and `stack_mirrored`, which moves the library's untagged upper windows onto
the openings below them -- a mirrored pair only together, within a bay -- and leaves every ground-floor opening, door,
breach and tagged window where gameplay put it. `presets.make` runs it on every spec it writes, and
`migrate_facade_stack.py` ran it over the library.

FAIL ON 0.237.0: there is no `facade_plan`, deli_a01's first-storey east window stands at 5.5 m over nothing, and
`presets.make("corner_deli")` writes it there. The library tests below read the specs alone, so they fail on 0.237.0
for that reason and not for an import.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import presets       # noqa: E402
import spec_loader   # noqa: E402


def _spec(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _u(d, side, story):
    """The openings of `side` on `story`, in metres along the wall from its centre, as the builder cuts them."""
    s = spec_loader.spec_from_dict(d)
    run = s.footprint_x if side in ("N", "S") else s.footprint_y
    for w in s.ext_walls:
        if w.wall == side and w.story == story:
            return sorted(round(round(o.pos * run / s.grid) * s.grid, 3) for o in w.openings)
    return []


def _storey(story, side, openings):
    return {"wall": side, "story": story, "openings": openings}


def _win(pos, **kw):
    return dict({"kind": "window", "pos": pos, "width": 1.4}, **kw)


def _building(ground, first, **extra):
    """A 40 x 20 m two-storey shell with one south face: `ground` and `first` are its openings."""
    d = {"name": "t", "footprint_x": 40.0, "footprint_y": 20.0, "n_stories": 2, "story_height": 3.5,
         "wall_thick": 0.3, "grid": 0.5, "ext_walls": [_storey(0, "S", ground), _storey(1, "S", first)]}
    d.update(extra)
    return d


# -- the library, read from its specs alone ----------------------------------------------------------------------

def test_deli_a01s_first_storey_east_window_stands_over_the_ground_floors():
    """The one window the rule moved in deli_a01: 5.5 m along the east wall, over nothing, to 7.0, over the ground
    floor's window."""
    d = _spec("deli_a01")
    assert _u(d, "E", 0) == [-7.0, 7.0]
    assert _u(d, "E", 1) == [7.0]


def test_bank_branch_a04s_front_is_stacked_and_still_mirrored():
    """Its south face: windows at 12 m either side of a centred main door, and upstairs a pair at 10 m that now stands
    over them."""
    d = _spec("bank_branch_a04")
    assert _u(d, "S", 0) == [-12.0, 0.0, 12.0]
    assert _u(d, "S", 1) == [-12.0, 12.0]


def test_the_corner_deli_preset_writes_the_composed_face():
    d = presets.make("corner_deli")
    assert _u(d, "E", 1) == [7.0]


def test_the_library_is_migrated_and_the_migration_is_idempotent():
    import migrate_facade_stack as M
    assert M.main(["--check"]) == 0


def test_the_empties_are_left_as_their_rows_wrote_them():
    """A rowhome's rear window stands in the other bay from its back door, on purpose."""
    for n, a in presets.EMPTY_ROWHOMES.items():
        assert _spec(n) == json.loads(json.dumps(presets.empty_rowhome(name=n, **a))), n


# -- the rows ----------------------------------------------------------------------------------------------------

def test_the_rowhome_row_is_the_presets_two_bays():
    import facade_plan as FP
    assert FP.bay_positions("rowhome", 6.0) == [-0.22, 0.22]
    assert FP.bay_positions("rowhome", 6.4) == [-0.22, 0.22]
    assert FP.bay_positions("rowhome", 5.8) == [-0.2, 0.2]


@pytest.mark.parametrize("width", [6.3, 15.0, 16.5, 18.0, 19.5, 21.0, 24.0])
def test_the_midrise_row_is_the_presets_bays(width):
    import facade_plan as FP
    bays = max(2, int(round(width / 3.2)))
    assert FP.bay_positions("midrise", width) == [round((i + 0.5) / bays - 0.5, 4) for i in range(bays)]
    assert presets.MIDRISE_BAY == FP.ROWS["midrise"]["bay_m"] == FP.REACH


def test_every_row_names_its_source():
    import facade_plan as FP
    assert all(r.get("source") for r in FP.ROWS.values())


# -- stack_mirrored ----------------------------------------------------------------------------------------------

def test_a_mirrored_pair_moves_together_onto_a_mirrored_pair_below():
    import facade_plan as FP
    d = _building([_win(-0.3), {"kind": "door", "pos": 0.0, "tag": "main_entry"}, _win(0.3)],
                  [_win(-0.25), _win(0.25)])
    moves, held = FP.stack_mirrored(d)
    assert sorted((m[2], m[3]) for m in moves) == [(-10.0, -12.0), (10.0, 12.0)]
    assert _u(d, "S", 1) == [-12.0, 12.0]
    assert held == []
    assert FP.stack_mirrored(d) == ([], [])          # a second run moves nothing


def test_a_pair_stays_when_the_ground_floor_offers_no_mirrored_pair():
    """Breaking the symmetry the upper storey was authored with is not this rule's to do."""
    import facade_plan as FP
    d = _building([_win(-0.3), _win(0.275)], [_win(-0.25), _win(0.25)])
    assert FP.stack_mirrored(d) == ([], [])
    assert _u(d, "S", 1) == [-10.0, 10.0]


def test_nothing_moves_further_than_a_bay():
    import facade_plan as FP
    d = _building([_win(-0.35), _win(0.35)], [_win(-0.25), _win(0.25)])     # 4 m away
    assert FP.stack_mirrored(d) == ([], [])


def test_the_ground_floor_and_tagged_windows_stay():
    import facade_plan as FP
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25, tag="upper_entry"), _win(0.25, tag="upper_entry")])
    assert FP.stack_mirrored(d) == ([], [])
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25), _win(0.25)])
    FP.stack_mirrored(d)
    assert _u(d, "S", 0) == [-12.0, 12.0]


def test_a_window_alone_moves_onto_the_nearest_opening_below():
    import facade_plan as FP
    d = _building([_win(-0.3), {"kind": "door", "pos": 0.1}], [_win(-0.25)])
    moves, _held = FP.stack_mirrored(d)
    assert [(m[2], m[3]) for m in moves] == [(-10.0, -12.0)]


def test_a_window_whose_mirror_stays_stays_with_it():
    """A tagged window or a held one keeps its mirrored partner where it is: moving one of the two alone would
    break the symmetry the storey was authored with."""
    import facade_plan as FP
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25, tag="upper_entry"), _win(0.25)])
    moves, held = FP.stack_mirrored(d)
    assert moves == [] and [h[3] for h in held] == ["its mirrored partner stays"]


def test_a_partition_junction_turns_a_target_down():
    """A room wall would stand in the window: the pair takes the next mirrored pair below, or stays."""
    import facade_plan as FP
    part = [{"story": 1, "axis": "Y", "pos": -12.0, "start": -10.0, "end": 0.0}]
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25), _win(0.25)], partitions=part)
    assert FP.stack_mirrored(d) == ([], [])


def test_a_draped_window_and_a_fire_escapes_wall_are_held():
    import facade_plan as FP
    drape = [{"name": "window_drape_s1_0", "x": -10.0, "y": -10.15, "z": 5.0, "size_x": 1.6, "size_y": 0.16,
              "size_z": 1.6}]
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25), _win(0.25)], volumes=drape)
    moves, held = FP.stack_mirrored(d)
    assert [h[3] for h in held] == ["a drape hangs over it", "its mirrored partner stays"] and moves == []
    fe = [{"id": "fe", "wall": "S", "served_stories": [1], "along": 0.0}]
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25), _win(0.25)], fire_escapes=fe)
    moves, held = FP.stack_mirrored(d)
    assert moves == [] and len(held) == 2


def test_an_empty_is_its_rows_and_is_not_touched():
    import facade_plan as FP
    d = _building([_win(-0.3), _win(0.3)], [_win(-0.25), _win(0.25)], facade=True)
    assert FP.stack_mirrored(d) == ([], [])
