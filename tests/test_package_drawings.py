"""A building's package carries its drawings (0.257.0, the factory's roadmap 296).

The walker, of roadmap 293's exploded axonometric, asked where it is seen: "both" -- a review page and a level's export
-- "It could even get into the game where the players can 'scope out' the level and see the buildings the level
assembles". A building's files reach a level only through this package (Level Factory's presentation compose, then its
export's copy into `lot/<id>/`), so `build_package` draws the building from its spec into `drawings/` when the caller
names the spec: the axonometric and a plan a storey, each kept by Godot as the file it is (`KEEP_IMPORT`, measured on
Godot 4.7: no texture made, the file read and drawn at run time), and `drawings.json` naming them. A facade gets the
record and the reason it has no drawing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import axonometric as AX  # noqa: E402
import floorplan as FP  # noqa: E402
import portable_building as PB  # noqa: E402
import spec_loader  # noqa: E402


def _spec(name):
    return os.path.join(HERE, "specs", name + ".json")


def test_the_keep_import_is_the_one_godot_left_as_written():
    """The `.import` Godot 4.7 kept as written, making no texture, when the drawing beside it was imported headless
    (the factory's patches/dc_drawings/keep_probe.out.txt)."""
    assert PB.KEEP_IMPORT == '[remap]\n\nimporter="keep"\n'


def test_a_building_package_carries_its_drawings(tmp_path):
    """deli_a03, a basement and two storeys: the axonometric and three plans, each the drawing its renderer makes of
    the spec, each beside a keep `.import`, and `drawings.json` naming them."""
    rec = PB.package_drawings(_spec("deli_a03"), str(tmp_path))
    spec = spec_loader.load_spec(_spec("deli_a03"))
    d = tmp_path / "drawings"
    assert rec["spec"] == spec.name and rec["axonometric"] == "axonometric.svg" and rec["scout"] == "scout.svg"
    assert rec["scout_model"] == "scout.glb"
    import scout_model as SM
    assert (d / "scout.glb").read_bytes() == SM.build_glb(spec)
    assert (d / "scout.glb.import").read_text(encoding="utf-8") == PB.KEEP_IMPORT
    assert [(p["storey"], p["file"]) for p in rec["plans"]] == [(-1, "floorB1.svg"), (0, "floor0.svg"),
                                                                 (1, "floor1.svg")]
    assert (d / "axonometric.svg").read_text(encoding="utf-8") == AX.render_axonometric(spec)
    assert (d / "scout.svg").read_text(encoding="utf-8") == AX.render_axonometric(spec, scout=True)
    for p in rec["plans"]:
        assert (d / p["file"]).read_text(encoding="utf-8") == FP.render_story(spec, p["storey"])
    svgs = sorted(f.name for f in d.glob("*.svg"))
    assert svgs == sorted(["axonometric.svg", "scout.svg"] + [p["file"] for p in rec["plans"]])
    for f in svgs:
        assert (d / (f + ".import")).read_text(encoding="utf-8") == PB.KEEP_IMPORT
    assert json.loads((d / "drawings.json").read_text(encoding="utf-8")) == rec


def test_a_facade_gets_its_reason_and_no_drawing(tmp_path):
    """gs_facade_rowhome: a street wall with no interior. Its axonometric is an empty walled box, so the package says
    why it carries none."""
    rec = PB.package_drawings(_spec("gs_facade_rowhome"), str(tmp_path))
    d = tmp_path / "drawings"
    assert rec["axonometric"] is None and rec["scout"] is None and rec["scout_model"] is None and rec["plans"] == []
    assert "facade" in rec["none_because"]
    assert not list(d.glob("*.svg")) and not list(d.glob("*.glb")) and not list(d.glob("*.import"))
    assert json.loads((d / "drawings.json").read_text(encoding="utf-8")) == rec


def test_build_package_draws_the_spec_it_is_given(tmp_path):
    """`build_package` draws when it is named a spec, and records it in its manifest; named none, it draws nothing --
    an older caller's package is the package it was. A building of no slots, so only the drawings are asked about."""
    slots = tmp_path / "empty.slots.json"
    slots.write_text(json.dumps({"building_id": "site", "slots": []}), encoding="utf-8")
    modules = tmp_path / "modules"
    modules.mkdir()
    man = PB.build_package(str(slots), None, str(modules), str(tmp_path / "with"), theme="delco_1997",
                           building_id="site", spec_path=_spec("deli_a03"))
    assert man["drawings"]["spec"] == spec_loader.load_spec(_spec("deli_a03")).name
    assert (tmp_path / "with" / "drawings" / "axonometric.svg").is_file()
    man = PB.build_package(str(slots), None, str(modules), str(tmp_path / "without"), theme="delco_1997",
                           building_id="site")
    assert man["drawings"] is None
    assert not (tmp_path / "without" / "drawings").exists()
