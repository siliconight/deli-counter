"""
stair_pitch.py  --  a stair a body can climb (pure, no bpy)
===========================================================
The walker, 2026-09-13, on cold run 9046's walk copy: "cant get up the steps".
The flight was a stadium's, 5.5 m of storey over a 4.7 m run -- 49.5 degrees.

MEASURED ACROSS THE LIBRARY BEFORE CHANGING ANYTHING (straight and switchback
flights in every shipped spec): 36 at 40 degrees or less, 51 between 40 and
45, and 61 over 45. `CharacterBody3D.floor_max_angle` is 45 degrees, so 61
flights -- 41% -- are slopes a player slides back down. The navmesh bakes them
anyway (`nav_bake.agent_max_slope_deg` is 55), which is why every nav gate
passed: the known contract tension CLAUDE.md names, found by a person on a
screen. Runs were authored near 4 m while storeys run 4.6 to 6.5 m, and pitch
is `atan(story_height / run)` for EVERY leg -- a switchback here is legs that
each climb a full storey in alternating directions, not half-rise flights.

THE RULE. A flight's pitch may not exceed `MAX_WALKABLE_PITCH_DEG` (40): five
degrees under the 45 a body stands on, because the smooth ramp collider sits
half a step proud and is extended at its foot, and a slope measured at exactly
the engine's limit is a slope some frames refuse. A flight over the limit is
lengthened to `TARGET_PITCH_DEG` (38), the building-code band (37 degrees is
the usual commercial maximum) and inside the tactical review's own "walkable"
range.

LENGTHENING MOVES A FOOTPRINT, so `make_walkable` re-checks every stair it
touched against `stairwell.circulation_contract` AND `layout_lint`'s L19 stair
bounds, and, when the longer flight now fails either, tries a turn and short
shifts along both axes. Measured before
this was written: lengthening alone left 55 of the 70 affected specs
compliant; the search repaired all 15 others.
"""
import math

MAX_WALKABLE_PITCH_DEG = 40.0
TARGET_PITCH_DEG = 38.0
#: Stair styles whose legs are straight runs this rule applies to. A spiral
#: and an L-shaped stair derive their geometry differently and are left alone.
PITCHED_STYLES = ("straight", "switchback", "scissor")
DEFAULT_RUN = 4.0            # spec_types.Stairwell.run
_SHIFTS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, -0.5, -1.0, -1.5, -2.0, -2.5, -3.0)


def pitch_deg(story_height, run):
    return math.degrees(math.atan2(float(story_height), float(run)))


def walkable_run(story_height):
    """The run, rounded UP to 0.1 m, that puts one storey at TARGET_PITCH_DEG."""
    need = float(story_height) / math.tan(math.radians(TARGET_PITCH_DEG))
    return math.ceil(need * 10.0 - 1e-9) / 10.0


def lengthen(spec):
    """Lengthen every over-steep flight in a spec DICT in place. Returns the
    ids (or indices) of the stairs changed. Touches `run` only."""
    H = float(spec.get("story_height") or 0.0)
    changed = []
    for i, st in enumerate(spec.get("stairs") or []):
        if (st.get("style") or "straight") not in PITCHED_STYLES or not H:
            continue
        run = float(st.get("run") or DEFAULT_RUN)
        if pitch_deg(H, run) > MAX_WALKABLE_PITCH_DEG + 1e-9:
            st["run"] = max(run, walkable_run(H))
            changed.append(st.get("id") or i)
    return changed


def make_walkable(spec):
    """Lengthen, then re-seat any lengthened stair the circulation contract now
    refuses. Returns ``{"lengthened": [...], "reseated": {id: (facing, axis,
    shift)}, "unresolved": [...]}``; the spec dict is edited in place."""
    import contextlib
    import io
    from spec_loader import spec_from_dict
    import stairwell

    import layout_lint

    def contract():
        with contextlib.redirect_stdout(io.StringIO()):
            return stairwell.circulation_contract(spec_from_dict(spec))

    def out_of_bounds(sid):
        """`layout_lint` L19 for this stair: a longer run can reserve ground
        past the exterior wall while the circulation contract is satisfied --
        `harbor_score` did, by 0.15 m, on the first migration."""
        return any(f"'{sid}'" in f for f in layout_lint.stair_bounds_findings(spec))

    def ok(sid):
        me = [s for s in contract()["stairs"] if s["id"] == sid]
        return bool(me) and me[0]["compliant"] and not out_of_bounds(sid)

    out = {"lengthened": lengthen(spec), "reseated": {}, "unresolved": []}
    if not out["lengthened"]:
        return out
    by_id = {st.get("id"): st for st in spec.get("stairs") or []}
    for sid in [s["id"] for s in contract()["stairs"] if not ok(s["id"])]:
        st = by_id.get(sid)
        if st is None or sid not in out["lengthened"]:
            continue            # it was already failing; not ours to move
        x0, y0, f0 = st["x"], st["y"], st.get("facing")
        found = None
        for facing in [f0] + [f for f in ("N", "E", "S", "W") if f != f0]:
            for axis in ("x", "y"):
                for d in (0.0,) + _SHIFTS:
                    st["x"], st["y"], st["facing"] = x0, y0, facing
                    st[axis] = round(st[axis] + d, 3)
                    if ok(sid):
                        found = (facing, axis, d)
                        break
                if found:
                    break
            if found:
                break
        if found:
            out["reseated"][sid] = found
        else:
            st["x"], st["y"], st["facing"] = x0, y0, f0
            out["unresolved"].append(sid)
    return out
