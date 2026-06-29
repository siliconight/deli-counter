# gasstation theme — authoring worklist (PRIMARY path: .tscn + theme_swap.gd)

The primary art-pass path: DC emits a greybox `.tscn` that instances greybox
modules from `res://art/zoo/`; `theme_swap.gd` (game-side, on the building root)
overlays themed art on any module that has a variant, **keeping greybox
collision**. So themed modules are **VISUAL-ONLY** and live in the **Godot
project** (`res://art/zoo/`), NOT the Deli Counter repo.

With the dims-aware overlay (0.41.0), `theme_swap.gd` resolves, per module:

    <type>_<theme>_<style>_w<cm>.glb   ->   <type>_<theme>_<style>.glb   ->   stays greybox

(`cm` = round(width x 100); width token is read from the greybox module's name.)

> NOTE: this only matters if your greybox modules themselves carry the width
> token (e.g. `doorway_greybox_01_w180.glb`). Modules are instanced at authored
> size and never scaled, so the greybox library must already have a piece that
> fits each slot width. Two ways to get there:
>   (A) Author per-width greybox + themed modules (the list below), or
>   (B) **Keep specs on a fixed opening-width palette** (e.g. doors 1.1/1.8,
>       windows 2.0/3.0) so one module per width serves every building. (B) is
>       the lower-maintenance route; (A) is the escape hatch for odd widths.

## Files to author for theme `gasstation` (visual-only, into res://art/zoo/)

Walls (the clean win — all 66 tiles are uniform 2.0 m):

    wall_gasstation_01.glb            2.0 x 0.3 x 4.2     visual-only

Windows:

    window_gasstation_01_w120.glb     1.2 wide   (x1)
    window_gasstation_01_w200.glb     2.0 wide   (x1)
    window_gasstation_01_w240.glb     2.4 wide   (x2)
    window_gasstation_01_w300.glb     3.0 wide   (x2)

Doorways:

    doorway_gasstation_01_w110.glb    1.1 wide   (x2)
    doorway_gasstation_01_w120.glb    1.2 wide   (x3)
    doorway_gasstation_01_w140.glb    1.4 wide   (x1)
    doorway_gasstation_01_w180.glb    1.8 wide   (x3, front entries)

Wall-end remainders (23 slots, 14 widths) — leave greybox.

## Authoring conventions (primary path)

- **Visual-only.** No `-convcolonly` / `-colonly` nodes — greybox owns collision.
  `theme_swap.gd` strips any collision it finds in the overlay anyway, but author
  clean visual meshes.
- Origin-centered; width -> X, thickness -> Y, height -> Z; share the greybox
  module's pose so the overlay lines up.
- Editing a themed `.glb` in `res://art/zoo/` updates every instance live — no DC
  rebuild.

## Starter generator

`make_gasstation_modules.py` emits visual-only stub GLBs with the width-token
names straight into your Godot project's `res://art/zoo/` (set OUT_DIR). Art-pass
them in place. (For the **baked** GLB special-case path, the same names resolve
via DC_THEME/DC_MODULE_LIB at build time — but those baked themed modules DO need
their collision, so that's a separate authoring choice.)
