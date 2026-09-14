"""A bank vault is a room behind a round door (`vault_room`, 0.130.0).

The walker, walk 9052: "the bank vault should absolutely be a hero piece".
Zoo 0.83.0 builds the door; these pin Deli Counter's half -- the slot it
needs, which way it faces, the floor its leaf swings over, the gate that keeps
that floor clear, and the generator that turns a vault box into a vault room.

THE CROSS-REPO PINS run when Zoo is found: `$DC_ZOO_ROOT`, else `../zoo`
beside this repo. Without it they skip and say so -- the retyped numbers are
then pinned only by the literals below.

    python -m pytest test_vault_room.py -q
"""
import contextlib
import copy
import importlib
import io
import json
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint  # noqa: E402
import level_design  # noqa: E402
import presets  # noqa: E402
import themed_tscn  # noqa: E402
import tscn_export  # noqa: E402
import vault_room as VR  # noqa: E402
from spec_loader import spec_from_dict  # noqa: E402
from spec_types import Opening  # noqa: E402

ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")


def _zoo():
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    return importlib.import_module("zoo_keeper.core.vault_forms")


def _spec(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def _bank(**kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return presets.make("bank", **kw)


# ------------------------------------------------------------------ the slot
def test_a_vault_slot_is_as_wide_as_the_door():
    """1.3 x 2.1 needs 3.5837 m of slot (Zoo's `required_size`), rounded up to
    a decimetre: 3.6. The aperture alone was 1.4, and Zoo built a porthole."""
    need = VR.required_size(1.3, 2.1, 0.0)
    assert need == {"width": 3.5837, "height": 2.6566, "portal_radius": 1.2349}
    assert VR.slot_width(1.3, 2.1, 0.0) == 3.6
    # 0.129.0's default aperture: 3.885 m of door (hinge radius clamped 0.16)
    assert VR.required_size(1.4, 2.3, 0.15)["width"] == 3.885
    assert VR.slot_width(1.4, 2.3, 0.15) == 3.9


def test_the_vault_default_is_zoos_aperture_on_the_floor():
    r = Opening(kind="vault").resolved()
    assert r == {"width": 1.3, "height": 2.1, "sill": 0.0} == VR.APERTURE
    # the old 0.15 m lip stood above the unassisted step
    import agent_contract
    step = agent_contract.contract()["clearances"]["unassisted_step_max_m"]
    assert r["sill"] <= step


def test_the_slot_numbers_are_zoos(tmp_path):
    vf = _zoo()
    assert vf.DEFAULT_OPENING == VR.APERTURE
    for k, mine in (("frame_frac", VR.FRAME_FRAC), ("margin", VR.MARGIN),
                    ("open_swing_deg", VR.OPEN_SWING_DEG),
                    ("breach_swing_deg", VR.BREACH_SWING_DEG),
                    ("breach_tilt_deg", VR.BREACH_TILT_DEG),
                    ("bolt_length", VR.BOLT_LENGTH)):
        assert vf.DEFAULTS[k] == mine, k
    for k in ("CUT_LEAF", "DOOR_GAP", "KNUCKLE", "BOSS_BACK", "BOSS_DEPTH"):
        assert getattr(vf, k) == getattr(VR, k), k
    for ow in (0.9, 1.25, 1.3, 1.6, 2.2):
        for oh in (1.9, 2.1, 2.4):
            for sill in (0.0, 0.1):
                assert vf.required_size(ow, oh, sill) == \
                    VR.required_size(ow, oh, sill), (ow, oh, sill)


def test_the_leaf_poses_are_zoos():
    """DC's retyped leaf boxes equal Zoo's `leaf_collision`, and the swept
    swing contains every one of them."""
    vf = _zoo()
    for w, d, h in ((3.6, 0.3, 3.3), (3.6, 0.6, 3.3), (4.0, 0.45, 3.9),
                    (1.4, 0.3, 3.3)):
        zv = vf.plan_vault(w, d, h, VR.APERTURE)
        mv = VR.plan(w, d, h, VR.APERTURE)
        for state in ("open", "breached"):
            zb = vf.leaf_collision(zv, state)
            mb = VR.leaf_boxes(mv, state)
            assert len(zb) == len(mb)
            for (za, zz), (ma, mz) in zip(zb, mb):
                for i in range(3):
                    assert za[i] == pytest.approx(ma[i], abs=1e-9)
                    assert zz[i] == pytest.approx(mz[i], abs=1e-9)
            x0, x1, y0, y1 = VR.swing_local(w, d, h, VR.APERTURE)
            for lo, hi in zb:
                assert x0 <= lo[0] and hi[0] <= x1, (w, d, state)
                assert hi[1] <= y1, (w, d, state)


def test_the_composer_mirror_of_state_art_is_zoos():
    _zoo()
    with open(os.path.join(ZOO, "zoo_keeper", "genome", "species",
                           "vault_door.json"), encoding="utf-8") as f:
        genome = json.load(f)
    assert tuple(genome["state_art"]) == \
        themed_tscn.SPECIES_STATE_ART["vault_door"]


# ------------------------------------------------------------------ the swing
def test_the_leaf_swings_out_on_the_face_and_past_the_hinge():
    """Measured off Zoo's own collision at 3.6 x 0.3 x 3.3: the open leaf
    reaches 2.606 m in front of the face; breached, 1.123 m past the hinge-side
    edge. The sweep is at least that."""
    x0, x1, y0, y1 = VR.swing_local(3.6, 0.3, 3.3)
    assert y0 == 0.15                      # starts at the face, not in the wall
    assert y1 - 0.15 >= 2.606
    assert x1 - 1.8 >= 1.123               # hinges at +x
    assert x0 > -1.8                       # the lock side stays inside the slot


def test_the_bearing_is_the_composers():
    """`to_world` turns module-local +y onto the bearing exactly as the Godot
    composer's basis does (Blender +y is glTF -z; Godot (X, Z) is Blender
    (x, -y))."""
    for face, rot in VR.BEARING.items():
        b = tscn_export.godot_basis(rot, [1.0, 1.0, 1.0])
        rows = [b[0:3], b[3:6], b[6:9]]
        local = (0.0, 0.0, -1.0)           # Blender local +y, in glTF
        gx = sum(rows[0][j] * local[j] for j in range(3))
        gz = sum(rows[2][j] * local[j] for j in range(3))
        wx, wy = VR.to_world(0.0, 0.0, rot, 0.0, 1.0)
        assert (round(gx, 9), round(-gz, 9)) == (round(wx, 9), round(wy, 9))
        want = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}[face]
        assert (round(wx), round(wy)) == want


# ---------------------------------------------------------------- the builder
@pytest.fixture
def dc(monkeypatch):
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def _builder(dc, d):
    import skin_style
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    return spec, b


def test_the_slot_records_the_door_width_and_the_aperture(dc):
    d = {"name": "v", "footprint_x": 20, "footprint_y": 20,
         "partitions": [{"story": 0, "axis": "X", "pos": 0.0, "start": -5.0,
                         "end": 5.0, "openings": [{"kind": "vault", "pos": 0.0,
                                                   "face": "S"}]}]}
    spec, b = _builder(dc, d)
    op = spec.partitions[0].openings[0]
    h = b._opening_to_hole(op, 10.0, "int_0_0", 0)
    assert h["w"] == 1.3 and h["slot_w"] == 3.6 and h["face"] == "S"
    b._record_opening_slot("int_0_0_open0", (0.0, 0.0, 1.5),
                           (10.0, 0.3, 3.0), 0, h)
    slot = b.slots[0]
    assert slot["role"] == "vault_door"
    assert slot["fit"]["dims"] == [3.6, 0.3, 3.0]
    assert slot["fit"]["openings"] == [
        {"kind": "vault", "width": 1.3, "height": 2.1, "sill": 0.0}]
    assert slot["transform"]["rot_y"] == 180
    assert slot["interactive"]["state_geometry"]["open"] == "vault_door"
    # Zoo's stem for it (the mirror keys width on dims[0], the tag on openings)
    stem, _ = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1)
    assert stem.startswith("vault_door_delco_1997_") and "_w360_o" in stem


