"""Tests for interactive-fixture derivation (pure -- no Blender).

Run:  python -m pytest test_interactives.py    (or: python test_interactives.py)
"""
import interactives as I


# --- inference by opening kind ---------------------------------------------

def test_door_is_inferred_interactive():
    m = I.derive_interactive("b", "ext_0_N", 0, "door", 0.0)
    assert m["kind"] == "door"
    assert m["states"] == ["closed", "open"]
    assert m["default"] == "closed"
    assert m["source"] == "inferred"
    # toggle both ways
    events = {(t["from"], t["to"]) for t in m["transitions"]}
    assert events == {("closed", "open"), ("open", "closed")}


def test_garage_infers_a_door():
    m = I.derive_interactive("b", "ext_0_N", 0, "garage", 0.0)
    assert m["kind"] == "door"


def test_breach_is_a_breachable_wall_with_state_geometry():
    m = I.derive_interactive("b", "ext_0_N", 0, "breach", 0.0)
    assert m["kind"] == "breach_wall"
    assert m["states"] == ["intact", "breached"]
    assert m["default"] == "intact"
    # the reframe: intact is a wall, breached is breach geometry
    assert m["state_geometry"] == {"intact": "wall", "breached": "breach"}
    assert m["reversible"] is False
    assert [t["event"] for t in m["transitions"]] == ["breach"]


def test_window_not_interactive_unless_breakable():
    assert I.derive_interactive("b", "ext_0_S", 0, "window", 0.0) is None
    m = I.derive_interactive("b", "ext_0_S", 0, "window", 0.0, breakable=True)
    assert m["kind"] == "window"
    assert m["states"] == ["intact", "broken"]


# --- vault door: a hero portal, closed by default --------------------------

def test_vault_is_inferred_as_a_vault_door():
    m = I.derive_interactive("gs_bank", "ext_0_N", 0, "vault", 0.0)
    assert m["kind"] == "vault_door"
    assert m["states"] == ["locked", "unlocked", "open", "breached"]
    assert m["default"] == "locked"          # closed by default
    # the closed door is its own art; open/breached reuse doorway/breach
    assert m["state_geometry"] == {
        "locked": "vault_door", "unlocked": "vault_door",
        "open": "doorway", "breached": "breach"}


def test_vault_can_be_breached_from_either_closed_state():
    m = I.derive_interactive("gs_bank", "ext_0_N", 0, "vault", 0.0)
    breach = {(t["from"], t["to"]) for t in m["transitions"]
              if t["event"] == "breach"}
    assert breach == {("locked", "breached"), ("unlocked", "breached")}
    # the lock/open cycle is reachable both ways
    events = {t["event"] for t in m["transitions"]}
    assert {"unlock", "lock", "open", "close", "breach"} == events


def test_vault_slot_view_carries_the_state_geometry_for_zoo():
    m = I.derive_interactive("gs_bank", "ext_0_N", 0, "vault", 0.0)
    sv = I.slot_interactive(m)
    assert sv["kind"] == "vault_door"
    assert sv["state_geometry"]["open"] == "doorway"
    assert sv["state_geometry"]["breached"] == "breach"
    # closed states block, open/breached don't (advisory)
    assert sv["collision_per_state"] == {
        "locked": True, "unlocked": True, "open": False, "breached": False}


# --- teller line + safe deposit boxes: solid barriers, one break state -----

def test_teller_is_inferred_as_a_teller_window():
    m = I.derive_interactive("gs_bank", "int_0_2", 0, "teller", 0.0)
    assert m["kind"] == "teller_window"
    assert m["states"] == ["intact", "shattered"]
    assert m["default"] == "intact"
    assert [t["event"] for t in m["transitions"]] == ["shatter"]
    # intact blocks, shattered is passable (advisory); no state_geometry ->
    # shattered reuses the teller_line art (Zoo defers it)
    assert "state_geometry" not in m
    assert m["collision_per_state"] == {"intact": True, "shattered": False}


def test_safe_deposit_is_inferred_as_a_box_wall():
    m = I.derive_interactive("gs_bank", "int_-1_0", -1, "safe_deposit", 0.2)
    assert m["kind"] == "safe_deposit_boxes"
    assert m["states"] == ["intact", "drilled"]
    assert [t["event"] for t in m["transitions"]] == ["drill"]
    # the wall stays solid in both states (per-box loot is gameplay's job)
    assert m["collision_per_state"] == {"intact": True, "drilled": True}


