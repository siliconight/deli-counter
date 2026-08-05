"""Prop-vs-circulation gate (pure, bpy-free).

A dressed building must keep its CIRCULATION clear: the player has to be able
to mount every ladder, pass every doorway, and walk every stair without a
prop parked in the way. Patina places dressing against walls and clutter
zones; nothing in that placement pass knows about climb volumes or apertures,
so this module is the contract that catches the overlap before it ships.

Three volume families, all derived from data DC already exports (no new
schema):

- LADDER climb volumes -- from gameplay ``markers`` of type ``ladder``
  (x, y, z, climb_height, width, facing). The volume matches the climb
  contract Area3D that portable_building bakes (width + catch margin, climb
  height + mount headroom, protruding onto the approach side): a prop inside
  it either blocks the mount or dead-stops the climb.
- DOORWAY apertures -- from ``slots`` with role ``doorway``: the aperture
  (openings[0] width x height above sill) extended ``DOOR_CLEARANCE`` out on
  BOTH sides of the wall, because a crate hard against either face of an
  open door blocks passage just as surely as one inside the frame.
- STAIR footprints -- from gameplay ``stair_systems`` ``footprint_polygon``
  (the reserved rect stairwell.py derives). The whole vertical column over a
  stair footprint is reserved circulation: a prop at ANY height inside the
  shaft is wrong (on a flight, on a landing, or floating in the well), so the
  volume is the rect extruded over the full z range under test.

Everything is computed in spec/Blender Z-up space (the space slots.json and
gameplay.json are written in); ``to_godot_aabb`` converts a volume to the
GLB/Godot Y-up space that dressing-GLB node boxes live in
((x, y, z) -> (x, z, -y), the same mapping tscn_export uses).

Consumed by portable_building.build_package (package gate, manifest key
``circulation_check``), Level Factory's compose driver (hard gate, rc 6) and
the unit tests -- one source of truth, per the guardrail pattern.

TWO INPUTS, NOT ONE. An earlier version of this docstring said "the conflict
only exists once a dressing GLB exists, so this is a package-time gate by
nature". That is false, and it cost a shipped defect: DC places its OWN props
-- vaults, teller counters, desks, cabinets, crate stacks -- into the same
space, before any dressing exists, and nothing tested them. Measured on
``art_probe_001`` seed 5017: ``VAULT`` (5.00 x 3.00 x 5.00 m) sits **1.6 m**
inside the reserved column of ``stair_1``, overlapping 15 consecutive treads
across the full 1.60 m stair width. The rule below already forbade it in
as many words, ``prop_conflicts`` already detected it on the first run, and
``check_dressing`` was simply never handed DC's own geometry.

So there are two entry points and they share everything but the box source:
:func:`check_dressing` for Patina's output and :func:`check_shell` for DC's
own greybox. A prop is a prop whoever placed it.
"""
from __future__ import annotations

# climb-contract box (mirrors portable_building._ladder_climb_nodes)
LADDER_CATCH_MARGIN = 0.6    # extra clear width across the ladder
LADDER_HEADROOM = 1.0        # mount headroom above the climb height
LADDER_DEPTH = 0.8           # how far the climb volume protrudes
LADDER_STANDOFF = 0.05       # volume starts just off the ladder face

DOOR_CLEARANCE = 0.6         # clear approach depth on each side of a doorway

PEN_MIN = 0.02               # ignore < 2 cm grazes (bevels, skirting overlap)

# Doorways get a deeper tolerance: Patina legitimately dresses the aperture
# PERIMETER (door frames, pilasters, lintel trim), and an AABB around a
# U-shaped frame covers the whole aperture even though its geometry only hugs
# the edges. Trim is thin along the wall normal, so its min-axis penetration
# stays at frame depth (<= ~5 cm measured on real builds); a free-standing
# prop parked in the walk path penetrates far deeper. 12 cm cleanly separates
# the two populations.
DOOR_TRIM_PEN = 0.12

# facing -> outward (approach) unit vector in Blender XY, same convention as
# ladder_geom.APPROACH / stairwell facing.
APPROACH = {"N": (0.0, 1.0), "S": (0.0, -1.0),
            "E": (1.0, 0.0), "W": (-1.0, 0.0)}


