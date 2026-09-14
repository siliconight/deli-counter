"""vault_room.py -- a bank vault is a room behind a round door (pure, no bpy).

The walker, walk 9052 (`bank_branch_a02`'s basement): "the bank vault should
absolutely be a hero piece". What stood there was a 5 x 5 x 3 m `VAULT` box
volume, a `prop` slot with no species. Zoo 0.83.0 builds a round vault door
for an opening slot of role `vault_door`, per state of the `vault_door`
machine. This module is Deli Counter's half:

* **the slot a vault door needs** (`slot_width`, `required_size`): the module
  replaces the WHOLE slot, and a round door with a frame and hinges is much
  wider than the aperture it circumscribes;
* **where its leaf swings** (`swing_local`, `swing_rect`): the floor in front
  of the door the open and breached leaf occupies, which nothing may stand in;
* **the gate** (`findings`, layout_lint L22);
* **the generator** (`enclose_vaults`): a vault volume becomes a vault room --
  partitions round it in a corner of the room it stands in, the `vault`
  opening facing the approach, deposit-box walls inside.

THE NUMBERS ARE ZOO'S. `zoo_keeper/core/vault_forms.py` decides every
position of the door; the subset needed to size a slot and bound a swing is
retyped here because Deli Counter must build without Zoo beside it.
`test_vault_room.py` pins every retyped number to Zoo's own functions when
the zoo repo is found next to this one, so the two cannot drift silently.

FRAME AND UNITS (Zoo's, `vault_forms` docstring). Module-local, centre pivot,
metres: x across the slot, y through the wall, +y the FACE the approach sees,
z up, the module floor at z = -h/2. Standing in front of the face looking at
it, +x is on the viewer's LEFT; the hinges are at +x.

WORLD. Deli Counter's slot `rot_y` is a COMPASS BEARING (`_slot_orient`: N 0,
E 90, S 180, W 270) that turns the module's +y onto that bearing: local +y is
world (sin t, cos t) and local +x is world (cos t, -sin t), in Blender Z-up
plan coordinates. Derived from `tscn_export.godot_basis`, the placement the
Godot composer writes (rows Ry(-t), glTF +Y up: Blender local +y is glTF -z).
`Builder._instance_module`, the Blender-side resolver, turns by Rz(+t), the
mirror image at 90 and 270 -- it is only used when a module library is
configured at build time and a symmetric door never showed it.
"""
from __future__ import annotations

import math
import re

# ------------------------------------------------------------ Zoo's constants
#: `vault_forms.DEFAULT_OPENING`: the body contract's `min_door_width_m` 1.25
#: rounded up, 2.1 m against `min_headroom_m` 2.0. Sill 0: Deli Counter's old
#: 0.15 sat above `clearances.unassisted_step_max_m` (0.1025), the known
#: contract tension (the factory root's "Known contract tensions"), and Zoo
#: lays a 16 mm threshold plate there.
APERTURE = {"width": 1.3, "height": 2.1, "sill": 0.0}

FRAME_FRAC = 0.22          # vault_forms.DEFAULTS["frame_frac"]
MARGIN = 0.10              # vault_forms.DEFAULTS["margin"]
OPEN_SWING_DEG = 100.0     # vault_forms.DEFAULTS["open_swing_deg"]
BREACH_SWING_DEG = 122.0   # vault_forms.DEFAULTS["breach_swing_deg"]
BREACH_TILT_DEG = 13.0     # vault_forms.DEFAULTS["breach_tilt_deg"]
BOLT_LENGTH = 0.16         # vault_forms.DEFAULTS["bolt_length"]
CUT_LEAF = 0.022           # vault_forms.CUT_LEAF
DOOR_GAP = 0.012           # vault_forms.DOOR_GAP
KNUCKLE = 1.12             # vault_forms.KNUCKLE
BOSS_BACK = 0.02           # vault_forms.BOSS_BACK
BOSS_DEPTH = 0.04          # vault_forms.BOSS_DEPTH
LEAF_CHUNKS = 4            # vault_forms.leaf_collision's `chunks`

#: A slot's width is the module's required width rounded UP to this. Zoo
#: builds the door unshrunk in any slot at least `required_size` wide, and the
#: filename carries whole centimetres, so a round decimetre keeps one stem per
#: aperture: 1.3 x 2.1 needs 3.5837 m and gets 3.6.
SLOT_STEP = 0.1

#: The sweep step, in degrees, when bounding the swinging leaf. A corner on a
#: 2.8 m leaf strays at most L * (1 - cos(step / 2)) = 0.1 mm between samples;
#: `SWING_PAD` covers it.
SWING_STEP_DEG = 1.0
SWING_PAD = 0.01


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def portal_radius(ow, oh):
    """`vault_forms.portal_radius`: the circle through the aperture's corners."""
    return math.hypot(ow / 2.0, oh / 2.0)


def frame_width(r):
    """`vault_forms.frame_width` at the default `frame_frac`."""
    return _clamp(FRAME_FRAC * r, 0.16, 0.34)


def hinge_radius(r):
    """`vault_forms.hinge_radius`."""
    return _clamp(0.12 * r, 0.09, 0.16)


def required_size(ow, oh, sill=0.0):
    """`vault_forms.required_size`: the smallest (width, height) slot that
    builds this aperture unshrunk. Width is the circle, the frame, the hinge
    barrels outside the frame and a margin each side; height the sill, the
    circle's top, the frame and the margin."""
    r = portal_radius(ow, oh)
    fw = frame_width(r)
    rb = hinge_radius(r)
    return {"width": round(2.0 * (r + fw + 1.25 * rb + MARGIN), 4),
            "height": round(sill + oh / 2.0 + r + fw + MARGIN, 4),
            "portal_radius": round(r, 4)}


def slot_width(ow, oh, sill=0.0):
    """The width Deli Counter gives a vault slot: `required_size` rounded up to
    `SLOT_STEP`. The subtraction guards a required width that is already a
    whole step from being pushed to the next one by float noise."""
    need = required_size(ow, oh, sill)["width"]
    return round(math.ceil(need / SLOT_STEP - 1e-6) * SLOT_STEP, 4)


