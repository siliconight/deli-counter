"""A slot owns its own greybox nodes, never a sibling slot's (0.203.0,
roadmap 205).

THE DEFECT. The placement gate (`portable_building._slot_greybox_extent`) and
the composer's fit (`themed_tscn._slot_extent`) counted a greybox node as part
of a slot when its name was the slot id or began `<slot_id>_` -- the rule for
an opening's own parts (`_lintel`, `_sill`, `_pane`). A SIBLING slot whose id
begins the same way was swallowed with them. gas_station_a02's `cooler_run`
(3.28 m, x 12.62..15.90) took in `cooler_run_sales` (8.0 m, x -9.54..-1.54)
and measured 25.442 m, so the gate refused the module built exactly to its
slot: `PRESENTATION_PLACEMENT_MISMATCH`, cold run 9195's art leg stopped. The
composer orients every module by the same extent.

Measured over the library on 2026-10-07: 9 of 145 buildings carry a slot id
that begins another's (19 pairs), and in 5 the sibling has greybox nodes --
the three pawn shops' `counter` (9.86 x 6.36 m read, 4.0 x 0.7 its own) and
the two gas stations' `cooler_run`.

THE RULE. A node belongs to the LONGEST slot id that names it.

Run:  python -m pytest test_slot_extent_owner.py
"""
import json
import os

import pytest

import portable_building as pb
import themed_tscn

HERE = os.path.dirname(os.path.abspath(__file__))


def _box(x0, x1, z0=-0.83, z1=0.07, h=2.2):
    return ([x0, 0.0, z0], [x1, h, z1])


#: gas_station_a02's two cooler runs, as its greybox carries them.
COOLERS = {"cooler_run": _box(12.62, 15.90),
           "cooler_run_sales": _box(-9.542, -1.542)}
COOLER_IDS = {"cooler_run", "cooler_run_sales"}


def test_a_sibling_slot_is_not_a_part_of_the_gate_extent():
    ext = pb._slot_greybox_extent(COOLERS, "cooler_run", COOLER_IDS)
    assert ext is not None and abs(ext[0] - 3.28) < 1e-6, ext
    ext = pb._slot_greybox_extent(COOLERS, "cooler_run_sales", COOLER_IDS)
    assert ext is not None and abs(ext[0] - 8.0) < 1e-6, ext


def test_the_composer_reads_the_extent_the_gate_reads():
    for sid in COOLER_IDS:
        gate = pb._slot_greybox_extent(COOLERS, sid, COOLER_IDS)
        comp = themed_tscn._slot_extent(COOLERS, sid, COOLER_IDS)
        assert [round(v, 3) for v in comp] == gate, (sid, comp, gate)


def test_an_openings_own_parts_still_measure_as_one():
    """The rule the prefix test was written for, and the numeric sibling it
    was written against (`seg1` must not swallow `seg10`)."""
    gb = {"door_1_lintel": _box(-0.6, 0.6, h=2.4), "door_1_sill": _box(-0.6, 0.6, h=0.1),
          "door_10": _box(5.0, 6.0)}
    ids = {"door_1", "door_10"}
    ext = pb._slot_greybox_extent(gb, "door_1", ids)
    assert ext is not None and abs(ext[0] - 1.2) < 1e-6 and abs(ext[1] - 2.4) < 1e-6, ext
    assert abs(pb._slot_greybox_extent(gb, "door_10", ids)[0] - 1.0) < 1e-6


def test_a_siblings_own_part_goes_to_the_sibling():
    gb = {"counter": _box(0.0, 4.0), "counter_service_1": _box(6.0, 9.0),
          "counter_service_1_lip": _box(6.0, 9.86)}
    ids = {"counter", "counter_service_1"}
    assert abs(pb._slot_greybox_extent(gb, "counter", ids)[0] - 4.0) < 1e-6
    assert abs(pb._slot_greybox_extent(gb, "counter_service_1", ids)[0] - 3.86) < 1e-6


def test_a_node_no_slot_names_is_nobodys():
    assert pb._slot_greybox_extent({"wall_A": _box(0, 1)}, "cooler_run", COOLER_IDS) is None


@pytest.mark.parametrize("building, slot, own_width", [
    ("gas_station_a02", "cooler_run", 3.28),
    ("gas_station_a02", "cooler_run_sales", 8.0),
])
def test_the_real_gas_station_measures_each_cooler_run_alone(building, slot, own_width):
    glb = os.path.join(HERE, "build", building + ".glb")
    slots = os.path.join(HERE, "build", building + ".slots.json")
    if not (os.path.exists(glb) and os.path.exists(slots)):
        pytest.skip("build/%s not present" % building)
    with open(slots, encoding="utf-8") as f:
        ids = {s["slot_id"] for s in json.load(f)["slots"] if s.get("slot_id")}
    ext = pb._slot_greybox_extent(pb._glb_visual_bboxes(glb), slot, ids)
    assert ext is not None and abs(ext[0] - own_width) < 0.01, ext
