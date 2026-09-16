"""The back of a flight is filled flush with its side walls (0.134.0).

The walker, cold run 9057, in `bank_branch_a02`'s basement: a slot 1.61 m
wide, 0.8 m deep and a storey tall stood between the east stair's side walls
behind the top of the flight -- "we will this in so the back is flush with
it's self". Pure geometry over `stairwell.stair_guards`; no bpy. Frame: the
building plan, metres. Run: python test_stair_back.py

0.138.0 -- THE OTHER RUN, NOT THE RECTANGLE. 0.134.0 excluded every
multi-storey switchback because "its second run is an open walkway under the
next leg, open to the room at both ends". Measured in `office_stepped`'s
0.137.0 glb (the walker, cold run 9060, "hole behind this stair and to the
side"): the walkway is that ONE run -- x -1.600..0.000 -- and the leg's own
half of the rectangle holds the same dead-end slot the rule was written for,
at x 0.000..1.605, y 2.089..3.150, floor to slab underside. So the fill now
covers the leg's own run and stops at the run boundary, and the slot behind
a leg that ends in a TURN LANDING is a step deeper than `run / 2` says,
because that leg is built one tread shorter.
"""
import glob
import os

import agent_contract
import spec_loader
import stairwell as S
from spec_types import LevelSpec, Opening, Partition, Stairwell

HERE = os.path.dirname(os.path.abspath(__file__))


def _library_specs():
    """The library's specs, not Level Factory's output beside them.

    `specs/lf_*.json` are levels Level Factory generates into this folder
    (gitignored). A checkout that has hosted a cold run holds hundreds: the
    exact census below read 291 flights instead of 130 in the factory
    checkout, and passed in the worktree it was written in, which had none."""
    return [p for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
            if not os.path.basename(p).startswith("lf_")]


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _load(name):
    return spec_loader.load_spec(os.path.join(HERE, "specs", name + ".json"))


def _rect(p):
    h = p.get("thick", S.GUARD_THICK) / 2.0
    if p["axis"] == "Y":
        return (p["pos"] - h, p["lo"], p["pos"] + h, p["hi"])
    return (p["lo"], p["pos"] - h, p["hi"], p["pos"] + h)


def _overlap_area(a, b):
    return (max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            * max(0.0, min(a[3], b[3]) - max(a[1], b[1])))


def _shell(*stairs, **kw):
    base = dict(name="s", n_stories=3, footprint_x=30, footprint_y=24,
                stairs=list(stairs))
    base.update(kw)
    return LevelSpec(**base)


def _straight(**kw):
    base = dict(x=0.0, y=0.0, from_story=0, to_story=1, width=1.6, run=4.7,
                style="straight", id="a")
    base.update(kw)
    return Stairwell(**base)


def _pocket(spec, st, s):
    """The slot a flight's side walls leave behind its top on storey `s`:
    from the rectangle's arrival edge to the top tread, between the side
    walls' inner faces. `None` for a flight that tops out at the high end
    of neither axis (never, for straight / switchback)."""
    x0, y0, x1, y1 = S.flight_rect(st, s)
    travel = "Y" if (st.facing or "N") in ("N", "S") else "X"
    t_lo, t_hi = (y0, y1) if travel == "Y" else (x0, x1)
    l_lo, l_hi = (x0, x1) if travel == "Y" else (y0, y1)
    tx, ty = S._stair_pt(st, st.x, st.y + st.run / 2.0)
    t_top = ty if travel == "Y" else tx
    arrive_hi = abs(t_top - t_hi) < abs(t_top - t_lo)
    narrow = st.width < agent_contract.min_corridor_width() - 1e-9
    inner = 0.0 if narrow else S.SIDE_MARGIN - S.SIDE_GAP
    t = (t_top, t_hi) if arrive_hi else (t_lo, t_top)
    l_ = (l_lo + inner, l_hi - inner)
    return ((l_[0], t[0], l_[1], t[1]) if travel == "Y"
            else (t[0], l_[0], t[1], l_[1]))


# --- the walker's stair ----------------------------------------------------

