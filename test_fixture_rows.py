"""Ceiling rows laid to the work, on the ceiling's grid (0.206.0, roadmap 229) -- pure, no bpy.

The walker, 2026-10-10: fixtures should "not always be in a perfect line". Every room had one
row at its centre along its longer axis; now a room takes as many rows across its width as its
work plane asks (WOOD's rule: rows at most 1.5 x the work-surface-to-lamp height apart), each on
the ceiling's 0.6 m tile or 0.4 m joist pitch, and a home's room one fixture at its centre.

Run:  python -m pytest test_fixture_rows.py
"""
import lights

CAP, SH, WALL = 0.3, 3.5, 0.3      # ceiling plane 3.2, the lamps 0.1 below it at 3.1


def _derive(rooms, residence=False, **kw):
    return lights.derive_light_anchors(rooms, [], SH, cap_thick=CAP, wall_thick=WALL,
                                       residence=residence, **kw)


def _rows(anchors, room):
    return [a for a in anchors if a["type"] == "fluorescent" and a["room"] == room]


def _on_pitch(value, pitch):
    return abs(value / pitch - round(value / pitch)) < 1e-6


def test_a_narrow_stockroom_keeps_one_row_and_its_original_id():
    # the floor is its work plane: A = 3.1, rows at most 4.65 m apart, so 4 m wide is one row
    r = {"id": "stockroom", "story": 0, "bounds": [0.0, 0.0, 12.0, 4.0], "role": "service",
         "center": [6.0, 2.0, 0.0]}
    rows = _rows(_derive([r]), "stockroom")
    assert [a["id"] for a in rows] == ["stockroom_ceiling"]
    assert rows[0]["pos"] == [6.0, 2.0, 3.1]          # 2.0 is on the 0.4 m joist pitch
    assert rows[0]["rot_y"] == 0.0
    assert rows[0]["row"] == {"count": 3, "spacing": 4.0}   # round(12 / 4.65) = 3


def test_a_wide_sales_floor_takes_rows_across_its_width_on_the_tile_grid():
    # a counter's plane, 1.0: A = 2.1, B = 3.15, so 8 m wide is ceil(8 / 3.15) = 3 rows
    r = {"id": "sales_floor", "story": 0, "bounds": [0.0, 0.0, 12.0, 8.0], "role": "public_entry",
         "center": [6.0, 4.0, 0.0]}
    rep = {}
    rows = _rows(_derive([r], report=rep), "sales_floor")
    assert [a["id"] for a in rows] == ["sales_floor_ceiling", "sales_floor_ceiling_r1",
                                       "sales_floor_ceiling_r2"]
    lines = [a["pos"][1] for a in rows]
    assert lines == [1.2, 4.2, 6.6]                    # 1.333, 4.0, 6.667 snapped to 0.6 m tiles
    assert all(_on_pitch(y, 0.6) for y in lines)
    assert all(a["pos"][0] == 6.0 and a["rot_y"] == 0.0 for a in rows)
    assert all(a["row"] == {"count": 4, "spacing": 3.0} for a in rows)   # round(12 / 3.15) = 4
    assert rep["rows_laid"] == 3


def test_an_office_lights_its_desks_in_two_rows():
    # a desk's plane, 0.75: A = 2.35, B = 3.525, so 6 m wide is two rows; 10 m long is 3 lamps a row
    r = {"id": "manager_office", "story": 0, "bounds": [-5.0, -3.0, 5.0, 3.0], "role": "objective_room",
         "center": [0.0, 0.0, 0.0]}
    rows = _rows(_derive([r]), "manager_office")
    assert [a["id"] for a in rows] == ["manager_office_ceiling", "manager_office_ceiling_r1"]
    # -1.5 and 1.5 snapped to the tiles: half a tile exactly, rounded to the even tile each
    assert [a["pos"][1] for a in rows] == [-1.2, 1.2]
    assert all(a["row"]["count"] == 3 for a in rows)
    # a 4 m office keeps one row: 4 / 3.525 = 1.13 spacings, within the slack
    narrow = dict(r, bounds=[-5.0, -2.0, 5.0, 2.0])
    assert [a["id"] for a in _rows(_derive([narrow]), "manager_office")] == ["manager_office_ceiling"]


def test_the_room_cap_thins_every_row_alike():
    # a 30 x 20 m hall on the floor plane: 5 rows asked, 3 allowed; 6 lamps asked, 5 a row allowed,
    # 15 over the room's 12, so 4 a row
    r = {"id": "concourse", "story": 0, "bounds": [0.0, 0.0, 30.0, 20.0], "role": "public_entry",
         "center": [15.0, 10.0, 0.0]}
    rows = _rows(_derive([r]), "concourse")
    assert len(rows) == lights._MAX_ROWS == 3
    assert sum(a["row"]["count"] for a in rows) == lights._MAX_LAMPS_ROOM == 12
    assert {a["row"]["count"] for a in rows} == {4}


