"""Measure the headroom over a stair flight, against the number already ratified.

Run from the factory root:

    python patch_dc_headroom.py --check
    python patch_dc_headroom.py

Pure: rect and interval arithmetic on the spec. No Blender, no Godot, no
behaviour change to any building that builds today -- the finding ships as a
WARNING (see the rollout note below).

WHAT WAS MEASURED, 2026-08-07.

`agent_contract.json:33` ratifies `clearances.min_headroom_m: 2.0` and it has
ZERO consumers repo-wide -- there is no `min_headroom()` beside the existing
`min_door_width()` / `min_corridor_width()`. Nothing reads it because nothing
in the offline chain asks a vertical question about a stair: `clearance_findings`
uses z only to filter volumes into a storey band (`stairwell.py:286`),
`circulation.stair_volume` spans `z_lo=-1e6, z_hi=1e6` which is prop exclusion
rather than clearance (`circulation.py:140`), `nav_endpoints` are 2D lifted to
`story*H`, and all 34 tests in `test_stair_clearance.py` are planar. A flight is
treated as a rect with a role.

Run over all 138 specs (103 of them carry stairs), the check added here finds:

  * the SLAB half fires 0 times. Every stair in the library has cut_slabs=true,
    every derived hole spans its run, and no spec has story_height -
    floor_thick below 2.0 (the shortest storey in the library is 3.0 m over a
    0.3 m slab). The "stair rises into an uncut ceiling slab" shape does not
    reproduce at spec resolution. It is checked anyway because
    STAIR_TERMINATES_INTO_SLAB already warns about exactly this shape without
    ever measuring it, and a warning with no number cannot be brought to zero.

  * the SOLID-OVERHEAD half fires twice:
      final_stand           'final_stand_stair_0'  0.15 m under 'boss_desk'
      foundry_heist_vertical 'foundry..._stair_1'  0.19 m under 'roof_ac_block_a'
    Both are the LAST treads of a flight running under a prop's underside.
    `final_stand.navgate.json` reports both of that building's stairs
    `status: "ok"`; that gate proves navmesh snap plus a polygon path and bakes
    with agent_height 1.8, not the ratified 2.0, so it has no way to disagree.

WHY THE ASCENT PATH IS RE-DERIVED RATHER THAN READ. The stair's slab hole is
appended to `spec.slab_holes` by the BUILDER, inside `_stairs`, and so does not
exist at review time -- the lateral-containment section says this in as many
words and drives off the reserved footprint to avoid it. Driving off the
footprint is not an option here: `footprint_rect` is the whole reserved column,
so measuring headroom against it asks "is anything above ANY part of this
stair", and on final_stand that answer is yes at 13 places, 11 of which are
above tread positions the flight never occupies at that height. The tread the
climber is actually standing on is what decides, so `ascent_surfaces` rebuilds
the same arithmetic the builder uses. That is duplication and it is the cost of
the check running without a bake -- the alternative is 138 Blender builds and a
human at a keyboard, which is the trap docs/WORKING_AGREEMENT.md names as the
structural cause of its eight wrong explanations.

WHY IT WARNS. Two shipped specs breach. The repo's rule is that a library goes
to zero BEFORE a gate starts refusing builds -- `LAYOUT_BLOCKING` was enabled
only after `layout_lint --all` was clean, and `CONTAINMENT_ENFORCED` is still
False for the same reason. `HEADROOM_ENFORCED` sits beside it with the same
one-line promotion.

WHAT THIS DOES NOT COVER, stated so the next reader does not assume it does.
Only the surfaces the stair itself builds (treads, turn landings, spiral
wedges) are sampled: not the floor either side of the top hole, not partitions
(a full-height wall across a flight is a wall, not a headroom case, and
`clearance_findings` owns the landings), not the exterior-tower slab model. A
volume whose bottom sits AT or BELOW a walking surface is Rule 10's
STAIR_VOLUME_INVADED, not headroom, and is deliberately skipped -- otherwise
'garage_cover' resting on final_stand_stair_1's foot would be reported twice
under two names.
"""
from __future__ import annotations

import sys
from pathlib import Path

CONTRACT = Path("deli_counter/agent_contract.py")
STAIRWELL = Path("deli_counter/stairwell.py")

CONTRACT_EDITS = [
    ("min_headroom accessor", '''\
def min_corridor_width():
    return float(contract()["clearances"]["min_corridor_width_m"])
''', '''\
def min_corridor_width():
    return float(contract()["clearances"]["min_corridor_width_m"])


def min_headroom():
    """Clear height a body needs ABOVE the surface it is standing on.

    The third clearance, and the last one to get a reader: it was ratified in
    agent_contract.json with no consumer at all, because every stair check in
    the repo worked on rects. stairwell.headroom_findings is the first caller.
    """
    return float(contract()["clearances"]["min_headroom_m"])
'''),
]

