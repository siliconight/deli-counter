"""A ramp's slab cut stops at its head, is railed, and leaves the floor past the head clear (0.241.0).

Found by the factory's install test 10: a stranger's first `make` picked seed 9205, whose lot stands a
parking_garage, and Level Factory's drop-edge gate refused the export on 33 edges round the garage's ramp -- the cut
`stairwell.ramp_hole` made ran from the ramp's middle to half a run PAST its head, so the storey it climbs to stood
open over nothing for 5 m beyond the top of the ramp, a 3 m fall at most of its edges, and the cut's other edges
dropped onto the ramp unguarded. Every library ramp did the same, 5 to 8 m past its head (the factory's
docs/findings/ramp_cut_241/). On 0.240.0 every test here fails: the cut runs past the head, nothing rails it,
`ramp_landing` does not exist, and a guard's material was the builder's alone to choose.
"""
import os

import spec_loader
import stairwell
from spec_types import Ramp

HERE = os.path.dirname(os.path.abspath(__file__))
T = stairwell.GUARD_THICK
#: Every library spec with a ramp that cuts a slab, as the census read them (9 ramps).
RAMP_SPECS = ("cbp_town_finale_midbalanced_schemafixed", "cr_garage", "foundry_heist_vertical", "parking_garage",
              "parking_garage_a01", "parking_garage_a02")


def _cut_ramps():
    for stem in RAMP_SPECS:
        spec = spec_loader.load_spec(os.path.join(HERE, "specs", stem + ".json"))
        for i, rp in enumerate(spec.ramps):
            if rp.cut_slabs and rp.to_story > rp.from_story:
                yield stem, spec, i, rp


def _span(rect, axis):
    cx, cy, sx, sy = rect
    return (cy - sy / 2, cy + sy / 2) if axis == "Y" else (cx - sx / 2, cx + sx / 2)


def test_the_library_has_the_ramps_this_file_reads():
    """A test over a list that went empty would prove nothing."""
    assert sum(1 for _ in _cut_ramps()) == 9


def test_a_ramps_cut_stops_at_its_head():
    """The ramp's box is centred on (x, y) and climbs toward +axis, so its head is half a run ahead of the centre;
    the cut ends there and never past it, and begins at the ramp's middle, where it always has. A synthetic ramp along
    X holds the other axis to the same rule (no library ramp runs along X)."""
    ramps = [(stem, i, rp) for stem, _s, i, rp in _cut_ramps()]
    ramps.append(("synthetic X", 0, Ramp(x=2.0, y=-3.0, from_story=0, to_story=1, run=10.0, width=3.0, axis="X")))
    for stem, i, rp in ramps:
        centre = rp.y if rp.axis == "Y" else rp.x
        lo, hi = _span(stairwell.ramp_hole(rp), rp.axis)
        assert abs(hi - (centre + rp.run / 2)) < 1e-9, (stem, i, "the cut ends at", hi, "the head is",
                                                         centre + rp.run / 2)
        assert abs(lo - centre) < 1e-9, (stem, i, lo)
        cx, cy, sx, sy = stairwell.ramp_hole(rp)
        assert abs((sx if rp.axis == "Y" else sy) - (rp.width + 2 * stairwell.RAMP_CUT_SIDE)) < 1e-9, (stem, i)


def test_a_ramps_cut_is_railed_and_its_head_left_open():
    """`stair_guards` rails the cut as it rails a flight's hole: both long edges and the entry end, `GUARD_THICK / 2`
    outside it, on the storey whose slab it opens -- and nothing across the head, the way off the ramp. Where a rail is
    trimmed, it is by what the stair rule trims for (furniture on its line, a wall holding it), so the kept pieces
    stay on the right lines."""
    for stem, spec, i, rp in _cut_ramps():
        lo, hi = _span(stairwell.ramp_hole(rp), rp.axis)
        cx, cy, sx, sy = stairwell.ramp_hole(rp)
        lat0, lat1 = (cx - sx / 2, cx + sx / 2) if rp.axis == "Y" else (cy - sy / 2, cy + sy / 2)
        mine = [g for g in stairwell.stair_guards(spec) if g["stair"] == "ramp_%d" % i]
        assert mine, (stem, i, "no rail round the cut")
        assert all(g["kind"] == "rail" and g["story"] == rp.to_story for g in mine), (stem, i)
        lateral = "X" if rp.axis == "Y" else "Y"
        sides = {round(g["pos"], 6) for g in mine if g["axis"] == rp.axis}
        assert sides <= {round(lat0 - T / 2, 6), round(lat1 + T / 2, 6)} and sides, (stem, i, sides)
        ends = {round(g["pos"], 6) for g in mine if g["axis"] == lateral}
        assert ends == {round(lo - T / 2, 6)}, (stem, i, "the entry end", ends, "not the head", hi)
        for g in mine:
            if g["axis"] == rp.axis:
                assert lo - 1e-9 <= g["lo"] and g["hi"] <= hi + 1e-9, (stem, i, g)


