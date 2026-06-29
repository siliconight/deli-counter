# Deli Counter — where it is, and how we make levels

A high-level overview for the team. Deli Counter (DC) is our tool for turning a
written building spec into a Godot-ready level shell.

## The one idea

**Greybox is the function. Art is a cosmetic skin on top.**

The greybox building — its collision, its navigation, its way in and out — is the
thing that makes a level *work*, and we validate it before anyone spends time on
art. The art pass only changes how it looks. Because of that, **an art pass can
never break a level**: the function was locked at greybox, and theming swaps
appearance, not behaviour.

## What DC does

You write one JSON spec for a building. DC builds it and gives you:

- **A greybox building** — walls, floors, stairs, collision, and the marker
  points where gameplay attaches. It's checked for the things that matter:
  reachable, has valid ways in and out, objective rooms have enough access. This
  is the source of truth.
- **Gameplay data** — objectives, loot, spawns, doors as labelled points the game
  code wires up.
- **A swap manifest** — a list of every swappable piece in the building (what it
  is, where it sits, what a replacement must match). This doubles as the artist's
  work order.

The building is made of **modular pieces** (a wall is a row of wall/door/window
segments, not one slab), and identical pieces share one mesh — so eight identical
walls cost one mesh in memory, and editing that one piece updates all eight.

## How a level gets made

1. **Build the greybox.** One spec in, a validated grey building out. It works —
   players and AI can move through it. This is shippable-for-testing as-is, grey.
2. **Wire the gameplay.** Game code reads the marker data and attaches objectives,
   loot, spawns, doors.
3. **Walk it.** Playtest in engine to confirm it feels right — the only check that
   catches physical snags.
4. **Art pass (cosmetic, optional, progressive).** Artists author themed pieces
   (e.g. `wall_gasstation_01`) into a shared library. The level points at them and
   they appear — greybox stays the fallback for anything not themed yet. Theme one
   piece type at a time; the level never stops working.

## Two ways the building comes out

- **Scene (`.tscn`) — the primary path.** The building is a Godot scene that
  *references* the module files. The greybox scene IS the functional level;
  theming is just adding/editing art files in the shared library, and every
  instance updates live — no rebuild. Edit one wall module, every wall in every
  building that uses it updates.
- **Baked single file (`.glb`) — the special case.** When you want one
  self-contained asset (e.g. shipping a level as a single file), DC can bake the
  whole building, themed, into one GLB.

Same building either way — they read the same data, so they never disagree.

## Bonus: in-game documentation

Borrowing the "gym / zoo / museum" workflow: DC can generate a **zoo** — every
module laid out on a grid with scale references and name labels — so artists see
exactly what they're skinning, at real scale, instead of guessing from
thumbnails. (Gym and museum versions — walkable scale guides and live system
demos — are natural follow-ons.)

## Honest status

- The full chain (modular pieces → shared meshes → swap manifest → theming →
  scene/baked output → zoo) is **built and logic-tested**, and the latest is
  **pushed**.
- It is **not yet walked end-to-end in Godot**. The architecture is sound on
  paper; this project's consistent lesson is that only an in-engine walk catches
  physical problems. So the immediate next step is to **walk one building through
  the whole chain** before we lean on it for production — and before we add more.

## The split, in one line

DC ships the **greybox function** (deterministic, validated, replication-free).
The game decides the **cosmetics**. Art is a skin; it never owns whether the level
works.
