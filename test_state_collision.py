"""A hidden interactive state must not ship a live collider.

THE WALKER'S RULE, 2026-09-23: "If I see collision, I expect collision." And,
on breachable areas: "we don't know if we have breachable areas in the game
yet... would rather have a fallback to solid walls."

WHAT WAS MEASURED BEFORE ANY OF THIS WAS WRITTEN, on cold run 9075's package:
six hidden `breached` nodes across three buildings, every one `visible = false`,
and `grep -c 'collision_layer\\|editable path'` over the whole scene returning
**0**. So the state that the contract calls not-solid shipped solid, and a ray
at two of six sampled walls hit `Breach` where a player sees brick.

The default is still solid and that is worth stating, because it is why nothing
fell through a wall: the intact and breached colliders are coincident, so their
union is the intact wall. What it costs is a surface query returning the wrong
collider, a physics-parsed navmesh baking both states superimposed, and a future
breach implemented the obvious way -- flip `visible` -- producing a visible hole
that is still solid, with no error anywhere.

THE FIXTURE MIRRORS A REAL FILE, not a guess at one. The node names below were
read out of the shipped
`lot/country_club_a01/art/zoo/breach_delco_1997_01_w140_ob6fc1c_breached.glb`
in cold run 9075's export, which carries exactly two nodes:

    Breach-colonly
    Breach_concrete_delco_1997

-- the collider and the visual. Writing a checker against a guessed schema is
the defect CLAUDE.md records three instances of; this one was read first.
"""
import os

import pytest

import interactives
import themed_tscn


# ------------------------------------------------------------------ part 1
# The advisory has to survive the trip to the netcode-facing entry, because
# `themed_tscn` reads it from there.

def test_the_gameplay_entry_carries_collision_per_state():
    """It is defined in `_DEFAULTS` for every kind, documented in
    docs/INTERACTIVES.md as one of four advisories, referenced by name in
    themed_tscn's own comment -- and it used to be dropped here."""
    m = interactives.derive_interactive("b", "w", 0, "breach", 0.5)
    entry = interactives.gameplay_interactive(m, "slot", [0, 0, 0])
    assert entry["collision_per_state"] == {"intact": True, "breached": False}


def test_every_default_kind_states_which_of_its_states_are_solid():
    """A kind whose machine says nothing is a kind whose hidden states ship
    solid, silently. Assert the contract is total rather than trusting it."""
    for kind, machine in interactives._DEFAULTS.items():
        cps = machine.get("collision_per_state")
        assert cps, "%s declares no collision_per_state" % kind
        assert set(cps) == set(machine["states"]), (
            "%s: collision_per_state %s does not cover states %s"
            % (kind, sorted(cps), sorted(machine["states"])))


def test_at_least_one_kind_has_a_state_that_is_not_solid():
    """A vacuity guard. If every state were solid the emitter below could
    never fire and its tests would pass by describing nothing."""
    assert any(False in m["collision_per_state"].values()
               for m in interactives._DEFAULTS.values())


# ------------------------------------------------------------------ part 2
# The body names Godot will give a GLB's colliders.

def _glb(tmp_path, names, fn="m.glb"):
    from pygltflib import GLTF2, Node, Scene
    g = GLTF2()
    g.nodes = [Node(name=n) for n in names]
    g.scenes = [Scene(nodes=list(range(len(names))))]
    g.scene = 0
    out = str(tmp_path / fn)
    g.save(out)
    return out


def test_the_fixture_is_a_glb_that_really_carries_those_nodes(tmp_path):
    """The fixture itself is checked, because a file that fails to load makes
    `_glb_collision_bodies` return [] and every assertion below vacuous."""
    from pygltflib import GLTF2
    p = _glb(tmp_path, ["Breach-colonly", "Breach_concrete_delco_1997"])
    assert [n.name for n in GLTF2().load(p).nodes] == [
        "Breach-colonly", "Breach_concrete_delco_1997"]


def test_a_real_breach_module_s_collider_is_named_breach(tmp_path):
    """The exact two-node shape of the shipped module named in this file's
    docstring: the collider is found, the visual beside it is not."""
    themed_tscn._COLBODY_CACHE.clear()
    p = _glb(tmp_path, ["Breach-colonly", "Breach_concrete_delco_1997"])
    assert themed_tscn._glb_collision_bodies(p) == ["Breach"]


@pytest.mark.parametrize("suffix", ["-colonly", "-convcolonly",
                                    "-col", "-convcol"])
def test_every_godot_collision_suffix_is_stripped(tmp_path, suffix):
    """Godot's four spellings, and the same set `_glb_extent` skips -- one
    convention read from one place rather than two lists that drift."""
    themed_tscn._COLBODY_CACHE.clear()
    p = _glb(tmp_path, ["Wall" + suffix], fn="s%s.glb" % suffix.strip("-"))
    assert themed_tscn._glb_collision_bodies(p) == ["Wall"]


def test_a_module_with_no_collider_yields_nothing(tmp_path):
    """No bodies means no override block, not an empty one -- an
    `[editable path=...]` with no children under it is a scene edit that says
    nothing and a diff nobody can explain."""
    themed_tscn._COLBODY_CACHE.clear()
    p = _glb(tmp_path, ["Pane_glass", "Frame"])
    assert themed_tscn._glb_collision_bodies(p) == []


def test_an_unreadable_module_yields_nothing_rather_than_raising(tmp_path):
    """A library whose file is missing or truncated must not take the whole
    scene write down; it degrades to today's behaviour, which is solid."""
    themed_tscn._COLBODY_CACHE.clear()
    bad = str(tmp_path / "truncated.glb")
    with open(bad, "wb") as fh:
        fh.write(b"glTF-ish but not")
    assert themed_tscn._glb_collision_bodies(bad) == []
    assert themed_tscn._glb_collision_bodies(
        str(tmp_path / "absent.glb")) == []


def test_the_cache_is_keyed_on_the_path(tmp_path):
    """One library module is instanced many times per scene; the parse must
    happen once. Keyed wrong, a second module would inherit the first's
    bodies and disable a collider that should stay."""
    themed_tscn._COLBODY_CACHE.clear()
    a = _glb(tmp_path, ["Breach-colonly"], fn="a.glb")
    b = _glb(tmp_path, ["Shutter-colonly"], fn="b.glb")
    assert themed_tscn._glb_collision_bodies(a) == ["Breach"]
    assert themed_tscn._glb_collision_bodies(b) == ["Shutter"]
    assert themed_tscn._glb_collision_bodies(a) == ["Breach"]
    assert set(themed_tscn._COLBODY_CACHE) == {a, b}


def test_the_visual_half_of_a_colonly_pair_is_not_mistaken_for_a_body(
        tmp_path):
    """`Breach_concrete_delco_1997` contains no suffix and must not match on
    a substring. The emitted override names a node by name; naming one that
    does not exist is a scene Godot loads with a warning and no effect --
    which is the failure mode that looks like the fix working."""
    themed_tscn._COLBODY_CACHE.clear()
    p = _glb(tmp_path, ["Breach_concrete_delco_1997"])
    assert themed_tscn._glb_collision_bodies(p) == []
