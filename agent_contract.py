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
                              "eye_height_m": 1.6, "chest_height_m": 1.0,
                              "max_step_up_m": 0.5,
                              "walk_speed_mps": 4.0}},
    # THESE MUST EQUAL agent_contract.json, and twice they did not.
    # `agent_max_climb_m` stood at 0.5 and `cell_size_m` at 0.15 -- the two
    # values the contract's own `*_derivation` notes record as REFUTED, with
    # measurements: 0.5 permitted a 0.49 m stringer that four walkers parked
    # against, and 0.15 capped the connected slope at 45 deg against a stated
    # 55, which failed eight path proofs as disjoint islands. `nav_gate.gd`'s
    # fallbacks were corrected when those values moved; this copy was not, and
    # it is the copy that WINS -- a missing contract makes `nav_env` export
    # DC_NAV_CLIMB and DC_NAV_CELL, and a present environment variable
    # overrides the correct GDScript fallback behind it. Degrading to a number
    # that was measured to disconnect the navmesh is not degrading gracefully.
    # `test_agent_contract.py` now asserts this block against the file.
    "nav_bake": {"agent_radius_m": 0.4, "agent_height_m": 1.8,
                 "agent_max_climb_m": 0.15, "agent_max_slope_deg": 55.0,
                 "cell_size_m": 0.1, "cell_height_m": 0.15},
    "clearances": {"min_door_width_m": 1.25, "min_corridor_width_m": 1.1,
                   "min_headroom_m": 2.0},
    # Read `sightlines.derivation` before touching these. They are the
    # firefight's geometry, not a body's, and they are measured off Laser Tag
    # rather than chosen here.
    #
    # `cover_break_height_m` is deliberately ABSENT. The contract stores it
    # so a reader of the file can see the answer without doing the algebra,
    # but a copy here would be merged into every contract that omits it --
    # so a studio setting its own sight heights would inherit OUR crossing,
    # and `cover_break_height` would then refuse its own correct derivation
    # for disagreeing with a number the studio never wrote. The three heights
    # are the contract; the fourth is a result.
    "sightlines": {"crew_sight_height_m": 1.6, "enemy_sight_height_m": 1.6,
                   "aim_height_m": 1.0},
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


def chest_height():
    """Where a shot is aimed on a body, in metres above its feet.

    A PROPERTY OF THE TARGET, not a constant, and that is the whole of why
    this function exists. `sightlines.aim_height_m` was settable and derived
    from nothing: 1.0 m is where a 1.8 m body's chest is, so a studio that
    stated a 2.05 m character got an eye height that followed and an aim
    point that stayed put.

    The band is not a matter of taste. A line-of-sight ray is cast AT this
    height and LOS is granted only when it hits the target body first, so an
    aim point outside the target's own capsule misses and every sightline on
    the map reads blocked. Inside the cylindrical section --
    ``radius <= chest <= height - radius`` -- the ray meets the full width;
    above it the ray grazes a hemisphere, and at the apex it misses. A 1.0 m
    character aimed at a fixed 1.0 m is aimed at the top of its own head.

    So the constraint is CHECKED rather than documented. A contract that puts
    the aim point outside its own body would produce a run in which nothing
    ever sees anything, and a report full of zeroes reads like a map problem.
    """
    player = contract()["characters"]["player"]
    chest = float(player["chest_height_m"])
    radius = float(player["radius_m"])
    height = float(player["height_m"])
    if not (radius <= chest <= height - radius):
        raise ValueError(
            "characters.player.chest_height_m %.3f is outside the body's own "
            "capsule (%.3f to %.3f for radius %.3f, height %.3f) -- a "
            "line-of-sight ray aimed there misses the target and every "
            "sightline reads blocked" % (chest, radius, height - radius,
                                         radius, height))
    return chest


def shelter_height():
    """The shortest solid that breaks a mutual sightline ANYWHERE along it.

    `cover_break_height` is the other end of the same question and answers a
    narrower one: the shortest solid that works AT ALL. At exactly that height
    there is one position on the line where it works and nowhere else, so a
    producer building to it has to land a crate within centimetres of a
    computed point -- and the first constraint that vetoes the position takes
    the whole sightline with it.

    A solid as tall as the taller EYE works from any position on the line,
    because the requirement along the line is
    ``max(a + (c - a)t, c + (b - c)t)`` and that is largest at the ends, where
    it equals each side's own eye. So this is a derivation and not a margin:
    below it the workable interval shrinks to a point, at it the whole line is
    available, and above it nothing further is bought.

    Measured on the shipped contract, 1.6 / 1.6 / 1.0::

        h=1.30  ->  t in [0.50, 0.50]   width 0.00   the crossing
        h=1.40  ->  t in [0.33, 0.67]   width 0.33
        h=1.50  ->  t in [0.17, 0.83]   width 0.67
        h=1.60  ->  t in [0.00, 1.00]   width 1.00   this
    """
    s = contract()["sightlines"]
    return max(float(s["crew_sight_height_m"]),
               float(s["enemy_sight_height_m"]))


def cover_break_height():
    """The shortest solid that stops BOTH sides of a firefight seeing each other.

    Below this a solid is scenery: one side keeps a free shot, and Laser Tag
    stamps first contact on the first shot by *either*, so the clock starts
    exactly where it would have. Derived in the contract from the two sight
    heights and the shared aim height rather than chosen -- and it is a
    STANDING number, because nothing in this toolchain crouches.

    Recomputed here rather than trusted, for the reason the contract's other
    derivations are: a stored value and a formula are two spellings of one
    quantity, and the file is edited by hand. A stored figure that disagrees
    with its own inputs by more than a millimetre is the finding, so it
    raises rather than being quietly preferred.
    """
    s = contract()["sightlines"]
    a = float(s["crew_sight_height_m"])
    b = float(s["enemy_sight_height_m"])
    # THE BODY'S, not this block's. `aim_height_m` is carried in `sightlines`
    # too, because the crossing needs all three numbers in one place -- but a
    # value carried twice is a value that rots, so the body decides and the
    # copy is checked against it.
    c = chest_height()
    stored_aim = s.get("aim_height_m")
    if stored_aim is not None and abs(float(stored_aim) - c) > 1e-6:
        raise ValueError(
            "sightlines.aim_height_m is %s and characters.player."
            "chest_height_m is %.3f -- one body, one aim point"
            % (stored_aim, c))
    spread = a + b - 2.0 * c
    if spread <= 0.0:
        # Both sides aim at or above their own eyes: no solid short enough to
        # call cover breaks the pair, and there is no crossing to report.
        raise ValueError(
            "sightlines: aim_height_m %.3f is not below both sight heights "
            "(%.3f, %.3f), so the two lines never cross" % (c, a, b))
    derived = a - (a - c) ** 2 / spread
    stored = s.get("cover_break_height_m")
    if stored is not None and abs(float(stored) - derived) > 0.001:
        raise ValueError(
            "agent_contract.json sightlines: cover_break_height_m is %s but "
            "its own inputs derive %.4f -- re-derive it or fix the heights"
            % (stored, derived))
    return derived


def min_headroom():
    """Clear height a body needs ABOVE the surface it is standing on.

    The third clearance, and the last one to get a reader: it was ratified in
    agent_contract.json with no consumer at all, because every stair check in
    the repo worked on rects. stairwell.headroom_findings is the first caller.
    """
    return float(contract()["clearances"]["min_headroom_m"])
