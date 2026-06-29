# Deli Counter — Godot editor plugin

Removes the manual per-level file shuffle. Instead of copying scripts, setting
the import script in the Import tab, reimporting, and dragging the level into a
scene by hand, you pick a `.glb` and click one button.

## Install (once per project)

**From a Release (no clone):** download `deli_counter-godot-addon-<version>.zip`
from the repo's Releases page and unzip it at your Godot **project root** — it
lands at `res://addons/deli_counter/`. Then enable the plugin (step 2 below).

**From the repo:**
1. Copy this entire `deli_counter/` folder into your project at
   `res://addons/deli_counter/`. It's self-contained — it already includes the
   post-import script, `deli_level.gd`, and the test harness under `template/`.
2. In the editor: **Project → Project Settings → Plugins**, find **Deli
   Counter**, set it to **Enabled**.
3. A **Deli Counter** dock appears (left side, upper-right slot). Drag it
   wherever you like.

You still copy each level's `.glb` + its `.gameplay.json` into the project
(they have to live somewhere under `res://`), but everything after that is
handled by the dock.

## Use (per level)

1. Copy the level's `<name>.glb` and `<name>.gameplay.json` into your project
   (e.g. `res://levels/`), keeping them together.
2. In the dock, click **Pick level .glb…** and choose it.
3. Click **Set up & Play ▶**. That:
   - assigns the post-import marker-conversion script to the `.glb` and
     reimports it (no Import-tab dance),
   - builds a test scene under `res://deli_counter_tests/` with the walkable
     harness and your level instanced in it,
   - opens and runs it.

Or use the numbered buttons to do the steps separately:
- **1. Assign import script + reimport** — sets up collision + marker
  conversion on the `.glb`.
- **2. Build test scene** — makes the harness scene without running it.

## Notes

- The first time you add a `.glb`, let Godot import it once (it happens
  automatically on focus) before clicking **Assign import script** — the
  button edits the existing `.import` file.
- Test scenes are written to `res://deli_counter_tests/` so they never touch
  your own scenes. Delete that folder anytime.
- Controls in the running scene: WASD/arrows move, mouse looks, Shift sprint,
  Space jump, Esc frees the mouse, R respawns, F1 HUD, F4 bakes a navmesh.
  See `template/README.md` for the full list and the WASD input-map setup.
- This plugin supersedes the manual "copy the template folder" workflow — the
  template now lives inside the addon and the dock instances it for you.
