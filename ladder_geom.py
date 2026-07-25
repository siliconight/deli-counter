"""
ladder_geom.py  --  pure ladder traversal geometry (no bpy), like partition_bounds
===================================================================================
Single source of truth for the two pieces of geometry that make a ladder
actually TRAVERSABLE, shared by the builder (deli_counter._ladders), the
layout linter (L14/L15) and the unit tests -- so the builder and its guards
can never drift apart (the partition_bounds pattern).

A ladder in DC is: visual rungs/rails, ONE thin collision plane (solid from
both sides -- climbing is the climb volume's job, walking through is never
possible), and, when it passes a slab, a through-hole big enough for a
climbing BODY. The climb volume holds a capsule ~0.5 m off the face on the
APPROACH side (the `facing` direction), so the hole must be biased onto that
side: symmetric cuts jam the capsule against the rim.

All coordinates are raw spec/Blender Z-up metres, like the spec itself.
"""

# Approach-side unit direction per facing (the side the rungs face and a
# climber mounts from). Spec Z-up: N=+y, S=-y, E=+x, W=-x.
APPROACH = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}

# The climb volume holds the capsule this far off the face (LF walk preview
# and the climb contract, docs/LADDER_CLIMB_CONTRACT.md).
CLIMB_STANDOFF = 0.5
# Body clearance the through-hole provides along the approach direction:
# standoff + capsule radius + margin. Biased: HOLE_BEHIND behind the face.
HOLE_ALONG = 1.3
HOLE_BEHIND = 0.2
HOLE_ACROSS_MARGIN = 0.6
# The solid face: thin plane, slightly wider than the rails.
PLANE_THICK = 0.1
PLANE_ACROSS_MARGIN = 0.12


def through_hole(x, y, width, facing):
    """Centre + size of the slab cut a body climbs through, biased onto the
    approach side. Returns (cx, cy, size_x, size_y)."""
    dx, dy = APPROACH.get(str(facing).upper(), (0, 1))
    # centre sits so the cut spans [-HOLE_BEHIND, +HOLE_ALONG-HOLE_BEHIND]
    # along the approach axis, relative to the ladder face.
    off = HOLE_ALONG / 2.0 - HOLE_BEHIND
    across = width + HOLE_ACROSS_MARGIN
    if dx:
        return (x + dx * off, y, HOLE_ALONG, across)
    return (x, y + dy * off, across, HOLE_ALONG)


def collision_plane(x, y, width, facing, z_lo, z_hi):
    """Centre + size of the ladder's solid face plane (full climb height).
    Returns (cx, cy, cz, size_x, size_y, size_z)."""
    dx, _dy = APPROACH.get(str(facing).upper(), (0, 1))
    across = width + PLANE_ACROSS_MARGIN
    cz = (z_lo + z_hi) / 2.0
    if dx:                      # facing E/W: plane thin in X, spans Y
        return (x, y, cz, PLANE_THICK, across, z_hi - z_lo)
    return (x, y, cz, across, PLANE_THICK, z_hi - z_lo)


def hole_rect(x, y, width, facing):
    """The through-hole as an axis-aligned rect (lo_x, lo_y, hi_x, hi_y)."""
    cx, cy, sx, sy = through_hole(x, y, width, facing)
    return (cx - sx / 2.0, cy - sy / 2.0, cx + sx / 2.0, cy + sy / 2.0)


def hole_overshoot(x, y, width, facing, footprint_x, footprint_y):
    """How far (m) the through-hole pokes past the slab footprint. 0.0 = fits.
    A ladder authored against the wrong wall for its facing produces a cut
    the slab can't contain -- the climb would dead-end into the exterior."""
    lo_x, lo_y, hi_x, hi_y = hole_rect(x, y, width, facing)
    hx, hy = footprint_x / 2.0, footprint_y / 2.0
    return max(0.0, -hx - lo_x, hi_x - hx, -hy - lo_y, hi_y - hy)


def partition_blocks_hole(part_axis, part_pos, part_lo, part_hi, wall_thick,
                          x, y, width, facing):
    """True if a partition wall crosses the through-hole rect: a wall over
    the hole walls off the climb at the story above."""
    lo_x, lo_y, hi_x, hi_y = hole_rect(x, y, width, facing)
    t = wall_thick / 2.0
    if str(part_axis).upper() == "Y":     # wall plane x = pos, runs along y
        return (lo_x - t <= part_pos <= hi_x + t
                and part_lo <= hi_y and part_hi >= lo_y)
    return (lo_y - t <= part_pos <= hi_y + t
            and part_lo <= hi_x and part_hi >= lo_x)