def test_the_walkers_stair_gets_one_back_flush_with_its_walls():
    sp = _load("bank_branch_a02")
    g = S.stair_guards(sp)
    backs = [p for p in g if p["stair"] == "a02_stair_e" and p["kind"] == "back"]
    assert len(backs) == 1, backs
    b = backs[0]
    assert b["story"] == -1 and b["axis"] == "Y", b
    x0, y0, x1, y1 = _rect(b)
    # from the rectangle's arrival edge to the flight's top end, less the
    # SIDE_GAP the side walls also keep from the treads
    assert abs(x0 - 7.85) < 1e-9 and abs(x1 - (8.65 - S.SIDE_GAP)) < 1e-9, b
    # between the side walls' inner faces, touching both
    sides = [p for p in g if p["stair"] == "a02_stair_e" and p["kind"] == "side"]
    inner = sorted([_rect(p)[3] for p in sides if p["pos"] < -6.0]
                   + [_rect(p)[1] for p in sides if p["pos"] > -6.0])
    assert abs(y0 - inner[0]) < 1e-9 and abs(y1 - inner[1]) < 1e-9, (b, inner)
    assert abs(y0 - -6.805) < 1e-9 and abs(y1 - -5.195) < 1e-9, b
    # ...so at the room-side face, x = 7.85, walls and fill are one face
    # from one wall's outer face to the other's
    at_face = sorted((_rect(p)[1], _rect(p)[3]) for p in sides + backs
                     if _rect(p)[0] <= 7.85 + 1e-9)
    assert abs(at_face[0][0] - -7.2) < 1e-9 and abs(at_face[-1][1] - -4.8) < 1e-9
    for (a0, a1), (c0, c1) in zip(at_face, at_face[1:]):
        assert abs(a1 - c0) < 1e-9, at_face


def test_the_west_stair_of_the_same_bank_gets_one_too():
    sp = _load("bank_branch_a02")
    backs = [p for p in S.stair_guards(sp)
             if p["stair"] == "a02_stair_w" and p["kind"] == "back"]
    assert len(backs) == 1 and backs[0]["story"] == -1, backs


# --- the library -----------------------------------------------------------

#: One-run solid flights whose slot is closed by something other than a back,
#: and what closes it. `credit_union_a02`: its ground-floor partition at
#: y = 3.0 stands across the slot's mouth (strip y 2.85..3.15 of 3.0..3.8),
#: so what is left is sealed on all sides.
_CLOSED_OTHERWISE = {("credit_union_a02", "cu02_stair_0", 0)}


def test_no_slot_remains_behind_any_one_run_solid_flight_in_the_library():
    open_ = []
    n = 0
    for path in _library_specs():
        name = os.path.basename(path)[:-5]
        sp = spec_loader.load_spec(path)
        guards = S.stair_guards(sp)
        for i, st in enumerate(sp.stairs or ()):
            sid = S.stair_ident(st, i)
            if st.style != "straight" and not S.single_run(st):
                continue
            lo = min(st.from_story, st.to_story)
            hi = max(st.from_story, st.to_story)
            for s in range(lo, hi):
                if not any(p["stair"] == sid and p["story"] == s
                           and p["kind"] == "side" for p in guards):
                    continue
                if not S.flight_solid_under(sp, st, s):
                    continue
                n += 1
                pocket = _pocket(sp, st, s)
                area = (pocket[2] - pocket[0]) * (pocket[3] - pocket[1])
                filled = sum(_overlap_area(_rect(p), pocket) for p in guards
                             if p["stair"] == sid and p["story"] == s
                             and p["kind"] == "back")
                # the fill stops SIDE_GAP short of the treads, and a volume
                # may trim a guard's T padding off one end
                if filled < 0.98 * area:
                    open_.append((name, sid, s))
    assert n == 131, n
    assert set(open_) == _CLOSED_OTHERWISE, sorted(open_)


