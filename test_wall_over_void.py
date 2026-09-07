"""A partition may not stand on a slab that has been cut away (roadmap 114).

THE CAPTURED CASE is `specs/night_pawn.json`. Its story-1 drywall runs
-7..7 at y = 0, and its story-0 switchback climbs through a slab hole spanning
x 4.10..6.90 on that same storey -- so the wall crossed the shaft it should
have stopped at, and the flight topped out into 2.05 m of headroom where the
navmesh bake quantises the 2.0 m agent to `ceil(2.0/0.15) * 0.15 = 2.10`.
Those polygons were dropped, the ramp baked as two islands, and `nav_gate`
reported `stair_0 no_path`.

Six static hypotheses were refuted before this one was measured (stair width
at three values, two crate placements, an undersized slab cut, a missing
discharge bridge), so the mechanism was finally settled by raycasting UP from
every tread in the physics world. The control is `cr_pawn`, which carries a
byte-identical partition, places its stair clear of it, and passes.

These run without Blender -- partition_bounds and stairwell are bpy-free.

    python -m pytest test_wall_over_void.py -q
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ladder_geom
import partition_bounds as PB
import spec_loader
import stairwell

FX, FY = 44.0, 32.0


# ---- hole_cuts: which holes a wall's centreline actually crosses -----------

def test_x_wall_is_cut_by_a_hole_its_centreline_crosses():
    # hole x 4..7, y -2..4;  X-wall at y = 0 runs through it
    assert PB.hole_cuts("X", 0.0, [(4.0, -2.0, 7.0, 4.0)]) == [(4.0, 7.0)]


def test_x_wall_clear_of_the_hole_is_not_cut():
    # same hole, wall at y = 5 -- outside the hole's y band
    assert PB.hole_cuts("X", 5.0, [(4.0, -2.0, 7.0, 4.0)]) == []


def test_y_wall_reads_the_other_pair_of_edges():
    # a Y-wall runs along y and is positioned in x: the roles swap
    assert PB.hole_cuts("Y", 5.0, [(4.0, -2.0, 7.0, 4.0)]) == [(-2.0, 4.0)]
    assert PB.hole_cuts("Y", 0.0, [(4.0, -2.0, 7.0, 4.0)]) == []


def test_a_wall_on_the_hole_edge_is_left_alone():
    """The centreline decides, and the bound is strict. A stair's hole is
    oversized by 0.8 m on purpose; a wall seated exactly on its edge is the
    shaft's enclosure, not a wall over void."""
    assert PB.hole_cuts("X", 4.0, [(0.0, 4.0, 3.0, 8.0)]) == []
    assert PB.hole_cuts("X", 8.0, [(0.0, 4.0, 3.0, 8.0)]) == []


# ---- subtract: what is left of the run ------------------------------------

def test_a_hole_in_the_middle_leaves_two_pieces():
    assert PB.subtract(-10.0, 10.0, [(-2.0, 2.0)]) == [(-10.0, -2.0), (2.0, 10.0)]


def test_a_hole_at_the_end_leaves_one_piece():
    assert PB.subtract(-10.0, 10.0, [(6.0, 12.0)]) == [(-10.0, 6.0)]


def test_a_hole_swallowing_the_run_leaves_nothing():
    assert PB.subtract(-1.0, 1.0, [(-5.0, 5.0)]) == []


def test_slivers_below_min_span_are_dropped():
    # night_pawn's own residue: 6.90..7.00, 0.10 m of drywall
    assert PB.subtract(-7.0, 7.0, [(4.1, 6.9)], min_span=0.25) == [(-7.0, 4.1)]
    # ...and kept when nothing asks for a minimum
    assert PB.subtract(-7.0, 7.0, [(4.1, 6.9)]) == [(-7.0, 4.1), (6.9, 7.0)]


def test_an_uncut_run_is_returned_untouched_by_the_threshold():
    """A wall that meets no hole must bake byte-identically -- INCLUDING a
    legitimately short one, which `min_span` would otherwise delete."""
    assert PB.subtract(0.0, 0.1, [], min_span=0.25) == [(0.0, 0.1)]
    assert PB.subtract(-7.0, 7.0, [(20.0, 30.0)], min_span=0.25) == [(-7.0, 7.0)]


