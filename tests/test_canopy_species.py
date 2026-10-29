"""A filling station's canopy is built by its species (0.293.0, Zoo 1.149.0, the factory's roadmap 324).

The box row's `canopy` and `col_` held every authored `canopy_roof` and `canopy_col` to a greybox box -- the forecourt's
landmark a grey slab on grey posts. They route to Zoo's `fuel_canopy` and `canopy_column`, ahead of that row.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import prop_species as P  # noqa: E402


def test_the_canopy_routes_to_its_species():
    """FAILS ON 0.292.0: both were None, a box."""
    assert P.species_for_name("canopy_roof") == "fuel_canopy"
    assert P.species_for_name("canopy_col_4") == "canopy_column"
    assert P.material_for("fuel_canopy", "canopy_steel") == "metal_painted"
    assert P.material_for("canopy_column", "metal") == "metal_painted"


def test_no_other_authored_name_is_claimed():
    """Every authored name the two rows now route is a canopy's: the rows steal nothing from the box row below."""
    routed = set()
    for f in glob.glob(os.path.join(HERE, "specs", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for v in (d.get("volumes") or []) + (d.get("placements") or []):
            n = v.get("name", "")
            if P.species_for_name(n) in ("fuel_canopy", "canopy_column"):
                routed.add(n.rstrip("0123456789_"))
    assert routed <= {"canopy_roof", "canopy_col"}, routed
