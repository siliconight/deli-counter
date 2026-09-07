"""Per-storey footprint -- the single source of truth for how wide a building
is at a given height (roadmap 116).

WHY THIS EXISTS. `LevelSpec` carries one `footprint_x`, one `footprint_y` and
one `n_stories`, so every shell the pipeline has ever made is a single
extruded rectangle. Measured 2026-09-07 by `tools/massing.py` across the whole
library: 127 shells, every one describing ONE footprint, and the 114 readable
from built geometry filling their own bounding box with min 1.000, mean 1.000
and no variance at all. Not "mostly boxes" -- 127 rectangular prisms.

WHAT A SETBACK IS. An upper storey inset from the base footprint, per side.
`story` names the LOWEST storey the inset applies to and it carries upward
until a higher setback overrides it, so one entry steps a building once and
two entries step it twice. A side left at 0.0 stays flush, which is what a
street frontage usually wants: the facade holds the building line while the
rear and the sides step back.

WHY `footprint_x` / `footprint_y` STAY AS THEY ARE. 24 source files read them,
including `lot/preview.py` and `lot/site_layout_lint.py`, which place the
building on a site and must know its widest extent. They keep meaning exactly
that: the base footprint, and therefore the maximum. Setbacks only ever
subtract. Nothing that does not opt in changes by a millimetre.

WHAT A SETBACK GIVES YOU BESIDES A SILHOUETTE. The slab that caps an inset
storey's neighbour spans the LOWER storey's extent -- so the step is a
walkable roof terrace with a real collider, not a texture. That is the whole
argument for changing the mass rather than adding a layer on top: it is the
only option a body can stand on.

EVERYTHING ASKS THIS MODULE, and that is the point. The builder's `_exterior`
and `_slabs`, the 2D floorplan, the partition clamp and `layout_lint`'s L13
and L19 all need "how wide is this building HERE", and four spellings of that
is how a wall ends up poking out of a facade nobody stepped back.
"""
from __future__ import annotations


def _story_range(spec):
    """(base, top) as `Builder._story_range` computes it."""
    base = -1 if getattr(spec, "has_basement", False) else 0
    return base, int(getattr(spec, "n_stories", 1) or 1)


def setback_for(spec, story):
    """The setback governing `story`, or None.

    The HIGHEST entry at or below `story` wins, so a second entry higher up
    overrides the first rather than compounding it. Two entries step a
    building twice; the alternative reading -- adding every applicable inset
    together -- makes the second entry's numbers depend on the first, which is
    how an author ends up computing deltas by hand.
    """
    best = None
    for sb in getattr(spec, "setbacks", ()) or ():
        if sb.story <= story and (best is None or sb.story > best.story):
            best = sb
    return best


def storey_extent(spec, story):
    """``(x0, y0, x1, y1)`` of `story`'s exterior wall CENTRELINES.

    The centreline, not the inner face, because that is what `footprint_x / 2`
    has always meant and what every existing reader compares against. A
    consumer that needs the room side subtracts half a wall thickness -- see
    `layout_lint` L19, which does exactly that and had to learn the difference
    the hard way (roadmap 115).
    """
    hx = float(spec.footprint_x) / 2.0
    hy = float(spec.footprint_y) / 2.0
    x0, y0, x1, y1 = -hx, -hy, hx, hy
    sb = setback_for(spec, story)
    if sb is not None:
        x0 += max(0.0, float(sb.inset_w))
        x1 -= max(0.0, float(sb.inset_e))
        y0 += max(0.0, float(sb.inset_s))
        y1 -= max(0.0, float(sb.inset_n))
    return (x0, y0, x1, y1)


def storey_size(spec, story):
    """``(size_x, size_y)`` of `story` -- the per-storey `footprint_x/y`."""
    x0, y0, x1, y1 = storey_extent(spec, story)
    return (x1 - x0, y1 - y0)


def storey_centre(spec, story):
    """``(cx, cy)``. An asymmetric setback moves the storey's centre, so a
    wall cannot be placed at +/- half a size and be right."""
    x0, y0, x1, y1 = storey_extent(spec, story)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def slab_extent(spec, story):
    """``(x0, y0, x1, y1)`` of the slab whose TOP FACE is `story`'s floor.

    A slab CAPS THE STOREY BELOW IT, so it takes that storey's extent -- which
    is what turns a setback into a walkable terrace rather than a ledge the
    upper wall stands on the edge of. The lowest slab has nothing below it and
    takes its own storey's.
    """
    base, _top = _story_range(spec)
    return storey_extent(spec, max(story - 1, base))


def is_stepped(spec):
    """True when any storey is inset from the base footprint."""
    base, top = _story_range(spec)
    first = storey_extent(spec, base)
    return any(storey_extent(spec, k) != first for k in range(base, top + 1))


def findings(spec):
    """``[(code, message)]`` -- setbacks that cannot be built.

    A spec-time check, because an inset that eats the whole footprint emits a
    zero-width wall and an inset deeper than the storey below leaves the upper
    storey standing on air. Neither is caught by anything downstream: the
    geometry builder would happily emit both.
    """
    out = []
    base, top = _story_range(spec)
    for sb in getattr(spec, "setbacks", ()) or ():
        if sb.story <= base:
            out.append(("SETBACK_AT_BASE",
                        f"setback at story {sb.story} is at or below the "
                        f"lowest storey ({base}); it would inset the whole "
                        f"building rather than step it"))
        if sb.story > top:
            out.append(("SETBACK_ABOVE_ROOF",
                        f"setback at story {sb.story} is above the roof "
                        f"({top}); it builds nothing"))
    for k in range(base, top + 1):
        sx, sy = storey_size(spec, k)
        if sx <= 0.0 or sy <= 0.0:
            out.append(("SETBACK_CONSUMES_STOREY",
                        f"story {k} insets to {sx:.2f} x {sy:.2f} m -- the "
                        f"setback is deeper than the footprint"))
            continue
        wt = float(getattr(spec, "wall_thick", 0.3) or 0.3)
        if sx < 2 * wt or sy < 2 * wt:
            out.append(("SETBACK_LEAVES_NO_ROOM",
                        f"story {k} insets to {sx:.2f} x {sy:.2f} m, which is "
                        f"thinner than its own two walls ({2 * wt:.2f} m)"))
    return out
