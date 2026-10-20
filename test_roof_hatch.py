"""The roof hatch: a prop slot with a lid for every hatch link on the roof slab (pure -- no Blender).

Factory roadmap 170. Fails on 0.223.0's tree: `interactives` has no `hatch` kind and nothing emits the slot.

0.239.0, the walker's look review of 2026-10-19 ("the hole of the ladder opening doesn't match the lid...they
should match"): a roof hatch stands over its ladder's own cut, and the built library's every one is held to it.
"""
import glob
import json
import os

import pytest

import interactives
import ladder_geom
import roof_hatch
from spec_types import Ladder, LevelSpec, VerticalLink

HERE = os.path.dirname(os.path.abspath(__file__))


def _spec(links, ladders=()):
    s = LevelSpec(name="t", footprint_x=20.0, footprint_y=16.0, n_stories=2, story_height=3.2)
    s.vertical_links = list(links)
    s.ladders = list(ladders)
    return s


def test_the_hatch_machine_opens_by_default_and_shuts():
    m = interactives.derive_interactive("t", "roof_hatch_13_-9", 2, "hatch", 0.0)
    assert m["kind"] == "hatch"
    assert m["states"] == ["open", "closed"]
    assert m["default"] == "open"
    assert m["state_geometry"] == {"open": "roof_hatch", "closed": "roof_hatch"}
    assert m["collision_per_state"] == {"open": False, "closed": True}
    events = {(t["from"], t["to"]) for t in m["transitions"]}
    assert events == {("open", "closed"), ("closed", "open")}
    assert m["id"].startswith("t:if:")


def test_a_roof_hatch_link_emits_one_lidded_slot_on_the_slab_top():
    s = _spec([VerticalLink(kind="hatch", story=2, x=13.0, y=-9.0)],
              [Ladder(x=13.0, y=-9.0, from_story=1, to_story=2, facing="S", role="roof_access")])
    out = roof_hatch.roof_hatches(s, style=3)
    assert len(out) == 1
    slot, entry, center, size = out[0]
    assert slot["slot_id"] == "roof_hatch_13_-9"
    assert slot["role"] == "prop" and slot["species"] == "roof_hatch"
    assert slot["fit"]["dims"] == [1.66, 1.66, 0.2]            # 1.5 m hole + 0.08 m curb a side
    assert slot["fit"]["collision"] == "none"                   # the species owns its collision
    assert slot["style"] == 3
    # OVER THE LADDER'S CUT (0.239.0): the ladder faces S and cuts its hole 0.45 m south of its face, so the
    # hatch's square stands there. Until 0.239.0 it stood at the link, (13.0, -9.0), on the ladder's face, and the
    # ladder's cut ran 0.35 m past the curb.
    assert slot["transform"]["translation"] == [13.0, -9.45, round(2 * 3.2 + 0.1, 4)]
    assert slot["transform"]["rot_y"] == 180.0                  # the ladder faces S
    assert slot["interactive"]["kind"] == "hatch"
    assert slot["interactive"]["default"] == "open"
    assert entry["id"] == slot["interactive"]["id"]
    assert entry["slot_ref"] == "roof_hatch_13_-9"
    assert center == (13.0, -9.45, 6.4 + 0.1) and size == (1.66, 1.66, 0.2)


def test_an_authored_hole_size_sizes_the_curb():
    s = _spec([VerticalLink(kind="hatch", story=2, x=0.0, y=0.0, size_x=1.0, size_y=1.2)])
    (slot, _e, _c, size), = roof_hatch.roof_hatches(s)
    assert slot["fit"]["dims"] == [1.16, 1.36, 0.2]
    assert slot["transform"]["rot_y"] == 0.0                    # no ladder here: north
    assert tuple(round(v, 6) for v in size) == (1.16, 1.36, 0.2)


def test_a_hatch_below_the_roof_is_not_a_scuttle():
    s = _spec([VerticalLink(kind="hatch", story=1, x=4.0, y=4.0),
               VerticalLink(kind="floor_hole", story=2, x=6.0, y=6.0),
               VerticalLink(kind="hatch", story=2, x=8.0, y=8.0, cut_slab=False)])
    assert roof_hatch.roof_hatches(s) == []


def test_two_hatches_get_two_ids():
    s = _spec([VerticalLink(kind="hatch", story=2, x=2.0, y=2.0),
               VerticalLink(kind="hatch", story=2, x=-2.0, y=2.0)])
    out = roof_hatch.roof_hatches(s)
    ids = {e["id"] for _s, e, _c, _z in out}
    assert len(out) == 2 and len(ids) == 2


def _inside(inner, outer, eps=1e-6):
    return (inner[0] >= outer[0] - eps and inner[1] >= outer[1] - eps
            and inner[2] <= outer[2] + eps and inner[3] <= outer[3] + eps)