# ------------------------------------------------------------ Zoo's leaf pose
def plan(w, d, h, opening=None):
    """The subset of `vault_forms.plan_vault` the leaf pose reads, retyped."""
    op = dict(APERTURE)
    for k in ("width", "height", "sill"):
        val = (opening or {}).get(k)
        if val is None:
            continue
        val = float(val)
        if val > 0.0 or (k == "sill" and val == 0.0):
            op[k] = val
    hw, hh = w / 2.0, h / 2.0
    sill = _clamp(op["sill"], 0.0, 0.5 * h)
    ow = op["width"]
    oh = min(op["height"], h - sill - 0.05)
    z_cut = -hh + sill
    zc = z_cut + oh / 2.0
    r_want = portal_radius(ow, oh)
    fw = frame_width(r_want)
    rb = hinge_radius(r_want)
    r = min(r_want, hw - MARGIN - fw - 1.25 * rb, hh - MARGIN - fw - zc)
    dz = zc - z_cut
    if r < dz + 0.06:
        dz = max(0.05, r - 0.12)
        zc = z_cut + dz
    fw = frame_width(r)
    rb = min(hinge_radius(r), d / 2.3)
    f = d / 2.0
    hz = 0.52 * r
    rim_x = math.sqrt(max(0.0, (r + fw) ** 2 - hz * hz))
    return {"w": w, "d": d, "h": h, "r": r, "zc": zc, "z_cut": z_cut,
            "rd": r - DOOR_GAP, "f": f, "y_leaf_back": -f + BOSS_BACK + BOSS_DEPTH,
            "hinge_x": rim_x + 0.25 * rb, "hinge_y": f - KNUCKLE * rb,
            "hinge_top": zc + hz + _clamp(0.28 * r, 0.25, 0.40) / 2.0,
            "shortfall": round(max(0.0, r_want - r), 4)}


def _axis_angle(point, axis, ang):
    """`vault_forms.mat_axis_angle`: a 4x4 row-major rotation about `axis`
    through `point`, right-hand rule."""
    ax, ay, az = axis
    ln = math.sqrt(ax * ax + ay * ay + az * az)
    ax, ay, az = ax / ln, ay / ln, az / ln
    c, s = math.cos(ang), math.sin(ang)
    k = 1.0 - c
    rot = ((c + ax * ax * k, ax * ay * k - az * s, ax * az * k + ay * s),
           (ay * ax * k + az * s, c + ay * ay * k, ay * az * k - ax * s),
           (az * ax * k - ay * s, az * ay * k + ax * s, c + az * az * k))
    t = [point[i] - sum(rot[i][j] * point[j] for j in range(3))
         for i in range(3)]
    return tuple(tuple(rot[i]) + (t[i],) for i in range(3)) + \
        ((0.0, 0.0, 0.0, 1.0),)


def _mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(4))
                       for j in range(4)) for i in range(4))


def _apply(m, p):
    return tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3]
                 for i in range(3))


def leaf_matrix(v, swing_deg, tilt=False):
    """`vault_forms.leaf_matrix` at an arbitrary swing: about the hinge axis
    (vertical, through the barrels at +x), clockwise from above, so the leaf
    travels toward +y. `tilt` adds the breached lean about its bottom edge."""
    phi = math.radians(swing_deg)
    m = _axis_angle((v["hinge_x"], v["hinge_y"], 0.0), (0.0, 0.0, 1.0), -phi)
    if not tilt:
        return m
    u_axis = (math.cos(phi), -math.sin(phi), 0.0)
    pivot = _apply(m, (0.0, v["y_leaf_back"], v["z_cut"] + CUT_LEAF))
    return _mul(_axis_angle(pivot, u_axis, math.radians(BREACH_TILT_DEG)), m)


def _leaf_chunks(v, bolt):
    """`vault_forms.leaf_collision`'s slices, in the closed pose: each an
    (x0, x1, y0, y1, z0, top) box."""
    rd = v["rd"] + bolt
    x0, x1 = -rd, v["hinge_x"]
    y0, y1 = v["y_leaf_back"], v["f"]
    z0 = v["z_cut"] + CUT_LEAF
    rr = v["zc"] + rd - v["zc"]
    out = []
    for c in range(LEAF_CHUNKS):
        xa = x0 + (x1 - x0) * c / LEAF_CHUNKS
        xb = x0 + (x1 - x0) * (c + 1) / LEAF_CHUNKS
        near = 0.0 if xa <= 0.0 <= xb else min(abs(xa), abs(xb))
        top = v["zc"] + math.sqrt(max(0.0, rr * rr - near * near))
        top = max(top, v["hinge_top"])
        out.append((xa, xb, y0, y1, z0, top))
    return out


def _boxes(m, chunks):
    out = []
    for xa, xb, y0, y1, z0, top in chunks:
        pts = [_apply(m, (x, y, z)) for x in (xa, xb) for y in (y0, y1)
               for z in (z0, top)]
        out.append((tuple(min(p[i] for p in pts) for i in range(3)),
                    tuple(max(p[i] for p in pts) for i in range(3))))
    return out


def leaf_boxes(v, state):
    """`vault_forms.leaf_collision(v, state)`: the AABBs of the leaf in the
    open or breached pose. Pinned to Zoo's by test."""
    if state == "open":
        return _boxes(leaf_matrix(v, OPEN_SWING_DEG), _leaf_chunks(v, BOLT_LENGTH))
    if state == "breached":
        return _boxes(leaf_matrix(v, BREACH_SWING_DEG, tilt=True),
                      _leaf_chunks(v, 0.04))
    return []


def swing_local(w, d, h, opening=None):
    """``(x0, x1, y0, y1)``, slot-local: the plan rectangle the leaf sweeps in
    front of the face, from closed to fully breached.

    Not only the two end poses. Zoo's collision boxes the leaf where it comes
    to REST; a leaf swinging open passes every angle in between, and at 90
    degrees its free edge stands further out than at 100. So the leaf is swept
    from 0 to the breach angle in `SWING_STEP_DEG` steps with its bolts drawn
    (the open pose's), and the breached pose's lean is added at the end.
    Starts at the face plane: behind it is the wall.
    """
    v = plan(w, d, h, opening)
    lo = [1e18, 1e18]
    hi = [-1e18, -1e18]
    chunks = _leaf_chunks(v, BOLT_LENGTH)
    n = int(round(BREACH_SWING_DEG / SWING_STEP_DEG))
    poses = [leaf_matrix(v, BREACH_SWING_DEG * i / n) for i in range(n + 1)]
    boxes = [b for m in poses for b in _boxes(m, chunks)]
    boxes += leaf_boxes(v, "breached")
    for a, b in boxes:
        for i in range(2):
            lo[i] = min(lo[i], a[i])
            hi[i] = max(hi[i], b[i])
    return (lo[0] - SWING_PAD, hi[0] + SWING_PAD, v["f"],
            max(v["f"], hi[1] + SWING_PAD))


# ------------------------------------------------------------- world frame
BEARING = {"N": 0, "E": 90, "S": 180, "W": 270}
#: Which faces a wall running along each axis can have.
FACES_FOR_AXIS = {"X": ("N", "S"), "Y": ("E", "W")}


def to_world(cx, cy, rot_deg, x, y):
    """Slot-local plan (x, y) to world, for a slot at (cx, cy) with compass
    bearing `rot_deg` (see WORLD above)."""
    t = math.radians(rot_deg)
    c, s = math.cos(t), math.sin(t)
    return (cx + x * c + y * s, cy - x * s + y * c)


