"""Roadmap 58: close the exterior corner. Runs inset, a post seats the corner.

    python patch_dc_corner_posts.py [--check]

Asserts every source block it replaces and refuses to write on a miss.

WHAT IS WRONG
-------------
`_exterior` builds the four runs from the footprint:

    "N": ((0,  hy, cz), (footprint_x, wt, wh), 0)
    "E": ((hx,  0, cz), (wt, footprint_y, wh), 1)

so an N/S run is `footprint_x` long centred at zero and ends at +/- hx --
which is exactly where the E/W wall's CENTRELINE sits. Every run therefore
terminates on the perpendicular wall's centreline, 0.000 m past it, and the
outer quadrant of every corner belongs to nobody: a re-entrant notch
`wall_thick/2` on each side, full storey height, open on two faces and open
to the sky.

MEASURED before this was written, over every slot manifest in
`deli_counter/build` (`tools/envelope_continuity.py`): 988 open corners
across 124 buildings, ZERO clean. The notch tracks the thickness and nothing
else -- 0.150 m on the 0.30 walls (812 corners), 0.175 on the 0.35 (152),
0.125 on the 0.25 (24). Half the thickness at three different thicknesses is
a rule, not a tolerance.

WHAT THIS DOES
--------------
1. `_emit_wall_run` grows `inset` and `corners`, both defaulted OFF. It has
   TWO callers -- `_exterior` and the interior-partition pass at :1387 -- and
   only the exterior one asks for either, so partitions are untouched by
   construction rather than by hope.
2. `inset` pulls the SOLID spans back from each end. Openings do NOT move:
   they are positioned in `_exterior` as a fraction of the full run and
   arrive here already placed. That is the whole reason the inset lives at
   this seam instead of in the run length -- shortening the run would slide
   every door inward and change the gameplay anchors of every building.
3. `corners` seats one post at each end of the run, centred on the run's own
   end coordinate so it spans the perpendicular wall's full thickness.

WHY N/S WINS THE CORNER
-----------------------
Two runs meeting at a corner must not both fill it. Giving it to one axis
makes the winner DETERMINISTIC rather than arbitrary, and N/S is the axis
whose runs already carry the building's long dimension. `corners=(axis == 0)`
is the whole of that decision.

WHY THE POST COSTS NO NEW GEOMETRY
----------------------------------
It is emitted `size_mod="end"`, so `_slot_typename` returns `wallEnd` -- the
ONE species Deli Counter scales, "authored as a UNIT box and the size rides
as a per-slot scale: one module fits every remainder" (`_record_wall_slot`).
A `t x t` post is that unit box at scale `[t, t, storey_h]`. Zoo's
`exact = typ != "wallEnd"` gives it unit treatment with no change in that
repo, no new stem, and no new GLB in any kit -- one more instance of geometry
every kit already carries.

Zoo HAS an authored corner (`wallCorner`, recipe + genome, dated 2026-07-14,
never once requested -- roadmap item 64). It is deliberately NOT used here:
an L cannot ride the unit-box scale, because scaling a leg scales its
thickness with it, so it is structurally exact-fit at 18 modules per theme
and style. Promoting these slots to it later is one function in each repo.

THE EDGE CASE, MEASURED
-----------------------
An opening whose aperture already reached into the pulled-back zone would
end up intersecting the new post. Across all 124 buildings: 0 of 1088
exterior openings come within a half-thickness of their run's end.
`_wall_span`'s own `if L <= 0.05: return k` already absorbs a degenerate
span, so there is no negative-length path either.

WHAT THIS DOES NOT FIX
----------------------
The ROOF still spans centreline to centreline (`roof_..._w3400_d2400` on a
34.3 x 24.3 m outer footprint), so the outer half-thickness of the whole wall
ring stays uncapped. That is pre-existing, unchanged by this, and not what
item 58 measured.

THE LOCK WILL FIRE. This changes collision on every building, which is
exactly what `functional_shell_locked` protects. Re-approval is correct here,
not a workaround.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

OLD_RUN = '''    def _emit_wall_run(self, vbase, cbase, center, size, axis, holes, material):
        """Walk the run left->right: solid spans become wall segment(s),
        each opening becomes its own piece. Every emitted object is a named
        visual+collision pair = an art-pass swap slot."""
        full = size[0] if axis == 0 else size[1]
        carve = sorted(holes, key=lambda hh: hh["u"])
        cursor = -full / 2.0
        k = 0
        for j, h in enumerate(carve):
            left = h["u"] - h["w"] / 2.0
            k = self._wall_span(vbase, cbase, center, size, axis,
                                cursor, left, k, material)
            self._opening_piece(vbase, cbase, center, size, axis, h, j, material)
            cursor = max(cursor, h["u"] + h["w"] / 2.0)
        self._wall_span(vbase, cbase, center, size, axis,
                        cursor, full / 2.0, k, material)
'''

NEW_RUN = '''    def _emit_wall_run(self, vbase, cbase, center, size, axis, holes, material,
                       inset=0.0, corners=False):
        """Walk the run left->right: solid spans become wall segment(s),
        each opening becomes its own piece. Every emitted object is a named
        visual+collision pair = an art-pass swap slot.

        `inset` pulls the SOLID spans back from each end of the run. Openings
        do NOT move with it: they are positioned in `_exterior` as a fraction
        of the full run and arrive here already placed. That is why the inset
        lives at this seam rather than in the run length -- shortening the run
        would slide every door inward and change every building's gameplay
        anchors. Measured before it was relied on: 0 of 1088 exterior openings
        in the shipped library reach within a half-thickness of their run's
        end, so no aperture lands in the pulled-back zone.

        `corners` seats one post at each END of the run, centred on the run's
        own end coordinate so it spans the perpendicular wall's full
        thickness. Two runs meeting at a corner must not both fill it, so ONE
        axis owns it -- `_exterior` gives it to N/S, which makes the winner
        deterministic rather than arbitrary. Roadmap item 58.

        Both default OFF. The interior-partition pass calls this too and asks
        for neither, so partitions are untouched by construction.
        """
        full = size[0] if axis == 0 else size[1]
        thick = size[1] if axis == 0 else size[0]
        carve = sorted(holes, key=lambda hh: hh["u"])
        cursor = -full / 2.0 + inset
        k = 0
        for j, h in enumerate(carve):
            left = h["u"] - h["w"] / 2.0
            k = self._wall_span(vbase, cbase, center, size, axis,
                                cursor, left, k, material)
            self._opening_piece(vbase, cbase, center, size, axis, h, j, material)
            cursor = max(cursor, h["u"] + h["w"] / 2.0)
        k = self._wall_span(vbase, cbase, center, size, axis,
                            cursor, full / 2.0 - inset, k, material)
        if corners:
            # `size_mod="end"` makes `_slot_typename` return `wallEnd`, the one
            # species Deli Counter scales -- a unit box sized per slot. So the
            # post adds no module to any kit, only another instance of geometry
            # every kit already carries. The `_seg{k}` name keeps
            # `_record_wall_slot`'s `vname.rsplit("_seg", 1)[0]` returning this
            # run's wall, so the post groups with the run that owns it.
            for cu in (-full / 2.0, full / 2.0):
                self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}",
                              center, size, axis, cu, thick,
                              center[2], size[2], role="wall",
                              material=material, size_mod="end")
                k += 1
'''

OLD_CALL = '''                if self._modular_on():
                    self._emit_wall_run(name, col_name, c, size, axis, holes, mat)
'''

NEW_CALL = '''                if self._modular_on():
                    # Roadmap 58: the run stops at the perpendicular wall's
                    # INNER face and a post seats the corner, instead of the
                    # run ending on that wall's centreline and leaving the
                    # outer quadrant to nobody. N/S owns the corner so the two
                    # runs meeting there cannot both fill it.
                    self._emit_wall_run(name, col_name, c, size, axis, holes,
                                        mat, inset=wt / 2.0,
                                        corners=(axis == 0))
'''

OLD_SPAN = '''        n = int((L + 1e-6) // M)         # whole modules
        x = a
        for _ in range(n):
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, x + M / 2.0, M, cz, H, role="wall",
                          material=material, size_mod="full")
            x += M
            k += 1
        rem = b - x
        if rem > 0.05:                   # end remainder (a 'wallEnd' partial)
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, x + rem / 2.0, rem, cz, H, role="wall",
                          material=material, size_mod="end")
            k += 1
        return k
'''

NEW_SPAN = '''        n = int((L + 1e-6) // M)         # whole modules
        rem = L - n * M
        # A remainder at or under the sliver threshold used to be dropped on
        # the floor, which does not tidy the run -- it opens a hole in it. The
        # threshold exists to keep degenerate meshes out, and the way to do
        # that without a hole is to let the LAST module eat the remainder.
        #
        # MEASURED, and this is why it ships beside the corner posts rather
        # than on its own: insetting a run by half a thickness shifts every
        # tile boundary, so remainders that used to clear 0.05 m stop clearing
        # it. Predicted across the shipped library, the corner change ALONE
        # takes `ENV_RUN_GAP` from 1 to 15 -- twelve new 0.050 m gaps and three
        # of 0.025 -- every one of them beside an opening or a run end, which
        # is the worst place for a 5 cm crack. With the remainder absorbed it
        # stays at 1, and that one is the pre-existing `auto_shop_a02` gap,
        # whose whole span is under the threshold and so has no module to
        # absorb into.
        #
        # The absorbed module is emitted `size_mod="end"` on purpose: a
        # `wallEnd` is the unit box Deli Counter scales, so an odd width costs
        # no new stem in the kit. Left as "full" it would mint a
        # `wall_<theme>_<style>_w205`-shaped module per absorbed run.
        absorb = n > 0 and 1e-9 < rem <= 0.05
        x = a
        for i in range(n):
            last = absorb and i == n - 1
            w = M + rem if last else M
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, x + w / 2.0, w, cz, H, role="wall",
                          material=material,
                          size_mod="end" if last else "full")
            x += w
            k += 1
        if not absorb and b - x > 0.05:  # end remainder (a 'wallEnd' partial)
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, x + (b - x) / 2.0, b - x, cz, H, role="wall",
                          material=material, size_mod="end")
            k += 1
        return k
'''

OLD_VER = 'KIT_VERSION = "0.101.2"'
NEW_VER = '''# 0.102.0: exterior runs inset by half a wall thickness and a `wallEnd` post
# seats each corner (roadmap 58) -- collision and visuals both move, so a
# rebuilt .glb differs, which is the bump condition stated above.
KIT_VERSION = "0.102.0"'''

CHANGES = [
    ("deli_counter.py", OLD_RUN, NEW_RUN),
    ("deli_counter.py", OLD_CALL, NEW_CALL),
    ("deli_counter.py", OLD_SPAN, NEW_SPAN),
    ("version.py", OLD_VER, NEW_VER),
    ("VERSION", "Deli Counter 0.101.2", "Deli Counter 0.102.0"),
]


def main(argv):
    """Changes are accumulated PER FILE before anything is written.

    The first version of this planned each change against the file as read
    from disk and wrote them in turn, so the two edits to `deli_counter.py`
    each started from the original text and the second write silently
    discarded the first -- 140,556 bytes, then 138,992. It was caught by
    re-running `--check` on the result, which found anchor one intact and
    anchor two gone. A patch that touches one file twice must thread the
    text through, and a patch nobody has re-checked has not been verified.
    """
    check = "--check" in argv
    texts, order = {}, []
    for name, old, new in CHANGES:
        p = HERE / name
        if not p.is_file():
            print(f"  MISSING: {p}")
            return 2
        if p not in texts:
            # bytes, then decode -- these files are LF and must stay LF.
            raw = p.read_bytes()
            if b"\r\n" in raw:
                print(f"  {name}: CRLF present; this patch writes LF and "
                      f"refuses to normalise a file it did not author")
                return 2
            texts[p] = raw.decode("utf-8")
            order.append(p)
        n = texts[p].count(old)
        if n != 1:
            print(f"  {name}: anchor found {n} times, expected exactly 1")
            print(f"    anchor starts: {old.splitlines()[0][:70]!r}")
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
