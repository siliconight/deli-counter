"""ticket_queue.py -- a box office sells through a ticket window, and its queue stands in front of it (pure, no bpy).

The factory's roadmap 267. The walker, 2026-10-20, asked what arena_a02's four steel barricades on its event floor were
for, and answered "queue lanes to the box office"; then "stanchion or stanchions are likley more common for banks and
indoor common areas", "metal barriers are for outdoor concerts or riot protection from police", "retractable belt
stanchion", and a photo -- black posts on round bases, flat black belts taut at waist height, lanes switching back in
front of a desk. Zoo 1.119.0 draws one straight run of those stanchions, `stanchion_run`; this lays a queue of them.

THE RULE (`queue_box_offices`, run by `level_design.enrich` before cover and furniture, and by
`migrate_ticket_queue.py` over the library). A room whose id names a box office or a ticket office (`is_box_office`)
and that shares an interior wall with a public room (`is_public`: the role `public_entry`, or a lobby or a hall by its
words) gets:

  * A TICKET WINDOW in that wall -- a `window` opening tagged `ticket_window`, `WINDOW_W` wide over a counter's sill,
    sealed (no `breakable`: a pane that shot out would be a firing line into the room behind it), on the builder's
    grid so it is cut where the queue was laid for it.
  * A QUEUE in front of it, on the public side: `lanes` lanes, two or three, between lines of stanchion runs parallel to
    the wall, each line one `stanchion_run_<q>_<k>` volume. The lines stop a turn short at alternate ends, so the queue
    switches back: in at the end away from the window, out of the last lane at the window's end into the floor in front
    of the window. Nothing closes a lane's open end; a run is one straight slot (Zoo's species), and a corner post two
    runs shared would stand two posts in one place.

EVERY CLEARANCE IS THE CONTRACT'S (`agent_contract`):
  * a lane is a corridor to the nav bake, so its clear floor between two lines' slots is `stair_flight_width()` -- the
    corridor minimum and one bake cell, "a corridor AT the minimum keeps a strip whose joining depends on where the
    voxel grid falls" -- and a turn is as wide;
  * the floor in front of the window, wall to the first line, is `door_approach()`: what a body needs to use a door;
  * the queue keeps `min_corridor_width()` from every wall but its own, every standing volume, every stair's reserve,
    every hole in its floor and every vault's swing, so a body walks round it; and from every walkable opening's
    approach -- its span along its wall, `door_approach()` deep both sides -- so it never stands in a doorway's way.

THE NUMBERS ARE ZOO'S where they are a stanchion's: `RUN_DEPTH` and `RUN_HEIGHT`, `stanchion_run`'s genome defaults --
a 14 in base, a 38 in post. Retyped because Deli Counter builds without Zoo beside it; `test_ticket_queue.py` pins them
to the genome when the zoo repo is found next to this one, as `test_vault_room.py` pins the vault door's.

WHAT IT DOES NOT DO, said so it is not read as an oversight: a box office on an EXTERIOR wall -- a theatre's window on
the street -- is the street's queue, and the street is Lot's; this reports it and lays nothing. A bank's teller line
takes a queue the same way and does not get one yet (the factory's roadmap). A queue that cannot fit two lanes clear
of all of the above is not laid, and the report says why.
"""
from __future__ import annotations

import math

import agent_contract

# ------------------------------------------------------------ Zoo's numbers
#: `stanchion_run`'s genome defaults (Zoo 1.119.0): the run's slot is a base's diameter deep and a post's height tall.
RUN_DEPTH = 0.356
RUN_HEIGHT = 0.97
#: the species' own kind (the dartboard's rule, `level_design._PROP_MATERIALS`): its stem carries no `_m`
RUN_MATERIAL = "metal_painted"
RUN_ACOUSTIC = ("Metal", 0.25, 0.2)
#: `stanchion_run`'s genome range: a line shorter than this is not a run Zoo draws
RUN_MIN = 1.1