def test_a_back_never_shares_space_with_the_flight_or_its_walls():
    """Contact, never interpenetration: `zfight_gate` flags two solids in one
    place with a coplanar face, and a back through a side wall would have
    three. Inside the reserved rectangle, outside the treads, and under the
    discharge plate (step_h below the cap it stops at).

    Against `flight_solid_rect`, not `footprint_rect`: the second is the air
    a switchback RESERVES, both runs and the full run length, and a
    multi-storey leg fills neither -- it stands in one run and stops a tread
    short of the run's end, under a turn landing that is at the top of the
    storey and not on its floor. For every one-run flight the two rects are
    the same rect, which the next test asserts.
    """
    for path in _library_specs():
        sp = spec_loader.load_spec(path)
        guards = S.stair_guards(sp)
        H = sp.story_height
        for i, st in enumerate(sp.stairs or ()):
            sid = S.stair_ident(st, i)
            for b in [p for p in guards if p["stair"] == sid
                      and p["kind"] == "back"]:
                r = _rect(b)
                fr = S.flight_rect(st, b["story"])
                assert (r[0] >= fr[0] - 1e-9 and r[1] >= fr[1] - 1e-9
                        and r[2] <= fr[2] + 1e-9 and r[3] <= fr[3] + 1e-9), (path, b)
                solid = S.flight_solid_rect(st, H, b["story"])
                assert _overlap_area(r, solid) < 1e-9, (path, b, solid)
                for p in guards:
                    if p is not b and p["story"] == b["story"]:
                        assert _overlap_area(r, _rect(p)) < 1e-9, (path, b, p)
                cap = ((sp.roof_thick or sp.floor_thick)
                       if b["story"] + 1 == sp.n_stories else sp.floor_thick)
                assert H / S._step_count(st, H) < cap, (path, b)


# --- scope -------------------------------------------------------------------

def test_a_narrow_flight_is_filled_between_its_thin_guards():
    st = _straight(width=0.9)
    assert st.width < agent_contract.min_corridor_width()
    sp = _shell(st)
    backs = [p for p in S.stair_guards(sp) if p["kind"] == "back"]
    assert len(backs) == 1, backs
    x0, _y0, x1, _y1 = S.flight_rect(st, 0)
    assert abs(backs[0]["lo"] - x0) < 1e-9 and abs(backs[0]["hi"] - x1) < 1e-9


def test_scissors_and_open_undersides_get_no_back():
    """A scissor arrives at both ends and its walls stop short of each; an
    open underside has no walls to be flush with."""
    for st in (_straight(style="scissor"), _straight(open_under=True)):
        sp = _shell(st)
        assert not [p for p in S.stair_guards(sp) if p["kind"] == "back"], st


# --- the multi-storey switchback (0.138.0) ---------------------------------

def _runs(st, s):
    """(the leg's own run, the other run) as world lateral intervals."""
    own = S.flight_run_lateral(st, s)
    x0, y0, x1, y1 = S.flight_rect(st, s)
    l_lo, l_hi = ((x0, x1) if (st.facing or "N") in ("N", "S") else (y0, y1))
    w = own[1] - own[0]
    other = ((own[0] - w, own[0]) if own[0] + own[1] > l_lo + l_hi
             else (own[1], own[1] + w))
    return own, other


def test_the_walkers_stair_gets_a_back_in_its_own_run_only():
    """`office_stepped`, cold run 9060. Leg 0 climbs storey 0 in the run
    x 0.000..1.600 and its top tread ends at y 2.089; the slot behind it runs
    to the rectangle's arrival edge at y 3.150 and out to the east side wall's
    inner face at x 1.605. The run at x -1.600..0.000 is the walkway and keeps
    every metre of it."""
    sp = _load("office_stepped")
    st = sp.stairs[0]
    backs = [p for p in S.stair_guards(sp) if p["kind"] == "back"]
    assert [p["story"] for p in backs] == [0], backs
    b = backs[0]
    x0, y0, x1, y1 = _rect(b)
    assert abs(x0 - 0.0) < 1e-9 and abs(x1 - 1.605) < 1e-9, b
    assert abs(y0 - (2.088889 + S.SIDE_GAP)) < 1e-6, b     # the top TREAD
    assert abs(y1 - 3.15) < 1e-9, b
    # and it is a step deeper than the run's end would have made it
    assert abs(y0 - (st.y + st.run / 2.0 + S.SIDE_GAP)) > 0.25, b
    # flush with the east side wall, which starts exactly where it stops
    east = [p for p in S.stair_guards(sp) if p["kind"] == "side"
            and p["story"] == 0 and p["pos"] > 0]
    assert len(east) == 1 and abs(_rect(east[0])[0] - x1) < 1e-9, east


