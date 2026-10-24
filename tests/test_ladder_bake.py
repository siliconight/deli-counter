"""Unit tests for the ladder climb contract bake (portable_building --
docs/LADDER_CLIMB_CONTRACT.md). Pure text/geometry; no bpy, no Godot.

Pins the guarantees: every ladder marker becomes an Area3D in group
ladder_area3d with +Z at the approach side, a full-height catch box, and a
TopOfLadder step-off marker; scenes without ladders are untouched; the
sub_resources splice keeps the tscn parseable (shapes before nodes,
load_steps consistent).
"""
import os
import re
import tempfile

from portable_building import _ladder_climb_nodes, splice_ladder_contract


def _gameplay(facing="E", x=-21.0, y=9.0, z=0.0, h=4.0, w=0.5):
    return {"markers": [{
        "name": "LADDER_0", "type": "ladder", "id": "ladder_0",
        "x": x, "y": y, "z": z,
        "climb_height": h, "width": w, "depth": 0.15, "facing": facing,
    }]}


def _basis_cols(tf_line):
    v = [float(t) for t in re.search(r"Transform3D\(([^)]+)\)",
                                     tf_line).group(1).split(",")]
    rows = [v[0:3], v[3:6], v[6:9]]
    plus_z = [rows[i][2] for i in range(3)]
    origin = v[9:12]
    return plus_z, origin


def test_no_ladders_no_output():
    assert _ladder_climb_nodes({"markers": []}) == ("", "")
    assert _ladder_climb_nodes({}) == ("", "")


def test_area_group_metadata_and_top_marker():
    subs, nodes = _ladder_climb_nodes(_gameplay())
    assert 'groups=["ladder_area3d", "dc_ladder"]' in nodes
    assert "metadata/climb_height = 4.0" in nodes
    assert 'metadata/facing = "E"' in nodes
    assert 'type="Area3D"' in nodes
    assert '[sub_resource type="BoxShape3D"' in subs
    # catch box: width + margin, height + headroom, 0.8 deep
    assert "size = Vector3(1.1, 5.0, 0.8)" in subs
    # TopOfLadder at climb_height - 0.2
    assert 'name="TopOfLadder"' in nodes
    assert "0, 3.8, 0)" in nodes


def test_plus_z_points_at_approach_side_all_facings():
    # spec->godot: (x,y,z) -> (x, z, -y). facing = approach direction.
    expected = {"E": [1, 0, 0], "W": [-1, 0, 0],
                "N": [0, 0, -1], "S": [0, 0, 1]}
    for facing, want in expected.items():
        _, nodes = _ladder_climb_nodes(_gameplay(facing=facing))
        area_tf = [l for l in nodes.splitlines()
                   if l.startswith("transform")][0]
        plus_z, _ = _basis_cols(area_tf)
        assert [round(c) for c in plus_z] == want, (facing, plus_z)


def test_base_anchor_converted_to_godot_space():
    _, nodes = _ladder_climb_nodes(_gameplay(x=-21.0, y=9.0, z=0.0))
    area_tf = [l for l in nodes.splitlines() if l.startswith("transform")][0]
    _, origin = _basis_cols(area_tf)
    assert origin == [-21.0, 0.0, -9.0]      # (x, z, -y)


def test_splice_keeps_tscn_parse_order_and_load_steps():
    scene = ('[gd_scene load_steps=3 format=3]\n\n'
             '[ext_resource type="PackedScene" path="res://b.glb" id="1_b"]\n\n'
             '[node name="Site" type="Node3D"]\n\n'
             '[node name="B" parent="." instance=ExtResource("1_b")]\n')
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "site.tscn")
        open(p, "w").write(scene)
        n = splice_ladder_contract(p, _gameplay())
        out = open(p).read()
    assert n == 1
    assert "[gd_scene load_steps=4" in out          # bumped by shape count
    # every sub_resource appears before the first node block
    assert out.rfind("[sub_resource") < out.find("[node ")
    assert 'name="Ladders"' in out and "ladder_area3d" in out


def test_splice_noop_without_ladders():
    scene = '[gd_scene load_steps=1 format=3]\n\n[node name="S" type="Node3D"]\n'
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "site.tscn")
        open(p, "w").write(scene)
        assert splice_ladder_contract(p, {"markers": []}) == 0
        assert open(p).read() == scene
