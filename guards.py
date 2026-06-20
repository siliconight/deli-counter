"""
guards.py  --  hard model/repo-integrity checks for CI
======================================================
These encode judgment that used to live in a human's head and a manual grep,
so the tool enforces it offline without anyone remembering to. Two checks:

1. IP-NAME GUARD (repo integrity) -- Deli Counter is a de-branded open-source
   tool. No inspiration/brand names may ship in a spec's author-controlled
   strings (name, room ids, marker ids/tags, zone ids, opening tags). This is
   a HARD gate: a match fails the build. An allowlist handles legitimate words
   that merely contain a flagged substring.

2. STEP-RISE BUDGET (model integrity) -- a stair whose per-step rise exceeds
   the player's MAX_STEP_UP is physically unclimbable: a broken model. Generated
   stairs are ~0.18 m, but a hand-authored spec with a large step_rise or a
   tiny n_steps could bust it. HARD gate against the 0.5 m budget.

Both raise nothing; they return (errors, warnings) lists like the tactical
analyzer, so check.py can aggregate and fail on errors.
"""

import re

# ---------------------------------------------------------------------------
# IP-NAME GUARD
# ---------------------------------------------------------------------------
# Brand / inspiration terms that must never appear in shipped specs. Matched
# case-insensitively as whole-ish tokens (word boundaries) to limit false hits.
IP_TERMS = [
    "delco", "gabagool", "payday", "rainbow six", "left 4 dead", "l4d",
    "siege", "scarface", "montana", "valve",
]

# Legitimate strings that contain a flagged substring but are NOT brand uses.
# Add here when a real false positive appears (keep it tight — each entry is an
# explicit exception to the guard).
IP_ALLOWLIST = {
    # e.g. "siegfried_hall",  # a room name that legitimately contains 'sieg'
}


def _iter_strings(spec):
    """Yield (location, string) for every author-controlled string in a spec
    that could carry a brand name."""
    yield ("name", spec.name or "")
    for r in getattr(spec, "rooms", []) or []:
        yield (f"room.id", r.id or "")
        if getattr(r, "role", None):
            yield ("room.role", r.role)
    for m in getattr(spec, "markers", []) or []:
        yield ("marker.id", getattr(m, "id", "") or "")
        yield ("marker.type", getattr(m, "type", "") or "")
        meta = getattr(m, "meta", None) or {}
        for k, v in meta.items():
            if isinstance(v, str):
                yield (f"marker.meta.{k}", v)
    for z in getattr(spec, "zones", []) or []:
        yield ("zone.id", getattr(z, "id", "") or "")
    for o in getattr(spec, "objectives", []) or []:
        yield ("objective.id", getattr(o, "id", "") or "")
    for ld in getattr(spec, "loot", []) or []:
        yield ("loot.id", getattr(ld, "id", "") or "")
    # opening tags on exterior walls and partitions
    for w in getattr(spec, "ext_walls", []) or []:
        for op in w.openings:
            if getattr(op, "tag", None):
                yield ("ext_opening.tag", op.tag)
    for p in getattr(spec, "partitions", []) or []:
        for op in p.openings:
            if getattr(op, "tag", None):
                yield ("partition_opening.tag", op.tag)


def check_ip_names(spec):
    """Hard gate: returns (errors, warnings). Any brand term in an author-
    controlled string is an error unless the exact string is allowlisted."""
    errors, warnings = [], []
    # Match brand terms as substrings bounded by non-letter chars OR string
    # ends — so 'payday_vault', 'delco-deli', 'final_scarface' all hit, but a
    # term embedded inside a longer *word* (letters on both sides) does not,
    # which limits false positives. Spaces in multiword terms are matched
    # flexibly against space/underscore/hyphen.
    patterns = []
    for t in IP_TERMS:
        core = re.escape(t).replace(r"\ ", r"[ _-]")
        patterns.append((t, re.compile(r"(?<![a-z])" + core + r"(?![a-z])",
                                       re.IGNORECASE)))
    seen = set()
    for loc, s in _iter_strings(spec):
        if not s or s.lower() in IP_ALLOWLIST:
            continue
        for term, pat in patterns:
            if pat.search(s):
                key = (loc, s, term)
                if key in seen:
                    continue
                seen.add(key)
                errors.append(
                    f"IP-NAME: '{term}' found in {loc} = '{s}'. Deli Counter is "
                    f"de-branded; rename it. (If this is a legitimate word, add "
                    f"'{s.lower()}' to IP_ALLOWLIST in guards.py.)")
    return errors, warnings


# ---------------------------------------------------------------------------
# STEP-RISE BUDGET (model integrity)
# ---------------------------------------------------------------------------
MAX_STEP_UP = 0.5        # m — the recommended player step-up budget
STEP_RISE_WARN = 0.4     # m — approaching the budget; worth a heads-up

# default target rise the builder aims for (mirrors spec_types default)
DEFAULT_STEP_RISE = 0.2


def _stair_rise(spec, st):
    """Replicate the builder's per-step rise: floor height / step count, where
    step count = explicit n_steps or round(H / target step_rise), clamped."""
    spans = abs(st.to_story - st.from_story)
    H = spans * spec.story_height
    if H <= 0:
        return 0.0
    target = getattr(st, "step_rise", None) or DEFAULT_STEP_RISE
    n = getattr(st, "n_steps", None) or max(6, min(40, round(H / target)))
    n = max(1, n)
    return H / n


def check_step_rise(spec):
    """Hard gate on unclimbable stairs: a per-step rise over MAX_STEP_UP is a
    broken model (the player physically can't ascend). Warn as it approaches."""
    errors, warnings = [], []
    for i, st in enumerate(getattr(spec, "stairs", []) or []):
        rise = _stair_rise(spec, st)
        if rise > MAX_STEP_UP:
            errors.append(
                f"STEP-RISE: stair #{i} rises ~{rise:.2f} m/step, over the "
                f"{MAX_STEP_UP} m climb budget — unclimbable. Increase n_steps "
                f"or lower step_rise.")
        elif rise > STEP_RISE_WARN:
            warnings.append(
                f"STEP-RISE: stair #{i} rises ~{rise:.2f} m/step, near the "
                f"{MAX_STEP_UP} m budget (target is ~{DEFAULT_STEP_RISE} m).")
    return errors, warnings


# ---------------------------------------------------------------------------
# AGGREGATE
# ---------------------------------------------------------------------------
def check_all(spec):
    """Run every guard. Returns (errors, warnings)."""
    errors, warnings = [], []
    for fn in (check_ip_names, check_step_rise):
        e, w = fn(spec)
        errors.extend(e)
        warnings.extend(w)
    return errors, warnings
