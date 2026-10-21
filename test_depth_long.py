"""A species long in depth (0.245.0, the factory's roadmap 267): Zoo's `cargo_container` is 2.3-2.5 m wide and
2.9-13.8 m deep, and Deli Counter records every hinted volume long side first -- so the freight terminal's
containers, authored 6.0 x 2.4, were recorded 6.0 wide, failed the genome's width and built as plain boxes.
`prop_species.DEPTH_LONG` records such a species short side first, and `prop_species.recorded_turn` is the one
turn every reader of a module's front asks."""

import glob
import importlib
import json
import os
import sys
import types

import pytest

import prop_species

HERE = os.path.dirname(os.path.abspath(__file__))

#: Zoo 1.119.0's `cargo_container` genome, (min, max) metres: width, depth, height.
CARGO_RANGES = ((2.3, 2.5), (2.9, 13.8), (2.4, 2.95))


def _library():
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            yield os.path.basename(path)[:-5], json.load(fh)


def test_container_routes_to_the_cargo_container_long_in_depth():
    """FAILS ON 0.244.0: `container` routes to None and `long_axis_first` takes no species."""
    f = prop_species.species_for_name
    assert f("container_0") == "cargo_container"
    assert f("cargo_cover") is None                    # 4.0 x 4.0 x 2.0 of wooden cargo, not a container
    assert "cargo_container" in prop_species.DEPTH_LONG
    # long in x: recorded short side first and turned; long in y: as it stands
    assert prop_species.long_axis_first((6.0, 2.4, 2.6), "cargo_container") == ([2.4, 6.0, 2.6], 90.0)
    assert prop_species.long_axis_first((2.4, 6.0, 2.6), "cargo_container") == ([2.4, 6.0, 2.6], 0.0)
    # every other species, and none named, keeps the long-side-first rule
    assert prop_species.long_axis_first((6.0, 2.4, 2.6)) == ([6.0, 2.4, 2.6], 0.0)
    assert prop_species.long_axis_first((2.4, 6.0, 2.6)) == ([6.0, 2.4, 2.6], 90.0)
    assert prop_species.long_axis_first((2.4, 6.0, 2.6), "desk") == ([6.0, 2.4, 2.6], 90.0)


def test_the_word_claims_exactly_the_freight_terminals_four_containers():
    """Every library volume routed to the species, measured: the four `container` volumes, written in the species'
    own kind -- `metal_painted`, the genome's default and every style's, so Zoo's stem carries no `_m` -- and each,
    recorded as the emitter records it, inside the genome. FAILS ON 0.244.0: none is routed."""
    hits = []
    for spec_id, spec in _library():
        for v in spec.get("volumes") or []:
            if prop_species.species_for_name(v.get("name") or "") == "cargo_container":
                dims, rot = prop_species.long_axis_first((v["size_x"], v["size_y"], v["size_z"]), "cargo_container")
                hits.append((spec_id, v["name"], v.get("material"), dims, rot))
    assert [(h[0], h[1], h[2]) for h in hits] == [("freight_terminal_a01", "container_%d" % k, "metal_painted")
                                                  for k in range(4)], hits
    for _spec, _name, _mat, dims, rot in hits:
        assert all(lo <= x <= hi for x, (lo, hi) in zip(dims, CARGO_RANGES)), dims
        assert (dims, rot) == ([2.4, 6.0, 2.6], 90.0)


def test_depth_long_is_every_routed_species_long_in_depth_and_nothing_else():
    """The set is held to Zoo's genomes, not chosen: a routed species belongs in it exactly when its whole depth
    range lies above its whole width range, so no slot recorded long side first could ever fit it."""
    root = os.environ.get("DC_ZOO_ROOT") or os.path.join(HERE, "..", "zoo")
    genomes = os.path.join(root, "zoo_keeper", "genome", "species")
    if not os.path.isdir(genomes):
        pytest.skip("no Zoo genomes beside this repo (set DC_ZOO_ROOT)")
    routed = {sp for _words, sp in prop_species.PROP_SPECIES if sp is not None}
    assert prop_species.DEPTH_LONG <= routed, prop_species.DEPTH_LONG - routed
    shaped = set()
    for sp in sorted(routed):
        with open(os.path.join(genomes, sp + ".json"), encoding="utf-8") as fh:
            dims = json.load(fh).get("dimensions") or {}
        w, d = dims.get("width"), dims.get("depth")
        if w and d and float(d["min"]) > float(w["max"]):
            shaped.add(sp)
    assert shaped == set(prop_species.DEPTH_LONG), (shaped, prop_species.DEPTH_LONG)