def local_rect_world(cx, cy, rot_deg, rect):
    x0, x1, y0, y1 = rect
    pts = [to_world(cx, cy, rot_deg, x, y) for x in (x0, x1) for y in (y0, y1)]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def swing_rect(cx, cy, face, w, d, h, opening=None):
    """World ``(x0, y0, x1, y1)`` of the leaf's sweep for a vault door slot at
    (cx, cy) whose face points `face`."""
    return local_rect_world(cx, cy, BEARING[face],
                            swing_local(w, d, h, opening))


# --------------------------------------------------- vault openings in a spec
def _num(v, default):
    return default if v is None else float(v)


def wall_height(spec, story):
    """A wall's built height: the storey less the slab that caps it
    (`Builder._cap_thick`)."""
    H = _num(spec.get("story_height"), 3.0)
    ft = _num(spec.get("floor_thick"), 0.3)
    top = int(spec.get("n_stories", 1) or 1)
    cap = (_num(spec.get("roof_thick"), ft) if story + 1 == top else ft)
    return H - cap


def resolved_aperture(op):
    """The aperture a `vault` opening builds, with `spec_types`' defaults."""
    out = dict(APERTURE)
    for k in ("width", "height", "sill"):
        if op.get(k) is not None:
            out[k] = float(op[k])
    return out


def _grid(spec):
    return _num(spec.get("grid"), 0.5)


def _snap(v, g):
    return round(v / g) * g


def wall_openings(spec, kinds=("vault",)):
    """Every opening of `kinds` on a partition or an exterior wall, with its
    world centre as the builder places it: ``pos * run`` from the run's centre,
    snapped to the spec's `grid` (`Builder._opening_to_hole`). Each entry:
    ``{"host", "is_ext", "story", "axis", "line", "lo", "hi", "along", "x",
    "y", "op"}`` -- `line` the wall's fixed coordinate, `lo..hi` its run."""
    fx = _num(spec.get("footprint_x"), 0.0)
    fy = _num(spec.get("footprint_y"), 0.0)
    hx, hy = fx / 2.0, fy / 2.0
    g = _grid(spec)
    out = []
    for p in spec.get("partitions") or []:
        ax = str(p.get("axis", "X")).upper()
        b = hx if ax == "X" else hy
        s = -b if p.get("start") is None else float(p["start"])
        e = b if p.get("end") is None else float(p["end"])
        lo, hi = min(s, e), max(s, e)
        for op in p.get("openings") or []:
            if op.get("kind") not in kinds:
                continue
            along = (lo + hi) / 2.0 + _snap(float(op.get("pos", 0.0)) * (hi - lo), g)
            line = float(p.get("pos", 0.0))
            x, y = (along, line) if ax == "X" else (line, along)
            out.append({"host": p, "is_ext": False, "story": int(p.get("story", 0)),
                        "axis": ax, "line": line, "lo": lo, "hi": hi,
                        "along": along, "x": x, "y": y, "op": op})
    for w in spec.get("ext_walls") or []:
        face = w.get("wall")
        if face not in BEARING:
            continue
        ax = "X" if face in ("N", "S") else "Y"
        run = fx if ax == "X" else fy
        line = {"N": hy, "S": -hy, "E": hx, "W": -hx}[face]
        for op in w.get("openings") or []:
            if op.get("kind") not in kinds:
                continue
            along = _snap(float(op.get("pos", 0.0)) * run, g)
            x, y = (along, line) if ax == "X" else (line, along)
            out.append({"host": w, "is_ext": True, "story": int(w.get("story", 0)),
                        "axis": ax, "line": line, "lo": -run / 2.0,
                        "hi": run / 2.0, "along": along, "x": x, "y": y,
                        "op": op})
    return out


def door_geometry(spec, entry):
    """Slot size and swing for one vault opening entry, or None when it has no
    `face` (no approach side, so no swing to keep clear)."""
    op = entry["op"]
    ap = resolved_aperture(op)
    wt = _num(spec.get("wall_thick"), 0.3)
    wh = wall_height(spec, entry["story"])
    sw = slot_width(ap["width"], ap["height"], ap["sill"])
    need = required_size(ap["width"], ap["height"], ap["sill"])
    face = op.get("face")
    out = {"aperture": ap, "slot_w": sw, "wall_h": wh, "thick": wt,
           "need_h": need["height"], "face": face, "swing": None}
    if face in BEARING:
        out["swing"] = swing_rect(entry["x"], entry["y"], face, sw, wt, wh, ap)
    return out


def keepout_rects(spec, story):
    """World rects on `story` that furniture and cover must stay out of: each
    faced vault door's swing."""
    out = []
    for e in wall_openings(spec):
        if e["story"] != story:
            continue
        geo = door_geometry(spec, e)
        if geo["swing"]:
            out.append(geo["swing"])
    return out


def _overlap(a, b, eps=1e-6):
    return (a[0] < b[2] - eps and b[0] < a[2] - eps
            and a[1] < b[3] - eps and b[1] < a[3] - eps)


def _stair_rects(spec, story):
    """Reserved rectangles of every stair that passes through `story`: the
    footprint and its landings, and the flight rectangle the builder cuts."""
    try:
        import stairwell
        from spec_types import Stairwell
    except ImportError:
        return []
    fields = ("x", "y", "from_story", "to_story", "width", "run", "style",
              "facing", "exterior", "transfer", "cut_slabs", "step_rise",
              "n_steps", "id", "role", "stack_id", "meta")
    out = []
    for raw in spec.get("stairs") or []:
        lo = min(raw.get("from_story", 0), raw.get("to_story", 0))
        hi = max(raw.get("from_story", 0), raw.get("to_story", 0))
        if not lo <= story <= hi:
            continue
        try:
            st = Stairwell(**{k: raw[k] for k in fields if k in raw})
        except TypeError:
            continue
        label = raw.get("id") or "stair"
        out.append((label, stairwell.footprint_rect(st)))
        # both landings, whatever storey they serve: `stair_endpoints` does
        # not say which storey an end is on, and a landing kept clear on a
        # storey that did not need it costs a corner, not a defect
        out.extend((label, e["rect"]) for e in stairwell.stair_endpoints(st))
        if st.style != "spiral":
            for s in range(lo, hi):
                if s in (story, story - 1):
                    out.append((label, stairwell.flight_rect(st, s)))
    return out


def _volume_rect(v):
    return (v["x"] - v.get("size_x", 1.0) / 2.0, v["y"] - v.get("size_y", 1.0) / 2.0,
            v["x"] + v.get("size_x", 1.0) / 2.0, v["y"] + v.get("size_y", 1.0) / 2.0)


def _volume_on_story(spec, v, story):
    H = _num(spec.get("story_height"), 3.0)
    z0 = v.get("z", 0.0) - v.get("size_z", 0.0) / 2.0
    z1 = v.get("z", 0.0) + v.get("size_z", 0.0) / 2.0
    return z1 > story * H + 1e-6 and z0 < (story + 1) * H - 1e-6