def test_teller_and_safe_deposit_get_stable_ids_and_slot_views():
    for kind in ("teller", "safe_deposit"):
        m = I.derive_interactive("gs_bank", "int_0_1", 0, kind, 0.1)
        sv = I.slot_interactive(m)
        gv = I.gameplay_interactive(m, "int_0_1_open0",
                                    {"translation": [1, 2, 1], "rot_y": 0})
        assert sv["id"] == gv["id"] == m["id"]
        assert "state_geometry" not in sv     # both defer to the base species
        assert gv["transitions"]


# --- authored override ------------------------------------------------------

def test_override_false_forces_non_interactive():
    assert I.derive_interactive("b", "ext_0_N", 0, "door", 0.0,
                                override=False) is None


def test_override_dict_merges_over_inference():
    m = I.derive_interactive(
        "b", "ext_0_N", 0, "door", 0.0,
        override={"states": ["closed", "ajar", "open"]})
    assert m["states"] == ["closed", "ajar", "open"]
    assert m["kind"] == "door"          # kept from inference
    assert m["source"] == "authored"


def test_override_dict_can_make_a_plain_window_interactive():
    m = I.derive_interactive(
        "b", "ext_0_S", 0, "window", 0.0,
        override={"kind": "window", "states": ["intact", "broken"],
                  "default": "intact"})
    assert m is not None and m["kind"] == "window"


# --- stable ids -------------------------------------------------------------

def test_id_is_deterministic_and_position_stable():
    a = I.interactive_id("gs_vault", "ext_0_N", 0, "door", 0.0)
    b = I.interactive_id("gs_vault", "ext_0_N", 0, "door", 0.0)
    assert a == b                       # same place -> same id
    assert a.startswith("gs_vault:if:")


def test_id_changes_when_the_fixture_moves_or_differs():
    base = I.interactive_id("gs_vault", "ext_0_N", 0, "door", 0.0)
    assert base != I.interactive_id("gs_vault", "ext_0_N", 0, "door", 0.25)
    assert base != I.interactive_id("gs_vault", "ext_0_S", 0, "door", 0.0)
    assert base != I.interactive_id("gs_vault", "ext_0_N", 1, "door", 0.0)
    assert base != I.interactive_id("other", "ext_0_N", 0, "door", 0.0)


def test_id_does_not_depend_on_authoring_order():
    # two doors authored in either order keep their own position-derived ids
    d_left = I.interactive_id("b", "ext_0_N", 0, "door", -0.3)
    d_right = I.interactive_id("b", "ext_0_N", 0, "door", 0.3)
    assert d_left != d_right
    # reversing the spec's opening list can't change either id (no index in key)
    assert d_left == I.interactive_id("b", "ext_0_N", 0, "door", -0.3)


# --- the two views share the id and split cleanly --------------------------

def test_slot_and_gameplay_views_share_the_id():
    m = I.derive_interactive("b", "ext_0_N", 0, "breach", 0.1)
    sv = I.slot_interactive(m)
    gv = I.gameplay_interactive(m, "ext_0_N_open0",
                                {"translation": [1, 0, 2], "rot_y": 0})
    assert sv["id"] == gv["id"] == m["id"]
    # slot view = art-facing (states + geometry), no transitions
    assert "transitions" not in sv
    assert sv["state_geometry"] == {"intact": "wall", "breached": "breach"}
    # gameplay view = netcode-facing (transitions + slot_ref), no state_geometry
    assert "state_geometry" not in gv
    assert gv["slot_ref"] == "ext_0_N_open0"
    assert gv["transitions"] and gv["reversible"] is False


def test_gameplay_view_carries_building_and_transform():
    m = I.derive_interactive("gs_vault", "ext_0_N", 0, "door", 0.0)
    gv = I.gameplay_interactive(m, "ext_0_N_open0",
                                {"translation": [1, 2, 3], "rot_y": 90},
                                building="gs_vault")
    assert gv["building"] == "gs_vault"
    assert gv["transform"]["rot_y"] == 90


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"ok: {len(fns)} interactive tests passed")
    sys.exit(0)
