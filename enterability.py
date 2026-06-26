"""
enterability.py  --  can a body actually get INTO this building?  (no Blender)
=============================================================================
Deli Counter builds shells for a game where you ENTER buildings -- you walk up,
open a door / vault a window / breach a wall, and the squad pushes in. A shell
with no opening a player can fit through is a sealed box: it validates clean
(geometry is fine, rooms are reachable FROM EACH OTHER) yet can't be played,
because nobody can get inside in the first place. Nothing else catches that.

This is the entry-side sibling of the reachability gate. Same philosophy as
guards.py: encode the judgment ("is there a way in?") so the tool enforces it
offline instead of someone discovering it on a walk. It returns (errors,
warnings) like the tactical analyzer and guards, so validate/check aggregate it.

GATE THE CLEAR-CUT CASE, WARN THE REST:
  - HARD ERROR: no usable ground-level exterior entry at all -> sealed box.
  - WARN: there's a way in, but it's awkward (crouch-only, breach-only,
    vault-only, or a tight squeeze) -- playable, but design should know.

What it CANNOT check offline (and says so): whether the swing/vault space is
physically clear of geometry on both faces. That's a walk-test fact, the same
class as the stair-overlap and ladder-collision bugs a walk caught. So a clean
pass means "nothing in the spec makes entry impossible," not "certified
walkable."

Thresholds come straight from the project scale guidelines (meters):
  player 1.8 m tall, crouch ~1.1-1.25 m, capsule radius 0.35-0.45 m (so a
  ~0.7-0.9 m gap is the passable width band); doorway min width 0.9-1.1 m;
  a sill within ~1.2 m of the floor is vault-up reachable from the ground.
"""

from __future__ import annotations

# --- body-fit thresholds (m), from docs/scale_guidelines.md --------------
MIN_PASS_WIDTH = 0.7     # below this, the default capsule can't fit at all
CLEAN_WIDTH    = 0.9     # doc's minimum doorway width; below = a tight squeeze
MIN_PASS_HEIGHT = 1.1    # below this, you can't even crouch through
STAND_HEIGHT   = 1.8     # at/above = walk in standing; between = crouch-only
VAULT_SILL_MAX = 1.2     # a bottom edge within this is vault-up reachable
LOW_WINDOW_SILL = 1.0    # a window this low reads as an openable/climb entry

# kinds that are entries by intent (you go through them on purpose)
_WALK_KINDS = ("door", "garage", "breach")


def classify_opening(op):
    """Classify one exterior opening as an entry candidate. Pure geometry +
    intent; no world position needed. Returns a dict of facts."""
    r = op.resolved()
    w, h, sill = r["width"], r["height"], r["sill"]
    fits_w = w >= MIN_PASS_WIDTH
    fits_h = h >= MIN_PASS_HEIGHT
    reachable = sill <= VAULT_SILL_MAX
    if op.kind in _WALK_KINDS:
        designated = True
    elif op.kind == "window":
        # a window is an entry only if it's meant to be one: flagged vaultable,
        # or sitting low enough to read as an openable/climb-through window.
        designated = bool(op.vaultable) or sill <= LOW_WINDOW_SILL
    else:
        designated = False
    valid = designated and fits_w and fits_h and reachable
    return {
        "kind": op.kind, "wall": None, "w": w, "h": h, "sill": sill,
        "designated": designated, "fits_w": fits_w, "fits_h": fits_h,
        "reachable": reachable, "valid": valid,
        "tight_w": MIN_PASS_WIDTH <= w < CLEAN_WIDTH,
        "crouch_only": MIN_PASS_HEIGHT <= h < STAND_HEIGHT,
        "standing": h >= STAND_HEIGHT,
        "is_door": op.kind in ("door", "garage"),
    }


def ground_entries(spec):
    """All ground-floor (story 0) exterior openings, classified, tagged by wall."""
    out = []
    for wall in spec.ext_walls:
        if wall.story != 0:
            continue
        for op in wall.openings:
            c = classify_opening(op)
            c["wall"] = wall.wall
            out.append(c)
    return out


def check(spec):
    """Return (errors, warnings). Errors fail the build; warnings inform.

    The walk-to-verify note about swing/vault clearance is NOT returned as a
    warning (it isn't a defect) -- validate prints it once as an info line."""
    errors, warnings = [], []
    ents = ground_entries(spec)
    valid = [e for e in ents if e["valid"]]

    # --- HARD GATE: sealed box -------------------------------------------
    if not valid:
        if not ents:
            errors.append(
                "sealed box: no exterior openings on the ground floor — nothing "
                "to enter through. Add a door (or a vaultable window / breach).")
        else:
            # there ARE openings but none works as an entry — say why
            reasons = []
            if any(not e["designated"] for e in ents):
                reasons.append("fixed windows that aren't vaultable")
            if any(e["designated"] and not e["fits_w"] for e in ents):
                reasons.append(f"openings narrower than {MIN_PASS_WIDTH} m")
            if any(e["designated"] and not e["fits_h"] for e in ents):
                reasons.append(f"openings shorter than {MIN_PASS_HEIGHT} m")
            if any(e["designated"] and e["fits_w"] and e["fits_h"]
                   and not e["reachable"] for e in ents):
                reasons.append(f"sills above {VAULT_SILL_MAX} m (out of vault reach)")
            why = "; ".join(reasons) or "no opening a player fits through"
            errors.append(
                "sealed box: no usable ground-level entry — "
                f"{why}. Add a door, lower a sill, widen an opening, or flag a "
                "window vaultable.")
        return errors, warnings  # nothing more to say if you can't get in

    # --- WARNINGS: there's a way in, but note the awkward shapes ---------
    if not any(e["is_door"] for e in valid):
        kinds = sorted({e["kind"] for e in valid})
        warnings.append(
            f"no standard door entry — the only way in is via {', '.join(kinds)}. "
            "Playable, but the squad can't just walk in the front.")
    if not any(e["standing"] for e in valid):
        warnings.append(
            "every entry is crouch-only (height < "
            f"{STAND_HEIGHT} m) — no standing walk-in.")
    for e in valid:
        if e["tight_w"]:
            warnings.append(
                f"tight entry on the {e['wall']} wall: {e['w']} m wide "
                f"(below the {CLEAN_WIDTH} m comfortable minimum).")
        if e["crouch_only"]:
            warnings.append(
                f"crouch-only entry on the {e['wall']} wall: {e['h']} m tall.")
    # a window flagged as an entry that won't actually work
    for e in ents:
        if e["kind"] == "window" and e["designated"] and not e["valid"]:
            warnings.append(
                f"window on the {e['wall']} wall reads as an entry "
                "(vaultable/low) but a body won't fit — widen/heighten it or "
                "drop the vaultable flag.")
    return errors, warnings


def summary(spec):
    """Intel dict for the scorecard: how many ways in, and of what kind."""
    ents = ground_entries(spec)
    valid = [e for e in ents if e["valid"]]
    return {
        "ground_openings": len(ents),
        "valid_entries": len(valid),
        "doors": sum(1 for e in valid if e["is_door"]),
        "standing_entries": sum(1 for e in valid if e["standing"]),
        "entry_walls": sorted({e["wall"] for e in valid}),
    }


# walk-to-verify line validate prints once (not a defect, so not a warning)
CLEARANCE_NOTE = ("entry swing/vault clearance on both faces is a walk-test "
                  "fact — offline can't confirm the space is physically clear.")
