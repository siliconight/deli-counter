"""A selling floor is tile and a working floor is concrete, whatever role routes it to carpet (0.271.0).

The walker, 2026-10-26: "far too dark in teh super market". The sales floor read luma p50 3 against the back stock's
77; it was carpeted maroon because `public_entry` maps to carpet (the factory's docs/findings/walk_2026-10-26_panel/,
L4). FAILS ON 0.270.0.
"""
import glob
import json
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import floors  # noqa: E402


def _room(rid, role, **kw):
    return SimpleNamespace(id=rid, role=role, **kw)


def _floor(room):
    return floors._material(room, "floor", floors.FLOOR_BY_ROLE, "concrete")


def test_the_supermarkets_sales_floor_is_tile():
    assert _floor(_room("sales_floor", "public_entry")) == "tile"


def test_stores_sell_on_tile_and_work_on_concrete():
    for rid in ("customer_floor", "shop_floor", "retail_floor", "stall_floor", "market_aisles"):
        assert _floor(_room(rid, "public_entry")) == "tile", rid
    for rid in ("stockroom_loading", "service_bay", "garage_bay", "deck_0_south", "dock_floor", "shed_floor",
                "lanes", "ground_works", "ground_pour"):
        assert _floor(_room(rid, "public_entry")) == "concrete", rid


def test_a_lobby_a_banking_hall_and_a_parlour_keep_their_carpet():
    for rid in ("lobby", "grand_lobby", "banking_hall", "parlor", "lounge", "waiting_room", "main_floor"):
        assert _floor(_room(rid, "public_entry")) == "carpet", rid


def test_only_a_carpet_is_reconsidered_and_a_rooms_own_floor_wins():
    assert _floor(_room("stockroom", "fortifiable")) == "concrete"          # the map's own answer
    assert _floor(_room("sales_floor", "route_node")) == "tile"             # the map's own answer
    assert _floor(_room("sales_floor", "public_entry", floor_material="wood")) == "wood"
    assert floors._material(_room("sales_floor", "public_entry"), "ceiling", floors.CEILING_BY_ROLE,
                            "concrete") == "ceiling_tile"                   # the ceiling is not touched


def test_no_selling_or_working_floor_in_the_library_is_carpeted():
    carpeted = []
    for path in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        try:
            spec = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in spec.get("rooms") or []:
            room = SimpleNamespace(id=r.get("id"), role=r.get("role"), floor_material=r.get("floor_material"),
                                   material=r.get("material"))
            if floors.floor_by_use(r.get("id")) and _floor(room) == "carpet":
                carpeted.append("%s/%s" % (os.path.basename(path), r.get("id")))
    assert carpeted == []