def test_two_holes_leave_three_pieces():
    assert PB.subtract(-10.0, 10.0, [(-6.0, -4.0), (4.0, 6.0)]) == [
        (-10.0, -6.0), (-4.0, 4.0), (6.0, 10.0)]


# ---- partition_spans: the clamp and the cut, in that order -----------------

def test_the_footprint_clamp_still_applies():
    assert PB.partition_spans(8, 22, "Y", 10.0, FX, FY) == [(8.0, 16.0)]


def test_clamp_and_cut_compose():
    # Y-wall clamped to 16, then a hole at 10..12 splits what is left
    assert PB.partition_spans(8, 22, "Y", 10.0, FX, FY,
                              [(9.0, 10.0, 11.0, 12.0)]) == [(8.0, 10.0),
                                                             (12.0, 16.0)]


def test_a_wall_wholly_outside_the_footprint_builds_nothing():
    assert PB.partition_spans(20, 30, "Y", 0.0, FX, FY) == []


# ---- remap_opening: a doorway keeps its world position --------------------

def test_an_opening_keeps_its_world_position_in_a_shortened_piece():
    # run -7..7, door at pos 0 -> world 0. Piece -7..4.1 has mid -1.45,
    # length 11.1, so the door sits at (0 - -1.45) / 11.1.
    npos = PB.remap_opening(0.0, -7.0, 7.0, -7.0, 4.1)
    assert npos is not None
    mid, length = (-7.0 + 4.1) / 2, 4.1 - -7.0
    assert abs((mid + npos * length) - 0.0) < 1e-9


def test_an_opening_in_a_removed_part_is_reported_absent():
    # door at world +5.0 with the piece ending at 4.1
    assert PB.remap_opening(5.0 / 14.0, -7.0, 7.0, -7.0, 4.1) is None


def test_an_untrimmed_piece_returns_the_authored_position():
    for pos in (-0.5, -0.3, 0.0, 0.35, 0.5):
        assert PB.remap_opening(pos, -7.0, 7.0, -7.0, 7.0) == pos


# ---- the captured case, end to end on the real spec ------------------------

def _night_pawn():
    return spec_loader.load_spec(os.path.join(HERE, "specs", "night_pawn.json"))


def test_night_pawn_wall_stops_at_the_stairwell():
    spec = _night_pawn()
    voids = stairwell.slab_openings(spec)
    p = spec.partitions[1]
    assert (p.story, p.axis, p.pos) == (1, "X", 0.0)
    spans = PB.partition_spans(p.start, p.end, p.axis, p.pos,
                               spec.footprint_x, spec.footprint_y,
                               voids.get(p.story, ()),
                               min_span=spec.wall_thick)
    assert len(spans) == 1, spans
    lo, hi = spans[0]
    assert lo == -7.0
    assert abs(hi - 4.1) < 1e-9, hi
    # ...and the flight it used to cover is now open to the storey above
    (hx0, _hy0, hx1, _hy1), = voids[1]
    assert hx0 < 5.5 < hx1                     # the stair's own x
    assert hi <= hx0 + 1e-9


def test_night_pawns_door_survives_the_cut():
    """The wall's only door is at world x = 0, well clear of the shaft. If a
    fix for a stair silently deleted the door in it, that would be a worse
    defect than the one being fixed."""
    spec = _night_pawn()
    p = spec.partitions[1]
    assert PB.remap_opening(p.openings[0].pos, -7.0, 7.0, -7.0, 4.1) is not None


def test_cr_pawn_is_unchanged_because_its_stair_is_clear():
    """The control. Same partition, a stair that does not cross it -- so the
    fix must not move a single metre of this building's geometry."""
    spec = spec_loader.load_spec(os.path.join(HERE, "specs", "cr_pawn.json"))
    voids = stairwell.slab_openings(spec)
    for p in spec.partitions:
        spans = PB.partition_spans(p.start, p.end, p.axis, p.pos,
                                   spec.footprint_x, spec.footprint_y,
                                   voids.get(p.story, ()),
                                   min_span=spec.wall_thick)
        assert spans == [(min(p.start, p.end), max(p.start, p.end))], (p, spans)


