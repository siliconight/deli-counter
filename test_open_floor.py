"""An open floor nobody named (layout_lint L26, 0.223.0; the factory's roadmap 255).

Two rooms on one storey whose shared edge no partition covers for `tactical.OPEN_FLOOR_M` are one floor to the
engine (`tactical.shared_open_edge`, 0.197.0), and until now the spec could not say whether that was meant: the
walker's walk of 2026-10-14 found the delis' basement divider stopping 7 m short of each wall, the vault open to the
utility room, and the library held 33 such stretches in 20 specs. L26 names each pair unless a room's `open_to`
names the other; `open_floor_baseline.json` freezes today's for the walker to sort.

FAIL ON 0.222.0: there is no `open_floors`, no `open_edge`, no `OPEN_FLOOR_M`, no `open_to` in the schema.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import layout_lint                   # noqa: E402
import tactical                      # noqa: E402

BASELINE = os.path.join(HERE, "open_floor_baseline.json")
FRONT, BACK = [-5.0, -5.0, 0.0, 5.0], [0.0, -5.0, 5.0, 5.0]


def _spec(partition_end=5.0, open_to=None):
    """Two 5 x 10 m rooms side by side on story 0, a door in from the west, the partition between them along
    x = 0 from y -5 to `partition_end`; `open_to` on the front room when given."""
    rooms = [{"id": "front", "story": 0, "bounds": list(FRONT)}, {"id": "back", "story": 0, "bounds": list(BACK)}]
    if open_to:
        rooms[0]["open_to"] = [open_to]
    return {"name": "t", "footprint_x": 10.0, "footprint_y": 10.0, "rooms": rooms,
            "partitions": [{"story": 0, "axis": "Y", "pos": 0.0, "start": -5.0, "end": partition_end,
                            "openings": []}],
            "ext_walls": [{"wall": "W", "story": 0, "openings": [{"kind": "door", "pos": 0.0, "width": 1.2}]}]}


def _parts(s):
    return layout_lint._story_parts(s, 0)


def test_a_partition_that_stops_short_is_named_with_where():
    s = _spec(3.0)                                            # 2 m of the 10 m edge uncovered
    assert layout_lint.open_floors(s) == [{"story": 0, "a": "front", "b": "back", "axis": "Y", "pos": 0.0,
                                           "lo": -5.0, "hi": 5.0, "uncovered": 2.0}]
    assert tactical.open_edge(FRONT, BACK, _parts(s)) == ("Y", 0.0, -5.0, 5.0, 2.0)
    found = layout_lint.open_floor_findings(s)
    assert len(found) == 1 and found[0].startswith("L26 "), found
    for words in ("'front' and 'back'", "story 0", "x = 0", "2.00 m", "open_to"):
        assert words in found[0], words


def test_a_wall_to_wall_partition_and_a_short_gap_are_not_open_floor():
    assert layout_lint.open_floors(_spec(5.0)) == []
    assert layout_lint.open_floors(_spec(4.0)) == []           # 1.0 m uncovered, under the rule's 1.2
    assert tactical.open_edge(FRONT, BACK, _parts(_spec(4.0))) is None
    assert not tactical.shared_open_edge(FRONT, BACK, _parts(_spec(4.0)))


def test_open_to_names_the_floor_for_the_lint_and_not_for_the_engine():
    s = _spec(3.0, open_to="back")
    assert layout_lint.open_floors(s) == [] and layout_lint.open_floor_findings(s) == []
    assert tactical.shared_open_edge(FRONT, BACK, _parts(s))     # the engine still walks it
    # named from the other side too
    t = _spec(3.0)
    t["rooms"][1]["open_to"] = ["front"]
    assert layout_lint.open_floors(t) == []


def test_one_threshold_for_tactical_and_the_lint(monkeypatch):
    s = _spec(3.0)
    assert tactical.OPEN_FLOOR_M == 1.2
    monkeypatch.setattr(tactical, "OPEN_FLOOR_M", 2.5)
    assert layout_lint.open_floors(s) == []
    assert not tactical.shared_open_edge(FRONT, BACK, _parts(s))
    monkeypatch.setattr(tactical, "OPEN_FLOOR_M", 1.2)
    assert len(layout_lint.open_floors(s)) == 1 and tactical.shared_open_edge(FRONT, BACK, _parts(s))


def test_lint_reports_it_as_a_warning_not_a_failure():
    spec = json.load(open(os.path.join(HERE, "specs", "rowhouse_raid.json"), encoding="utf-8"))
    _name, fails, warns = layout_lint.lint_spec(spec, "rowhouse_raid")
    assert any(w.startswith("L26 ") and "'garage_bay'" in w for w in warns), warns
    assert not any(f.startswith("L26 ") for f in fails)


def test_the_schema_admits_open_to():
    schema = json.load(open(os.path.join(HERE, "schema", "level.schema.json"), encoding="utf-8"))
    room = schema["properties"]["rooms"]["items"]
    assert room["properties"]["open_to"] == {"type": "array", "items": {"type": "string"}}
    assert room["additionalProperties"] is False


def test_the_search_leaves_the_spec_alone():
    s = _spec(3.0)
    before = json.dumps(s, sort_keys=True)
    layout_lint.open_floors(s)
    assert json.dumps(s, sort_keys=True) == before


def _library():
    out = {}
    for m in sorted(glob.glob(os.path.join(HERE, "build", "*.manifest.json"))):
        name = os.path.basename(m)[:-len(".manifest.json")]
        p = os.path.join(HERE, "specs", name + ".json")
        if name.startswith("lf_") or not os.path.exists(p):
            continue
        got = layout_lint.open_floors(json.load(open(p, encoding="utf-8")))
        if got:
            out[name] = sorted("%s|%s" % (f["a"], f["b"]) for f in got)
    return out


def _frozen():
    d = json.load(open(BASELINE, encoding="utf-8"))
    return {k: sorted(v) for k, v in d["open_floors"].items()}


def test_no_new_open_floor_nobody_named():
    frozen = _frozen()
    new = {k: [n for n in v if n not in frozen.get(k, [])] for k, v in _library().items()}
    assert not {k: v for k, v in new.items() if v}, new


def test_open_floor_baseline_has_not_gone_stale():
    lib = _library()
    gone = {k: [n for n in v if n not in lib.get(k, [])] for k, v in _frozen().items()}
    assert not {k: v for k, v in gone.items() if v}, gone