def ladder_volume(marker):
    """Blender-space AABB of one ladder's climb volume, or None."""
    try:
        x = float(marker.get("x", 0.0))
        y = float(marker.get("y", 0.0))
        z = float(marker.get("z", 0.0))
        h = float(marker.get("climb_height", 3.0))
        w = float(marker.get("width", 0.5))
    except (TypeError, ValueError):
        return None
    ax, ay = APPROACH.get(marker.get("facing", "S"), APPROACH["S"])
    half_across = w / 2 + LADDER_CATCH_MARGIN / 2
    lo_out, hi_out = LADDER_STANDOFF, LADDER_STANDOFF + LADDER_DEPTH
    if ax:  # approach along X; across is Y
        xs = sorted((x + ax * lo_out, x + ax * hi_out))
        lo = [xs[0], y - half_across, z - 0.5]
        hi = [xs[1], y + half_across, z + h + LADDER_HEADROOM - 0.5]
    else:   # approach along Y; across is X
        ys = sorted((y + ay * lo_out, y + ay * hi_out))
        lo = [x - half_across, ys[0], z - 0.5]
        hi = [x + half_across, ys[1], z + h + LADDER_HEADROOM - 0.5]
    return lo, hi


def doorway_volume(slot, clearance=DOOR_CLEARANCE):
    """Blender-space AABB of a doorway slot's walk-through volume, or None.

    The aperture (width x height above sill) extended ``clearance`` past BOTH
    wall faces. Falls back to the full slot box when the slot carries no
    aperture record (older manifests).
    """
    if slot.get("role") != "doorway":
        return None
    tr = (slot.get("transform") or {})
    t = tr.get("translation") or [0.0, 0.0, 0.0]
    rot = int(round(float(tr.get("rot_y") or 0.0))) % 360
    dims = ((slot.get("fit") or {}).get("dims")) or [1.0, 0.2, 2.0]
    w, thick, seg_h = float(dims[0]), float(dims[1]), float(dims[2])
    ops = ((slot.get("fit") or {}).get("openings")) or []
    if ops:
        ap = ops[0]
        w = float(ap.get("width", w))
        ap_h = float(ap.get("height", seg_h))
        sill = float(ap.get("sill", 0.0))
    else:
        ap_h, sill = seg_h, 0.0
    z_lo = t[2] - seg_h / 2 + sill
    z_hi = z_lo + ap_h
    half_w = w / 2
    half_n = thick / 2 + clearance
    # rot_y 0/180: wall runs along X, normal along Y; 90/270: swapped.
    if rot in (90, 270):
        lo = [t[0] - half_n, t[1] - half_w, z_lo]
        hi = [t[0] + half_n, t[1] + half_w, z_hi]
    else:
        lo = [t[0] - half_w, t[1] - half_n, z_lo]
        hi = [t[0] + half_w, t[1] + half_n, z_hi]
    return lo, hi


def stair_volume(system, z_lo=-1e6, z_hi=1e6):
    """Blender-space AABB over a stair system's reserved footprint, or None.

    The full vertical column: a prop at any height inside the shaft blocks a
    flight, a landing, or the well. Callers clamp z to the range under test.
    """
    poly = system.get("footprint_polygon")
    if not poly:
        return None
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return [min(xs), min(ys), z_lo], [max(xs), max(ys), z_hi]


def circulation_volumes(slots_manifest, gameplay):
    """All named circulation volumes for a build, in Blender space.

    Returns ``[(name, (lo, hi))]``. Sources: gameplay ladder markers, doorway
    slots, gameplay stair systems. Missing sections contribute nothing (the
    gate degrades gracefully on partial inputs).
    """
    vols = []
    for m in ((gameplay or {}).get("markers") or []):
        if m.get("type") != "ladder":
            continue
        v = ladder_volume(m)
        if v:
            vols.append((f"ladder:{m.get('id') or m.get('name')}", v))
    for s in ((slots_manifest or {}).get("slots") or []):
        v = doorway_volume(s)
        if v:
            vols.append((f"doorway:{s.get('slot_id')}", v))
    for st in ((gameplay or {}).get("stair_systems") or []):
        v = stair_volume(st)
        if v:
            vols.append((f"stair:{st.get('id')}", v))
    return vols