# ---- the name three passes have to agree on --------------------------------

def test_piece_zero_keeps_the_authored_name():
    """An unsplit wall -- 115 of the library's 129 specs -- must keep the slot
    ids, interactive ids and surface names it has always had."""
    assert PB.piece_name("int_1_1", 0) == "int_1_1"
    assert PB.piece_name("int_col_1_1", 0) == "int_col_1_1"


def test_later_pieces_are_suffixed():
    assert PB.piece_name("int_1_1", 1) == "int_1_1p1"
    assert PB.piece_name("int_col_-1_2", 2) == "int_col_-1_2p2"


# ---- the egress contract must name a door that was actually built ----------

def test_door_nodes_name_pieces_that_exist():
    """`_door_nodes` promises "the SAME stable id the builder bakes". Measured
    on the shipped build before this was fixed: 3 of night_pawn's 4 door nodes
    named an interactive that was in no baked set, because the wall they cite
    had been split and the position they cite is in the authored frame."""
    spec = _night_pawn()
    st = spec.stairs[0]
    served = stairwell.floors_served(spec, st)
    nodes = stairwell._door_nodes(spec, st, served)
    assert nodes, "no door nodes -- the test would prove nothing"
    voids = stairwell.slab_openings(spec)
    flights = stairwell.stair_footprints(spec)
    interior = [n for n in nodes if n["wall"].startswith("int_")]
    assert interior, "no interior door nodes -- the test would prove nothing"
    for n in interior:
        story = int(n["wall"].split("_")[1])
        i = int(n["wall"].split("_")[2].split("p")[0])
        p = spec.partitions[i]
        spans = PB.partition_spans(
            p.start, p.end, p.axis, p.pos, spec.footprint_x, spec.footprint_y,
            list(voids.get(story, ())) + list(flights.get(story, ())),
            min_span=spec.wall_thick)
        k = int(n["wall"].split("p")[1]) if "p" in n["wall"].split("_")[-1]             else 0
        lo, hi = spans[k]
        # the node's position must land inside the piece it names
        assert abs(n["pos"]) <= 0.5 + 1e-6, n
        world = (lo + hi) / 2 + n["pos"] * (hi - lo)
        assert lo - 1e-6 <= world <= hi + 1e-6, (n, lo, hi, world)


def test_a_door_in_a_removed_part_leaves_the_egress_contract():
    """night_pawn's `int_0_0` carries a door at world x 5.6 -- inside the
    stairwell. It is not built, so a route through it is not a route."""
    spec = _night_pawn()
    st = spec.stairs[0]
    nodes = stairwell._door_nodes(spec, st, stairwell.floors_served(spec, st))
    p = spec.partitions[0]
    raw_lo, raw_hi = min(p.start, p.end), max(p.start, p.end)
    dropped = [op for op in p.openings if abs(raw_lo + (op.pos + 0.5)
                                              * (raw_hi - raw_lo) - 5.6) < 0.2]
    assert dropped, "the captured door moved -- re-measure before editing this"
    assert not [n for n in nodes
                if n["wall"].startswith("int_0_0")
                and abs(n["pos"] - dropped[0].pos) < 1e-9]


# ---- the plan must not rule a wall across its own OPEN hatch ---------------

def test_the_plan_draws_no_wall_across_the_void():
    """Both rectangles come from floorplan's OWN transform rather than from a
    regex over the SVG: a pattern that matches nothing gives a clean bill of
    health over zero rows, which is how this check failed the first time it
    was written."""
    import re
    import floorplan as F
    spec = _night_pawn()
    tx = F._Tx(spec)
    voids = stairwell.slab_openings(spec).get(1, [])
    assert voids, "no void on story 1 -- the test would prove nothing"
    vpx = [(tx.x(x0), tx.y(y1), tx.x(x1), tx.y(y0)) for x0, y0, x1, y1 in voids]
    svg = F.render_story(spec, 1)
    block = re.search(r'<g id="walls">(.*?)</g>', svg, re.S)
    assert block, "no walls group in the plan"
    walls = [(float(a), float(b), float(a) + float(c), float(b) + float(d))
             for a, b, c, d in re.findall(
                 r'x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" '
                 r'height="([\d.]+)"', block.group(1))]
    assert walls, "no wall bands parsed -- the test would prove nothing"
    for v in vpx:
        for w in walls:
            ox = min(v[2], w[2]) - max(v[0], w[0])
            oy = min(v[3], w[3]) - max(v[1], w[1])
            assert not (ox > 0.5 and oy > 0.5), (v, w, ox, oy)


