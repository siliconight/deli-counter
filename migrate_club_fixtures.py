#!/usr/bin/env python3
"""
migrate_club_fixtures.py  --  the library's dartboards and cigarette machines (0.136.0)
======================================================================================
One-shot, idempotent. `level_design.furnish` now ends with `place_fixtures`:
a strip club's club rooms get a chalk-score dartboard at regulation height
with a clear throwing lane and a cigarette machine, and a bar or lounge
(`club`), a lobby and a hall a cigarette machine. The library's rooms were
furnished before that, and `furnish` skips a furnished room, so this runs
`place_fixtures` -- THE SAME FUNCTION, reading only the spec -- over every
library spec, and nothing else.

WHY NOT A REFURNISH, AND WHY IT WOULD HAVE BEEN THE SAME. The request asked
for a targeted migration because re-furnishing "does not reproduce today's
specs". That was REFUTED before this was written (see the FIXTURES block in
`level_design.py`): stripping and refurnishing all 126 room-bearing specs on
0.135.1 gives back all 126 byte for byte. And because the fixture pass runs
after the whole room loop and reads only the spec, measured after it was
added: strip-and-refurnish and this script produce the same JSON for 126 of
126 specs. This one writes fewer bytes through fewer code paths.

The migration skips `specs/lf_*.json`, Level Factory's gitignored output.

    python migrate_club_fixtures.py            # write specs/
    python migrate_club_fixtures.py --check    # report only
"""
import collections
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import level_design  # noqa: E402


def migrate(spec):
    """Place missing fixtures in place; returns {piece stem: count added}."""
    before = {v.get("name") for v in spec.get("volumes") or []}
    level_design.place_fixtures(spec)
    added = collections.Counter()
    for v in spec.get("volumes") or []:
        if v.get("name") not in before:
            added[v["name"].split("_r")[0]] += 1
    return added


def main(argv=None):
    check = "--check" in (argv if argv is not None else sys.argv[1:])
    total = collections.Counter()
    for path in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        # `specs/lf_*.json` are Level Factory's generated levels -- gitignored
        # pipeline output in the same folder, not library specs
        if os.path.basename(path).startswith("lf_"):
            continue
        spec = json.loads(io.open(path, encoding="utf-8").read())
        if not spec.get("rooms"):
            continue
        added = migrate(spec)
        if not added:
            continue
        total.update(added)
        print("[club_fixtures] %s: %s" % (os.path.basename(path),
                                          ", ".join("+%d %s" % (n, k) for k, n in sorted(added.items()))))
        if not check:
            # the writer every other migration here uses (indent 1, LF)
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                json.dumps(spec, indent=1) + "\n")
    print("[club_fixtures] %s %s" % (dict(total), "would be placed" if check else "placed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
