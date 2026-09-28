"""0.150.0 -- a convenience store has its frozen drink station.

`migrate_slush_machine.py` puts Zoo 1.15.0's `slush_machine` against a solid
wall of every convenience store's sales floor: clear of the openings, an
aisle all round, facing the room, nearest the coffee island (or the
register). These hold for every store in the library, and the built slots
carry the species, so a spec edit that does not reach the build is caught.
"""
import json
import os

import pytest

import level_design
import migrate_slush_machine as M

HERE = os.path.dirname(os.path.abspath(__file__))
STORES = ("cr_gas", "fuel_stop_heist", "gas_station", "gas_station_a01", "gas_station_a02",
          "gas_station_a03", "gas_street", "gs_corner_station", "stop_n_go")


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8"))


def _box(v):
    return (v["x"] - v["size_x"] / 2, v["y"] - v["size_y"] / 2, v["x"] + v["size_x"] / 2, v["y"] + v["size_y"] / 2)


def test_every_convenience_store_has_one_station_and_nothing_else_does():
    assert M.main(["--check"]) == 0, "run: python migrate_slush_machine.py"
    import glob
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-5]
        if name.startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        n = sum(1 for v in d.get("volumes") or [] if v.get("name") == M.NAME)
        assert n == (1 if name in STORES else 0), (name, n)
    assert set(STORES) == {n for n in STORES if M.is_store(_load(n))}


def test_the_station_is_zoos_size():
    """Zoo's `slush_machine_forms.DC_SIZES[0]`, copied as a literal the way
    `test_furnish._ZOO_RANGES` copies Zoo's ranges: 1.6 m is what holds two
    barrels and the six-bottle rail."""
    assert (M.WIDTH, M.DEPTH, M.HEIGHT) == (1.6, 0.7, 2.0)


def test_each_station_stands_on_a_solid_wall_facing_the_room_with_an_aisle():
    aisle = level_design.island_aisle_width()
    for name in STORES:
        d = _load(name)
        v = next(x for x in d["volumes"] if x["name"] == M.NAME)
        room = next(r for r in d["rooms"] if r["id"] == M.ROOM)
        rx0, ry0, rx1, ry1 = room["bounds"]
        x0, y0, x1, y1 = _box(v)
        assert rx0 <= x0 and x1 <= rx1 and ry0 <= y0 and y1 <= ry1, name
        back = float(d.get("wall_thick") or 0.3) / 2 + level_design._WALL_PIECE_AIR
        # its back is `back` off exactly one of the room's sides, and its
        # front faces away from that side (the cooler wall's measured rule)
        sides = [("X", ry0, +1, y0), ("X", ry1, -1, y1), ("Y", rx0, +1, x0), ("Y", rx1, -1, x1)]
        on = [(ax, line, sign) for ax, line, sign, edge in sides if abs(edge - (line + sign * back)) < 1e-3]
        assert len(on) == 1, (name, on)
        ax, line, sign = on[0]
        assert (v.get("rot_z") == 180.0) == (sign > 0), name
        assert (v["size_x"] > v["size_y"]) == (ax == "X"), name
        # not against a glazed exterior wall
        assert not [w for w in M._walls(d, room) if w[0] == ax and abs(w[1] - line) < 1e-6
                    and w[5] in level_design._glazed_walls(d, 0)], name
        # no authored volume within the aisle, on any side -- but a
        # neighbour against the same wall (0.152.0: the roller grill), which
        # keeps `NEIGHBOUR_GAP` along the wall and shares the aisle in front
        for bx0, by0, bx1, by1 in M._obstacles(d):
            if (bx0, by0, bx1, by1) == (x0, y0, x1, y1):
                continue
            gap_x = max(bx0 - x1, x0 - bx1)
            gap_y = max(by0 - y1, y0 - by1)
            across_b = (by0, by1) if ax == "X" else (bx0, bx1)
            same_wall = min(abs(across_b[0] - line), abs(across_b[1] - line)) <= back + M.NEIGHBOUR_TOL
            need = M.NEIGHBOUR_GAP if same_wall else aisle
            assert max(gap_x, gap_y) >= need - 1e-6, (name, (bx0, by0, bx1, by1))


