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


def test_furniture_does_not_stand_against_an_outside_wall():
    """One shell of 130 said why. A shelf run went flush against the outside
    wall of `office`'s exec suite, across its door, and the nav gate reported
    the objective unreachable -- `_seed_clear` keeps a piece a metre off any
    PARTITION, which is where interior doors are, and knows nothing about
    the openings in an exterior wall."""
    s = _spec(12.0, 10.0)
    s["footprint_x"], s["footprint_y"] = 12.0, 10.0      # the room IS the shell
    assert level_design.furnish(s) >= 0
    hx, hy = 6.0, 5.0
    for v in s["volumes"]:
        assert abs(abs(v["x"]) - hx) > level_design._FURNISH_EXT_KEEPOUT or                abs(abs(v["y"]) - hy) > level_design._FURNISH_EXT_KEEPOUT, v
