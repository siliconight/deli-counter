"""Pure tests for the stairwell Phase-5 advanced types (no bpy).
Run: python3 test_stair_phase5.py"""
import stairwell as S
from spec_types import LevelSpec, Stairwell, Room, ExtWall, Opening


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("STAIRWELL ", "") for m in msgs}


# --- facing + style footprints -----------------------------------------------

def test_facing_rotates_footprint():
    base = dict(x=0, y=0, from_story=0, to_story=1, width=1.2, run=5.0,
                style="straight")
    n = S.footprint_rect(Stairwell(**base, facing="N"))
    assert n == (-0.6, -2.5, 0.6, 2.5)           # pre-0.68 formula, unchanged
    e = S.footprint_rect(Stairwell(**base, facing="E"))
    assert e == (-2.5, -0.6, 2.5, 0.6)           # long axis now X
    s = S.footprint_rect(Stairwell(**base, facing="S"))
    assert s == (-0.6, -2.5, 0.6, 2.5)           # symmetric rect, same AABB
    w = S.footprint_rect(Stairwell(**base, facing="W"))
    assert w == (-2.5, -0.6, 2.5, 0.6)


def test_style_footprints():
    sw = S.footprint_rect(Stairwell(x=0, y=0, from_story=0, to_story=1,
                                    width=1.2, run=5.0, style="switchback"))
    sc = S.footprint_rect(Stairwell(x=0, y=0, from_story=0, to_story=1,
                                    width=1.2, run=5.0, style="scissor"))
    assert sw == sc == (-1.2, -2.5, 1.2, 2.5)    # same two-channel shaft
    sp = S.footprint_rect(Stairwell(x=0, y=0, from_story=0, to_story=1,
                                    width=1.5, style="spiral"))
    assert sp == (-1.5, -1.5, 1.5, 1.5)          # disc, width = radius
    l = S.footprint_rect(Stairwell(x=0, y=0, from_story=0, to_story=1,
                                   width=1.2, run=4.0, style="l_shaped"))
    assert l == (-0.6, -2.0, 4.6, 3.2)           # both legs + corner


def test_facing_east_stair_reviews_clean():
    sp = LevelSpec(name="s", n_stories=2, footprint_x=40, footprint_y=30,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                     width=1.2, run=5.0, style="straight",
                                     facing="E", id="a",
                                     role="primary_egress")],
                   rooms=[Room(id="hall", story=0, bounds=[-5, -3, 5, 3],
                               role="connector"),
                          Room(id="up", story=1, bounds=[-5, -3, 5, 3],
                               role="connector")],
                   ext_walls=[ExtWall(wall="S", story=0,
                                      openings=[Opening(kind="door",
                                                        pos=0.0)])])
    # room "hall" doesn't touch the S wall, so route the discharge via an
    # outdoor room the hall reaches -- simpler: hall spans to the wall
    sp.rooms[0] = Room(id="hall", story=0, bounds=[-5, -15, 5, 3],
                       role="connector")
    errors, _, _ = S.check(sp)
    assert errors == []


# --- spiral / scissor / roof --------------------------------------------------

def test_spiral_refuses_egress_role():
    sp = LevelSpec(name="s", n_stories=2,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=1,
                                     style="spiral", id="a",
                                     role="secondary_egress")])
    errors, _, _ = S.check(sp)
    assert "STAIR_STYLE_NOT_EGRESS_CAPABLE" in _codes(errors)
    sp.stairs[0].role = "service"
    errors, _, _ = S.check(sp)
    assert errors == []


def test_scissor_channels_and_congestion():
    sp = LevelSpec(name="s", n_stories=3,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=2,
                                     width=1.2, style="scissor")])
    sysd = S.derive(sp)[0]
    assert sysd["channels"] == 2
    assert sysd["gameplay"]["congestion"]["clear_width_m"] == 1.2  # per channel


def test_slab_termination_warns_and_roof_access_flag():
    sp = LevelSpec(name="s", n_stories=2,
                   stairs=[Stairwell(x=0, y=0, from_story=0, to_story=2,
                                     cut_slabs=False, id="a")])
    sysd = S.derive(sp)[0]
    assert sysd["roof_access"] is True           # tops out past story 1
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert "STAIR_TERMINATES_INTO_SLAB" in _codes(warnings)
    sp2 = LevelSpec(name="s", n_stories=3,
                    stairs=[Stairwell(x=0, y=0, from_story=0, to_story=2)])
    assert S.derive(sp2)[0]["roof_access"] is False


