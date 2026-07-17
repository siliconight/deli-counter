"""
stair_core.py  --  vertical circulation FIRST, rooms around it (no Blender)
===========================================================================
Humans design multistory buildings roughly as: footprint -> entrances ->
vertical circulation cores -> corridors -> rooms -> props. Deli Counter's
recipes historically went footprint -> partitions -> "find a rectangle where
stairs might fit", which is how stairs ended up facing walls and landing in
closets. This module inverts that order for generated buildings:

    1. RESERVE  -- propose stair cores against the shell (stair_place, all
       four facings, landing clearances) before partitions matter. A core is
       the whole oriented system: flight footprint + lower/upper landings.
    2. APPLY    -- the floorplan adapts to the reservation, never the other
       way around:
         - partitions crossing the flight footprint are TRIMMED to its edge
           (walls may enclose the shaft, never cross it);
         - doorless partitions crossing a landing get a DOOR punched at the
           crossing (the enclosure opens onto the landing);
         - each core gets a dedicated 'stairwell' room; rooms it overlaps
           are guillotine-split around it, and room references (objectives,
           loot, markers) are remapped to the surviving piece;
         - props/markers standing inside the reservation are EVICTED
           (Rule 10: reserved space, not leftover space).

Entry points:
    cores = reserve(spec_dict, archetype)         # placement only
    apply(spec_dict, cores)                       # floorplan surgery
    core_first(spec_dict, archetype=None)         # both; returns eviction log
    presets.make(name, stairs_first=True)         # recipe integration
    python new_level.py --preset office --name x --stairs-first

Everything is pure and deterministic: same spec dict, same cores, forever.
"""

import copy

import spec_loader
import stair_place
import stairwell

_MIN_PIECE = 0.8        # m; a split room remnant thinner than this is dropped
_MIN_WALL_SEG = 0.6     # m; a trimmed partition shorter than this is dropped
_PUNCH_DOOR_W = 1.1     # m; door punched where an enclosure crosses a landing

# preset -> stair_place archetype for core-first generation. Chosen by what
# the building IS, not by floor-count pedantry (a mismatch only notes).
DEFAULT_ARCHETYPE = {
    "bank": "office_lowrise",
    "police_station": "office_lowrise",
    "corner_deli": "urban_storefront_narrow",
    "compound": "office_lowrise",
    "hospital": "school_wings",
    "casino_tower": "office_midrise",
    "rowhome": "residential_house",
    "suburban_safehouse": "residential_house",
    "office": "office_lowrise",
    "parking_garage": "parking_structure",
    "auto_shop": "warehouse_mezzanine",
    "pawn_shop": "urban_storefront_narrow",
    "warehouse": "warehouse_mezzanine",
}


def _bbox(rects):
    xs0, ys0, xs1, ys1 = zip(*rects)
    return (min(xs0), min(ys0), max(xs1), max(ys1))


def _overlap(a, b):
    return (min(a[2], b[2]) - max(a[0], b[0]) > 1e-9
            and min(a[3], b[3]) - max(a[1], b[1]) > 1e-9)


# ---------------------------------------------------------------------------
# 1. RESERVE
# ---------------------------------------------------------------------------

def _core_of(shell, sd):
    st = spec_loader.spec_from_dict({**shell, "stairs": [sd]}).stairs[0]
    fp = stairwell.footprint_rect(st)
    lands = [dict(e) for e in stairwell.stair_endpoints(st)]
    well = _bbox([fp] + [e["rect"] for e in lands])
    return {"stair": sd, "footprint": fp, "landings": lands, "well": well}


