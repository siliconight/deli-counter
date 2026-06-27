# WALL_SEGMENTATION.md

Module segmentation + opening decomposition — Deli Counter

**Status:** IMPLEMENTED in 0.35.0 (opt-in) · Phase A (opening decomposition) + Phase B (module
tiling) ship in `deli_counter.py` via `_emit_wall_run`; slot-key emission (step 4) is not yet built ·
pairs with `ASSET_SWAP_CONTRACT.md`

Goal: stop emitting a wall as one boolean-cut box, and instead emit a **run of module-sized wall
segments with each opening as its own piece** — `[wall][doorway][wall]`, `[wall][window][wall]` — so a
fixed themed prefab can swap 1:1 against each piece.

---

## The surprise: collision already does this

The visual wall is monolithic (`_box_with_holes` makes one box and boolean-subtracts a cutter per
opening). But **`_wall_collision` already walks the run and emits separate chunks** — full-height
jambs in the gaps between/flanking openings, plus per-opening sill / lintel / breach-panel. That
cursor walk *is* the segmentation algorithm. So the change isn't inventing decomposition — it's
making the **visual** side use the same walk the collision side already uses, and naming the pieces
as swap slots.

That reframes the work: replace `_box_with_holes` (boolean) + `_wall_collision` (chunked collision)
with **one unified emitter** that produces matched visual+collision segment pairs.

---

## Phase A — opening decomposition (the required change)

Walk the run, emit solid spans as `wall` pieces and openings as their own pieces. This is
`_wall_collision`'s jamb loop, generalized to emit visual + role + collision together.

```
def _emit_wall_run(name, col_name, center, size, axis, holes, material):
    full = size[0] if axis == 0 else size[1]          # run length
    carve = sorted(holes, key=lambda h: h["u"])        # all openings split the RUN (see windows note)
    cursor = -full / 2
    k = 0
    for j, h in enumerate(carve):
        left = h["u"] - h["w"] / 2
        k = _wall_span(name, col_name, center, size, axis, cursor, left, k)   # solid -> wall piece(s)
        _opening_piece(name, col_name, center, size, axis, h, j)             # doorway / window / breach
        cursor = h["u"] + h["w"] / 2
    _wall_span(name, col_name, center, size, axis, cursor, full / 2, k)       # trailing solid run
```

- `u` is the opening centre offset from the wall centre (range `-full/2 .. +full/2`), exactly as
  `_opening_to_hole` already emits it. `_record_openings` still runs unchanged — it keys off the
  opening, not the wall geometry, so sockets + gameplay.json opening entries are untouched.
- Each `wall` span and each opening piece gets its own name → its own `surface_roles` entry
  (`wall` / `doorway` / `window`) → its own slot in the manifest.

**Windows now split the run too (deliberate change).** Today windows don't carve the visual wall (it
stays solid behind). For `[wall][window][wall]` and a swappable window prefab, the window becomes its
own piece occupying the span — *but the window piece carries solid collision*, so the shell stays
exactly as sealed as before (vaulting through is still game code, same as today). Nothing about
enterability changes; only the geometry is now decomposed. Call this out in the changelog.

`_opening_piece` emits, grouped under one `{name}_open{j}` slot:

- **doorway** — lintel above the opening (and frame if you want a greybox read); the gap is a **void**
  (no collision), so it's walkable. role `doorway`.
- **window** — sill below + lintel above + a solid pane box across the span (sealed). role `window`.
- **breach** — the existing removable `BREACHPANEL` (visual + collision; game deletes to open). role
  `breach`.

The lintel/sill chunks already exist verbatim in `_wall_collision`; they just move under the opening
piece's name instead of the collision name.

---

## Phase B — module tiling of the solid spans

`_wall_span(a, b)` decides how a solid run becomes pieces. Phase A makes it one box; Phase B tiles it.

```
def _wall_span(name, col_name, center, size, axis, a, b, k):
    L = b - a
    if L <= 0.05: return k
    if not self.s.modular:
        _wall_chunk(name, col_name, center, size, axis, (a+b)/2, L, k, size_mod="full")
        return k + 1
    M = self.s.module          # e.g. 2.0, must be a multiple of grid (0.5)
    n = int(round(L / M, 3) // 1)               # whole modules
    x = a
    for _ in range(n):
        _wall_chunk(..., (x + x+M)/2, M, k, size_mod="full"); x += M; k += 1
    rem = b - x
    if rem > 0.05:
        _wall_chunk(..., (x + b)/2, rem, k, size_mod="end")    # partial / wallEnd
        k += 1
    return k
```