# ------------------------------------------------------------ the window
#: a box office's window, about 4 ft wide, at a counter's sill, its head at a door's
WINDOW_W = 1.2
WINDOW_SILL = 1.0
WINDOW_H = 1.1
#: what a window's jamb keeps from a wall's end or another opening (`layout_lint.LEAF_MARGIN`)
JAMB = 0.3

# ------------------------------------------------------------ the queue
LANES = (3, 2)
#: a queue's length along its wall: long enough that a line is a run of two belts, short of a stadium's
MAX_SPAN = 6.0
#: the steps a span is shortened by while it is fitted
SPAN_STEP = 0.1

#: words that name a room that sells tickets, as whole tokens of its id (`box` alone is a box room; with `office` it
#: is a box office)
_TICKET_TOKENS = frozenset(("ticket", "tickets", "ticketing", "boxoffice"))
_BOX_OFFICE = frozenset(("box", "office"))
_PUBLIC_ROLES = frozenset(("public_entry",))
_PUBLIC_KINDS = frozenset(("lobby", "hall"))
#: the openings a body walks through, whose approaches a queue keeps clear of
_WALKABLE = ("door", "garage", "breach", "vault")


def lane_clear():
    """The clear floor across a lane, between two lines' slots, and across a turn: a stair flight's width."""
    return agent_contract.stair_flight_width()


def pitch():
    """Line to line, centre to centre."""
    return lane_clear() + RUN_DEPTH


def service_depth():
    """The floor in front of the window, from the wall's face to the first line's slot."""
    return agent_contract.door_approach()


def line_min():
    """The shortest line beside its turn: as long as the lanes are wide, or a lane reads as a pen."""
    return pitch()


def is_box_office(room):
    tokens = set(str(room.get("id", "")).lower().replace("-", "_").split("_"))
    return bool(tokens & _TICKET_TOKENS) or _BOX_OFFICE <= tokens


def is_public(room, building=None):
    if str(room.get("role") or "").lower() in _PUBLIC_ROLES:
        return True
    import level_design
    return level_design._room_kind(room, building) in _PUBLIC_KINDS


def _box_gap(a, b):
    import level_design
    return level_design._box_gap(a, b)


def _opening_width(op):
    """An opening's width as the builder resolves it (`spec_types.Opening.resolved`)."""
    if op.get("width") is not None:
        return float(op["width"])
    if op.get("kind", "door") == "vault":
        import vault_room
        return float(vault_room.resolved_aperture(op)["width"])
    defaults = {"door": agent_contract.min_door_width(), "window": 1.6, "garage": 3.5, "breach": 1.5,
                "teller": 2.0, "safe_deposit": 2.0}
    return float(defaults.get(op.get("kind", "door"), 1.6))


def _walls(spec):
    """Every partition as ``(index, p, axis, line, lo, hi)``, its run as the builder stands it."""
    hx = float(spec.get("footprint_x") or 0.0) / 2.0
    hy = float(spec.get("footprint_y") or 0.0) / 2.0
    out = []
    for i, p in enumerate(spec.get("partitions") or []):
        ax = str(p.get("axis", "X")).upper()
        b = hx if ax == "X" else hy
        s = -b if p.get("start") is None else float(p["start"])
        e = b if p.get("end") is None else float(p["end"])
        out.append((i, p, ax, float(p.get("pos", 0.0)), min(s, e), max(s, e)))
    return out


