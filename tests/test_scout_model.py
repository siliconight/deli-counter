"""The scout model: the scout view's signals as a model a player turns all the way round (0.259.0, the factory's
roadmap 295).

The walker, of the scout view: "make it look more polished and artistic so it could ship to players....They can scout
out the buildings and rotate the schemas in a 360 degree way". `scout_model.build_glb` builds a GLB, one mesh a
storey, one material, colour in the vertex data.

THE TEST THAT MATTERS IS `test_the_model_and_the_scout_drawing_agree_on_every_door_and_window`: the model reads the
layout the drawings read, and a player must not find a door in one that the other does not have.
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import axonometric as AX  # noqa: E402
import floorplan as FP  # noqa: E402
import scout_model as SM  # noqa: E402
import spec_loader  # noqa: E402

NAMES = ("deli_a03", "office", "pharmacy_a01")


def _load(name):
    return spec_loader.load_spec(os.path.join(HERE, "specs", name + ".json"))


def _gltf(data):
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    jlen, jtype = struct.unpack_from("<II", data, 12)
    assert jtype == 0x4E4F534A
    blen, btype = struct.unpack_from("<II", data, 20 + jlen)
    assert btype == 0x004E4942 and 28 + jlen + blen == len(data)
    return json.loads(data[20:20 + jlen])


def test_a_node_and_a_mesh_a_storey_at_its_true_elevation_with_one_material():
    for name in NAMES:
        spec = _load(name)
        g = _gltf(SM.build_glb(spec))
        sh = FP._story_height(spec)
        stories = FP.stories_in(spec)
        floors = [n for n in g["nodes"] if not n["extras"].get("points")]
        assert [n["extras"]["storey"] for n in floors] == stories, name
        for n in floors:
            assert abs(n["translation"][1] - n["extras"]["storey"] * sh) < 1e-6, (name, n["name"])
        # a mesh a storey, and one more on each storey with points of interest (0.260.0)
        with_points = len({p["storey"] for p in g["scenes"][0]["extras"]["points"]})
        assert len(g["materials"]) == 1 and len(g["meshes"]) == len(stories) + with_points, name
        for m in g["meshes"]:
            (prim,) = m["primitives"]
            col = g["accessors"][prim["attributes"]["COLOR_0"]]
            assert (col["componentType"], col["type"], col.get("normalized")) == (5121, "VEC4", True), name


def _openings_by_storey_in_the_drawing(spec):
    """{storey: (doors, windows)} as the scout drawing draws them: a door's threshold line, a window's glass box."""
    svg = AX.render_axonometric(spec, scout=True)
    heads = list(re.finditer(r'<g id="storey_[^"]+" data-storey="(-?\d+)"', svg))
    ends = [h.start() for h in heads[1:]] + [svg.index('<g id="connections">')]
    out = {}
    for h, e in zip(heads, ends):
        part = svg[h.end():e]
        doors = len(re.findall(r'<line [^>]*data-opening=', part))
        windows = len(re.findall(r'<g data-opening=', part))
        out[int(h.group(1))] = (doors, windows)
    return out


def _openings_by_storey_in_the_model(spec):
    """{storey: (doors, windows)} counted off the model's own boxes: a door strip's top in the door or entry colour,
    a window's top in the glass colour."""
    pal = SM.PALETTES[SM.DEFAULT_PALETTE]

    def rgba(c):
        return tuple(int(round(SM._linear(v) * 255)) for v in c) + (255,)
    door, entry, glass = rgba(pal["door"]), rgba(pal["entry"]), rgba(pal["glass"])
    out = {}
    for s, m in SM._storeys(spec, pal).items():
        ups = [m.col[i] for i in range(0, len(m.pos), 4) if m.nrm[i] == (0.0, 1.0, 0.0)]
        out[s] = (sum(1 for c in ups if c in (door, entry)), sum(1 for c in ups if c == glass))
    return out


def test_the_model_and_the_scout_drawing_agree_on_every_door_and_window():
    seen = 0
    for name in NAMES + ("bank_branch_a02", "apartment_walkup_a01"):
        spec = _load(name)
        drawn, built = _openings_by_storey_in_the_drawing(spec), _openings_by_storey_in_the_model(spec)
        assert drawn == built, (name, drawn, built)
        seen += sum(d + w for d, w in drawn.values())
    assert seen > 40, seen    # the control: there are openings to agree about


