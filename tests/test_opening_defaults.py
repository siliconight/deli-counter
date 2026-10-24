"""Roadmap item 46, step 4: bare openings get the values authors already
write by hand -- and nothing more.

`_derive_opening_defaults` runs once at spec load. The law is measured, not
invented: across every authored spec, windows are glass (16/16), a breach
panel's material is its host wall's (12/12), soft_wall sits on drywall
(10/10) and reinforceable on brick_ext (2/2). Authored values always win,
and an unknown material derives NOTHING -- a null stays honest where a
guess would lie.
"""
import interactives as I
from spec_loader import spec_from_dict


def _spec(ext_walls=None, partitions=None, **top):
    d = {"name": "t", "ext_walls": ext_walls or [], "partitions": partitions or []}
    d.update(top)
    return spec_from_dict(d)


def test_window_pane_is_glass():
    s = _spec(ext_walls=[{"wall": "N", "story": 0, "material": "brick_ext",
                          "openings": [{"kind": "window", "pos": 0.5}]}])
    assert s.ext_walls[0].openings[0].material == "glass"


def test_breach_inherits_the_host_wall():
    s = _spec(partitions=[{"story": 0, "axis": "X", "pos": 4.0,
                           "start": 0.0, "end": 8.0, "material": "drywall",
                           "openings": [{"kind": "breach", "pos": 0.5}]}])
    op = s.partitions[0].openings[0]
    assert op.material == "drywall"
    assert op.breach_class == "soft_wall"


def test_breach_in_hard_wall_is_reinforceable():
    s = _spec(ext_walls=[{"wall": "S", "story": 0, "material": "brick_ext",
                          "openings": [{"kind": "breach", "pos": 0.3}]}])
    op = s.ext_walls[0].openings[0]
    assert op.material == "brick_ext"
    assert op.breach_class == "reinforceable"


def test_palette_default_material_backs_a_bare_wall():
    s = _spec(default_material="concrete",
              partitions=[{"story": 0, "axis": "Y", "pos": 2.0,
                           "start": 0.0, "end": 6.0,
                           "openings": [{"kind": "breach", "pos": 0.5}]}])
    op = s.partitions[0].openings[0]
    assert op.material == "concrete"
    assert op.breach_class == "reinforceable"


def test_authored_values_always_win():
    s = _spec(ext_walls=[{"wall": "E", "story": 0, "material": "brick_ext",
                          "openings": [
                              {"kind": "breach", "pos": 0.2,
                               "material": "drywall",
                               "breach_class": "reinforceable"},
                              {"kind": "window", "pos": 0.7,
                               "material": "plexi"}]}])
    breach, window = s.ext_walls[0].openings
    assert breach.material == "drywall"           # author said so
    assert breach.breach_class == "reinforceable"  # author said so
    assert window.material == "plexi"


def test_unknown_material_derives_no_breach_class():
    s = _spec(ext_walls=[{"wall": "W", "story": 0, "material": "hullmetal",
                          "openings": [{"kind": "breach", "pos": 0.5}]}])
    op = s.ext_walls[0].openings[0]
    assert op.material == "hullmetal"     # inherited: it IS the wall
    assert op.breach_class is None        # but its yield is not guessed


def test_no_material_anywhere_stays_null():
    s = _spec(partitions=[{"story": 0, "axis": "X", "pos": 1.0,
                           "start": 0.0, "end": 4.0,
                           "openings": [{"kind": "breach", "pos": 0.5}]}])
    op = s.partitions[0].openings[0]
    assert op.material is None and op.breach_class is None


def test_doors_and_fixtures_stay_untouched():
    s = _spec(ext_walls=[{"wall": "N", "story": 0, "material": "brick_ext",
                          "openings": [{"kind": "door", "pos": 0.2},
                                       {"kind": "garage", "pos": 0.5},
                                       {"kind": "vault", "pos": 0.8}]}])
    for op in s.ext_walls[0].openings:
        assert op.material is None and op.breach_class is None


def test_machine_carries_the_advisories_to_the_netcode():
    m = I.derive_interactive("b", "ext_0_N", 0, "breach", 0.5,
                             material="drywall", breach_class="soft_wall")
    assert m["material"] == "drywall"
    assert m["breach_class"] == "soft_wall"
    entry = I.gameplay_interactive(m, "ext_0_N_open0",
                                   {"translation": [0, 0, 1.1], "rot_y": 0},
                                   building="b")
    assert entry["material"] == "drywall"
    assert entry["breach_class"] == "soft_wall"
    # windows too: the machine knows its pane shatters
    w = I.derive_interactive("b", "ext_0_S", 0, "window", 0.5,
                             breakable=True, material="glass")
    assert w["material"] == "glass"


def test_authored_override_beats_the_stamp():
    m = I.derive_interactive("b", "ext_0_N", 0, "breach", 0.5,
                             override={"material": "ballistic_panel"},
                             material="drywall", breach_class="soft_wall")
    assert m["material"] == "ballistic_panel"    # setdefault never clobbers
    assert m["breach_class"] == "soft_wall"


def test_slot_view_stays_art_only():
    m = I.derive_interactive("b", "ext_0_N", 0, "breach", 0.5,
                             material="drywall", breach_class="soft_wall")
    assert "material" not in I.slot_interactive(m)