def test_the_walkway_under_the_next_leg_keeps_both_its_mouths():
    """The run the NEXT leg flies over carries no fill on any storey, in any
    multi-storey switchback in the library -- that is the channel 0.134.0
    protected and the reason this rule is per-run and not per-rectangle."""
    n = 0
    for path in _library_specs():
        sp = spec_loader.load_spec(path)
        guards = S.stair_guards(sp)
        for i, st in enumerate(sp.stairs or ()):
            if st.style != "switchback" or S.single_run(st):
                continue
            sid = S.stair_ident(st, i)
            lo = min(st.from_story, st.to_story)
            hi = max(st.from_story, st.to_story)
            for s in range(lo, hi):
                n += 1
                _own, other = _runs(st, s)
                for b in [p for p in guards if p["stair"] == sid
                          and p["story"] == s and p["kind"] == "back"]:
                    assert min(b["hi"], other[1]) - max(b["lo"], other[0]) \
                        < 1e-9, (path, sid, s, b, other)
    assert n == 41, n


#: Multi-storey switchback legs that could carry a back and do not, and what
#: refuses each. Both are the EXTERIOR-WALL arm of `covered_by_walls`, which
#: pre-dates 0.138.0 and is why 129 of the 130 one-run flights carry one:
#: the slot's far end IS the exterior wall, so the wall lands inside the
#: back's `band` and the piece reads as already covered. Not touched here --
#: changing it would move the one-run flights too, and that is its own
#: measurement.
_MULTI_REFUSED_BY_A_WALL = {
    ("foundry_heist_vertical", "foundry_heist_vertical_stair_0", -1),
    ("primos_pizza", "primos_pizza_stair_0", -1),
}


def test_every_multi_storey_switchback_leg_is_accounted_for():
    """34 legs can carry a back: 17 leg 0s and 17 leg 1s. A leg 1 stands on
    the slab leg 0 cut, and `back_only` refuses a back over an opening, so
    all 17 go. Of the 17 leg 0s, 15 carry one and 2 are refused by a wall."""
    cand, got, refused = 0, 0, set()
    legs = {0: 0, 1: 0}
    for path in _library_specs():
        name = os.path.basename(path)[:-5]
        sp = spec_loader.load_spec(path)
        guards = S.stair_guards(sp)
        for i, st in enumerate(sp.stairs or ()):
            if st.style != "switchback" or S.single_run(st):
                continue
            sid = S.stair_ident(st, i)
            lo = min(st.from_story, st.to_story)
            hi = max(st.from_story, st.to_story)
            for s in range(lo, hi):
                if not S.flight_solid_under(sp, st, s):
                    continue
                if not any(p["stair"] == sid and p["story"] == s
                           and p["kind"] == "side" for p in guards):
                    continue
                cand += 1
                legs[s - lo] = legs.get(s - lo, 0) + 1
                if any(p["stair"] == sid and p["story"] == s
                       and p["kind"] == "back" for p in guards):
                    got += 1
                elif s - lo == 0:
                    refused.add((name, sid, s))
    assert cand == 34 and legs == {0: 17, 1: 17}, (cand, legs)
    assert got == 15, got
    assert refused == _MULTI_REFUSED_BY_A_WALL, sorted(refused)


def test_no_leg_above_the_first_is_filled_over_the_hole_below_it():
    """A leg 1's slot is 0.5 m of floor and 0.295 m of the hole leg 0 cut
    (`flight_rect` puts the two rectangles 0.5 m apart along travel), and a
    back must stand on floor. Every one of the 17 is refused."""
    for path in _library_specs():
        sp = spec_loader.load_spec(path)
        guards = S.stair_guards(sp)
        for i, st in enumerate(sp.stairs or ()):
            if st.style != "switchback" or S.single_run(st):
                continue
            sid = S.stair_ident(st, i)
            lo = min(st.from_story, st.to_story)
            for b in [p for p in guards if p["stair"] == sid
                      and p["kind"] == "back"]:
                assert b["story"] == lo, (path, b)