def to_godot_aabb(vol):
    """Blender Z-up AABB -> GLB/Godot Y-up AABB ((x, y, z) -> (x, z, -y))."""
    lo, hi = vol
    return ([lo[0], lo[2], -hi[1]], [hi[0], hi[2], -lo[1]])


def _pen(a, b):
    """Minimum axis penetration depth of two AABBs, <= 0 when separated."""
    return min(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) for i in range(3))


def prop_conflicts(prop_boxes, volumes, pen_min=PEN_MIN):
    """Which props intrude into which circulation volumes.

    ``prop_boxes``: [(name, (lo, hi))] in GLB/Godot space (as produced by
    zfight_gate._node_world_boxes on a dressing GLB).
    ``volumes``: [(name, (lo, hi))] in Blender space (circulation_volumes).

    Returns [{prop, volume, penetration}] -- penetration is the smallest-axis
    overlap depth in metres, i.e. how far the prop must move to clear.
    Doorway volumes use the deeper ``DOOR_TRIM_PEN`` threshold (aperture
    trim is legal dressing); everything else uses ``pen_min``.
    """
    out = []
    gvols = [(name, to_godot_aabb(v),
              max(pen_min, DOOR_TRIM_PEN) if name.startswith("doorway:")
              else pen_min)
             for name, v in volumes]
    for pname, pbox in prop_boxes:
        for vname, vbox, thresh in gvols:
            p = _pen(pbox, vbox)
            if p > thresh:
                out.append({"prop": pname, "volume": vname,
                            "penetration": round(p, 4)})
    return out


def shell_prop_boxes(shell_glb, gameplay):
    """DC's own props out of its own greybox GLB, in GLB/Godot space.

    Selected by DECLARED ROLE, not by a name pattern: ``gameplay.surface_roles``
    names every node DC built and what it is, so ``role == "prop"`` is
    authoritative and survives a prop being called something new. A regex over
    node names would have to guess at the naming convention and would rot.

    ``zfight_gate._node_world_boxes`` already skips ``*colonly`` nodes, so what
    comes back is the visual geometry a player sees and walks into.
    """
    import zfight_gate
    roles = (gameplay or {}).get("surface_roles") or {}
    props = {n for n, r in roles.items() if r == "prop"}
    if not props:
        return []
    return [(n, b) for n, b in zfight_gate._node_world_boxes(shell_glb)
            if n in props]


def check_shell(shell_glb, slots_manifest, gameplay):
    """Spec-time gate: does DC's OWN greybox keep its own circulation clear?

    Same volumes and same comparison as :func:`check_dressing` -- only the box
    source differs. This is the half that was missing: a vault parked in a
    stairwell is not a dressing problem, it is a layout problem, and it exists
    the moment DC writes the shell.

    Returns ``{ok, volumes, props, conflicts:[{prop, volume, penetration}]}``.
    ``props: 0`` means no node declared ``role == "prop"`` -- say that out loud
    rather than reporting ``ok``, because a gate with no input is not a pass.
    """
    props = shell_prop_boxes(shell_glb, gameplay)
    vols = circulation_volumes(slots_manifest, gameplay)
    conflicts = prop_conflicts(props, vols)
    return {"ok": not conflicts, "volumes": len(vols), "props": len(props),
            "conflicts": conflicts[:50]}


def check_dressing(dressing_glb, slots_manifest, gameplay):
    """Package-level gate: does a dressing GLB keep circulation clear?

    Returns {ok, volumes, props, conflicts:[{prop, volume, penetration}]}.
    Needs pygltflib (same dep the placement/z-fight gates already use).
    """
    import zfight_gate
    props = zfight_gate._node_world_boxes(dressing_glb)
    vols = circulation_volumes(slots_manifest, gameplay)
    conflicts = prop_conflicts(props, vols)
    return {"ok": not conflicts, "volumes": len(vols), "props": len(props),
            "conflicts": conflicts[:50]}
