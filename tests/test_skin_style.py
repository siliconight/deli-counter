"""Unit tests for the material-driven skin styles (skin_style.py +
themed_tscn's per-slot style resolution and style-01 fallback).

Pins the fix for 'only 1 pixelcoat skin shows': style -- the axis Zoo/
Pixelcoat vary skins on -- used to be hard-coded to 1 at every slot emission
site AND flattened by the composer's global --style. Now it follows the
surface material, and a kit that hasn't built the styled variants yet
degrades to style 01, never to greybox.
"""
import os
import tempfile

import skin_style as SS
from themed_tscn import resolve_themed_stem, write_themed_tscn


def test_mapping_is_spec_order_one_based():
    m = SS.material_styles(["brick_ext", "drywall", "glass", "metal"])
    assert m == {"brick_ext": 1, "drywall": 2, "glass": 3, "metal": 4}


def test_style_for_falls_back_material_then_default_then_one():
    m = SS.material_styles(["brick_ext", "drywall"])
    assert SS.style_for("drywall", m, "brick_ext") == 2
    assert SS.style_for("unknown", m, "brick_ext") == 1   # default material
    assert SS.style_for("unknown", m, None) == 1          # bare fallback
    assert SS.style_for(None, {}, None) == 1              # no materials at all


def test_duplicate_material_ids_first_wins():
    m = SS.material_styles(["brick_ext", "brick_ext", "drywall"])
    assert m == {"brick_ext": 1, "drywall": 3}


def _slot(style=None, width=2.0):
    s = {"slot_id": "w0", "role": "wall", "size_mod": "full",
         "fit": {"dims": [width, 0.35, 4.0]},
         "transform": {"translation": [0, 0, 2], "rot_y": 0,
                       "scale": [1, 1, 1]}}
    if style is not None:
        s["style"] = style
    return s


def test_resolver_prefers_slot_style_over_global():
    stem, _ = resolve_themed_stem(_slot(style=3), "rockay", 1)
    assert stem == "wall_rockay_03_w200"
    # no slot style -> the compose-level style is the fallback
    stem, _ = resolve_themed_stem(_slot(style=None), "rockay", 2)
    assert stem == "wall_rockay_02_w200"


def test_composer_falls_back_to_style_01_not_greybox():
    # library has ONLY the style-01 module; a style-2 slot must dress with it.
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "wall_rockay_01_w200.glb"), "wb").close()
        out = os.path.join(td, "b.tscn")
        _, stats = write_themed_tscn([_slot(style=2)], "b", out,
                                     theme="rockay", style=1, library_dir=td)
        assert stats["themed"] == 1
        assert stats["style_fallback_to_01"] == 1
        assert stats["greybox_fallback"] == 0
        assert "wall_rockay_01_w200" in open(out).read()


def test_composer_uses_styled_module_when_built():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "wall_rockay_01_w200.glb"), "wb").close()
        open(os.path.join(td, "wall_rockay_02_w200.glb"), "wb").close()
        out = os.path.join(td, "b.tscn")
        _, stats = write_themed_tscn([_slot(style=2)], "b", out,
                                     theme="rockay", style=1, library_dir=td)
        assert stats["themed"] == 1
        assert stats["style_fallback_to_01"] == 0
        assert "wall_rockay_02_w200" in open(out).read()