def test_an_opening_face_turns_a_partition_slot(dc):
    d = {"name": "v", "footprint_x": 20, "footprint_y": 20}
    _spec_, b = _builder(dc, d)
    assert b._opening_rot("int_0_3", 1, None) == 90
    assert b._opening_rot("int_0_3", 1, "W") == 270
    assert b._opening_rot("int_0_3", 1, "E") == 90
    assert b._opening_rot("int_0_3", 0, "S") == 180
    with contextlib.redirect_stdout(io.StringIO()) as out:
        assert b._opening_rot("int_0_3", 0, "E") == 0     # not on an X wall
    assert "WARNING" in out.getvalue()


def test_the_composer_places_every_state_zoo_draws(tmp_path):
    lib = str(tmp_path)
    slot = {"slot_id": "int_-1_6_open0", "role": "vault_door", "size_mod": "full",
            "style": 1, "transform": {"translation": [0, 0, 0], "rot_y": 0,
                                      "scale": [1, 1, 1]},
            "fit": {"dims": [3.6, 0.3, 3.3], "pivot": "center",
                    "openings": [{"kind": "vault", "width": 1.3, "height": 2.1,
                                  "sill": 0.0}]},
            "interactive": {"id": "x:if:1", "kind": "vault_door",
                            "states": ["locked", "unlocked", "open", "breached"],
                            "default": "locked",
                            "state_geometry": {s: "vault_door" for s in
                                               ("locked", "unlocked", "open",
                                                "breached")}}}
    base, _ = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1)
    for suffix in ("", "_open"):
        open(os.path.join(lib, base + suffix + ".glb"), "wb").write(b"glTF")
    got = themed_tscn.state_variant_stems(slot, "delco_1997", 1, lib)
    assert [(s, a) for s, _stem, a in got] == [
        ("unlocked", False), ("open", True), ("breached", False)]


