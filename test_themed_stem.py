"""The module-stem mirror: Deli Counter asks for the file Zoo built.

``themed_tscn.module_stem`` and ``zoo_keeper.core.kit.module_stem`` construct
the same filename from the same slot, and NEITHER PARSES. They agree only by
being kept identical, which no import enforces -- they are different repos.

So the seam is pinned by literals. Zoo's ``tests/test_openings.py`` asserts
these same six-character tags; either side drifting alone fails its own suite
rather than quietly resolving to a module that was never built. That failure
mode is not hypothetical: a plate depth collision and a stairwell collision
both shipped as "one file wins and one room gets the other's geometry".
"""

import themed_tscn


def _slot(role, dims, openings=None, voids=None, style=1):
    return {"slot_id": "s", "role": role, "size_mod": "full", "style": style,
            "fit": {"dims": dims, "pivot": "center",
                    "openings": openings or [], "voids": voids or []}}


DOOR = {"kind": "door", "width": 1.2, "height": 2.2, "sill": 0.0}
WINDOW = {"kind": "window", "width": 3.0, "height": 1.4, "sill": 0.8}


def test_the_opening_tag_matches_zoo_exactly():
    """The literals are the contract. Change one and change Zoo's too."""
    assert themed_tscn.opening_tag([DOOR]) == "97cfbf"
    assert themed_tscn.opening_tag([WINDOW]) == "ba672d"
    assert themed_tscn.opening_tag(
        [{"kind": "garage", "width": 3.2, "height": 2.6,
          "sill": 0.0}]) == "150910"
    assert themed_tscn.opening_tag([]) is None
    assert themed_tscn.opening_tag(None) is None


def test_the_stem_carries_the_opening_tag():
    assert themed_tscn.module_stem(
        "doorway", "rockay", 1, 120, None, None, None,
        "97cfbf") == "doorway_rockay_01_w120_o97cfbf"


def test_a_doorway_slot_resolves_to_the_tagged_stem():
    stem, scaled = themed_tscn.resolve_themed_stem(
        _slot("doorway", [1.2, 0.35, 3.7], [DOOR]), "rockay", 1)
    assert stem == "doorway_rockay_01_w120_o97cfbf"
    assert scaled is False


def test_two_doorways_of_one_width_and_different_apertures_differ():
    """The collision the tag exists for: both were `doorway_rockay_01_w140`,
    one file won, and one room got the other's hole."""
    a = [{"kind": "door", "width": 1.4, "height": 2.2, "sill": 0.0}]
    b = [{"kind": "door", "width": 1.4, "height": 2.4, "sill": 0.0}]
    sa, _ = themed_tscn.resolve_themed_stem(
        _slot("doorway", [1.4, 0.35, 3.7], a), "rockay", 1)
    sb, _ = themed_tscn.resolve_themed_stem(
        _slot("doorway", [1.4, 0.35, 3.7], b), "rockay", 1)
    assert sa != sb


def test_the_order_of_openings_is_kept():
    """Only the first aperture is cut, so a different order is a different
    module. (A plate's voids are a set and sort; these must not.)"""
    assert (themed_tscn.opening_tag([DOOR, WINDOW])
            != themed_tscn.opening_tag([WINDOW, DOOR]))


def test_wall_floor_and_ceiling_names_are_untouched():
    """A wall has no aperture, so no existing wall/plate filename moves."""
    stem, _ = themed_tscn.resolve_themed_stem(
        _slot("wall", [2.0, 0.35, 3.7]), "rockay", 1)
    assert stem == "wall_rockay_01_w200"
    stem, _ = themed_tscn.resolve_themed_stem(
        _slot("floor", [44.0, 24.0, 0.02]), "rockay", 1)
    assert stem == "floor_rockay_01_w4400_d2400"


def test_a_corner_slot_is_keyed_on_thickness_and_height():
    """The mirror of Zoo's `test_a_corner_is_keyed_on_every_axis_it_is_free_on`
    (roadmap 64): the same literal on both sides, or a corner resolves to a
    module that was never built."""
    stem, scaled = themed_tscn.resolve_themed_stem(
        _slot("wallCorner", [0.3, 0.3, 3.3]), "delco", 1)
    assert stem == "wallCorner_delco_01_w30_d30_h330" and scaled is False
    tall, _ = themed_tscn.resolve_themed_stem(
        _slot("wallCorner", [0.3, 0.3, 5.2]), "delco", 1)
    assert tall != stem


def test_a_wall_remainder_is_still_one_unit_module():
    slot = _slot("wall", [1.3, 0.35, 3.7])
    slot["size_mod"] = "end"
    stem, scaled = themed_tscn.resolve_themed_stem(slot, "rockay", 1)
    assert stem == "wallEnd_rockay_01" and scaled is True


