"""
agent_contract.py  --  load the shared character/agent dimension contract
=========================================================================
agent_contract.json is the ONE place body sizes and their derived clearances
live (the body-metrics sibling of docs/COORDINATE_CONTRACT.md). Validators,
bake runners, and QA harnesses read it through this module; every consumer
keeps a hardcoded fallback equal to the ratified values, so a missing file
degrades gracefully instead of failing the pipeline.

Search order: $DC_AGENT_CONTRACT, then agent_contract.json beside this file.

    from agent_contract import contract, nav_env
    c = contract()
    c["nav_bake"]["agent_radius_m"]      # 0.4

`nav_env()` returns the contract's bake block as environment variables
(DC_NAV_RADIUS, DC_NAV_HEIGHT, DC_NAV_CLIMB, DC_NAV_SLOPE, DC_NAV_CELL,
DC_NAV_CELL_H, DC_QA_ARRIVE, DC_QA_STUCK, DC_QA_SNAP) -- the bridge into
GDScript gates, which read them via OS.get_environment with the same
fallbacks.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_cache = None

_DEFAULTS = {
    "characters": {"player": {"radius_m": 0.35, "height_m": 1.8,
                              "eye_height_m": 1.6, "max_step_up_m": 0.5,
                              "walk_speed_mps": 4.0}},
    "nav_bake": {"agent_radius_m": 0.4, "agent_height_m": 1.8,
                 "agent_max_climb_m": 0.5, "agent_max_slope_deg": 55.0,
                 "cell_size_m": 0.15, "cell_height_m": 0.15},
    "clearances": {"min_door_width_m": 1.25, "min_corridor_width_m": 1.1,
                   "min_headroom_m": 2.0},
    "qa": {"arrive_dist_m": 1.5, "stuck_seconds": 4.0, "snap_max_m": 2.0,
           "walker_capsule_radius_m": 0.35, "walker_capsule_height_m": 1.8},
    "review": {"character_reference_height_m": 1.8,
               "gameplay_camera_eye_m": 1.6},
}


def contract():
    """The parsed contract (cached), with defaults filled for missing keys."""
    global _cache
    if _cache is not None:
        return _cache
    path = os.environ.get("DC_AGENT_CONTRACT") or \
        os.path.join(HERE, "agent_contract.json")
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    merged = {}
    for section, defaults in _DEFAULTS.items():
        merged[section] = dict(defaults)
        merged[section].update(data.get(section, {}))
    _cache = merged
    return merged


def nav_env(base=None):
    """Environment dict carrying the bake/QA numbers into GDScript gates."""
    c = contract()
    env = dict(base if base is not None else os.environ)
    env.update({
        "DC_NAV_RADIUS": str(c["nav_bake"]["agent_radius_m"]),
        "DC_NAV_HEIGHT": str(c["nav_bake"]["agent_height_m"]),
        "DC_NAV_CLIMB": str(c["nav_bake"]["agent_max_climb_m"]),
        "DC_NAV_SLOPE": str(c["nav_bake"]["agent_max_slope_deg"]),
        "DC_NAV_CELL": str(c["nav_bake"]["cell_size_m"]),
        "DC_NAV_CELL_H": str(c["nav_bake"]["cell_height_m"]),
        "DC_QA_ARRIVE": str(c["qa"]["arrive_dist_m"]),
        "DC_QA_STUCK": str(c["qa"]["stuck_seconds"]),
        "DC_QA_SNAP": str(c["qa"]["snap_max_m"]),
    })
    return env


def min_door_width():
    return float(contract()["clearances"]["min_door_width_m"])


def min_corridor_width():
    return float(contract()["clearances"]["min_corridor_width_m"])
