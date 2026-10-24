"""Roadmap item 54: the slab VISUAL is tiled to light-budget-sized meshes.

Godot's GL Compatibility renderer lights at most `max_lights_per_object`
positional lights per MESH (engine default 8). A full-footprint `slab_<n>`
visual -- 34 to 52 m on the shipped buildings -- was one light budget for a
whole storey, and the reason level_factory ships a per-object light cap.
`floors.slab_tiles` cuts the visual; the trimesh collision slab stays ONE
piece, authoritative and holed, because a collider has no light budget.
"""
import floors
import portable_building as pb


def _area(tiles):
    return sum(t[2][0] * t[2][1] for t in tiles)


def test_a_small_footprint_is_byte_identical():
    """A footprint inside the tile must not change by one byte: same single
    piece, empty suffix, so the visual object is still named exactly
    `slab_<n>`. Stated relative to SLAB_TILE since 0.100.0 -- the byte-
    identity promise belongs to the LAW, not to any one tile size."""
    assert floors.slab_tiles(floors.SLAB_TILE, 3.0) == \
        [("", (0.0, 0.0), (floors.SLAB_TILE, 3.0))]
    assert floors.slab_tiles(3.0, 3.0) == [("", (0.0, 0.0), (3.0, 3.0))]


def test_the_arena_footprint_tiles_to_budget_size():
    tiles = floors.slab_tiles(52.0, 32.0)
    assert len(tiles) == 77                       # 11 x 7 at SLAB_TILE 5.0
    for _sfx, _off, (tx, ty) in tiles:
        # interior cut lines snap to whole millimetres, so a cell can sit
        # half a millimetre over the equal division
        assert tx <= floors.SLAB_TILE + 1e-3
        assert ty <= floors.SLAB_TILE + 1e-3
    assert round(_area(tiles), 6) == 52.0 * 32.0


def test_tiles_reassemble_the_exact_footprint():
    tiles = floors.slab_tiles(45.5, 23.7)
    lo_x = min(o[0] - d[0] / 2 for _s, o, d in tiles)
    hi_x = max(o[0] + d[0] / 2 for _s, o, d in tiles)
    lo_y = min(o[1] - d[1] / 2 for _s, o, d in tiles)
    hi_y = max(o[1] + d[1] / 2 for _s, o, d in tiles)
    assert (round(hi_x - lo_x, 6), round(hi_y - lo_y, 6)) == (45.5, 23.7)
    assert round(lo_x + hi_x, 6) == 0.0 and round(lo_y + hi_y, 6) == 0.0


def test_suffixes_are_unique_and_boundary_safe():
    """`slab_1` + suffix must never collide with `slab_10`: every suffix
    starts with `_t`, which is the boundary `_slab_holes_cut` matches on."""
    tiles = floors.slab_tiles(52.0, 32.0)
    sfx = [s for s, _o, _d in tiles]
    assert len(sfx) == len(set(sfx))
    assert all(s.startswith("_t") for s in sfx)
    assert tiles == floors.slab_tiles(52.0, 32.0)   # deterministic


def test_no_sliver_tiles():
    """Equal division, not fixed strides: 8.05 m is two ~4 m tiles, never an
    8 m tile plus a 5 cm strip. Item 41 (fragmentation) is the counter-
    pressure this law answers."""
    tiles = floors.slab_tiles(8.05, 3.0)
    assert len(tiles) == 2
    assert all(d[0] > 1.0 for _s, _o, d in tiles)


def test_an_exactly_tile_sized_footprint_is_one_piece():
    assert len(floors.slab_tiles(floors.SLAB_TILE, floors.SLAB_TILE)) == 1


def test_zero_or_negative_tile_disables_tiling():
    assert floors.slab_tiles(52.0, 32.0, 0) == [("", (0.0, 0.0), (52.0, 32.0))]
    assert floors.slab_tiles(52.0, 32.0, -1) == [("", (0.0, 0.0),
                                                  (52.0, 32.0))]