# ---------------------------------------------------------------------------
# 0.131.0 -- a volume's DRESSING in its name (Zoo 0.84.0 `kit.DRESSING_FIELDS`)
# ---------------------------------------------------------------------------

import os      # noqa: E402
import sys     # noqa: E402

import pytest  # noqa: E402

ZOO = os.environ.get("DC_ZOO_ROOT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zoo")


def _zoo_kit():
    if not os.path.isdir(os.path.join(ZOO, "zoo_keeper")):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % ZOO)
    if ZOO not in sys.path:
        sys.path.insert(0, ZOO)
    import importlib
    return importlib.import_module("zoo_keeper.core.kit")


def _volume(dims, species, **dress):
    s = {"slot_id": "v", "role": "prop", "size_mod": "full", "style": 2,
         "species": species, "stock": None, "variant": 0, "form": None,
         "fit": {"dims": list(dims), "pivot": "center", "openings": []}}
    s.update(dress)
    return s


def test_the_dressing_suffixes_follow_the_height_and_unset_adds_nothing():
    """The literals are the contract, as for the opening tag: Zoo's own
    `module_stem` builds these names."""
    f = themed_tscn.module_stem
    assert f("prop", "delco_1997", 2, 160, None, 80, None, None, 75,
             species="desk", stock="office", variant=2) \
        == "prop_desk_delco_1997_02_w160_d80_h75_soffice_n2"
    assert f("prop", "delco_1997", 1, 60, None, 60, None, None, 240,
             species="furnace", form="water_heater") \
        == "prop_furnace_delco_1997_01_w60_d60_h240_fwater_heater"
    for unset in ({}, {"stock": "none"}, {"variant": 0}, {"stock": None,
                                                          "form": None}):
        assert f("prop", "delco_1997", 2, 160, None, 80, None, None, 75,
                 species="desk", **unset) == "prop_desk_delco_1997_02_w160_d80_h75"
    # the resolver clears "auto" and "none" before it builds the name
    stem, _ = themed_tscn.resolve_themed_stem(
        _volume((0.6, 0.6, 2.4), "furnace", form="auto", stock="none"),
        "delco_1997", 1)
    assert stem == "prop_furnace_delco_1997_02_w60_d60_h240"


def test_the_stem_is_zoo_s_for_every_field_combination():
    """DC's mirror against Zoo's function, argument for argument."""
    kit = _zoo_kit()
    cases = []
    for species in ("desk", "carton_stack", None):
        for form in (None, "", "auto", "sofa", "water_heater"):
            for stock in (None, "none", "office", "vault"):
                for variant in (None, 0, 1, 3):
                    cases.append(dict(species=species, form=form, stock=stock,
                                      variant=variant))
    materials = ((None,) if not hasattr(kit, "material_tag")
                 else (None, "leather"))          # 0.89.0: the `_m<kind>`
    for kw in cases:
        for state in (None, "open"):
            for material in materials:
                args = ("prop", "delco_1997", 2, 160, state, 80, None, None, 75)
                mk = dict(kw, material=material) if material else kw
                assert themed_tscn.module_stem(*args, **mk) == \
                    kit.module_stem(*args, **mk), mk


def test_the_resolver_names_the_module_zoo_plans_for_a_dressed_slot(tmp_path):
    """Through the whole chain: Zoo's `plan_kit` on a one-slot manifest names
    a module; with only that file in the library, DC's resolver lands on it.
    Covers a dressing Zoo honours, one it drops (a variant on a chair, stock
    on a carton stack), and a species that does not fit its slot."""
    kit = _zoo_kit()
    slots = [
        _volume((1.6, 0.8, 0.75), "desk", stock="office", variant=2),
        _volume((1.6, 0.8, 0.75), "desk"),
        _volume((0.6, 0.6, 2.4), "furnace", form="water_heater"),
        _volume((1.0, 0.9, 3.25), "furnace", form="furnace"),
        _volume((0.9, 0.6, 1.0), "carton_stack", variant=3),
        _volume((0.9, 0.6, 1.0), "carton_stack", stock="office", variant=1),
        _volume((0.5, 0.5, 0.9), "chair", variant=2),
        _volume((2.0, 0.9, 0.85), "booth_seat", form="sofa", variant=1),
        _volume((3.0, 0.8, 1.08), "counter", stock="bar", variant=3),
        _volume((9.0, 0.8, 1.08), "pool_table", variant=1),   # too long: the box
    ]
    for i, slot in enumerate(slots):
        plan = kit.plan_kit({"slots": [slot]}, theme="delco_1997", style=1)
        stems = [m["stem"] for m in plan["modules"]]
        assert len(stems) == 1, stems
        lib = tmp_path / str(i)
        lib.mkdir()
        (lib / (stems[0] + ".glb")).write_bytes(b"")
        got, _scaled, fell = themed_tscn.resolve_slot_ref(slot, "delco_1997",
                                                         1, str(lib))
        assert (got, fell) == (stems[0], False), (slot, stems[0], got)