def _wall_strip(spec, p):
    """A partition's plan rect, at its thickness."""
    fx = _num(spec.get("footprint_x"), 0.0)
    fy = _num(spec.get("footprint_y"), 0.0)
    wt = _num(spec.get("wall_thick"), 0.3)
    ax = str(p.get("axis", "X")).upper()
    b = fx / 2.0 if ax == "X" else fy / 2.0
    s = -b if p.get("start") is None else float(p["start"])
    e = b if p.get("end") is None else float(p["end"])
    lo, hi = min(s, e), max(s, e)
    line = float(p.get("pos", 0.0))
    if ax == "X":
        return (lo, line - wt / 2.0, hi, line + wt / 2.0)
    return (line - wt / 2.0, lo, line + wt / 2.0, hi)


def findings(spec):
    """L22 -- (fails, warns) for every vault door in a spec.

    FAIL:
      * the `face` is not one a wall on that axis can have;
      * the slot the door needs (`slot_width`) runs past its wall's ends, or
        overlaps another opening on the same wall;
      * the wall is too low for the door (`required_size` height);
      * a solid volume, a stair's reserved rectangle, a ladder or another
        partition stands in the leaf's swing (`swing_rect`).
    WARN: a vault opening in a MODULAR spec with no `face` -- Zoo will build
    the round door, and nothing knows which side its leaf swings into.
    """
    fails, warns = [], []
    wt = _num(spec.get("wall_thick"), 0.3)
    modular = bool(spec.get("modular"))
    all_openings = wall_openings(spec, kinds=("door", "garage", "breach",
                                              "window", "vault", "teller",
                                              "safe_deposit"))
    for e in wall_openings(spec):
        op = e["op"]
        where = (f"story {e['story']} {e['host'].get('wall')} exterior wall"
                 if e["is_ext"] else
                 f"story {e['story']} {e['axis']}-partition at pos={e['line']:g}")
        label = op.get("tag") or "vault"
        geo = door_geometry(spec, e)
        face = op.get("face")
        if face is None:
            if modular:
                warns.append(f"L22 vault door '{label}' on the {where} has no "
                             f"face -- nothing says which side its leaf swings "
                             f"into, so nothing keeps that floor clear")
        elif face not in FACES_FOR_AXIS[e["axis"]]:
            fails.append(f"L22 vault door '{label}' on the {where} faces "
                         f"{face}; a wall along {e['axis']} faces "
                         f"{' or '.join(FACES_FOR_AXIS[e['axis']])}")
            continue
        half = geo["slot_w"] / 2.0
        # a perpendicular wall meeting this one at its end stands half a
        # thickness into the run
        s_lo, s_hi = e["along"] - half, e["along"] + half
        if s_lo < e["lo"] + wt / 2.0 - 1e-6 or s_hi > e["hi"] - wt / 2.0 + 1e-6:
            fails.append(f"L22 vault door '{label}' on the {where} needs a "
                         f"{geo['slot_w']:.2f} m slot ({s_lo:.2f}..{s_hi:.2f}) "
                         f"and the wall runs {e['lo']:.2f}..{e['hi']:.2f}")
        for other in all_openings:
            if other["op"] is op or other["host"] is not e["host"]:
                continue
            ow = float(other["op"].get("width") or 1.0)
            if other["op"].get("kind") == "vault":
                ap = resolved_aperture(other["op"])
                ow = slot_width(ap["width"], ap["height"], ap["sill"])
            if abs(other["along"] - e["along"]) < half + ow / 2.0 - 1e-6:
                fails.append(f"L22 vault door '{label}' on the {where}: its "
                             f"{geo['slot_w']:.2f} m slot overlaps the "
                             f"{other['op'].get('kind')} "
                             f"'{other['op'].get('tag') or ''}' at "
                             f"{other['along']:.2f}")
        if geo["need_h"] > geo["wall_h"] + 1e-6:
            fails.append(f"L22 vault door '{label}' on the {where} needs a "
                         f"{geo['need_h']:.2f} m wall and the wall is "
                         f"{geo['wall_h']:.2f} m")
        sw = geo["swing"]
        if sw is None:
            continue
        story = e["story"]
        zone = (f"its leaf's swing ({sw[0]:.2f}, {sw[1]:.2f})-({sw[2]:.2f}, "
                f"{sw[3]:.2f})")
        for v in spec.get("volumes") or []:
            if v.get("collision") == "none" or not _volume_on_story(spec, v, story):
                continue
            if _overlap(_volume_rect(v), sw):
                fails.append(f"L22 solid in a vault door's swing: "
                             f"'{v.get('name')}' stands in {zone} "
                             f"('{label}', {where})")
        for sid, rect in _stair_rects(spec, story):
            if _overlap(rect, sw):
                fails.append(f"L22 stair in a vault door's swing: '{sid}' "
                             f"reserves ({rect[0]:.2f}, {rect[1]:.2f})-"
                             f"({rect[2]:.2f}, {rect[3]:.2f}), inside {zone} "
                             f"('{label}', {where})")
        for lad in spec.get("ladders") or []:
            lo_s = min(lad.get("from_story", 0), lad.get("to_story", 0))
            hi_s = max(lad.get("from_story", 0), lad.get("to_story", 0))
            if lo_s <= story <= hi_s and _overlap(
                    (lad["x"] - 0.5, lad["y"] - 0.5, lad["x"] + 0.5,
                     lad["y"] + 0.5), sw):
                fails.append(f"L22 ladder in a vault door's swing at "
                             f"({lad['x']:g}, {lad['y']:g}), inside {zone}")
        for p in spec.get("partitions") or []:
            if p is e["host"] or int(p.get("story", 0)) != story:
                continue
            if _overlap(_wall_strip(spec, p), sw):
                fails.append(f"L22 wall in a vault door's swing: the "
                             f"{p.get('axis')}-partition at pos={p.get('pos')} "
                             f"crosses {zone} ('{label}', {where})")
    return fails, warns


# ---------------------------------------------------------------- generator
#: A vault VOLUME: a solid a body could stand inside, named a vault. The
#: library's walk-in vaults are 5 x 5 x 3 m; `basement_vault_block` (1.3 m),
#: `vault_safe_block` (1.7 m) and `vault_block` (1.4 m) are safes to crouch
#: behind, and `VAULT_DOOR` is a door. Measured 2026-09-13 over specs/ and
#: presets: 4 specs and the `bank` preset match.
VAULT_MIN_HEIGHT = 2.0
VAULT_MIN_SIDE = 3.0
#: The room stands this far past the vault box's edges.
PAD = 0.5
#: The longest side a vault room is given. The three library banks need 8 m
#: to reach their host room's corner from a 5 m box; past this a vault is a
#: hall, and the box's placement is not worth following further.
MAX_SIDE = 9.0
#: layout_lint.LEAF_MARGIN: a door leaf and jamb past the aperture.
LEAF_MARGIN = 0.3
#: `agent_contract.min_door_width_m`.
DOOR_WIDTH = 1.25
SAFE_DEPOSIT_WIDTH = 2.0
#: `spec_types.Opening.resolved`'s breach width.
BREACH_WIDTH = 1.5
#: Floor a body needs in front of a door (layout_lint.DOOR_APPROACH_M:
#: 2 x player radius + 0.3).
APPROACH = 1.0

