# Roofs in Deli Counter — integration sketch

Drop into `deli_counter/docs/ROOF_PLAN.md`.

## Starting point (what already exists)

DC is **not** open-top today. `Builder._slabs()` already lays a slab per story
and tags the topmost one as the roof:

```python
role = "ceiling" if s == top else "floor"
self._box(f"slab_{s}", (0, 0, z - ft/2), (fx, fy, ft), self.VISUAL, role=role)
self._col_box(f"slab_col_{s}", (0, 0, z - ft/2), (fx, fy, ft), mode="trimesh")
```

So every building is capped with a visual + trimesh-collision roof, feeding the
`surface_roles` map as `ceiling`. `parapets` (roof-edge walls) and `slab_holes`
(atrium/shaft cutter, via `_slab_holes_cut`) already exist too.

The wawa greybox looked open-top only because the standalone `emit_demo.py`
reimplemented the shell and omitted the ceiling. Real DC has the roof — it's
just **always solid, always baked, never a swap-slot, and not authorable-away.**

So the work is four upgrades to the existing ceiling, then Zoo + Lot.

The invariant that makes all of this safe to apply *after* the greybox passes
the fun test: **roof derivation reads only frozen structure** (footprint,
`story_height`, room bounds). It never re-solves layout, so every wall / opening
/ fixture / room / anchor id stays byte-identical. Flipping the roof on or off,
or switching to per-room, only adds a top surface keyed to what's already there.

---

## 1. Spec (`spec_types.py`) — additive, old specs unchanged

```python
@dataclass
class LevelSpec:
    ...
    # ROOF. "solid" = today (baked visual + collision). "open" = suppress the
    # roof VISUAL for top-down authoring but KEEP collision (grenades/projectiles
    # still bounce — the "fun test" mode). "none" = no top cap at all.
    roof: str = "solid"                 # solid | open | none
    roof_mode: str = "footprint"        # footprint | per_room
    roof_thick: Optional[float] = None  # None -> floor_thick

@dataclass
class Room:
    ...
    roofed: bool = True                 # per-room opt-out for open-air rooms

@dataclass
class SlabHole:
    ...
    breakable: bool = False             # top-story hole + breakable = skylight
    interactive: Optional[dict] = None  # same override slot as Opening.interactive
```

Defaults reproduce today's output exactly → `SCHEMA_VERSION` minor bump only
(`1.10.0 → 1.11.0`), `KIT_VERSION` unchanged (geometry identical for `solid`).

---

## 2. Emitter (`deli_counter.py`) — three surgical edits to `_slabs`

**(a) Split the top ceiling's visual from its collision** so `roof="open"` drops
the mesh but keeps the walkable/bounce surface:

```python
def _slabs(self):
    base, top = self._story_range()
    ft = self.s.roof_thick or self.s.floor_thick
    for s in range(base, top + 1):
        z = s * self.s.story_height
        is_roof = (s == top)
        if is_roof and self.s.roof == "none":
            continue
        role = "ceiling" if is_roof else "floor"
        # visual: skip only the roof mesh when authoring open-top
        if not (is_roof and self.s.roof == "open"):
            self._box(f"slab_{s}", (0, 0, z - ft/2),
                      (self.s.footprint_x, self.s.footprint_y, ft),
                      self.VISUAL, role=role)
        # collision: ALWAYS on for the roof (unless roof == "none")
        self._col_box(f"slab_col_{s}", (0, 0, z - ft/2),
                      (self.s.footprint_x, self.s.footprint_y, ft), mode="trimesh")
        if is_roof and self._modular_on():
            self._record_roof_slots(top, z, ft)
```

**(b) Always emit a roof SLOT** (mirror of `_record_wall_slot`) so Zoo can dress
it — present even in `open` mode, because the slot is the always-there hook:

```python
def _record_roof_slots(self, top, z, ft):
    fx, fy = self.s.footprint_x, self.s.footprint_y
    def slot(sid, cx, cy, sx, sy, room=None):
        self.slots.append({
            "slot_id": sid, "role": "roof", "size_mod": "full", "style": 1,
            "current_ref": "roof_greybox_01", "kit_axis": "theme",
            "story": top, "facing": "up", "room": room,
            "transform": {"translation": [round(cx,4), round(cy,4), round(z-ft/2,4)],
                          "rot_y": 0, "scale": [1.0, 1.0, 1.0]},
            "fit": {"dims": [round(sx,4), round(sy,4), round(ft,4)],
                    "pivot": "center", "openings": self._skylight_voids(top),
                    "collision": "trimesh"},
        })
    if self.s.roof_mode == "per_room":
        for r in self.s.rooms:
            if r.story == top and r.roofed:
                b = r.bounds
                slot(f"roof_{r.id}", (b[0]+b[2])/2, (b[1]+b[3])/2,
                     b[2]-b[0], b[3]-b[1], room=r.id)
    else:
        slot("roof_footprint", 0.0, 0.0, fx, fy)
```