# ---------------------------------------------------------------- the gate
def _vault_wall_spec(face="N", volume=None):
    d = {"name": "g", "mode": "heist", "footprint_x": 20, "footprint_y": 20,
         "story_height": 3.6, "n_stories": 1, "modular": True,
         "partitions": [{"story": 0, "axis": "X", "pos": 0.0, "start": -10.0,
                         "end": 10.0, "openings": [{"kind": "vault", "pos": 0.0,
                                                    "face": face}]}],
         "volumes": [volume] if volume else []}
    return d


def test_l22_fails_a_solid_in_the_swing():
    crate = {"name": "crate_stack", "x": 0.5, "y": 1.5, "z": 0.5,
             "size_x": 1.0, "size_y": 1.0, "size_z": 1.0}
    fails, _ = VR.findings(_vault_wall_spec("N", crate))
    assert any("L22 solid in a vault door's swing: 'crate_stack'" in f
               for f in fails), fails
    # the same crate behind the door, in the vault, is fine
    behind = dict(crate, y=-1.5)
    assert VR.findings(_vault_wall_spec("N", behind))[0] == []
    # and so is it in front of a door facing the other way
    assert VR.findings(_vault_wall_spec("S", crate))[0] == []
    # layout_lint carries it
    assert any(f.startswith("L22") for f in
               layout_lint.gate(_vault_wall_spec("N", crate))[0])


def test_l22_fails_a_wrong_face_a_short_wall_and_a_faceless_modular_door():
    assert any("faces E" in f for f in VR.findings(_vault_wall_spec("E"))[0])
    short = _vault_wall_spec("N")
    short["partitions"][0].update(start=-1.5, end=1.5)
    assert any("3.60 m slot" in f for f in VR.findings(short)[0])
    faceless = _vault_wall_spec("N")
    del faceless["partitions"][0]["openings"][0]["face"]
    fails, warns = VR.findings(faceless)
    assert fails == [] and any("has no face" in w for w in warns)


def test_seeding_keeps_out_of_the_swing():
    d = _vault_wall_spec("N")
    room = {"id": "hall", "story": 0, "bounds": [-10, 0, 10, 10]}
    swing = VR.keepout_rects(d, 0)[0]
    cx, cy = (swing[0] + swing[2]) / 2.0, (swing[1] + swing[3]) / 2.0
    assert not level_design._seed_clear(d, room, cx, cy, [], half=0.3)


