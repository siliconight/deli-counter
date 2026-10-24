"""An indoor litter bin stands against a wall (0.266.0). The walker, walking cold run 9386, of deli_a03's bin alone at
an aisle's end: "garbage cans are usually up against walls inside buildings" (the factory's
docs/findings/walk_2026-10-23_9386/, finding 8).

`furnish` draws a bin as it always has and `stand_bins_on_walls`, its last step, stands each against a wall of its
room -- so a bin is judged where it ends, by the arrangement census's own reason.
"""
import glob
import json
import os

import arrangement
import level_design

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bins_by_reason(spec):
    """``[(name, reason)]`` for every bin furnish stood in one spec."""
    rooms = {r["id"]: r for r in spec.get("rooms") or [] if r.get("bounds")}
    out = []
    for rid, ps in arrangement.standing(spec).items():
        if rid not in rooms:
            continue
        for v, why in arrangement.reasons(rooms[rid], ps):
            if arrangement.stem(v["name"], rid) == "litter_bin" and arrangement.producer(v, rooms[rid]) == "furnish":
                out.append((v["name"], why))
    return out


def _library():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        name = os.path.basename(p)[:-len(".json")]
        if name.startswith("lf_"):
            continue
        spec = json.load(open(p, encoding="utf-8"))
        if isinstance(spec, dict) and spec.get("rooms"):
            yield name, spec


def test_every_furnished_bin_in_the_library_stands_against_a_wall():
    """Every bin furnish stood in the library's own specs reads `wall` to the arrangement census: its footprint within
    `arrangement.WALL_REACH` of its room's edge."""
    seen, off = 0, []
    for name, spec in _library():
        for bname, why in _bins_by_reason(spec):
            seen += 1
            if why != "wall":
                off.append((name, bname, why))
    assert seen, "no furnished litter bin in the library: the census found nothing to judge"
    assert not off, (len(off), off[:10])


def test_the_library_is_a_fixed_point_of_the_bin_pass():
    moved = [(name, level_design.stand_bins_on_walls(spec)) for name, spec in _library()]
    assert not [m for m in moved if m[1] != (0, 0)], [m for m in moved if m[1] != (0, 0)][:10]


def test_a_furnished_room_stands_its_bins_on_its_walls_and_moves_nothing_else():
    """furnish with the bin pass, against the same furnish with the pass set aside: every bin it keeps reads `wall`,
    and every other volume stands exactly where it stood."""
    import presets
    # presets whose builds draw bins at seed 0 (measured on 0.266.0: corner_deli 9, bank 2)
    keys = [k for k in ("corner_deli", "bank") if k in presets.REGISTRY]
    assert keys == ["corner_deli", "bank"], sorted(presets.REGISTRY)[:20]
    for key in keys:
        with_pass = presets.make(key, name="bins_%s" % key, seed=0)
        with_pass = with_pass if isinstance(with_pass, dict) else with_pass.to_dict()
        real = level_design.stand_bins_on_walls
        level_design.stand_bins_on_walls = lambda spec, routes_of=None: (0, 0)
        try:
            without = presets.make(key, name="bins_%s" % key, seed=0)
            without = without if isinstance(without, dict) else without.to_dict()
        finally:
            level_design.stand_bins_on_walls = real
        bins = _bins_by_reason(with_pass)
        assert bins and all(why == "wall" for _n, why in bins), (key, bins)
        rest = lambda s: sorted((v["name"], v.get("x"), v.get("y"), v.get("z")) for v in s["volumes"]
                                if not v["name"].startswith("litter_bin_"))
        assert rest(with_pass) == rest(without), key


def test_a_bin_with_no_clear_wall_goes():
    """A room whose walls are all taken keeps no bin in the middle of its floor."""
    spec = {"footprint_x": 6.0, "footprint_y": 6.0, "story_height": 3.0, "wall_thick": 0.3,
            "rooms": [{"id": "box", "story": 0, "bounds": [-3.0, -3.0, 3.0, 3.0]}],
            "volumes": [], "partitions": []}
    tag = level_design._room_tag(spec["rooms"][0])
    spec["volumes"].append({"name": "litter_bin_%s_1" % tag, "x": 0.0, "y": 0.0, "z": 0.5,
                            "size_x": 0.6, "size_y": 0.6, "size_z": 1.0})
    # a ring of tall pieces 0.9 m from nothing: every wall spot is within 0.9 m of one
    for i in range(-3, 4):
        for x, y in ((i * 0.9, -2.5), (i * 0.9, 2.5), (-2.5, i * 0.9), (2.5, i * 0.9)):
            spec["volumes"].append({"name": "post_%d_%d" % (round(x * 10), round(y * 10)), "x": x, "y": y,
                                    "z": 0.5, "size_x": 0.3, "size_y": 0.3, "size_z": 1.0})
    room = spec["rooms"][0]
    spots = level_design._bin_wall_spots(spec, room, 0.6, 0.6)
    assert spots, "the test room has no wall spot at all, so it would not test the posts"
    moved, removed = level_design.stand_bins_on_walls(spec)
    assert (moved, removed) == (0, 1)
    assert not [v for v in spec["volumes"] if v["name"].startswith("litter_bin_")]
