"""An exploded axonometric of every building, with architectural cutaways (0.254.0, the factory's roadmap 293).

The plan drew one storey at a time and nothing drew how a building's storeys stack. `axonometric.py` draws each storey
as a slab raised by a DISPLAY OFFSET over its true floor, walls cut at the plan cut, roofs and ceilings off, from the
same layout the plan reads (`floorplan.storey_walls`). The checks are the walker's guide's
(`docs/reference/Floor_Plan_to_3D_Layout_and_Automap_Guide.md` at the factory root, section 10), asked of library
buildings: a doorway moved, a stair moved, an atrium kept open, two markers one above the other, the floors separated
with their markers and their elevations unchanged. Since 0.255.0 a stair is drawn as its treads: every surface
`stairwell.ascent_surfaces` says the builder builds, at its own height and place, a turn landing one riser thick.

THE TEST THAT MATTERS IS `test_the_offset_is_the_drawings_alone`.
"""
import copy
import dataclasses
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import axonometric as AX  # noqa: E402
import floorplan as FP  # noqa: E402
import spec_loader  # noqa: E402
from spec_types import Marker, SlabHole  # noqa: E402


def _load(name):
    return spec_loader.load_spec(os.path.join(HERE, "specs", name + ".json"))


def _storeys(svg):
    """{story: (elevation, offset, the group's text)}: each storey's group runs to the next one's, or to the
    connections drawn over them all -- a storey's group holds groups of its own, so a closing tag is no edge."""
    heads = list(re.finditer(r'<g id="storey_[^"]+" data-storey="(-?\d+)" data-elevation="([-\d.]+)" '
                             r'data-offset="([-\d.]+)">', svg))
    ends = [h.start() for h in heads[1:]] + [svg.index('<g id="connections">')]
    return {int(h.group(1)): (float(h.group(2)), float(h.group(3)), svg[h.end():e]) for h, e in zip(heads, ends)}


def test_the_offset_is_the_drawings_alone():
    """THE POINT OF THE ITEM, the guide's own rule: the display offsets belong to the drawing and never change a
    floor's elevation. Every storey is drawn, its true floor beside what the drawing adds, the lowest at no offset and
    each higher one higher; and the spec is read, never written."""
    spec = _load("deli_a03")
    before = copy.deepcopy(spec)
    storeys = _storeys(AX.render_axonometric(spec))
    assert spec == before, "rendering wrote to the spec"
    sh = FP._story_height(spec)
    assert sorted(storeys) == FP.stories_in(spec) == [-1, 0, 1]
    for s, (elev, off, _g) in storeys.items():
        assert abs(elev - s * sh) < 1e-6, (s, elev)
    offs = [storeys[s][1] for s in sorted(storeys)]
    assert offs[0] == 0.0 and all(b > a for a, b in zip(offs, offs[1:])), offs


def test_every_library_building_draws_every_storey():
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        spec = spec_loader.load_spec(path)
        svg = AX.render_axonometric(spec)
        assert sorted(_storeys(svg)) == FP.stories_in(spec), spec.name


def test_the_drawing_is_deterministic():
    spec = _load("office")
    assert AX.render_axonometric(spec) == AX.render_axonometric(spec)


def _door(svg, tag):
    m = re.search(r'data-opening="%s" data-kind="door" data-at="([-\d.]+),([-\d.]+)"' % re.escape(tag), svg)
    assert m, tag
    return float(m.group(1)), float(m.group(2))


def test_a_doorway_moved_moves_its_gap_in_both_drawings():
    """One layout: a doorway's gap stands where the plan's does, and moving the door in the spec moves it in both."""
    spec = _load("office")
    k, wall = next((k, w) for k, w in enumerate(spec.ext_walls)
                   if any(o.kind == "door" and o.tag for o in w.openings))
    j, op = next((j, o) for j, o in enumerate(wall.openings) if o.kind == "door" and o.tag)
    x0, y0 = _door(AX.render_axonometric(spec), op.tag)
    moved = copy.deepcopy(spec)
    ops = list(moved.ext_walls[k].openings)
    ops[j] = dataclasses.replace(ops[j], pos=ops[j].pos + 0.05)
    moved.ext_walls[k] = dataclasses.replace(moved.ext_walls[k], openings=ops)
    x1, y1 = _door(AX.render_axonometric(moved), op.tag)
    run = spec.footprint_x if wall.wall in ("N", "S") else spec.footprint_y
    assert abs(((x1 - x0) if wall.wall in ("N", "S") else (y1 - y0)) - 0.05 * run) < 2e-3
    plan = FP.render_story(moved, wall.story)
    assert 'data-opening="%s" data-kind="door"' % op.tag in plan


def test_a_stair_moved_moves_its_flight_and_its_column():
    spec = _load("office")
    svg = AX.render_axonometric(spec)
    moved = copy.deepcopy(spec)
    moved.stairs[0] = dataclasses.replace(moved.stairs[0], x=moved.stairs[0].x + 2.0)
    svg2 = AX.render_axonometric(moved)
    sid = re.escape(spec.stairs[0].id or "stair_0")
    a = re.search(r'<g data-stair="%s" data-from="0" data-to="1">(.*?)</g>' % sid, svg, re.S).group(1)
    b = re.search(r'<g data-stair="%s" data-from="0" data-to="1">(.*?)</g>' % sid, svg2, re.S).group(1)
    assert a != b, "the stair's column did not move"


