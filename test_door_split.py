"""Roadmap 59: one door, two corridors -- L18, the door-split lint.

A partition whose end lands inside a doorway's aperture divides one opening
into two squeeze-past channels with a wall edge-on to the door. Both
channels TRAVERSE, so every engine gate passes; the defect is a question no
building should ask ("which half of the door do I take"), which makes it a
spec-level lint. These tests pin the geometry: what counts as MEETING the
host, what counts as INSIDE the aperture, and -- just as deliberately --
what stays exempt (crossings, near-misses, other storeys, windows).
"""
import layout_lint


def _spec(**kw):
    d = {"name": "t", "footprint_x": 20.0, "footprint_y": 12.0,
         "wall_thick": 0.35, "rooms": [], "partitions": [], "ext_walls": []}
    d.update(kw)
    return d


def _door_on_north(pos=0.1, width=1.2, tag="entry_main"):
    return {"wall": "N", "story": 0,
            "openings": [{"kind": "door", "pos": pos, "width": width,
                          "tag": tag}]}


def test_a_partition_ending_in_an_exterior_doorway_warns():
    # door center x = 0.1 * 20 = 2.0, half-aperture 0.6 + 0.3 margin = 0.9;
    # the Y-partition ends ON the north wall (end = footprint_y/2) at x 2.3.
    s = _spec(ext_walls=[_door_on_north()],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.3,
                           "start": 0.0, "end": 6.0}])
    w = layout_lint.door_split_findings(s)
    assert len(w) == 1 and "L18" in w[0] and "entry_main" in w[0]


def test_a_partition_ending_one_bay_short_is_clean():
    # Same wall, same x -- but the partition stops 1.5 m shy of the wall,
    # which is the generator's own avoidance move. No meet, no finding.
    s = _spec(ext_walls=[_door_on_north()],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.3,
                           "start": 0.0, "end": 4.5}])
    assert layout_lint.door_split_findings(s) == []


def test_a_partition_meeting_the_wall_clear_of_the_door_is_clean():
    s = _spec(ext_walls=[_door_on_north()],
              partitions=[{"axis": "Y", "story": 0, "pos": 4.0,
                           "start": 0.0, "end": 6.0}])
    assert layout_lint.door_split_findings(s) == []


def test_a_partition_ending_in_an_interior_doorway_warns():
    # Host runs along X at y=0 spanning the footprint; its door sits at
    # x = 0 + 0.25 * 16 = 4.0. The Y-partition ends on the host's line at
    # x 4.3 -- inside 0.6 + 0.3.
    host = {"axis": "X", "story": 0, "pos": 0.0, "start": -8.0, "end": 8.0,
            "openings": [{"kind": "door", "pos": 0.25, "width": 1.2,
                          "tag": "ward_door"}]}
    term = {"axis": "Y", "story": 0, "pos": 4.3, "start": 0.0, "end": 5.0}
    s = _spec(partitions=[host, term])
    w = layout_lint.door_split_findings(s)
    assert len(w) == 1 and "ward_door" in w[0]


def test_a_partition_crossing_the_host_is_exempt():
    """Termination is the defect; a wall PASSING THROUGH the aperture line
    is a different animal with different owners. Endpoints at +/-5 never
    land on the host's line, so no meet."""
    host = {"axis": "X", "story": 0, "pos": 0.0, "start": -8.0, "end": 8.0,
            "openings": [{"kind": "door", "pos": 0.25, "width": 1.2}]}
    term = {"axis": "Y", "story": 0, "pos": 4.3, "start": -5.0, "end": 5.0}
    s = _spec(partitions=[host, term])
    assert layout_lint.door_split_findings(s) == []


def test_the_leaf_margin_is_part_of_the_aperture():
    # Aperture half-width 0.6; at 0.85 from center the wall end is past the
    # panel but inside the 0.3 leaf margin -- still a split door in play.
    s = _spec(ext_walls=[_door_on_north()],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.85,
                           "start": 0.0, "end": 6.0}])
    assert len(layout_lint.door_split_findings(s)) == 1
    s2 = _spec(ext_walls=[_door_on_north()],
               partitions=[{"axis": "Y", "story": 0, "pos": 2.95,
                            "start": 0.0, "end": 6.0}])
    assert layout_lint.door_split_findings(s2) == []


def test_an_unstated_width_defaults_like_the_drawing_does():
    # No width on the opening -> 1.0 (the floorplan's default): half 0.5
    # + margin 0.3 = 0.8. 0.75 away warns; 0.85 away is clean.
    wall = {"wall": "N", "story": 0,
            "openings": [{"kind": "door", "pos": 0.1}]}
    s = _spec(ext_walls=[wall],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.75,
                           "start": 0.0, "end": 6.0}])
    assert len(layout_lint.door_split_findings(s)) == 1
    s2 = _spec(ext_walls=[wall],
               partitions=[{"axis": "Y", "story": 0, "pos": 2.85,
                            "start": 0.0, "end": 6.0}])
    assert layout_lint.door_split_findings(s2) == []


def test_windows_do_not_own_an_aperture():
    wall = {"wall": "N", "story": 0,
            "openings": [{"kind": "window", "pos": 0.1, "width": 1.2}]}
    s = _spec(ext_walls=[wall],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.0,
                           "start": 0.0, "end": 6.0}])
    assert layout_lint.door_split_findings(s) == []


def test_another_storeys_door_is_not_this_storeys_problem():
    s = _spec(ext_walls=[{"wall": "N", "story": 1,
                          "openings": [{"kind": "door", "pos": 0.1,
                                        "width": 1.2}]}],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.0,
                           "start": 0.0, "end": 6.0}])
    assert layout_lint.door_split_findings(s) == []


def test_meeting_the_hosts_line_beyond_its_built_span_is_clean():
    # The host only spans x [-8, -2]; the terminator ends on the host's
    # LINE at x 4.3, far past where any wall stands -- no wall, no split.
    host = {"axis": "X", "story": 0, "pos": 0.0, "start": -8.0, "end": -2.0,
            "openings": [{"kind": "door", "pos": 0.25, "width": 1.2}]}
    term = {"axis": "Y", "story": 0, "pos": 4.3, "start": 0.0, "end": 5.0}
    s = _spec(partitions=[host, term])
    assert layout_lint.door_split_findings(s) == []


def test_the_lint_is_wired_into_lint_spec():
    s = _spec(ext_walls=[_door_on_north()],
              partitions=[{"axis": "Y", "story": 0, "pos": 2.3,
                           "start": 0.0, "end": 6.0}])
    _, fails, warns = layout_lint.lint_spec(s, "t")
    assert any("L18" in w for w in warns)
    assert not any("L18" in f for f in fails)   # WARN first, by decision
