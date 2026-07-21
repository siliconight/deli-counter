"""Pure tests for the nav_gate.py wrapper (no Godot needed -- a fake godot
executable stands in for the engine). Run: python3 test_nav_gate.py"""
import json
import os
import stat
import sys
import tempfile

import nav_gate


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _fake_godot(tmp, version="4.3.stable.official", result=None,
                exit_code=0):
    """A stand-in binary: answers --version, and on a gate call writes
    `result` to the out.json argument and exits with exit_code."""
    path = os.path.join(tmp, "godot4")
    payload = json.dumps(result or {})
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""#!{sys.executable}
import json, sys
if "--version" in sys.argv:
    print("{version}")
    sys.exit(0)
args = sys.argv[sys.argv.index("--") + 1:]
out = args[2]
with open(out, "w") as f:
    json.dump(json.loads('''{payload}'''), f)
print("[nav-gate] fake run")
sys.exit({exit_code})
""")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


def _artifacts(tmp):
    glb = os.path.join(tmp, "x.glb")
    gp = os.path.join(tmp, "x.gameplay.json")
    open(glb, "w").write("stub")
    json.dump({"stair_systems": []}, open(gp, "w"))
    return glb, gp


def test_find_godot_env_override_trusted_without_probe():
    # An EXPLICIT DC_GODOT is trusted (no --version subprocess): the probe
    # spawns the Windows console wrapper + engine child and can time out on
    # a loaded machine, SKIPping gates against a perfectly good binary
    # (Phase 2 batch B). A wrong path still fails loudly at gate run time.
    with tempfile.TemporaryDirectory() as tmp:
        good = _fake_godot(tmp)
        path, why = nav_gate.find_godot(env={"DC_GODOT": good})
        assert path == good and "unprobed" in why


def test_find_godot_explicit_but_missing_is_refused():
    path, why = nav_gate.find_godot(env={"DC_GODOT": "/nonexistent/godot4"})
    assert path is None and "not found" in why


def test_find_godot_missing_binary():
    path, why = nav_gate.find_godot(env={"DC_GODOT": "/nonexistent/godot",
                                         "PATH": ""})
    assert path is None


def test_run_gate_parses_result_and_exit_code():
    with tempfile.TemporaryDirectory() as tmp:
        result = {"ok": True, "navmesh_polys": 42,
                  "stairs": [{"id": "core_0", "status": "ok", "detail": "d"}],
                  "markers": {"checked": 3, "reachable": 3,
                              "unreachable": []}}
        godot = _fake_godot(tmp, result=result, exit_code=0)
        glb, gp = _artifacts(tmp)
        out = nav_gate.run_gate(glb, gp, godot=godot)
        assert out["exit_code"] == 0 and out["ok"] is True
        assert out["navmesh_polys"] == 42
        ok, lines = nav_gate.verdict(out)
        assert ok and any("core_0: ok" in l for l in lines)


def test_run_gate_failure_verdict():
    with tempfile.TemporaryDirectory() as tmp:
        result = {"ok": False, "navmesh_polys": 40,
                  "stairs": [{"id": "core_0", "status": "no_path",
                              "detail": "endpoints on disjoint islands"}]}
        godot = _fake_godot(tmp, result=result, exit_code=1)
        glb, gp = _artifacts(tmp)
        out = nav_gate.run_gate(glb, gp, godot=godot)
        ok, lines = nav_gate.verdict(out)
        assert not ok
        assert any("no_path" in l for l in lines)


def test_run_gate_skips_gracefully_without_godot():
    with tempfile.TemporaryDirectory() as tmp:
        glb, gp = _artifacts(tmp)
        env_bak = dict(os.environ)
        os.environ["DC_GODOT"] = "/nonexistent/godot"
        os.environ["PATH"] = tmp                     # no godot anywhere
        try:
            out = nav_gate.run_gate(glb, gp)
        finally:
            os.environ.clear()
            os.environ.update(env_bak)
        assert out.get("skipped") is True
        ok, lines = nav_gate.verdict(out)
        assert ok and any("SKIP" in l for l in lines)   # skip is not failure


def test_run_gate_missing_artifacts_raise():
    try:
        nav_gate.run_gate("/nonexistent/x.glb")
        assert False, "should have raised"
    except FileNotFoundError:
        pass


def test_gate_script_exists_and_is_godot4_gdscript():
    src = open(nav_gate.GATE_GD, encoding="utf-8").read()
    assert src.startswith("extends SceneTree")
    assert "NavigationMeshSourceGeometryData3D" in src   # Godot 4 API
    assert "get_cmdline_user_args" in src
    # agent params come from the shared agent contract via the env bridge,
    # with ratified fallbacks equal to the F4 harness bake
    assert 'AGENT_RADIUS := _envf("DC_NAV_RADIUS", 0.4)' in src
    assert 'AGENT_HEIGHT := _envf("DC_NAV_HEIGHT", 1.8)' in src


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all nav_gate tests passed")
