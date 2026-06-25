# Customizing — taking a level the last 20%

Deli Counter usually gets you most of the way to the level you want. This is how
you close the gap to 100% **without breaking the property that makes the tool
worth using** — that a level is a deterministic, reproducible build from its
spec.

## The one idea to internalize

**The `.glb` is disposable. The spec is what you iterate.**

Every build throws away the old `.glb` and regenerates a fresh one from the
spec. You are never editing the model — you are editing the *description*, and
the model is just the current render of that description. So the loop is:

```
build → look at the level → "the kitchen's too cramped" → edit the spec → rebuild → look again
```

Each rebuild is a brand-new `.glb`, but it *converges*, because the spec gets
closer to what you want each pass. The model is regenerated; your design intent
accumulates in the spec.

This is why determinism and iteration aren't in tension — determinism is what
*enables* fast iteration. Because the build is deterministic, you can throw away
the `.glb` fearlessly every time, knowing the spec fully reproduces it. If builds
drifted (random seeds, creeping hand-edits), you'd be scared to rebuild in case
you lost something. Determinism is what makes the `.glb` safe to treat as
disposable — which is what makes the loop fast.

**The `.glb` is read-only. You never edit it by hand.** Anything you want to
change goes back into the spec (if it can be expressed there) or layers on top
(if it can't).

## The fast loop

This is the intended workflow, and it's what `--watch` + the dock button exist
for:

1. `python build.py specs/<name>.json --watch` in a terminal.
2. Edit the spec, save. The `.glb` regenerates; Godot auto-reimports it.
3. Hit **↻ Rebuild last level** in the Deli Counter dock — reimports and replays,
   no file picker.

Spec edit → running playtest in one click. The faster this loop, the more
iterations you do, the closer the spec converges.

## The decision tree

When you want to change something Deli Counter made:

```
Can the spec express it? (resize a room, move a doorway, add a wall/room/
                          marker, change a material, swap mode...)
│
├─ YES → edit the JSON, rebuild. Don't touch the .glb. Determinism kept.
│        This is the 80% -> 100% path for almost everything.
│
└─ NO  → it's a sculpted / organic / genuinely one-off detail the parametric
         box generator will never produce. Then:
         │
         ├─ Recurring (you want it in every deli level)?
         │     → make it a KITBASH part the spec places at a marker. The builder
         │       drops it deterministically every rebuild. Determinism kept.
         │
         └─ Truly one-off?
               ├─ BEST: layer it on top. Instance the generated level as a
               │        locked base scene in Godot; your hand-made additions are
               │        siblings in the parent scene. The shell stays byte-
               │        identical and re-buildable; your overlay sits on top.
               │        Determinism of the generated layer is fully preserved.
               │
               └─ OK: edit a COPY saved as a distinct hand-owned asset
                      (e.g. corner_deli_handfinished.glb). Treat it as a new,
                      non-deterministic, human-owned artifact OUTSIDE the
                      pipeline. You knowingly drop determinism for that one file.
                      Never overwrite the generated .glb with it, and don't
                      pretend the spec still describes it.

NEVER: edit the generated .glb in place, then rebuild over it. The rebuild
       erases your edit, and until it does, the spec lies about what the level
       is.
```

## Why "edit the spec" beats "edit the model" for the expressible 80%

It's the same reason you edit source code, not the compiled binary:

- **It survives rebuilds.** A wall you nudge in Blender vanishes the next build.
  A wall you move in the spec is permanent and reproducible.
- **The spec stays honest.** If you hand-edit the `.glb`, the spec no longer
  describes the level — anyone who rebuilds gets something different from what
  you shipped. Keeping changes in the spec keeps "the spec IS the level" true.
- **It composes with everything else.** Validation, floorplans, navigability,
  poly budget, the tactical scorecard — all read the spec. Edit the spec and
  they stay accurate. Edit the `.glb` and they're describing a level that no
  longer exists.

## Determinism is a property of the generated layer, not your whole project

You don't have to make your entire level deterministic. You have to keep the
*generated shell* deterministic and clearly *separated* from hand-made parts.
The moment you blur them — hand-editing generated geometry in place — you lose
the property, because "rebuild from spec" stops reproducing what you have. Keep
the layers separate and you get both: a reproducible spatial shell, plus all the
hand-crafted detail you want on top.

## Going further than geometry

Two sanctioned routes for taking the shell beyond a raw blockout, both of which
keep the generated layer intact:

- **`--vertex-nuance`** — an opt-in pass that adds readability (densify, bevel,
  procedural vertex color) to the generated geometry. Still deterministic, still
  from the spec. See `godot/VERTEX_NUANCE.md`.
- **Patina** (sibling tool) — the downstream PS1-style auto-pipeline (auto-UV,
  procedural textures, shader). It styles the shell; it doesn't change the
  layout. It reads `gameplay.json` (including `surface_roles`) as its contract —
  see `docs/GAMEPLAY_JSON_CONTRACT.md`.

Both treat the generated `.glb` as input and produce styled output, never editing
the source geometry by hand.
