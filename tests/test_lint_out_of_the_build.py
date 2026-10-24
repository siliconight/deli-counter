"""A shell build reads nothing from the layout lint (0.233.0, the factory's roadmap 259).

`build_freshness` keeps `layout_lint.py` out of its sources so a lint edit does not demand a rebuild. That held only
if no build-time code read the lint, and stairwell did: `_host_openings` and `DOOR_APPROACH_M`, asked where a stair
can stand. They are `partition_bounds.host_openings` (watched) and `agent_contract.door_approach()` (watched) now.

Run: python -m pytest -q tests/test_lint_out_of_the_build.py
"""
import ast
from pathlib import Path

import agent_contract
import layout_lint
import partition_bounds

HERE = Path(__file__).resolve().parent.parent


def test_stairwell_imports_no_lint():
    tree = ast.parse((HERE / "stairwell.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert "layout_lint" not in names


def test_the_openings_are_one_function_under_two_names():
    assert layout_lint._host_openings is partition_bounds.host_openings


def test_the_approach_is_the_contracts():
    assert layout_lint.DOOR_APPROACH_M == agent_contract.door_approach()