def _shared_walls(spec, office):
    """The partitions between `office` and a public room on its storey: ``(wall, public room, side)``, `side` the
    direction (+1 / -1 on the wall's perpendicular axis) from the wall into the public room."""
    story = int(office.get("story", 0) or 0)
    building = __import__("level_design").club_building_id(spec)
    ox0, oy0, ox1, oy1 = office["bounds"]
    out = []
    for w in _walls(spec):
        _i, p, ax, line, lo, hi = w
        if int(p.get("story", 0) or 0) != story:
            continue
        # the office's edge on this wall's line, and which side of it the office is
        if ax == "X":
            o_lo, o_hi = ox0, ox1
            o_side = -1 if abs(oy1 - line) < 1e-6 else (1 if abs(oy0 - line) < 1e-6 else 0)
        else:
            o_lo, o_hi = oy0, oy1
            o_side = -1 if abs(ox1 - line) < 1e-6 else (1 if abs(ox0 - line) < 1e-6 else 0)
        if o_side == 0 or min(o_hi, hi) - max(o_lo, lo) < WINDOW_W + 2 * JAMB:
            continue
        for r in spec.get("rooms") or []:
            if r is office or int(r.get("story", 0) or 0) != story or not r.get("bounds"):
                continue
            rx0, ry0, rx1, ry1 = r["bounds"]
            if ax == "X":
                r_lo, r_hi = rx0, rx1
                r_side = 1 if abs(ry0 - line) < 1e-6 else (-1 if abs(ry1 - line) < 1e-6 else 0)
            else:
                r_lo, r_hi = ry0, ry1
                r_side = 1 if abs(rx0 - line) < 1e-6 else (-1 if abs(rx1 - line) < 1e-6 else 0)
            if r_side == 0 or r_side == o_side:
                continue
            if min(o_hi, r_hi, hi) - max(o_lo, r_lo, lo) < WINDOW_W + 2 * JAMB:
                continue
            if not is_public(r, building):
                continue
            out.append((w, r, r_side))
    return out


def _world(ax, line, face, side, u, v):
    """Wall-local (u along the wall, v from its face into the public room) to world plan (x, y)."""
    b = line + side * face + side * v
    return (u, b) if ax == "X" else (b, u)


def _rect(ax, line, face, side, u0, u1, v0, v1):
    x0, y0 = _world(ax, line, face, side, u0, v0)
    x1, y1 = _world(ax, line, face, side, u1, v1)
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _keepouts(spec, story, wall_index, room_rect):
    """What a queue on `story` keeps `min_corridor_width()` from, as plan boxes with a name: walls but the queue's
    own, walkable openings' approaches, standing volumes, stairs, holes, vaults' swings; and the points it keeps the
    same distance from: ladders, and markers on the floor. ONLY WHAT IS IN THE PUBLIC ROOM: each box clipped to
    `room_rect` and dropped when nothing of it is left, each point dropped outside it -- the office's furniture and the
    walls standing on the office's side of the shared wall are behind that wall, and a cabinet 0.6 m behind it would
    otherwise have refused every queue in front of it."""
    import level_design
    import vault_room
    sh = level_design._story_height(spec)
    floor = story * sh
    t = float(spec.get("wall_thick", 0.3) or 0.3)
    hx = float(spec.get("footprint_x") or 0.0) / 2.0
    hy = float(spec.get("footprint_y") or 0.0) / 2.0
    boxes = [("wall N", (-hx, hy - t / 2, hx, hy + t / 2)), ("wall S", (-hx, -hy - t / 2, hx, -hy + t / 2)),
             ("wall E", (hx - t / 2, -hy, hx + t / 2, hy)), ("wall W", (-hx - t / 2, -hy, -hx + t / 2, hy))]
    for i, p, ax, line, lo, hi in _walls(spec):
        if int(p.get("story", 0) or 0) != story or i == wall_index:
            continue
        boxes.append(("partition %d" % i, (lo, line - t / 2, hi, line + t / 2) if ax == "X"
                      else (line - t / 2, lo, line + t / 2, hi)))
    da = agent_contract.door_approach()
    for e in vault_room.wall_openings(spec, kinds=_WALKABLE):
        if e["story"] != story:
            continue
        w = _opening_width(e["op"]) / 2.0
        d = t / 2 + da
        boxes.append(("%s approach at (%.2f, %.2f)" % (e["op"].get("kind", "door"), e["x"], e["y"]),
                      (e["along"] - w, e["line"] - d, e["along"] + w, e["line"] + d) if e["axis"] == "X"
                      else (e["line"] - d, e["along"] - w, e["line"] + d, e["along"] + w)))
    for v in spec.get("volumes") or []:
        vz, vh = float(v.get("z", 0.0)), float(v.get("size_z", 0.0))
        if not level_design._on_storey(vz, vh, floor, sh) or level_design._hung(v, floor):
            continue
        ax_, ay_ = float(v.get("size_x", 1)) / 2.0, float(v.get("size_y", 1)) / 2.0
        boxes.append(("volume %s" % v.get("name"), (v["x"] - ax_, v["y"] - ay_, v["x"] + ax_, v["y"] + ay_)))
    for r in level_design._stair_reserved_rects(spec):
        boxes.append(("a stair", tuple(r)))
    for h in spec.get("slab_holes") or []:
        if int(h.get("story", 0) or 0) == story:
            boxes.append(("a floor hole", (h["x"] - h["size_x"] / 2.0, h["y"] - h["size_y"] / 2.0,
                                           h["x"] + h["size_x"] / 2.0, h["y"] + h["size_y"] / 2.0)))
    for r in vault_room.keepout_rects(spec, story):
        boxes.append(("a vault door's swing", tuple(r)))
    head = agent_contract.min_headroom()
    points = []
    for lad in spec.get("ladders") or []:
        if int(lad.get("from_story", 0) or 0) <= story <= int(lad.get("to_story", 0) or 0):
            points.append(("a ladder", (lad["x"], lad["y"])))
    for m in spec.get("markers") or []:
        z = float(m.get("z", 0.0) or 0.0)
        if floor - 0.05 <= z <= floor + head:
            points.append(("marker %s" % m.get("type"), (m.get("x", 0.0), m.get("y", 0.0))))
    rx0, ry0, rx1, ry1 = room_rect
    kept = []
    for name, (x0, y0, x1, y1) in boxes:
        c = (max(x0, rx0), max(y0, ry0), min(x1, rx1), min(y1, ry1))
        if c[2] - c[0] > 1e-6 and c[3] - c[1] > 1e-6:
            kept.append((name, c))
    points = [(n, (px, py)) for n, (px, py) in points if rx0 <= px <= rx1 and ry0 <= py <= ry1]
    return kept, points


