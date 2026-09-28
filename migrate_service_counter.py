#!/usr/bin/env python3
"""
migrate_service_counter.py  --  a convenience store's counter is the store's
============================================================================
One-shot, idempotent migration over specs/*.json for Zoo 1.7.0's `counter`
form ``service``: the convenience store's counter, with checkerboard trim, a
candy rack on the customer face, registers and lottery dispensers, and the
cigarette rack overhead. The walker asked for it by name, 2026-09-27:
"start with the service counter, cigarette overhead and candy rack".

WHY A MIGRATION AND NOT ONLY THE PRESET. 0.146.0's first draft put
``"form": "service"`` on the `gas_station` preset's `register_counter` and
stopped there. The buildings a cold run places are the CHECKED-IN specs, not
the preset -- `gas_station_a02.json` is the forecourt store club_block_014
stands -- and none of them is regenerated from the preset at build time. The
first rebuild after that edit reproduced every gas station with its spec
hash unchanged. The preset edit covers a spec made tomorrow; this covers the
ones that exist.

WHICH COUNTERS. A volume named exactly ``register_counter``. Measured before
it ran, over every non-`lf_` spec: nine specs carry one, and all nine are a
fuel stop or a convenience store -- seven with a pump forecourt
(`gas_station`, `_a01`, `_a02`, `gas_street`, `gs_corner_station`,
`cr_gas`, `fuel_stop_heist`) and two storefront-only stores
(`gas_station_a03`, `stop_n_go`). A forecourt test was considered and
refused: it would have missed those two, which are the same store without
pumps. The delis name theirs ``front_register_counter`` and are NOT touched
-- a deli's counter is a deli's counter. A counter that already names a
form keeps it.

`lf_*` specs are Level Factory's per-run transients and are skipped.

    python migrate_service_counter.py            # write specs/
    python migrate_service_counter.py --check    # report only; exit 1 if any
    python migrate_service_counter.py --dir D    # another spec directory
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

#: The one volume name this migration reads, exactly.
COUNTER = "register_counter"
FORM = "service"


def formless_counters(spec):
    return [v for v in spec.get("volumes") or []
            if v.get("name") == COUNTER and not v.get("form")]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    root = os.path.join(HERE, "specs")
    if "--dir" in argv:
        root = argv[argv.index("--dir") + 1]
    specs = pieces = 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except ValueError:
            continue
        todo = formless_counters(d)
        if not todo:
            continue
        specs += 1
        pieces += len(todo)
        if check:
            continue
        for v in todo:
            v["form"] = FORM
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(d, indent=1) + "\n")
    verb = "need the service form" if check else "given the service form"
    print(f"[service_counter] {specs} spec(s), {pieces} counter(s) {verb}")
    return 1 if check and pieces else 0


if __name__ == "__main__":
    sys.exit(main())