def test_a_room_exactly_one_spacing_wide_is_one_row():
    # 5 m wide on the floor plane is 5 / 4.65 = 1.08 rows; a shade over is still forgiven
    r = {"id": "hall", "story": 0, "bounds": [0.0, 0.0, 10.0, 4.7], "role": "connector",
         "center": [5.0, 2.35, 0.0]}
    assert len(_rows(_derive([r]), "hall")) == 1


def test_the_line_moves_to_the_joists_by_half_a_pitch_at_most():
    r = {"id": "back_hall", "story": 0, "bounds": [0.0, 0.1, 10.0, 4.3], "role": "connector",
         "center": [5.0, 2.2, 0.0]}
    row = _rows(_derive([r]), "back_hall")[0]
    assert row["pos"][1] == 2.0                        # 2.2 to the nearest 0.4 m joist
    assert abs(row["pos"][1] - 2.2) <= 0.2 + 1e-9


def test_a_home_room_is_one_fixture_at_its_centre():
    r = {"id": "living_room", "story": 0, "bounds": [0.0, 0.0, 9.0, 7.0], "role": "connector",
         "center": [4.5, 3.5, 0.0]}
    rows = _rows(_derive([r], residence=True), "living_room")
    assert len(rows) == 1
    assert rows[0]["row"] == {"count": 1, "spacing": 0.0}
    assert rows[0]["pos"][:2] == [4.5, 3.5]           # the centre, not the grid
    # the same room in a store is two rows: 7 / 4.65 = 1.5 spacings, past the slack
    assert len(_rows(_derive([r]), "living_room")) == 2


def test_below_grade_bulbs_are_as_they_were():
    r = {"id": "vault", "story": -1, "bounds": [0.0, 0.0, 10.0, 10.0], "role": "objective_room",
         "center": [5.0, 5.0, -3.5]}
    bulbs = [a for a in _derive([r]) if a["type"] == "pendant"]
    assert len(bulbs) == 1
    assert bulbs[0]["id"] == "vault_bulbs"
    assert bulbs[0]["pos"][:2] == [5.0, 5.0]
    assert bulbs[0]["row"] == {"count": 2, "spacing": 5.0}   # 100 m2 / 25, held to 10 / 3.5


def test_a_second_row_split_by_a_void_names_its_runs():
    # a 12 x 8 sales floor, three rows; a stairwell hole across the middle row's middle
    r = {"id": "sales_floor", "story": 0, "bounds": [0.0, 0.0, 12.0, 8.0], "role": "public_entry",
         "center": [6.0, 4.0, 0.0]}
    void = [{"story": 0, "x0": 5.0, "y0": 3.5, "x1": 7.0, "y1": 5.0}]
    ids = [a["id"] for a in _rows(_derive([r], ceiling_voids=void), "sales_floor")]
    # row 1 at y 4.2 has lamps at x 1.5, 4.5, 7.5, 10.5: none inside x 5..7, so it is not split
    assert ids == ["sales_floor_ceiling", "sales_floor_ceiling_r1", "sales_floor_ceiling_r2"]
    void = [{"story": 0, "x0": 4.0, "y0": 3.5, "x1": 5.0, "y1": 5.0}]
    ids = [a["id"] for a in _rows(_derive([r], ceiling_voids=void), "sales_floor")]
    assert ids == ["sales_floor_ceiling", "sales_floor_ceiling_r1_0", "sales_floor_ceiling_r1_1",
                   "sales_floor_ceiling_r2"]


def test_a_colinear_partition_moves_the_row_it_lies_under_only():
    # a 12 x 8 sales floor; a partition along y = 4.2, under the middle row, for the room's length
    r = {"id": "sales_floor", "story": 0, "bounds": [0.0, 0.0, 12.0, 8.0], "role": "public_entry",
         "center": [6.0, 4.0, 0.0]}
    walls = lights.partition_rects([{"story": 0, "axis": "X", "pos": 4.2, "start": 0.0, "end": 12.0}], WALL)
    rep = {}
    rows = _rows(_derive([r], partitions=walls, report=rep), "sales_floor")
    assert rep["rows_shifted"] == 1
    assert [a["pos"][1] for a in rows][0] == 1.2 and [a["pos"][1] for a in rows][2] == 6.6
    assert rows[1]["pos"][1] != 4.2                    # moved to the larger side's centre
