"""What is in a room is what stands on its storey, and every library combat room has something to fight from (0.249.0,
the factory's roadmap 283).

0.246.0 made furnish's count ask a volume's FOOT. Three more places asked the question their own ways:
`level_design._room_has_cover` and `_room_has_shelter` -- which decide whether `seed_cover` stands shelter in a room --
kept `abs(z - (floor + size_z / 2)) < sh`, the float window 0.246.0 closed, and asked no storey of a cover marker;
`combat_audit._cover_in_room` asked `abs(z - floor) < sh` of a volume's CENTRE, which counts everything standing on the
floor below as cover in the room over it, and no storey of a marker either. All four ask
`level_design.stands_on_storey` and `marker_on_storey` now.

And nothing ran the shelter pass over the library. `enrich` runs in `presets.make`; `build.py` builds a spec's JSON as
it stands; the shelter test (`test_cover_breaks_sightlines.test_every_combat_room_big_enough_to_seed_has_shelter`)
asked presets alone. Measured on 0.248.0's library: eleven combat rooms of nine specs with nothing to fight from --
three by the storey leak, three since a refurnish moved furnish's tall pieces, five never sheltered in any committed
version. `migrate_shelter.py` filled them; the last test keeps the library a fixed point of the pass.
"""
import copy
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import combat_audit as CA  # noqa: E402
import level_design as LD  # noqa: E402
from spec_loader import spec_from_dict  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = 3.3
#: From the break height to a tall shelf, in 5 cm steps: the volume window is float noise, so the tests sweep for it
#: rather than naming the one height that found it (as `test_room_count_storey` does).
TALL = [round(1.30 + 0.05 * k, 2) for k in range(23)]


class _Thing:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _two_storeys(volumes=(), markers=()):
    """A spec dict: one 12 x 12 m combat room on each of two storeys, the upper over the lower."""
    return {"name": "storey_probe", "story_height": SH, "floor_thick": 0.3, "footprint_x": 12, "footprint_y": 12,
            "rooms": [{"id": "below", "story": 0, "bounds": [-6.0, -6.0, 6.0, 6.0], "combat_range": "medium"},
                      {"id": "above", "story": 1, "bounds": [-6.0, -6.0, 6.0, 6.0], "combat_range": "medium"}],
            "volumes": list(volumes), "markers": list(markers)}


def _piece(story, h, x=0.0, name="crate"):
    """A 1 x 1 m piece `h` tall standing on `story`'s floor, z rounded to the millimetre as the producers write it."""
    return {"name": name, "x": x, "y": 0.0, "z": round(story * SH + h / 2.0, 3),
            "size_x": 1.0, "size_y": 1.0, "size_z": h, "collision": "convex", "material": "wood"}


def test_a_piece_stands_on_the_storey_its_foot_is_on():
    for h in [0.3, 0.95] + TALL:
        z0, z1 = round(h / 2.0, 3), round(SH + h / 2.0, 3)
        assert LD.stands_on_storey(z0, h, 0.0, SH) and not LD.stands_on_storey(z0, h, SH, SH), h
        assert LD.stands_on_storey(z1, h, SH, SH) and not LD.stands_on_storey(z1, h, 0.0, SH), h


def test_a_marker_stands_on_the_floor_its_z_names():
    for m in ({"type": "cover_high", "x": 0.0, "y": 0.0, "z": 0.0},
              _Thing(type="cover_high", x=0.0, y=0.0, z=0.0)):
        assert LD.marker_on_storey(m, 0.0, SH) and not LD.marker_on_storey(m, SH, SH)
    up = {"type": "cover_low", "x": 0.0, "y": 0.0, "z": SH}
    assert LD.marker_on_storey(up, SH, SH) and not LD.marker_on_storey(up, 0.0, SH)
    # A marker with no z cannot be placed on a storey and keeps counting on every one, as every marker did.
    assert LD.marker_on_storey({"type": "cover_low", "x": 0.0, "y": 0.0}, SH, SH)


def test_every_library_cover_marker_names_its_floor():
    """What keeps `marker_on_storey`'s no-z fallback harmless: no library cover marker leans on it."""
    blind = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        blind += [(os.path.basename(p), m.get("id")) for m in d.get("markers") or []
                  if m.get("type") in ("cover_low", "cover_high") and "z" not in m]
    assert blind == [], blind


