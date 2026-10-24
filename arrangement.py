"""
arrangement.py  --  does every piece in a room have a visible reason to stand where it stands?
==============================================================================================
The walker, walking cold run 9383, of deli_a03's stair landing: "layout of these tables doesn't seem to have a rhyme
or reason" -- and, of the fix: "nuance and flavor, but not look like random assortment" (the factory's roadmap 300).
A room reads as designed when a player can see why each thing is where it is; it reads as generated when they
cannot. This measures that, piece by piece, so a furnishing rule can be held to a number rather than to a look.

EVERY STANDING PIECE gets the first REASON that holds, tried in this order:

  wall     its footprint comes within `WALL_REACH` of an edge of its room's bounds. Room bounds stand in for walls:
           an open-plan edge with no wall counts as one, which over-credits a piece there.
  seat     a chair (`SEAT_WORDS` in its name) within `SEAT_REACH`, box to box, of a standing piece that is not one.
  aligned  it shares a centre line -- x or y within `ALIGN_TOL` -- with another piece of the same stem in the room,
           lying the same way (its long side on the same axis): a row, a column, a grid.
  centred  its centre is on one of the room's own centre lines, within `ALIGN_TOL`.
  grouped  its box comes within `GROUP_GAP` of another standing piece's -- a stool at its counter -- or within
           `PILE_GAP` of another piece of its own stem: a pile of cartons, a stack of crates.
  loose    none of them: the random assortment.

A STANDING PIECE is a volume whose foot is on its storey's floor (`level_design.stands_on_storey`), not hung
(`level_design._hung`), visual, colliding, at least `MIN_HEIGHT` tall, its centre in a room of that storey (the
innermost: `level_design._room_for_point`). Its footprint is `size_x` by `size_y` as recorded, axis-aligned; a
piece's own small turn (a chair's `rot_z` jitter) is not read. The stem is its name before `_r<crc>_` or `_<room>_`.

BY PRODUCER, because an author's intent is not this tool's to judge: `seed` (`level_design._seeded_cover`), `furnish`
(its ``_r<crc>_`` names), `authored` (everything else). The headline is the generated pieces, seed and furnish.

Measurements only: per room, the count by reason; over a set of specs, the totals by producer and the rooms holding
two or more loose GENERATED pieces. No verdict.

    python arrangement.py                       # the library's own specs, lf_ excepted
    python arrangement.py --lf                   # Level Factory's composed lf_ specs
    python arrangement.py --presets 2            # every preset at two seeds, built in memory
    python arrangement.py --spec deli_a03        # one spec, room by room
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import level_design  # noqa: E402

REASONS = ("wall", "seat", "aligned", "centred", "grouped", "loose")
WALL_REACH = 0.5      # m from a footprint edge to its room's edge
SEAT_REACH = 1.0      # m, box to box, from a chair to what it serves
ALIGN_TOL = 0.1       # m between two centre lines that read as one
GROUP_GAP = 0.3       # m, box to box, between two pieces that read as one
PILE_GAP = 1.0        # m, box to box, between two pieces of one stem that read as one pile
MIN_HEIGHT = 0.3      # m: under this a piece is floor dressing, not furniture
SEAT_WORDS = ("chair", "stool", "seat")
_FURNISHED = re.compile(r"^(?P<stem>[a-z_]+?)_r[0-9a-f]{8}_\d+(_\d+)?$")


def stem(name, room_id):
    """The piece's kind: before furnish's ``_r<crc>_<n>`` or the seeder's ``_<room>_<n>``."""
    m = _FURNISHED.match(name)
    if m:
        return m.group("stem")
    head = name.split("_%s_" % room_id)[0] if ("_%s_" % room_id) in name else name
    return re.sub(r"(_\d+)+$", "", head)


def standing(spec):
    """``{room id: [(volume, stem, box)]}`` for every standing piece, by its innermost room on its storey."""
    sh = float(spec.get("story_height") or 3.0)
    out = collections.defaultdict(list)
    for v in spec.get("volumes") or []:
        if v.get("visual") is False or v.get("collision") == "none":
            continue
        h = float(v.get("size_z", 0) or 0)
        if h < MIN_HEIGHT or "x" not in v or "y" not in v:
            continue
        z = float(v.get("z", 0) or 0)
        story = round((z - h / 2.0) / sh)
        if not level_design.stands_on_storey(z, h, story * sh, sh) or level_design._hung(v, story * sh):
            continue
        room = level_design._room_for_point(spec, float(v["x"]), float(v["y"]), story)
        if room is None:
            continue
        ax, ay = float(v.get("size_x", 0)) / 2.0, float(v.get("size_y", 0)) / 2.0
        box = (float(v["x"]) - ax, float(v["y"]) - ay, float(v["x"]) + ax, float(v["y"]) + ay)
        out[room["id"]].append((v, stem(str(v.get("name", "")), room["id"]), box))
    return out


def _gap(a, b):
    """The box-to-box gap between two footprints, 0 when they touch or overlap."""
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return (dx * dx + dy * dy) ** 0.5


def producer(v, room):
    """seed, furnish or authored: who stood this piece."""
    if level_design._seeded_cover(v, room):
        return "seed"
    return "furnish" if _FURNISHED.match(str(v.get("name", ""))) else "authored"