def test_a_dressed_slot_falls_to_the_bare_species_then_to_the_box(tmp_path):
    lib = str(tmp_path)
    slot = _volume((1.6, 0.8, 0.75), "desk", stock="office", variant=2)
    assert themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)[0] is None
    open(os.path.join(lib, "prop_delco_02_w160_d80_h75.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)[0] \
        == "prop_delco_02_w160_d80_h75"
    open(os.path.join(lib, "prop_desk_delco_02_w160_d80_h75.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)[0] \
        == "prop_desk_delco_02_w160_d80_h75"
    open(os.path.join(lib, "prop_desk_delco_02_w160_d80_h75_soffice_n2.glb"),
         "w").close()
    assert themed_tscn.resolve_slot_ref(slot, "delco", 1, lib)[0] \
        == "prop_desk_delco_02_w160_d80_h75_soffice_n2"


def test_a_small_turn_survives_the_fit_and_a_wrong_quarter_does_not():
    """A chair turned 15 degrees off square: the composer used to try only
    the four cardinals and placed it square. The fit still owns the quarter."""
    chair = [0.5, 0.9, 0.5]                      # module extent x, y(up), z
    assert themed_tscn._fit_rotation(chair, [0.5, 0.9, 0.5], fallback=195.0) == 195.0
    assert themed_tscn._fit_rotation(chair, [0.5, 0.9, 0.5], fallback=180) == 180
    desk = [1.6, 0.75, 0.8]
    # a 1.6 x 0.8 desk whose greybox runs the other way cannot keep a turn
    # that leaves it across its own footprint
    assert themed_tscn._fit_rotation(desk, [0.8, 0.75, 1.6], fallback=12.0) in (90, 270)


# ---------------------------------------------------------------------------
# 0.132.0 -- the material in the name (Zoo 0.89.0). A leather sofa and a wood
# one were two geometries under one filename, and the later build overwrote
# the earlier; `_m<kind>` is written when the slot's material is a known kind
# that is not the species' own for the theme -- on every slot type.
# ---------------------------------------------------------------------------

def test_the_material_tag_sits_after_the_dressing_and_before_the_hashes():
    f = themed_tscn.module_stem
    assert f("prop", "delco_1997", 10, 200, None, 90, None, None, 85,
             species="booth_seat", form="sofa", variant=1, material="leather") \
        == "prop_booth_seat_delco_1997_10_w200_d90_h85_fsofa_n1_mleather"
    assert f("wall", "rockay", 3, 200, None, material="drywall") \
        == "wall_rockay_03_w200_mdrywall"
    assert f("vault_door", "delco_1997", 1, 360, "open", 30, None, "abc123",
             330, material="concrete") \
        == "vault_door_delco_1997_01_w360_d30_h330_mconcrete_oabc123_open"
    assert f("wall", "rockay", 3, 200, None, material=None) == "wall_rockay_03_w200"
    # only a KIND is a candidate tag: a spec id is not
    assert themed_tscn.stem_material({"material": "brick_ext"}) is None
    assert themed_tscn.stem_material({"material": "drywall"}) == "drywall"
    assert themed_tscn.stem_material({"material": None}) is None


def test_the_tagged_name_is_asked_first_and_the_plain_one_second(tmp_path):
    lib = str(tmp_path)
    wall = dict(_slot("wall", [2.0, 0.3, 3.3], style=3), material="drywall")
    assert themed_tscn.resolve_slot_ref(wall, "rockay", 3, lib)[0] is None
    open(os.path.join(lib, "wall_rockay_03_w200.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(wall, "rockay", 3, lib)[0] == "wall_rockay_03_w200"
    open(os.path.join(lib, "wall_rockay_03_w200_mdrywall.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(wall, "rockay", 3, lib)[0] \
        == "wall_rockay_03_w200_mdrywall"
    # a dressed volume: tagged-and-dressed, dressed, tagged-and-bare, bare,
    # then the box -- and the style-01 degrade applies to each in turn
    sofa = dict(_volume((2.0, 0.9, 0.85), "booth_seat", form="sofa", variant=1),
                material="leather", style=10)
    open(os.path.join(lib, "prop_delco_1997_10_w200_d90_h85.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(sofa, "delco_1997", 10, lib)[0] \
        == "prop_delco_1997_10_w200_d90_h85"
    open(os.path.join(lib, "prop_booth_seat_delco_1997_10_w200_d90_h85_fsofa_n1.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(sofa, "delco_1997", 10, lib)[0] \
        == "prop_booth_seat_delco_1997_10_w200_d90_h85_fsofa_n1"
    open(os.path.join(lib, "prop_booth_seat_delco_1997_10_w200_d90_h85_fsofa_n1_mleather.glb"), "w").close()
    assert themed_tscn.resolve_slot_ref(sofa, "delco_1997", 10, lib)[0] \
        == "prop_booth_seat_delco_1997_10_w200_d90_h85_fsofa_n1_mleather"
    # an interactive slot's states carry the material its base resolved with
    door = dict(_slot("vault_door", [3.6, 0.3, 3.3], openings=[
        {"kind": "vault", "width": 1.3, "height": 2.1, "sill": 0.0}]),
        material="concrete", interactive={
            "states": ["locked", "open"], "default": "locked",
            "state_geometry": {"locked": "vault_door", "open": "vault_door"}})
    base, _ = themed_tscn.resolve_themed_stem(door, "delco_1997", 1, material="concrete")
    open(os.path.join(lib, base + ".glb"), "w").close()
    variants = themed_tscn.state_variant_stems(door, "delco_1997", 1, lib)
    assert variants and all("_mconcrete_" in stem for _st, stem, _av in variants), variants
    assert all(stem.endswith("_open") for _st, stem, _av in variants)


def test_the_material_stem_matches_zoo_for_walls_a_vault_door_a_club_chair_and_a_sofa(tmp_path):
    """Through Zoo's own `plan_kit`, read only (DC_ZOO_ROOT): a wall whose
    material is not the theme's own, one whose material is, a vault door, a
    club chair whose `wood` is its frame and the species' own (no tag), a
    sofa in leather (the upholstery, and a tag), a wall naming a spec id
    (no tag). Skips against a Zoo without the contract."""
    kit = _zoo_kit()
    if not hasattr(kit, "material_tag"):
        pytest.skip("Zoo < 0.89.0: no material_tag")
    theme = "delco_1997"
    wall_own = kit.species_default_material("wall", theme)
    wall_mat = "drywall" if wall_own != "drywall" else "plaster"
    slots = [
        dict(_slot("wall", [2.0, 0.3, 3.3], style=3), material=wall_mat),
        dict(_slot("wall", [2.0, 0.3, 3.3], style=3), material=wall_own),
        dict(_slot("vault_door", [3.6, 0.3, 3.3], openings=[
            {"kind": "vault", "width": 1.3, "height": 2.1, "sill": 0.0}]),
             material="concrete"),
        dict(_volume((0.78, 0.75, 0.78), "club_chair"), material="wood"),
        dict(_volume((2.0, 0.9, 0.85), "booth_seat", form="sofa", variant=1),
             material="leather"),
        dict(_slot("wall", [2.0, 0.3, 3.3], style=3), material="brick_ext"),
        # an upholstery kind that is NOT the species' own: tagged
        dict(_volume((2.0, 0.9, 0.85), "booth_seat", form="sofa", variant=1),
             material="canvas"),
    ]
    for i, slot in enumerate(slots):
        plan = kit.plan_kit({"slots": [slot]}, theme=theme, style=1)
        stems = sorted({m["stem"] for m in plan["modules"]})
        lib = tmp_path / str(i)
        lib.mkdir()
        for s in stems:
            (lib / (s + ".glb")).write_bytes(b"")
        got, _scaled, fell = themed_tscn.resolve_slot_ref(slot, theme, 1, str(lib))
        assert got in stems and not fell, (slot.get("material"), stems, got)
        base = [s for s in stems if not s.endswith(("_unlocked", "_open", "_breached"))]
        assert got == base[0], (stems, got)
    # what was tagged: the wall in a foreign kind, the canvas sofa; not the
    # wall in the theme's own kind, the chair's own wood, or a spec id. The
    # leather sofa is tagged only if leather is not booth_seat's own for
    # the theme (delco_1997: it is, so no tag) -- asked of Zoo, not assumed.
    tagged = [kit.material_tag(s["material"], s.get("species") or s["role"], theme)
              for s in slots]
    own_sofa = kit.species_default_material("booth_seat", theme)
    assert tagged == [wall_mat, None, kit.material_tag("concrete", "vault_door", theme),
                      None, None if own_sofa == "leather" else "leather", None,
                      "canvas"], tagged
