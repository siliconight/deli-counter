"""migrate_door_width.py  --  every walkable door is at least the contract's min_door_width (0.214.0)
=====================================================================================================
One-shot, idempotent migration over the library, specs/*.json, Level Factory's lf_ specs excepted as
`layout_lint --all` excepts them. `agent_contract.json`'s `clearances.min_door_width_m` is 1.25 m, and the
library built 200 walkable doors under it: 13 at 1.0 m, 74 at 1.1 and 113 at 1.2, 47 of those width-less and
so at this builder's own default, then 1.2 (the factory's `docs/findings/door_widths/`). The walker, 2026-10-13:
changing the door widths is fine, and the contract should call it out.

A door AUTHORED narrower than the minimum, on a building that is not an Empty (`facade`), is written at the
minimum and centred where it was: its `pos` is kept, so the doorway does not move, only its sides. A
width-less door needs no edit -- `spec_types.Opening.resolved` now gives a door the contract's minimum -- and an
Empty's doors are shut and nothing walks through them, so they are left. Each file keeps its own form (the
library's two: `indent=1` with a closing newline, `indent=2` without).

Whether a widened door fits is asked twice, by what already judges a door: `layout_lint` (L18, a partition
ending inside a doorway; L21, a doorway over a stair hole -- both FAIL), and `door_fit.py`, which reads the
shells built from what this writes and names any two openings on one wall run that overlap. Two doors are named
below, from the lint's own numbers: one slid along its wall clear of L18 (`NUDGES`), and one left narrow because
no place on its wall holds the minimum (`KEPT`).

    python migrate_door_width.py            # write specs/
    python migrate_door_width.py --check    # report only
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agent_contract   # noqa: E402

#: the floor a walkable door is written at
MIN = agent_contract.min_door_width()

#: A DOOR SLID ALONG ITS WALL, by (spec, door tag): its new `pos`. Widened where it stood, `final_stand`'s
#: `west_entry` (wall W, centre y -3.9) failed L18 -- the X-partition at y -3 ends 0.90 m from its centre where
#: the lint needs more than 0.93 -- so it moves to y -4.00, 1.00 m clear (the precedent: 0.101.1 slid 33
#: openings clear of L18).
NUDGES = {("final_stand", "west_entry"): -0.1333}

#: A DOOR LEFT NARROW, by (spec, door tag), with why. `primos_pizza`'s `kitchen_stairs` (the X-partition at
#: y 1, centre x 4.9) has a partition ending 0.90 m to one side and the basement stair's hole to the other:
#: at 1.25 m it fails L18 where it stands, and slid to x 5.0 it hangs 0.12 m over the hole (L21). No place on
#: that wall holds a 1.25 m door until the stair moves, so it stays 1.20 m and the contract names it.
KEPT = {("primos_pizza", "kitchen_stairs"):
        "between a partition's end (L18) and the basement stair's hole (L21) a 1.25 m door has no place; "
        "it stays 1.20 m until the stair moves"}


def narrow_doors(d):
    """``(group, wall index, opening index, width)`` for every door this spec authors under the minimum --
    none on an Empty, none width-less, none KEPT."""
    if d.get("facade"):
        return []
    out = []
    for group in ("ext_walls", "partitions"):
        for wi, w in enumerate(d.get(group) or []):
            for oi, o in enumerate(w.get("openings") or []):
                width = o.get("width")
                if (o.get("kind") == "door" and width is not None and float(width) < MIN - 1e-9
                        and (d.get("name"), o.get("tag")) not in KEPT):
                    out.append((group, wi, oi, float(width)))
    return out


def migrate(d):
    """Widen every narrow door to the minimum, in place, and slide the NUDGES. Returns what `narrow_doors`
    found."""
    found = narrow_doors(d)
    for group, wi, oi, _w in found:
        o = d[group][wi]["openings"][oi]
        o["width"] = MIN
        if (d.get("name"), o.get("tag")) in NUDGES:
            o["pos"] = NUDGES[(d.get("name"), o.get("tag"))]
    return found


def dump_like(d, text):
    """`d` in the form `text` was written in -- `indent=1` with a closing newline, or `indent=2` without."""
    original = json.loads(text)
    for indent, tail in ((1, "\n"), (2, "")):
        if json.dumps(original, indent=indent) + tail == text:
            return json.dumps(d, indent=indent) + tail
    raise SystemExit("UNKNOWN SHAPE: a spec in neither of the library's two forms")


def main():
    check = "--check" in sys.argv
    n_specs = n_doors = 0
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        text = io.open(p, encoding="utf-8", newline="").read()
        d = json.loads(text)
        found = migrate(d)
        if not found:
            continue
        n_specs += 1
        n_doors += len(found)
        widths = sorted({w for _g, _wi, _oi, w in found})
        print("%-44s %2d door(s) from %s m" % (os.path.basename(p)[:-len(".json")], len(found),
                                                "/".join("%.2f" % w for w in widths)))
        if not check:
            io.open(p, "w", encoding="utf-8", newline="").write(dump_like(d, text))
    print("%d spec(s): %d door(s) to %.2f m%s" % (n_specs, n_doors, MIN,
                                                 " -- check only, nothing written" if check else ""))


if __name__ == "__main__":
    main()
