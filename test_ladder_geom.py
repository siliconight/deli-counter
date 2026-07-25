"""Unit tests for ladder_geom.py -- the pure source of truth for ladder
traversal geometry (shared by the builder, the L14/L15 linter and the compose
bake). Pins the guarantees walk-testing exposed:

  - the through-hole is biased onto the APPROACH side (a symmetric cut jams
    the climbing capsule against the rim),
  - the hole always contains the capsule's climb column (standoff + radius),
  - the collision plane is thin, full-height, wider than the rails, and
    clear of the climb snap distance,
  - out-of-footprint holes and partition-blocked holes are detectable
    (what L14/L15 gate on).
"""
import ladder_geom as LG


def test_hole_biased_onto_approach_side_all_facings():
    for facing, (dx, dy) in LG.APPROACH.items():
        lo_x, lo_y, hi_x, hi_y = LG.hole_rect(0.0, 0.0, 0.5, facing)
        # signed extent along the approach direction
        lo = lo_x if dx == 1 else (-hi_x if dx == -1 else (lo_y if dy == 1 else -hi_y))
        hi = hi_x if dx == 1 else (-lo_x if dx == -1 else (hi_y if dy == 1 else -lo_y))
        assert lo == -LG.HOLE_BEHIND, (facing, lo)
        assert hi == LG.HOLE_ALONG - LG.HOLE_BEHIND, (facing, hi)
        assert hi > -lo, "must extend further on the approach side"


def test_hole_contains_the_climb_column():
    # capsule of radius 0.4 held CLIMB_STANDOFF off the face must fit
    # inside the hole along the approach axis with margin.
    r = 0.4
    assert LG.CLIMB_STANDOFF - r >= -LG.HOLE_BEHIND
    assert LG.CLIMB_STANDOFF + r <= LG.HOLE_ALONG - LG.HOLE_BEHIND


def test_hole_across_size_covers_ladder_width():
    _, _, sx, sy = LG.through_hole(0, 0, 0.5, "E")
    assert (sx, sy) == (LG.HOLE_ALONG, 0.5 + LG.HOLE_ACROSS_MARGIN)
    _, _, sx, sy = LG.through_hole(0, 0, 0.5, "N")
    assert (sx, sy) == (0.5 + LG.HOLE_ACROSS_MARGIN, LG.HOLE_ALONG)


def test_collision_plane_thin_full_height_and_clear_of_snap():
    cx, cy, cz, sx, sy, sz = LG.collision_plane(-21.0, 9.0, 0.5, "E", 0.0, 4.0)
    assert (cx, cy, cz) == (-21.0, 9.0, 2.0)
    assert sx == LG.PLANE_THICK and sz == 4.0
    assert sy == 0.5 + LG.PLANE_ACROSS_MARGIN
    # capsule at the snap distance never scrapes the plane
    assert LG.CLIMB_STANDOFF - 0.4 > LG.PLANE_THICK / 2.0
    # facing N: thin axis flips
    _, _, _, sx, sy, _ = LG.collision_plane(0, 0, 0.5, "N", 0, 4)
    assert sy == LG.PLANE_THICK and sx == 0.5 + LG.PLANE_ACROSS_MARGIN


def test_hole_overshoot_detects_bad_authoring():
    # ladder against the E wall facing E: the hole pokes out of the slab.
    assert LG.hole_overshoot(21.8, 0.0, 0.5, "E", 44.0, 32.0) > 0.0
    # same spot facing W: hole cuts inward, fits.
    assert LG.hole_overshoot(21.8, 0.0, 0.5, "W", 44.0, 32.0) == 0.0
    # interior ladder: fits whatever the facing.
    for f in "NSEW":
        assert LG.hole_overshoot(0.0, 0.0, 0.5, f, 44.0, 32.0) == 0.0


def test_partition_blocks_hole():
    # wall plane x=0.4 runs along y through the hole of an E-facing ladder
    # at origin (hole spans x -0.2..1.1) -> blocked.
    assert LG.partition_blocks_hole("Y", 0.4, -5.0, 5.0, 0.35, 0, 0, 0.5, "E")
    # same wall but its span stops short of the hole -> clear.
    assert not LG.partition_blocks_hole("Y", 0.4, 2.0, 5.0, 0.35, 0, 0, 0.5, "E")
    # wall far from the hole -> clear.
    assert not LG.partition_blocks_hole("Y", 6.0, -5.0, 5.0, 0.35, 0, 0, 0.5, "E")
    # X-axis wall crossing the hole vertically -> blocked.
    assert LG.partition_blocks_hole("X", 0.0, -1.0, 2.0, 0.35, 0, 0, 0.5, "E")


def test_builder_parity_with_release_0_86_values():
    # the values 0.86.0 shipped (verified by walk test) -- the helper must
    # keep producing them so builder output can't silently drift.
    cx, cy, sx, sy = LG.through_hole(-21.0, 9.0, 0.5, "E")
    assert (cx, cy, sx, sy) == (-20.55, 9.0, 1.3, 1.1)
    p = LG.collision_plane(-21.0, 9.0, 0.5, "E", 0.0, 4.0)
    assert p == (-21.0, 9.0, 2.0, 0.1, 0.62, 4.0)
