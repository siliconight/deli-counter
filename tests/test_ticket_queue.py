"""A box office's ticket window and the queue in front of it (0.243.0, the factory's roadmap 267), and a bank teller
line's queue (0.244.0, roadmap 275; `ticket_queue.py`).

The walker, 2026-10-20: "queue lanes to the box office", in retractable-belt stanchions -- "metal barriers are for
outdoor concerts or riot protection from police" -- and "stanchion or stanchions are likley more common for banks and
indoor common areas". Every test here fails on 0.242.0, which has no `ticket_queue`; the teller-line tests fail on
0.243.0, which queues no teller line.

THE CROSS-REPO PINS run when Zoo is found: `$DC_ZOO_ROOT`, else `../zoo`, as `test_vault_room.py`'s do.
"""
import copy
import importlib
import json
import math
import os
import sys
import types

import pytest

import agent_contract
import floors
import level_design
import prop_species
import ticket_queue as tq
import vault_room

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(os.path.dirname(HERE), "zoo")
_PALETTE = [{"id": "concrete", "acoustic": "Concrete"}, {"id": "drywall", "acoustic": "Drywall"},
            {"id": "glass", "acoustic": "Glass"}, {"id": "metal", "acoustic": "Metal"},
            {"id": "wood", "acoustic": "Wood"}]


def _theatre(door_pos=0.4, office_id="box_office", public_role="public_entry", extra_doors=()):
    """A 30 x 20 m theatre: a lobby along the south, the box office and a back room behind a partition at y 2."""
    return {"name": "t_theatre", "mode": "pvp_heist", "seed": 7, "footprint_x": 30, "footprint_y": 20,
            "story_height": 4.0, "n_stories": 1, "default_material": "concrete",
            "materials": copy.deepcopy(_PALETTE),
            "ext_walls": [{"wall": "S", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 2.4}]}],
            "partitions": [{"story": 0, "axis": "X", "pos": 2.0, "start": -15.0, "end": 15.0,
                            "openings": [{"kind": "door", "pos": door_pos, "width": 1.25}]
                            + [{"kind": "door", "pos": p, "width": 1.25} for p in extra_doors]},
                           {"story": 0, "axis": "Y", "pos": -5.0, "start": 2.0, "end": 10.0,
                            "openings": [{"kind": "door", "pos": 0.0, "width": 1.25}]}],
            "rooms": [{"id": "lobby", "story": 0, "bounds": [-15.0, -10.0, 15.0, 2.0], "role": public_role,
                       "combat_range": "medium"},
                      {"id": office_id, "story": 0, "bounds": [-15.0, 2.0, -5.0, 10.0], "role": "objective_room",
                       "combat_range": "close"},
                      {"id": "back_room", "story": 0, "bounds": [-5.0, 2.0, 15.0, 10.0], "role": "connector",
                       "combat_range": "medium"}],
            "volumes": [], "markers": [], "stairs": [], "ladders": []}