def test_every_role_a_player_reads_has_its_own_colour():
    """A door in from outside, a hole in a floor, a stair, a ladder, a window and an inside door each read by colour,
    so no two may share one in any palette (the first draft gave the hole's rim the entry's red)."""
    for name, pal in SM.PALETTES.items():
        cols = [pal[r] for r in SM.ROLES_READ]
        assert len(set(cols)) == len(cols), name
        assert set(SM.PALETTES[name]) == set(SM.PALETTES[SM.DEFAULT_PALETTE]), name


def test_the_score_and_every_prop_of_interest_is_in_the_model():
    """The walker: "buildings should show the 'score' location and key props of interest". Every objective marker
    is a score beacon on its storey, every safe, ATM, loot and camera marker a point; the scene names each one, and
    each storey's points are a node of their own under it."""
    seen = {}
    for name in NAMES + ("bank_branch_a02", "apartment_walkup_a01"):
        spec = _load(name)
        want = [(m.type, FP._marker_story(spec, m)) for m in spec.markers
                if m.type in ("objective", "loot", "camera_socket")]
        want += [(v.name.split("_")[0], None) for v in spec.volumes
                 if v.name.split("_")[0] in ("safe", "atm") and getattr(v, "visual", True)]
        g = _gltf(SM.build_glb(spec))
        pts = g["scenes"][0]["extras"]["points"]
        assert len(pts) == len(want), (name, len(pts), len(want))
        scores = [p for p in pts if p["label"] == "SCORE"]
        assert len(scores) == sum(1 for t, _s in want if t == "objective"), name
        for (t, s), p in zip([w for w in want if w[1] is not None], pts):
            assert p["storey"] == s, (name, t, p)
        kids = {n["name"]: n for n in g["nodes"]}
        for s in {p["storey"] for p in pts}:
            parent = kids["storey_%d" % s]
            assert [g["nodes"][c]["name"] for c in parent["children"]] == ["storey_%d_points" % s], name
        for p in pts:
            seen[p["label"]] = seen.get(p["label"], 0) + 1
    assert seen.get("SCORE", 0) >= 5 and seen.get("SAFE", 0) >= 3, seen    # the control: there is something to show


def test_doors_in_from_outside_wear_the_entry_colour():
    """deli_a03 is entered from the street: its ground floor has doors in its exterior walls, and they, and only they,
    wear the entry colour."""
    spec = _load("deli_a03")
    pal = SM.PALETTES[SM.DEFAULT_PALETTE]
    entry = tuple(int(round(SM._linear(v) * 255)) for v in pal["entry"]) + (255,)
    tops = {s: [m.col[i] for i in range(0, len(m.pos), 4) if m.nrm[i] == (0.0, 1.0, 0.0)]
            for s, m in SM._storeys(spec, pal).items()}
    exterior_doors = 0
    for wall in FP.storey_walls(spec, 0):
        if str(wall["name"]).startswith("ext"):
            exterior_doors += sum(1 for op in wall["openings"] if float(op.resolved().get("sill") or 0.0) < 1e-6)
    assert exterior_doors > 0
    assert tops[0].count(entry) == exterior_doors


def test_the_model_is_deterministic_and_every_library_building_builds():
    """Every building with an inside builds; the largest is a REGRESSION DETECTOR, not a frame cost (CLAUDE.md: draw
    calls are the budget) -- a model that silently doubles trips it. Measured 2026-10-22: 132 buildings, the largest
    cbp_town_finale_midbalanced at 5,628 triangles."""
    import glob
    worst = 0
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(path).startswith("lf_"):
            continue
        spec = spec_loader.load_spec(path)
        if getattr(spec, "facade", False):
            continue
        worst = max(worst, sum(SM.model_stats(spec).values()))
    assert 0 < worst <= 8000, worst
    spec = _load("office")
    assert SM.build_glb(spec) == SM.build_glb(spec)
    assert set(SM.PALETTES) >= {SM.DEFAULT_PALETTE}