# --- exterior towers (s8.4) -----------------------------------------------------

def _tower(doors_on=(0, 1, 2)):
    """Three-story shell, tower standing off the E facade."""
    walls = []
    for s in doors_on:
        walls.append(ExtWall(wall="E", story=s,
                             openings=[Opening(kind="door", pos=0.05)]))
    for s in (0, 1, 2):
        if s not in doors_on:
            walls.append(ExtWall(wall="E", story=s,
                                 openings=[Opening(kind="window", pos=0.2)]))
    return LevelSpec(name="s", n_stories=3, footprint_x=40, footprint_y=30,
                     stairs=[Stairwell(x=22.5, y=0, from_story=0, to_story=2,
                                       width=1.2, run=4.0, id="tower",
                                       role="secondary_egress",
                                       exterior=True)],
                     rooms=[Room(id=f"floor{s}", story=s,
                                 bounds=[-20, -15, 20, 15], role="connector")
                            for s in (0, 1, 2)],
                     ext_walls=walls)


def test_exterior_tower_derives_site_discharge_and_doors():
    sysd = S.derive(_tower())[0]
    assert sysd["exterior"] is True
    assert sysd["approach"] == []                 # no interior approach
    d = sysd["discharge"]
    assert d["type"] == "exterior_tower" and d["destination"] == "site"
    floors = sorted(dn["floor"] for dn in sysd["door_nodes"])
    assert floors == [0, 1, 2]
    assert [dn for dn in sysd["door_nodes"] if dn["floor"] == 0][0][
        "discharge_door"] is True
    assert all(dn["wall"].startswith("ext_") for dn in sysd["door_nodes"])


def test_exterior_tower_reviews_clean_with_doors():
    errors, _, _ = S.check(_tower())
    assert errors == []                           # no corridor/approach noise


def test_exterior_tower_missing_floor_door_gates():
    errors, _, _ = S.check(_tower(doors_on=(0, 2)))
    assert "EXTERIOR_TOWER_NO_DOOR" in _codes(errors)
    assert any("story 1" in e for e in errors)


# --- transfer floors (Rule 2 relaxation) -------------------------------------------

def _transfer(rooms):
    return LevelSpec(name="s", n_stories=3, footprint_x=40, footprint_y=30,
                     stairs=[Stairwell(x=-5, y=0, from_story=0, to_story=1,
                                       id="lo", stack_id="core",
                                       style="straight"),
                             Stairwell(x=5, y=0, from_story=1, to_story=2,
                                       id="hi", stack_id="core",
                                       style="straight", transfer=True)],
                     rooms=rooms)


def test_declared_transfer_with_walkable_floor_is_clean():
    sp = _transfer([Room(id="hall1", story=1, bounds=[-10, -5, 10, 5],
                         role="connector")])
    errors, _, _ = S.check(sp)
    assert errors == []
    systems = S.derive(sp)
    assert systems[0]["transfer_floor"] == 1
    assert systems[1]["transfer_floor"] == 1


def test_declared_transfer_with_unwalkable_floor_gates():
    sp = _transfer([Room(id="ra", story=1, bounds=[-10, -5, -2, 5]),
                    Room(id="rb", story=1, bounds=[2, -5, 10, 5])])
    errors, _, _ = S.check(sp)
    assert "STAIR_NOT_STACKED" in _codes(errors)
    assert any("unconnected rooms" in e for e in errors)


def test_declared_transfer_without_rooms_warns_accepted():
    sp = _transfer([])
    errors, warnings, _ = S.check(sp)
    assert errors == []
    assert any("accepted as declared" in w for w in warnings)


def test_undeclared_lateral_shift_still_gates():
    sp = _transfer([Room(id="hall1", story=1, bounds=[-10, -5, 10, 5])])
    sp.stairs[1].transfer = False
    errors, _, _ = S.check(sp)
    assert "STAIR_NOT_STACKED" in _codes(errors)
    assert any("transfer: true" in e for e in errors)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all stair phase5 tests passed")
