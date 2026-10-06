"""0.102.1: compute a span's remainder ONCE, so it cannot fall between two tests.

    python patch_dc_span_remainder.py [--check]

Asserts its anchors and refuses to write on a miss.

THE DEFECT, measured rather than reasoned
-----------------------------------------
0.102.0 closed 988 of 988 open corners and introduced exactly one new sub-5 cm
gap: `strip_retail_a01 ext_1_N`, 0.050 m before `ext_1_N_open0`. Instrumented
with `patch_dc_span_probe.py` and rebuilt, the span reported:

    ext_1_N_seg6  a=-9.85 b=2.2  L=12.05  M=2.0  n=6
                  rem = L - n*M      = 0.05000000000000071   -> rem <= 0.05  FALSE
                  rem = b - x        = 0.04999999999999982   -> rem >  0.05  FALSE
                  hole = 0.04999999999999982

The remainder is computed TWICE, by two different routes, and the two land on
opposite sides of the 0.05 threshold. `absorb` asks `L - n*M` and is told the
sliver is too big to absorb; the emit branch asks `b - x` and is told it is too
small to be worth emitting. Neither fires and the 5 cm is simply gone.

The contrast case is in the same run and rules out coincidence:

    ext_1_N_seg9  a=3.8   b=9.85  L=6.05   M=2.0  n=3
                  rem = L - n*M      = 0.04999999999999982   -> absorb TRUE

Same nominal 0.05, both expressions below the line, absorbed cleanly.

This is the classic form of the bug and it is worth naming: `L - n*M` and
`b - (a + n*M)` are algebraically identical and are NOT identical in floating
point, because the first accumulates the error of `b - a` and the second the
error of `a + n*M`. A threshold tested against two spellings of one number has
a window either side of it where the code does neither thing.

THE FIX
-------
Derive the remainder from the same expression the emit test uses -- the
distance from where the tiles actually END to where the span actually ENDS --
and use that ONE value for both decisions. Verified against the probe's real
floats before it was written: the -9.85 span absorbs, the 3.8 span still
absorbs, and a span whose remainder is genuinely over the threshold still
emits its `wallEnd` partial.

NOT A NEW THRESHOLD, and deliberately so. 0.05 is still the sliver limit and
`_seg_box` still refuses anything at or under it. What changes is that the two
questions are asked of the same number.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

OLD_REM = '''        n = int((L + 1e-6) // M)         # whole modules
        rem = L - n * M'''

NEW_REM = '''        n = int((L + 1e-6) // M)         # whole modules
        # ONE computation of the remainder, used by BOTH decisions below.
        # `L - n * M` is algebraically the same number and is not the same
        # float: it carries the error of `b - a`, while this carries the error
        # of `a + n * M`, and the two can straddle the 0.05 threshold. Measured
        # on `strip_retail_a01 ext_1_N` (a=-9.85, b=2.2, n=6): `L - n * M` is
        # 0.05000000000000071 -- too big to absorb -- while `b - x` is
        # 0.04999999999999982 -- too small to emit. Neither branch fired and
        # the 5 cm became a hole beside a window. A threshold asked of two
        # spellings of one number has a blind window either side of it.
        rem = b - (a + n * M)'''

OLD_EMIT = '''        if not absorb and b - x > 0.05:  # end remainder (a 'wallEnd' partial)'''
NEW_EMIT = '''        if not absorb and rem > 0.05:    # end remainder (a 'wallEnd' partial)'''

OLD_EMIT_BODY = '''                          axis, x + (b - x) / 2.0, b - x, cz, H, role="wall",'''
NEW_EMIT_BODY = '''                          axis, x + rem / 2.0, rem, cz, H, role="wall",'''

OLD_VER = 'KIT_VERSION = "0.102.0"'
NEW_VER = '''# 0.102.1: a span's remainder is computed once, not twice by two routes that
# can straddle the sliver threshold -- geometry correction, so a rebuilt .glb
# differs on the affected spans.
KIT_VERSION = "0.102.1"'''

CHANGES = [
    ("deli_counter.py", OLD_REM, NEW_REM),
    ("deli_counter.py", OLD_EMIT, NEW_EMIT),
    ("deli_counter.py", OLD_EMIT_BODY, NEW_EMIT_BODY),
    ("version.py", OLD_VER, NEW_VER),
    ("VERSION", "Deli Counter 0.102.0", "Deli Counter 0.102.1"),
]


def main(argv):
    check = "--check" in argv
    texts, order = {}, []
    for name, old, new in CHANGES:
        p = HERE / name
        if not p.is_file():
            print(f"  MISSING: {p}")
            return 2
        if p not in texts:
            raw = p.read_bytes()
            if b"\r\n" in raw:
                print(f"  {name}: CRLF present; refusing to normalise")
                return 2
            texts[p] = raw.decode("utf-8")
            order.append(p)
        n = texts[p].count(old)
        if n != 1:
            print(f"  {name}: anchor found {n} times, expected exactly 1")
            print(f"    starts: {old.splitlines()[0][:70]!r}")
            return 2
        texts[p] = texts[p].replace(old, new)
        print(f"  ok  {name}: anchor matched once")
    if check:
        print("  --check only; nothing written")
        return 0
    for p in order:
        blob = texts[p].encode("utf-8")
        p.write_bytes(blob)
        print(f"  wrote {p.name} ({len(blob)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