_GENERATED = (re.compile(r"_r[0-9a-f]{8}_\d+(_\d+)?$"),
              re.compile(r"_shelter$"))


def is_vault_volume(v):
    tokens = str(v.get("name") or "").lower().split("_")
    if "vault" not in tokens or "door" in tokens:
        return False
    return (float(v.get("size_z", 0.0)) >= VAULT_MIN_HEIGHT
            and min(float(v.get("size_x", 0.0)),
                    float(v.get("size_y", 0.0))) >= VAULT_MIN_SIDE)


def is_generated(v, spec):
    """A volume `furnish` or `seed_cover` placed (and so may be moved), as
    against one an author placed (which the generator must not move)."""
    name = str(v.get("name") or "")
    if any(rx.search(name) for rx in _GENERATED):
        return True
    for r in spec.get("rooms") or []:
        rid = str(r.get("id", ""))
        if rid and re.search(r"_%s_\d+$" % re.escape(rid), name):
            return True
    return False


def _room_containing(spec, story, x, y):
    best, area = None, None
    for r in spec.get("rooms") or []:
        if int(r.get("story", 0)) != story or not r.get("bounds"):
            continue
        x0, y0, x1, y1 = r["bounds"]
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            a = (x1 - x0) * (y1 - y0)
            if area is None or a < area:
                best, area = r, a
    return best


def _host_wall(spec, story, axis, line, lo, hi):
    """The wall standing on `line` across lo..hi on `story`: ``("ext", wall
    dict or None)`` for the envelope, ``("part", partition)``, or None."""
    fx, fy = float(spec["footprint_x"]), float(spec["footprint_y"])
    edge = {"X": {fy / 2.0: "N", -fy / 2.0: "S"},
            "Y": {fx / 2.0: "E", -fx / 2.0: "W"}}[axis]
    for val, face in edge.items():
        if abs(line - val) < 0.2:
            wall = next((w for w in spec.get("ext_walls") or []
                         if w.get("wall") == face and int(w.get("story", 0)) == story),
                        None)
            return ("ext", wall, face)
    for p in spec.get("partitions") or []:
        if int(p.get("story", 0)) != story or str(p.get("axis")).upper() != axis:
            continue
        if abs(float(p.get("pos", 0.0)) - line) > 0.05:
            continue
        s, e = sorted((float(p.get("start", -1e9)), float(p.get("end", 1e9))))
        if s <= lo + 1e-6 and e >= hi - 1e-6:
            return ("part", p, None)
    return None


def _corner_rooms(spec, host, box, slot_w):
    """Candidate vault rooms in each corner of `host`, nearest the box first:
    ``(rect, corner)``."""
    x0, y0, x1, y1 = host["bounds"]
    bx0, by0, bx1, by1 = box
    wt = _num(spec.get("wall_thick"), 0.3)
    g = _grid(spec)
    min_side = slot_w + 2.0 * (wt + LEAF_MARGIN)
    cx, cy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
    out = []
    for kx in (0, 1):
        for ky in (0, 1):
            ax = (x0, x1)[kx]
            ay = (y0, y1)[ky]
            wx = abs(ax - ((bx1 + PAD) if kx == 0 else (bx0 - PAD)))
            wy = abs(ay - ((by1 + PAD) if ky == 0 else (by0 - PAD)))
            wx = math.ceil(_clamp(wx, min_side, MAX_SIDE) / g - 1e-6) * g
            wy = math.ceil(_clamp(wy, min_side, MAX_SIDE) / g - 1e-6) * g
            if wx > (x1 - x0) - min_side or wy > (y1 - y0) - min_side:
                continue      # the room would leave no approach in the host
            rx = (ax, ax + wx) if kx == 0 else (ax - wx, ax)
            ry = (ay, ay + wy) if ky == 0 else (ay - wy, ay)
            rect = (rx[0], ry[0], rx[1], ry[1])
            out.append((math.hypot(ax - cx, ay - cy), rect, (kx, ky)))
    out.sort(key=lambda t: t[0])
    return [(r, c) for _d, r, c in out]


def _relocate(spec, entry, keep_out, g, others, swing):
    """A new `pos` for a door-like opening on a host wall that must leave
    `keep_out` (lo, hi along its wall), or None.

    Every grid position on the wall is a candidate, nearest first -- on the
    grid measured from the wall's centre, where the builder snaps it. One is
    refused when its aperture and leaf margin reach into `keep_out` or past
    the wall's ends, when it comes within a leaf margin of another opening on
    the wall (`others`: (along, width)), or when the floor a body needs in
    front of it on either side (`APPROACH` deep, the aperture wide) overlaps
    the vault door's `swing`."""
    op = entry["op"]
    w = float(op.get("width") or DOOR_WIDTH)
    wt = _num(spec.get("wall_thick"), 0.3)
    lo, hi = entry["lo"], entry["hi"]
    run = hi - lo
    mid = (lo + hi) / 2.0
    need = w / 2.0 + LEAF_MARGIN + wt / 2.0
    n = int(run / g) + 1
    cands = [mid + i * g for i in range(-n, n + 1)]
    cands.sort(key=lambda a: (abs(a - entry["along"]), a))
    for along in cands:
        if along < lo + need or along > hi - need:
            continue
        if keep_out[0] - need < along < keep_out[1] + need:
            continue
        if any(abs(along - oa) < w / 2.0 + ow / 2.0 + LEAF_MARGIN
               for oa, ow in others):
            continue
        a0, a1 = along - w / 2.0, along + w / 2.0
        d0, d1 = entry["line"] - wt / 2.0 - APPROACH, entry["line"] + wt / 2.0 + APPROACH
        front = (a0, d0, a1, d1) if entry["axis"] == "X" else (d0, a0, d1, a1)
        if _overlap(front, swing):
            continue
        return round((along - mid) / run, 6), along
    return None


