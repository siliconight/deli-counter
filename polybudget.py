"""
polybudget.py  --  offline polygon-count estimator + budget check
==================================================================
Deli Counter emits a level as a set of box-based meshes (walls, floors, stair
steps, partitions, props) plus boolean-cut openings. Because the geometry is
deterministic from the spec, we can ESTIMATE the triangle count without running
Blender — which means the poly budget can be checked offline, in CI, alongside
the other validators.

This reports tri counts as INTEL, in the same spirit as the tactical path
metrics: the tool makes models, and an artist may deliberately exceed a target.
The numbers are informational. The one thing it can flag is the art-director
**Environment/Module cap** — pieces that bust the hard ceiling are worth a
designer's eye — but it's a warning, never a build-blocking error.

Budgets (Environment/Module pieces), from the art direction:
    target 50-500 tris, cap 1,000 tris  -- per piece
A Deli Counter shell is made of many such pieces; we report per-collection
totals and the per-piece distribution, and flag any single piece over the cap.

Estimation model (matches deli_counter.py primitives):
    - a plain box (_box / _col_box)         = 12 tris (cube: 6 quads x 2)
    - a box with N rectangular holes        ~ 12 + N * HOLE_TRIS  (boolean cut
      replaces a face with a frame; ~16 tris added per hole, empirically)
    - a stair = one box per step            = 12 * n_steps
    - a ladder = rails + rungs (boxes)      = 12 * parts
    - markers are Empties                    = 0 tris (no mesh)
Counts are estimates; the authoritative number comes from Blender. Treat these
as a guardrail, not gospel.
"""

from dataclasses import dataclass

BOX_TRIS = 12
HOLE_TRIS = 24           # extra tris a single boolean-cut opening adds.
                         # Calibrated against a real exported GLB (corner_deli:
                         # 30 openings + 1 slab hole accounted for ~762 tris over
                         # the base boxes -> ~24-25 tris/cut).

# Environment/Module budget (per piece)
ENV_TARGET_LO = 50
ENV_TARGET_HI = 500
ENV_CAP = 1000


@dataclass
class PieceEstimate:
    name: str
    tris: int
    kind: str            # 'wall', 'floor', 'stair', 'partition', 'prop', ...


def _box_tris(n_holes=0):
    return BOX_TRIS + n_holes * HOLE_TRIS