def _arena():
    with open(os.path.join(HERE, "specs", "arena_a02.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _runs(spec):
    return [v for v in spec.get("volumes") or [] if str(v.get("name", "")).startswith("stanchion_run_")]


def _box(v):
    return (v["x"] - v["size_x"] / 2.0, v["y"] - v["size_y"] / 2.0, v["x"] + v["size_x"] / 2.0,
            v["y"] + v["size_y"] / 2.0)


def _standing(spec, story):
    """The volumes standing on `story`'s floor, as `ticket_queue._keepouts` reads them: on that storey
    (`level_design._on_storey`) and not hung over it (`level_design._hung`). A plan rectangle is not a storey -- the
    first draft of the bank checks below read a basement's tables as standing in a ground-floor queue."""
    sh = level_design._story_height(spec)
    floor = story * sh
    return [o for o in spec.get("volumes") or []
            if level_design._on_storey(float(o["z"]), float(o["size_z"]), floor, sh)
            and not level_design._hung(o, floor)]


def _ticket_window(spec):
    got = [(p, op) for p in spec.get("partitions") or [] for op in p.get("openings") or []
           if op.get("tag") == "ticket_window"]
    assert len(got) == 1, got
    return got[0]


# ---------------------------------------------------------------- the words and the numbers

def test_a_box_office_is_named_by_its_words():
    yes = ("box_office", "ticket_booth", "tickets", "boxoffice", "ticketing_hall", "east_box_office")
    no = ("box_room", "office", "back_office", "post_office", "lobby", "event_floor", "cashier_cage")
    assert all(tq.is_box_office({"id": r}) for r in yes)
    assert not any(tq.is_box_office({"id": r}) for r in no)


def test_the_numbers_are_the_contracts():
    """A lane is a corridor to the bake, so its clear floor is a stair flight's: the corridor minimum and one cell. The
    floor in front of the window is a door's approach. Nothing here is a literal a body's size could move under."""
    assert tq.lane_clear() == agent_contract.stair_flight_width()
    assert math.isclose(tq.pitch(), agent_contract.stair_flight_width() + tq.RUN_DEPTH)
    assert tq.service_depth() == agent_contract.door_approach()
    assert tq.line_min() == tq.pitch()
    assert tq.lane_clear() > agent_contract.min_corridor_width()


def _zoo_genome():
    path = os.path.join(ZOO, "zoo_keeper", "genome", "species", "stanchion_run.json")
    if not os.path.isfile(path):
        pytest.skip("zoo's stanchion_run genome not found at %s (set DC_ZOO_ROOT)" % path)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_stanchion_numbers_are_zoos():
    g = _zoo_genome()
    dims = g["dimensions"]
    assert tq.RUN_DEPTH == dims["depth"]["default"] and tq.RUN_HEIGHT == dims["height"]["default"]
    assert tq.RUN_MIN == dims["width"]["min"]
    assert g["materials"]["default"] == tq.RUN_MATERIAL and tq.RUN_MATERIAL in g["materials"]["options"]
    # a line the rule lays is a run Zoo draws
    assert dims["width"]["min"] <= tq.line_min() and tq.MAX_SPAN - tq.lane_clear() <= dims["width"]["max"]


def test_a_run_is_the_species_and_a_lone_post_is_still_the_single_stanchion():
    assert prop_species.species_for_name("stanchion_run_0_3") == "stanchion_run"
    assert prop_species.species_for_name("stanchion_rcce455f7_5") == "queue_stanchion"
    assert prop_species.owns_collision("stanchion_run")
    assert level_design._prop_material({"materials": []}, "stanchion_run_0_0") == tq.RUN_MATERIAL
    # the run's name carries no cover word: a belt is not cover
    assert not level_design._looks_like_cover({"name": "stanchion_run_0_0", "size_x": 4.8, "size_y": 0.356,
                                               "size_z": tq.RUN_HEIGHT})


# ---------------------------------------------------------------- arena_a02, as the library carries it

def test_arena_a02_sells_through_a_ticket_window_in_the_box_offices_wall():
    """One window, in the partition between the box office and the event floor, inside the office's run, on the
    builder's grid -- so it is cut where its queue was laid -- and a jamb clear of the secure door and the office's
    east wall."""
    spec = _arena()
    p, op = _ticket_window(spec)
    assert (p["axis"], p["pos"]) == ("X", 5.9)
    assert (op["kind"], op["width"], op["sill"], op["height"], op["vaultable"]) == (
        "window", tq.WINDOW_W, tq.WINDOW_SILL, tq.WINDOW_H, False)
    assert "breakable" not in op
    (e,) = [e for e in vault_room.wall_openings(spec, kinds=("window",)) if e["op"] is op]
    run = p["end"] - p["start"]
    assert math.isclose(e["along"], op["pos"] * run, abs_tol=1e-6)
    office = [r for r in spec["rooms"] if r["id"] == "box_office"][0]
    w0, w1 = e["along"] - op["width"] / 2.0, e["along"] + op["width"] / 2.0
    assert office["bounds"][0] + 0.15 + tq.JAMB <= w0 and w1 <= office["bounds"][2] - 0.15 - tq.JAMB
    for o in vault_room.wall_openings(spec, kinds=("door", "breach")):
        if o["host"] is p:
            hw = tq._opening_width(o["op"]) / 2.0
            assert w1 + tq.JAMB <= o["along"] - hw or o["along"] + hw <= w0 - tq.JAMB, o["op"]


def test_arena_a02s_queue_switches_back_to_the_window():
    """Four lines, three lanes, parallel to the wall: each line a lane apart, stopping a turn short at alternate ends,
    the first -- nearest the wall -- short at the window's end, so the last lane lets out in front of the window."""
    spec = _arena()
    runs = sorted(_runs(spec), key=lambda v: -v["y"])
    assert [v["name"] for v in sorted(_runs(spec), key=lambda v: v["name"])] == [
        "stanchion_run_0_%d" % k for k in range(4)]
    assert all(v["material"] == tq.RUN_MATERIAL and v["size_z"] == tq.RUN_HEIGHT
               and v["size_y"] == tq.RUN_DEPTH and math.isclose(v["z"], tq.RUN_HEIGHT / 2.0) for v in runs)
    face = 5.9 - 0.15
    assert math.isclose(face - _box(runs[0])[3], tq.service_depth(), abs_tol=1e-3)
    for a, b in zip(runs, runs[1:]):
        assert math.isclose(_box(a)[1] - _box(b)[3], tq.lane_clear(), abs_tol=1e-3)
    _p, op = _ticket_window(spec)
    wx = op["pos"] * 50.0
    lo = min(_box(v)[0] for v in runs)
    hi = max(_box(v)[2] for v in runs)
    ends = [(_box(v)[0], _box(v)[2]) for v in runs]
    # the window's end is the one line 0 stops short of
    window_low = ends[0][0] > lo + 1e-6
    for k, (x0, x1) in enumerate(ends):
        short_at_window = (k % 2 == 0)
        short_low = x0 > lo + 1e-6
        assert short_low == (short_at_window == window_low), (k, x0, x1)
        assert math.isclose((x1 - x0), hi - lo - tq.lane_clear(), abs_tol=1e-3)
    gap = (lo, lo + tq.lane_clear()) if window_low else (hi - tq.lane_clear(), hi)
    assert gap[0] - 1e-6 <= wx - tq.WINDOW_W / 2.0 and wx + tq.WINDOW_W / 2.0 <= gap[1] + 1e-6


def test_arena_a02s_queue_stands_clear_of_everything():
    """Measured from the spec, not asked of `ticket_queue`: nothing else stands inside the queue, wall face to the
    last line, and every line keeps `min_corridor_width()` from every other standing volume in the event floor, every
    walkable opening's approach and the walls but its own."""
    spec = _arena()
    cw = agent_contract.min_corridor_width()
    runs = _runs(spec)
    rect = (min(_box(v)[0] for v in runs), min(_box(v)[1] for v in runs),
            max(_box(v)[2] for v in runs), 5.9 - 0.15)
    floor_room = [r for r in spec["rooms"] if r["id"] == "event_floor"][0]["bounds"]
    others = [v for v in _standing(spec, 0) if v not in runs]
    for v in others:
        b = _box(v)
        assert not (b[0] < rect[2] and rect[0] < b[2] and b[1] < rect[3] and rect[1] < b[3]), v["name"]
        if floor_room[0] <= v["x"] <= floor_room[2] and floor_room[1] <= v["y"] <= floor_room[3]:
            for r in runs:
                assert level_design._box_gap(_box(r), b) >= cw - 1e-9, (r["name"], v["name"])
    da = agent_contract.door_approach()
    for e in vault_room.wall_openings(spec, kinds=("door", "garage", "breach", "vault")):
        if e["story"] != 0:
            continue
        hw, d = tq._opening_width(e["op"]) / 2.0, 0.15 + da
        ap = ((e["along"] - hw, e["line"] - d, e["along"] + hw, e["line"] + d) if e["axis"] == "X"
              else (e["line"] - d, e["along"] - hw, e["line"] + d, e["along"] + hw))
        clipped = (max(ap[0], floor_room[0]), max(ap[1], floor_room[1]), min(ap[2], floor_room[2]),
                   min(ap[3], floor_room[3]))
        if clipped[2] - clipped[0] <= 1e-6 or clipped[3] - clipped[1] <= 1e-6:
            continue
        for r in runs:
            assert level_design._box_gap(_box(r), clipped) >= cw - 1e-9, (r["name"], e["op"])
    # the event floor's west wall, the nearest wall but the queue's own
    for r in runs:
        assert _box(r)[0] - (-25.0 + 0.15) >= cw


def test_arena_a02_keeps_no_steel_barricade_and_declares_the_stanchions_kind_last():
    """0.242.0's four crowd barricades stood across arena_a02's event floor; the walker: "metal barriers are for
    outdoor concerts or riot protection from police". They and `metal_bare`, which they alone wore, are gone, and
    `metal_painted` is declared after the finish palette, so no finish slot's style moved."""
    spec = _arena()
    assert not [v for v in spec["volumes"] if "barrier" in v["name"].lower()]
    ids = [m["id"] for m in spec["materials"]]
    assert ids == ["concrete", "drywall", "glass", "metal", "wood", "carpet", "tile", "ceiling_tile", "plaster",
                   "metal_painted"]


def test_the_library_is_a_fixed_point_of_the_rule():
    """Re-run over every library spec, both rules change nothing -- through the migration too, which sets furniture
    aside, fits and refurnishes: arena_a02 already has its box office's queue, four banks their teller lines', and the
    fifth teller line cannot hold one."""
    import glob
    import migrate_ticket_queue
    offices, queued = [], []
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        before = json.dumps(spec, sort_keys=True)
        tq.lay_queues(spec)
        assert json.dumps(spec, sort_keys=True) == before, path
        migrate_ticket_queue.migrate(spec)
        assert json.dumps(spec, sort_keys=True) == before, path
        offices += [(os.path.basename(path), r["id"]) for r in spec.get("rooms") or [] if tq.is_box_office(r)]
        if any(v["name"].startswith("stanchion_run_t") for v in spec.get("volumes") or []):
            queued.append(os.path.basename(path)[:-5])
    assert offices == [("arena_a02.json", "box_office")]
    assert queued == ["bank_branch_a02", "bank_branch_a03", "bank_job", "credit_union_a01"], queued


# ---------------------------------------------------------------- the rule, on a building made for it

def test_a_theatre_gets_three_lanes_and_its_window():
    spec = _theatre()
    (r,) = tq.queue_box_offices(spec)
    assert r["queued"] and r["lanes"] == 3 and len(r["runs"]) == 4, r
    _p, op = _ticket_window(spec)
    assert op["kind"] == "window"
    # idempotent: a second pass adds nothing and reports nothing
    before = json.dumps(spec, sort_keys=True)
    assert tq.queue_box_offices(spec) == []
    assert json.dumps(spec, sort_keys=True) == before


def test_declaring_the_kind_moves_no_style():
    """A slot's style is its material's place in `floors.palette_ids`. The rule declares the finish palette before
    `metal_painted` when a spec has not, so every material the spec could already name keeps its place."""
    from spec_loader import spec_from_dict
    spec = _theatre()
    before = floors.palette_ids(spec_from_dict(copy.deepcopy(spec)))
    tq.queue_box_offices(spec)
    after = floors.palette_ids(spec_from_dict(copy.deepcopy(spec)))
    assert after[:len(before)] == before and after[len(before):] == [tq.RUN_MATERIAL], (before, after)


def test_a_box_office_with_no_public_neighbour_gets_none():
    spec = _theatre(public_role="connector")
    spec["rooms"][0]["id"] = "yard"
    (r,) = tq.queue_box_offices(spec)
    assert not r["queued"] and r["why"] == "no interior wall shared with a public room", r
    assert not _runs(spec) and not any(op.get("tag") for p in spec["partitions"] for op in p["openings"])


def test_a_wall_full_of_doors_leaves_the_queue_unlaid_and_says_why():
    """Doors every three metres along the office's wall: no window clears them by a jamb with a queue clear of their
    approaches, and the rule lays nothing rather than a queue in a doorway."""
    spec = _theatre(door_pos=-0.4, extra_doors=(-0.3, -0.2, -0.1, 0.0))
    (r,) = tq.queue_box_offices(spec)
    assert not r["queued"] and r["why"], r
    assert not _runs(spec)


def test_enrich_lays_the_queue_before_cover_and_furniture():
    """`enrich` lays the queue before it seeds cover and furnishes, so nothing it places stands in a lane."""
    spec = _theatre()
    rep = level_design.enrich(spec)
    assert rep["queues_laid"] == 1, rep
    runs = _runs(spec)
    rect = (min(_box(v)[0] for v in runs), min(_box(v)[1] for v in runs), max(_box(v)[2] for v in runs), 2.0 - 0.15)
    placed = [v for v in spec["volumes"] if v not in runs]
    assert placed, "enrich placed nothing: the check below would pass vacuously"
    for v in placed:
        if v.get("collision") == "none" and v["z"] - v["size_z"] / 2.0 >= 1.8:
            continue
        b = _box(v)
        assert not (b[0] < rect[2] and rect[0] < b[2] and b[1] < rect[3] and rect[1] < b[3]), v["name"]


# ---------------------------------------------------------------- the builder

@pytest.fixture
def dc(monkeypatch):
    """deli_counter against stub bpy/bmesh, as test_prop_species does."""
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def test_the_builder_writes_each_line_as_the_species_with_no_box(dc):
    """Each line is a `stanchion_run` slot, its long side the module's width, its collision the module's own -- no
    greybox box, which would be a 0.97 m wall where a belt is."""
    import skin_style
    from spec_loader import spec_from_dict
    spec = _theatre()
    tq.queue_box_offices(spec)
    s = spec_from_dict(spec)
    b = dc._Builder(s)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in s.materials])
    cols = []
    b._box = lambda *a, **k: None
    b._col_box = lambda name, *a, **k: cols.append(name)
    b._record_surface = lambda *a, **k: None
    b._volumes()
    slots = {x["slot_id"]: x for x in b.slots}
    assert sorted(slots) == ["stanchion_run_0_%d" % k for k in range(4)], sorted(slots)
    assert not [c for c in cols if c.startswith("stanchion_run_")], cols
    for x in slots.values():
        assert x["species"] == "stanchion_run" and x["fit"]["collision"] == "none", x
        assert x["fit"]["dims"] == [4.8, tq.RUN_DEPTH, tq.RUN_HEIGHT], x["fit"]