def _overlaps(a, b):
    return a[0] < b[2] - 1e-9 and b[0] < a[2] - 1e-9 and a[1] < b[3] - 1e-9 and b[1] < a[3] - 1e-9


def _clash(rect, line_boxes, boxes, points, room_rect):
    """What stops a queue, or None. TWO QUESTIONS, because the queue is mostly floor: the floor in front of the window
    and the lanes are walked, and only the lines stand. Nothing may stand INSIDE the queue's rectangle, wall face to
    last line -- a crate in a lane, a doorway's approach under the window -- and each LINE keeps a corridor from
    everything, so a body passes every end and every side of the queue. The first draft held the whole rectangle a
    corridor off everything, as if the lanes were solid, and on arena_a02 nothing fitted between the event floor's
    west breach and the box office's door."""
    cw = agent_contract.min_corridor_width()
    rx0, ry0, rx1, ry1 = room_rect
    if rect[0] < rx0 - 1e-9 or rect[1] < ry0 - 1e-9 or rect[2] > rx1 + 1e-9 or rect[3] > ry1 + 1e-9:
        return "the public room's bounds"
    for name, b in boxes:
        if _overlaps(rect, b):
            return name + " inside the queue"
    for name, (px, py) in points:
        if rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]:
            return name + " inside the queue"
    for lb in line_boxes:
        for name, b in boxes:
            if _box_gap(lb, b) < cw - 1e-9:
                return "%s within %.2f m of a line" % (name, cw)
        for name, (px, py) in points:
            if _box_gap(lb, (px, py, px, py)) < cw - 1e-9:
                return "%s within %.2f m of a line" % (name, cw)
    return None


def _lines(ua, ub, window_high, lanes):
    """Each line's span along the wall and its offset from the wall's face (to the slot's centre): ``[(u0, u1, v)]``.
    Line 0 is nearest the wall, and stops a turn short at the window's end -- the way out to the window -- and the
    lines after it stop short at alternate ends."""
    turn = lane_clear()
    v0 = service_depth() + RUN_DEPTH / 2.0
    out = []
    for k in range(lanes + 1):
        short_at_window = (k % 2 == 0)
        if short_at_window == window_high:
            u0, u1 = ua, ub - turn
        else:
            u0, u1 = ua + turn, ub
        out.append((u0, u1, v0 + k * pitch()))
    return out


