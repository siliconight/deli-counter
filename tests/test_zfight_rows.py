"""The z-fight gate reads a `.tscn` Transform3D as Godot does: the basis's rows, then the origin (0.230.0, the
factory's roadmap 177).

Until 0.229.0 the gate built the transpose. A turned, non-uniformly scaled wall module -- deli_a01's east-wall end
piece `ext_0_E_seg10`, 0.6 m long and 0.35 m thick on a wall that runs along Godot Z -- came out 0.6 m through the
wall and 0.35 m along it, sharing both side planes of partition 1's end piece `int_0_1_seg18`: the last two pairs
the gate reported in cold runs 9322 to 9324. The engine stands it 0.35 m through and 0.6 m along (the factory's
`tools/module_pose_census.py` on cold run 9324's package: x 18.825..19.175, z -6.300..-5.700). These use the two
nodes' transforms exactly as cold run 9324 wrote them, on a unit-cube module, as the wall-end modules are.

Run: python -m pytest -q tests/test_zfight_rows.py
"""
import struct

import pytest

import zfight_gate

# exactly as cold run 9324's lot/deli_a01/site.tscn writes them
EXT_SEG10 = "0.0, 0.0, -0.35, 0.0, 3.0, 0.0, 0.6, 0.0, 0.0, 19.0, 1.496, -6.0"
INT_SEG18 = "0.375, 0.0, -0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0.35, 18.8125, 1.496, -6.0"
EXT_SEG9 = "0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 19.0, 1.496, -4.7"


def _box(xf_text, half=0.5):
    m = zfight_gate.instance_matrix([float(v) for v in xf_text.split(",")])
    pts = [zfight_gate._apply(m, (x, y, z))
           for x in (-half, half) for y in (-half, half) for z in (-half, half)]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def test_the_end_piece_stands_as_the_engine_measured_it():
    lo, hi = _box(EXT_SEG10)
    assert lo[0] == pytest.approx(18.825) and hi[0] == pytest.approx(19.175)   # 0.35 m through the wall
    assert lo[2] == pytest.approx(-6.3) and hi[2] == pytest.approx(-5.7)       # 0.6 m along it
    assert lo[1] == pytest.approx(-0.004) and hi[1] == pytest.approx(2.996)


def test_a_pure_turn_reads_as_it_always_did():
    lo, hi = _box(EXT_SEG9)
    assert hi[0] - lo[0] == pytest.approx(1.0) and hi[2] - lo[2] == pytest.approx(1.0)
    assert (lo[0] + hi[0]) / 2 == pytest.approx(19.0) and (lo[2] + hi[2]) / 2 == pytest.approx(-4.7)


def _unit_cube_glb(path):
    """A one-mesh glTF whose POSITION accessor spans the unit cube about the origin -- all the gate reads."""
    from pygltflib import GLTF2, Accessor, Attributes, Buffer, BufferView, Mesh, Node, Primitive, Scene
    blob = b"".join(struct.pack("<3f", x, y, z) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5))
    g = GLTF2(scene=0, scenes=[Scene(nodes=[0])], nodes=[Node(mesh=0, name="WallEnd_Panel")],
              meshes=[Mesh(primitives=[Primitive(attributes=Attributes(POSITION=0))])],
              accessors=[Accessor(bufferView=0, componentType=5126, count=8, type="VEC3",
                                  min=[-0.5, -0.5, -0.5], max=[0.5, 0.5, 0.5])],
              bufferViews=[BufferView(buffer=0, byteOffset=0, byteLength=len(blob))],
              buffers=[Buffer(byteLength=len(blob))])
    g.set_binary_blob(blob)
    g.save_binary(str(path))


# The storey's slabs, as the building stands them: the walls are sunk 4 mm (`SLAB_CAP_SINK`) into the floor, their
# caps 4 mm under the slab above. Both pieces span the same height, so their tops and bottoms share planes; matter
# within the gate's outward gap buries those, as it does in the building. Without the slabs this would be asking
# about faces no building leaves open.
FLOOR = "2.0, 0.0, 0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 2.0, 18.8, -0.15, -6.0"
CEILING = "2.0, 0.0, 0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 2.0, 18.8, 3.15, -6.0"


def _instance(name, xf):
    return '[node name="%s" parent="." instance=ExtResource("1_cube")]\ntransform = Transform3D(%s)\n\n' % (name, xf)


def test_the_junction_holds_no_pair(tmp_path):
    pkg = tmp_path / "pkg"
    (pkg / "art" / "zoo").mkdir(parents=True)
    _unit_cube_glb(pkg / "art" / "zoo" / "cube.glb")
    (pkg / "site.tscn").write_text(
        '[gd_scene format=3]\n\n'
        '[ext_resource type="PackedScene" path="res://art/zoo/cube.glb" id="1_cube"]\n\n'
        '[node name="Site" type="Node3D"]\n\n'
        + _instance("ext_0_E_seg10", EXT_SEG10) + _instance("int_0_1_seg18", INT_SEG18)
        + _instance("floor_0", FLOOR) + _instance("ceiling_1", CEILING), encoding="utf-8")
    r = zfight_gate.check_package(str(pkg), "site.tscn")
    assert r["solids"] == 4, r
    assert r["pairs"] == 0 and r["ok"], r["findings"]