def _basement_connector(shell, profile, main_cores):
    """A separate service core climbing basement -> grade. Unlike the main
    cores it MAY open into a protected room (a stair into the vault is how
    you reach the vault; a service role keeps approach findings at intel
    severity), but it must still be physically clean and stand clear of the
    main cores. Deterministic: candidates in zone order, the one farthest
    from the main cores wins."""
    bshell = copy.deepcopy(shell)
    bshell["n_stories"] = 1                # the connector climbs -1 -> 0
    sp = spec_loader.spec_from_dict(bshell)
    fw, run, rise, w, style = stair_place.stair_dims(sp, profile)
    best, best_d = None, -1.0
    for cand in stair_place.candidate_zones(sp, profile):
        sd = {"x": cand["x"], "y": cand["y"], "from_story": -1, "to_story": 0,
              "width": w, "run": run, "style": style,
              "step_rise": round(rise, 3), "facing": cand["facing"],
              "cut_slabs": True, "role": "service",
              "meta": {"generated_by": "stair_core"}}
        core = _core_of(bshell, sd)
        st = spec_loader.spec_from_dict({**bshell, "stairs": [sd]}).stairs[0]
        if stairwell.clearance_findings(sp, st, "b"):
            continue
        if any(_overlap(core["well"], m["well"]) for m in main_cores):
            continue
        d = min((abs(cand["x"] - m["stair"]["x"])
                 + abs(cand["y"] - m["stair"]["y"]) for m in main_cores),
                default=0.0)
        if d > best_d:
            best, best_d = sd, d
    return best


def reserve(spec_dict, archetype, count=None):
    """Propose stair cores for a spec BEFORE its partitions are binding.

    The proposal runs against a shell copy with partitions stripped (they are
    adjustable -- apply() reshapes them around the winners) but rooms kept, so
    cores still avoid objective/prohibited rooms and score real discharge
    routes. The enclosure requirement is relaxed because apply() BUILDS the
    stairwell enclosure.

    Main cores serve grade -> top. A basement is served by its own SERVICE
    connector core (-1 -> 0): a whole-basement vault would otherwise reject
    every through-running candidate on protected-room overlap, and real
    buildings interrupt public circulation at grade anyway (Rule 8).

    Returns a list of core dicts:
        {stair, footprint, landings, well}   (all rects in world meters)
    """
    shell = copy.deepcopy(spec_dict)
    shell["stairs"] = []
    shell["partitions"] = []
    has_basement = bool(shell.get("has_basement"))
    main_shell = dict(copy.deepcopy(shell), has_basement=False)
    sp = spec_loader.spec_from_dict(main_shell)
    profile = dict(stair_place.PROFILES[archetype])
    profile["allow_open_primary_stair"] = True     # we build the enclosure
    prop = stair_place.propose(sp, archetype, count=count, profile=profile)

    cores = []
    for i, sd in enumerate(prop["stairs"]):
        sd = dict(sd)
        sd["id"] = f"core_{i}_{sd['role']}"
        sd["meta"] = {"generated_by": "stair_core"}
        cores.append(_core_of(main_shell, sd))

    if has_basement and cores \
            and any(r.get("story") == -1 for r in shell.get("rooms") or []):
        sd = _basement_connector(shell, profile, cores)
        if sd is not None:
            sd["id"] = f"core_{len(cores)}_basement_service"
            cores.append(_core_of(shell, sd))
    return cores


# ---------------------------------------------------------------------------
# 2. APPLY  --  the floorplan adapts to the reservation
# ---------------------------------------------------------------------------

def _served_stories(spec_dict, sd):
    base = -1 if spec_dict.get("has_basement") else 0
    lo, hi = sorted([sd["from_story"], sd["to_story"]])
    top = spec_dict.get("n_stories", 1)
    return [s for s in range(lo, hi + 1) if base <= s <= top]


def _trim_partition(p, fp, wall_thick):
    """Trim one partition dict against a flight footprint. Returns a list of
    replacement partition dicts (possibly [p] unchanged, possibly empty)."""
    axis = p["axis"]
    lo, hi = sorted([p["start"], p["end"]])
    t2 = wall_thick / 2
    if axis == "Y":
        crosses = fp[0] - t2 <= p["pos"] <= fp[2] + t2
        ov0, ov1 = max(lo, fp[1]), min(hi, fp[3])
    else:
        crosses = fp[1] - t2 <= p["pos"] <= fp[3] + t2
        ov0, ov1 = max(lo, fp[0]), min(hi, fp[2])
    if not crosses or ov1 - ov0 <= 1e-9:
        return [p]
    length = hi - lo
    out = []
    for seg_lo, seg_hi in ((lo, ov0), (ov1, hi)):
        if seg_hi - seg_lo < _MIN_WALL_SEG:
            continue
        seg = dict(p, start=seg_lo, end=seg_hi)
        keep = []
        for op in p.get("openings") or []:
            along = lo + (op["pos"] + 0.5) * length
            if seg_lo <= along <= seg_hi:
                keep.append(dict(op, pos=(along - seg_lo)
                                 / (seg_hi - seg_lo) - 0.5))
        seg["openings"] = keep
        out.append(seg)
    return out


