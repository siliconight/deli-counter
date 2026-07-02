# DESIGN_RULES — the genre grammars behind `combat_audit --rules`

Three games, three grammars, one spec model. Each rule below states the
lesson from the source game, the rule in Deli Counter vocabulary, and what
the audit actually measures (every measured rule has a finding code). Rules
the audit can't measure are marked JUDGMENT — they're for the author and the
walk, not the tool. Run with:

    python combat_audit.py --preset bank --rules auto     # packs by mode
    python combat_audit.py specs/x.json --rules all       # everything
    python combat_audit.py --all-presets --rules heist,cqb

`auto` applies: heist-mode specs → heist + cqb + flow; survival/assault →
flow + cqb. All pack findings respect `audit_accept`.

---

## The heist grammar (PayDay 2)

A heist is a loop, not a line: get in, do the thing under pressure, get the
bags out. The map succeeds if PLANS differ between crews and runs.

**H_ONE_ROUTE — plans must be able to differ.**
If every route from the entries to the objective passes through the same
interior rooms, there is exactly one plan and every run is that plan. The
audit computes interior-disjoint routes on the room graph; fewer than two is
the flag. Fixes that work in this kit: a breach `soft_wall` on a second
approach, a vaultable window, a ladder — anything that opens a second
disjoint spine. (Currently open: `office/exec_suite` funnels; both verticals
share the same floor-1 spine.)

**H_NO_HOLDOUT — the drill needs a room to defend.**
The objective-wait phase (drill, hack, timer) is a fight in place. The
objective room or a neighbor must work as a holdout: 2–3 coverable entries
(1 is a camping closet, 4+ is indefensible), ≥ 12 m², and something to
shelter behind (`fortifiable` role or actual cover solids). Measured
directly. (Currently open: `warehouse/office`.)

**H_CARRY_PINCH — bags don't fit through squeezes.**
The loot leaves through doors. From every objective there must be a route
to a ≥ 1.4 m exterior egress using only ≥ 1.2 m openings — stairs carry
bags, ladders don't (the width-filtered graph reflects that). If the only
way out is a pinch, the exfil is a turnstile under fire.

**H_NO_STEALTH — a heist map should have a stealth layer to beat.**
`camera_socket` and `patrol_point` markers are the stealth vocabulary. A
heist spec with neither is loud-only by construction. INFO, not a demand.

**JUDGMENT:** escalation staging (where responders arrive as waves build —
site-level, Lot's `responder_spawn` markers own it); which walls should be
soft (drama says: the one the crew doesn't expect); civilian placement.

---

## The CQB grammar (Ready or Not)

The door is the tactical unit. Every room is a question asked at its
threshold; the grammar is about what the entry team can know before
committing.

**Feed types (measured, reported in findings).**
A *corner-fed* door (≤ 1.5 m from a corner) gives the entry one hard angle
to solve; a *center-fed* door exposes it to both flanks at once. Neither is
wrong — center-fed is harder, corner-fed is cleaner — but:

**C_FEED_MONOTONE — variety is the rule.**
If every interior door in the building is the same feed type, every room
clears identically. INFO census.

**C_NO_PIE — thresholds need standoff.**
Pieing a door takes floor space on the approach side. If the approach room
is < 1.6 m deep at the door, the stack breaches blind from a squeeze.

**C_NAKED_ROOM / C_BLIND_ROOM — the first slice should answer 50–90%.**
From the best doorway into a hot room (objective/fortifiable), the visible
fraction of the room is the "first slice." Every-door-sees-everything
(> 97%, no cover) means the room is a formality; best-door-sees-< 35%
means every entry is grenade-bait into hard corners. The band between is
where clearing is a decision. Measured by 2-D raycast from the threshold
against ≥ 0.9 m solids; judged on the BEST door because the team picks its
threshold.

**JUDGMENT:** door swing direction and wedgeability (game code owns doors);
mirror-under-door sight leaks; light/dark thresholds (art pass); exact
hard-corner placement (walk it — the audit only bounds the fraction).

---

## The flow grammar (Left 4 Dead 2)

Co-op flow is directed: one dominant path players never have to think
about, compression and release along it, and arenas where the horde can
actually arrive.

**F_FLAT_RHYTHM — alternate tight and open.**
Along the entry→objective path, room scale should change. If every step is
within ~1.4× of the last, the run reads as one long corridor — no dread in
the tight parts, no relief in the open ones. Measured on the golden-path
area sequence.

**F_BRANCH_OVERLOAD — decision points should be shallow.**
A main-path room with 5+ connections is a wayfinding puzzle mid-fight.
INFO per room.

**F_ARENA_STARVED — holdouts need ingress.**
A horde arena (finale rooms; objective/fortifiable rooms in
survival/assault modes) with fewer than 3 ways in makes the horde
single-file: a shooting gallery, not a stand. Heist drill rooms are
exempt — the heist grammar WANTS 2–3 coverable entries there, and the two
rules would otherwise fight.

**F_FEW_HORDE_SPAWNS — give the director choices.**
Survival specs with < 3 `horde_spawn` markers produce same-y waves. INFO.

**JUDGMENT:** lighting-as-signposting, safe-room placement rhythm across a
CAMPAIGN (site/Lot level — `site_pacing.py` owns travel legs), crescendo
trigger placement, and the actual second-to-second horde feel. Walk it.

---

## How the grammars stack

The core audit is the floor (reachability, loops, killboxes, widths,
verticals). The packs are genre ceilings on top of it. They deliberately
overlap: a PayDay holdout is a Ready or Not room with a feed type and a
first-slice number, sitting on an L4D2 path with a rhythm. When two
grammars disagree (heist holdout entries vs horde arena ingress), the
spec's `mode` decides which rule applies — that conflict is resolved in
code, not left to the reader.

Everything here is a structural estimate. The audit exists to make the
walk cheaper, not to replace it.
