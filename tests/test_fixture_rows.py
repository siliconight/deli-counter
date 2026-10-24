"""Ceiling rows laid to the work, on the ceiling's grid (0.206.0, roadmap 229) -- pure, no bpy.

The walker, 2026-10-10: fixtures should "not always be in a perfect line". Every room had one
row at its centre along its longer axis; now a room takes as many rows across its width as its
work plane asks (WOOD's rule: rows at most 1.5 x the work-surface-to-lamp height apart), each on
the ceiling's 0.6 m tile or 0.4 m joist pitch, and a home's room one fixture at its centre.

Run:  python -m pytest tests/test_fixture_rows.py
"""
import lights

CAP, SH, WALL = 0.3, 3.5, 0.3      # ceiling plane 3.2, the lamps 0.1 below it at 3.1


def _derive(rooms, residence=False, **kw):
    return lights.derive_light_anchors(rooms, [], SH, cap_thick=CAP, wall_thick=WALL,
                                       residence=residence, **kw)


def _rows(anchors, room):
    # a home's room lays the same rows as domes (0.208.0)
    return [a for a in anchors if a["type"] in ("fluorescent", "dome") and a["room"] == room]


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
    # the same bounds under a name with no home in it, in a store, is two rows: 7 / 4.65 =
    # 1.5 spacings, past the slack (0.206.1: a living room is a home's in any building)
    assert len(_rows(_derive([dict(r, id="back_floor")]), "back_floor")) == 2


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


def test_a_home_room_in_a_shop_takes_the_home_rule():
    # cold run 9229: the deli's apartment hideout, 21 x 16 m, took three rows of four
    r = {"id": "apartment_hideout", "story": 1, "bounds": [-2.0, -14.0, 19.0, 2.0],
         "role": "fortifiable", "center": [8.5, -6.0, 3.3]}
    rows = _rows(_derive([r]), "apartment_hideout")
    # the home rule, not the office ceiling: a fixture a bay (0.207.1), two rows of three at
    # the bays' centres rather than three rows of four on the tile grid
    assert len(rows) == 2 and all(a["row"] == {"count": 3, "spacing": 7.0} for a in rows)
    assert [a["pos"][1] for a in rows] == [-10.0, -2.0]
    # the same bounds under a name that says nothing of a home is still an office ceiling
    office = dict(r, id="upper_office")
    assert len(_rows(_derive([office]), "upper_office")) == 3


# --- rows over the aisles (0.207.0) -------------------------------------------------------------

def _gondola(name, x, y, sx=1.0, sy=6.0, h=1.6, z=None):
    return {"name": name, "x": x, "y": y, "z": h / 2.0 if z is None else z,
            "size_x": sx, "size_y": sy, "size_z": h}


def test_a_sales_floor_lays_its_rows_over_the_aisles_between_the_gondolas():
    # 15 x 20 m, long in y, two gondolas standing along y: three lanes across x of 5.5, 3.5 and
    # 4.0 m; on the counter's plane B = 3.15 the wide lane asks two rows and the others one, and
    # 20 m along asks 5 lamps a row: 20 for the room's twelve, so the cap binds and the long
    # hall's trade gives the wide lane one row (5.5 m across) for four lamps along (5.0 m) rather
    # than two for three (6.7 m); every line on the 0.6 m tiles and none over a gondola
    r = {"id": "market_aisles", "story": 0, "bounds": [-8.0, -14.0, 7.0, 6.0], "role": "sales",
         "center": [-0.5, -4.0, 0.0]}
    vols = [_gondola("gondola_aisle_1", -2.0, -9.5), _gondola("gondola_aisle_2", 2.5, -9.5)]
    rep = {}
    rows = _rows(_derive([r], volumes=vols, report=rep), "market_aisles")
    assert [a["id"] for a in rows] == ["market_aisles_ceiling", "market_aisles_ceiling_r1",
                                       "market_aisles_ceiling_r2"]
    lines = [a["pos"][0] for a in rows]
    assert lines == [-5.4, 0.0, 4.8]
    assert all(_on_pitch(x, 0.6) for x in lines)
    for x in lines:
        assert not (-2.5 <= x <= -1.5) and not (2.0 <= x <= 3.0)
    assert all(a["rot_y"] == 90.0 and a["pos"][1] == -4.0 for a in rows)
    assert all(a["row"] == {"count": 4, "spacing": 5.0} for a in rows)
    assert rep["rows_over_aisles"] == 1 and rep["rows_laid"] == 3


