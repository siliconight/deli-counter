"""specs_failing/: the known-bad building set (Production Package §25 /
acceptance 44-45). Every blocking guardrail has a fixture that MUST fail, and
must fail FOR ITS DOCUMENTED REASON (recorded in the fixture's own
meta.failing_fixture block). If one of these ever passes, a guardrail has
silently stopped guarding.

Engine-leg conditions (fall-through floors, navmesh breaks, Godot import) are
covered by the nav_gate/walktest fixtures where a Godot binary exists; this
file covers every offline-checkable blocking condition, plus the bad-GLB
coordinate fixtures when the bpy module is available."""

import glob
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXDIR = os.path.join(HERE, "specs_failing")

import evidence

FIXTURES = sorted(glob.glob(os.path.join(FIXDIR, "fx_*.json")))

with open(os.path.join(FIXDIR, "FIXTURES.json"), "r", encoding="utf-8") as _f:
    _MANIFEST = json.load(_f)


def _meta(path):
    return _MANIFEST[os.path.basename(path)]


def test_every_fixture_documents_its_reason():
    assert FIXTURES, "no failing fixtures found"
    assert {os.path.basename(p) for p in FIXTURES} == set(_MANIFEST), \
        "specs_failing/ and FIXTURES.json disagree"
    for p in FIXTURES:
        m = _meta(p)
        assert m.get("expected_gate"), f"{p}: no expected_gate"
        assert m.get("expected_code"), f"{p}: no expected_code"
        assert m.get("reason"), f"{p}: no reason"


@pytest.mark.parametrize("path", FIXTURES,
                         ids=[os.path.basename(p) for p in FIXTURES])
def test_fixture_fails_for_documented_reason(path):
    m = _meta(path)
    report, _, _ = evidence.collect(path)
    gate = m["expected_gate"]
    code = m["expected_code"]

    assert not report.get("passed", False), \
        f"{os.path.basename(path)} PASSED but must fail ({m['reason']})"
    assert gate in report["blocking_failures"], \
        (f"{os.path.basename(path)} failed on {report['blocking_failures']}, "
         f"expected gate '{gate}'")

    gate_errors = " | ".join(report["gates"][gate]["errors"])
    assert code.lower() in gate_errors.lower(), \
        (f"{os.path.basename(path)}: gate '{gate}' failed but not for the "
         f"documented reason '{code}'. Errors: {gate_errors}")


def test_reference_passes_without_exceptions():
    """§25: approved reference buildings pass with NO manual exceptions."""
    report, _, _ = evidence.collect(
        os.path.join(HERE, "specs", "pvp_station_ref.json"))
    assert report["passed"], report["blocking_failures"]


# ---------------------------------------------------------------------------
# coordinate fixtures: a GLB violating the transform contract must fail the
# round-trip test (needs the bpy module; skipped where Blender is absent)
# ---------------------------------------------------------------------------

_BPY_OPTIN = os.environ.get("DC_BPY_TESTS", "") == "1"
_bpy_reason = ("bpy round-trip fixtures run in their own process: "
               "DC_BPY_TESTS=1 pytest test_failing_fixtures.py -k glb "
               "(repeated Blender factory resets in a shared pytest process "
               "can deadlock)")


@pytest.mark.skipif(not _BPY_OPTIN, reason=_bpy_reason)
def test_bad_scale_glb_fails_roundtrip(tmp_path):
    bpy = pytest.importorskip("bpy")
    import roundtrip

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("m")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new("scaled_box", mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.scale = (10.0, 4.0, 3.0)          # the violation
    glb = str(tmp_path / "fx_bad_scale.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")

    man = {"expected": {
        "space": "spec/Blender Z-up meters",
        "bounds_min": [-5.0, -2.0, -1.5], "bounds_max": [5.0, 2.0, 1.5],
        "origin": [0, 0, 0], "story_height": 3.0,
        "floor_elevations": [0.0], "markers": []}}
    with open(str(tmp_path / "fx_bad_scale.manifest.json"), "w") as f:
        json.dump(man, f)

    report = roundtrip.check_glb(glb)
    assert not report["passed"]
    codes = {c["code"] for c in report["checks"] if not c["ok"]}
    assert "RT-SCALE" in codes, codes


@pytest.mark.skipif(not _BPY_OPTIN, reason=_bpy_reason)
def test_drifted_bounds_glb_fails_roundtrip(tmp_path):
    bpy = pytest.importorskip("bpy")
    import roundtrip

    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("m")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)   # 2m cube, unit scale (legal scale)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new("box", mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0.5, 0.0, 1.0)         # drifted from where it was recorded
    glb = str(tmp_path / "fx_drift.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")

    man = {"expected": {
        "space": "spec/Blender Z-up meters",
        "bounds_min": [-1.0, -1.0, 0.0], "bounds_max": [1.0, 1.0, 2.0],
        "origin": [0, 0, 0], "story_height": 3.0,
        "floor_elevations": [0.0], "markers": []}}
    with open(str(tmp_path / "fx_drift.manifest.json"), "w") as f:
        json.dump(man, f)

    report = roundtrip.check_glb(glb)
    assert not report["passed"]
    codes = {c["code"] for c in report["checks"] if not c["ok"]}
    assert "RT-BOUNDS" in codes, codes