def test_an_atrium_stays_open():
    """The upper floor keeps the opening rather than filling it with a walkable surface: a hole in a storey's slab is
    cut out of that storey's slab and nothing else."""
    spec = _load("office")
    opened = copy.deepcopy(spec)
    opened.slab_holes = list(opened.slab_holes) + [SlabHole(x=0.0, y=0.0, size_x=4.0, size_y=4.0, story=1)]
    before = re.findall(r'<mask id="voids_(\w+)".*?</mask>', AX.render_axonometric(spec), re.S)
    masks = dict(re.findall(r'<mask id="voids_(\w+)"(.*?)</mask>', AX.render_axonometric(opened), re.S))
    plain = dict(re.findall(r'<mask id="voids_(\w+)"(.*?)</mask>', AX.render_axonometric(spec), re.S))
    assert len(before) == len(masks)
    assert masks["1"].count("data-void") == plain["1"].count("data-void") + 1
    assert masks["G"].count("data-void") == plain["G"].count("data-void")


def test_two_markers_one_above_the_other_land_on_their_own_floors():
    spec = _load("office")
    sh = FP._story_height(spec)
    two = copy.deepcopy(spec)
    two.markers = list(two.markers) + [Marker(type="loot", x=1.0, y=1.0, z=0.1),
                                       Marker(type="loot", x=1.0, y=1.0, z=sh + 0.1)]
    storeys = _storeys(AX.render_axonometric(two))
    hits = {}
    for s, (_e, _o, g) in storeys.items():
        for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*data-marker="loot" data-at="1.000,1.000,'
                             r'([-\d.]+)"', g):
            hits[s] = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    assert set(hits) == {0, 1}, hits
    assert hits[0][0] == hits[1][0] and hits[1][1] < hits[0][1], "the upper marker is not drawn over the lower"


def test_the_axonometric_stands_a_partition_at_its_built_thickness():
    """One layout: the walls the axonometric stands are `floorplan.storey_walls`, at the thickness the builder
    stands them at, and `PART_T`, the plan's 0.15 m, is gone."""
    spec = _load("deli_a03")
    walls = [w for w in FP.storey_walls(spec, 0) if not w["exterior"]]
    assert walls and all(w["t"] == spec.wall_thick for w in walls)
    assert not hasattr(FP, "PART_T")


def _treads(svg):
    """{(stair, storey, k): (kind, world top z, x, y)} of every tread and turn landing drawn."""
    out = {}
    for m in re.finditer(r'data-(tread|landing)="([^":]+):(-?\d+):(\d+)" data-top="([-\d.]+)" '
                         r'data-at="([-\d.]+),([-\d.]+)"', svg):
        out[(m.group(2), int(m.group(3)), int(m.group(4)))] = (
            m.group(1), float(m.group(5)), float(m.group(6)), float(m.group(7)))
    return out


def test_a_flight_is_drawn_as_the_treads_the_builder_builds():
    """THE STAIRS AS TREADS (0.255.0). Every walking surface `stairwell.ascent_surfaces` says a stair builds -- the
    headroom gate's model of the same stair -- is drawn on the storey its flight climbs from, at its own height and
    place, and nothing else is drawn as a tread; a switchback's turn landing is drawn as one."""
    import stairwell
    for name in ("office", "deli_a03"):
        spec = _load(name)
        drawn = _treads(AX.render_axonometric(spec))
        want = {}
        for i, st in enumerate(spec.stairs):
            sid = stairwell.stair_ident(st, i)
            by_storey = {}
            for u in stairwell.ascent_surfaces(spec, st):
                by_storey.setdefault(u[0], []).append(u)
            for s, us in by_storey.items():
                if s not in FP.stories_in(spec):
                    continue
                for k, u in enumerate(us):
                    want[(sid, s, k)] = (round(u[3], 3), round(u[1], 3), round(u[2], 3))
        assert want, name
        assert set(drawn) == set(want), (name, sorted(set(drawn) ^ set(want))[:6])
        for key, (top, x, y) in want.items():
            assert drawn[key][1:] == (top, x, y), (name, key, drawn[key], (top, x, y))
        assert name != "office" or any(v[0] == "landing" for v in drawn.values()), name


def test_a_landing_is_a_plate_and_a_solid_flight_stands_on_its_floor():
    """The builder fills a solid leg's treads to the storey floor (`flight_solid_under`) and stands a turn landing
    one riser deep; the drawing does the same, so a landing does not stand as a column at a stair's head."""
    import stairwell
    spec = _load("office")
    st = spec.stairs[0]
    assert stairwell.flight_solid_under(spec, st, 0) and st.style == "switchback"
    svg = AX.render_axonometric(spec)
    sid = stairwell.stair_ident(st, 0)
    sh = FP._story_height(spec)
    riser = sh / stairwell._step_count(st, sh)

    def rises(attr):
        return [(float(top), float(rise)) for top, rise in re.findall(
            r'%s="%s:0:\d+" data-top="([-\d.]+)" data-at="[-\d.]+,[-\d.]+" data-rise="([-\d.]+)"'
            % (attr, re.escape(sid)), svg)]
    treads, landing = rises("data-tread"), rises("data-landing")
    assert len(landing) == 1 and treads
    assert abs(landing[0][1] - riser) < 2e-3, (landing, riser)
    assert all(abs(rise - top) < 2e-3 for top, rise in treads), treads   # each tread stands on storey 0's floor


def test_a_stair_moved_moves_its_treads():
    spec = _load("office")
    moved = copy.deepcopy(spec)
    moved.stairs[0] = dataclasses.replace(moved.stairs[0], x=moved.stairs[0].x + 2.0)
    a, b = _treads(AX.render_axonometric(spec)), _treads(AX.render_axonometric(moved))
    assert a, "no tread drawn: the check would ask nothing"
    assert set(a) == set(b)
    assert all(abs(b[k][2] - a[k][2] - 2.0) < 1e-6 and b[k][3] == a[k][3] for k in a)
