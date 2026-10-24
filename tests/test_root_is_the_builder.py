"""The repo's root holds the builder and nothing else (0.265.0).

The walker, 2026-10-23: "Deli Counter Repo needs a little clean up/organization? (and a way so the home root doesn't
just fill up with python files?)". 300 files stood at the root, 181 of them tests and 32 migrations; the tests moved to
tests/, the one-shots to migrations/, and `check.py` holds the root to `root_modules.txt`.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check  # noqa: E402


def test_the_root_holds_the_builder_and_nothing_else():
    assert check.root_is_the_builder() == []


def test_a_stray_script_at_the_root_is_refused(tmp_path, monkeypatch):
    (tmp_path / "root_modules.txt").write_text("# the builder\nbuild.py\ngone.py\n", encoding="utf-8")
    (tmp_path / "build.py").write_text("", encoding="utf-8")
    (tmp_path / "probe_something.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(check, "HERE", str(tmp_path))
    got = check.root_is_the_builder()
    assert len(got) == 2
    assert any("probe_something.py stands at the root" in p for p in got)
    assert any("names gone.py, which is not at the root" in p for p in got)