# ------------------------------------------------------------- the generator
def test_the_bank_preset_walls_its_vault_into_a_room():
    d = _bank()
    assert not [v for v in d["volumes"] if VR.is_vault_volume(v)]
    vault = [r for r in d["rooms"] if r["id"] == "vault"][0]
    assert vault["story"] == -1 and vault["bounds"] == [0.0, -11.0, 9.0, -3.0]
    doors = VR.wall_openings(d)
    assert len(doors) == 1
    door = doors[0]
    assert door["op"]["face"] == "N" and (door["x"], door["y"]) == (4.5, -3.0)
    deposits = VR.wall_openings(d, kinds=("safe_deposit",))
    assert sorted((e["x"], e["op"]["face"]) for e in deposits) == \
        [(0.0, "E"), (9.0, "W")]
    crack = [o for o in d["objectives"] if o["id"] == "crack_vault"][0]
    cash = [o for o in d["loot"] if o["id"] == "vault_cash"][0]
    assert (crack["x"], crack["y"], crack["room"]) == (4.5, -2.25, "vault_room_east")
    assert cash["room"] == "vault"
    fails, _ = layout_lint.gate(d)[:2]
    assert fails == [], fails


def test_the_preset_lost_three_lint_failures_not_gained_one():
    """0.129.0's bank preset failed L11 once and L10 twice in its basement,
    one room over the whole storey cut by a wall. Both modes build clean."""
    for mode in ("heist", "assault"):
        assert layout_lint.gate(_bank(mode=mode))[0] == [], mode


def test_it_is_idempotent():
    d = _bank(enrich=False)
    VR.enclose_vaults(d)
    again = copy.deepcopy(d)
    assert VR.enclose_vaults(again) == []
    assert again == d


def test_a_door_inside_the_vault_is_slid_clear_of_it_and_its_swing():
    d = _spec("bank_branch_a02")
    ends = [(e["along"], e["op"].get("kind")) for e in
            VR.wall_openings(d, kinds=("door",))
            if e["story"] == -1 and e["line"] == 0.0]
    assert ends == [(0.5, "door")]          # was -4.5, inside the vault
    vault = [r for r in d["rooms"] if r["id"] == "vault"][0]
    assert vault["bounds"] == [-8.0, -11.0, 0.0, -3.0]


def test_a_vault_with_no_room_says_so():
    d = _spec("bank")
    report = VR.enclose_vaults(copy.deepcopy(d))
    assert [(r["enclosed"], r["why"]) for r in report] == \
        [(False, "no room holds the vault")]


def test_a_vault_with_every_corner_blocked_is_left_with_the_reasons():
    d = _bank(enrich=False)
    # a solid an author placed in the swing of each corner's door (the fourth
    # corner is already the service stair's)
    authored = [{"name": "pillar_%d" % i, "x": x, "y": y, "z": -2.0,
                 "size_x": 1.0, "size_y": 1.0, "size_z": 3.0}
                for i, (x, y) in enumerate(((4.5, -1.5), (10.5, 1.5),
                                            (4.5, 1.5), (10.5, -1.5)))]
    d["volumes"].extend(authored)
    report = VR.enclose_vaults(d)
    assert [r["enclosed"] for r in report] == [False]
    assert "stands where a vault wall or its swing would" in report[0]["why"]
    assert any(VR.is_vault_volume(v) for v in d["volumes"])


def test_the_library_banks_have_vault_rooms():
    for name in ("bank_branch_a02", "bank_branch_a03", "bank_job"):
        d = _spec(name)
        assert not [v for v in d["volumes"] if VR.is_vault_volume(v)], name
        doors = VR.wall_openings(d)
        assert len(doors) == 1 and doors[0]["op"]["face"] in VR.BEARING, name
        assert VR.findings(d)[0] == [], name
        assert VR.enclose_vaults(copy.deepcopy(d)) == [], name


