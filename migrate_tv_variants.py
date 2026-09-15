#!/usr/bin/env python3
"""
migrate_tv_variants.py  --  a wall TV carries its variant (0.135.1)
===================================================================
One-shot, idempotent. `level_design._PIECES["wall_tv"]` now sets
`variants=True`, so a freshly furnished TV writes `variant` = crc32(name) % 4
(omitted when 0), the rule every other variant piece follows. The library's
TVs were furnished before that, and Zoo 0.90.0 draws a ballgame from the
variant, so they would all show variant 0.

This stamps ONLY that field on existing `wall_tv_*` volumes. It deliberately
does not re-run the furnish migrations: measured 2026-09-15, re-furnishing
the library with today's code does not reproduce today's specs
(`migrate_club_rooms.py --check`: strip_club_a01 -87/+85, a02 -76/+75, a03
-149/+145; `migrate_furnish_recipes.py --check`: -7435/+7428 across 126
specs), so a full refurnish here would carry an unrelated change in with a
one-field fix. That drift is recorded as its own finding.

    python migrate_tv_variants.py            # write specs/
    python migrate_tv_variants.py --check    # report only
"""
import glob
import io
import json
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))


def variant_for(name: str) -> int:
    """The same rule as `level_design.furnish` for a 4-variant piece."""
    return (zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF) % 4


def migrate(spec: dict) -> int:
    """Stamp missing variants; returns how many volumes changed."""
    changed = 0
    for v in spec.get("volumes", []) or []:
        name = str(v.get("name", ""))
        if not name.startswith("wall_tv_"):
            continue
        n = variant_for(name)
        want = n if n else None
        if v.get("variant") != want:
            if want is None:
                v.pop("variant", None)
            else:
                v["variant"] = want
            changed += 1
    return changed


def main(argv=None) -> int:
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    total = 0
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        # `specs/lf_*.json` are Level Factory's generated levels -- gitignored
        # pipeline output in the same folder, not library specs
        if os.path.basename(path).startswith("lf_"):
            continue
        spec = json.loads(io.open(path, encoding="utf-8").read())
        n = migrate(spec)
        if not n:
            continue
        total += n
        print("[tv_variants] %s: %d wall TV(s) stamped" % (os.path.basename(path), n))
        if not check:
            # the writer every other migration here uses (indent 1, LF)
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                json.dumps(spec, indent=1) + "\n")
    print("[tv_variants] %d volume(s) %s" % (total, "would change" if check else "changed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