def enclose_vaults(spec):
    """Turn every vault VOLUME into a vault ROOM. In place; idempotent (the
    volume is gone afterwards). Returns ``[report]`` per vault volume:
    ``{"volume", "enclosed", "why", "room", "moved", "added", "evicted"}``.

    For a vault box on storey s in host room R (the innermost room holding
    its centre), each corner of R is tried, nearest the box first:

    * THE ROOM runs from the corner past the box's far edges by `PAD`, each
      side clamped to [slot + 2 (wall + leaf margin), `MAX_SIDE`] and rounded
      up to the grid, leaving at least that much of R beside it.
    * ITS WALLS: R's two walls at the corner (the envelope or a partition
      spanning the room's side -- a corner with no wall there is refused),
      and two new partitions closing the other two sides.
    * THE DOOR goes in the new wall with the most of R in front of it, at the
      wall's centre, `face` toward R, the aperture `APERTURE`, the machine
      inferred (`vault_door`, locked). That floor must hold the swing and
      `APPROACH` beyond it.
    * DEPOSIT BOXES: a `safe_deposit` opening, `face` into the vault, centred
      on every partition side but the door's.
    * The corner is refused when a stair's reserved rectangle, a ladder, an
      authored solid or another partition stands in the room, the new walls
      or the swing, or when a doorway on R's walls inside the room cannot be
      slid clear. Furniture and cover the generator placed are evicted
      instead (named in the report).

    The box goes. Objectives whose id names the vault, or that stood in the
    box, move to the door's face, in R; loot likewise moves into the vault
    room; markers that stood in the box move to the door's face.
    """
    report = []
    if not spec.get("footprint_x") or not spec.get("footprint_y"):
        return report
    H = _num(spec.get("story_height"), 3.0)
    g = _grid(spec)
    vaults = [v for v in spec.get("volumes") or [] if is_vault_volume(v)]
    for k, vol in enumerate(vaults):
        entry = {"volume": vol.get("name"), "enclosed": False, "why": "",
                 "room": None, "moved": [], "added": [], "evicted": []}
        report.append(entry)
        story = int(round((vol["z"] - vol["size_z"] / 2.0) / H))
        host = _room_containing(spec, story, vol["x"], vol["y"])
        if host is None:
            entry["why"] = "no room holds the vault"
            continue
        box = _volume_rect(vol)
        ap = dict(APERTURE)
        sw = slot_width(ap["width"], ap["height"], ap["sill"])
        wh = wall_height(spec, story)
        need_h = required_size(ap["width"], ap["height"], ap["sill"])["height"]
        if need_h > wh + 1e-6:
            entry["why"] = (f"the storey's walls are {wh:.2f} m and the door "
                            f"needs {need_h:.2f} m")
            continue
        why = []
        plan_ok = None
        for rect, corner in _corner_rooms(spec, host, box, sw):
            result = _try_corner(spec, story, host, vol, rect, corner, sw, wh, g)
            if isinstance(result, str):
                why.append(result)
                continue
            plan_ok = result
            break
        if plan_ok is None:
            entry["why"] = "; ".join(why) or "the host room has no corner that fits"
            continue
        _apply_plan(spec, story, host, vol, plan_ok, entry, k, H)
    return report


def _try_corner(spec, story, host, vol, rect, corner, sw, wh, g):
    """A plan dict for one corner, or the reason it is refused."""
    wt = _num(spec.get("wall_thick"), 0.3)
    hx0, hy0, hx1, hy1 = host["bounds"]
    rx0, ry0, rx1, ry1 = rect
    tag = "corner (%g, %g)" % ((hx0, hx1)[corner[0]], (hy0, hy1)[corner[1]])
    # the room's four sides: which are the host's, which are new
    sides = []
    for axis, line, lo, hi, host_line in (
            ("Y", rx0, ry0, ry1, hx0), ("Y", rx1, ry0, ry1, hx1),
            ("X", ry0, rx0, rx1, hy0), ("X", ry1, rx0, rx1, hy1)):
        if abs(line - host_line) < 1e-6:
            wall = _host_wall(spec, story, axis, line, lo, hi)
            if wall is None:
                return f"{tag}: no wall on the host room's side at {axis}={line:g}"
            sides.append({"axis": axis, "line": line, "lo": lo, "hi": hi,
                          "new": False, "wall": wall})
        else:
            sides.append({"axis": axis, "line": line, "lo": lo, "hi": hi,
                          "new": True, "wall": None})
    new = [s for s in sides if s["new"]]
    if not new:
        return f"{tag}: the room would fill its host"
    # the door: the new side with the most host room in front of it
    for s in new:
        if s["axis"] == "Y":
            out_dir = -1 if abs(s["line"] - rx0) < 1e-6 else 1
            s["depth"] = (s["line"] - hx0) if out_dir < 0 else (hx1 - s["line"])
            s["face"] = "W" if out_dir < 0 else "E"
        else:
            out_dir = -1 if abs(s["line"] - ry0) < 1e-6 else 1
            s["depth"] = (s["line"] - hy0) if out_dir < 0 else (hy1 - s["line"])
            s["face"] = "S" if out_dir < 0 else "N"
    door = max(new, key=lambda s: (s["depth"], s["axis"] == "X"))
    # the new wall's own centre: the builder snaps an opening's offset from its
    # piece's centre, so `pos` 0 lands exactly here whatever the grid
    along = (door["lo"] + door["hi"]) / 2.0
    dx, dy = ((along, door["line"]) if door["axis"] == "X"
              else (door["line"], along))
    swing = swing_rect(dx, dy, door["face"], sw, wt, wh, APERTURE)
    front = (swing[3] - dy if door["face"] == "N" else
             dy - swing[1] if door["face"] == "S" else
             swing[2] - dx if door["face"] == "E" else dx - swing[0])
    if door["depth"] < front + APPROACH:
        return (f"{tag}: {door['depth']:.2f} m in front of the door, the "
                f"swing and its approach need {front + APPROACH:.2f} m")
    if (swing[0] < hx0 + wt / 2.0 - 1e-6 or swing[2] > hx1 - wt / 2.0 + 1e-6
            or swing[1] < hy0 + wt / 2.0 - 1e-6 or swing[3] > hy1 - wt / 2.0 + 1e-6):
        return f"{tag}: the leaf's swing leaves the host room"
    # what the plan occupies: the room, the new walls, the swing
    strips = []
    for s in new:
        if s["axis"] == "X":
            strips.append((s["lo"], s["line"] - wt / 2.0 - 0.1,
                           s["hi"], s["line"] + wt / 2.0 + 0.1))
        else:
            strips.append((s["line"] - wt / 2.0 - 0.1, s["lo"],
                           s["line"] + wt / 2.0 + 0.1, s["hi"]))
    zones = [rect, swing] + strips
    for sid, srect in _stair_rects(spec, story):
        grown = (srect[0] - 0.3, srect[1] - 0.3, srect[2] + 0.3, srect[3] + 0.3)
        if any(_overlap(grown, z) for z in zones):
            return f"{tag}: stair '{sid}' stands where the vault would"
    for lad in spec.get("ladders") or []:
        lo_s = min(lad.get("from_story", 0), lad.get("to_story", 0))
        hi_s = max(lad.get("from_story", 0), lad.get("to_story", 0))
        pt = (lad["x"] - 1.0, lad["y"] - 1.0, lad["x"] + 1.0, lad["y"] + 1.0)
        if lo_s <= story <= hi_s and any(_overlap(pt, z) for z in zones):
            return f"{tag}: a ladder stands where the vault would"
    evict = []
    for v in spec.get("volumes") or []:
        if v is vol or v.get("collision") == "none":
            continue
        if not _volume_on_story(spec, v, story):
            continue
        vr = _volume_rect(v)
        crossing = any(_overlap(vr, z) for z in [swing] + strips)
        if not crossing:
            continue
        if is_generated(v, spec):
            evict.append(v)
        else:
            return f"{tag}: '{v.get('name')}' stands where a vault wall or its swing would"
    inner = (rx0 + wt, ry0 + wt, rx1 - wt, ry1 - wt)
    for p in spec.get("partitions") or []:
        if int(p.get("story", 0)) != story:
            continue
        strip = _wall_strip(spec, p)
        is_side = any(s["wall"] and s["wall"][0] == "part" and s["wall"][1] is p
                      for s in sides)
        if (not is_side and _overlap(strip, inner)) or _overlap(strip, swing):
            return (f"{tag}: the {p.get('axis')}-partition at pos={p.get('pos')} "
                    f"crosses the vault or its swing")
    # doorways on the host's walls inside the room's side move out of it
    moves = []
    for s in sides:
        if s["new"] or s["wall"][0] != "part":
            if not s["new"] and s["wall"][0] == "ext" and s["wall"][1]:
                for e in wall_openings({**spec, "partitions": [],
                                        "ext_walls": [s["wall"][1]]},
                                       kinds=("door", "garage", "breach",
                                              "window")):
                    w = float(e["op"].get("width") or 1.0)
                    if s["lo"] - w / 2.0 < e["along"] < s["hi"] + w / 2.0:
                        return (f"{tag}: the {s['wall'][2]} exterior wall has "
                                f"an opening inside the vault")
            continue
        part = s["wall"][1]
        ents = [e for e in wall_openings({**spec, "partitions": [part],
                                          "ext_walls": []},
                                         kinds=("door", "garage", "breach",
                                                "window", "vault", "teller",
                                                "safe_deposit"))]
        for e in ents:
            w = float(e["op"].get("width") or 1.0)
            keep = (s["lo"] - wt / 2.0, s["hi"] + wt / 2.0)
            if not (keep[0] - w / 2.0 - LEAF_MARGIN < e["along"]
                    < keep[1] + w / 2.0 + LEAF_MARGIN):
                continue
            others = [(o["along"], float(o["op"].get("width") or 1.0))
                      for o in ents if o is not e]
            got = _relocate(spec, e, keep, g, others, swing)
            if got is None:
                return (f"{tag}: the {e['op'].get('kind')} at {e['along']:.2f} "
                        f"on the {s['axis']}-partition at pos={s['line']:g} "
                        f"is inside the vault and cannot be slid clear")
            moves.append((e["op"], got[0], e["along"], got[1], s))
    breach = _plan_breach(spec, story, host, vol, sides, door, swing, moves,
                          evict, g)
    if isinstance(breach, str):
        return f"{tag}: {breach}"
    return {"rect": rect, "sides": sides, "door": door, "along": along,
            "door_xy": (dx, dy), "swing": swing, "evict": evict,
            "moves": moves, "wh": wh, "slot_w": sw, "breach": breach}