def test_a_one_run_flights_solid_is_its_footprint_exactly():
    """`flight_solid_rect` is the new rect the containment check uses. For
    every flight that tops out at its run's end it must BE `footprint_rect`,
    so nothing a one-run flight ships has moved."""
    n = 0
    for path in _library_specs():
        sp = spec_loader.load_spec(path)
        for st in sp.stairs or ():
            if st.style not in ("straight", "switchback") or not S.single_run(st) \
                    and st.style != "straight":
                continue
            lo = min(st.from_story, st.to_story)
            hi = max(st.from_story, st.to_story)
            for s in range(lo, hi):
                n += 1
                a = S.flight_solid_rect(st, sp.story_height, s)
                b = S.footprint_rect(st)
                assert all(abs(u - v) < 1e-9 for u, v in zip(a, b)), (path, a, b)
    assert n >= 130, n


def test_a_single_storey_switchback_is_one_run_and_gets_a_back():
    sp = _shell(_straight(style="switchback"))
    assert len([p for p in S.stair_guards(sp) if p["kind"] == "back"]) == 1


def test_a_multi_storey_straight_flight_is_filled_on_its_bottom_storey_only():
    """Above the bottom leg, the slot's floor is the discharge plate of the
    flight below -- that flight's way off."""
    sp = _shell(_straight(to_story=2))
    backs = [p for p in S.stair_guards(sp) if p["kind"] == "back"]
    assert [p["story"] for p in backs] == [0], backs


def test_a_door_facing_the_slot_keeps_its_approach():
    """A wall across the slot's mouth with a door in it: the back stops
    `DOOR_APPROACH_M` clear of the wall over the aperture."""
    import layout_lint
    st = _straight()                           # N: arrives at y = +2.35
    _x0, _y0, _x1, y1 = S.flight_rect(st, 0)
    wall = Partition(story=0, axis="X", pos=y1 + 0.4, start=-15.0, end=15.0,
                     openings=[Opening(kind="door", pos=0.0, width=1.0)])
    sp = _shell(st, partitions=[wall])
    backs = [p for p in S.stair_guards(sp) if p["kind"] == "back"]
    # the door's aperture x -0.5..0.5 reaches 1.0 m past a wall 0.4 m past
    # the rectangle, over the whole slot's depth: that span is cut
    assert layout_lint.DOOR_APPROACH_M > 0.4
    for b in backs:
        assert b["hi"] <= -0.5 - S.GUARD_THICK + 1e-9 or \
            b["lo"] >= 0.5 + S.GUARD_THICK - 1e-9, b
    # and the rest of the slot, either side of the approach, is still filled
    assert sorted((round(b["lo"], 6), round(b["hi"], 6)) for b in backs) == [
        (-0.805, -0.6), (0.6, 0.805)], backs


def test_a_door_that_faces_a_side_wall_takes_nothing_from_the_back():
    """`strip_retail_a01` `sr01_stair_up`: `dining_rear` at y = 1.0 faces the
    side wall at y 1.3..1.695, and reaches the back only through it."""
    sp = _load("strip_retail_a01")
    backs = [p for p in S.stair_guards(sp)
             if p["stair"] == "sr01_stair_up" and p["kind"] == "back"]
    assert len(backs) == 1, backs
    assert abs(backs[0]["lo"] - 1.695) < 1e-9, backs


def test_the_containment_review_does_not_count_a_back():
    """A back stands at a mouth, behind the treads. The review asks whether a
    flight's SIDES are closed and its mouths open; its answers are the same
    with the backs taken away."""
    sp = _load("bank_branch_a02")
    real = S.stair_guards
    with_backs = {S.stair_ident(st, i): S.containment_findings(
        sp, st, S.stair_ident(st, i)) for i, st in enumerate(sp.stairs)}
    try:
        S.stair_guards = lambda spec: [p for p in real(spec)
                                       if p["kind"] != "back"]
        without = {S.stair_ident(st, i): S.containment_findings(
            sp, st, S.stair_ident(st, i)) for i, st in enumerate(sp.stairs)}
    finally:
        S.stair_guards = real
    assert with_backs == without


ALL = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for fn in ALL:
        _run(fn)
    print(f"\n{len(ALL)} stair back tests passed.")
