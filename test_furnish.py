"""Rooms get FURNITURE, and it is a different question from cover.

The walker, 2026-09-13: great progress outside the buildings, what about the
props inside. Measured over the 130 built shells before this: 819 prop slots
in all, 6.3 per building, 29 buildings with none. A bank tower's whole
interior was three teller lines and a funeral home had nothing.

`seed_cover` could not be the answer and must not be made into one. It fires
only when a room is BARE or has no SHELTER, caps at four pieces, and its
docstring argues the case: "props that give cover AND life without overkill".
That thesis is about COVER -- a mid-floor blocker changes how a room plays --
so furniture is a separate pass written to leave the cover balance alone.
These tests are what "leave it alone" means, stated so it cannot drift.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_design   # noqa: E402
import prop_species   # noqa: E402


def _spec(w=12.0, d=10.0, role="office", **kw):
    # The footprint is deliberately LARGER than the room: wall furniture
    # stands against interior walls only, because `_seed_clear` knows about
    # partitions and nothing here knows where the openings in an outside
    # wall are. A probe room that WAS the whole building would have four
    # exterior walls and no shelf would ever be placed.
    s = {"name": "furnish_probe", "seed": 1997, "story_height": 3.0,
         "footprint_x": w + 4.0, "footprint_y": d + 4.0, "n_stories": 1,
         "rooms": [{"id": "r0", "story": 0, "role": role,
                    "bounds": [-w / 2, -d / 2, w / 2, d / 2],
                    "combat_range": "medium"}],
         "volumes": [], "partitions": [], "stairs": []}
    s.update(kw)
    return s


def test_a_bare_room_is_furnished_to_a_density_derived_from_its_area():
    s = _spec(12.0, 10.0)                       # 120 m2
    n = level_design.furnish(s)
    assert n == round(120.0 / level_design._FURNISH_PER_AREA), n
    assert len(s["volumes"]) == n


def test_it_is_idempotent_because_what_is_there_counts():
    s = _spec(12.0, 10.0)
    first = level_design.furnish(s)
    assert first > 0
    assert level_design.furnish(s) == 0
    assert len(s["volumes"]) == first


def test_an_authored_room_is_topped_up_rather_than_doubled():
    s = _spec(12.0, 10.0)
    want = round(120.0 / level_design._FURNISH_PER_AREA)
    s["volumes"] = [{"name": f"authored_{i}", "x": -5.0 + i * 0.9, "y": -4.0,
                     "z": 0.45, "size_x": 0.6, "size_y": 0.6, "size_z": 0.9,
                     "collision": "convex"} for i in range(want - 1)]
    assert level_design.furnish(s) == 1


def test_nothing_it_puts_mid_floor_reaches_shelter_height():
    """The whole reason this is a separate pass, stated as the invariant it
    actually is.

    REFUTED FIRST DRAFT, kept above the result that replaced it. This
    asserted that nothing mid-floor reached `_COVER_MIN_Z` (0.60 m) and it
    failed on its first run: a desk is 0.75 and a floor safe is 1.00. That
    assertion was wrong, not the furniture -- a desk IS low cover, in this
    engine and in a real office, and pretending otherwise would have meant
    furnishing rooms with nothing but chairs.

    What `seed_cover`'s over-cover thesis actually protects is SHELTER: a
    body can fight from something only at `cover_break_height`, and one
    shelter piece per room is the rule that module enforces. So the
    invariant here is that this pass never creates one. Anything that tall
    goes flush against a wall, where it is a bookcase and not a redoubt.
    """
    shelter_z = level_design.shelter_height()
    tall_mid_floor = []
    for role in ("office", "storage", "bay", "vault", "utility", "lobby",
                 "something_unmatched"):
        s = _spec(20.0, 16.0, role=role)
        level_design.furnish(s)
        x0, y0, x1, y1 = s["rooms"][0]["bounds"]
        for v in s["volumes"]:
            if v["size_z"] < shelter_z:
                continue
            edge = min(abs(v["x"] - x0), abs(x1 - v["x"]),
                       abs(v["y"] - y0), abs(y1 - v["y"]))
            half = max(v["size_x"], v["size_y"]) / 2.0
            if edge > half + 0.5:
                tall_mid_floor.append((role, v["name"], round(edge, 2)))
    assert not tall_mid_floor, tall_mid_floor


def test_every_name_it_writes_routes_to_a_species_zoo_builds():
    """A volume whose name matches nothing is a grey box, which is the
    defect this pass exists to reduce. Cover pieces may be boxes by nature;
    furniture may not."""
    unrouted = set()
    for role in ("office", "storage", "bay", "vault", "utility", "lobby",
                 "something_unmatched"):
        s = _spec(20.0, 16.0, role=role)
        level_design.furnish(s)
        for v in s["volumes"]:
            if prop_species.species_for_name(v["name"]) is None:
                unrouted.add(v["name"].rsplit("_", 2)[0])
    assert not unrouted, sorted(unrouted)


def test_a_cupboard_is_left_alone():
    s = _spec(2.5, 2.5)                         # 6.25 m2
    assert level_design.furnish(s) == 0


def test_the_same_seed_and_room_furnish_the_same_way():
    a, b = _spec(14.0, 12.0), _spec(14.0, 12.0)
    level_design.furnish(a)
    level_design.furnish(b)
    assert [(v["name"], v["x"], v["y"]) for v in a["volumes"]] == \
           [(v["name"], v["x"], v["y"]) for v in b["volumes"]]


def test_wall_furniture_stands_on_outside_walls_but_never_in_an_opening():
    """SUPERSEDED, kept above the result that replaced it. 0.122.0 asserted
    furniture stayed OFF exterior walls: a shelf run had stood across the door
    of `office`'s exec suite, because `_seed_clear` guards partitions and knew
    nothing about exterior openings. The ban emptied every hall whose long
    walls are exterior, which cold run 9044's brewery frame showed. The rule
    now is the real one: exterior walls are allowed, and no piece may overlap
    an opening plus its clearance."""
    s = _spec(12.0, 10.0, role="storage")
    s["footprint_x"], s["footprint_y"] = 12.0, 10.0      # the room IS the shell
    s["ext_walls"] = [
        {"wall": "S", "story": 0, "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2}]},
        {"wall": "E", "story": 0, "openings": [
            {"kind": "window", "pos": 0.1, "width": 1.0, "sill": 1.0}]}]
    level_design.furnish(s)
    clear = level_design._FURNISH_OPENING_CLEAR
    on_ext = 0
    for v in s["volumes"]:
        if abs(v["y"] + 5.0) < 1.0:                        # against S
            on_ext += 1
            assert abs(v["x"] - 0.0) >= v["size_x"] / 2 + 0.6 + clear - 1e-6, v
        if abs(v["x"] - 6.0) < 1.0:                        # against E
            on_ext += 1
            assert abs(v["y"] - 1.0) >= v["size_y"] / 2 + 0.5 + clear - 1e-6, v
    assert on_ext > 0, "no wall piece stood on an exterior wall at all"


def test_a_setback_storey_keeps_its_outside_walls_bare():
    """The one place the exclusion survives: with a setback the storey's
    extent is not the footprint, and the opening positions are not re-derived
    here, so guessing them would be the defect this replaced."""
    s = _spec(12.0, 10.0, role="storage")
    s["footprint_x"], s["footprint_y"] = 12.0, 10.0
    s["setbacks"] = [{"story": 1, "n": 1.0}]
    level_design.furnish(s)
    for v in s["volumes"]:
        if v["size_z"] >= level_design.shelter_height():
            edge = min(6.0 - abs(v["x"]), 5.0 - abs(v["y"]))
            assert edge > level_design._FURNISH_EXT_KEEPOUT + 0.2, v


def test_a_hall_is_furnished_sparser_than_an_office_but_not_capped_at_ten():
    """Cold run 9044's brewery hall, about 1,000 m2: 63 pieces at office
    density, 10 under the old cap, 25 now."""
    assert level_design._furnish_target(120.0) == 8
    assert level_design._furnish_target(160.0) == 10
    assert level_design._furnish_target(1000.0) == 25
    assert level_design._furnish_target(5000.0) == level_design._FURNISH_HALL_MAX


def test_a_table_brings_its_chairs_and_the_set_is_still_idempotent():
    s = _spec(20.0, 16.0, role="lobby")
    first = level_design.furnish(s)
    chairs = [v for v in s["volumes"] if v["name"].startswith("chair_set_")]
    tables = [v for v in s["volumes"] if v["name"].startswith("table_")]
    assert tables and chairs, [v["name"] for v in s["volumes"]]
    assert len(chairs) <= 2 * len(tables)
    assert all(prop_species.species_for_name(c["name"]) == "chair" for c in chairs)
    assert level_design.furnish(s) == 0
    assert len(s["volumes"]) == first


#: Zoo's genome ranges for every species furnish routes to, as of Zoo 0.76.0,
#: ``species: (width, depth, height)`` as (min, max). Duplicated rather than
#: imported because Zoo is a separate repo -- the same reason
#: `material_kind.SKIN_KINDS` is a literal. A slot outside its species' range
#: is built as a plain box, so this is what "routes to a species" has to mean.
_ZOO_RANGES = {
    "desk": ((1.0, 12.0), (0.5, 6.0), (0.65, 1.3)),
    "chair": ((0.38, 12.0), (0.38, 2.0), (0.5, 1.1)),
    "table": ((0.6, 8.0), (0.6, 2.0), (0.4, 0.95)),
    "counter": ((0.8, 12.0), (0.5, 2.0), (0.85, 1.2)),
    "shelving": ((0.6, 20.0), (0.3, 1.4), (0.9, 4.5)),
    "filing_cabinet": ((0.35, 4.0), (0.5, 0.9), (0.7, 2.1)),
    "drop_safe": ((0.4, 1.2), (0.4, 1.0), (0.4, 1.5)),
    "water_tank": ((1.2, 3.0), (1.2, 3.0), (1.8, 4.5)),
}


def test_every_piece_is_a_size_its_species_builds():
    """The name test above passed while every chair this pass wrote was a
    box: `chair` routes to the species by NAME, and at 0.45 m it was below
    the species' 0.5 m minimum, so Zoo built the fallback. Cold run 9045's
    hall frame showed a table between two wooden cubes. Routing by name and
    building as the species are two different claims; this is the second."""
    pieces = [p for _, ps in level_design._FURNITURE for p in ps]
    pieces += list(level_design._FURNITURE_DEFAULT)
    pieces.append(("chair_set", 0.5, 0.5, level_design._CHAIR_H, "floor"))
    bad = []
    for name, w, d, h, _where in pieces:
        sp = prop_species.species_for_name(name + "_room_1")
        rng = _ZOO_RANGES.get(sp)
        assert rng is not None, (name, sp)
        for label, v, (lo, hi) in zip(("width", "depth", "height"),
                                      (max(w, d), min(w, d), h), rng):
            if not lo - 1e-9 <= v <= hi + 1e-9:
                bad.append(f"{name} -> {sp}: {label} {v} outside {lo}-{hi}")
    assert not bad, bad


def test_a_room_id_cannot_hijack_its_furniture_into_another_species():
    """`prop_species` matches keywords anywhere in a name, in table order. In
    a room called `teller_line`, `chair_set_teller_line_1_1` routed to
    `teller_line` before `chair` was tried, and Zoo built the fallback box --
    17 of them on cold run 9046. Furniture names carry a crc32 tag of the
    room id instead, and a tag is `r` plus hex digits."""
    for rid in ("teller_line", "safe_room", "counter_area", "tank_room",
                "desk_pool", "station_1", "bar_back", "col_bay"):
        s = _spec(20.0, 16.0, role="lobby")
        s["rooms"][0]["id"] = rid
        level_design.furnish(s)
        for v in s["volumes"]:
            want = v["name"].split("_r")[0]
            got = prop_species.species_for_name(v["name"])
            assert got == prop_species.species_for_name(want + "_x_1"), \
                (rid, v["name"], got)
    # and no species keyword can occur inside a tag at ANY alignment. The tag
    # is `_r` then eight hex digits then `_`; a set-of-letters check was the
    # first spelling of this and wrongly flagged `bar_`, whose `r` would have
    # to be followed by `_` where a tag's `r` is followed by a hex digit.
    template = ["_", "r"] + [None] * 8 + ["_"]      # None: any hex digit
    hexd = set("0123456789abcdef")

    def fits(word, at):
        for i, ch in enumerate(word):
            slot = template[at + i]
            if (slot is None and ch not in hexd) or                     (slot is not None and ch != slot):
                return False
        return True
    for words, _sp in prop_species.PROP_SPECIES:
        for w in words:
            assert not any(fits(w, at) for at in range(len(template) - len(w) + 1)), w
