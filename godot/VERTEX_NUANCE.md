# Vertex nuance (optional anti-flatness pass)

**Optional and off by default.** The pure greybox is the default output. Build a
spec with `--vertex-nuance` (or `"vertex_nuance": true` in the JSON) and Deli
Counter applies a visual-only pass that makes the blockout read less like a flat
CG box — for readability, not beauty. Collision, markers, and the gameplay.json
are untouched.

## What it does (VISUAL meshes only)

1. **Densify** — subdivides large faces to ~grid edge length so vertex color has
   resolution (and so PS1-style affine texture mapping doesn't over-warp).
2. **Bevel** — ~1.5 cm bevel on hard edges so light catches them and the
   "perfect CG box" read breaks.
3. **Procedural vertex color**, all derived from geometry (deterministic):
   - fake ambient occlusion darkening crevices/high-valence vertices,
   - a height/grime gradient darkening near the floor,
   - a per-surface base tint so floor / wall / ceiling read distinctly.

No hand-painting, no textures, no UVs. The color is baked into the mesh and
ships in the `.glb`.

## Displaying it in Godot

Vertex colors are invisible unless a material reads them. On the imported
level's `StandardMaterial3D` (or your own material), enable:

- **Vertex Color → Use as Albedo** = on.

That's it for the base look. If you're going for the PS1 style, this pairs
naturally with a vertex-lit PS1 shader (white ambient light + vertex colors
faking the lighting is the authentic approach — see the wider PS1 pipeline
notes).

## When to use it

- You want the blockout to communicate the space better in screenshots or
  review, without doing an art pass.
- You're feeding the shell into a PS1-style shader that wants vertex colors.

## When NOT to use it

- You want the pure, honest greybox (the default) — leave it off.
- You're tight on the poly budget: densify + bevel raise vertex count. The pass
  is budget-aware but adds geometry; check `polybudget` after enabling.