def test_a_shelf_in_an_office_does_not_move_its_grid():
    # an office is laid to its desks on the tile grid whatever stands against its wall
    r = {"id": "manager_office", "story": 0, "bounds": [-5.0, -3.0, 5.0, 3.0], "role": "objective_room",
         "center": [0.0, 0.0, 0.0]}
    unit = _gondola("shelf_unit_r1", 0.0, 2.7, sx=1.0, sy=0.5, h=1.4)
    bare = _rows(_derive([r]), "manager_office")
    rep = {}
    shelved = _rows(_derive([r], volumes=[unit], report=rep), "manager_office")
    assert [a["pos"] for a in shelved] == [a["pos"] for a in bare]
    assert rep["rows_over_aisles"] == 0


def test_a_stockroom_with_one_wall_run_lights_the_floor_beside_it():
    # 12 x 8 m on the floor plane (B = 4.65), a shelf run along the north wall: the lane is the
    # 7.4 m south of it and takes two rows on the joists, where the bare room's second row stood
    # at 6.0
    r = {"id": "stockroom", "story": 0, "bounds": [0.0, 0.0, 12.0, 8.0], "role": "service",
         "center": [6.0, 4.0, 0.0]}
    run = _gondola("shelf_run_r1", 6.0, 7.7, sx=6.0, sy=0.6, h=1.9)
    assert [a["pos"][1] for a in _rows(_derive([r]), "stockroom")] == [2.0, 6.0]
    assert [a["pos"][1] for a in _rows(_derive([r], volumes=[run]), "stockroom")] == [2.0, 5.6]


def test_a_sign_hung_over_an_aisle_is_not_a_shelf():
    r = {"id": "market_aisles", "story": 0, "bounds": [-8.0, -14.0, 7.0, 6.0], "role": "sales",
         "center": [-0.5, -4.0, 0.0]}
    sign = _gondola("gondola_aisle_sign", 0.25, -9.5, sx=0.8, sy=0.1, h=0.4, z=2.6)
    vols = [_gondola("gondola_aisle_1", -2.0, -9.5), _gondola("gondola_aisle_2", 2.5, -9.5), sign]
    assert [a["pos"][0] for a in _rows(_derive([r], volumes=vols), "market_aisles")] == [-5.4, 0.0, 4.8]


def test_shelves_that_leave_no_lane_lay_the_room_as_before():
    # a 4 m wide cold store filled by two racks 1.0 m apart: no aisle, so WOOD's one row stands
    r = {"id": "cold_room_stock", "story": 0, "bounds": [0.0, 0.0, 10.0, 4.0], "role": "service",
         "center": [5.0, 2.0, 0.0]}
    racks = [_gondola("stock_rack_a", 5.0, 0.75, sx=8.0, sy=1.5, h=2.0),
             _gondola("stock_rack_b", 5.0, 3.25, sx=8.0, sy=1.5, h=2.0)]
    rep = {}
    rows = _rows(_derive([r], volumes=racks, report=rep), "cold_room_stock")
    assert [a["pos"] for a in rows] == [[5.0, 2.0, 3.1]]
    assert rep["rows_over_aisles"] == 0


def test_a_field_of_staggered_islands_is_laid_as_before():
    # two gondolas standing at different places ALONG the room whose spans across it overlap
    # into a 2.2 m band (4.5 and 5.5, each 1.2 deep): not parallel runs but a field, and a row
    # kept off the band would leave the middle dark, so the room keeps 0.206.1's grid
    r = {"id": "sales_floor", "story": 0, "bounds": [0.0, 0.0, 20.0, 12.0], "role": "sales",
         "center": [10.0, 6.0, 0.0]}
    field = [_gondola("gondola_aisle_1", 5.0, 4.5, sx=4.0, sy=1.2), _gondola("gondola_aisle_2", 14.0, 5.5, sx=4.0, sy=1.2)]
    bare = _rows(_derive([r]), "sales_floor")
    rep = {}
    got = _rows(_derive([r], volumes=field, report=rep), "sales_floor")
    assert [a["pos"] for a in got] == [a["pos"] for a in bare] and len(got) == 3
    assert rep["rows_over_aisles"] == 0