def _plan_breach(spec, story, host, vol, sides, door, swing, moves, evict, g):
    """The vault's SECOND WAY IN: a reinforceable breach on a partition side
    other than the door's, as ``(side, along)``, or the reason there is none.

    `tactical` requires two access paths into an objective room, and a vault
    with one door is a one-approach siege -- the same reason this bank's
    basement already has a breach beside its door. A side whose far room is
    not the room the door opens on is preferred (a route the door's approach
    does not share), then the longer side. Positions go nearest the side's
    centre first, on the grid from the partition's centre, clear of the side's
    ends, every other opening on the wall (as moved), the swing, stairs, and
    authored solids in the floor a body needs either side; furniture there is
    evicted."""
    wt = _num(spec.get("wall_thick"), 0.3)
    half = BREACH_WIDTH / 2.0
    rx0 = min(x["line"] for x in sides if x["axis"] == "Y")
    ry0 = min(x["line"] for x in sides if x["axis"] == "X")
    cands = []
    for sd in sides:
        if sd is door:
            continue
        if not sd["new"] and sd["wall"][0] != "part":
            continue                  # the envelope: no room beyond it
        mx = (sd["lo"] + sd["hi"]) / 2.0
        if sd["axis"] == "Y":
            out = -1 if abs(sd["line"] - rx0) < 1e-6 else 1
            beyond = _room_containing(spec, story, sd["line"] + out * 0.6, mx)
        else:
            out = -1 if abs(sd["line"] - ry0) < 1e-6 else 1
            beyond = _room_containing(spec, story, mx, sd["line"] + out * 0.6)
        if beyond is None:
            continue
        other = beyond is not host
        cands.append((not other, -(sd["hi"] - sd["lo"]), sd))
    cands.sort(key=lambda c: (c[0], c[1]))
    moved = {id(op): now for op, _pos, _was, now, _s in moves}
    stairs = _stair_rects(spec, story)
    for _o, _l, sd in cands:
        if sd["new"]:
            p_lo, p_hi = sd["lo"], sd["hi"]
            taken = []
        else:
            part = sd["wall"][1]
            ents = wall_openings({**spec, "partitions": [part], "ext_walls": []},
                                 kinds=("door", "garage", "breach", "window",
                                        "vault", "teller", "safe_deposit"))
            b = _wall_strip(spec, part)
            p_lo, p_hi = ((b[1], b[3]) if sd["axis"] == "Y" else (b[0], b[2]))
            taken = [(moved.get(id(e["op"]), e["along"]),
                      float(e["op"].get("width") or 1.0)) for e in ents]
        mid = (p_lo + p_hi) / 2.0
        centre = (sd["lo"] + sd["hi"]) / 2.0
        n = int((sd["hi"] - sd["lo"]) / g) + 1
        spots = sorted({mid + round((centre - mid) / g + i) * g
                        for i in range(-n, n + 1)},
                       key=lambda a: (abs(a - centre), a))
        for along in spots:
            if (along - half < sd["lo"] + wt / 2.0 + LEAF_MARGIN
                    or along + half > sd["hi"] - wt / 2.0 - LEAF_MARGIN):
                continue
            if any(abs(along - ta) < half + tw / 2.0 + LEAF_MARGIN
                   for ta, tw in taken):
                continue
            d0 = sd["line"] - wt / 2.0 - APPROACH
            d1 = sd["line"] + wt / 2.0 + APPROACH
            front = ((along - half, d0, along + half, d1) if sd["axis"] == "X"
                     else (d0, along - half, d1, along + half))
            if _overlap(front, swing):
                continue
            if any(_overlap((r[0] - 0.3, r[1] - 0.3, r[2] + 0.3, r[3] + 0.3),
                            front) for _sid, r in stairs):
                continue
            blocked = False
            extra = []
            for v in spec.get("volumes") or []:
                if (v is vol or v.get("collision") == "none"
                        or any(v is x for x in evict)):
                    continue
                if not _volume_on_story(spec, v, story):
                    continue
                if _overlap(_volume_rect(v), front):
                    if is_generated(v, spec):
                        extra.append(v)
                    else:
                        blocked = True
            if blocked:
                continue
            evict.extend(extra)
            return (sd, along)
    return "no partition side of the vault holds a second way in"


