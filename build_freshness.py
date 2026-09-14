#!/usr/bin/env python3
"""
build_freshness.py  --  are the shells in build/ older than the code?
=====================================================================
A gate that grades stale artefacts is worse than one that skips: it runs
thoroughly, examines everything, and reports with total confidence about a
version of the project that no longer exists.

Measured 2026-08-05. `nav_gate.py --all` ran for the first time against 103
built shells and reported 10 stairs across 7 shells as unwalkable, plus 19
unreachable objectives. Every one was a fossil. `build/mansion_a01.glb` was
built 2026-07-21; `stairwell.ramp_foot_extension` -- which fixes exactly that
failure, and whose docstring names it -- was written 2026-07-29. Rebuilding
the one shell flipped both its stairs to ok and its objective to reachable,
with the bake parameters untouched. The code had been correct for two weeks.

`check.py` already runs `catalog.py --check` to confirm CATALOG.md is not
stale. This is the same idea one directory over, for the artefacts every
downstream gate reads.

    python build_freshness.py            # report, exit 1 if any shell is stale
    python build_freshness.py --list     # name every stale shell

ON MTIME. This compares modification times, which are not a perfect record:
a fresh `git clone` or a checkout that rewrites a source file will mark
everything stale even though nothing changed. That direction is the safe one
-- it asks for a rebuild that was not strictly needed. The unsafe direction,
reporting fresh when stale, needs a source to be modified with an OLDER
timestamp than the build, which git does not do in normal use. A content
fingerprint recorded at build time would be strictly better and is worth
doing when build.py next changes; this catches the two-week drift that
actually happened, today, without touching the builder.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# Modules whose output is BAKED INTO a shell. A change to any of these makes
# every previously built .glb a description of the past. This list is
# deliberately about geometry and manifests -- the things a shell carries --
# not about the tools that read shells afterwards (nav_gate, zfight_gate,
# circulation), which re-run against whatever is there.
GEOMETRY_SOURCES = (
    "deli_counter.py",      # the builder itself
    "stairwell.py",         # stair geometry + ramp_foot_extension
    "stair_core.py",
    "stair_place.py",
    "floorplan.py",
    "floors.py",
    "lights.py",            # the light manifest is a build output (0.116.0)
    "wallruns.py",
    "roofs.py",
    "ladder.py",
    "ladder_geom.py",
    "ladder_place.py",
    "interactives.py",
    "partition_bounds.py",
    "presets.py",
    "spec_types.py",
    "spec_loader.py",
    "build.py",
)


def source_stamp(here=HERE, sources=GEOMETRY_SOURCES):
    """(newest mtime, filename) across the modules baked into a shell."""
    newest, who = 0.0, None
    for name in sources:
        p = os.path.join(here, name)
        if not os.path.exists(p):
            continue                       # optional module; absence is fine
        m = os.path.getmtime(p)
        if m > newest:
            newest, who = m, name
    return newest, who


def stale_shells(here=HERE, sources=GEOMETRY_SOURCES):
    """[(shell_path, shell_mtime, source_mtime, source_name)] oldest first.

    A shell with no .gameplay.json beside it is not something any downstream
    gate reads, so it is not reported.
    """
    newest, who = source_stamp(here, sources)
    if not newest:
        return []
    out = []
    for glb in sorted(glob.glob(os.path.join(here, "build", "*.glb"))):
        if not os.path.exists(os.path.splitext(glb)[0] + ".gameplay.json"):
            continue
        m = os.path.getmtime(glb)
        if m < newest:
            out.append((glb, m, newest, who))
    return sorted(out, key=lambda r: r[1])


def _sha16(path, normalise_eol=False):
    import hashlib
    with open(path, "rb") as f:
        data = f.read()
    if normalise_eol:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:16]


def content_stale(here=HERE):
    """[(shell_path, reason)] for shells whose manifest describes other bytes.

    THE FINGERPRINT THE DOCSTRING ABOVE ASKED FOR, and the gap mtime cannot
    see. `build/*.glb` is gitignored; the manifest, slots and gameplay beside
    it are tracked. A checkout or a merge therefore moves the tracked half to
    a new build and leaves the old shell on disk. Cold run 9053, 2026-09-14:
    0.131.0's `bank_tower_a03.slots.json` named `chair_waiting_rbeaaca49_4`
    1.8 x 0.6 m while the 0.129.0 shell still on disk drew a node of that
    name 0.6 x 2.4, and the placement gate refused the export. Nothing about
    that is visible to the code-mtime rule unless somebody runs it.

    Two questions per shell with a gameplay.json beside it:
      * the spec its manifest names no longer hashes to `spec_sha256_16`
        (compared raw and with CRLF folded to LF: git's autocrlf rewrites
        endings without changing content -- `gas_station_a02` measured so);
      * the GLB no longer hashes to `outputs_sha256_16` (manifests written
        before 0.131.1 carry no such field and are not judged on it).
    """
    import json
    out = []
    for glb in sorted(glob.glob(os.path.join(here, "build", "*.glb"))):
        base = os.path.splitext(glb)[0]
        if not os.path.exists(base + ".gameplay.json"):
            continue
        mpath = base + ".manifest.json"
        if not os.path.exists(mpath):
            out.append((glb, "no manifest"))
            continue
        try:
            with open(mpath, encoding="utf-8") as f:
                man = json.load(f)
        except (OSError, ValueError) as ex:
            out.append((glb, "unreadable manifest (%s)" % ex))
            continue
        spec = os.path.join(here, "specs", str(man.get("spec", "")))
        want = man.get("spec_sha256_16")
        if want and os.path.isfile(spec) and want not in (
                _sha16(spec), _sha16(spec, normalise_eol=True)):
            out.append((glb, "spec %s changed since this shell was built"
                        % os.path.basename(spec)))
            continue
        recorded = (man.get("outputs_sha256_16") or {}).get(os.path.basename(glb))
        if recorded and recorded != _sha16(glb):
            out.append((glb, "the GLB on disk is not the build its manifest "
                             "records"))
    return out


def _age(seconds):
    d = seconds / 86400.0
    if d >= 1:
        return "%.1f days" % d
    return "%.1f hours" % (seconds / 3600.0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--list", action="store_true",
                    help="name every stale shell, not just the count")
    ap.add_argument("--warn-only", action="store_true",
                    help="report but exit 0 (for adopting this gradually)")
    args = ap.parse_args(argv)

    newest, who = source_stamp()
    if not newest:
        print("build-freshness: no geometry sources found; nothing to compare")
        return 0
    stale = stale_shells()
    built = len(glob.glob(os.path.join(HERE, "build", "*.glb")))
    content = content_stale()
    if content:
        print("build-freshness: %d of %d shell(s) do not match their manifest"
              % (len(content), built))
        for glb, why in (content if args.list else content[:5]):
            print("    %-34s %s" % (os.path.basename(glb), why))
        if not args.list and len(content) > 5:
            print("    ... (--list names all)")
    if not stale and not content:
        print("build-freshness: %d shell(s) newer than %s -- up to date"
              % (built, who))
        return 0
    if not stale:
        print("  Rebuild:  python build.py --all")
        return 0 if args.warn_only else 1

    worst = stale[0]
    print("build-freshness: %d of %d shell(s) are OLDER than %s"
          % (len(stale), built, who))
    print("  newest geometry source: %s  (%s)"
          % (who, time.strftime("%Y-%m-%d %H:%M",
                                time.localtime(newest))))
    print("  oldest stale shell:     %s  (%s, %s behind)"
          % (os.path.basename(worst[0]),
             time.strftime("%Y-%m-%d %H:%M", time.localtime(worst[1])),
             _age(worst[2] - worst[1])))
    if args.list:
        for glb, m, src_m, _ in stale:
            print("    %-34s %s  (%s behind)"
                  % (os.path.basename(glb),
                     time.strftime("%Y-%m-%d %H:%M", time.localtime(m)),
                     _age(src_m - m)))
    print("  Every gate that reads build/ -- nav_gate, and anything measuring "
          "a shell --")
    print("  is reporting on geometry this code no longer produces.  Rebuild:")
    print("      python build.py --all")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