@pytest.fixture
def dc(monkeypatch):
    """deli_counter against stub bpy/bmesh, as test_prop_species does."""
    for name in ("bpy", "bmesh"):
        try:
            importlib.import_module(name)
        except ImportError:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delitem(sys.modules, "deli_counter", raising=False)
    mod = importlib.import_module("deli_counter")
    yield mod
    sys.modules.pop("deli_counter", None)


def test_a_container_slot_is_recorded_short_side_first_and_keeps_its_box(dc):
    """The slot Zoo plans from: 2.4 wide, 6.0 deep, turned 90 onto the volume's long x. The container is cover, a
    solid the size of its slot, so the greybox keeps its collider (`SPECIES_OWNS_COLLISION` does not hold it).
    FAILS ON 0.244.0: dims 6.0 x 2.4, rot 0, no species."""
    import skin_style
    from spec_loader import spec_from_dict
    d = {"name": "yard", "footprint_x": 30, "footprint_y": 20, "n_stories": 1,
         "materials": [{"id": "concrete"}, {"id": "metal_painted"}],
         "volumes": [{"name": "container_0", "x": 0, "y": 0, "z": 1.3, "size_x": 6.0, "size_y": 2.4,
                      "size_z": 2.6, "material": "metal_painted"},
                     {"name": "container_1", "x": 8, "y": 0, "z": 1.3, "size_x": 2.4, "size_y": 6.0,
                      "size_z": 2.6, "material": "metal_painted"}]}
    spec = spec_from_dict(d)
    b = dc._Builder(spec)
    b.slots = []
    b._mat_style = skin_style.material_styles([m.id for m in spec.materials])
    cols = []
    b._box = lambda *a, **k: None
    b._col_box = lambda name, *a, **k: cols.append(name)
    b._record_surface = lambda *a, **k: None
    b._volumes()
    got = {s["slot_id"]: (s["species"], s["fit"]["dims"], s["transform"]["rot_y"], s["fit"]["collision"])
           for s in b.slots}
    assert got == {"container_0": ("cargo_container", [2.4, 6.0, 2.6], 90.0, "convex"),
                   "container_1": ("cargo_container", [2.4, 6.0, 2.6], 0.0, "convex")}, got
    assert cols == ["container_0_col", "container_1_col"], cols


def test_every_front_reader_asks_the_emitters_turn():
    """`level_design._front_turn` and `lights._front_bearing` each spelled the long-side-first rule out for themselves
    until 0.245.0; now both ask `prop_species.recorded_turn`. A depth-long piece long in x is turned 90, so its front
    points at 90 + rot_z + 180. And for every other volume in the library the turn is the rule they spelled, so
    nothing they placed before moves. FAILS ON 0.244.0: `recorded_turn` does not exist, and `_front_turn` read the
    container as unturned."""
    import level_design
    import lights
    assert prop_species.recorded_turn("container_0", 6.0, 2.4) == 90.0
    assert prop_species.recorded_turn("container_0", 2.4, 6.0) == 0.0
    assert prop_species.recorded_turn("crate_stack", 1.0, 3.0) == 0.0           # unhinted: never turned
    assert level_design._front_turn("container_0", 6.0, 2.4, 0.0) == 90.0       # 0 + 180 - 90
    assert lights._front_bearing({"name": "container_0", "size_x": 6.0, "size_y": 2.4}) == 270.0
    for _spec_id, spec in _library():
        for v in spec.get("volumes") or []:
            name, sx, sy = v.get("name") or "", float(v["size_x"]), float(v["size_y"])
            species = prop_species.species_for_name(name)
            if species in prop_species.DEPTH_LONG:
                continue
            spelled = 90.0 if (species is not None and sy > sx + 1e-9) else 0.0
            assert prop_species.recorded_turn(name, sx, sy) == spelled, (name, sx, sy)
