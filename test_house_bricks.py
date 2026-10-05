"""A house's own brick (0.183.0): the rowhome family wears three.

The walker's South Philly photograph (the factory root's
`docs/reference/EMPTIES_COMPS.md`, "Window comps"): "every house a different
brick: brown, red, orange". The three brick rowhomes all wore the one red.
Pixelcoat (>= 0.57.0) paints `brick_brown` and `brick_orange`, Zoo
(>= 1.73.0) knows them, and here two houses are built in them.
"""
import glob
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import material_kind   # noqa: E402
import presets         # noqa: E402


def test_the_house_bricks_are_kinds_and_map_to_themselves():
    """FAILS ON 0.182.0: neither kind existed here."""
    for kind in ("brick_brown", "brick_orange"):
        assert kind in material_kind.SKIN_KINDS
        assert material_kind.KIND_BY_MATERIAL[kind] == kind


def test_a_house_brick_belongs_outside_like_brick():
    """An exterior wall in it carries its building's interior finish on its
    room face (0.166.0), as brick does."""
    src = open(os.path.join(HERE, "deli_counter.py"), encoding="utf-8").read()
    line = next(l for l in src.splitlines() if "OUTSIDE_ONLY = frozenset(" in l)
    for kind in ("brick", "brick_brown", "brick_orange"):
        assert '"%s"' % kind in line, line


def test_the_brick_houses_are_three_different_bricks():
    bricks = sorted(a["wall"] for a in presets.EMPTY_ROWHOMES.values() if a["wall"].startswith("brick"))
    assert bricks == ["brick", "brick_brown", "brick_orange"]


@pytest.mark.skipif(not glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.slots.json")),
                    reason="no built Empties")
def test_every_built_rowhome_s_front_wears_its_wall():
    for name, args in presets.EMPTY_ROWHOMES.items():
        with open(os.path.join(HERE, "build", f"{name}.slots.json"), encoding="utf-8") as fh:
            walls = {s.get("material") for s in json.load(fh)["slots"]
                     if s["role"] == "wall" and s["slot_id"].startswith("ext_")}
        assert material_kind.KIND_BY_MATERIAL.get(args["wall"], args["wall"]) in walls, (name, walls)
