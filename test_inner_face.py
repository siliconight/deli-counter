"""An outside-only wall finish stops at the wall (0.166.0).

Cold run 9120, finding 3: the gas station's exterior stone on the inside of
its exterior walls. Held here: every exterior wall slot in brick, stone, wood
or siding names its building's interior finish as `material_in`, no other
slot does, a remainder never does; the finish is never itself outside-only;
the stem mirror writes `_i<kind>` and resolves the plain name when the tagged
one is not built; and the room face is local -Y on all four facings,
measured through `tscn_export.godot_basis`, the transform every package is
placed with.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import themed_tscn  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUTSIDE_ONLY = {"brick", "stone", "wood", "siding"}


def _manifests():
    for p in sorted(glob.glob(os.path.join(HERE, "build", "*.slots.json"))):
        with open(p, encoding="utf-8") as f:
            yield json.load(f)


def test_every_outside_only_exterior_wall_names_its_room_face_and_nothing_else_does():
    tagged = 0
    for d in _manifests():
        for s in d["slots"]:
            parts = str(s.get("wall") or "").split("_")
            ext = len(parts) >= 3 and parts[0] == "ext" and parts[2] in ("N", "E", "S", "W")
            want = (ext and s.get("material") in OUTSIDE_ONLY and not s.get("glazing")
                    and s.get("role") in ("wall", "window", "doorway", "breach"))
            if want:
                tagged += 1
                assert s.get("material_in"), (d["building_id"], s["slot_id"])
                assert s["material_in"] not in OUTSIDE_ONLY, (d["building_id"], s["slot_id"])
            else:
                assert "material_in" not in s, (d["building_id"], s["slot_id"])
    assert tagged >= 1500, tagged


def test_the_gas_station_s_stone_walls_are_drywall_inside():
    """Every stone wall slot, the 9 remainders cold run 9123 showed stone at
    included (0.166.1)."""
    d = json.load(open(os.path.join(HERE, "build", "gas_station_a02.slots.json"), encoding="utf-8"))
    stone = [s for s in d["slots"] if s.get("material") == "stone" and s.get("role") != "roof"]
    assert stone and all(s.get("material_in") == "drywall" for s in stone), \
        [s["slot_id"] for s in stone if not s.get("material_in")]
    assert sum(1 for s in stone if s.get("size_mod") == "end") == 9


def test_the_remainder_stem_mirror_writes_the_room_face():
    slot = {"slot_id": "ext_0_N_seg12", "role": "wall", "size_mod": "end", "style": 1,
            "material": "stone", "material_in": "drywall",
            "fit": {"dims": [0.175, 0.3, 3.9], "pivot": "center"}}
    stem, scaled = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1, material="stone")
    assert scaled and stem == "wallEnd_delco_1997_01_mstone_idrywall"


def test_the_stem_mirror_writes_the_room_face_and_falls_back(tmp_path):
    slot = {"slot_id": "ext_0_N_seg0", "role": "wall", "size_mod": "full", "style": 1,
            "material": "stone", "material_in": "drywall",
            "fit": {"dims": [2.0, 0.3, 3.9], "pivot": "center"}}
    tagged, _ = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1, material="stone")
    plain, _ = themed_tscn.resolve_themed_stem(dict(slot, material_in=None), "delco_1997", 1,
                                               material="stone")
    assert tagged == plain.replace("_mstone", "_mstone_idrywall") and "_idrywall" in tagged
    # only the plain module built: the resolver lands on it
    (tmp_path / (plain + ".glb")).write_bytes(b"")
    got = themed_tscn.resolve_slot_ref(slot, "delco_1997", 1, str(tmp_path))[0]
    assert got == plain
    (tmp_path / (tagged + ".glb")).write_bytes(b"")
    assert themed_tscn.resolve_slot_ref(slot, "delco_1997", 1, str(tmp_path))[0] == tagged


def test_the_room_face_is_local_minus_y_on_every_facing():
    from tscn_export import godot_basis
    for facing, rot, out in (("N", 0, (0, 1)), ("E", 90, (1, 0)), ("S", 180, (0, -1)),
                             ("W", 270, (-1, 0))):
        b = godot_basis(rot, [1.0, 1.0, 1.0])
        rows = [b[0:3], b[3:6], b[6:9]]
        v = (0.0, 0.0, 1.0)              # local -Y in Blender is +Z in the module's Godot frame
        w = [sum(rows[i][k] * v[k] for k in range(3)) for i in range(3)]
        assert (round(w[0], 6), round(-w[2], 6)) == (-out[0], -out[1]), facing