def test_the_garages_rails_are_whole():
    """Where nothing stands on a rail's line it runs the whole edge: each garage ramp's three rails, untrimmed."""
    for stem, spec, i, rp in _cut_ramps():
        if "garage" not in stem:
            continue
        lo, hi = _span(stairwell.ramp_hole(rp), rp.axis)
        mine = [g for g in stairwell.stair_guards(spec) if g["stair"] == "ramp_%d" % i]
        assert len(mine) == 3, (stem, i, mine)
        for g in mine:
            if g["axis"] == rp.axis:
                assert (abs(g["lo"] - lo) < 1e-9 and abs(g["hi"] - hi) < 1e-9), (stem, i, g)


def test_no_wall_stands_across_a_ramps_head():
    """`ramp_landing` is a wall void past the head, as deep as the ramp is wide or IBC's 60 in, whichever is more,
    reaching back over the cut's last `RAMP_CUT_SIDE`: floor a body or a car arrives on, not a hole. Two library walls stood across a ramp's arrival and were clipped
    only by the old cut running past the head: foundry_heist_vertical's `int_0_4` on the head itself, and
    parking_garage_a02's wall at y 6, 1 m past ramp 0's head. Both still open where the ramp arrives."""
    import partition_bounds as PB
    import setbacks
    for stem, spec, i, rp in _cut_ramps():
        land = stairwell.ramp_landing(rp)
        assert land in stairwell.wall_voids(spec)[rp.to_story], (stem, i)
        depth = (land[3] - land[1]) if rp.axis == "Y" else (land[2] - land[0])
        assert abs(depth - max(rp.width, stairwell.RAMP_LANDING_MIN) - stairwell.RAMP_CUT_SIDE) < 1e-9, (stem, i, depth)
        assert stairwell.ramp_landing(rp) not in stairwell.slab_openings(spec).get(rp.to_story, ()), (stem, i)
    for stem, story, axis, pos in (("foundry_heist_vertical", 0, "X", -4.0), ("parking_garage_a02", 1, "X", 6.0)):
        spec = spec_loader.load_spec(os.path.join(HERE, "specs", stem + ".json"))
        p = next(p for p in spec.partitions if (p.story, p.axis, p.pos) == (story, axis, pos))
        spans = PB.partition_spans(p.start, p.end, p.axis, p.pos, spec.footprint_x, spec.footprint_y,
                                   stairwell.wall_voids(spec).get(p.story, ()), min_span=spec.wall_thick,
                                   extent=setbacks.storey_extent(spec, p.story))
        assert len(spans) == 2, (stem, spans)


def test_a_ramps_rails_are_steel_where_the_palette_has_it():
    """A garage's guardrail is painted steel, not a stair's wood: the rails carry `material`, and the builder takes a
    piece's own material before its wood-where-the-palette-has-it default."""
    for stem, spec, i, rp in _cut_ramps():
        mats = {m.id for m in spec.materials}
        want = "metal_painted" if "metal_painted" in mats else ("metal" if "metal" in mats else None)
        for g in stairwell.stair_guards(spec):
            if g["stair"] == "ramp_%d" % i:
                assert g.get("material") == want, (stem, i, g.get("material"))
    src = open(os.path.join(HERE, "deli_counter.py"), encoding="utf-8").read()
    assert 'mat = g.get("material") or ("wood" if "wood" in have else None)' in src
