"""Which greybox nodes a themed slot owns.

This rule has now been wrong twice, in OPPOSITE directions, and each time it
shipped and was found by walking the level rather than by a test:

  substring  -- "VAULT" matched "VAULTLEDGE_0". The ledge's visual was
                dropped and its collider kept: a body-blocking box you cannot
                see, on a node whose role is `floor`.
  exact      -- "ext_0_S_open1" no longer matched "ext_0_S_open1_lintel".
                42 sub-parts (30 window, 7 doorway, 4 breach, 1 floor) were
                orphaned inside their themed modules and the compose z-fight
                gate went 15 pairs -> 193.

Both are the same missing idea: `_` is a name boundary. These tests pin both
failure directions at once, because fixing one by breaking the other is the
documented history of this function.

Run:  python -m pytest test_strip_greybox.py
"""
import json
import os

import pytest

from portable_building import slot_owner_test

HERE = os.path.dirname(os.path.abspath(__file__))


# --- the two historical failures ---------------------------------------

def test_a_longer_name_sharing_a_prefix_is_not_owned():
    """The invisible-collision bug. `VAULTLEDGE_0` is not part of `VAULT`;
    it merely begins with the same five letters. Dropping it left a collider
    with no visual, which is the dangerous direction -- you walk into
    nothing."""
    owns = slot_owner_test(["VAULT"])
    assert owns("VAULT") is True
    assert owns("VAULTLEDGE_0") is False


def test_a_sub_part_behind_a_separator_is_owned():
    """The z-fight bug. An opening's greybox is not one node -- it is the
    opening plus its lintel, sill, pane and breach panel. Leaving them behind
    stands them inside the themed module that replaced the opening."""
    owns = slot_owner_test(["ext_0_S_open1"])
    for part in ("_lintel", "_sill", "_pane", "_BREACHPANEL"):
        assert owns("ext_0_S_open1" + part) is True, part


def test_the_separator_is_the_whole_rule():
    """Same slot id, same leading characters, opposite verdicts -- the only
    difference is the underscore."""
    owns = slot_owner_test(["VAULT"])
    assert owns("VAULT_door") is True        # a sub-part of the vault
    assert owns("VAULTLEDGE_0") is False     # a different object


# --- protect: unthemed slots keep their own greybox --------------------

def test_an_unthemed_sibling_is_not_eaten_by_a_prefix():
    """A slot with no themed module keeps its OWN greybox visual. If a
    sibling slot's prefix could drop it, the invisible-collision bug returns
    by another route -- so every slot_id in the manifest is protected, not
    just the themed ones."""
    owns = slot_owner_test(["wall_N"], protect=["wall_N", "wall_N_2"])
    assert owns("wall_N") is True
    assert owns("wall_N_2") is False
    assert owns("wall_N_trim") is True       # not a slot, so still owned


def test_protect_cannot_save_a_slot_from_itself():
    """A themed slot is dropped even if it appears in `protect` -- the
    protection is against OTHER slots' prefixes, not against its own module
    replacing it."""
    owns = slot_owner_test(["wall_N"], protect=["wall_N"])
    assert owns("wall_N") is True


# --- shape --------------------------------------------------------------

def test_matching_is_case_insensitive_both_ways():
    owns = slot_owner_test(["Wall_N"])
    assert owns("wall_n") is True
    assert owns("WALL_N_TRIM") is True


def test_no_slots_owns_nothing():
    """An empty slot list must not turn `startswith(())` into a match-all.
    Python's str.startswith(()) is False, but relying on that silently is
    how a whole greybox gets deleted."""
    owns = slot_owner_test([])
    assert owns("anything") is False
    assert owns("") is False


def test_unrelated_nodes_are_untouched():
    owns = slot_owner_test(["ext_0_S_open1"])
    for n in ("floor_0", "slab_1", "stair_0_tread_3", "canopy"):
        assert owns(n) is False, n


# --- replay against the shipping manifest ------------------------------

