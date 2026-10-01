"""A Blender build that raises is a FAILED build (0.165.1).

0.165.0's first library build raised a NameError in every building's light
manifest, and `build.py --all` exited 0: Blender exits 0 after a `--python`
script raises unless it is launched with `--python-exit-code`. The build
manifest is written after the light manifest, so 128 of 131 shells were left
stale on disk with nothing saying so. Held here: the launch carries the flag
before the script it governs, and with Blender present, a spec the runner
cannot load reports failure.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build  # noqa: E402


def test_the_launch_fails_on_a_script_exception(monkeypatch, tmp_path):
    seen = {}

    class R:
        returncode = 1

    def fake_run(cmd, env=None):
        seen["cmd"] = cmd
        return R()
    monkeypatch.setattr(build.subprocess, "run", fake_run)
    assert build.build_one("blender", str(tmp_path / "x.json"), [str(tmp_path / "x.glb")]) is False
    cmd = seen["cmd"]
    assert "--python-exit-code" in cmd, cmd
    i = cmd.index("--python-exit-code")
    assert cmd[i + 1] != "0" and i < cmd.index("--python")


def test_blender_reports_a_runner_that_raises(tmp_path):
    blender = build.find_blender(None)
    if not blender:
        pytest.skip("no Blender here")
    missing = str(tmp_path / "no_such_spec.json")         # the runner raises loading it
    assert build.build_one(blender, missing, [str(tmp_path / "out.glb")]) is False
