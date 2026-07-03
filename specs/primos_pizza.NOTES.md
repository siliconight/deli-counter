# primos_pizza — design notes (the Deli Counter showcase building)

**Primo's Pizza & Social Club.** A 1997 Delco corner pizzeria with an
illegal card room and cash count upstairs. This spec is the kit's proof of
concept: every feature Deli Counter has, used the way the game doc says the
game plays — *get the crew together, case the place, do dumb stuff, go
loud, take the score, survive the heat, get out.*

## The heist, told through architecture

**Case the place (before it goes hot).** The dining room is a
`public_entry` room: the crew walks in the front like customers. Booths,
arcade cabinet, payphone, the deli counter itself — the goofy-interaction
phase has furniture to happen at. Three `camera_socket`s and four
`patrol_point`s are the stealth layer to read: the dining camera watches
the register, the alley camera watches the roll door, the club camera
watches the tables.

**The score.** The count room sits above the kitchen: safe, count desk,
money rack, 12k and four bags. Three ways in, and every one is a different
plan: the **count door** off the upper hall (1.4 m — the loud assault
line), the **soft wall** from the social club (breach charge through
drywall while the card game screams), and the **dumbwaiter ladder** from
the kitchen (cash goes up, crew goes up — the quiet line). Route diversity
is structural: the heist pack verifies two interior-disjoint approaches.

**Survive the heat.** The count room is the holdout — 2–3 coverable
entries, safe and desk for cover — while the drill runs. The social club
is `fortifiable` (card tables, bar, jukebox: flip-a-table cover). The
upper hall has box stacks; the kitchen has the oven block and prep island.
No kill boxes anywhere: the audit's cover census passes without seeding.

**Get out.** Bags leave down the wide route: count door → upper hall →
switchback stair → 1.4 m hall door → the alley roll-up (2.6 m garage).
The carry graph is verified ≥ 1.2 m the whole way. Alternates for a crew
in trouble: the roof (parapet-lipped, ladder from the hall, breachable
hatch back down), the kitchen service door, or straight out a vaultable
dining window with the till money.

## Feature checklist (what this spec demos)

basement + 2 stories + roof · switchback stair (gentle 35°) · 3 ladders
(cellar, dumbwaiter, roof) · breachable roof hatch · parapet · every
opening kind: door / window (sill + vaultable) / garage / breach
soft_wall ×2 · tagged doors, corner-fed and center-fed mixed · rarity
stamp (`rare`) · objective (drill, 35 s) + 3 loot spawns (7 bags, 16.3k)
· extraction + attacker spawns + cameras + patrols · secure + extraction
zones · 25 authored volumes across 5 materials · ~1.9k tris, every piece
inside the poly budget

## Audit state (regenerate anytime)

    python check.py specs/primos_pizza.json          # 0 errors, 0 warnings
    python combat_audit.py specs/primos_pizza.json --rules all
    # 0 HIGH / 0 MED / 0 INFO -- core + heist + cqb + flow, no accepts

The three ENTRY-WARN crouch-only notes are the vaultable windows being
vaultable — windows are crouch entries by nature.

## Not walked yet

Structural estimates only. First walk checklist: the dumbwaiter climb
(kitchen → count room), the roof loop (ladder up, hatch drop back to the
hall), bag-carry width feel on the alley route, and the first slice from
the count door.
