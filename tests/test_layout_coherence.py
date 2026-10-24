"""Pure tests for layout_lint structural coherence (L10 dead opening / L11
orphan wall). Run: python3 test_layout_coherence.py"""
import layout_lint as LL

CLEAN = {  # two rooms sharing a wall, door on the real boundary
    "name": "clean", "footprint_x": 10, "footprint_y": 8, "n_stories": 1,
    "rooms": [{"id": "a", "story": 0, "bounds": [-5, -4, 0, 4]},
              {"id": "b", "story": 0, "bounds": [0, -4, 5, 4]}],
    "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -4, "end": 4,
                    "openings": [{"kind": "door", "pos": 0.0, "width": 1.0}]}]}

BROKEN = {  # one room; a door on a wall inside it -> dead opening + orphan wall
    "name": "broken", "footprint_x": 10, "footprint_y": 8, "n_stories": 1,
    "rooms": [{"id": "a", "story": 0, "bounds": [-5, -4, 5, 4]}],
    "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -4, "end": 4,
                    "openings": [{"kind": "door", "pos": 0.0, "width": 1.0}]}]}


def test_clean_has_no_structural_fail():
    f, w = LL.structural_findings(CLEAN)
    assert not any(x.startswith("L10") for x in f), f
    assert not any(x.startswith("L11") for x in f), f


def test_dead_door_fails():
    f, w = LL.structural_findings(BROKEN)
    assert any(x.startswith("L10 dead opening") for x in f), f


def test_orphan_wall_fails():
    f, w = LL.structural_findings(BROKEN)  # extreme mode: orphan walls are hard FAILs
    assert any(x.startswith("L11 orphan wall") for x in f), f


def test_gate_blocks_broken():
    errs, warns, summ = LL.gate(BROKEN)
    assert errs and summ["fails"] >= 1


REACH = {  # ext door into a; a<->b via interior door -> both reachable
    "name": "reach", "footprint_x": 10, "footprint_y": 8, "n_stories": 1,
    "ext_walls": [{"wall": "S", "story": 0,
                   "openings": [{"kind": "door", "pos": -0.25, "width": 1.0}]}],
    "rooms": [{"id": "a", "story": 0, "bounds": [-5, -4, 0, 4]},
              {"id": "b", "story": 0, "bounds": [0, -4, 5, 4]}],
    "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -4, "end": 4,
                    "openings": [{"kind": "door", "pos": 0.0, "width": 1.0}]}]}

SEALED = {  # same, but the partition has NO opening -> b is a sealed room
    "name": "sealed", "footprint_x": 10, "footprint_y": 8, "n_stories": 1,
    "ext_walls": [{"wall": "S", "story": 0,
                   "openings": [{"kind": "door", "pos": -0.25, "width": 1.0}]}],
    "rooms": [{"id": "a", "story": 0, "bounds": [-5, -4, 0, 4]},
              {"id": "b", "story": 0, "bounds": [0, -4, 5, 4]}],
    "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -4, "end": 4,
                    "openings": []}]}


def test_reachable_ok():
    assert not LL.reachability_findings(REACH)


def test_sealed_room_fails():
    f = LL.reachability_findings(SEALED)
    assert any("'b'" in x for x in f), f


if __name__ == "__main__":
    for n, fn in sorted(globals().items()):
        if n.startswith("test_"):
            fn(); print("[ok]", n)
    print("all layout coherence tests passed")