STAIRWELL_EDITS = [
    ("header: what headroom is gated as", '''\
  - PHYSICAL clearance findings (entry/exit faces solid, landing blocked)
    are UNIVERSAL hard errors as of v0.78: a stair walking into a wall is
    broken geometry regardless of role or authorship. Every shipped spec
    was migrated to comply; new specs must comply from day one.
''', '''\
  - PHYSICAL clearance findings (entry/exit faces solid, landing blocked)
    are UNIVERSAL hard errors as of v0.78: a stair walking into a wall is
    broken geometry regardless of role or authorship. Every shipped spec
    was migrated to comply; new specs must comply from day one.
  - HEADROOM findings (STAIR_HEADROOM_BLOCKED / STAIR_HEADROOM_UNDER_SLAB)
    are the same kind of physical fact but are WARNINGS while two shipped
    specs still breach; HEADROOM_ENFORCED promotes them.
'''),
    ("headroom rollout constant", '''\
_SOLID_BAND = 0.45              # a wall this close to the entry/exit edge =
                                # "the tread faces solid geometry"
''', '''\
_SOLID_BAND = 0.45              # a wall this close to the entry/exit edge =
                                # "the tread faces solid geometry"

# Headroom rollout. The measurement is the same kind of physical fact as the
# clearance findings above -- a body either fits under the thing or it does
# not -- but two shipped specs breach it (see the HEADROOM section), and this
# repo brings a library to zero before a gate starts refusing builds. Same
# switch, same reason, as CONTAINMENT_ENFORCED.
HEADROOM_ENFORCED = False       # -> True once the library measures clean
'''),
    ("headroom section", '''\
# ---------------------------------------------------------------------------
# LATERAL CONTAINMENT  --  a body may fall ALONG a stair, never OUT of it
# ---------------------------------------------------------------------------
''', '''\
# ---------------------------------------------------------------------------
# HEADROOM  --  a flight is a VOLUME; everything above is a rect
# ---------------------------------------------------------------------------
# clearance_findings proves the LONGITUDINAL axis and containment_findings the
# LATERAL one. Both are planar: they ask where a body may walk, never how much
# room it has above its head. agent_contract ratified min_headroom_m years'
# worth of stairs ago and nothing ever read it, so a flight that tops out under
# a desk reads as a clean stair here and as a path in the engine nav gate --
# which bakes at agent_height 1.8 and proves a polygon route, not clearance.
#
# The measurement needs the tread a body is standing ON, not the reserved
# column. footprint_rect is the column, and asking "is anything above any part
# of this footprint" reports every prop on the floor plate the stair passes.
# So ascent_surfaces rebuilds the builder's own tread arithmetic. That is a
# deliberate duplication: the alternative is a Blender build per spec, and the
# whole point is a check that can be run over the library in a second.
#
# KEEP IN STEP WITH deli_counter.Builder._stairs / _stair_l_shaped /
# _stair_spiral. If a flight's step count, run split, or landing depth changes
# there, it changes here. test_headroom.py pins the two ends of every flight
# against the storey heights, which is what catches a drift.


def _stair_pt(st, lx, ly):
    """A point in the stair's own unrotated frame -> world, under `facing`.
    The same mapping as the builder's `Builder._stair_pt`; `_rot_pt` above is
    the half already shared with footprint_rect."""
    dx, dy = _rot_pt(getattr(st, "facing", "N") or "N", lx - st.x, ly - st.y)
    return st.x + dx, st.y + dy


def _stair_sz(st, sx, sy):
    """Local (across, along) extents -> world (x, y); E/W swap the axes."""
    return (sy, sx) if (getattr(st, "facing", "N") or "N") in ("E", "W") \\
        else (sx, sy)


def _step_count(st, H):
    """Steps per storey. Derived from story_height and step_rise so the rise
    stays near the authored target; `n_steps` overrides. Clamps differ by
    style because the builder's do."""
    if st.style == "spiral":
        return st.n_steps or max(10, min(24, round(H / st.step_rise)))
    return st.n_steps or max(6, min(40, round(H / st.step_rise)))


def ascent_surfaces(spec, st):
    """Every walking surface the stair BUILDS, bottom to top.

    Returns ``[(story, x, y, z_top, size_x, size_y)]`` in world coordinates --
    the TOP face of each tread, turn landing and spiral wedge, because that is
    the plane a body's feet are on. The reserved footprint is not usable here:
    it is one rect for the whole stair and carries no z.

    Empty for a stair that spans no stories.
    """
    H = spec.story_height
    lo = min(st.from_story, st.to_story)
    hi = max(st.from_story, st.to_story)
    n = _step_count(st, H)
    out = []

    if st.style == "spiral":
        step_h = H / n
        r = st.width                      # `width` is the RADIUS on a spiral
        tread = 2 * math.pi * r / n * 1.15
        for s in range(lo, hi):
            for i in range(n):
                a = 2 * math.pi * (i + 0.5) / n
                out.append((s, st.x + math.cos(a) * r / 2,
                            st.y + math.sin(a) * r / 2,
                            s * H + step_h * (i + 1), r, tread))
        return out

    if st.style == "l_shaped":
        half = max(1, n // 2)
        n2 = max(1, n - half)
        step_h = H / n
        dA, dB = st.run / half, st.run / n2
        w = st.width
        riseA = H * half / n
        yB = st.y + st.run / 2 + w / 2    # leg B's local row
        for s in range(lo, hi):
            z = s * H
            for i in range(half):         # leg A ascends local +Y
                cy = st.y + dA * (i + 0.5) - st.run / 2
                x, y = _stair_pt(st, st.x, cy)
                sx, sy = _stair_sz(st, w, dA)
                out.append((s, x, y, z + step_h * (i + 1), sx, sy))
            for i in range(n2):           # leg B ascends local +X
                cx = st.x + w / 2 + dB * (i + 0.5)
                x, y = _stair_pt(st, cx, yB)
                sx, sy = _stair_sz(st, dB, w)
                out.append((s, x, y, z + riseA + step_h * (i + 1), sx, sy))
        return out

    step_d, step_h = st.run / n, H / n
    x_off = 0.0 if st.style == "straight" else st.width / 2
    for s in range(lo, hi):
        z = s * H
        leg = s - lo
        # a leg that ends in a turn landing has no top tread: the landing IS
        # the top surface, spanning both runs (builder comment, _stairs).
        has_landing = (st.style == "switchback" and s < hi - 1)
        if st.style == "scissor":
            flights = [(1, st.x - x_off), (-1, st.x + x_off)]
        else:
            sign = 1 if (leg % 2 == 0 or st.style == "straight") else -1
            flights = [(sign, st.x + (x_off if sign > 0 else -x_off))]
        for sign, sxl in flights:
            for i in range(n - 1 if has_landing else n):
                cy = st.y + sign * (step_d * (i + 0.5) - st.run / 2)
                x, y = _stair_pt(st, sxl, cy)
                sx, sy = _stair_sz(st, st.width, step_d)
                out.append((s, x, y, z + step_h * (i + 1), sx, sy))
            if has_landing:
                land_far = 0.7 * step_d
                land_d = step_d + land_far
                land_y = st.y + sign * (st.run / 2 + land_far - land_d / 2)
                land_w = ((st.width + 2 * x_off + 0.8) if st.cut_slabs
                          else st.width + 2 * x_off)
                x, y = _stair_pt(st, st.x, land_y)
                sx, sy = _stair_sz(st, land_w, land_d)
                out.append((s, x, y, z + H, sx, sy))
    return out


def slab_openings(spec):
    """``{slab story: [world rects]}`` -- everything that opens a slab.

    Authored `spec.slab_holes` PLUS the cut each `cut_slabs` stair makes. The
    second half is not in the spec at review time: the builder appends it to
    `spec.slab_holes` during `_stairs`, which is why `_record_slab_slots` has
    to run after the stair pass and why the containment section refuses to
    read slab holes at all. Re-deriving it here is what makes the headroom
    question answerable without a build.

    A hole with ``story == s`` cuts the slab whose TOP face is the floor of
    storey s -- the same key `floors.room_voids` uses, restated nowhere else.
    """
    out = {}
    for h in getattr(spec, "slab_holes", ()) or ():
        out.setdefault(int(getattr(h, "story", 0)), []).append(
            (h.x - h.size_x / 2, h.y - h.size_y / 2,
             h.x + h.size_x / 2, h.y + h.size_y / 2))
    for st in getattr(spec, "stairs", ()) or ():
        if not getattr(st, "cut_slabs", True):
            continue
        lo = min(st.from_story, st.to_story)
        hi = max(st.from_story, st.to_story)
        for s in range(lo, hi):
            if st.style == "spiral":
                r = st.width
                rect = (st.x - r - 0.25, st.y - r - 0.25,
                        st.x + r + 0.25, st.y + r + 0.25)
            elif st.style == "l_shaped":
                w = st.width
                lx0, lx1 = st.x - w / 2 - 0.3, st.x + w / 2 + st.run + 0.8
                ly0, ly1 = st.y - st.run / 2 - 0.3, st.y + st.run / 2 + w + 0.3
                px, py = _stair_pt(st, (lx0 + lx1) / 2, (ly0 + ly1) / 2)
                sx, sy = _stair_sz(st, lx1 - lx0, ly1 - ly0)
                rect = (px - sx / 2, py - sy / 2, px + sx / 2, py + sy / 2)
            else:
                x_off = 0.0 if st.style == "straight" else st.width / 2
                clear = 0.8              # walk-off depth past the landing
                hole_w = st.width + 2 * x_off + clear
                if st.style == "scissor":
                    px, py = _stair_pt(st, st.x, st.y)
                    sx, sy = _stair_sz(st, hole_w, st.run + 2 * clear)
                else:
                    leg = s - lo
                    sign = (1 if (leg % 2 == 0 or st.style == "straight")
                            else -1)
                    near, far = st.run / 2 + 0.3, st.run / 2 + clear
                    px, py = _stair_pt(st, st.x,
                                       st.y + sign * (far - near) / 2)
                    sx, sy = _stair_sz(st, hole_w, far + near)
                rect = (px - sx / 2, py - sy / 2, px + sx / 2, py + sy / 2)
            out.setdefault(s + 1, []).append(rect)
    return out


def _slab_undersides(spec):
    """``{slab story: underside z}`` for every slab the builder lays.

    Mirrors `Builder._slabs`: one per storey from the basement up, plus the
    roof cap at index `n_stories` using roof_thick. ``roof == "none"`` drops
    the top cap entirely, so the top flight of such a building looks at sky.
    """
    H = spec.story_height
    base = -1 if getattr(spec, "has_basement", False) else 0
    top = spec.n_stories
    out = {}
    for k in range(base, top + 1):
        if k == top and getattr(spec, "roof", "solid") == "none":
            continue
        thick = ((getattr(spec, "roof_thick", None) or spec.floor_thick)
                 if k == top else spec.floor_thick)
        out[k] = k * H - thick
    return out


def headroom_findings(spec, st, sid):
    """Clear height over the ascent path, against the RATIFIED min_headroom.

    Returns ``[(code, message)]`` -- STAIR_HEADROOM_UNDER_SLAB when the first
    thing above a walking surface is a slab that nothing opens, and
    STAIR_HEADROOM_BLOCKED when it is a solid volume. One finding per
    obstruction, quoting the WORST sample, because a flight passes nineteen
    treads under the same desk and nineteen identical findings is noise.

    A volume whose bottom sits AT or BELOW the surface is skipped: that is an
    object ON the stair, which Rule 10's STAIR_VOLUME_INVADED already reports
    by name. Reporting it twice under two codes would make the same defect
    look like two.

    A decorative_nontraversable stair is exempt for the reason the module
    header gives: it is explicitly not walked.
    """
    if getattr(st, "role", None) in DECORATIVE_ROLES:
        return []
    clear = agent_contract.min_headroom()
    surfaces = ascent_surfaces(spec, st)
    if not surfaces:
        return []
    exterior = bool(getattr(st, "exterior", False))
    openings = {} if exterior else slab_openings(spec)
    # an exterior tower stands OUTSIDE the shell against a facade, so the
    # storey slabs are not above it and the slab half does not apply (s8.4).
    slabs = {} if exterior else _slab_undersides(spec)
    eps = 1e-6
    worst = {}

    for _s, x, y, zs, sx, sy in surfaces:
        rect = (x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)

        ceiling, label, code = None, None, None
        for k in sorted(slabs):
            zc = slabs[k]
            if zc <= zs + eps:
                continue
            # the sampled surface's CENTRE decides: a tread whose centre is
            # under the opening is a tread a body walks through.
            if any(r[0] <= x <= r[2] and r[1] <= y <= r[3]
                   for r in openings.get(k, ())):
                continue
            ceiling, label = zc, f"the slab at story {k}"
            code = "STAIR_HEADROOM_UNDER_SLAB"
            break
        if ceiling is not None and ceiling - zs < clear - eps:
            key = (code, label)
            if key not in worst or ceiling - zs < worst[key][0]:
                worst[key] = (ceiling - zs, zs, x, y)

        for v in spec.volumes:
            nm = v.name.lower()
            if any(kw in nm for kw in ("stair", "ramp", "land")):
                continue                 # the stair's own furniture
            if getattr(v, "collision", "convex") == "none":
                continue                 # nothing a body can hit
            vrect = (v.x - v.size_x / 2, v.y - v.size_y / 2,
                     v.x + v.size_x / 2, v.y + v.size_y / 2)
            if not _rects_overlap(vrect, rect):
                continue
            vb = v.z - v.size_z / 2
            if vb <= zs + eps:
                continue                 # on the stair -> Rule 10, not this
            if vb - zs < clear - eps:
                key = ("STAIR_HEADROOM_BLOCKED", f"volume '{v.name}'")
                if key not in worst or vb - zs < worst[key][0]:
                    worst[key] = (vb - zs, zs, x, y)

    findings = []
    for (code, label), (gap, zs, x, y) in sorted(
            worst.items(), key=lambda kv: kv[1][0]):
        findings.append((code,
                         f"'{sid}' has {gap:.2f} m of headroom under {label} "
                         f"at ({x:.1f}, {y:.1f}) where the walking surface is "
                         f"z={zs:.2f} -- the contract ratifies {clear:g} m "
                         f"(agent_contract.json clearances.min_headroom_m). A "
                         f"body tops out into it."))
    return findings


# ---------------------------------------------------------------------------
# LATERAL CONTAINMENT  --  a body may fall ALONG a stair, never OUT of it
# ---------------------------------------------------------------------------
'''),
    ("import the contract", '''\
import math

import tactical
''', '''\
import math

import agent_contract
import tactical
'''),
    ("call it from check", '''\
        for code, msg in clearance_findings(spec, st, sid):
            errors.append(f"STAIRWELL {code}: {msg}")
''', '''\
        for code, msg in clearance_findings(spec, st, sid):
            errors.append(f"STAIRWELL {code}: {msg}")

        # headroom: the same physical question on the vertical axis. Warned
        # until the library measures clean; HEADROOM_ENFORCED promotes it.
        for code, msg in headroom_findings(spec, st, sid):
            (errors if HEADROOM_ENFORCED else warnings).append(
                f"STAIRWELL {code}: {msg}")
'''),
]

