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


def _checks(spec):
    """The three questions a seated stair must answer, as closures over the
    spec DICT (read fresh on every call, because the search edits it)."""
    import contextlib
    import io
    from spec_loader import spec_from_dict
    import stairwell

    import layout_lint

    def contract():
        with contextlib.redirect_stdout(io.StringIO()):
            return stairwell.circulation_contract(spec_from_dict(spec))

    def mine(findings, sid):
        return [f for f in findings if f"'{sid}'" in f]

    def ok(sid):
        """Compliant with the circulation contract, inside the footprint
        (`layout_lint` L19 -- a longer run can reserve ground past the exterior
        wall while the contract is satisfied; `harbor_score` did, by 0.15 m),
        and cutting no wall and opening under no doorway (L21)."""
        me = [s for s in contract()["stairs"] if s["id"] == sid]
        return (bool(me) and me[0]["compliant"]
                and not mine(layout_lint.stair_bounds_findings(spec), sid)
                and not mine(layout_lint.stair_wall_findings(spec), sid))

    return contract, ok, mine


def _reseat(spec, st, ok, also=None):
    """Try the stair's own facing then the other three, each with short shifts
    along both axes; keep the first seat `ok` accepts (and `also`, if given).
    Returns ``(facing, axis, shift)`` or None, restoring the seat on None."""
    sid = st.get("id")
    x0, y0, f0 = st["x"], st["y"], st.get("facing")
    for facing in [f0] + [f for f in ("N", "E", "S", "W") if f != f0]:
        for axis in ("x", "y"):
            for d in (0.0,) + _SHIFTS:
                st["x"], st["y"], st["facing"] = x0, y0, facing
                st[axis] = round(st[axis] + d, 3)
                if ok(sid) and (also is None or also()):
                    return (facing, axis, d)
    st["x"], st["y"], st["facing"] = x0, y0, f0
    return None


#: The wider search `clear_walls` falls back to: both axes at once, out to
#: this far, nearest seat first. A stair in a tight plan can need a diagonal
#: move the one-axis search never tries.
WIDE_SHIFT_MAX = 6.0
WIDE_SHIFT_STEP = 0.5


def _reseat_wide(spec, st, ok, also=None):
    """As `_reseat`, over a two-axis grid of shifts ordered by distance.
    Returns ``(facing, "xy", (dx, dy))`` or None, restoring the seat on None."""
    sid = st.get("id")
    x0, y0, f0 = st["x"], st["y"], st.get("facing")
    n = int(round(WIDE_SHIFT_MAX / WIDE_SHIFT_STEP))
    steps = [i * WIDE_SHIFT_STEP for i in range(-n, n + 1)]
    grid = sorted(((dx, dy) for dx in steps for dy in steps),
                  key=lambda d: (abs(d[0]) + abs(d[1]), abs(d[0]), d))
    for facing in [f0] + [f for f in ("N", "E", "S", "W") if f != f0]:
        for dx, dy in grid:
            st["x"], st["y"], st["facing"] = (round(x0 + dx, 3),
                                              round(y0 + dy, 3), facing)
            if ok(sid) and (also is None or also()):
                return (facing, "xy", (dx, dy))
    st["x"], st["y"], st["facing"] = x0, y0, f0
    return None


def make_walkable(spec):
    """Lengthen, then re-seat any lengthened stair the circulation contract now
    refuses. Returns ``{"lengthened": [...], "reseated": {id: (facing, axis,
    shift)}, "unresolved": [...]}``; the spec dict is edited in place."""
    contract, ok, _mine = _checks(spec)
    out = {"lengthened": lengthen(spec), "reseated": {}, "unresolved": []}
    if not out["lengthened"]:
        return out
    by_id = {st.get("id"): st for st in spec.get("stairs") or []}
    for sid in [s["id"] for s in contract()["stairs"] if not ok(s["id"])]:
        st = by_id.get(sid)
        if st is None or sid not in out["lengthened"]:
            continue            # it was already failing; not ours to move
        found = _reseat(spec, st, ok)
        if found:
            out["reseated"][sid] = found
        else:
            out["unresolved"].append(sid)
    return out


def _rect_intrusions(spec):
    """``{"INTRUDES <volume> <stair> <storey>"}`` -- every solid volume standing
    in a stair's reserved rectangle on the storey it climbs through or the
    storey whose slab it opens. Measured on the first run of `clear_walls`:
    the two-axis search seated three stairs over existing props
    (`primos_pizza`'s prep island and crates, `night_pawn`'s display case,
    `strip_retail_a01`'s prep island), none of which any gate refused."""
    from spec_loader import spec_from_dict
    import stairwell
    s = spec_from_dict(spec)
    H = s.story_height
    out = set()
    for j, st in enumerate(s.stairs):
        if st.style == "spiral":
            continue
        lo = min(st.from_story, st.to_story)
        hi = max(st.from_story, st.to_story)
        for k in range(lo, hi):
            a0, b0, a1, b1 = stairwell.flight_rect(st, k)
            for v in s.volumes:
                if v.collision == "none" or v.name.startswith("stair_guard_"):
                    continue
                base = v.z - v.size_z / 2.0
                if not (k * H - 0.01 <= base < (k + 2) * H - 0.01):
                    continue
                if (min(v.x + v.size_x / 2.0, a1) - max(v.x - v.size_x / 2.0, a0)
                        > 0.05 and
                        min(v.y + v.size_y / 2.0, b1) - max(v.y - v.size_y / 2.0, b0)
                        > 0.05):
                    out.add(f"INTRUDES {v.name} {stairwell.stair_ident(st, j)} {k}")
    return out


def _stair_errors(spec):
    """Every stairwell review ERROR for the spec, as a set of strings."""
    import contextlib
    import io
    from spec_loader import spec_from_dict
    import stairwell
    with contextlib.redirect_stdout(io.StringIO()):
        errors, _warnings, _summary = stairwell.check(spec_from_dict(spec))
    return set(errors)


def clear_walls(spec):
    """Re-seat every stair whose hole cuts a wall or opens under a doorway
    (`layout_lint` L21). A stair already refused by the contract or L19 for
    another reason is still moved if L21 names it, but only to a seat that
    passes all three -- and that adds no lint failure naming anything else.
    Returns ``{"reseated": {id: seat}, "unresolved": [...]}``."""
    import layout_lint
    _contract, ok, mine = _checks(spec)
    out = {"reseated": {}, "unresolved": []}
    for st in spec.get("stairs") or []:
        sid = st.get("id")
        if sid is None or st.get("exterior"):
            continue
        if not mine(layout_lint.stair_wall_findings(spec), sid):
            continue
        before = (set(layout_lint.gate(spec)[0]) | _stair_errors(spec)
                  | _rect_intrusions(spec))

        def no_new_failures():
            # Nothing may get worse: no new lint failure and no new stairwell
            # error. Measured on the `bank` stair-core
            # preset: a seat that satisfied this stair's own contract took
            # the lower landing of the core beside it.
            # The error that proved it named BOTH stairs, so a filter on
            # "findings that do not mention this stair" let it through: any
            # finding that was not there before refuses the seat.
            now = (set(layout_lint.gate(spec)[0]) | _stair_errors(spec)
                   | _rect_intrusions(spec))
            return not (now - before)

        found = (_reseat(spec, st, ok, also=no_new_failures)
                 or _reseat_wide(spec, st, ok, also=no_new_failures))
        if found:
            out["reseated"][sid] = found
        else:
            out["unresolved"].append(sid)
    return out