def reasons(room, pieces):
    """``[(volume, reason)]`` for a room's standing pieces, each by the first reason that holds."""
    x0, y0, x1, y1 = room["bounds"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    out = []
    for i, (v, st, b) in enumerate(pieces):
        px, py = float(v["x"]), float(v["y"])
        long_x = float(v.get("size_x", 0)) >= float(v.get("size_y", 0))
        others = [p for j, p in enumerate(pieces) if j != i]
        if min(b[0] - x0, x1 - b[2], b[1] - y0, y1 - b[3]) <= WALL_REACH:
            why = "wall"
        elif any(w in st for w in SEAT_WORDS) and any(
                _gap(b, ob) <= SEAT_REACH for ov, ost, ob in others if not any(w in ost for w in SEAT_WORDS)):
            why = "seat"
        elif any(ost == st and (float(ov.get("size_x", 0)) >= float(ov.get("size_y", 0))) == long_x and
                 (abs(float(ov["x"]) - px) <= ALIGN_TOL or abs(float(ov["y"]) - py) <= ALIGN_TOL)
                 for ov, ost, ob in others):
            why = "aligned"
        elif abs(px - cx) <= ALIGN_TOL or abs(py - cy) <= ALIGN_TOL:
            why = "centred"
        elif any(_gap(b, ob) <= (PILE_GAP if ost == st else GROUP_GAP) for ov, ost, ob in others):
            why = "grouped"
        else:
            why = "loose"
        out.append((v, why))
    return out


def spec_census(spec):
    """``{room id: Counter((producer, reason) -> pieces)}`` for one spec."""
    rooms = {r["id"]: r for r in spec.get("rooms") or [] if r.get("bounds")}
    return {rid: collections.Counter((producer(v, rooms[rid]), why) for v, why in reasons(rooms[rid], ps))
            for rid, ps in standing(spec).items() if rid in rooms}


def generated(c):
    """A room's counter by reason over its generated pieces alone (seed and furnish)."""
    out = collections.Counter()
    for (who, why), n in c.items():
        if who != "authored":
            out[why] += n
    return out


def _report(name_to_spec, label, detail=False):
    tot = collections.Counter()
    by_who = collections.Counter()
    loose_rooms = []
    for name, spec in name_to_spec:
        for rid, c in spec_census(spec).items():
            g = generated(c)
            tot.update(g)
            by_who.update(c)
            if g["loose"] >= 2:
                loose_rooms.append((g["loose"], sum(g.values()), name, rid))
            if detail:
                print("  %-28s %s" % (rid, "  ".join("%s %d" % (k, g[k]) for k in REASONS if g[k])))
    n = sum(tot.values())
    print("%s: %d generated standing pieces; %s" % (label, n, ", ".join(
        "%s %d (%.1f %%)" % (k, tot[k], 100.0 * tot[k] / max(1, n)) for k in REASONS)))
    for who in ("seed", "furnish", "authored"):
        m = sum(v for (w, _r), v in by_who.items() if w == who)
        print("  %-8s %5d pieces, loose %5d (%.1f %%)" % (who, m, by_who[(who, "loose")],
                                                         100.0 * by_who[(who, "loose")] / max(1, m)))
    print("  rooms holding two or more loose generated pieces: %d" % len(loose_rooms))
    for k, total, name, rid in sorted(loose_rooms, reverse=True)[:15]:
        print("    %3d loose of %3d  %s / %s" % (k, total, name, rid))
    return tot, loose_rooms


def _specs(lf, root=HERE):
    for p in sorted(glob.glob(os.path.join(root, "specs", "*.json"))):
        name = os.path.basename(p)[:-len(".json")]
        if name.startswith("lf_") != lf:
            continue
        d = json.load(open(p, encoding="utf-8"))
        if isinstance(d, dict) and d.get("rooms"):
            yield name, d


def _presets(seeds):
    import presets
    for key in sorted(presets.REGISTRY):
        for seed in range(seeds):
            s = presets.make(key, name="%s_census_%d" % (key, seed), seed=seed)
            yield "%s@%d" % (key, seed), (s if isinstance(s, dict) else s.to_dict())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lf", action="store_true")
    ap.add_argument("--presets", type=int, default=0)
    ap.add_argument("--spec")
    ap.add_argument("--dir", default=HERE, help="a Deli Counter checkout whose specs/ to read (default: this one)")
    a = ap.parse_args(argv)
    if a.spec:
        d = json.load(open(os.path.join(a.dir, "specs", a.spec + ".json"), encoding="utf-8"))
        _report([(a.spec, d)], a.spec, detail=True)
    elif a.presets:
        _report(list(_presets(a.presets)), "presets at %d seed(s)" % a.presets)
    else:
        specs = list(_specs(a.lf, a.dir))
        if not specs:
            # NOTHING READ IS NOT NOTHING LOOSE: Level Factory's lf_ specs are untracked, so a clone has none
            print("NO SPECS: %s holds no %s spec with rooms" % (os.path.join(a.dir, "specs"), "lf_" if a.lf else "library"))
            return 1
        _report(specs, "lf_ specs" if a.lf else "library")
    return 0


if __name__ == "__main__":
    sys.exit(main())