def _punch_door(p, land, wall_thick):
    """If partition dict p crosses the landing rect doorlessly, punch a door
    at the crossing center. Mutates p in place; returns True if punched."""
    axis = p["axis"]
    lo, hi = sorted([p["start"], p["end"]])
    t2 = wall_thick / 2
    if axis == "Y":
        if not (land[0] - t2 <= p["pos"] <= land[2] + t2):
            return False
        ov0, ov1 = max(lo, land[1]), min(hi, land[3])
    else:
        if not (land[1] - t2 <= p["pos"] <= land[3] + t2):
            return False
        ov0, ov1 = max(lo, land[0]), min(hi, land[2])
    if ov1 - ov0 < _PUNCH_DOOR_W:
        return False                      # crossing too short for a doorway
    length = hi - lo
    for op in p.get("openings") or []:
        if op.get("kind", "door") in ("door", "garage", "breach", "vault"):
            along = lo + (op["pos"] + 0.5) * length
            half = (op.get("width") or 1.2) / 2
            if along + half >= ov0 and along - half <= ov1:
                return False              # already doored here
    center = (ov0 + ov1) / 2
    p.setdefault("openings", []).append(
        {"kind": "door", "pos": round(center_frac(center, lo, length), 4),
         "width": _PUNCH_DOOR_W})
    return True


def center_frac(along, lo, length):
    return (along - lo) / length - 0.5 if length > 1e-9 else 0.0


def _subtract_room(bounds, cut):
    """Guillotine-subtract `cut` from room `bounds`. Returns remnant rects
    (W, E, S, N order) with useless slivers dropped."""
    x0, y0, x1, y1 = bounds
    cx0, cy0 = max(x0, cut[0]), max(y0, cut[1])
    cx1, cy1 = min(x1, cut[2]), min(y1, cut[3])
    if cx1 - cx0 <= 1e-9 or cy1 - cy0 <= 1e-9:
        return [tuple(bounds)]
    pieces = [(x0, y0, cx0, y1),        # west
              (cx1, y0, x1, y1),        # east
              (cx0, y0, cx1, cy0),      # south
              (cx0, cy1, cx1, y1)]      # north
    return [p for p in pieces
            if p[2] - p[0] >= _MIN_PIECE and p[3] - p[1] >= _MIN_PIECE]


