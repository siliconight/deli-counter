"""TEMPORARY instrument: print the real floats at every near-threshold span.

    python patch_dc_span_probe.py            # add the probe
    python patch_dc_span_probe.py --revert   # take it back out

Asserts its anchors both ways and refuses to write on a miss, so `--revert`
cannot leave a half-instrumented file behind.

WHY
---
The corner change closed 988 of 988 open corners across the library, and
introduced exactly ONE new sub-5 cm gap: `strip_retail_a01 ext_1_N`, 0.050 m
between `ext_1_N_seg5` and `ext_1_N_open0`. Two spans down that same run
`seg8` is 2.05 m wide and marked `end`, so absorption fired there and not at
seg5 -- two spans that look identical from the manifest took different
branches.

The obvious explanation was tested and REFUTED: that `rem = L - n * M` (the
absorb test) and `b - x` (the emit test) are the same quantity computed two
ways and that float noise put a boundary value on opposite sides of 0.05.
Reconstructed from the recorded spans, both expressions give the same value
here, and that value would have EMITTED a remainder rather than dropped one.
So the mechanism is not established, and it cannot be established from the
manifest: `h["u"]`, `h["w"]` and whatever `snap()` does to them never reach
it. Only the builder knows.

Hence this. It prints `repr()` -- full precision, not the 4-decimal rounding
the manifest carries, which is exactly the information that was missing.

Filtered to `1e-9 < rem < 0.06` so a whole-library run does not drown the
console; on one building it is a handful of lines. Guarded on `_SPAN_PROBE`
so the revert is one constant and the instrument cannot be left on by
accident.

REMOVE IT AFTER READING. A probe left in is a print in everyone's build.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "deli_counter.py"

PLAIN_FLAG = '''    # -- modular wall emitter ---'''
PROBE_FLAG = '''    # -- modular wall emitter ---'''

FLAG_ANCHOR = '''from dataclasses import replace'''
FLAG_ADDED = '''from dataclasses import replace

# TEMPORARY (patch_dc_span_probe.py) -- remove with `--revert`.
_SPAN_PROBE = True'''

TAIL_PLAIN = '''            k += 1
        return k

    def _opening_piece(self, vbase, cbase, center, size, axis, h, j, material):'''

TAIL_PROBE = '''            k += 1
        if _SPAN_PROBE and 1e-9 < rem < 0.06:
            emitted = (not absorb) and (b - x > 0.05)
            hole = 0.0 if (absorb or emitted) else (b - x)
            print(f"[span] {vbase}_seg{k} a={a!r} b={b!r} L={L!r} M={M!r} "
                  f"n={n} rem_L_minus_nM={rem!r} rem_b_minus_x={(b - x)!r} "
                  f"absorb={absorb} emitted_remainder={emitted} hole={hole!r}",
                  flush=True)
        return k

    def _opening_piece(self, vbase, cbase, center, size, axis, h, j, material):'''


def main(argv):
    revert = "--revert" in argv
    raw = TARGET.read_bytes()
    if b"\r\n" in raw:
        print("  CRLF present; refusing to normalise a file this did not author")
        return 2
    text = raw.decode("utf-8")
    pairs = ([(FLAG_ADDED, FLAG_ANCHOR), (TAIL_PROBE, TAIL_PLAIN)] if revert
             else [(FLAG_ANCHOR, FLAG_ADDED), (TAIL_PLAIN, TAIL_PROBE)])
    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            print(f"  anchor found {n} times, expected exactly 1")
            print(f"    starts: {old.splitlines()[0][:70]!r}")
            print("  nothing written")
            return 2
        text = text.replace(old, new)
    TARGET.write_bytes(text.encode("utf-8"))
    print(f"  {'removed' if revert else 'added'} the span probe "
          f"({len(text.encode('utf-8'))} bytes)")
    if not revert:
        print(r'  now:  python build.py specs\strip_retail_a01.json '
              r'--blender "C:\blender\blender.exe"')
        print("  then: python patch_dc_span_probe.py --revert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
