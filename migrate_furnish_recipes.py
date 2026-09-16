#!/usr/bin/env python3
"""
migrate_furnish_recipes.py  --  refurnish the library with 0.131.0's recipes
===========================================================================
One-shot, idempotent migration over specs/*.json. Every volume `furnish`
wrote -- a furniture stem, then ``_r<crc32 of a room id in this spec>_<n>``,
chair sets with one more ``_<n>`` -- is removed, and `level_design.furnish`
runs again on what is left. Authored volumes, `seed_cover`'s pieces (named by
room id, not by tag) and everything else in the spec are untouched.

WHY STRIP AND REFURNISH rather than replay 0.129.0's sequence from the
pre-furniture snapshot. Measured against 0.130.0's library before this was
written: stripping the tagged volumes and running 0.130.0's own `furnish`
gives back 122 of the 126 room-bearing specs volume for volume. The other
four are explained, not noise: the three vault banks were enclosed AFTER
they were furnished (`migrate_vault_rooms.py` evicted pieces and furnished
the new vault alone), and `twin_a01` still carried pre-0.129.0 wall offsets,
so the 0.129.0 refurnish had missed it. Stripping is the same starting point
the sequence reaches, one step shorter, and it keeps 0.130.0's vault rooms.

    python migrate_furnish_recipes.py            # write specs/
    python migrate_furnish_recipes.py --check    # report only
    python migrate_furnish_recipes.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402

_GENERATED = re.compile(r"^(?P<stem>[a-z_]+?)_(?P<tag>r[0-9a-f]{8})_\d+(_\d+)?$")


def furnished_by_this_pass(v, tags):
    """A volume `furnish` wrote: a known stem and a tag of a room in this
    spec. Both, so an authored `desk_r1234abcd_1` in a spec with no such
    room is left alone."""
    m = _GENERATED.match(str(v.get("name") or ""))
    if not m or m.group("tag") not in tags:
        return False
    stems = (set(level_design._PIECES) | set(level_design._LEGACY_STEMS)
             | set(level_design._COLLIDER_STEMS) | {"chair_set"})
    return m.group("stem") in stems


#: MARKERS `furnish` WRITES (0.137.0). The back bar pass drops a
#: `patrol_point` in each bar's staff aisle, so the nav gate answers
#: whether a bartender can be reached there. It is generated, it is named
#: with the room's tag like everything else this pass writes, and it has to
#: be stripped with the volumes or a refurnish leaves one behind and is no
#: longer a fixed point.
#: The patrol points the furnishing pass writes, DERIVED from the roles
#: `level_design` actually writes rather than spelled here. The first
#: spelling was `^bartender_...` -- correct for the one pass that existed
#: and silently wrong for the card shop's `shopkeeper`, which this
#: migration then left behind for the refurnish to write a second time.
_GENERATED_MARKER = re.compile(
    r"^(?:%s)_(?P<tag>r[0-9a-f]{8})_\d+$"
    % "|".join(re.escape(r) for r in level_design.STAFF_MARKER_ROLES))


def marker_written_by_this_pass(m, tags):
    g = _GENERATED_MARKER.match(str(m.get("id") or ""))
    return bool(g and g.group("tag") in tags)


def migrate(d):
    """Strip and refurnish one spec dict in place: (removed, added)."""
    tags = {level_design._room_tag(r) for r in d.get("rooms") or []}
    vols = d.get("volumes") or []
    keep = [v for v in vols if not furnished_by_this_pass(v, tags)]
    removed = len(vols) - len(keep)
    d["volumes"] = keep
    marks = d.get("markers") or []
    # WHERE the staff patrol points stood, not just that they did. Stripping
    # them and letting `furnish` append the new ones moved each from the
    # middle of the list to the end, so a spec that had just been generated
    # was NOT a fixed point of this migration -- the JSON differed by marker
    # ORDER alone. MEASURED on a fresh `strip_club` spec, 2026-09-16:
    # `bartender_r1d196568_2` at index 5 came back at index 29. The shipped
    # `strip_club_a01..a03` hid it, because 0.137.0's own migration had
    # already appended their bartenders at the end, so the test was passing
    # on where those three files happened to be rather than on a property of
    # the code. Each re-written marker goes back to the index it held.
    was_at = [(i, m.get("id")) for i, m in enumerate(marks)
              if marker_written_by_this_pass(m, tags)]
    kept_marks = [m for m in marks if not marker_written_by_this_pass(m, tags)]
    removed += len(marks) - len(kept_marks)
    if marks:
        d["markers"] = kept_marks
    added = level_design.furnish(d) if d.get("rooms") else 0
    if was_at:
        after = d.get("markers") or []
        ids = {mid for _i, mid in was_at}
        back = {m.get("id"): m for m in after if m.get("id") in ids}
        out = [m for m in after if m.get("id") not in back]
        for i, mid in was_at:
            if mid in back:
                out.insert(min(i, len(out)), back[mid])
        d["markers"] = out
    return removed, added


def main():
    check = "--check" in sys.argv
    root = os.path.join(HERE, "specs")
    if "--dir" in sys.argv:
        root = sys.argv[sys.argv.index("--dir") + 1]
    specs = removed = added = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(p)
        if name.startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        if not d.get("rooms"):
            continue
        before = json.dumps(d, sort_keys=True)
        r, a = migrate(d)
        specs += 1
        removed += r
        added += a
        if not check and json.dumps(d, sort_keys=True) != before:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, indent=1) + "\n")
    print(f"[furnish_recipes] {specs} specs: -{removed} furnished volumes, "
          f"+{added} refurnished")


if __name__ == "__main__":
    main()
