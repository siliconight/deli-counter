"""Pure tests for stair-cores-first generation (no bpy).
Run: python3 test_stair_core.py"""
import copy

import presets
import stair_core as C
import stairwell as S
import ladder as L
import navigability
from spec_loader import spec_from_dict


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


MULTI = [p for p in sorted(presets.REGISTRY)
         if not presets.REGISTRY[p]().get("facade")
         and presets.REGISTRY[p]().get("n_stories", 1) >= 2]


# --- unit: partition surgery ---------------------------------------------------

def test_trim_partition_splits_around_shaft():
    p = {"story": 0, "axis": "Y", "pos": 0.0, "start": -10.0, "end": 10.0,
         "openings": [{"kind": "door", "pos": -0.4, "width": 1.2},
                      {"kind": "door", "pos": 0.4, "width": 1.2}]}
    fp = (-1.0, -2.0, 1.0, 2.0)          # shaft the wall crosses
    segs = C._trim_partition(p, fp, 0.3)
    assert len(segs) == 2
    (a, b) = sorted(segs, key=lambda s: s["start"])
    assert a["start"] == -10.0 and a["end"] == -2.0
    assert b["start"] == 2.0 and b["end"] == 10.0
    # each side kept its own door, remapped into the new span
    assert len(a["openings"]) == 1 and len(b["openings"]) == 1
    along_a = a["start"] + (a["openings"][0]["pos"] + 0.5) * 8.0
    assert abs(along_a - (-8.0)) < 1e-6  # original door at -10+0.1*20 = -8


def test_trim_partition_leaves_nonparallel_walls_alone():
    p = {"story": 0, "axis": "Y", "pos": 5.0, "start": -10.0, "end": 10.0,
         "openings": []}
    assert C._trim_partition(p, (-1.0, -2.0, 1.0, 2.0), 0.3) == [p]


def test_punch_door_on_doorless_landing_crossing():
    p = {"story": 0, "axis": "X", "pos": -2.5, "start": -5.0, "end": 5.0,
         "openings": []}
    land = (-0.6, -3.2, 0.6, -2.0)       # landing the wall crosses... no:
    land = (-2.0, -3.0, 2.0, -2.0)       # spans x -2..2 at the wall's y
    punched = C._punch_door(p, land, 0.3)
    assert punched and len(p["openings"]) == 1
    assert p["openings"][0]["kind"] == "door"


def test_punch_door_skips_already_doored_crossing():
    p = {"story": 0, "axis": "X", "pos": -2.5, "start": -5.0, "end": 5.0,
         "openings": [{"kind": "door", "pos": 0.0, "width": 1.2}]}
    assert not C._punch_door(p, (-2.0, -3.0, 2.0, -2.0), 0.3)
    assert len(p["openings"]) == 1


def test_subtract_room_guillotine():
    pieces = C._subtract_room([-10, -10, 10, 10], (-1, -2, 1, 2))
    assert len(pieces) == 4
    total = sum((r[2] - r[0]) * (r[3] - r[1]) for r in pieces)
    assert abs(total - (400 - 2 * 4)) < 1e-6   # area conserved minus the cut
    assert C._subtract_room([-10, -10, -5, -5], (0, 0, 1, 1)) \
        == [(-10, -10, -5, -5)]                # disjoint: unchanged


# --- reserve ------------------------------------------------------------------

def test_reserve_returns_oriented_stamped_cores():
    spec = presets.REGISTRY["office"]()
    cores = C.reserve(spec, "office_lowrise")
    assert cores
    for c in cores:
        sd = c["stair"]
        assert sd["facing"] in ("N", "E", "S", "W")
        assert sd["role"] in S.STAIR_ROLES
        assert sd["meta"]["generated_by"] == "stair_core"
        fp, well = c["footprint"], c["well"]
        assert well[0] <= fp[0] and well[1] <= fp[1]   # well contains flight
        assert well[2] >= fp[2] and well[3] >= fp[3]


def test_full_vault_basement_gets_service_connector():
    spec = presets.REGISTRY["bank"]()        # whole-basement vault room
    cores = C.reserve(spec, "office_lowrise")
    mains = [c for c in cores if c["stair"]["from_story"] == 0]
    down = [c for c in cores if c["stair"]["from_story"] == -1]
    assert mains and len(down) == 1
    assert down[0]["stair"]["to_story"] == 0
    assert down[0]["stair"]["role"] == "service"


# --- apply: the floorplan adapts ----------------------------------------------

def test_apply_builds_wells_and_splits_rooms():
    spec = presets.make("office", name="t_cf", stairs_first=True)
    wells = [r for r in spec["rooms"] if r.get("role") == "stairwell"]
    assert wells
    sp = spec_from_dict(spec)
    for i, st in enumerate(sp.stairs):
        if st.from_story < 0:
            continue
        room = S._approach_room(sp, 0, st)
        assert room is not None and room.role == "stairwell", \
            (S.stair_ident(st, i), room and room.id)


def test_no_partition_crosses_a_core_shaft():
    spec = presets.make("bank", name="t_cf2", stairs_first=True)
    sp = spec_from_dict(spec)
    for st in sp.stairs:
        fp = S.footprint_rect(st)
        served = S.floors_served(sp, st)
        t2 = sp.wall_thick / 2
        for p in sp.partitions:
            if p.story not in served:
                continue
            lo, hi = sorted([p.start, p.end])
            if p.axis == "Y":
                crosses = (fp[0] - t2 <= p.pos <= fp[2] + t2
                           and min(hi, fp[3]) - max(lo, fp[1]) > 1e-6)
            else:
                crosses = (fp[1] - t2 <= p.pos <= fp[3] + t2
                           and min(hi, fp[2]) - max(lo, fp[0]) > 1e-6)
            assert not crosses, (st.id, p.axis, p.pos)


def test_room_references_remapped_after_split():
    spec = presets.make("bank", name="t_cf3", stairs_first=True)
    room_ids = {r["id"] for r in spec["rooms"]}
    for key in ("objectives", "loot", "markers"):
        for e in spec.get(key) or []:
            if e.get("room"):
                assert e["room"] in room_ids, (key, e.get("id"), e["room"])


def test_core_first_presets_review_clean():
    for p in MULTI:
        spec = presets.make(p, name=f"t_cf_{p}", stairs_first=True)
        sp = spec_from_dict(spec)
        serrs, _, _ = S.check(sp)
        lerrs, _, _ = L.check(sp)
        nerrs, _, _ = navigability.check(sp)
        assert serrs == [], (p, serrs[:2])
        assert lerrs == [], (p, lerrs[:2])
        assert nerrs == [], (p, nerrs[:2])


def test_core_first_is_deterministic():
    a = presets.make("hospital", name="t_det", stairs_first=True)
    b = presets.make("hospital", name="t_det", stairs_first=True)
    assert a["stairs"] == b["stairs"]
    assert a["rooms"] == b["rooms"] and a["partitions"] == b["partitions"]


def test_single_story_and_facade_are_noops():
    spec = {"name": "t", "n_stories": 1, "footprint_x": 20, "footprint_y": 20}
    assert C.core_first(copy.deepcopy(spec), "office_lowrise") == []
    fac = {"name": "t", "n_stories": 3, "facade": True,
           "footprint_x": 20, "footprint_y": 20}
    assert C.core_first(copy.deepcopy(fac), "office_lowrise") == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all stair_core tests passed")