def apply(spec_dict, cores):
    """Reshape the floorplan around the reserved cores, in place. Returns an
    eviction log: [(kind, name, reason)] for everything removed."""
    evicted = []
    wall_thick = spec_dict.get("wall_thick", 0.3)
    sh = spec_dict.get("story_height", 3.5)
    spec_dict["stairs"] = [c["stair"] for c in cores]

    for core in cores:
        served = _served_stories(spec_dict, core["stair"])
        roomed = {r["story"] for r in spec_dict.get("rooms") or []}
        lo_s = min(served) if served else 0
        hi_s = max(served) if served else 0
        land_story = {"lower": lo_s, "upper": hi_s}

        # -- partitions: trim through the shaft, punch doors at landings ----
        new_parts = []
        for p in spec_dict.get("partitions") or []:
            if p["story"] not in served:
                new_parts.append(p)
                continue
            for seg in _trim_partition(p, core["footprint"], wall_thick):
                for e in core["landings"]:
                    if seg["story"] == land_story[e["end"]]:
                        _punch_door(seg, e["rect"], wall_thick)
                new_parts.append(seg)
        spec_dict["partitions"] = new_parts

        # -- rooms: dedicated stairwell + guillotine splits -----------------
        renames = {}                       # (story, old_id) -> [(rect, new_id)]
        new_rooms = []
        for s in served:
            if s not in roomed:
                continue
            new_rooms.append({
                "id": f"{core['stair']['id']}_well_{s}",
                "story": s, "bounds": list(core["well"]),
                "role": "stairwell",
            })
        for r in spec_dict.get("rooms") or []:
            if r["story"] not in served \
                    or not _overlap(r["bounds"], core["well"]):
                new_rooms.append(r)
                continue
            pieces = _subtract_room(r["bounds"], core["well"])
            if len(pieces) == 1 and tuple(pieces[0]) == tuple(r["bounds"]):
                new_rooms.append(r)
                continue
            tags = ("w", "e", "s", "n")
            for j, rect in enumerate(pieces):
                piece = dict(r, id=f"{r['id']}_{tags[j] if j < 4 else j}",
                             bounds=list(rect))
                renames.setdefault((r["story"], r["id"]), []).append(
                    (rect, piece["id"]))
                new_rooms.append(piece)
            if not pieces:
                evicted.append(("room", r["id"], "fully consumed by core"))
        spec_dict["rooms"] = new_rooms

        # -- remap room references to the surviving piece -------------------
        def _remap(entry, z_default=0.0):
            rid = entry.get("room")
            if not rid:
                return
            z = entry.get("z", z_default) or 0.0
            story = int(z // sh) if z >= 0 else -1
            for (s, old), pieces in renames.items():
                if old != rid:
                    continue
                x, y = entry.get("x", 0.0), entry.get("y", 0.0)
                for rect, new_id in pieces:
                    if rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                        entry["room"] = new_id
                        return
                if pieces:
                    entry["room"] = pieces[0][1]    # nearest surviving piece
                return
        for key in ("objectives", "loot", "markers"):
            for entry in spec_dict.get(key) or []:
                _remap(entry)

    # -- evict props/markers standing inside any reservation ---------------
    keep_rects = []
    for core in cores:
        served = _served_stories(spec_dict, core["stair"])
        z_lo = (min(served) if served else 0) * sh
        z_hi = ((max(served) if served else 0) + 1) * sh
        keep_rects.append((core["well"], z_lo, z_hi))

    def _inside(x, y, z):
        return any(r[0] <= x <= r[2] and r[1] <= y <= r[3]
                   and z_lo <= z <= z_hi
                   for (r, z_lo, z_hi) in keep_rects)

    vols = []
    for v in spec_dict.get("volumes") or []:
        nm = v.get("name", "").lower()
        if any(k in nm for k in ("stair", "ramp", "land")):
            vols.append(v)
            continue
        vrect = (v["x"] - v["size_x"] / 2, v["y"] - v["size_y"] / 2,
                 v["x"] + v["size_x"] / 2, v["y"] + v["size_y"] / 2)
        if any(_overlap(vrect, r) and z_lo <= v.get("z", 0) <= z_hi
               for (r, z_lo, z_hi) in keep_rects):
            evicted.append(("volume", v.get("name", "?"),
                            "inside stair core reservation"))
            continue
        vols.append(v)
    spec_dict["volumes"] = vols

    marks = []
    for m in spec_dict.get("markers") or []:
        if m.get("type") in ("objective", "loot", "cover_low", "cover_high",
                             "extraction") \
                and _inside(m.get("x", 0), m.get("y", 0), m.get("z", 0)):
            evicted.append(("marker", f"{m.get('type')}:{m.get('id', '?')}",
                            "inside stair core reservation"))
            continue
        marks.append(m)
    spec_dict["markers"] = marks
    return evicted


def core_first(spec_dict, archetype=None, count=None):
    """Reserve cores and reshape the floorplan around them. Returns the
    eviction log. No-op (returns []) for facades and single-story specs."""
    if spec_dict.get("facade") or spec_dict.get("n_stories", 1) < 2:
        return []
    arch = archetype or spec_dict.get("archetype")
    if arch is None:
        raise ValueError("core_first needs an archetype (pass one or set "
                         "spec['archetype'])")
    cores = reserve(spec_dict, arch, count=count)
    if not cores:
        raise ValueError(f"no valid stair core placement for archetype "
                         f"'{arch}' on this shell")
    spec_dict.setdefault("archetype", arch)
    return apply(spec_dict, cores)
