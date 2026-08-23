# Interactive Fixtures — the shared contract

**Doors, breachable walls, and anything whose state all players must agree on.**

This is the contract between three layers of the pipeline. The same file lives in
the **zoo** repo — keep them in sync. Deli Counter emits it; Zoo builds the art
it points at; the game (`DELCO_DANGEROUS`) reads it to replicate state.

---

## The one principle

**The contract describes STATE, never SYNCHRONIZATION.**

It says *what* is interactive, *what discrete states* it can be in, and *what
named transitions* move between them. It says **nothing** about who is
authoritative, how state replicates, tick rate, or interpolation. All of that is
the game's networking layer, chosen later.

That is the whole reason it stays network-solution agnostic. Deli Counter must
never emit a field that tells the netcode *how* to replicate.

---

## The model: a replicable state machine

Every interactive fixture is `(stable_id, states[], default, transitions[])` —
the **entire networked surface**. It maps onto any solution:

| Networking solution           | What it replicates                               |
|--------------------------------|--------------------------------------------------|
| Server-authoritative snapshot  | the current-state enum per `id`                  |
| Event / RPC                    | the named transition per `id`                    |
| Deterministic lockstep         | the input; every client runs the same transition |
| Rollback                       | the state enum is in the snapshot; transitions are deterministic |

Because the contract carries **both** the state set **and** the named
transitions, the game replicates whichever fits — and nothing here committed.

---

## The two files DC emits

### `<building>.slots.json` — art swap contract (Zoo reads this)

An interactive slot carries an `interactive` block (the art-facing view). Zoo
derives per-state art from the `_<state>` naming law:

```json
{
  "slot_id": "ext_0_N_open1",
  "role": "breach",
  "fit": { "dims": [1.5, 0.3, 2.2], "pivot": "center" },
  "current_ref": "breach_greybox_01",
  "interactive": {
    "id": "primos_pizza:if:2cf6a380",
    "kind": "breach_wall",
    "states": ["intact", "breached"],
    "default": "intact",
    "state_geometry": { "intact": "wall", "breached": "breach" },
    "collision_per_state": { "intact": true, "breached": false }
  }
}
```

### `<building>.gameplay.json` — netcode-owned (the game reads this)

The `interactives` array, one self-sufficient state machine per fixture:

```json
"interactives": [
  {
    "id": "primos_pizza:if:89318e3e",
    "kind": "door",
    "slot_ref": "ext_0_S_open0",
    "transform": { "translation": [6.0, -4.0, 1.1], "rot_y": 180 },
    "states": ["closed", "open"],
    "default": "closed",
    "transitions": [
      { "event": "toggle", "from": "closed", "to": "open" },
      { "event": "toggle", "from": "open",   "to": "closed" }
    ],
    "reversible": true,
    "source": "inferred",
    "building": "primos_pizza"
  },
  {
    "id": "primos_pizza:if:2cf6a380",
    "kind": "breach_wall",
    "slot_ref": "ext_0_N_open1",
    "transform": { "translation": [3.0, 8.0, 1.1], "rot_y": 0 },
    "states": ["intact", "breached"],
    "default": "intact",
    "transitions": [ { "event": "breach", "from": "intact", "to": "breached" } ],
    "reversible": false,
    "source": "inferred",
    "building": "primos_pizza"
  }
]
```

The two share the `id`; the game joins on it. `slot_ref` points at the slot in
`slots.json` where the art lives.

---

## The composed scene ships both states

`themed_tscn` (the art-pass composer) instances the DEFAULT state's module
visible, and every non-default state whose geometry differs as a HIDDEN
sibling at the same transform — `<slot_id>_<state>`, `visible = false`. Both
nodes carry `metadata/interactive_id` (this contract's `id`) and
`metadata/interactive_state`, so netcode finds the pair without parsing node
names. The runtime swap the game owns is therefore: flip visibility, and
honor `collision_per_state` if it chooses — the art is already loaded,
nothing streams. A state sharing the default's species (a door's `open`)
gets no sibling; its motion is presentation (see Mid-states below). The
variant set is exactly what Zoo's `kit.slot_variants` builds —
`state_variant_stems` in `themed_tscn.py` is its composer-side mirror, and
the z-fight gate deliberately ignores the parked hidden siblings.