def estimate(spec):
    """Return (pieces, summary). pieces is a list of PieceEstimate for the
    VISUAL geometry (what ships); summary aggregates totals + budget flags.
    Pure Python — no bpy. Mirrors what deli_counter.py's builder emits."""
    pieces = []

    # exterior walls — one box per wall segment, plus holes for openings
    for w in spec.ext_walls:
        n_holes = len(w.openings)
        pieces.append(PieceEstimate(
            f"ext_{w.wall}_{w.story}", _box_tris(n_holes), "wall"))

    # partitions — one box per partition, holes for openings
    for i, p in enumerate(spec.partitions):
        n_holes = len(p.openings)
        pieces.append(PieceEstimate(
            f"partition_{i}_{p.story}", _box_tris(n_holes), "partition"))

    # floor slabs — one per story (+ basement), each cut by slab holes
    stories = sorted({r.story for r in spec.rooms}) if spec.rooms else \
        list(range(0, spec.n_stories))
    if spec.has_basement and -1 not in stories:
        stories = [-1] + stories
    n_slab_holes = {}
    for h in spec.slab_holes:
        n_slab_holes[h.story] = n_slab_holes.get(h.story, 0) + 1
    for st in stories:
        pieces.append(PieceEstimate(
            f"slab_{st}", _box_tris(n_slab_holes.get(st, 0)), "floor"))

    # roof / parapets
    for para in spec.parapets:
        # a parapet ring ~ 4 boxes
        for side in range(4):
            pieces.append(PieceEstimate(
                f"parapet_{para.story}_{side}", BOX_TRIS, "parapet"))

    # stairs — one box per step; step count from floor height / step_rise
    for si, st in enumerate(spec.stairs):
        spans = abs(st.to_story - st.from_story)
        H = spans * spec.story_height
        rise = getattr(st, "step_rise", None) or 0.18
        n_steps = st.n_steps or max(6, min(40, round(H / rise)))
        for step in range(n_steps):
            pieces.append(PieceEstimate(
                f"stair{si}_step{step}", BOX_TRIS, "stair"))

    # ladders — rails (2) + rungs (one per rung_spacing over the rise)
    for li, ld in enumerate(spec.ladders):
        spans = abs(ld.to_story - ld.from_story)
        H = spans * spec.story_height
        spacing = getattr(ld, "rung_spacing", None) or 0.3
        n_rungs = max(2, int(H / spacing))
        for part in range(2 + n_rungs):
            pieces.append(PieceEstimate(
                f"ladder{li}_part{part}", BOX_TRIS, "ladder"))

    # ramps — one box each
    for ri, rp in enumerate(spec.ramps):
        pieces.append(PieceEstimate(f"ramp_{ri}", BOX_TRIS, "ramp"))

    # vault ledges — one box each
    for vi, vl in enumerate(spec.vault_ledges):
        pieces.append(PieceEstimate(f"vault_ledge_{vi}", BOX_TRIS, "prop"))

    # volumes (props / cover / kitbash placeholders) — one box each, UNLESS the
    # volume references an imported asset, which we cannot estimate (flag it).
    imported = []
    for v in spec.volumes:
        asset = getattr(v, "asset", None) or getattr(v, "import_path", None)
        if asset:
            imported.append(v.name)
            # unknown tri count — record as an unestimatable piece
            pieces.append(PieceEstimate(v.name, -1, "imported"))
        else:
            pieces.append(PieceEstimate(v.name, BOX_TRIS, "prop"))

    # summary
    estimable = [p for p in pieces if p.tris >= 0]
    total = sum(p.tris for p in estimable)
    over_cap = [p for p in estimable if p.tris > ENV_CAP]
    biggest = max(estimable, key=lambda p: p.tris) if estimable else None

    summary = {
        "total_tris_estimate": total,
        "piece_count": len(pieces),
        "estimable_pieces": len(estimable),
        "imported_unestimatable": imported,
        "over_env_cap": [(p.name, p.tris) for p in over_cap],
        "biggest_piece": (biggest.name, biggest.tris) if biggest else None,
        "env_cap": ENV_CAP,
        "env_target": [ENV_TARGET_LO, ENV_TARGET_HI],
    }
    return pieces, summary


def format_summary(spec_name, summary):
    s = summary
    lines = [f"  poly estimate for {spec_name}:"]
    lines.append(f"    ~{s['total_tris_estimate']} tris across "
                 f"{s['estimable_pieces']} mesh pieces "
                 f"(Environment budget: {s['env_target'][0]}-{s['env_target'][1]} "
                 f"target, {s['env_cap']} cap per piece)")
    if s["biggest_piece"]:
        nm, t = s["biggest_piece"]
        lines.append(f"    biggest piece: {nm} (~{t} tris)")
    if s["over_env_cap"]:
        names = ", ".join(f"{n} (~{t})" for n, t in s["over_env_cap"])
        lines.append(f"    OVER CAP ({s['env_cap']} tris): {names}")
    if s["imported_unestimatable"]:
        lines.append(f"    imported assets (count separately in Blender): "
                     f"{', '.join(s['imported_unestimatable'])}")
    return "\n".join(lines)


def budget_warnings(summary):
    """Return a list of neutral-but-worth-noting strings. Per the model-not-
    gameplay principle these are intel, surfaced as warnings (never errors):
    the only thing flagged is busting the hard Environment cap, plus imported
    assets we couldn't estimate."""
    out = []
    for name, tris in summary["over_env_cap"]:
        out.append(f"piece '{name}' ~{tris} tris exceeds the Environment cap "
                   f"({summary['env_cap']}); consider splitting or simplifying")
    if summary["imported_unestimatable"]:
        out.append("imported asset(s) not poly-estimated here — verify their "
                   "tri counts against the budget in Blender: "
                   + ", ".join(summary["imported_unestimatable"]))
    return out
