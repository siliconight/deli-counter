#!/usr/bin/env python3
"""
evidence.py  --  persist validation evidence as report files
============================================================
The Production Package requires every approved configuration to carry PROOF:
stored validation reports, not stdout that scrolls away. This tool runs the
offline analyzer chain programmatically and writes, next to the build outputs:

    build/<name>.validation.json     all gates: pass/fail + errors + warnings
    build/<name>.combat_audit.json   combat_audit findings (rule packs by mode)
    build/<name>.navigation.json     room graph, entries, navigability summary

It never re-implements a check — it imports the same modules validate.py uses,
so a stored report can never disagree with the CLI gate.

    python evidence.py specs/bank.json
    python evidence.py --all
    python evidence.py specs/bank.json --out build

Exit code: non-zero if any BLOCKING gate failed (same judgment as validate.py).
Reports are written either way — failing evidence is still evidence.
"""

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BLOCKING_GATES = ("schema", "loader", "tactical", "guards", "enterability",
                  "navigability", "stairwell", "ladder", "pvp_heist")


def _gate(fn):
    """Run an (errors, warnings, summary)-style check defensively."""
    try:
        out = fn()
        if isinstance(out, tuple) and len(out) == 3:
            errors, warnings, summary = out
        elif isinstance(out, tuple) and len(out) == 2:
            errors, warnings = out
            summary = None
        else:
            errors, warnings, summary = [], [], out
        return {"ran": True, "passed": not errors,
                "errors": list(errors), "warnings": list(warnings),
                "summary": summary}
    except Exception as ex:
        return {"ran": False, "passed": False,
                "errors": [f"analyzer crashed: {ex}"], "warnings": [],
                "summary": None}


