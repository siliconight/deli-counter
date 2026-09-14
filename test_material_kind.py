"""A slot must name a material KIND the art pass can resolve.

The spec library names its surfaces the way a builder does -- `brick_ext`,
`stone_ext`, `storefront_glass` -- and the skin resolver knows a fixed
vocabulary of kinds. Measured 2026-09-13 over all 281 specs: 25 distinct
material ids across 6,716 surface references, 16 of them outside that
vocabulary, 326 references in all. `find_pack` returns None for an unknown
kind and the material factory falls back to a FLAT colour, so the 131
surfaces that say `brick_ext` were exactly the ones that never got brick.

These tests keep the map honest in both directions: no target this repo
invented, and no spec material left out.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import material_kind   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(HERE, "specs")


def _spec_material_ids():
    """Every material id that can reach a slot: the library's own, plus the
    finishes the BUILDER appends.

    `floors.FINISH_PALETTE` is added to every spec's palette by the loader so
    a room role can name its floor and ceiling, and two of its seven ids
    (`ceiling_tile`, `plaster`) appear in no spec file. Scanning `specs/`
    alone missed them, and the first twin build printed 8 slots naming a
    material with no kind. A test that reads only what is authored cannot
    see what is generated."""
    import floors
    ids = {m["id"] for m in floors.FINISH_PALETTE}
    for path in glob.glob(os.path.join(SPECS, "*.json")):
        try:
            spec = json.load(open(path, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if spec.get("default_material"):
            ids.add(spec["default_material"])
        for m in spec.get("materials") or []:
            if m.get("id"):
                ids.add(m["id"])
        for coll in ("ext_walls", "partitions", "volumes"):
            for item in spec.get(coll) or []:
                if item.get("material"):
                    ids.add(item["material"])
                for op in item.get("openings") or []:
                    if op.get("material"):
                        ids.add(op["material"])
        # a room's own finishes reach the floor and ceiling slots (0.132.0:
        # the strip clubs' `carpet_club`)
        for r in spec.get("rooms") or []:
            for k in ("material", "floor_material", "ceiling_material"):
                if r.get(k):
                    ids.add(r[k])
    return ids


def test_every_target_is_a_kind_the_resolver_knows():
    """A kind invented here resolves to no pack and renders flat -- which is
    the exact defect this module exists to remove, reintroduced silently."""
    bad = {m: k for m, k in material_kind.KIND_BY_MATERIAL.items()
           if k not in material_kind.SKIN_KINDS}
    assert not bad, f"targets outside SKIN_KINDS: {bad}"


def test_every_spec_material_has_a_kind():
    """A new spec naming a new surface fails here rather than shipping a grey
    wall that looks like a styling decision."""
    missing = material_kind.unmapped(_spec_material_ids())
    assert not missing, (
        "these spec materials have no skin kind; add them to "
        f"material_kind.KIND_BY_MATERIAL: {missing}")


def test_the_kinds_are_zoo_s_when_zoo_is_beside_this_repo():
    """`SKIN_KINDS` is a literal copy of `zoo_keeper.core.skins.KNOWN_KINDS`.
    Every kind here must be one Zoo knows; the four club kinds Pixelcoat
    0.42.0 draws are being added to Zoo beside this release, so until they
    land there they are reported, not failed."""
    import pytest
    zoo = os.environ.get("DC_ZOO_ROOT") or os.path.join(
        os.path.dirname(HERE), "zoo")
    skins = os.path.join(zoo, "zoo_keeper", "core", "skins.py")
    if not os.path.exists(skins):
        pytest.skip("zoo repo not found at %s (set DC_ZOO_ROOT)" % zoo)
    if zoo not in sys.path:
        sys.path.insert(0, zoo)
    from zoo_keeper.core import skins as zk
    # Zoo 0.89.0's additions, pending until DC's neighbour is that version
    pending = {"carpet_club", "wallpaper_club", "wood_stained", "paint_block",
               "cloth"}
    ours = set(material_kind.SKIN_KINDS)
    missing_here = set(zk.KNOWN_KINDS) - ours
    assert not missing_here, f"Zoo knows kinds this copy lacks: {sorted(missing_here)}"
    invented = ours - set(zk.KNOWN_KINDS) - pending
    assert not invented, f"kinds Zoo does not know: {sorted(invented)}"
    still = pending - set(zk.KNOWN_KINDS)
    if still:
        print(f"club kinds not yet in Zoo's KNOWN_KINDS: {sorted(still)}")


def test_the_masonry_the_library_tried_hardest_to_name_resolves():
    assert material_kind.kind_for("brick_ext") == "brick"
    assert material_kind.kind_for("stone_ext") == "stone"
    assert material_kind.kind_for("poured_concrete") == "concrete"


def test_an_unmapped_id_is_not_guessed_at():
    assert material_kind.kind_for("unobtanium") is None
    assert material_kind.kind_for("unobtanium", "concrete") == "concrete"
    assert material_kind.kind_for(None) is None
    assert material_kind.unmapped(["brick_ext", "unobtanium", None]) == ["unobtanium"]


def test_the_library_still_needs_this(capsys):
    """The measurement that justified the module, re-taken each run so the
    claim in its docstring cannot rot."""
    ids = _spec_material_ids()
    kinds = set(material_kind.SKIN_KINDS)
    renamed = sorted(i for i in ids if i not in kinds)
    assert len(ids) >= 20, f"only {len(ids)} material ids found; check the glob"
    assert renamed, "no spec material needs mapping any more -- retire this map"
    print(f"{len(renamed)} of {len(ids)} spec materials are not skin kinds: "
          f"{renamed}")