def test_is_vault_volume_keeps_safes_and_doors_out():
    assert VR.is_vault_volume({"name": "VAULT", "size_x": 5, "size_y": 5,
                               "size_z": 3})
    for v in ({"name": "basement_vault_block", "size_x": 7, "size_y": 5,
               "size_z": 1.3},
              {"name": "VAULT_DOOR", "size_x": 1.6, "size_y": 0.5,
               "size_z": 2.4},
              {"name": "vault_safe_block", "size_x": 5, "size_y": 5,
               "size_z": 1.7}):
        assert not VR.is_vault_volume(v), v["name"]


# ------------------------------------------------------- the second way in
def test_the_vault_has_a_second_way_in_from_another_room():
    """A breach, reinforceable, on the host wall the vault shares with the
    next room -- a route the door's approach does not share."""
    d = _spec("bank_branch_a02")
    breaches = [e for e in VR.wall_openings(d, kinds=("breach",))
                if str(e["op"].get("tag", "")).startswith("vault_breach")]
    assert len(breaches) == 1
    b = breaches[0]
    assert (b["axis"], b["line"], b["along"]) == ("Y", 0.0, -7.0)
    assert b["op"]["breach_class"] == "reinforceable" and b["op"]["reinforceable"]
    assert level_design._room_containing(d, -1, 0.6, -7.0)["id"] == "vault_east"
    assert level_design._room_containing(d, -1, -0.6, -7.0)["id"] == "vault"


def test_tactical_sees_the_vault_and_its_two_ways_in():
    import tactical
    for name in ("bank_branch_a02", "bank_branch_a03", "bank_job"):
        sp = spec_from_dict(_spec(name))
        with contextlib.redirect_stdout(io.StringIO()):
            errors, _w, _s = tactical.analyze(sp)
        assert errors == [], (name, errors)
        adj = tactical.build_graph(sp)
        assert {"vault_west", "vault_east"} <= adj["vault"] or \
            {"vault_room_east"} <= adj["vault"], (name, adj["vault"])


def test_a_nested_room_wins_and_a_touching_one_does_not():
    """`tactical._room_at`: a room inside another owns its floor (layout_lint's
    rule); two rooms that only touch keep spec order on the shared edge, which
    `test_stair_gameplay`'s discharge fixture depends on."""
    import tactical
    from spec_types import LevelSpec, Room
    sp = LevelSpec(name="t", rooms=[
        Room(id="hall", story=0, bounds=[-10, -10, 10, 10]),
        Room(id="vault", story=0, bounds=[-8, -10, 0, -3]),
        Room(id="next", story=0, bounds=[10, -10, 20, 10])])
    assert tactical._room_at(sp, 0, -4, -6) == "vault"
    assert tactical._room_at(sp, 0, 5, 5) == "hall"
    assert tactical._room_at(sp, 0, 10, 0) == "hall"     # touching: first wins


def test_full_height_fixtures_sink_under_the_room_skins(tmp_path):
    """A vault door's slot is the wall's full height, so its bottom and top
    lie on the room's floor and ceiling skins. Composed unsunk onto the rebuilt
    `bank_branch_a02`, the door and two deposit walls made 14 same-facing
    pairs; the composer sinks them like every other wall-height module."""
    lib = str(tmp_path)
    slot = {"slot_id": "int_-1_6_open0", "role": "vault_door",
            "size_mod": "full", "style": 1,
            "transform": {"translation": [-4.0, -3.0, -1.95], "rot_y": 0,
                          "scale": [1, 1, 1]},
            "fit": {"dims": [3.6, 0.3, 3.3], "pivot": "center",
                    "openings": [{"kind": "vault", "width": 1.3,
                                  "height": 2.1, "sill": 0.0}]}}
    stem, _ = themed_tscn.resolve_themed_stem(slot, "delco_1997", 1)
    open(os.path.join(lib, stem + ".glb"), "wb").write(b"glTF")
    out = str(tmp_path / "s.tscn")
    themed_tscn.write_themed_tscn([slot], "b", out, theme="delco_1997",
                                  library_dir=lib)
    text = open(out, encoding="utf-8").read()
    want = -1.95 - themed_tscn.SLAB_CAP_SINK
    assert ("%s, 3.0)" % tscn_export._f(want)) in text, text
    assert {"vault_door", "safe_deposit_boxes"} <= themed_tscn._SLAB_CAP_SINK_ROLES
