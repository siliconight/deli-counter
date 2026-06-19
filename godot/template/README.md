# Level test harness (Godot)

A drop-in scene for walking a generated Deli Counter level at player scale and
checking collision, routes, and fit. It is a **greybox testing rig**, not a
shipping player or UI — keep your real game player elsewhere.

## Setup (once)

Copy this `template/` folder into your project under
`res://addons/deli_counter/template/`, alongside the import scripts. So you'll
have:

```
res://addons/deli_counter/
    deli_counter_postimport.gd
    deli_level.gd
    template/
        level_test.tscn
        level_test.gd
        player.gd
```

## Use it per level

1. Import a level `.glb` (see `../IMPORT_GUIDE.md`) so its collision and markers
   are set up.
2. Open `level_test.tscn`.
3. Either: drag your imported `.glb` into the scene as a child of `Main`
   (the harness auto-finds the first level-like child), **or** select `Main`
   and set its **Level Scene** export to your imported `.glb`.
4. Press **F6** (run current scene). You spawn at the first attacker/crew spawn.

## Controls

| Key | Action |
|---|---|
| WASD / arrows | move |
| mouse | look |
| Shift | sprint |
| Space | jump |
| Esc | free / recapture mouse |
| F1 | toggle the HUD |
| F3 | toggle SCALE_REF proxies (if the level baked them) |
| F4 | bake a NavigationMesh over the level and show it |
| R | respawn at the first spawn marker |

**Collision view:** Godot's runtime collision toggle is unreliable, so use the
editor's **Debug → Visible Collision Shapes** menu (toggle it before/while
running), or set the harness's **Show Collision Shapes** export on. Either shows
the StaticBody3D shapes the importer generated.

## What to check (the scale/playability pass)

- You clear doorways with headroom (you're 1.8 m; doors are 2.2 m).
- Walls read at human height — you don't feel ant-sized or giant.
- Collision stops you at every wall and holds you on every floor (you don't
  fall through a slab or walk through a wall).
- You can actually reach the objective room, and aisles/halls aren't cramped.
- F4's navmesh covers the walkable floor without big holes — a quick read on
  whether AI could path the space.

The player capsule is 1.8 m tall / 0.4 m radius and the camera sits at 1.6 m,
matching `docs/scale_guidelines.md`, so "does it feel right to walk" is a real
scale test, not an approximation.
