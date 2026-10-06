"""Split the nav gate's verdict into the two questions it actually asks.

Run from the factory root:

    python patch_dc_navgate_split.py --check
    python patch_dc_navgate_split.py

Pure text edits to two files. NO GATE BEHAVIOUR CHANGES: `_exit_code` is
untouched, `result["ok"]` keeps writing exactly the value it writes today, and
`nav_gate.verdict()` keeps returning the same pass/fail. What changes is what
the file ASSERTS about what it measured.

WHAT WAS MEASURED, 2026-08-08.

`nav_gate.gd` counts `failures` over STAIR SYSTEMS only -- the loop that
increments it (`nav_gate.gd:167-199`) never touches markers. The marker
section runs after it, is labelled "secondary, warn-only", and its result is
stored and then ignored:

    result["markers"] = _check_markers(gp, nm, graph)

    if failures > 0:
        ...
        _exit_code = 1
    else:
        result["ok"] = true

So `ok` has always meant "every traversable stair proved a path", which is
what the file header says the EXIT CODE means. The name does not say that, and
`ok` is read downstream as an overall verdict.

Census over the 137 shells in build/ that have a .navgate.json: 107 have at
least one marker unreachable from the spawn, and 101 of those 107 report
`ok: true`. The clearest single case is `final_stand.navgate.json`: both
stairs `status: "ok"`, `markers: {checked: 1, reachable: 0, unreachable:
["objective_final_boss (snap 0.7m)"]}`, `ok: true`. A shell whose objective a
nav agent cannot reach is indistinguishable, at the key everything reads,
from one where it can.

WHAT THIS ADDS.

  stairs_ok  -- exactly what `ok` means today, under the name it earned.
  ok         -- UNCHANGED value. Retained solely because consumers read it:
                `nav_gate.py:verdict()` and `library_census.py` (which reports
                "of which navgate still says ok=True"). Deleting the key would
                make both read a missing value as False and start reporting
                failures that did not happen, silently.
  navigable  -- TRI-STATE. true only when stairs_ok AND markers were CHECKED
                AND every checked marker is reachable; false when markers were
                checked and something does not connect; NULL when nothing was
                checked. 20 of the 137 shells are in that third state (no
                spawn marker, or no objective/extraction/loot/patrol_point/
                rescue marker to reach). Unjudged is not passing. That
                distinction already exists in `library_clean.py`, which counts
                "UNJUDGED for reachability (markers.checked == 0 or no
                navgate)" as its own bucket rather than folding it into
                either verdict; this puts the same three-way answer in the
                gate's own output instead of leaving every reader to
                reconstruct it.
  navigable_reason -- the one-line why, so reading the JSON does not require
                re-deriving it from three other keys.

WHY THE EXIT CODE IS NOT TOUCHED. 107 of 137 shells would flip to failing. The
repo's rule is that a library goes to zero BEFORE a gate starts refusing --
`HEADROOM_ENFORCED` and `CONTAINMENT_ENFORCED` are both sitting at False for
that reason. This step only stops the file asserting something it never
measured. Promoting `navigable` to the exit code is a separate decision with a
different cost, and it needs the 107 to be understood first, not swept.

WHY ISLAND COUNT IS NOT GATED. Requiring `islands == 1` was considered and
rejected. `final_stand` bakes 12 islands and nothing shows that all 12 are
supposed to be connected: its own report has nine 2-poly fragments and a
24-poly patch at y=4.05, and a roof reachable only by a ladder the navmesh
does not model is a legitimate island. Marker reachability already measures
what must connect, directly. A comment now says this at the island line so it
does not get re-added on the next reading.

WHAT THIS DOES NOT DO, stated so the next reader does not assume it does.
`nav_gate.gd` is NOT executed by this work -- there is no Godot binary on the
machine that wrote it. The .py half is tested (test_navgate_verdict.py, run
red against the unpatched file first). The .gd half is text that has been read
for GDScript validity and nothing more; running `nav_gate.py --all` against a
real Godot 4 is what closes that gap, and the first thing to look at in the
output is whether `navigable` and `navigable_reason` appear in the written
.navgate.json at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

GATE_GD = Path("deli_counter/godot/addon/deli_counter/nav_gate.gd")
GATE_PY = Path("deli_counter/nav_gate.py")

# ---------------------------------------------------------------------------
# nav_gate.gd  --  TABS. Every inserted line inside a func is tab-indented to
# match the file; the dictionary continuation lines keep the file's existing
# tabs-then-spaces alignment.
# ---------------------------------------------------------------------------
GD_EDITS = [
    ("header: what the three verdict keys mean", '''\
## Exit code 0 = every traversable stair passes; 1 = failures; 2 = bad input.
## Machine-readable results go to out.json (default: alongside the glb).
''', '''\
## Exit code 0 = every traversable stair passes; 1 = failures; 2 = bad input.
## Machine-readable results go to out.json (default: alongside the glb).
##
## THREE VERDICT KEYS, because "ok" was answering a narrower question than its
## name suggests:
##   stairs_ok -- every traversable stair proved a path. What the exit code
##                has always gated on.
##   ok        -- the SAME value as stairs_ok. Kept because consumers read it
##                (nav_gate.py verdict(), library_census.py). It is not an
##                overall verdict and never was.
##   navigable -- true / false / null. true needs stairs_ok AND at least one
##                marker checked AND every checked marker reachable; false
##                means markers were checked and something does not connect;
##                null means NOTHING CHECKED THE MARKERS, which is unjudged,
##                not passing. navigable_reason carries the one-line why.
## Measured 2026-08-08 over the 137 shells with a .navgate.json: 107 have an
## unreachable marker and 101 of those report ok: true. The exit code is
## deliberately unchanged by that split -- see the verdict section in _run.
'''),

    ("result dict: the new keys exist on every path", '''\
	var result := {"glb": glb_path, "ok": false, "stairs": [], "markers": {},
				   "navmesh_polys": 0, "error": ""}
''', '''\
	# `ok` is stairs-only (see the verdict section at the end of _run);
	# `navigable` is tri-state and starts NULL so that an early return -- bad
	# input, unloadable glb, 0-poly navmesh -- reports "never judged" rather
	# than a verdict nothing computed. On those paths the `error` key is what
	# says the gate broke.
	var result := {"glb": glb_path, "ok": false, "stairs_ok": false,
				   "navigable": null, "navigable_reason": "not evaluated",
				   "stairs": [], "markers": {},
				   "navmesh_polys": 0, "error": ""}
'''),

    ("islands: reported, not gated", '''\
	var graph := _poly_graph(nm)
	var islands := _islands(graph)
	result["islands"] = _island_summary(nm, islands)
''', '''\
	var graph := _poly_graph(nm)
	var islands := _islands(graph)
	# REPORTED, NOT GATED -- a decision, not an oversight. Requiring
	# islands == 1 was considered on 2026-08-08 and rejected: final_stand bakes
	# 12 and nothing shows all 12 are meant to connect (nine of them are 2-poly
	# fragments), while a roof reachable only by a ladder the navmesh does not
	# model is a legitimate island. What MUST connect is measured directly by
	# marker reachability below. Do not fold an island count into `navigable`
	# without a measurement saying which islands are supposed to be reachable.
	result["islands"] = _island_summary(nm, islands)
'''),

    ("verdict: stairs_ok, ok, navigable, navigable_reason", '''\
	if failures > 0:
		print("[nav-gate] FAIL: %d stair(s) not traversable" % failures)
		_exit_code = 1
	else:
		result["ok"] = true
		print("[nav-gate] all traversable stairs pass in both directions")
	return result
''', '''\
	# -- verdict -------------------------------------------------------------
	# `failures` counts STAIRS and only stairs: the loop above is the only
	# thing that increments it, and the marker section is warn-only. So the
	# value below is the stair verdict, and it is now written under a name that
	# says so. `ok` KEEPS WRITING THE SAME VALUE -- it is retained only because
	# consumers read it (nav_gate.py verdict(), library_census.py); removing
	# the key would make them read a missing value as False and start failing
	# shells that did not fail. It is not an overall verdict.
	var stairs_ok := failures == 0
	result["stairs_ok"] = stairs_ok
	result["ok"] = stairs_ok

	# `navigable` is the overall answer, and it is TRI-STATE:
	#   true  -- stairs proved AND markers were checked AND all of them connect
	#   false -- markers were checked and this shell does not hold together
	#   null  -- NOTHING WAS CHECKED. 20 of 137 shells are here (no spawn
	#            marker, or no objective/extraction/loot/patrol_point/rescue
	#            marker to reach). Unjudged is not passing. Do not collapse
	#            null into false, and above all not into true.
	# checked == 0 is tested FIRST on purpose: with nothing measured there is
	# no reachability answer to give, and `stairs_ok` immediately above is
	# where the stair verdict lives. A reader asking "did anything fail" reads
	# both keys, which is the point of there being two.
	var mk: Dictionary = result["markers"]
	var checked: int = int(mk.get("checked", 0))
	var reachable: int = int(mk.get("reachable", 0))
	var navigable: Variant = null
	var reason := ""
	if checked == 0:
		reason = "UNJUDGED: 0 markers checked (no spawn marker, or no " \\
			+ "objective/extraction/loot/patrol_point/rescue marker) -- " \\
			+ "nothing asked whether this shell connects"
	elif not stairs_ok:
		navigable = false
		reason = "%d stair(s) not traversable; %d/%d markers reachable " \\
			% [failures, reachable, checked] + "from spawn"
	elif reachable == checked:
		navigable = true
		reason = "stairs traverse and all %d checked marker(s) reachable " \\
			% checked + "from spawn"
	else:
		navigable = false
		reason = "%d of %d marker(s) unreachable from spawn" \\
			% [checked - reachable, checked]
	result["navigable"] = navigable
	result["navigable_reason"] = reason
	var nav_word := "null"
	if navigable != null:
		nav_word = str(navigable)
	print("[nav-gate] navigable: %s -- %s" % [nav_word, reason])

	# THE EXIT CODE IS DELIBERATELY UNCHANGED. Gating on `navigable` would fail
	# 107 of 137 shells today. This repo brings a library to zero before a gate
	# starts refusing (HEADROOM_ENFORCED, CONTAINMENT_ENFORCED are both False
	# for that reason). This section only stops the gate asserting something it
	# never measured; promoting it is a separate decision.
	if failures > 0:
		print("[nav-gate] FAIL: %d stair(s) not traversable" % failures)
		_exit_code = 1
	else:
		print("[nav-gate] all traversable stairs pass in both directions")
	return result
'''),
]

# ---------------------------------------------------------------------------
# nav_gate.py  --  4-space Python.
# ---------------------------------------------------------------------------
PY_EDITS = [
    ("module docstring: the three keys", '''\
stair's lower and upper nav endpoints; the polygon graph is undirected, so
the reverse direction is the same proof. Markers get the documented F5
connectivity check as a warn-only section.
''', '''\
stair's lower and upper nav endpoints; the polygon graph is undirected, so
the reverse direction is the same proof. Markers get the documented F5
connectivity check as a warn-only section.

The gate's JSON carries `stairs_ok` (every traversable stair proved a path),
`ok` (the same value, kept because things read it), and `navigable` -- the
overall answer, tri-state, null when no marker was checked. verdict() below
still passes/fails on the STAIRS alone; it prints the navigable state so that
a shell which traverses fine and cannot reach its objective stops reading
identically to one that can. Results written before that split carry `ok`
alone and are reported as unjudged rather than assumed.
'''),

    ("verdict docstring: what ok means here", '''\
def verdict(result):
    """(ok, lines) human summary for one gate result."""
''', '''\
def verdict(result):
    """(ok, lines) human summary for one gate result.

    The returned `ok` is the STAIR verdict and nothing more -- the same thing
    the gate's exit code means, unchanged. The reachability answer goes into
    `lines` as the gate's own tri-state `navigable`; promoting it to the
    return value is a separate decision with 107 of 137 shells behind it.
    """
'''),

    ("read stairs_ok, fall back to ok for old results", '''\
    ok = result.get("exit_code") == 0 and result.get("ok", False)
''', '''\
    # `ok` in the gate's JSON has always meant STAIRS ONLY, so read the key
    # that now says so. The fallback is not defensive habit: 137 .navgate.json
    # files sit in build/ that were written before the split and carry `ok`
    # alone, and re-running them all needs a Godot binary.
    stairs_ok = result.get("stairs_ok", result.get("ok", False))
    ok = result.get("exit_code") == 0 and stairs_ok
'''),

    ("print the navigable state", '''\
    mk = result.get("markers") or {}
    if mk.get("checked"):
        lines.append(f"markers: {mk.get('reachable', 0)}/{mk['checked']} "
                     f"reachable from spawn")
        for u in mk.get("unreachable", []):
            lines.append(f"  unreachable: {u}")
    return ok, lines
''', '''\
    mk = result.get("markers") or {}
    if mk.get("checked"):
        lines.append(f"markers: {mk.get('reachable', 0)}/{mk['checked']} "
                     f"reachable from spawn")
        for u in mk.get("unreachable", []):
            lines.append(f"  unreachable: {u}")
    else:
        lines.append("markers: 0 checked -- reachability UNJUDGED")
    # Say the tri-state out loud. Reading this output used to require noticing
    # that "markers: 0/1 reachable from spawn" sat one line under a verdict
    # that said the shell passed -- which is how 101 shells reported ok: true
    # with something unreachable in them.
    if "navigable" in result:
        nav = result["navigable"]
        word = "yes" if nav is True else ("NO" if nav is False else "UNJUDGED")
        why = result.get("navigable_reason") or ""
        lines.append(f"navigable: {word}" + (f" -- {why}" if why else ""))
    else:
        lines.append("navigable: UNJUDGED -- this result predates the "
                     "stairs/markers split; its `ok` means stairs only")
    return ok, lines
'''),
]

TARGETS = [(GATE_GD, GD_EDITS), (GATE_PY, PY_EDITS)]


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
    # Nothing is written until EVERY anchor on EVERY file has matched. A
    # half-applied patch leaves nav_gate.py reading a `stairs_ok` the .gd
    # never writes, which reads as False on every shell -- and the next run's
    # --check cannot tell that state from a fresh tree.
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