**Where boundaries fall — pick one, recommend the first:**

- **Snap openings to the module grid (`--modular` default).** `_opening_to_hole` snaps `op.pos*run`
  with `msnap(v)=round(v/M)*M` instead of the 0.5 m grid. Then every solid span is a whole number of
  modules → no partials except possibly one `end` piece where the wall length itself isn't a module
  multiple. Cleanest tiling; the cost is openings can't sit at arbitrary positions.
- **Don't snap openings.** Tile each span from its own start `a`; accept one partial `end` piece per
  span, adjacent to each opening. More placement freedom, more partial pieces to author.

Either way, tile each span from a **consistent datum** (the wall start `-full/2`, or the span start
`a`) so seams are deterministic and reproducible across rebuilds.

`M` must divide the 0.5 m grid evenly (2.0 does). Building footprints that aren't module multiples
get one `end` piece per wall — fine, just author a `wallEnd` variant.

---

## Per-segment collision pairing

`_wall_chunk` emits a visual box (role-tagged) **and** its collision sibling, co-located, name-paired:

```
visual:     {name}_seg{k}            role -> surface_roles
collision:  {col_name}_seg{k}        via _col_box (same centre/size, spec collision mode)
```

- **wall segment** → solid collision sibling, spec's default mode (`col_suffix`).
- **doorway void** → no collision in the gap (walkable); only the lintel gets a collision box.
- **window piece** → solid collision across the span (sealed), matching today's behaviour.
- **breach panel** → removable collision + visual, unchanged.

Name parity (`_seg{k}` ↔ `_seg{k}`) is what keeps the single-GLB export's visual and collision
together and survives any future per-file split. **This is the walk-to-verify hotspot:** segment
seams are where gaps (light-leak / z-fight), double-walls (overlap at a boundary), and collision
gaps at door-void edges hide — the same class as the stair-overlap and ladder bugs. Offline checks
can't catch it; budget one walk when this lands.

---

## Slot keys fall out for free

Each emitted piece already knows everything `ASSET_SWAP_CONTRACT.md` needs: `role` (wall / doorway /
window / breach), `module` (its `[clen, H, thick]`), `size_mod` (`full` / `end` / a width bucket for
openings), `facing` (the `wname` N/S/E/W), `pivot` (centred — `_box` origins are already centred),
and the transform. Emitting the slot is just collecting those at `_wall_chunk` time — the placements
manifest with the swap fields, nothing new computed.

---

## What changes, concretely

- **New** `_emit_wall_run` + `_wall_span` + `_wall_chunk` + `_opening_piece` (the unified emitter;
  lifts and generalizes the `box()` helper already inside `_wall_collision`).
- **`_exterior`** — replace the `_box_with_holes(...)` + `_wall_collision(...)/_col_box(...)` pair
  with a single `_emit_wall_run(...)` call. Same for the `auto_exterior` / explicit-wall branching.
- **`_partitions`** — identical swap (it uses the same `_box_with_holes` + `_wall_collision` pair).
- **`_box_with_holes` / `_wall_collision`** — retire, or keep as the non-modular path (see gating).
- **`_opening_to_hole`** — add `msnap` when modular; otherwise unchanged.
- **Spec** — add `modular: bool` and `module: float` (default off / 2.0). New optional fields.

---

## Gating, schema, byte-identity

Gate the whole thing behind **`modular` (off by default)**, consistent with DC's everything-optional
rule. Default builds keep the boolean `_box_with_holes` path → existing specs rebuild **byte-identical**,
no forced churn. Modular is opt-in per spec (or `new_level.py --modular`).

Bump `SCHEMA_VERSION` 1.8.0 → 1.9.0 (new optional spec fields) and `KIT_VERSION` (geometry output
changes when modular is on). Record in CHANGELOG that windows now decompose under modular.

---

## Suggested build order

1. **Phase A behind `--modular`** — opening decomposition only (`_wall_span` = one box per solid run,
   no tiling). Gives `[wall][doorway][wall]`, low risk, and is independently walkable.
2. **Walk it** — verify seams, door voids, window sealing on one preset (corner_deli is the obvious
   first, it's a heist with openings).
3. **Phase B** — add module tiling + the opening-snap rule + `wallEnd` partials.
4. **Emit slot keys** — attach the `ASSET_SWAP_CONTRACT` fields per chunk (manifest write).

Phases 1 and 3 are the only real geometry work; 2 is the walk that catches the seam bugs; 4 is
additive output.
