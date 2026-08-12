"""nav_gate.verdict() -- which key it reads, and what it says about markers.

The gate's `ok` counts STAIRS and only stairs: `nav_gate.gd` increments
`failures` in the stair loop, never in the marker section, and then writes
`result["ok"] = true` when that count is zero. Measured 2026-08-08 over the
137 shells in build/ with a .navgate.json: 107 have a marker unreachable from
the spawn and 101 of those report `ok: true`.

So the value moved to `stairs_ok`, `ok` kept writing it for the consumers that
read it, and `navigable` became a TRI-STATE overall answer -- with null for
the 20 shells where nothing checked a marker at all. These tests pin the
wrapper end of that:

  * old results (the 137 files on disk) carry `ok` alone and must still be
    read, and must be REPORTED as unjudged rather than assumed navigable;
  * `stairs_ok` wins over `ok` when they disagree, which is how you can tell
    the read actually moved;
  * the returned pass/fail is UNCHANGED by any of it -- a shell with an
    unreachable objective still returns True here, because gating on that
    would fail 107 of 137 shells and that promotion is a separate decision.

No Godot: these are synthetic result dicts, the same shape run_gate() parses
out of the gate's out.json.

Run:  python -m pytest test_navgate_verdict.py -q
      python test_navgate_verdict.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import nav_gate                      # noqa: E402


def _line(lines, needle):
    """The one line containing `needle`, or None."""
    hits = [ln for ln in lines if needle in ln]
    return hits[0] if hits else None


# ---------------------------------------------------------------------------
# old format: 137 .navgate.json files on disk predate the split
# ---------------------------------------------------------------------------

def test_old_format_ok_true_still_passes():
    """A pre-split result carries `ok` and no `stairs_ok`. The fallback has to
    read it, or every existing file on disk starts reporting a stair failure
    that never happened."""
    old = {"exit_code": 0, "ok": True, "navmesh_polys": 524,
           "stairs": [{"id": "s0", "status": "ok", "detail": "path"}],
           "markers": {"checked": 1, "reachable": 0,
                       "unreachable": ["objective_final_boss (snap 0.7m)"]}}
    ok, lines = nav_gate.verdict(old)
    assert ok is True
    assert _line(lines, "markers: 0/1")


def test_old_format_ok_false_still_fails():
    old = {"exit_code": 1, "ok": False,
           "stairs": [{"id": "s0", "status": "no_path", "detail": "islands"}]}
    ok, _ = nav_gate.verdict(old)
    assert ok is False


def test_old_format_is_reported_unjudged_not_navigable():
    """The absence of a `navigable` key is not evidence of navigability. An
    old result has to SAY it is unjudged -- this is the captured shape of
    build/final_stand.navgate.json (both stairs ok, objective unreachable,
    ok: true), which is exactly the file that reads as a pass today."""
    final_stand = {"exit_code": 0, "ok": True, "navmesh_polys": 524,
                   "islands": [{"island": 0, "polys": 462}],
                   "stairs": [
                       {"id": "final_stand_stair_0", "status": "ok",
                        "detail": "path lower<->upper"},
                       {"id": "final_stand_stair_1", "status": "ok",
                        "detail": "path lower<->upper"}],
                   "markers": {"checked": 1, "reachable": 0,
                               "unreachable":
                                   ["objective_final_boss (snap 0.7m)"]}}
    ok, lines = nav_gate.verdict(final_stand)
    assert ok is True                       # pass/fail deliberately unchanged
    nav = _line(lines, "navigable:")
    assert nav is not None
    assert "UNJUDGED" in nav
    assert "predates" in nav
    assert _line(lines, "unreachable: objective_final_boss (snap 0.7m)")


# ---------------------------------------------------------------------------
# new format: stairs_ok is the key that decides
# ---------------------------------------------------------------------------

def test_stairs_ok_is_what_is_read_when_it_disagrees_with_ok():
    """`ok` is retained for consumers, `stairs_ok` is the meaning. If a result
    ever carries both and they disagree, the new key decides -- otherwise this
    patch changed a name and nothing else.

    The dict is deliberately contradictory (exit_code 0 with a failed stair),
    which the real gate cannot emit: it is the only way to isolate WHICH key
    the wrapper reads, since agreeing keys make the two implementations
    indistinguishable."""
    r = {"exit_code": 0, "ok": True, "stairs_ok": False,
         "navigable": False, "navigable_reason": "1 stair(s) not traversable",
         "stairs": [{"id": "s0", "status": "no_path", "detail": "d"}],
         "markers": {"checked": 2, "reachable": 2, "unreachable": []}}
    ok, _ = nav_gate.verdict(r)
    assert ok is False


def test_navigable_true_is_reported_yes():
    r = {"exit_code": 0, "ok": True, "stairs_ok": True,
         "navigable": True,
         "navigable_reason": "stairs traverse and all 3 checked marker(s) "
                             "reachable from spawn",
         "stairs": [{"id": "s0", "status": "ok", "detail": "d"}],
         "markers": {"checked": 3, "reachable": 3, "unreachable": []}}
    ok, lines = nav_gate.verdict(r)
    assert ok is True
    nav = _line(lines, "navigable:")
    assert nav is not None and "yes" in nav
    assert "reachable from spawn" in nav        # the reason is carried through


def test_navigable_false_is_reported_but_does_not_flip_the_verdict():
    """The 101-shell case: stairs traverse, a marker does not connect. It has
    to SHOW as not navigable and still RETURN pass, because the exit code is
    unchanged by this step on purpose."""
    r = {"exit_code": 0, "ok": True, "stairs_ok": True,
         "navigable": False,
         "navigable_reason": "1 of 1 marker(s) unreachable from spawn",
         "stairs": [{"id": "s0", "status": "ok", "detail": "d"}],
         "markers": {"checked": 1, "reachable": 0,
                     "unreachable": ["objective_boss (snap 0.7m)"]}}
    ok, lines = nav_gate.verdict(r)
    assert ok is True
    nav = _line(lines, "navigable:")
    assert nav is not None
    assert "NO" in nav
    assert "yes" not in nav and "UNJUDGED" not in nav
    assert "1 of 1 marker(s) unreachable" in nav


def test_navigable_null_is_unjudged_not_pass_and_not_fail():
    """20 of the 137 shells check no markers at all. null must not read as
    either verdict -- `library_clean.py` already counts them as their own
    bucket for this reason."""
    r = {"exit_code": 0, "ok": True, "stairs_ok": True,
         "navigable": None,
         "navigable_reason": "UNJUDGED: 0 markers checked (no spawn marker, "
                             "or no objective/extraction/loot/patrol_point/"
                             "rescue marker) -- nothing asked whether this "
                             "shell connects",
         "stairs": [{"id": "s0", "status": "ok", "detail": "d"}],
         "markers": {"checked": 0, "reachable": 0, "unreachable": []}}
    ok, lines = nav_gate.verdict(r)
    assert ok is True
    nav = _line(lines, "navigable:")
    assert nav is not None
    assert "UNJUDGED" in nav
    assert "yes" not in nav and ": NO" not in nav
    assert _line(lines, "markers: 0 checked")


def test_navigable_null_does_not_read_as_true_via_truthiness():
    """A `nav or True` / `bool(nav)` implementation would report null as NO
    and false as NO alike, losing the distinction the tri-state exists for.
    Pin that the two produce DIFFERENT words."""
    base = {"exit_code": 0, "ok": True, "stairs_ok": True,
            "stairs": [], "markers": {"checked": 0, "reachable": 0}}
    _, null_lines = nav_gate.verdict(dict(base, navigable=None))
    _, false_lines = nav_gate.verdict(
        dict(base, navigable=False,
             markers={"checked": 1, "reachable": 0, "unreachable": ["x"]}))
    assert _line(null_lines, "navigable:") != _line(false_lines, "navigable:")


# ---------------------------------------------------------------------------
# the things that must NOT have moved
# ---------------------------------------------------------------------------

def test_gate_error_still_short_circuits():
    r = {"exit_code": 2, "ok": False, "stairs_ok": False,
         "error": "navmesh baked 0 polygons"}
    ok, lines = nav_gate.verdict(r)
    assert ok is False
    assert lines == ["gate error: navmesh baked 0 polygons"]


def test_skip_is_still_not_a_failure():
    """Unchanged on purpose: --require is the supported way to make a missing
    Godot binary fail, and 13 of 103 shells failing is why flipping it here
    would block commits rather than inform anyone."""
    ok, lines = nav_gate.verdict({"skipped": True, "reason": "no Godot 4"})
    assert ok is True
    assert any("SKIP" in ln for ln in lines)


def test_bake_numbers_are_still_echoed():
    r = {"exit_code": 0, "ok": True, "stairs_ok": True, "navigable": True,
         "navigable_reason": "r", "stairs": [],
         "markers": {"checked": 1, "reachable": 1, "unreachable": []},
         "stdout": "[nav-gate] bake: radius 0.40 cell 0.10 climb 0.15 "
                   "slope 55\n[nav-gate] wrote x.navgate.json\n"}
    _, lines = nav_gate.verdict(r)
    assert _line(lines, "bake: radius 0.40 cell 0.10 climb 0.15 slope 55")


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
        except AssertionError as ex:                    # noqa: PERF203
            failed += 1
            print(f"[FAIL] {name}: {ex or 'assertion failed'}")
        except Exception as ex:                         # noqa: BLE001
            failed += 1
            print(f"[ERROR] {name}: {type(ex).__name__}: {ex}")
        else:
            print(f"[ok] {name}")
    print("all navgate verdict tests passed" if not failed
          else f"{failed} test(s) failed")
    raise SystemExit(1 if failed else 0)
