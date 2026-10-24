"""Pure tests for ladder Phase 5 (legacy fire escapes, no bpy).
Run: python3 test_ladder_fire_escape.py"""
import ladder as L
from spec_types import (LevelSpec, Ladder, Room, FireEscape, ExtWall, Opening,
                        Volume)


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _codes(msgs):
    return {m.split(":")[0].replace("LADDER ", "") for m in msgs}


def _rowhouse(fe_kw=None, ladder_kw=None, with_windows=True):
    """Historic 3-story building with a rear (N) fire escape + drop ladder."""
    fk = dict(id="rear_fe", wall="N", served_stories=[1, 2],
              termination="drop_ladder", access="window")
    if fe_kw:
        fk.update(fe_kw)
    lk = dict(x=0, y=10.5, from_story=0, to_story=1, facing="S", id="dl",
              role="fire_escape_termination", placement_mode="exterior_wall",
              lower_surface="grade", upper_surface="rear_fe",
              direction="deploy_then_bidirectional", access_class="emergency",
              transition="fire_escape_platform_entry", fire_escape_id="rear_fe",
              access_control="removable_section",
              counts_as_secondary_escape=True)
    if ladder_kw:
        lk.update(ladder_kw)
    walls = []
    if with_windows:
        walls = [ExtWall(wall="N", story=1,
                         openings=[Opening(kind="window", pos=0.0)]),
                 ExtWall(wall="N", story=2,
                         openings=[Opening(kind="window", pos=0.0)])]
    return LevelSpec(
        name="row", n_stories=3, story_height=3.5, footprint_x=12,
        footprint_y=20,
        fire_escapes=[FireEscape(**fk)],
        ladders=[Ladder(**lk)],
        rooms=[Room(id="apt1", story=1, bounds=[-6, -10, 6, 10],
                    role="connector"),
               Room(id="apt2", story=2, bounds=[-6, -10, 6, 10],
                    role="connector")],
        ext_walls=walls)


# --- system resolution --------------------------------------------------------

def test_fire_escape_is_a_surface():
    sp = _rowhouse()
    assert L._fire_escape_by_id(sp, "rear_fe") is not None
    assert L._surface_valid(sp, "rear_fe", 1) is True
    assert L._surface_story(sp, "rear_fe", 0) == 1     # lowest served


def test_drop_ladder_pins_to_lowest_balcony():
    sp = _rowhouse()
    d = L.derive(sp)[0]
    # ladder climbs grade -> lowest balcony (story 1 at 3.5 m)
    assert d["upper_anchor"][2] == 3.5
    assert d["climb_height_m"] == 3.5


def test_clean_fire_escape_passes():
    sp = _rowhouse()
    errors, warnings, _ = L.check(sp)
    assert errors == []
    # the only expected warning is the legacy-profile advisory
    assert "LEGACY_FIRE_ESCAPE_PROFILE" in _codes(warnings)


# --- orphan check (Rule 14) ---------------------------------------------------

def test_ladder_with_missing_system_orphaned():
    sp = _rowhouse(ladder_kw={"fire_escape_id": "ghost",
                              "upper_surface": "roof"})
    errors, _, _ = L.check(sp)
    assert "FIRE_ESCAPE_LADDER_ORPHANED" in _codes(errors)


def test_fire_escape_termination_without_id_orphaned():
    sp = _rowhouse(ladder_kw={"fire_escape_id": None, "upper_surface": "roof",
                              "counts_as_secondary_escape": False})
    errors, _, _ = L.check(sp)
    assert "FIRE_ESCAPE_LADDER_ORPHANED" in _codes(errors)


def test_empty_system_orphaned():
    sp = _rowhouse(fe_kw={"served_stories": []})
    errors, _, _ = L.check(sp)
    assert "FIRE_ESCAPE_LADDER_ORPHANED" in _codes(errors)


# --- deployment clearance (s9.4) ----------------------------------------------

def test_drop_ladder_onto_dumpster_gates():
    sp = _rowhouse()
    sp.volumes = [Volume(name="dumpster", x=0, y=10.5, z=1.0,
                         size_x=2, size_y=2, size_z=1.5)]
    errors, _, _ = L.check(sp)
    assert "DROP_LADDER_NO_DEPLOYMENT_CLEARANCE" in _codes(errors)


def test_clear_base_ok():
    sp = _rowhouse()
    sp.volumes = [Volume(name="planter", x=5, y=10.5, z=0.3,
                         size_x=1, size_y=1, size_z=0.6)]
    errors, _, _ = L.check(sp)
    assert "DROP_LADDER_NO_DEPLOYMENT_CLEARANCE" not in _codes(errors)


# --- deploy direction (s3.7 / s13.2) ------------------------------------------

def test_drop_ladder_wrong_direction_warns():
    sp = _rowhouse(ladder_kw={"direction": "bidirectional"})
    _, warnings, _ = L.check(sp)
    assert any("deploy_then_bidirectional or" in w for w in warnings)


def test_deploy_direction_ok():
    sp = _rowhouse()   # deploy_then_bidirectional
    _, warnings, _ = L.check(sp)
    assert not any("deploy_then_bidirectional or" in w for w in warnings)


# --- access opening (s9.2) ----------------------------------------------------

def test_no_access_opening_warns():
    sp = _rowhouse(with_windows=False)
    _, warnings, _ = L.check(sp)
    assert any("no window opening" in w for w in warnings)


def test_access_opening_present_ok():
    sp = _rowhouse()   # windows on N wall at both served stories
    _, warnings, _ = L.check(sp)
    assert not any("no window opening" in w for w in warnings)


# --- termination reaching grade (s9.1 step 8) ---------------------------------

def test_unlinked_drop_ladder_termination_warns():
    # a fire escape declaring drop_ladder but with no ladder linking to it
    sp = _rowhouse()
    sp.ladders = []            # remove the linking drop ladder
    _, warnings, _ = L.check(sp)
    assert any("no ladder links to it" in w for w in warnings)


def test_stair_termination_needs_no_ladder():
    sp = _rowhouse(fe_kw={"termination": "stair_to_grade"})
    sp.ladders = []
    _, warnings, _ = L.check(sp)
    assert not any("no ladder links to it" in w for w in warnings)


# --- egress classification (s2 / s13.3) ---------------------------------------

def test_fire_escape_ladder_counts_as_secondary_escape():
    sp = _rowhouse()
    d = L.derive(sp)[0]
    assert d["egress_classification"] == "fire_escape_termination"
    assert d["counts_as_secondary_escape"] is True
    assert d["counts_as_primary_egress"] is False
    assert d["counts_as_public_circulation"] is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all ladder fire-escape tests passed")