def test_the_producer_does_not_shelter_a_room_from_another_storey():
    """A tall piece shelters the room it stands in and neither room over or under it."""
    for h in TALL:
        if h < LD._COVER_HIGH_Z:
            continue
        down = _two_storeys([_piece(0, h)])
        below, above = down["rooms"]
        assert LD._room_has_shelter(down, below) and not LD._room_has_shelter(down, above), h
        up = _two_storeys([_piece(1, h)])
        below, above = up["rooms"]
        assert LD._room_has_shelter(up, above) and not LD._room_has_shelter(up, below), h


def test_the_producer_does_not_shelter_a_room_from_a_marker_on_another_storey():
    """twin_a01's front_left_1 read sheltered on 0.248.0 by a cover_high marker on the ground floor under it, and
    final_stand's stair_core by one two storeys up."""
    spec = _two_storeys(markers=[{"id": "cover_below", "type": "cover_high", "x": 0.0, "y": 0.0, "z": 0.0}])
    below, above = spec["rooms"]
    assert LD._room_has_shelter(spec, below)
    assert not LD._room_has_shelter(spec, above)
    assert not LD._room_has_cover(spec, above)


def test_the_audit_does_not_count_the_floor_below_as_cover_upstairs():
    """0.248.0's audit asked `abs(z - floor) < sh` of a piece's centre: a 1 m crate standing on the ground floor was
    cover in the room over it, and so was a marker on any storey."""
    room = _Thing(id="above", bounds=(-6.0, -6.0, 6.0, 6.0), story=1, combat_range="medium", role="")
    crate = _Thing(name="crate", x=0.0, y=0.0, z=0.5, size_x=1.0, size_y=1.0, size_z=1.0)
    marker = _Thing(type="cover_low", x=1.0, y=0.0, z=0.0)
    spec = _Thing(rooms=[room], volumes=[crate], markers=[marker], story_height=SH)
    assert abs(crate.z - room.story * SH) < SH          # the control: the old spelling let it in
    assert CA._cover_in_room(spec, room) == 0
    crate.z, marker.z = round(SH + 0.5, 3), SH
    assert CA._cover_in_room(spec, room) == 2


def test_cover_all_low_quotes_a_piece_on_its_own_storey():
    """A room furnished with 0.95 m crates over a 1.9 m shelf on the floor below cannot be fought in, and says so: on
    0.248.0 the shelf below was its cover, and had it not been, the finding would have quoted it as the tallest."""
    spec = _two_storeys([_piece(1, 0.95, x=-2.0, name="crate_a"), _piece(0, 1.9, x=2.0, name="shelf_b")])
    low = [f for f in CA.audit(spec_from_dict(spec), name="storey_probe")["findings"] if f[1] == "COVER_ALL_LOW"]
    assert [f[2].split("'")[1] for f in low] == ["above"], low
    assert "the tallest is 0.95 m" in low[0][2], low[0][2]


def test_a_room_whose_own_shelter_fits_nowhere_gets_the_smallest():
    """The rowhome preset's back_0, 8 x 11 m with a flight up its middle, chooses a 2.6 m shelf run by its words; the
    stair, its landings and the door approach refuse it everywhere. It read sheltered on 0.248.0 only because a 1.9 m
    piece on the floor above was counted in it."""
    import presets as P
    d = P.make("rowhome", enrich=True)
    back = next(r for r in d["rooms"] if r["id"] == "back_0")
    assert LD._seed_shelter(back)[0] == "shelf_run"
    assert [v["name"] for v in d["volumes"] if v["name"].endswith("_back_0_shelter")] == \
        ["%s_back_0_shelter" % LD._SEED_SHELTER_DEFAULT[0]]
    assert LD._room_has_shelter(d, back)


def test_the_library_is_a_fixed_point_of_the_shelter_pass():
    """Every library combat room the shelter pass would fill is filled. On 0.248.0 eleven were not, and nothing
    noticed: the guarantee was tested on presets, and a library room was sheltered when furnish happened to stand a
    tall piece in it. A refurnish that takes one away fails here."""
    import migrate_shelter
    owed = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        added = migrate_shelter.migrate(copy.deepcopy(d))
        owed += ["%s: %s" % (os.path.basename(p), a) for a in added]
    assert owed == [], "run `python migrations/migrate_shelter.py`: " + "; ".join(owed)