def plan(spec, office):
    """The best ticket window and queue for `office`, or the reason there is none: ``{"ok", "why", ...}``.

    Every window centre the builder's grid allows on each shared wall, the window at either end of the queue, three
    lanes then two, the queue as long as `MAX_SPAN` then shorter by `SPAN_STEP`, down to a line of `line_min()` beside
    its turn: the first that clears everything (`_keepouts`, `_clash`) inside the public room. Preferred: more lanes, then a
    longer queue, then a window nearer the middle of the office's wall, then the lower window centre."""
    import vault_room
    story = int(office.get("story", 0) or 0)
    walls = _shared_walls(spec, office)
    if not walls:
        return {"ok": False, "why": "no interior wall shared with a public room"}
    t = float(spec.get("wall_thick", 0.3) or 0.3)
    face = t / 2.0
    g = vault_room._grid(spec)
    turn = lane_clear()
    cw = agent_contract.min_corridor_width()
    best, best_key, last_why = None, None, "nothing fits"
    for (wall, room, side) in walls:
        wi, p, ax, line, lo, hi = wall
        ox0, oy0, ox1, oy1 = office["bounds"]
        rx0, ry0, rx1, ry1 = room["bounds"]
        room_rect = (rx0, ry0, rx1, ry1)
        o_lo, o_hi = (ox0, ox1) if ax == "X" else (oy0, oy1)
        r_lo, r_hi = (rx0, rx1) if ax == "X" else (ry0, ry1)
        # the window: in the run the office, the public room and the wall all share, a jamb off its ends
        s_lo, s_hi = max(o_lo, r_lo, lo), min(o_hi, r_hi, hi)
        seg_lo, seg_hi = s_lo + face + JAMB + WINDOW_W / 2.0, s_hi - face - JAMB - WINDOW_W / 2.0
        mid = (s_lo + s_hi) / 2.0
        boxes, points = _keepouts(spec, story, wi, room_rect)
        # the openings already in this wall: the window keeps a jamb from each, and from a wall ending on it
        spans = []
        for e in vault_room.wall_openings(spec, kinds=("door", "window", "garage", "breach", "vault", "teller",
                                                       "safe_deposit")):
            if e["host"] is p:
                hw = _opening_width(e["op"]) / 2.0
                spans.append((e["along"] - hw, e["along"] + hw))
        for j, q, qax, qline, qlo, qhi in _walls(spec):
            if qax != ax and int(q.get("story", 0) or 0) == story and qlo - face <= line <= qhi + face:
                spans.append((qline - face, qline + face))
        centre = (lo + hi) / 2.0
        k_lo = math.ceil((seg_lo - centre) / g - 1e-9)
        k_hi = math.floor((seg_hi - centre) / g + 1e-9)
        for kk in range(k_lo, k_hi + 1):
            wc = centre + kk * g
            w0, w1 = wc - WINDOW_W / 2.0, wc + WINDOW_W / 2.0
            if any(a - JAMB < w1 and w0 < b + JAMB for a, b in spans):
                last_why = "no place on the wall clears its openings and the walls ending on it"
                continue
            for window_high in (True, False):
                for lanes in LANES:
                    depth = service_depth() + RUN_DEPTH + lanes * pitch()
                    span = MAX_SPAN
                    while span >= turn + line_min() - 1e-9:
                        ub = wc + turn / 2.0 if window_high else wc - turn / 2.0 + span
                        ua = ub - span
                        rect = _rect(ax, line, face, side, ua, ub, 0.0, depth)
                        line_boxes = [_rect(ax, line, face, side, u0, u1, v - RUN_DEPTH / 2.0, v + RUN_DEPTH / 2.0)
                                      for (u0, u1, v) in _lines(ua, ub, window_high, lanes)]
                        why = _clash(rect, line_boxes, boxes, points, room_rect)
                        if why is None:
                            key = (lanes, round(span, 6), -abs(wc - mid), -wc)
                            if best_key is None or key > best_key:
                                best_key = key
                                best = {"ok": True, "why": "", "wall": wall, "room": room, "side": side,
                                        "window_u": wc, "window_high": window_high, "lanes": lanes,
                                        "span": (ua, ub), "depth": depth, "rect": rect}
                            break
                        last_why = why
                        span = round(span - SPAN_STEP, 6)
    if best is None:
        return {"ok": False, "why": last_why}
    wi, p, ax, line, lo, hi = best["wall"]
    ua, ub = best["span"]
    best["lines"] = []
    for (u0, u1, v) in _lines(ua, ub, best["window_high"], best["lanes"]):
        cx, cy = _world(ax, line, face, best["side"], (u0 + u1) / 2.0, v)
        length = u1 - u0
        best["lines"].append({"x": cx, "y": cy, "length": length,
                              "size": (length, RUN_DEPTH) if ax == "X" else (RUN_DEPTH, length)})
    return best