# ---------------------------------------------------------------- a bank's teller line (0.244.0, roadmap 275)

TELLER_BANKS = ("bank_branch_a02", "bank_branch_a03", "bank_job", "credit_union_a01")


def _spec(name):
    with open(os.path.join(HERE, "specs", name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_the_teller_numbers_are_the_contracts():
    """The floor in front of a counter: a door's approach for the customer at a window and a corridor behind them for
    the next walking along the counter to a free one."""
    assert tq.teller_service_depth() == agent_contract.door_approach() + agent_contract.min_corridor_width()
    assert prop_species.species_for_name("stanchion_run_t0_3") == "stanchion_run"
    assert level_design._prop_material({"materials": []}, "stanchion_run_t0_0") == tq.RUN_MATERIAL


@pytest.mark.parametrize("name", TELLER_BANKS)
def test_a_library_bank_queues_in_front_of_its_counter(name):
    """Four lines parallel to the counter on its public side, the first a teller line's floor off the counter's face,
    each a lane's clear floor from the next, stopping a turn short at alternate ends; the last lane lets out where the
    counter is, so the customer leaving it faces a window. Measured from the spec."""
    spec = _spec(name)
    ((v, story, axis),) = level_design._teller_lines(spec)
    assert axis == "X"
    runs = [r for r in spec["volumes"] if r["name"].startswith("stanchion_run_t0_")]
    assert sorted(r["name"] for r in runs) == ["stanchion_run_t0_%d" % k for k in range(4)]
    public = level_design._public_side(spec, story, tq._host_room(spec, story, v["x"], v["y"]), axis, v["y"])
    face = v["y"] + public * v["size_y"] / 2.0
    runs.sort(key=lambda r: abs(r["y"] - face))
    assert all(r["material"] == tq.RUN_MATERIAL and r["size_y"] == tq.RUN_DEPTH for r in runs)
    near = _box(runs[0])
    assert math.isclose(abs((near[3] if public < 0 else near[1]) - face), tq.teller_service_depth(), abs_tol=1e-3)
    for a, b in zip(runs, runs[1:]):
        assert math.isclose(abs(a["y"] - b["y"]), tq.pitch(), abs_tol=1e-3)
    lo = min(_box(r)[0] for r in runs)
    hi = max(_box(r)[2] for r in runs)
    exit_low = _box(runs[0])[0] > lo + 1e-6
    for k, r in enumerate(runs):
        short_low = _box(r)[0] > lo + 1e-6
        assert short_low == ((k % 2 == 0) == exit_low), (name, k)
    gap = (lo, lo + tq.lane_clear()) if exit_low else (hi - tq.lane_clear(), hi)
    assert v["x"] - v["size_x"] / 2.0 - 1e-6 <= gap[0] and gap[1] <= v["x"] + v["size_x"] / 2.0 + 1e-6, (name, gap)


@pytest.mark.parametrize("name", TELLER_BANKS)
def test_a_library_banks_queue_stands_clear_of_everything(name):
    """Nothing else stands inside the queue, counter face to last line, and every line keeps `min_corridor_width()`
    from every other standing volume in the room, every walkable opening's approach and every wall but the counter."""
    spec = _spec(name)
    ((v, story, axis),) = level_design._teller_lines(spec)
    cw = agent_contract.min_corridor_width()
    runs = [r for r in spec["volumes"] if r["name"].startswith("stanchion_run_t0_")]
    host = tq._host_room(spec, story, v["x"], v["y"])
    public = level_design._public_side(spec, story, host, axis, v["y"])
    face = v["y"] + public * v["size_y"] / 2.0
    ys = [_box(r)[1] for r in runs] + [_box(r)[3] for r in runs]
    rect = (min(_box(r)[0] for r in runs), min(ys + [face]), max(_box(r)[2] for r in runs), max(ys + [face]))
    room = tq._host_room(spec, story, v["x"], face + public * 0.2)["bounds"]
    for o in _standing(spec, story):
        if o in runs or o is v:
            continue
        b = _box(o)
        assert not (b[0] < rect[2] - 1e-9 and rect[0] < b[2] - 1e-9 and b[1] < rect[3] - 1e-9
                    and rect[1] < b[3] - 1e-9), (name, o["name"])
        if room[0] <= o["x"] <= room[2] and room[1] <= o["y"] <= room[3]:
            for r in runs:
                assert level_design._box_gap(_box(r), b) >= cw - 1e-9, (name, r["name"], o["name"])
    da = agent_contract.door_approach()
    for e in vault_room.wall_openings(spec, kinds=("door", "garage", "breach", "vault")):
        if e["story"] != story:
            continue
        hw, d = tq._opening_width(e["op"]) / 2.0, 0.15 + da
        ap = ((e["along"] - hw, e["line"] - d, e["along"] + hw, e["line"] + d) if e["axis"] == "X"
              else (e["line"] - d, e["along"] - hw, e["line"] + d, e["along"] + hw))
        c = (max(ap[0], room[0]), max(ap[1], room[1]), min(ap[2], room[2]), min(ap[3], room[3]))
        if c[2] - c[0] <= 1e-6 or c[3] - c[1] <= 1e-6:
            continue
        for r in runs:
            assert level_design._box_gap(_box(r), c) >= cw - 1e-9, (name, r["name"], e["op"])
    hx, hy = spec["footprint_x"] / 2.0, spec["footprint_y"] / 2.0
    for r in runs:
        b = _box(r)
        assert min(b[0] + hx, hx - b[2], b[1] + hy, hy - b[3]) - 0.15 >= cw - 1e-9, (name, r["name"])


def test_a_counter_against_a_wall_is_left_with_its_reason():
    """bank_branch_a04's counter stands against the lobby's concrete wall, its public face 0.1 m into partition 0:
    no queue stands in front of it, and the rule says why rather than laying one in a wall."""
    spec = _spec("bank_branch_a04")
    assert not _runs(spec) and not [r for r in spec["volumes"] if r["name"].startswith("stanchion_run_t")]
    ((v, story, axis),) = level_design._teller_lines(spec)
    got = tq.plan_teller(spec, v, story, axis)
    assert not got["ok"] and got["why"] == "partition 0 inside the queue", got


def test_a_bank_made_by_the_preset_gets_its_queue():
    """`presets.make` enriches, and `enrich` lays a teller line's queue after its enclosure and before its cover and
    furniture: the preset's bank carries one, and nothing it furnished stands inside it."""
    import presets
    d = presets.make("bank")
    runs = [r for r in d["volumes"] if r["name"].startswith("stanchion_run_t0_")]
    assert len(runs) in (3, 4), [r["name"] for r in runs]
    ((v, story, axis),) = level_design._teller_lines(d)
    public = level_design._public_side(d, story, tq._host_room(d, story, v["x"], v["y"]), axis, v["y"])
    face = v["y"] + public * v["size_y"] / 2.0
    ys = [_box(r)[1] for r in runs] + [_box(r)[3] for r in runs]
    rect = (min(_box(r)[0] for r in runs), min(ys + [face]), max(_box(r)[2] for r in runs), max(ys + [face]))
    for o in _standing(d, story):
        if o in runs or o is v:
            continue
        b = _box(o)
        assert not (b[0] < rect[2] - 1e-9 and rect[0] < b[2] - 1e-9 and b[1] < rect[3] - 1e-9
                    and rect[1] < b[3] - 1e-9), o["name"]
    # and once is enough
    before = json.dumps(d, sort_keys=True)
    assert tq.lay_queues(d) == [] and json.dumps(d, sort_keys=True) == before


# ---------------------------------------------------------------- a queue is not furniture (0.244.0)

def test_furnish_does_not_count_a_queue_as_furniture():
    """`level_design._room_volume_count` leaves stanchion runs out: counted, a bank lobby's four runs cost it four
    pieces, and the ones it lost were bank_job's payphone and bank_branch_a03's and credit_union_a01's ATMs."""
    spec = _spec("bank_job")
    lobby = [r for r in spec["rooms"] if r["id"] == "lobby"][0]
    without = dict(spec, volumes=[v for v in spec["volumes"] if not v["name"].startswith("stanchion_run_")])
    assert len([v for v in spec["volumes"] if v["name"].startswith("stanchion_run_t")]) == 4
    assert level_design._room_volume_count(spec, lobby) == level_design._room_volume_count(without, lobby)


@pytest.mark.parametrize("name, kinds", [("bank_job", ("payphone", "atm", "sofa")),
                                         ("bank_branch_a03", ("atm",)), ("credit_union_a01", ("atm",))])
def test_a_queued_lobby_keeps_what_a_lobby_is_known_by(name, kinds):
    spec = _spec(name)
    stems = [v["name"].split("_r")[0] for v in spec["volumes"]]
    assert all(k in stems for k in kinds), (name, kinds, sorted(set(stems)))


def test_a_room_with_a_queue_has_no_lone_queue_posts():
    """A lobby's cluster of lone `stanchion` posts stood for a queue; where `ticket_queue` lays one, furnish places
    none -- in every library spec, and in a theatre made for it."""
    import glob
    import re
    rooms_with_queues = 0
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
        for room in spec.get("rooms") or []:
            if not room.get("bounds") or not level_design._holds_queue(spec, room):
                continue
            rooms_with_queues += 1
            tag = level_design._room_tag(room)
            posts = [v["name"] for v in spec["volumes"] if re.match(r"^stanchion_%s_\d+$" % tag, v["name"])]
            assert posts == [], (os.path.basename(path), room["id"], posts)
    assert rooms_with_queues == 5, rooms_with_queues