# NOT in specs/ -- `validate.py --all` globs `specs/*.json` and validates
# every hit as a level spec, so a test fixture parked there fails the commit
# gate. testdata/ is inert.
MANIFEST = os.path.join(HERE, "testdata", "strip_fixture.json")


def _fixture():
    if not os.path.exists(MANIFEST):
        pytest.skip("no captured manifest fixture at %s" % MANIFEST)
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


def test_real_manifest_keeps_everything_with_no_module():
    """Replay of art_probe_001 seed 5017. The nodes that must SURVIVE are the
    ones no themed module covers: the four floors (VAULTLEDGE_0 among them),
    the unthemed walls, the ceiling, and all 57 stairs -- stairs have no
    slots at all (see docs/STAIR_ART_PASS.md), so every one of them must
    still be there afterwards."""
    fx = _fixture()
    owns = slot_owner_test(fx["themed_slot_ids"], protect=fx["all_slot_ids"])
    kept = {n: r for n, r in fx["surface_roles"].items() if not owns(n)}
    assert sum(1 for r in kept.values() if r == "stair") == 57
    assert "VAULTLEDGE_0" in kept
    assert kept["VAULTLEDGE_0"] == "floor"


def test_real_manifest_drops_every_opening_sub_part():
    """The 42 orphans. If any of these come back, the z-fight count goes with
    them."""
    fx = _fixture()
    owns = slot_owner_test(fx["themed_slot_ids"], protect=fx["all_slot_ids"])
    subs = [n for n in fx["surface_roles"]
            if n.endswith(("_lintel", "_sill", "_pane", "_BREACHPANEL"))]
    assert subs, "fixture has no opening sub-parts to check"
    orphans = [n for n in subs if not owns(n)]
    assert orphans == [], orphans


def test_no_slot_id_is_a_prefix_sibling_of_another():
    """The `protect` guard is currently load-bearing for nothing -- no slot
    in the shipping manifest sits behind another slot's `_`. That is worth
    KNOWING rather than assuming: if it ever stops being true, this goes red
    and someone reads the guard before trusting it."""
    fx = _fixture()
    ids = sorted({str(s).lower() for s in fx["all_slot_ids"] if s})
    collisions = [(a, b) for a in ids for b in ids
                  if a != b and b.startswith(a + "_")]
    assert collisions == [], collisions


# --- the shell circulation arm: no input is not a pass ------------------

def _empty_glb(tmp_path):
    """A glb that EXISTS and contains none of the prop nodes -- which is the
    real shape of the bug. The stripped base was a perfectly valid file; it
    had simply had the props removed from it."""
    from pygltflib import GLTF2, Scene
    g = GLTF2()
    g.scenes = [Scene(nodes=[])]
    g.scene = 0
    out = str(tmp_path / "stripped.glb")
    g.save(out)
    return out


def test_a_blind_shell_check_fails_rather_than_passing(tmp_path):
    """`check_shell` reporting `{"ok": true, "props": 0}` against eleven
    declared props is what a gate looks like when it has been handed the
    wrong file. Zero examined must never read as zero found."""
    import circulation
    gameplay = {"surface_roles": {"VAULT": "prop", "desk_0": "prop"},
                "markers": [], "rooms": []}
    got = circulation.check_shell(_empty_glb(tmp_path), {"slots": []}, gameplay)
    assert got["declared_props"] == 2
    assert got["props"] == 0
    assert got["ok"] is False
    assert "examined nothing" in got["error"]


def test_a_building_with_no_props_passes_honestly(tmp_path):
    """The other side of it: declared == 0 is a real, clean answer, not a
    plumbing failure, and must not be turned into a false alarm."""
    import circulation
    gameplay = {"surface_roles": {"wall_N": "wall"}, "markers": [], "rooms": []}
    got = circulation.check_shell(_empty_glb(tmp_path), {"slots": []}, gameplay)
    assert got["declared_props"] == 0
    assert got["props"] == 0
    assert got["ok"] is True
    assert "error" not in got