TARGETS = [(CONTRACT, CONTRACT_EDITS), (STAIRWELL, STAIRWELL_EDITS)]


def _apply(target, edits, check_only):
    if not target.is_file():
        print(f"[patch] {target} not found -- run from the factory root")
        return 1, 0
    raw = target.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    print(f"[patch] {target}: {len(raw)} bytes, "
          f"endings={'CRLF' if crlf else 'LF'}")

    problems = []
    for name, before, after in edits:
        if after in text:
            print(f"[patch]   ALREADY APPLIED: {name}")
        elif before not in text:
            print(f"[patch]   ANCHOR NOT FOUND: {name}")
            problems.append(name)
        elif text.count(before) != 1:
            print(f"[patch]   ANCHOR NOT UNIQUE ({text.count(before)}x): {name}")
            problems.append(name)
    if problems:
        print(f"[patch] REFUSING to write {target}: {len(problems)} anchor(s) "
              f"did not match cleanly.")
        return 1, 0

    for name, before, after in edits:
        if after in text:
            continue
        text = text.replace(before, after)
        print(f"[patch]   applied: {name}")

    payload = (text.replace("\n", "\r\n") if crlf else text).encode("utf-8")
    if payload == raw:
        print(f"[patch]   no change ({len(raw)} bytes)")
        return 0, 0
    if check_only:
        print(f"[patch]   --check: would write {len(raw)} -> {len(payload)} "
              f"bytes ({len(payload) - len(raw):+d})")
        return 0, 0
    target.write_bytes(payload)
    print(f"[patch]   wrote {len(raw)} -> {len(payload)} bytes "
          f"({len(payload) - len(raw):+d})")
    return 0, len(payload) - len(raw)


def main(argv):
    check_only = "--check" in argv
    # Nothing is written until EVERY anchor on EVERY file has matched. A patch
    # that half-applies leaves stairwell.py calling a function agent_contract.py
    # does not have, and the next run's --check cannot tell that from a fresh
    # tree.
    for target, edits in TARGETS:
        rc, _ = _apply(target, edits, check_only=True)
        if rc:
            print("[patch] REFUSING to write anything.")
            return 1
    if check_only:
        print("[patch] --check: all anchors matched, no write")
        return 0
    total = 0
    for target, edits in TARGETS:
        rc, delta = _apply(target, edits, check_only=False)
        if rc:
            return 1
        total += delta
    print(f"[patch] total {total:+d} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