def _declare_material(spec):
    """Declare `RUN_MATERIAL` LAST, after the finish palette: a slot's style is its material's place in the palette
    and `floors.ensure_finish_palette` appends the finish materials after the authored list, so a material appended
    to the authored list ahead of them would move every finish slot's style by one (Deli Counter 0.242.0 moved 50
    on arena_a02 that way, and declared the palette instead)."""
    import floors
    have = [m.get("id") for m in spec.get("materials") or []]
    if RUN_MATERIAL in have:
        return
    mats = spec.setdefault("materials", [])
    for m in floors.FINISH_PALETTE:
        if m["id"] not in have:
            mats.append(dict(m))
    a, absorption, damping = RUN_ACOUSTIC
    mats.append({"id": RUN_MATERIAL, "acoustic": a, "absorption": absorption, "damping": damping})


def queue_box_offices(spec):
    """Give every box office a ticket window and its queue. Idempotent: a spec that already has a `ticket_window`
    opening or a `stanchion_run_*` volume is left alone. Returns ``[report]``, one per box office:
    ``{"room", "queued": bool, "why", "lanes", "runs"}``."""
    report = []
    if any(op.get("tag") == "ticket_window" for p in spec.get("partitions") or [] for op in p.get("openings") or []):
        return report
    if any(str(v.get("name", "")).startswith("stanchion_run_") for v in spec.get("volumes") or []):
        return report
    if not spec.get("footprint_x") or not spec.get("footprint_y"):
        return report
    import level_design
    sh = level_design._story_height(spec)
    q = 0
    for office in spec.get("rooms") or []:
        if not office.get("bounds") or not is_box_office(office):
            continue
        entry = {"room": office.get("id"), "queued": False, "why": "", "lanes": 0, "runs": []}
        report.append(entry)
        got = plan(spec, office)
        if not got["ok"]:
            entry["why"] = got["why"]
            continue
        wi, p, ax, line, lo, hi = got["wall"]
        centre, run = (lo + hi) / 2.0, hi - lo
        p.setdefault("openings", []).append({
            "kind": "window", "pos": round((got["window_u"] - centre) / run, 6), "width": WINDOW_W,
            "height": WINDOW_H, "sill": WINDOW_SILL, "vaultable": False, "tag": "ticket_window"})
        floor = int(office.get("story", 0) or 0) * sh
        for k, ln in enumerate(got["lines"]):
            name = "stanchion_run_%d_%d" % (q, k)
            spec.setdefault("volumes", []).append({
                "name": name, "x": round(ln["x"], 3), "y": round(ln["y"], 3),
                "z": round(floor + RUN_HEIGHT / 2.0, 3),
                "size_x": round(ln["size"][0], 3), "size_y": round(ln["size"][1], 3), "size_z": RUN_HEIGHT,
                "collision": "convex", "material": RUN_MATERIAL})
            entry["runs"].append(name)
        _declare_material(spec)
        entry["queued"] = True
        entry["lanes"] = got["lanes"]
        entry["why"] = "%d lanes, %.1f m along %s's wall with %s" % (
            got["lanes"], got["span"][1] - got["span"][0], office.get("id"), got["room"].get("id"))
        q += 1
    return report