@pytest.mark.parametrize("facing", ["N", "E", "S", "W"])
def test_the_hatch_stands_over_its_ladders_cut(facing):
    """The ladder's through-hole lies inside the hatch's opening, and the opening inside the curb by the curb's
    width a side, whichever way the ladder faces. FAILS ON 0.238.0: there is no `opening`, and the slot stood on
    the link with the ladder's cut 0.35 m past its square."""
    s = _spec([VerticalLink(kind="hatch", story=2, x=3.0, y=-2.0)],
              [Ladder(x=3.0, y=-2.0, from_story=1, to_story=2, facing=facing, role="roof_access")])
    ld = s.ladders[0]
    cut = ladder_geom.hole_rect(ld.x, ld.y, ld.width, ld.facing)
    cx, cy, sx, sy = roof_hatch.opening(s, s.vertical_links[0])
    hole = (cx - sx / 2.0, cy - sy / 2.0, cx + sx / 2.0, cy + sy / 2.0)
    assert _inside(cut, hole)
    assert (sx, sy) == (roof_hatch.DEFAULT_HOLE, roof_hatch.DEFAULT_HOLE)   # the square keeps its size
    (slot, _e, (x, y, _z), (w, d, _h)), = roof_hatch.roof_hatches(s)
    curb = (x - w / 2.0 + roof_hatch.CURB, y - d / 2.0 + roof_hatch.CURB,
            x + w / 2.0 - roof_hatch.CURB, y + d / 2.0 - roof_hatch.CURB)
    assert _inside(hole, curb) and _inside(curb, hole)


def test_without_a_ladder_the_hatch_stands_on_its_link():
    s = _spec([VerticalLink(kind="hatch", story=2, x=1.0, y=4.0, size_x=1.2, size_y=1.0)])
    assert roof_hatch.opening(s, s.vertical_links[0]) == (1.0, 4.0, 1.2, 1.0)


def test_a_square_too_small_for_the_cut_grows_round_both_and_turns_with_the_slot():
    """A hatch authored smaller than its ladder's cut (1.0 m against 1.1 x 1.3) takes the box round both, and a
    quarter-turned slot carries that box's world sides swapped as its own (w, d), as `hole_causes._local` does."""
    s = _spec([VerticalLink(kind="hatch", story=2, x=0.0, y=0.0, size_x=1.0, size_y=1.0)],
              [Ladder(x=0.0, y=0.0, from_story=1, to_story=2, facing="E", role="roof_access")])
    ld = s.ladders[0]
    cut = ladder_geom.hole_rect(ld.x, ld.y, ld.width, ld.facing)
    cx, cy, sx, sy = roof_hatch.opening(s, s.vertical_links[0])
    hole = (cx - sx / 2.0, cy - sy / 2.0, cx + sx / 2.0, cy + sy / 2.0)
    assert _inside(cut, hole) and _inside((-0.5, -0.5, 0.5, 0.5), hole)
    (slot, _e, _c, size), = roof_hatch.roof_hatches(s)
    assert slot["transform"]["rot_y"] == 90.0
    assert tuple(round(v, 4) for v in size[:2]) == (round(sx + 0.16, 4), round(sy + 0.16, 4))
    assert slot["fit"]["dims"][:2] == [round(sy + 0.16, 4), round(sx + 0.16, 4)]


def _built_roof_hatches():
    """``(spec, slot, voids)`` for every roof hatch slot the built library carries. A footprint roof's voids are in
    the spec's frame already: `roofs` takes them about (0, 0), the centre every roof with a hole has."""
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "build", "*.slots.json"))):
        name = os.path.basename(p)[:-len(".slots.json")]
        if name.startswith("lf_"):
            continue
        slots = json.load(open(p, encoding="utf-8")).get("slots") or []
        hatches = [s for s in slots if s.get("species") == roof_hatch.SPECIES and s["slot_id"].startswith("roof_hatch_")]
        if not hatches:
            continue
        roof = [s for s in slots if s["slot_id"] == "roof_footprint"]
        if len(roof) != 1:
            continue
        voids = [(v["x0"], v["y0"], v["x1"], v["y1"]) for v in roof[0]["fit"].get("voids") or []]
        out.extend((name, h, voids) for h in hatches)
    return out


def test_every_built_roof_hatch_holds_every_hole_cut_under_it():
    """The built library: each roof hatch's curb (its slot less the curb a side) holds every hole the roof is cut
    with under it -- its own square and its ladder's cut -- so the opening a body sees is the one the lid covers.
    FAILS ON 0.238.0's build: 39 hatches, every ladder's cut 0.35 m past the square and 0.27 m past the curb."""
    built = _built_roof_hatches()
    # 39 when this was written: the 46 roof hatch links in the specs, less those whose roof is not one footprint slot
    assert len(built) >= 35, "the library carries fewer roof hatches than when this was written: %d" % len(built)
    bad = []
    for name, h, voids in built:
        x, y = h["transform"]["translation"][:2]
        w, d = h["fit"]["dims"][:2]
        if int(h["transform"].get("rot_y") or 0) % 180:
            w, d = d, w
        curb = (x - w / 2.0 + roof_hatch.CURB, y - d / 2.0 + roof_hatch.CURB,
                x + w / 2.0 - roof_hatch.CURB, y + d / 2.0 - roof_hatch.CURB)
        under = [v for v in voids if v[0] < curb[2] and curb[0] < v[2] and v[1] < curb[3] and curb[1] < v[3]]
        if not under or not all(_inside(v, curb, eps=1e-3) for v in under):
            bad.append((name, h["slot_id"], [tuple(round(c, 3) for c in v) for v in under]))
    assert not bad, bad[:5]