# ---- every producer that opens a slab, not just stairs (roadmap 117) -------

def test_wall_voids_carries_a_ramps_cut_and_its_footprint():
    """A ramp cuts the slab at its TOP and occupies the air of every storey it
    climbs through, and those are DIFFERENT rectangles -- the cut is offset
    half a run along the ascent axis. cbp_town's `int_0_1` stands in the
    footprint and in no cut, so a rule written from cuts alone leaves a wall
    across a ramp."""
    spec = spec_loader.load_spec(
        os.path.join(HERE, "specs", "foundry_heist_vertical.json"))
    rp = spec.ramps[0]
    cut = stairwell.ramp_hole(rp)
    fp = stairwell.ramp_footprint_rect(rp)
    assert cut[:2] != (rp.x, rp.y), "the cut is not centred on the ramp"
    assert abs(fp[0] + fp[2]) / 2 == abs(rp.x)
    voids = stairwell.wall_voids(spec)
    assert voids.get(rp.to_story), "no cut at the ramp's top storey"
    assert voids.get(min(rp.from_story, rp.to_story)), "no air on the climb"


def test_the_ramp_wall_that_exposed_this_is_clipped():
    """`foundry_heist_vertical`'s `int_0_4` stands over the ramp's slab cut.
    It was found because two derivations of a wall's pieces disagreed on it --
    880 of 882 door nodes agreed, and this was one of the 2 that did not."""
    spec = spec_loader.load_spec(
        os.path.join(HERE, "specs", "foundry_heist_vertical.json"))
    p = spec.partitions[4]
    assert (p.story, p.axis, p.pos) == (0, "X", -4.0)
    spans = PB.partition_spans(p.start, p.end, p.axis, p.pos,
                               spec.footprint_x, spec.footprint_y,
                               stairwell.wall_voids(spec).get(p.story, ()),
                               min_span=spec.wall_thick)
    assert len(spans) == 2, spans
    assert spans != [(min(p.start, p.end), max(p.start, p.end))]


def test_ladders_and_hatches_are_deliberately_not_voids():
    """Both open a slab, so the same argument reaches them -- and an earlier
    draft of `wall_voids` included both. The per-producer count is why they
    came back out: 0 walls in 162 specs stand over either, so shipping the
    arms would change geometry on an argument alone, with no case to check the
    result against. This pins the decision so it is re-taken deliberately,
    with the spec that needs it, rather than drifting back in."""
    spec = spec_loader.load_spec(
        os.path.join(HERE, "specs", "foundry_heist_vertical.json"))
    assert spec.ladders, "no ladders -- the test would prove nothing"
    assert [v for v in (spec.vertical_links or [])
            if v.kind in ("floor_hole", "hatch")], "no links to check"
    voids = stairwell.wall_voids(spec)
    for ld in spec.ladders:
        rect = ladder_geom.hole_rect(ld.x, ld.y, ld.width, ld.facing)
        for rects in voids.values():
            assert rect not in rects, (ld.id, rect)


def test_wall_voids_is_a_superset_of_what_it_replaced():
    """`wall_voids` took over from two calls unioned at three sites. It must
    not have lost a rectangle on the way."""
    for stem in ("night_pawn", "cbp_town_finale_midbalanced_schemafixed",
                 "foundry_heist_vertical", "primos_pizza"):
        spec = spec_loader.load_spec(os.path.join(HERE, "specs", stem + ".json"))
        old = {}
        for d in (stairwell.slab_openings(spec), stairwell.stair_footprints(spec)):
            for k, v in d.items():
                old.setdefault(k, []).extend(v)
        new = stairwell.wall_voids(spec)
        assert old, "nothing to compare -- the test would prove nothing"
        for story, rects in old.items():
            for r in rects:
                assert r in new.get(story, []), (stem, story, r)
