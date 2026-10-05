"""An Empty's door is shut to a ray as well as a body (0.186.0, roadmap 183).

A door's aperture is a walkable void (`_opening_piece`), which is right for a
building you enter. On an Empty -- a sealed, hollow facade shell -- it was a
hole: the door module's jambs left 0.7 m, which stopped the 0.8 m walk capsule
but not a shot, and rays passed 10 m into gs_empty_rowhome_f through its front
door (cold run 9162, `patches/lf_empties/door_collision_probe.gd`). A facade's
door is now filled full-thickness, as its window's pane is.

Read off the built shells, so it fails until `build.py --all` has run on
0.186.0.
"""
import glob
import json
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))


def _nodes(glb):
    with open(glb, "rb") as f:
        b = f.read()
    clen = struct.unpack_from("<I", b, 12)[0]
    return {n.get("name", "") for n in json.loads(b[20:20 + clen])["nodes"]}


def _facade(name):
    p = os.path.join(HERE, "specs", name + ".json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return bool(json.load(f).get("facade"))


def _doors(names):
    """`ext_<storey>_<facing>_open<k>` openings with a lintel and neither a
    sill nor a pane: the doors."""
    out = set()
    for n in names:
        m = re.match(r"^(ext_\d+_[NESW]_open\d+)_lintel$", n)
        if m and m.group(1) + "_sill" not in names and m.group(1) + "_pane" not in names:
            out.add(m.group(1))
    return out


def test_every_empty_door_is_filled_and_has_its_collider():
    """FAILS ON 0.185.0: the door was a void."""
    shells = sorted(glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.glb")))
    assert len(shells) == 12
    for glb in shells:
        names = _nodes(glb)
        doors = _doors(names)
        assert len(doors) == 2, (glb, doors)               # front and back
        for d in doors:
            assert d + "_leaf" in names, (glb, d)
            assert d.replace("ext_", "ext_col_", 1) + "_leaf-convcolonly" in names, (glb, d)


def test_a_building_you_enter_keeps_its_doors_open():
    """The control: no shell that is not a facade grows a leaf."""
    seen = 0
    for glb in sorted(glob.glob(os.path.join(HERE, "build", "*.glb"))):
        name = os.path.basename(glb)[:-4]
        if _facade(name) is not False:
            continue
        names = _nodes(glb)
        if not _doors(names):
            continue
        seen += 1
        assert not [n for n in names if n.endswith("_leaf") or n.endswith("_leaf-convcolonly")], glb
    assert seen > 20