def test_a_long_hall_favours_lamps_along_over_rows_across():
    # 58 x 20 m on the floor plane (B = 4.65): WOOD asks 3 rows of 12; the cap allowed 3 rows of
    # 4 at 14.5 m along, where 2 rows of 5 at 11.6 m along and 10 m across is the smaller worst
    r = {"id": "concourse_hall", "story": 0, "bounds": [0.0, 0.0, 58.0, 20.0], "role": "public_entry",
         "center": [29.0, 10.0, 0.0]}
    rows = _rows(_derive([r]), "concourse_hall")
    assert len(rows) == 2
    assert all(a["row"] == {"count": 5, "spacing": 11.6} for a in rows)
    assert [a["pos"][1] for a in rows] == [4.8, 15.2]          # 5.0 and 15.0 on the 0.4 m joists
    # a 24 x 20 m hall, where the cap also binds, keeps its three rows of four: its across spacing
    # (6.7 m) is the larger and two rows would only widen it
    hall = {"id": "concourse", "story": 0, "bounds": [0.0, 0.0, 24.0, 20.0], "role": "public_entry",
            "center": [12.0, 10.0, 0.0]}
    got = _rows(_derive([hall]), "concourse")
    assert len(got) == 3 and all(a["row"]["count"] == 4 for a in got)


def test_the_room_cap_holds_over_many_aisles():
    # five gondolas across a 24 x 18 m floor make six lanes; six rows share the room's twelve lamps
    r = {"id": "sales_floor", "story": 0, "bounds": [0.0, 0.0, 24.0, 18.0], "role": "sales",
         "center": [12.0, 9.0, 0.0]}
    vols = [_gondola("gondola_%d" % i, 12.0, 3.0 * (i + 1), sx=12.0, sy=1.0) for i in range(5)]
    rows = _rows(_derive([r], volumes=vols), "sales_floor")
    assert len(rows) == 6
    assert sum(a["row"]["count"] for a in rows) == lights._MAX_LAMPS_ROOM == 12


def test_a_big_home_room_takes_a_fixture_a_bay():
    # cold run 9232: the deli's 21 x 16 m hideout read dark at both ends under one troffer;
    # at a 7 m bay it is two rows of three at the bays' centres, 7 m apart along, no snap
    r = {"id": "apartment_hideout", "story": 1, "bounds": [-2.0, -14.0, 19.0, 2.0],
         "role": "fortifiable", "center": [8.5, -6.0, 3.3]}
    rows = _rows(_derive([r]), "apartment_hideout")
    assert [a["id"] for a in rows] == ["apartment_hideout_ceiling", "apartment_hideout_ceiling_r1"]
    assert [a["pos"][1] for a in rows] == [-10.0, -2.0]
    assert all(a["row"] == {"count": 3, "spacing": 7.0} and a["pos"][0] == 8.5 for a in rows)
    # a bedroom is one bay and keeps its one fixture at its centre
    bed = {"id": "bedroom", "story": 1, "bounds": [0.0, 0.0, 4.0, 5.0], "role": "connector",
           "center": [2.0, 2.5, 3.3]}
    one = _rows(_derive([bed]), "bedroom")
    assert len(one) == 1 and one[0]["pos"][:2] == [2.0, 2.5] and one[0]["row"] == {"count": 1, "spacing": 0.0}


def test_a_homes_room_hangs_domes_and_a_shops_keeps_its_troffers():
    """0.208.0, roadmap 229's species step: the home rule's rows are domes -- in a
    residence, and in a residence-like room inside a shop (the deli's hideout) --
    and a shop's own room keeps its fluorescent rows."""
    home = {"id": "living_room", "story": 0, "bounds": [0.0, 0.0, 9.0, 7.0], "role": "connector",
            "center": [4.5, 3.5, 0.0]}
    hideout = {"id": "apartment_hideout", "story": 1, "bounds": [-2.0, -14.0, 19.0, 2.0],
               "role": "fortifiable", "center": [8.5, -6.0, 3.3]}
    office = {"id": "back_office", "story": 0, "bounds": [30.0, 0.0, 39.0, 7.0], "role": "connector",
              "center": [34.5, 3.5, 0.0]}
    house = _derive([home], residence=True)
    shop = _derive([hideout, office])
    assert _rows(house, "living_room") and _rows(shop, "apartment_hideout")
    assert not [a for a in house if a["room"] == "living_room" and a["type"] == "fluorescent"]
    assert all(a["type"] == "dome" for a in _rows(house, "living_room"))
    assert all(a["type"] == "dome" for a in _rows(shop, "apartment_hideout"))
    assert _rows(shop, "back_office") and all(
        a["type"] == "fluorescent" for a in _rows(shop, "back_office"))
