"""The roof hatch: a prop slot with a lid for every hatch link on the roof slab (pure -- no Blender).

Factory roadmap 170. Fails on 0.223.0's tree: `interactives` has no `hatch` kind and nothing emits the slot.
"""
import interactives
import roof_hatch
from spec_types import Ladder, LevelSpec, VerticalLink


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
    assert slot["transform"]["translation"] == [13.0, -9.0, round(2 * 3.2 + 0.1, 4)]
    assert slot["transform"]["rot_y"] == 180.0                  # the ladder faces S
    assert slot["interactive"]["kind"] == "hatch"
    assert slot["interactive"]["default"] == "open"
    assert entry["id"] == slot["interactive"]["id"]
    assert entry["slot_ref"] == "roof_hatch_13_-9"
    assert center == (13.0, -9.0, 6.4 + 0.1) and size == (1.66, 1.66, 0.2)


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
