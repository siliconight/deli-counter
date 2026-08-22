"""Interactive slots ship BOTH states: the composer's half of INTERACTIVES.md.

``themed_tscn.state_variant_stems`` is the mirror of
``zoo_keeper.core.kit.slot_variants``: the kit builds a module per
non-default interactive state whose geometry differs; the composer must
instance exactly those, hidden, at the slot's own transform -- or the shipped
scene has nothing for the game's state machine to swap TO. Doors prove the
negative space: their states share one species (the swing is game-side
presentation), so they get art for neither -- exactly what the kit defers.

The z-fight gate learns the same contract from the other side: a parked
hidden variant is deliberately coplanar with its visible default and must
not gate the package.
"""

import os

import themed_tscn
import zfight_gate


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"glTF")


def _window_slot(slot_id="win_0", width=1.4):
    return {
        "slot_id": slot_id, "role": "window", "size_mod": "full", "style": 1,
        "current_ref": "window_greybox_01",
        "transform": {"translation": [1.0, 2.0, 1.5], "rot_y": 0,
                      "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [width, 0.35, 3.0], "pivot": "center", "openings": []},
        "interactive": {
            "id": "cr_test:if:aaaa1111", "kind": "window",
            "states": ["intact", "broken"], "default": "intact",
            "state_geometry": {"intact": "window", "broken": "window_broken"},
            "collision_per_state": {"intact": True, "broken": False},
        },
    }


def _breach_slot():
    return {
        "slot_id": "br_0", "role": "breach", "size_mod": "full", "style": 1,
        "transform": {"translation": [0.0, 0.0, 1.5], "rot_y": 90,
                      "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [1.5, 0.35, 3.0], "pivot": "center", "openings": []},
        "interactive": {
            "id": "cr_test:if:bbbb2222", "kind": "breach_wall",
            "states": ["intact", "breached"], "default": "intact",
            "state_geometry": {"intact": "wall", "breached": "breach"},
            "collision_per_state": {"intact": True, "breached": False},
        },
    }


def _door_slot():
    return {
        "slot_id": "door_0", "role": "doorway", "size_mod": "full", "style": 1,
        "transform": {"translation": [3.0, 0.0, 1.5], "rot_y": 0,
                      "scale": [1.0, 1.0, 1.0]},
        "fit": {"dims": [1.2, 0.35, 3.0], "pivot": "center", "openings": []},
        "interactive": {
            "id": "cr_test:if:cccc3333", "kind": "door",
            "states": ["closed", "open"], "default": "closed",
            "collision_per_state": {"closed": True, "open": False},
        },
    }


def test_window_variant_stem_mirrors_the_kit(tmp_path):
    """The literal is the contract, same as the module-stem mirror tests:
    the kit names the broken variant `<typ>_<theme>_<style>_w<cm>_<state>`."""
    lib = str(tmp_path)
    _touch(os.path.join(lib, "window_rockay_01_w140.glb"))
    _touch(os.path.join(lib, "window_rockay_01_w140_broken.glb"))
    variants = themed_tscn.state_variant_stems(
        _window_slot(), "rockay", 1, lib)
    assert variants == [("broken", "window_rockay_01_w140_broken", True)]


def test_breach_intact_is_wall_species_so_breached_differs(tmp_path):
    """A breach slot's default state is WALL geometry under the base stem;
    `breached` is the punched wall and must be instanced."""
    lib = str(tmp_path)
    _touch(os.path.join(lib, "breach_rockay_01_w150.glb"))
    _touch(os.path.join(lib, "breach_rockay_01_w150_breached.glb"))
    variants = themed_tscn.state_variant_stems(
        _breach_slot(), "rockay", 1, lib)
    assert variants == [("breached", "breach_rockay_01_w150_breached", True)]


def test_door_defers_exactly_like_the_kit(tmp_path):
    """No state_geometry -> every state is the same species -> identical art
    today -> no variant node, matching kit.slot_variants' deferral."""
    lib = str(tmp_path)
    _touch(os.path.join(lib, "doorway_rockay_01_w120.glb"))
    assert themed_tscn.state_variant_stems(_door_slot(), "rockay", 1, lib) == []


def test_missing_variant_is_reported_not_faked(tmp_path):
    """Progressive art: base built, broken not built yet -> available=False,
    and the composer must skip the node while counting the gap."""
    lib = str(tmp_path)
    _touch(os.path.join(lib, "window_rockay_01_w140.glb"))
    variants = themed_tscn.state_variant_stems(
        _window_slot(), "rockay", 1, lib)
    assert variants == [("broken", "window_rockay_01_w140_broken", False)]

    out = str(tmp_path / "t.tscn")
    _, stats = themed_tscn.write_themed_tscn(
        [_window_slot()], "b", out, theme="rockay", style=1, library_dir=lib)
    text = open(out, encoding="utf-8").read()
    assert "win_0_broken" not in text
    assert stats["state_variants"] == 0
    assert stats["state_variants_missing"] == 1


def test_greybox_fallback_slot_gets_no_variants(tmp_path):
    """No base module in the library -> the slot rides as greybox -> greybox
    has no state art, so no variant may be emitted either."""
    lib = str(tmp_path)
    _touch(os.path.join(lib, "window_rockay_01_w140_broken.glb"))  # orphan
    assert themed_tscn.state_variant_stems(
        _window_slot(), "rockay", 1, lib) == []


def test_composed_scene_carries_hidden_sibling_and_ids(tmp_path):
    lib = str(tmp_path)
    _touch(os.path.join(lib, "window_rockay_01_w140.glb"))
    _touch(os.path.join(lib, "window_rockay_01_w140_broken.glb"))
    out = str(tmp_path / "t.tscn")
    _, stats = themed_tscn.write_themed_tscn(
        [_window_slot()], "b", out, theme="rockay", style=1, library_dir=lib)
    text = open(out, encoding="utf-8").read()

    assert stats["state_variants"] == 1
    assert stats["state_variants_missing"] == 0
    # the broken module is a real ext_resource (so bundling picks it up)
    assert 'path="res://art/zoo/window_rockay_01_w140_broken.glb"' in text

    blocks = text.split("[node ")
    default = next(b for b in blocks if b.startswith('name="win_0"'))
    hidden = next(b for b in blocks if b.startswith('name="win_0_broken"'))
    # hidden, same transform, both tagged with the stable id
    assert "visible = false" in hidden
    assert "visible = false" not in default
    xf = [ln for ln in default.splitlines() if ln.startswith("transform =")]
    assert xf and xf[0] in hidden
    assert 'metadata/interactive_id = "cr_test:if:aaaa1111"' in default
    assert 'metadata/interactive_id = "cr_test:if:aaaa1111"' in hidden
    assert 'metadata/interactive_state = "intact"' in default
    assert 'metadata/interactive_state = "broken"' in hidden


def test_zfight_gate_skips_parked_state_variants(tmp_path):
    """The hidden sibling is coplanar with its default BY DESIGN; the gate
    must measure what renders at rest, so `visible = false` blocks are
    skipped BEFORE their GLB is touched. The bait: the hidden node's GLB is
    present but malformed -- if the visibility rule ever regresses, the walk
    parses it and this test fails loudly with a decode error, not quietly
    with a wrong count. (The default's GLB is removed; missing files were
    always skipped.)"""
    pkg = tmp_path / "pkg"
    art = pkg / "art" / "zoo"
    art.mkdir(parents=True)
    lib = str(art)
    _touch(os.path.join(lib, "window_rockay_01_w140.glb"))
    _touch(os.path.join(lib, "window_rockay_01_w140_broken.glb"))
    out = str(pkg / "b.tscn")
    themed_tscn.write_themed_tscn(
        [_window_slot()], "b", out, theme="rockay", style=1, library_dir=lib)
    text = open(out, encoding="utf-8").read()
    hidden_blocks = [b for b in text.split("[node ")
                     if "visible = false" in b]
    assert len(hidden_blocks) == 1
    os.remove(os.path.join(lib, "window_rockay_01_w140.glb"))
    boxes = zfight_gate._scene_module_boxes(str(pkg), "b.tscn")
    assert boxes == []