def test_a02s_station_is_clear_of_the_door_to_food_service():
    """a02, the store club_block_014 stands: on the partition at x = 7 whose
    `sales_to_food` door is 1.8 m wide at its centre (y = -5)."""
    d = _load("gas_station_a02")
    v = next(x for x in d["volumes"] if x["name"] == M.NAME)
    x0, y0, x1, y1 = _box(v)
    assert abs(x1 - (7.0 - 0.16)) < 1e-6 and "rot_z" not in v
    door_lo, door_hi = -5.0 - 0.9, -5.0 + 0.9
    clear = level_design._FURNISH_OPENING_CLEAR
    assert y1 <= door_lo - clear + 1e-6 or y0 >= door_hi + clear - 1e-6


def test_the_built_slots_carry_the_species():
    for name in STORES:
        slots = json.load(open(os.path.join(HERE, "build", name + ".slots.json"), encoding="utf-8"))
        rows = slots["slots"] if isinstance(slots, dict) else slots
        got = [s for s in rows if str(s.get("slot_id", "")).startswith(M.NAME)]
        assert len(got) == 1 and got[0].get("species") == "slush_machine", (name, got)


@pytest.mark.parametrize("mode", ["heist", "assault"])
def test_a_store_made_from_the_preset_has_gondolas_and_a_station(mode):
    """0.151.0: 0.149.0 and 0.150.0 migrated the checked-in stores and left
    `presets.gas_station` emitting `aisle_N`, which routes to nothing, and
    no station. A store generated from it later is held to the library's."""
    import presets
    import prop_species
    spec = presets.gas_station(mode=mode)
    routed = [prop_species.species_for_name(v["name"]) for v in spec["volumes"]]
    assert routed.count("snack_gondola") == 2, [v["name"] for v in spec["volumes"]]
    assert routed.count("slush_machine") == 1
    assert M.is_store(spec)
    # placed by the migration's own rule: the same station the checked-in
    # `gas_station` spec was given, and a second pass adds nothing
    v = next(x for x in spec["volumes"] if x["name"] == M.NAME)
    lib = next(x for x in _load("gas_station")["volumes"] if x["name"] == M.NAME)
    assert v == lib, (v, lib)
    assert M.plan_station(spec)[0] is not None and M.migrate(spec) == (None, "already has one")


def test_the_migration_is_idempotent_and_refuses_rather_than_forces(tmp_path):
    d = _load("gas_station_a02")
    d["volumes"] = [v for v in d["volumes"] if v["name"] != M.NAME]
    (tmp_path / "a.json").write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    assert M.main(["--check", "--dir", str(tmp_path)]) == 1
    assert M.main(["--dir", str(tmp_path)]) == 0
    first = (tmp_path / "a.json").read_bytes()
    assert M.main(["--dir", str(tmp_path)]) == 0
    assert (tmp_path / "a.json").read_bytes() == first
    # every solid wall lined with crates: refused, and says why
    full = _load("gas_station_a02")
    full["volumes"] = [v for v in full["volumes"] if v["name"] != M.NAME]
    room = next(r for r in full["rooms"] if r["id"] == M.ROOM)["bounds"]
    for i, (x, y, sx, sy) in enumerate(((room[0] + 0.5, (room[1] + room[3]) / 2, 1.0, room[3] - room[1]),
                                        (0.0 + (room[0] + room[2]) / 2, room[3] - 0.5, room[2] - room[0], 1.0),
                                        (room[2] - 0.5, (room[1] + room[3]) / 2, 1.0, room[3] - room[1]))):
        full["volumes"].append({"name": "crate_wall_%d" % i, "x": x, "y": y, "z": 0.5,
                                "size_x": sx, "size_y": sy, "size_z": 1.0})
    vol, why = M.plan_station(full)
    assert vol is None and "clear" in why, (vol, why)
