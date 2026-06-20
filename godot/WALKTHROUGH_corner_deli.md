# Verification walk-through — corner_deli via the editor plugin

Goal: prove the whole pipeline end-to-end on a hard level, in the real engine.
One pass validates four things at once: the **stair fix** (basement→roof
switchback — the hardest vertical we've built), the **editor plugin** (never
run in-engine before), **marker conversion**, and **collision**.

If the plugin breaks at any step, jump to **Plan B (manual path)** at the
bottom — it's the known-good route and still tests the stairs + collision.
A plugin bug should not block the gameplay test.

Work top to bottom. Each box is pass/fail; note anything weird in the margin.

---

## 0. Build the level (Blender)

The stair fix lives in the builder, so the GLB **must be rebuilt** — an old
GLB has the old broken stairs.

- [ ] Unzip **0.18.0** over `C:\deli_counter` (replace all).
- [ ] **Restart Blender** (module-cache trap — skipping this runs old code).
- [ ] Generate the spec if you haven't:
      `python new_level.py --preset corner_deli --name cd_test`
- [ ] In `_run_in_blender.py`, set the CONFIG block:
      - `SPEC_PATH = r"C:\deli_counter\specs\cd_test.json"`
      - `PKG_DIR   = r"C:\deli_counter"`
      - `OUT_PATH  = r"C:\deli_counter\build\cd_test.glb"`
- [ ] Run Script. **Expect:** console prints `built 'cd_test' ... 116 visual,
      90 collision, ...`, and a `cd_test.glb` + `cd_test.gameplay.json` appear
      in `build\`.
- [ ] Glance at the viewport: you should see a **3-level** building — basement
      below ground, two floors above, a roof with a parapet. ✦ *Checkpoint 1.*

---

## 1. Get the files into the project

- [ ] Copy **both** `cd_test.glb` and `cd_test.gameplay.json` into your Godot
      project (e.g. `res://levels/`), keeping them side by side.
- [ ] Let Godot import the `.glb` once (happens on focus — you'll see it in
      the import dock). If you get a **UID error**, do
      **Project → Reload Current Project** (known fresh-project hiccup).

---

## 2. Plugin install (one-time, if not already)

- [ ] Copy `godot/addon/deli_counter/` into `res://addons/deli_counter/`.
- [ ] **Project → Project Settings → Plugins** → enable **Deli Counter**.
- [ ] **Expect:** a **Deli Counter** dock appears (left side). ✦ *First real
      in-engine test of the plugin — if no dock appears, the plugin's
      `_enter_tree`/dock code is the suspect. Note it and go to Plan B.*

---

## 3. One-click: Set up & Play

- [ ] In the dock, click **Pick level .glb…**, choose `cd_test.glb`.
      **Expect:** the path shows, and status says it found the gameplay.json
      companion (not the "not found" warning).
- [ ] Click **Set up & Play ▶**. Watch the status line + the Output panel.
      **Expect, in order:**
      - "Assigned import script and reimported cd_test.glb"
      - "Built test scene: res://deli_counter_tests/test_cd_test.tscn"
      - "Playing test_cd_test.tscn" and the game window opens.
- [ ] ✦ *Checkpoint 2 — the plugin worked end-to-end.* If it errored partway,
      note which message was **last** printed (that pinpoints the failing
      step), then go to Plan B.

---

## 4. Walk it — the actual gameplay test

Controls: **WASD** move, mouse look, **Shift** sprint, **Space** jump,
**Esc** frees the mouse, **R** respawn, **F1** HUD, **F4** bake navmesh.

### The headline test — stairs
- [ ] You spawn at the first spawn marker. Find the **switchback stairwell**
      (NW corner of the building).
- [ ] Walk **up** from the ground floor to the **second floor**. ✦
      **THE fix:** you should crest the top and step off cleanly onto floor 2,
      **not** jam near the top step. This is the exact bug from before.
- [ ] Keep going **up** to the **roof** (the stair spans to story 2).
- [ ] Walk **down** the full span — ground floor, then down to the
      **basement**. The basement→ground leg is new territory (first basement
      stair we've walked); watch the bottom transition specifically.
- [ ] ✦ *If you can travel basement↔roof cleanly in both directions, the stair
      fix is confirmed on the hardest case.*

### Collision + scale
- [ ] You don't fall through any floor or slab.
- [ ] You can't walk through exterior walls; door/window openings are actually
      open (you can pass through doorways).
- [ ] Doorways clear your head; rooms feel ~human-scale (the player is 1.8 m).
- [ ] The counters / shelves / vault block read as solid cover (you bump into
      them, can't walk through).

### Markers converted
- [ ] Turn on collision view if you want: **Debug menu → Visible Collision
      Shapes** (editor toggle is more reliable than runtime).
- [ ] In the **Scene tree** (or via groups), confirm the marker empties became
      nodes: spawns, the 3 objectives (register on ground, safe in basement,
      server upstairs), loot, cover, patrol points. ✦ *Checkpoint 3.*

### The three objectives (reachability in practice)
- [ ] Physically walk to all three objective spots: **register** (ground,
      deli counter), **safe** (basement vault), **server** (upstairs). If you
      can reach all three on foot, the route graph matched reality.

---

## 5. Verdict

- [ ] **Stairs:** climb cleanly basement↔roof? (the whole point)
- [ ] **Plugin:** dock appeared + Set up & Play ran end-to-end?
- [ ] **Collision/scale:** solid floors/walls, human-scale, openings open?
- [ ] **Markers:** converted to nodes in the right places?

If all four pass: the pipeline is **proven on a rich level** and churning the
remaining presetable buildings (warehouse, suburban_safehouse, rowhome) is now
low-risk. If any fail, note exactly what and we fix it before scaling.

---

## Plan B — manual path (if the plugin misbehaves)

Known-good route; still fully tests stairs + collision + markers.

1. Select `cd_test.glb` in the FileSystem dock → **Import** tab.
2. Set **Import Script** to
   `res://addons/deli_counter/deli_counter_postimport.gd`
   (or `res://godot/deli_counter_postimport.gd` if you didn't install the
   addon) → **Reimport**.
3. Open `res://addons/deli_counter/template/level_test.tscn` (the harness).
4. Drag `cd_test.glb` into the scene as a child of the root.
5. Press **F6** (Play Scene) — or F5 if it's the main scene.
6. Resume at **section 4** above and walk it.

If Plan B works but the plugin didn't, the level/pipeline is fine and the bug
is isolated to the plugin — tell me the last status message it printed and
I'll fix the plugin specifically.