`_skylight_voids(top)` returns the top-story `slab_holes` as `fit.openings`
(same shape walls use for doorway voids) so a themed roof module knows where the
holes are.

**(c) Skylights = breakable horizontal windows.** `_slab_holes_cut` already cuts
the void. For a top-story hole with `breakable=True`, register an interactive via
the *existing* `interactives.py` — a skylight is just a `window[intact,broken]`
whose `state_geometry` is `{intact: pane, broken: void}`, exactly the breach
reframe rotated horizontal:

```python
# in _slab_holes_cut, after the cut, when hole.story == top and hole.breakable:
machine = derive_interactive(self.s.name, wall="roof", story=hole.story,
                             kind="window", pos=(hole.x, hole.y),
                             breakable=True, override=hole.interactive)
# emit the intact pane as the removable state box + append to gameplay interactives,
# same code path as _record_openings uses for wall windows.
```

The id keys on `(building, "roof", top, "skylight", pos)` → stable across
re-greybox, and it drops straight into the `interactives` array and slot
`interactive` block you already ship. Free rooftop breach-entry.

---

## 3. Godot addon (consumer loader)

The DC Godot side that instances the GLB + reads slots.json spawns the roof as a
**hide-mesh / keep-collision** node — the pattern the wawa demo already proves:

```gdscript
func set_roof_visible(v): show_roof = v; for mi in _roof_meshes: mi.visible = v
func toggle_roof(): set_roof_visible(not show_roof)
```

For a `roof="open"` build the roof mesh isn't in the GLB at all, so the toggle
just governs the Zoo-instanced module. `show_roof` lives on the level root; an
authoring build flips it for top-down inspection, playtest leaves it on.

---

## 4. Zoo — dress the roof slot

One new architectural species on the **existing** `arch.py` slab machinery:

- **`roof`** = a solid horizontal Panel (a "wall" laid flat) → `slab_parts` with
  no void.
- **`skylight`** = slab-with-void → `void_for` + `slab_parts`, exactly the
  window/doorway decomposition, horizontal.

Resolver: `roof_<theme>_<style>[_w<cm>][_<state>].glb`, greybox-box fallback when
the art isn't authored yet (progressive art pass, same as walls). Rooftop props
(AC units, vents, pipe runs) anchor via the `ceiling` / `lid` connector sockets
already in the vocabulary. The skylight's `intact`/`broken` variants come from
the `interactive` block Zoo already expands for wall windows — no new path.

---

## 5. Lot — merge rooflines at site scale

A `_rooflines` / `merge_roofs` pass parallel to `merge_lights`:

1. Offset each building's roof slot(s) to world (`_place_point`), namespace
   `{bid}/roof_...`, world-AABB the bounds — identical to how lights merge.
2. **Dedupe shared rooflines:** where buildings abut, coincident roof edges join
   into one continuous roof (strip-mall / row-block). Same seam logic Lot uses
   for adjoining walls.
3. Emit site-level roof anchors DC can't see — a block-wide canopy, parapet runs,
   silhouette/occlusion volumes for the skybox — the same shape as the existing
   `_streetlight_anchors()` exterior pass.

---

## Versions / docs / tests

- `slot_manifest_version` `1.1.0 → 1.2.0` (new `role:"roof"`, `facing:"up"`).
- `SCHEMA_VERSION` `1.10.0 → 1.11.0` (additive: `roof`, `roof_mode`, `roof_thick`,
  `Room.roofed`, `SlabHole.breakable/interactive`).
- `KIT_VERSION` unchanged for `roof="solid"` (byte-identical geometry); the roof
  slot is a slots.json manifest addition, not a geometry change.
- Docs: `docs/ROOF_MANIFEST.md` (or a "Roof/ceiling slot" section in
  `SLOT_MANIFEST.md`) + an "Open-top authoring & sealing" note in `AUTHORING.md`.
- `test_roofs.py` (pure, no bpy, like `test_lights.py`): footprint vs per_room
  slot derivation, `Room.roofed` opt-out, skylight→interactive id stability,
  `roof="open"` keeps the collision slab + roof slot but drops the visual.

## Highest-leverage first commit

Edits (a)+(b) alone — split visual/collision on the top slab and always emit the
roof slot. That gives you open-top authoring with collision retained and the Zoo
hook, without touching skylights, Zoo, or Lot yet. Everything else layers on
without reopening it.
