# Prose building-DSL — design sketch

**Status: design sketch for evaluation. Not built, not committed.** This explores
a human-readable authoring surface that compiles to a Deli Counter spec JSON — a
potential *fifth* on-ramp beside the interview, presets, hand-authored JSON, and
the GridMap sketch. The goal is to decide whether it's worth pursuing, not to
commit to it.

## Why (and the honest origin)

The external review's I-6 criticism: "JSON is a weak medium for geometry — humans
don't think in partition axes and coordinates." A spec author writes
`{"axis": "X", "pos": -8.0, "start": -14.0, "end": 14.0}` when they mean "a wall
splits the customer floor from the kitchen, with a door." The DSL's job is to let
them write the second thing.

This idea came from asking whether Gherkin/BDD prose could be an input. The answer
there was **no** — Gherkin is Given/When/Then, built to describe *behavior over
time* (an action and its outcome), and a building is a *static spatial
declaration*, not a behavior. Forcing a building into Given/When/Then produces
hollow ceremony. But the *instinct* — author in readable prose that compiles to
JSON — is right. The correct shape is a **spatial-declarative** mini-language that
talks about rooms, walls, and doors, not a behavioral one.

(Footnote: Gherkin *would* fit one day as a format for the validation rules —
"Given the level, When an agent paths from the entrance, Then it reaches the
vault" is a real behavior. That's a test-layer idea, not an authoring one.)

## What it looks like

Indentation-based (consistent with the YAML/Python feel of the existing tools).
A worked example, roughly a corner_deli:

```
building corner_deli
  size 38 x 28
  mode heist
  stories ground, upper
  basement

  ground
    room customer_floor   zone SW   role entry
    room deli_counter     zone S    role objective
    room kitchen          zone SE
    room stockroom        zone NE
    room stairwell        zone NW
    wall customer_floor | kitchen        door
    wall customer_floor | deli_counter   door, breach
    exterior S   door, window
    exterior W   door

  upper
    room office       zone N   role objective
    room apartment    zone S

  basement
    room vault        role objective   loot 3
    room cold_storage
    room corridor     role entry

  stair  switchback  stairwell -> upper
  ladder kitchen -> office

  spawn crew    at corridor
  extraction    at corridor
```

That reads like a description of a building. No coordinates, no axes, no bounds
arrays. Every line maps deterministically to the JSON the builder already
consumes.

## How it maps to the schema

The compiler (`dsl_compile.py`, bpy-free, offline) turns each construct into
existing spec fields. Nothing new in the schema — the DSL is a *front end* to the
spec that already exists.

| DSL construct | Compiles to |
|---|---|
| `building NAME` / `size W x D` | `name`, `footprint_x`, `footprint_y` |
| `mode M` | `mode` (assault/heist/survival) |
| `stories a, b` / `basement` | `n_stories`, `has_basement` |
| `room ID zone Z role R` | a `rooms[]` entry — `bounds` **computed from zone** |
| `wall A \| B door` | a `partitions[]` entry on the shared edge of A and B, with a door opening |
| `exterior S door, window` | `ext_walls[]` openings on side S |
| `stair STYLE A -> B` | a `stairs[]` entry (endpoints derived from the rooms/stories) |
| `ladder A -> B` | a `ladders[]` entry |
| `spawn/extraction/objective at ROOM` | a `markers[]` entry centered in the room |
| `role objective` + `loot N` | room role + `objectives[]` / `loot[]` entries |

## The hard part (and why this sketch exists)

**The make-or-break is layout solving: turning "zone SW" into real `bounds`.** The
DSL's entire value is removing coordinates — which means the compiler must
*generate* them. That is not free, and it's the thing to prototype before
committing.

The realistic v1 is **coarse grid placement**: divide the footprint into a 3×3
(or NxN) zone grid — NW N NE / W C E / SW S SE — and a room's `bounds` come from
its zone cell (rooms can span multiple cells, or auto-fill leftover space). Walls
between two rooms are placed on their shared edge once both have bounds. This is
deterministic and simple, but **coarser than hand-authored JSON** — you get a
plausible blockout, not pixel-exact rooms.

That coarseness is the honest positioning, and it's *fine*: the DSL trades
precision for speed and readability, exactly like presets trade specificity for
convenience. JSON stays the precision tool. The intended workflow:

1. Sketch the building in prose → compile to JSON (fast, readable, approximate).
2. Build and walk it.
3. If a room needs exact dimensions, edit that room's `bounds` in the JSON.

So the DSL gets you to a *valid, walkable* spec in a minute; JSON remains where
you refine. It does not replace JSON — it's the fastest way to a first draft.

Harder layout features deliberately **out of v1**: relative constraints ("kitchen
north of the deli, sharing a wall"), which need a real constraint solver;
non-rectangular rooms; precise sizing. Those are where it stops being "quick
sketch" and starts being a CAD tool — out of scope.

## Properties it must keep (thesis alignment)

- **Deterministic** — same DSL text → byte-identical JSON. Grid placement is a
  pure function of the input, so this holds.
- **Offline, no deps** — a hand-written tokenizer + parser in plain Python. No
  ANTLR, no parser-generator dependency.
- **Optional / deletable** — a fifth on-ramp. Delete `dsl_compile.py` and nothing
  else changes. Compiles *to* the spec JSON, so it depends on the schema, not the
  other way around.
- **One-way** — DSL → JSON only. No promise of JSON → DSL round-trip (the JSON
  carries exact coordinates the DSL deliberately abstracts away; round-tripping
  would lose that or require re-inferring zones, which is fragile). Like presets:
  generate once, then own the JSON.

## Verification (if built)

Fully offline-verifiable, which makes it attractive: the compiler is pure Python,
so every example DSL → JSON → `validate.py` round-trip can be tested in CI. A
golden-file test (sample `.deli` files with expected JSON output) would pin
determinism. No Blender or Godot needed to prove it works — unlike the builder
changes, this whole feature is in the verifiable tier.

## Recommendation

Worth a **prototype spike**, not a commitment. The deciding question is whether
coarse grid placement produces layouts good enough to be useful — if a 3×3 grid
feels too blocky, the DSL needs a constraint solver and the cost jumps. Build the
smallest possible `dsl_compile.py` that handles `building/size/room/zone/wall/
exterior/stair/spawn`, compile the example above, and walk the result. If the
blockout feels usable, expand. If it feels too coarse, the idea needs the harder
layout engine before it's worth shipping — decide then.

This sits behind the still-open higher-priority work (finishing the corner_deli
walk; I-3 verticality). It's a genuinely good idea, offline-verifiable, and
thesis-clean — but it's a new authoring surface, which is enrichment, not a gap
that's blocking anything.