def collect(spec_path):
    """Run the full offline chain on one spec. Returns (report, combat, nav)."""
    from spec_loader import spec_from_dict
    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = {"schema_version": 1, "tool": "deli_counter/evidence.py",
              "spec_path": os.path.relpath(spec_path, HERE),
              "gates": {}, "blocking_failures": []}

    # schema
    try:
        import validate as _v
        schema_errs = [e for e in _v._schema_check(data) if not e.startswith("(")]
        report["gates"]["schema"] = {"ran": True, "passed": not schema_errs,
                                     "errors": schema_errs, "warnings": [],
                                     "summary": None}
    except Exception as ex:
        report["gates"]["schema"] = {"ran": False, "passed": False,
                                     "errors": [str(ex)], "warnings": [],
                                     "summary": None}

    # loader
    try:
        spec = spec_from_dict(data)
        report["gates"]["loader"] = {"ran": True, "passed": True, "errors": [],
                                     "warnings": [], "summary": {
                                         "name": spec.name, "mode": spec.mode,
                                         "stories": spec.n_stories,
                                         "rooms": len(spec.rooms or [])}}
    except Exception as ex:
        report["gates"]["loader"] = {"ran": True, "passed": False,
                                     "errors": [f"loader error: {ex}"],
                                     "warnings": [], "summary": None}
        report["name"] = os.path.splitext(os.path.basename(spec_path))[0]
        report["blocking_failures"] = ["loader"]
        return report, None, None

    report["name"] = spec.name
    report["mode"] = spec.mode
    facade = bool(getattr(spec, "facade", False))
    report["facade"] = facade

    combat = None
    nav = None
    if not facade:
        import tactical, guards, enterability, navigability, stairwell, ladder
        report["gates"]["tactical"] = _gate(lambda: tactical.analyze(spec))
        report["gates"]["guards"] = _gate(lambda: guards.check_all(spec))
        report["gates"]["enterability"] = _gate(lambda: enterability.check(spec))
        report["gates"]["navigability"] = _gate(lambda: navigability.check(spec))
        report["gates"]["stairwell"] = _gate(lambda: stairwell.check(spec))
        report["gates"]["ladder"] = _gate(lambda: ladder.check(spec))

        if spec.mode == "pvp_heist":
            import pvp_heist
            report["gates"]["pvp_heist"] = _gate(lambda: pvp_heist.check(spec))

        # sightlines: intel, never gates — recorded for the review sheet
        try:
            import sightlines
            report["intel"] = {"sightlines": sightlines.analyze(spec)}
        except Exception as ex:
            report["intel"] = {"sightlines_error": str(ex)}

        # combat audit: full findings persisted as their own report
        try:
            import combat_audit
            packs = combat_audit.packs_for(spec, "auto")
            result = combat_audit.audit(spec, name=spec.name, rules="auto")
            findings = [{"severity": f[0], "code": f[1], "message": f[2]}
                        for f in result.get("findings", [])]
            combat = dict(result, schema_version=1, mode=spec.mode,
                          rule_packs=packs, findings=findings)
            high = [f for f in findings if f["severity"] == "HIGH"]
            report["gates"]["combat_audit_high"] = {
                "ran": True,
                # HIGH findings block only under the pvp_heist production
                # profile; legacy modes keep combat audit advisory.
                "passed": (spec.mode != "pvp_heist") or not high,
                "errors": [_finding_line(f) for f in high]
                          if spec.mode == "pvp_heist" else [],
                "warnings": [_finding_line(f) for f in high]
                            if spec.mode != "pvp_heist" else [],
                "summary": {"total": len(findings), "high": len(high)}}
        except Exception as ex:
            combat = {"schema_version": 1, "name": spec.name,
                      "error": str(ex), "findings": []}

        # navigation report: the graph itself, entries, objective rooms
        try:
            adj = tactical.build_graph(spec)
            entries = sorted(tactical._entry_rooms(spec))
            nav = {"schema_version": 1, "name": spec.name,
                   "rooms": [{"id": r.id, "story": r.story, "role": r.role,
                              "bounds": r.bounds} for r in spec.rooms or []],
                   "adjacency": {k: sorted(v) for k, v in adj.items()},
                   "entry_rooms": entries,
                   "objective_rooms": [r.id for r in spec.rooms or []
                                       if r.objective or r.role == "objective_room"],
                   "navigability": report["gates"]["navigability"]["summary"]}
        except Exception as ex:
            nav = {"schema_version": 1, "name": spec.name, "error": str(ex)}

    blocking = [g for g in BLOCKING_GATES
                if g in report["gates"] and not report["gates"][g]["passed"]]
    if spec.mode == "pvp_heist" and "combat_audit_high" in report["gates"] \
            and not report["gates"]["combat_audit_high"]["passed"]:
        blocking.append("combat_audit_high")
    report["blocking_failures"] = blocking
    report["passed"] = not blocking
    return report, combat, nav


def _finding_line(f):
    return f"{f.get('code', '?')}: {f.get('message', '')}"


def write_reports(spec_path, out_dir):
    report, combat, nav = collect(spec_path)
    name = report.get("name") or os.path.splitext(os.path.basename(spec_path))[0]
    os.makedirs(out_dir, exist_ok=True)
    paths = {}

    def dump(suffix, payload):
        p = os.path.join(out_dir, f"{name}.{suffix}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1, default=_jsonable)
        paths[suffix] = p
        return p

    dump("validation", report)
    if combat is not None:
        dump("combat_audit", combat)
    if nav is not None:
        dump("navigation", nav)
    return report, paths


def _jsonable(o):
    if hasattr(o, "__dict__"):
        return o.__dict__
    return str(o)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec", nargs="?", help="path to a spec JSON")
    ap.add_argument("--all", action="store_true", help="every spec in specs/")
    ap.add_argument("--out", default=os.path.join(HERE, "build"),
                    help="output directory (default build/)")
    args = ap.parse_args(argv)

    if args.all:
        targets = sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
    elif args.spec:
        targets = [args.spec]
    else:
        ap.error("give a spec path or --all")

    rc = 0
    for t in targets:
        report, paths = write_reports(t, args.out)
        state = "PASS" if report.get("passed") else \
                ("FACADE" if report.get("facade") else
                 f"FAIL ({', '.join(report['blocking_failures'])})")
        print(f"[evidence] {report.get('name', t)}: {state} -> "
              + ", ".join(os.path.relpath(p, HERE) for p in paths.values()))
        if not report.get("passed") and not report.get("facade"):
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