---

## Stable ids — the one thing to get right

`id` is the handle every client, snapshot, and saved game references. Deli
Counter derives it from the fixture's **place** —
`sha1(building, wall, story, kind, round(pos, 4))` — **never an array index**.

Openings on a wall are re-sorted by position during the geometry pass, so an
index-based id would be unstable. A position-based id is stable across a
re-greybox: adding an opening elsewhere doesn't renumber this one. Moving the
opening changes the id, which is correct — it's a new place. (`interactives.py`,
`interactive_id`.)

---

## Which openings are interactive (inference + authoring)

Deli Counter infers the common cases and lets the author override:

| Opening `kind` | Fixture       | By default          |
|----------------|---------------|---------------------|
| `door`, `garage` | `door` — `[closed, open]` | **inferred** (always) |
| `breach`       | `breach_wall` — `[intact, breached]`, `state_geometry {intact: wall, breached: breach}` | **inferred** (always) |
| `vault`        | `vault_door` — `[locked, unlocked, open, breached]`, `state_geometry {locked: vault_door, unlocked: vault_door, open: doorway, breached: breach}` | **inferred** (always) |
| `teller`       | `teller_window` — `[intact, shattered]` (solid barrier; shattered reuses the teller_line art) | **inferred** (always) |
| `safe_deposit` | `safe_deposit_boxes` — `[intact, drilled]` (solid box wall; drilled reuses the art) | **inferred** (always) |
| `window`       | `window` — `[intact, broken]` | only when authored `breakable: true` |

Per-opening override in the spec:

```json
{ "kind": "door", "pos": 0.4, "interactive": false }   // force non-interactive
{ "kind": "door", "pos": 0.0, "interactive": {          // custom machine (merged)
    "states": ["closed", "ajar", "open"] } }
{ "kind": "window", "pos": 0.2, "breakable": true }     // opt a window in
```

`interactive: false` forces it off; a dict is merged over the inferred machine
(or stands alone for a custom fixture). See `docs/AUTHORING.md`.

---

## Advisory hints stay advisory

`reversible`, `collision_per_state`, `material`, `breach_class` (and any future
`authority_hint` / `persist`) are **descriptions the netcode MAY honor or
ignore** — never instructions. The moment the contract tells the game *how* to
replicate, it stops being agnostic.

`material` says what the fixture's panel is made of (a window's pane is
`glass`; a breach panel inherits its host wall — drywall, brick_ext, ...);
`breach_class` says how a wall yields (`soft_wall` / `reinforceable`). The
game maps weapons to events with them: what shatters to small arms, what
needs a charge, what a charge must be shaped for. Authored values always
win; unauthored ones are derived at spec load from what every authored spec
already does by hand.

---

## Mid-states and continuous motion

Handle these with the **state set**, not networking concepts. A door that can be
ajar → `["closed", "ajar", "open"]`; a wall that cracks first →
`["intact", "damaged", "breached"]`. The *visual* swing of the door is
presentation the game interpolates locally; the networked truth stays the
discrete checkpoint. Never sync a float angle.

---

## Ownership

| Layer            | Owns                                                              |
|------------------|-------------------------------------------------------------------|
| **Deli Counter** | the seam: flags a slot interactive, assigns the stable `id`, emits both blocks, composes both states into the shipped scene (default visible, variants hidden). |
| **Zoo**          | the per-state art variants (via the `_<state>` naming law). Netcode-free. |
| **The game**     | the netcode: one replicated node per `id`, drives which variant renders. |

Deli Counter and Zoo stay offline and deterministic; they only expose the seam
so replication has a clean hook. DC never invents transitions the game must obey
beyond the reachable state graph, and never replicates anything itself.