def _apply_plan(spec, story, host, vol, pl, entry, k, H):
    wt = _num(spec.get("wall_thick"), 0.3)
    g = _grid(spec)
    rx0, ry0, rx1, ry1 = pl["rect"]
    material = "concrete" if any(m.get("id") == "concrete"
                                 for m in spec.get("materials") or []) \
        else spec.get("default_material")
    rid = "vault" if not any(r.get("id") == "vault"
                             for r in spec.get("rooms") or []) else f"vault_{k}"
    evicted = {id(v) for v in pl["evict"]}
    names = {v.get("name") for v in pl["evict"]}
    spec["volumes"] = [v for v in spec.get("volumes") or []
                       if v is not vol and id(v) not in evicted]
    spec["markers"] = [m for m in spec.get("markers") or []
                       if (m.get("meta") or {}).get("from") not in names]
    entry["evicted"] = sorted(n for n in names if n)
    for op, pos, was, now, s in pl["moves"]:
        op["pos"] = pos
        entry["moved"].append(f"{op.get('kind')} '{op.get('tag') or ''}' on the "
                              f"{s['axis']}-partition at pos={s['line']:g}: "
                              f"{was:.2f} -> {now:.2f}")
    door = pl["door"]
    for s in pl["sides"]:
        openings = []
        if s is door:
            openings.append({"kind": "vault", "pos": 0.0,
                             "width": APERTURE["width"],
                             "height": APERTURE["height"],
                             "sill": APERTURE["sill"], "face": door["face"],
                             "tag": f"vault_door_{k}", "material": "metal"})
        if s["new"]:
            part = {"story": story, "axis": s["axis"], "pos": round(s["line"], 3),
                    "start": round(s["lo"], 3), "end": round(s["hi"], 3),
                    "openings": openings}
            if material:
                part["material"] = material
            spec.setdefault("partitions", []).append(part)
            s["part"] = part
        elif s["wall"][0] == "part":
            s["part"] = s["wall"][1]
        else:
            s["part"] = None
    # the second way in (planned in `_plan_breach`)
    b_side, b_along = pl["breach"]
    b_part = b_side["part"]
    bp_lo, bp_hi = sorted((float(b_part["start"]), float(b_part["end"])))
    b_part.setdefault("openings", []).append(
        {"kind": "breach", "pos": round((b_along - (bp_lo + bp_hi) / 2.0)
                                        / (bp_hi - bp_lo), 6),
         "width": BREACH_WIDTH, "breach_class": "reinforceable",
         "reinforceable": True,
         "material": b_part.get("material") or material,
         "tag": f"vault_breach_{k}"})
    entry["added"].append(f"breach into the vault on the {b_side['axis']}-wall "
                          f"at {b_side['line']:g}, {b_along:.2f} along it")
    # deposit boxes on every partition side of the room but the door's, into
    # the vault: centred on the room's span of that wall when that is clear,
    # else the nearest clear grid position
    for s in pl["sides"]:
        part = s.get("part")
        if part is None or s is door:
            continue
        span = s["hi"] - s["lo"] - wt - 2.0 * LEAF_MARGIN
        width = min(SAFE_DEPOSIT_WIDTH, round(span, 2))
        if width < 0.6:
            continue
        p_lo, p_hi = sorted((float(part["start"]), float(part["end"])))
        mid = (p_lo + p_hi) / 2.0
        centre = (s["lo"] + s["hi"]) / 2.0
        if s["axis"] == "Y":
            face = "E" if abs(s["line"] - rx0) < 1e-6 else "W"
        else:
            face = "N" if abs(s["line"] - ry0) < 1e-6 else "S"
        taken = [(e["along"], float(e["op"].get("width") or 1.0)) for e in
                 wall_openings({**spec, "partitions": [part], "ext_walls": []},
                               kinds=("door", "garage", "breach", "window",
                                      "vault", "teller", "safe_deposit"))]
        n = int((s["hi"] - s["lo"]) / g) + 1
        spots = sorted({mid + round((centre - mid) / g + i) * g
                        for i in range(-n, n + 1)},
                       key=lambda a: (abs(a - centre), a))
        for along in spots:
            if (along - width / 2.0 < s["lo"] + wt / 2.0 + LEAF_MARGIN
                    or along + width / 2.0 > s["hi"] - wt / 2.0 - LEAF_MARGIN):
                continue
            if any(abs(along - ta) < width / 2.0 + tw / 2.0 + LEAF_MARGIN
                   for ta, tw in taken):
                continue
            part.setdefault("openings", []).append(
                {"kind": "safe_deposit",
                 "pos": round((along - mid) / (p_hi - p_lo), 6),
                 "width": width, "face": face, "tag": f"deposit_boxes_{k}",
                 "material": "metal"})
            break
    room = {"id": rid, "story": story,
            "bounds": [round(rx0, 3), round(ry0, 3), round(rx1, 3), round(ry1, 3)],
            "role": "objective_room", "objective": True, "fortifiable": True}
    spec.setdefault("rooms", []).append(room)
    # objectives, loot and markers follow the vault
    dx, dy = pl["door_xy"]
    fx, fy = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}[door["face"]]
    ax_, ay_ = dx + fx * (wt / 2.0 + 0.6), dy + fy * (wt / 2.0 + 0.6)
    box = _volume_rect(vol)
    cx, cy = (rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0

    def _in_box(o):
        return (o.get("x") is not None and box[0] <= o["x"] <= box[2]
                and box[1] <= o["y"] <= box[3])

    for o in spec.get("objectives") or []:
        if "vault" in str(o.get("id", "")).lower() or _in_box(o):
            o.update({"x": round(ax_, 3), "y": round(ay_, 3),
                      "z": round(story * H + 0.5, 3), "room": host["id"]})
            entry["moved"].append(f"objective '{o.get('id')}' to the vault door")
    for o in spec.get("loot") or []:
        if "vault" in str(o.get("id", "")).lower() or _in_box(o):
            o.update({"x": round(cx, 3), "y": round(cy, 3),
                      "z": round(story * H + 0.5, 3), "room": rid})
            entry["moved"].append(f"loot '{o.get('id')}' into the vault")
    for m in spec.get("markers") or []:
        if _in_box(m) and m.get("type") not in ("cover_high", "cover_low", "landmark"):
            m.update({"x": round(ax_, 3), "y": round(ay_, 3),
                      "z": round(story * H, 3), "room": host["id"]})
            entry["moved"].append(f"marker {m.get('type')} to the vault door")
    entry["room"] = rid
    entry["enclosed"] = True
    entry["why"] = (f"{rx1 - rx0:g} x {ry1 - ry0:g} m room, door facing "
                    f"{door['face']} on the {door['axis']}-wall at "
                    f"{door['line']:g}")