# --------------------------------------------------------------------------- #
# parapet runs: census #7 (2026-08-24) measured the arena's 52 m parapet_N
# binding 9 lights -- the one greybox VISUAL that had escaped the tile law.
# The builder now routes parapet visuals through slab_tiles; these pin the
# law at parapet proportions (one long axis, one thin one).
# --------------------------------------------------------------------------- #


def test_a_long_parapet_run_splits_along_its_length_only():
    tiles = floors.slab_tiles(52.0, 0.2)
    assert len(tiles) == 11                       # ceil(52 / SLAB_TILE)
    for _sfx, _off, (tx, ty) in tiles:
        assert tx <= floors.SLAB_TILE + 1e-3
        assert ty == 0.2                          # thickness never splits
    assert round(_area(tiles), 6) == round(52.0 * 0.2, 6)


def test_a_short_parapet_run_keeps_its_exact_name():
    """A run inside the tile keeps the empty suffix -- `parapet_N` on a
    small building stays byte-identical."""
    assert floors.slab_tiles(4.6, 0.2) == [("", (0.0, 0.0), (4.6, 0.2))]


# --------------------------------------------------------------------------- #
# roof_covered_nodes: equality became containment, because the top slab the
# themed roof replaces is now a SET of tiles and an AABB-equality test would
# find none of them -- the whole set would z-fight the themed module.
# --------------------------------------------------------------------------- #

_SLOT = {"slot_id": "roof_footprint", "role": "roof",
         "transform": {"translation": [0.0, 0.0, 7.55]},
         "fit": {"dims": [40.0, 30.0, 0.3]}}
# slot box in glb Y-up: centre (0, 7.55, 0), dims (40, 0.3, 30)


def _fake_boxes(monkeypatch, boxes):
    monkeypatch.setattr(pb, "_glb_visual_bboxes", lambda _p: boxes)


def test_every_tile_of_a_themed_roof_is_covered(monkeypatch):
    _fake_boxes(monkeypatch, {
        "slab_2_t0_0": ((-20.0, 7.4, -15.0), (-12.5, 7.7, -7.5)),
        "slab_2_t3_6": ((12.5, 7.4, 7.5), (20.0, 7.7, 15.0)),
    })
    got = pb.roof_covered_nodes("x.glb", [_SLOT], ["roof_footprint"])
    assert got == ["slab_2_t0_0", "slab_2_t3_6"]


def test_an_untiled_slab_still_matches():
    """The old single-node case: exactly the slot box. Containment includes
    equality, so a small building's one-piece slab is still stripped."""
    import pytest
    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(pb, "_glb_visual_bboxes",
                   lambda _p: {"slab_2": ((-20.0, 7.4, -15.0),
                                          (20.0, 7.7, 15.0))})
        got = pb.roof_covered_nodes("x.glb", [_SLOT], ["roof_footprint"])
        assert got == ["slab_2"]
    finally:
        mp.undo()


def test_walls_and_rooftop_props_stay(monkeypatch):
    """Nothing OUTSIDE the thin slab volume may be eaten: walls stop under
    it, rooftop units stand above it, and a parapet pokes past its rim."""
    _fake_boxes(monkeypatch, {
        "slab_2_t0_0": ((-20.0, 7.4, -15.0), (-12.5, 7.7, -7.5)),
        "ext_0_N": ((-20.0, 0.0, -15.35), (20.0, 7.4, -15.0)),
        "hvac_unit_0": ((2.0, 7.7, 3.0), (4.0, 8.9, 5.0)),
        "parapet_2_0": ((-20.0, 7.55, -15.35), (20.0, 8.45, -15.0)),
    })
    got = pb.roof_covered_nodes("x.glb", [_SLOT], ["roof_footprint"])
    assert got == ["slab_2_t0_0"]


def test_a_greybox_fallback_roof_keeps_all_its_tiles(monkeypatch):
    _fake_boxes(monkeypatch, {
        "slab_2_t0_0": ((-20.0, 7.4, -15.0), (-12.5, 7.7, -7.5)),
    })
    got = pb.roof_covered_nodes("x.glb", [_SLOT], themed_ids=[])
    assert got == []
