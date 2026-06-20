"""
presets.py  --  parameterized recipe generators
================================================
Each preset is a function that takes a few knobs and returns a complete spec
dict (the same shape spec_loader.load_spec consumes). Presets emit the tactical
layer, materials, and spawns so a walk-up user gets a *playable* level from one
command, not just a building shell.

Presets are pure Python — no Blender, no bpy. They build a dict; the CLI
(new_level.py) validates it and writes specs/<name>.json. Hand-edit from there.

Adding a recipe: write a function returning a dict, register it in REGISTRY.
The bank recipe is the reference implementation; keep the others structurally
parallel so the set stays consistent.
"""

from typing import Optional


# common acoustic palette presets can draw from. Acoustic-only (gool enum +
# absorption/damping); visuals are textured in Godot.
_PALETTE = {
    "concrete":  {"id": "concrete",  "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
    "drywall":   {"id": "drywall",   "acoustic": "Drywall"},
    "glass":     {"id": "glass",     "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
    "metal":     {"id": "metal",     "acoustic": "Metal", "absorption": 0.5, "damping": 0.3},
    "wood":      {"id": "wood",      "acoustic": "Wood"},
}


def _mats(*names):
    """Pull a subset of the shared palette by name."""
    return [_PALETTE[n] for n in names]


# ---------------------------------------------------------------------------
# BANK  --  reference recipe
# ---------------------------------------------------------------------------
def bank(name: str = "bank_preset",
         mode: str = "assault",
         floors: int = 2,
         basement: bool = True,
         scale_ref: bool = False) -> dict:
    """A bank branch: glass-front public lobby with a teller line, a
    back-of-house manager office + security room, and a vault (the objective)
    in the basement reached by a stair. Sized to the 'medium tactical' band of
    the scale guidelines. floors counts above-ground stories (>=1)."""
    floors = max(1, int(floors))
    fx, fy = 30.0, 22.0          # footprint (m): a medium tactical building
    sh = 3.6

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name,
        "mode": mode,
        "seed": 1999,
        "footprint_x": fx,
        "footprint_y": fy,
        "story_height": sh,
        "n_stories": floors,
        "has_basement": bool(basement),
        "collision": "convex",
        "auto_exterior": True,
        "scale_ref": bool(scale_ref),
        "default_material": "concrete",
        "materials": _mats("concrete", "drywall", "glass", "metal", "wood"),
    }

    half_x, half_y = fx / 2, fy / 2

    # --- exterior: glass storefront on south, solid block elsewhere ----------
    ext = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.1, "width": 1.8, "tag": "main_entry"},
            {"kind": "window", "pos": 0.2, "width": 2.4, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.4, "width": 2.4, "sill": 0.9, "vaultable": True},
        ]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.0, "tag": "side_entry"},
        ]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.25, "width": 1.0, "tag": "staff_entry"},
        ]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "breach", "pos": 0.2, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"},
        ]},
    ]
    # upper floors: windows all round (vaultable for rappel/entry)
    for st in range(1, floors):
        for w in ("S", "N", "E", "W"):
            ext.append({"wall": w, "story": st, "material": "concrete", "openings": [
                {"kind": "window", "pos": -0.25, "width": 1.6, "sill": 0.9, "vaultable": True},
                {"kind": "window", "pos": 0.25, "width": 1.6, "sill": 0.9, "vaultable": True},
            ]})
    spec["ext_walls"] = ext

    # --- ground floor partitions: split public lobby / back-of-house ---------
    # an east-west wall at y=+2 separates the public lobby (south) from the
    # staff area (north); two doored gaps keep the objective reachable.
    parts = [
        {"story": 0, "axis": "X", "pos": 2.0, "start": -half_x, "end": half_x,
         "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.3}, {"kind": "door", "pos": 0.35},
         ]},
        # staff area subdivided: manager office (west) / security room (east)
        {"story": 0, "axis": "Y", "pos": 0.0, "start": 2.0, "end": half_y,
         "material": "drywall", "openings": [{"kind": "door", "pos": 0.0}]},
    ]
    spec["partitions"] = parts

    # --- vertical: a switchback stair spanning basement..top -----------------
    lo = -1 if basement else 0
    spec["stairs"] = [{
        "x": -half_x + 4, "y": half_y - 4,
        "from_story": lo, "to_story": floors - 1 if floors > 1 else (0 if not basement else 1),
        "style": "switchback", "cut_slabs": True,
    }]
    # ensure the stair actually spans something if single-story + basement
    if floors == 1 and basement:
        spec["stairs"][0]["to_story"] = 0

    # --- rooms (tactical) ----------------------------------------------------
    rooms = [
        {"id": "lobby", "story": 0, "bounds": [-half_x, -half_y, half_x, 2.0],
         "role": "public_entry", "combat_range": "long"},
        {"id": "manager_office", "story": 0, "bounds": [-half_x, 2.0, 0.0, half_y],
         "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
        {"id": "security_room", "story": 0, "bounds": [0.0, 2.0, half_x, half_y],
         "role": "connector", "combat_range": "close"},
    ]
    # vault objective: in the basement if present, else in the security room
    if basement:
        rooms.append({"id": "vault_room", "story": -1,
                      "bounds": [-half_x, -half_y, half_x, half_y],
                      "role": "objective_room", "objective": True,
                      "fortifiable": True, "combat_range": "close"})
        # basement partition giving the vault a second access (soft wall)
        parts.append({"story": -1, "axis": "Y", "pos": 0.0,
                      "start": -half_y, "end": half_y, "material": "concrete",
                      "openings": [{"kind": "door", "pos": -0.2},
                                   {"kind": "breach", "pos": 0.3,
                                    "breach_class": "reinforced", "material": "concrete"}]})
        vault_xyz = (half_x - 5, -half_y + 5, -1.8)
        obj_room = "vault_room"
    else:
        vault_xyz = (half_x - 5, half_y - 4, 0.5)
        obj_room = "security_room"
        rooms[2]["role"] = "objective_room"
        rooms[2]["objective"] = True
    spec["rooms"] = rooms

    # --- volumes: teller line (cover), vault box, roof unit ------------------
    vols = [
        {"name": "teller_counter", "x": 0.0, "y": -2.0, "z": 0.55,
         "size_x": 12.0, "size_y": 0.8, "size_z": 1.1, "collision": "convex",
         "material": "wood"},
    ]
    if basement:
        vols.append({"name": "VAULT", "x": vault_xyz[0], "y": vault_xyz[1], "z": -1.8,
                     "size_x": 5.0, "size_y": 5.0, "size_z": 3.0,
                     "collision": "convex", "material": "metal"})
    if floors >= 1:
        vols.append({"name": "roof_unit", "x": half_x - 5, "y": half_y - 5,
                     "z": (floors * sh) + 0.6, "size_x": 3.0, "size_y": 2.0,
                     "size_z": 1.2, "collision": "convex", "material": "metal"})
    spec["volumes"] = vols

    # --- vault ledge: teller line doubles as vaultable cover -----------------
    spec["vault_ledges"] = [
        {"x": 0.0, "y": 4.0, "story": 0, "length": 4.0, "axis": "X",
         "height": 1.1, "material": "wood"},
    ]

    # --- markers: spawns, objective, cover, camera ---------------------------
    spec["markers"] = [
        {"type": "attacker_spawn", "id": "A", "x": -2, "y": -half_y - 3, "z": 0,
         "rot_z": 90, "room": "lobby"},
        {"type": "attacker_spawn", "id": "B", "x": -half_x - 3, "y": 0, "z": 0,
         "rot_z": 0, "room": "lobby"},
        {"type": "defender_spawn", "x": vault_xyz[0], "y": vault_xyz[1],
         "z": vault_xyz[2] - 0.0, "rot_z": 270, "room": obj_room},
        {"type": "objective", "id": "A", "x": vault_xyz[0], "y": vault_xyz[1],
         "z": vault_xyz[2], "room": obj_room, "meta": {"kind": "secure"}},
        {"type": "cover_high", "x": 0, "y": -2, "z": 0, "room": "lobby"},
        {"type": "camera_socket", "id": "01", "x": half_x - 3, "y": -half_y + 2,
         "z": 3.0, "room": "lobby"},
    ]

    # roof parapet on the top story
    spec["parapets"] = [{"story": floors, "height": 1.1}]

    # --- heist mode: add the heist loop (objectives, loot, extraction) -------
    # assault mode uses the room.objective flag above; heist mode needs the
    # explicit heist grammar or it fails heist validation.
    if mode == "heist":
        spec["objectives"] = [
            {"id": "crack_vault", "kind": "drill",
             "x": vault_xyz[0], "y": vault_xyz[1], "z": vault_xyz[2],
             "room": obj_room, "required": True, "duration": 90},
            {"id": "grab_drawers", "kind": "grab",
             "x": 0.0, "y": -2.0, "z": 0.5, "room": "lobby",
             "required": False},
        ]
        spec["loot"] = [
            {"id": "vault_cash", "kind": "cash",
             "x": vault_xyz[0], "y": vault_xyz[1], "z": vault_xyz[2],
             "value": 500000, "bags": 4, "room": obj_room},
            {"id": "teller_cash", "kind": "cash",
             "x": -2.0, "y": -2.0, "z": 0.5, "value": 80000, "bags": 1,
             "room": "lobby"},
        ]
        # extraction at the south entry; a secure/drop point near the stair
        spec["zones"] = [
            {"id": "main", "kind": "extraction", "story": 0,
             "bounds": [-half_x, -half_y, -half_x + 8, -half_y + 6]},
            {"id": "stage", "kind": "secure", "story": 0,
             "bounds": [-half_x, half_y - 6, -half_x + 6, half_y]},
        ]
        # heist spawns: crew enters, no defender/attacker split
        spec["markers"] = [
            {"type": "crew_spawn", "id": "A", "x": -2, "y": -half_y - 3, "z": 0,
             "rot_z": 90, "room": "lobby", "meta": {"phase": "stealth"}},
            {"type": "responder_spawn", "id": "1", "x": half_x - 3,
             "y": half_y - 3, "z": 0, "meta": {"phase": "loud"}},
            {"type": "camera_socket", "id": "01", "x": half_x - 3,
             "y": -half_y + 2, "z": 3.0, "room": "lobby"},
        ]

    return spec


# ---------------------------------------------------------------------------
# POLICE STATION  --  dense tactical interior, 2 floors + roof access
# ---------------------------------------------------------------------------
def police_station(name: str = "police_station_preset",
                   mode: str = "assault",
                   floors: int = 2,
                   basement: bool = False,
                   scale_ref: bool = False) -> dict:
    """A precinct: public lobby + front desk and holding cells on the ground
    floor; detective offices, interrogation, and a REINFORCED armory (the
    objective) upstairs. Vertical: a stairwell (main route), a roof hatch +
    ladder (flanking entry), and a floor hole over the armory (top-down
    pressure). Breach-vs-reinforced walls: soft interior walls breach, the
    armory does not. Sized to the 'medium tactical' band. floors is forced to
    >=2 (the recipe is inherently two-story)."""
    floors = max(2, int(floors))
    fx, fy = 34.0, 26.0
    sh = 3.6
    half_x, half_y = fx / 2, fy / 2

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name,
        "mode": mode,
        "seed": 1977,
        "footprint_x": fx,
        "footprint_y": fy,
        "story_height": sh,
        "n_stories": floors,
        "has_basement": bool(basement),
        "collision": "convex",
        "auto_exterior": True,
        "scale_ref": bool(scale_ref),
        "default_material": "concrete",
        "materials": _mats("concrete", "drywall", "glass", "metal", "wood"),
    }

    # --- exterior: glass lobby front (S), garage bay (E), solid elsewhere ----
    ext = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.1, "width": 1.8, "tag": "main_entry"},
            {"kind": "window", "pos": 0.25, "width": 2.0, "sill": 0.9, "vaultable": True},
        ]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "garage", "pos": -0.1, "width": 3.2, "tag": "garage_bay"},
        ]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.0, "tag": "staff_entry"},
        ]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "breach", "pos": 0.2, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"},
        ]},
    ]
    # upper floor: windows for vertical angles / rappel entry
    for w in ("S", "N", "E", "W"):
        ext.append({"wall": w, "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.25, "width": 1.6, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.25, "width": 1.6, "sill": 0.9, "vaultable": True},
        ]})
    spec["ext_walls"] = ext

    # --- partitions: dense ground floor (lobby / desk / cells / booking) -----
    parts = [
        # ground: front-of-house vs back-of-house divider
        {"story": 0, "axis": "X", "pos": -2.0, "start": -half_x, "end": half_x,
         "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.3}, {"kind": "door", "pos": 0.3}]},
        # ground: holding cells block (west back), reinforced cell wall
        {"story": 0, "axis": "Y", "pos": -6.0, "start": -2.0, "end": half_y,
         "material": "concrete", "openings": [{"kind": "door", "pos": 0.0, "tag": "cell_door"}]},
        # ground: booking / garage divider (east)
        {"story": 0, "axis": "Y", "pos": 8.0, "start": -2.0, "end": half_y,
         "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.2},
            {"kind": "breach", "pos": 0.3, "breach_class": "soft_wall", "material": "drywall"}]},
        # upper: offices vs armory+interrogation divider
        {"story": 1, "axis": "X", "pos": 0.0, "start": -half_x, "end": half_x,
         "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.35}, {"kind": "door", "pos": 0.35}]},
        # upper: armory (the objective) walled off REINFORCED — no breach
        {"story": 1, "axis": "Y", "pos": 6.0, "start": 0.0, "end": half_y,
         "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.0, "tag": "armory_door", "reinforceable": True}]},
    ]
    spec["partitions"] = parts

    # --- vertical: stairwell (main), roof ladder+hatch, hole over armory -----
    spec["stairs"] = [{
        "x": -half_x + 4, "y": half_y - 4,
        "from_story": 0, "to_story": floors - 1,
        "style": "switchback", "cut_slabs": True,
    }]
    # roof hatch + ladder near the east side (flanking entry from the roof)
    spec["ladders"] = [{
        "x": half_x - 4, "y": -half_y + 4,
        "from_story": floors - 1, "to_story": floors,
        "facing": "S",
    }]
    spec["vertical_links"] = [
        # hatch to the roof at the ladder top
        {"kind": "hatch", "story": floors, "x": half_x - 4, "y": -half_y + 4},
        # floor hole over the armory: top-down pressure point onto the objective
        {"kind": "floor_hole", "story": floors - 1, "x": half_x - 6, "y": half_y - 5},
    ]
    # roof parapet so the roof is a usable fighting position
    spec["parapets"] = [{"story": floors, "height": 1.1}]

    # --- rooms (tactical), dense ground + objective upstairs ----------------
    rooms = [
        {"id": "lobby", "story": 0, "bounds": [-half_x, -half_y, half_x, -2.0],
         "role": "public_entry", "combat_range": "long"},
        {"id": "holding_cells", "story": 0, "bounds": [-half_x, -2.0, -6.0, half_y],
         "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
        {"id": "booking", "story": 0, "bounds": [-6.0, -2.0, 8.0, half_y],
         "role": "connector", "combat_range": "medium"},
        {"id": "garage", "story": 0, "bounds": [8.0, -2.0, half_x, half_y],
         "role": "open_floor", "combat_range": "medium"},
        {"id": "detective_offices", "story": 1, "bounds": [-half_x, -half_y, half_x, 0.0],
         "role": "connector", "combat_range": "medium"},
        {"id": "interrogation", "story": 1, "bounds": [-half_x, 0.0, 6.0, half_y],
         "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
        {"id": "armory", "story": 1, "bounds": [6.0, 0.0, half_x, half_y],
         "role": "objective_room", "objective": True, "fortifiable": True,
         "combat_range": "close"},
    ]
    spec["rooms"] = rooms

    # --- volumes: front desk cover, cell bunks, evidence racks, roof unit ----
    objz = sh  # upper floor level
    vols = [
        {"name": "front_desk", "x": 0.0, "y": -4.0, "z": 0.55,
         "size_x": 6.0, "size_y": 0.9, "size_z": 1.1, "collision": "convex", "material": "wood"},
        {"name": "evidence_rack", "x": half_x - 4, "y": half_y - 6, "z": objz + 1.0,
         "size_x": 0.8, "size_y": 5.0, "size_z": 2.0, "collision": "convex", "material": "metal"},
        {"name": "ARMORY_LOCKER", "x": half_x - 3, "y": half_y - 3, "z": objz + 1.0,
         "size_x": 3.0, "size_y": 0.8, "size_z": 2.0, "collision": "convex", "material": "metal"},
        {"name": "roof_unit", "x": -half_x + 6, "y": half_y - 6,
         "z": floors * sh + 0.6, "size_x": 3.0, "size_y": 2.0, "size_z": 1.2,
         "collision": "convex", "material": "metal"},
    ]
    spec["volumes"] = vols

    # --- vault ledge: front desk doubles as vaultable cover -----------------
    spec["vault_ledges"] = [
        {"x": 0.0, "y": -1.0, "story": 0, "length": 4.0, "axis": "X",
         "height": 1.1, "material": "wood"},
    ]

    # --- markers -------------------------------------------------------------
    armory_xyz = (half_x - 4, half_y - 4, objz)
    spec["markers"] = [
        {"type": "attacker_spawn", "id": "A", "x": -2, "y": -half_y - 3, "z": 0,
         "rot_z": 90, "room": "lobby"},
        {"type": "attacker_spawn", "id": "B", "x": half_x + 3, "y": 0, "z": 0,
         "rot_z": 180, "room": "garage"},
        {"type": "attacker_spawn", "id": "ROOF", "x": half_x - 4, "y": -half_y + 4,
         "z": floors * sh, "rot_z": 0, "room": "armory"},
        {"type": "defender_spawn", "x": armory_xyz[0], "y": armory_xyz[1],
         "z": armory_xyz[2], "rot_z": 270, "room": "armory"},
        {"type": "objective", "id": "A", "x": armory_xyz[0], "y": armory_xyz[1],
         "z": armory_xyz[2], "room": "armory", "meta": {"kind": "secure"}},
        {"type": "cover_high", "x": 0, "y": -4, "z": 0, "room": "lobby"},
        {"type": "camera_socket", "id": "01", "x": half_x - 3, "y": -half_y + 2,
         "z": 3.0, "room": "lobby"},
    ]

    # --- heist loop if in heist mode ----------------------------------------
    if mode == "heist":
        spec["objectives"] = [
            {"id": "crack_armory", "kind": "drill", "x": armory_xyz[0],
             "y": armory_xyz[1], "z": armory_xyz[2], "room": "armory",
             "required": True, "duration": 75},
            {"id": "grab_evidence", "kind": "grab", "x": half_x - 4,
             "y": half_y - 6, "z": objz, "room": "armory", "required": False},
        ]
        spec["loot"] = [
            {"id": "seized_cash", "kind": "cash", "x": armory_xyz[0],
             "y": armory_xyz[1], "z": armory_xyz[2], "value": 200000, "bags": 2,
             "room": "armory"},
            {"id": "weapons", "kind": "cargo", "x": half_x - 3, "y": half_y - 3,
             "z": objz, "value": 150000, "bags": 3, "room": "armory"},
        ]
        spec["zones"] = [
            {"id": "main", "kind": "extraction", "story": 0,
             "bounds": [8.0, -2.0, half_x, half_y]},  # the garage bay
            {"id": "stage", "kind": "secure", "story": 0,
             "bounds": [-half_x, -half_y, -half_x + 6, -half_y + 6]},
        ]
        spec["markers"] = [
            {"type": "crew_spawn", "id": "A", "x": -2, "y": -half_y - 3, "z": 0,
             "rot_z": 90, "room": "lobby", "meta": {"phase": "stealth"}},
            {"type": "responder_spawn", "id": "1", "x": -half_x - 3, "y": 0,
             "z": 0, "meta": {"phase": "loud"}},
            {"type": "camera_socket", "id": "01", "x": half_x - 3,
             "y": -half_y + 2, "z": 3.0, "room": "lobby"},
        ]

    return spec


# ---------------------------------------------------------------------------
# CORNER DELI  --  2-story deli/market over a basement, heist-first
# ---------------------------------------------------------------------------
def corner_deli(name: str = "corner_deli_preset",
                mode: str = "heist",
                basement: bool = True,
                scale_ref: bool = False,
                floors: int = 2) -> dict:
    """A corner deli/market: customer floor + deli counter, market aisles,
    kitchen, and a stockroom/loading bay on the ground; manager office,
    a back apartment, and a server room upstairs; a vault + cold storage in
    the basement. Three vertical routes — a switchback stair spanning the
    whole building (basement->roof), a side ladder to the roof, and a floor
    hole as a vertical attack angle. Heist mode (default) carries a loot
    economy across all three levels; assault mode converts to attacker/
    defender objective play. floors is fixed at 2 above ground (this recipe is
    inherently a 2-story-over-basement deli); the arg is accepted but ignored
    so the CLI stays uniform."""
    fx, fy = 38.0, 28.0
    sh = 3.3
    half_x, half_y = fx / 2, fy / 2

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name,
        "mode": mode,
        "seed": 1984,
        "grid": 0.5,
        "footprint_x": fx,
        "footprint_y": fy,
        "story_height": sh,
        "n_stories": 2,
        "has_basement": bool(basement),
        "wall_thick": 0.35,
        "floor_thick": 0.3,
        "collision": "convex",
        "auto_exterior": True,
        "scale_ref": bool(scale_ref),
        "default_material": "brick_ext",
        "materials": [
            {"id": "brick_ext", "acoustic": "Concrete", "absorption": 0.72, "damping": 0.62},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.08, "damping": 0.05},
            {"id": "metal", "acoustic": "Metal", "absorption": 0.18, "damping": 0.16},
            {"id": "wood", "acoustic": "Wood", "absorption": 0.35, "damping": 0.3},
        ],
    }

    # --- exterior walls ------------------------------------------------------
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "brick_ext", "openings": [
            {"kind": "door", "pos": -0.28, "width": 1.2, "tag": "front_customer_entry"},
            {"kind": "window", "pos": 0.0, "width": 2.0, "sill": 0.85, "vaultable": True, "material": "glass"},
            {"kind": "breach", "pos": 0.34, "width": 1.6, "breach_class": "soft_wall", "material": "drywall", "tag": "south_breach"}]},
        {"wall": "N", "story": 0, "material": "brick_ext", "openings": [
            {"kind": "garage", "pos": -0.25, "width": 3.2, "height": 2.7, "tag": "loading_bay"},
            {"kind": "door", "pos": 0.32, "width": 1.1, "tag": "rear_staff_entry"}]},
        {"wall": "W", "story": 0, "material": "brick_ext", "openings": [
            {"kind": "door", "pos": 0.18, "width": 1.0, "tag": "alley_entry"},
            {"kind": "breach", "pos": -0.32, "width": 1.5, "breach_class": "soft_wall", "material": "drywall", "tag": "alley_soft_wall"}]},
        {"wall": "E", "story": 0, "material": "brick_ext", "openings": [
            {"kind": "window", "pos": -0.25, "width": 1.4, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.25, "width": 1.4, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "S", "story": 1, "material": "brick_ext", "openings": [
            {"kind": "window", "pos": -0.28, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.28, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 1, "material": "brick_ext", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.4, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "breach", "pos": 0.34, "width": 1.4, "breach_class": "soft_wall", "material": "drywall", "tag": "roofline_breach"}]},
        {"wall": "E", "story": 1, "material": "brick_ext", "openings": [
            {"kind": "window", "pos": 0.2, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"}]},
    ]

    # --- partitions (ground + upper always; basement only if present) --------
    parts = [
        {"story": 0, "axis": "X", "pos": -8.0, "start": -14.0, "end": 14.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.4, "width": 1.1, "tag": "customer_to_counter"},
            {"kind": "breach", "pos": 0.38, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]},
        {"story": 0, "axis": "X", "pos": 7.0, "start": -14.0, "end": 14.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": 0.42, "width": 1.1, "tag": "kitchen_to_loading"},
            {"kind": "window", "pos": -0.3, "width": 1.4, "sill": 1.1, "material": "glass"}]},
        {"story": 0, "axis": "Y", "pos": -3.0, "start": -19.0, "end": 19.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.05, "width": 1.2, "tag": "front_to_back"},
            {"kind": "breach", "pos": 0.28, "width": 1.5, "breach_class": "soft_wall", "material": "drywall"}]},
        {"story": 0, "axis": "Y", "pos": 6.0, "start": -19.0, "end": 19.0, "material": "drywall", "openings": [
            {"kind": "garage", "pos": 0.15, "width": 2.4, "height": 2.5, "tag": "stockroom_gate"},
            {"kind": "door", "pos": -0.4, "width": 1.0, "tag": "office_stair_door"}]},
        {"story": 1, "axis": "X", "pos": -2.0, "start": -14.0, "end": 14.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.1, "tag": "hall_to_manager_office"},
            {"kind": "breach", "pos": 0.36, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]},
        {"story": 1, "axis": "Y", "pos": 2.0, "start": -19.0, "end": 19.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.25, "width": 1.0, "tag": "apartment_hall"},
            {"kind": "breach", "pos": 0.28, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]},
    ]
    if basement:
        parts += [
            {"story": -1, "axis": "X", "pos": 1.0, "start": -12.0, "end": 12.0, "material": "brick_ext", "openings": [
                {"kind": "door", "pos": -0.35, "width": 1.1, "tag": "basement_corridor"},
                {"kind": "breach", "pos": 0.3, "width": 1.4, "breach_class": "reinforceable", "material": "brick_ext", "reinforceable": True, "tag": "vault_side_breach"}]},
            {"story": -1, "axis": "Y", "pos": 1.0, "start": -16.0, "end": 16.0, "material": "brick_ext", "openings": [
                {"kind": "door", "pos": 0.1, "width": 1.1, "tag": "cold_room_door"},
                {"kind": "breach", "pos": -0.32, "width": 1.4, "breach_class": "reinforceable", "material": "brick_ext", "reinforceable": True}]},
        ]
    spec["partitions"] = parts

    # --- vertical: stair spans the whole building; ladder + floor hole + hatch
    stair_lo = -1 if basement else 0
    spec["stairs"] = [{
        "x": -15.0, "y": 9.0, "from_story": stair_lo, "to_story": 2,
        "width": 1.4, "run": 5.5, "style": "switchback", "cut_slabs": True}]
    spec["ladders"] = [{
        "x": 17.5, "y": 9.5, "from_story": 0, "to_story": 2,
        "width": 0.7, "depth": 0.25, "rung_spacing": 0.3, "cut_slabs": True, "facing": "W"}]
    spec["slab_holes"] = [{"story": 1, "x": 8.0, "y": -4.0, "size_x": 2.2, "size_y": 2.2}]
    spec["vertical_links"] = [
        {"kind": "stair", "from_story": stair_lo, "to_story": 2, "role": "main_internal_rotation"},
        {"kind": "floor_hole", "story": 1, "x": 8.0, "y": -4.0, "size_x": 2.2, "size_y": 2.2, "role": "vertical_attack_angle"},
        {"kind": "hatch", "story": 1, "x": -12.0, "y": 8.0, "size_x": 1.4, "size_y": 1.4, "breachable": True, "cut_slab": True, "role": "roof_drop_to_stair"},
    ]
    spec["parapets"] = [{"story": 2, "height": 1.0, "thick": 0.35}]

    # --- vault ledges (ground-floor cover) -----------------------------------
    spec["vault_ledges"] = [
        {"story": 0, "x": -11.0, "y": -6.0, "length": 5.5, "axis": "Y", "height": 1.05, "thick": 0.35, "material": "wood"},
        {"story": 0, "x": 10.5, "y": 2.0, "length": 6.0, "axis": "Y", "height": 1.2, "thick": 0.4, "material": "metal"},
    ]

    # --- volumes (props/cover); basement ones only if basement present -------
    vols = [
        {"name": "front_register_counter", "x": -12.0, "y": -7.0, "z": 0.55, "size_x": 6.0, "size_y": 0.9, "size_z": 1.1, "collision": "convex", "material": "wood"},
        {"name": "deli_case_cover", "x": -10.5, "y": -1.2, "z": 0.65, "size_x": 7.0, "size_y": 1.1, "size_z": 1.3, "collision": "convex", "material": "glass"},
        {"name": "aisle_shelf_01", "x": -2.0, "y": -9.5, "z": 0.8, "size_x": 1.0, "size_y": 6.0, "size_z": 1.6, "collision": "convex", "material": "metal"},
        {"name": "aisle_shelf_02", "x": 2.5, "y": -9.5, "z": 0.8, "size_x": 1.0, "size_y": 6.0, "size_z": 1.6, "collision": "convex", "material": "metal"},
        {"name": "kitchen_prep_table", "x": 12.0, "y": -4.5, "z": 0.45, "size_x": 4.0, "size_y": 1.2, "size_z": 0.9, "collision": "convex", "material": "metal"},
        {"name": "loading_pallet_stack", "x": 12.0, "y": 10.0, "z": 0.75, "size_x": 4.5, "size_y": 2.5, "size_z": 1.5, "collision": "convex", "material": "wood"},
        {"name": "stockroom_rack_01", "x": 2.0, "y": 10.5, "z": 1.0, "size_x": 1.0, "size_y": 5.5, "size_z": 2.0, "collision": "convex", "material": "metal"},
        {"name": "manager_desk", "x": -9.5, "y": -6.5, "z": sh + 0.55, "size_x": 3.0, "size_y": 1.4, "size_z": 1.1, "collision": "convex", "material": "wood"},
        {"name": "server_rack_cluster", "x": 8.0, "y": 8.0, "z": sh + 0.8, "size_x": 4.0, "size_y": 1.4, "size_z": 2.2, "collision": "convex", "material": "metal"},
        {"name": "apartment_sofa_cover", "x": 7.5, "y": -8.0, "z": sh + 0.45, "size_x": 4.0, "size_y": 1.2, "size_z": 0.9, "collision": "convex", "material": "wood"},
    ]
    if basement:
        vols += [
            {"name": "basement_vault_block", "x": 8.5, "y": 6.0, "z": -2.65, "size_x": 7.0, "size_y": 5.0, "size_z": 1.3, "collision": "convex", "material": "metal"},
            {"name": "basement_cold_room_rack", "x": -8.0, "y": 5.0, "z": -2.5, "size_x": 6.0, "size_y": 1.0, "size_z": 1.6, "collision": "convex", "material": "metal"},
        ]
    spec["volumes"] = vols

    # --- rooms ---------------------------------------------------------------
    rooms = [
        {"id": "customer_floor", "story": 0, "bounds": [-19.0, -14.0, -8.0, -3.0], "role": "public_entry", "combat_range": "medium"},
        {"id": "deli_counter", "story": 0, "bounds": [-19.0, -3.0, -8.0, 6.0], "role": "objective_room", "objective": True, "combat_range": "close", "fortifiable": True},
        {"id": "market_aisles", "story": 0, "bounds": [-8.0, -14.0, 7.0, -3.0], "role": "connector", "combat_range": "medium"},
        {"id": "kitchen", "story": 0, "bounds": [7.0, -14.0, 19.0, 6.0], "role": "connector", "combat_range": "close"},
        {"id": "stockroom_loading", "story": 0, "bounds": [-8.0, 6.0, 19.0, 14.0], "role": "public_entry", "combat_range": "long"},
        {"id": "stairwell", "story": 0, "bounds": [-19.0, 6.0, -8.0, 14.0], "role": "connector", "combat_range": "close"},
        {"id": "manager_office", "story": 1, "bounds": [-19.0, -14.0, -2.0, 2.0], "role": "objective_room", "objective": True, "combat_range": "medium", "fortifiable": True},
        {"id": "apartment_hideout", "story": 1, "bounds": [-2.0, -14.0, 19.0, 2.0], "role": "fortifiable", "combat_range": "close", "fortifiable": True},
        {"id": "server_room", "story": 1, "bounds": [-2.0, 2.0, 19.0, 14.0], "role": "objective_room", "objective": True, "combat_range": "medium", "fortifiable": True},
        {"id": "upper_hall", "story": 1, "bounds": [-19.0, 2.0, -2.0, 14.0], "role": "connector", "combat_range": "medium"},
    ]
    if basement:
        rooms += [
            {"id": "basement_corridor", "story": -1, "bounds": [-19.0, -14.0, 1.0, 1.0], "role": "connector", "combat_range": "medium"},
            {"id": "cold_storage", "story": -1, "bounds": [-19.0, 1.0, 1.0, 14.0], "role": "loot_room", "combat_range": "close"},
            {"id": "basement_vault", "story": -1, "bounds": [1.0, 1.0, 19.0, 14.0], "role": "objective_room", "objective": True, "combat_range": "close", "fortifiable": True},
            {"id": "utility_room", "story": -1, "bounds": [1.0, -14.0, 19.0, 1.0], "role": "connector", "combat_range": "medium"},
        ]
    spec["rooms"] = rooms

    # --- markers (shared: spawns, cover, cameras, patrols) -------------------
    markers = [
        {"type": "attacker_spawn", "id": "STEALTH_FRONT", "x": 0.0, "y": -18.0, "z": 0.0, "rot_z": 0, "meta": {"phase": "stealth"}},
        {"type": "attacker_spawn", "id": "LOUD_ALLEY", "x": -22.0, "y": 4.0, "z": 0.0, "rot_z": 90, "meta": {"phase": "loud"}},
        {"type": "cover_low", "id": "AISLE_LEFT", "x": -2.0, "y": -9.5, "z": 0.0, "room": "market_aisles"},
        {"type": "cover_low", "id": "AISLE_RIGHT", "x": 2.5, "y": -9.5, "z": 0.0, "room": "market_aisles"},
        {"type": "cover_high", "id": "PALLET_STACK", "x": 12.0, "y": 10.0, "z": 0.0, "room": "stockroom_loading"},
        {"type": "camera_socket", "id": "CAM_FRONT", "x": -17.5, "y": -12.5, "z": 2.6, "room": "customer_floor", "rot_z": 45},
        {"type": "camera_socket", "id": "CAM_SERVER", "x": 16.0, "y": 12.0, "z": sh + 2.5, "room": "server_room", "rot_z": -135},
        {"type": "patrol_point", "id": "P01", "x": -2.0, "y": -11.0, "z": 0.0, "room": "market_aisles"},
        {"type": "patrol_point", "id": "P02", "x": 12.0, "y": -4.0, "z": 0.0, "room": "kitchen"},
        {"type": "patrol_point", "id": "P03", "x": 4.0, "y": 10.0, "z": 0.0, "room": "stockroom_loading"},
    ]

    # --- mode-specific gameplay ---------------------------------------------
    if mode == "heist":
        spec["objectives"] = [
            {"id": "grab_register_cash", "kind": "bag_cash", "x": -12.0, "y": -7.0, "z": 0.9, "room": "deli_counter", "required": True, "duration": 8.0, "meta": {"phase": "stealth_or_loud", "payoff": "fast_cash"}},
            {"id": "wipe_camera_server", "kind": "hack", "x": 8.0, "y": 8.0, "z": sh + 1.1, "room": "server_room", "required": False, "duration": 18.0, "meta": {"reward": "lower_alarm_pressure"}},
        ]
        spec["loot"] = [
            {"id": "cigarette_case_01", "kind": "contraband_case", "x": 13.5, "y": 10.0, "z": 0.9, "value": 1500, "bags": 1, "room": "stockroom_loading"},
            {"id": "manager_safe_docs", "kind": "evidence", "x": -9.5, "y": -6.5, "z": sh + 0.9, "value": 3000, "bags": 1, "room": "manager_office"},
        ]
        spec["zones"] = [
            {"id": "south_van_extract", "kind": "extraction", "story": 0, "bounds": [-6.0, -20.0, 6.0, -15.0], "meta": {"phase": "escape"}},
            {"id": "rear_alley_drop", "kind": "drop", "story": 0, "bounds": [8.0, 15.0, 18.0, 20.0], "meta": {"bag_throw": True}},
            {"id": "stockroom_secure_area", "kind": "secure", "story": 0, "bounds": [7.0, 6.0, 19.0, 14.0], "meta": {"temporary_loot_hold": True}},
        ]
        if basement:
            spec["objectives"].insert(1, {"id": "drill_basement_safe", "kind": "drill", "x": 8.5, "y": 6.0, "z": -2.2, "room": "basement_vault", "required": True, "duration": 45.0, "meta": {"phase": "loud", "noise_radius": 30}})
            spec["loot"] += [
                {"id": "cold_room_rare_meat", "kind": "black_market_food", "x": -8.0, "y": 5.0, "z": -2.1, "value": 2200, "bags": 2, "room": "cold_storage"},
                {"id": "vault_cash_bags", "kind": "cash", "x": 8.5, "y": 6.0, "z": -2.0, "value": 8000, "bags": 3, "room": "basement_vault"},
            ]
        markers += [
            {"type": "extraction", "id": "VAN", "x": 0.0, "y": -17.0, "z": 0.0, "rot_z": 180, "meta": {"zone": "south_van_extract"}},
            {"type": "objective", "id": "REGISTER", "x": -12.0, "y": -7.0, "z": 0.9, "room": "deli_counter"},
            {"type": "objective", "id": "SERVER", "x": 8.0, "y": 8.0, "z": sh + 1.1, "room": "server_room"},
        ]
        if basement:
            markers += [
                {"type": "objective", "id": "SAFE", "x": 8.5, "y": 6.0, "z": -2.2, "room": "basement_vault"},
                {"type": "loot", "id": "VAULT_CASH", "x": 8.5, "y": 6.0, "z": -2.0, "room": "basement_vault"},
                {"type": "patrol_point", "id": "P04", "x": -8.0, "y": 5.0, "z": -sh, "room": "cold_storage"},
            ]
    else:  # assault — defender holds the objective rooms; attackers breach in
        markers += [
            {"type": "defender_spawn", "x": 8.5, "y": 6.0, "z": (-2.2 if basement else sh + 0.5), "rot_z": 270, "room": ("basement_vault" if basement else "server_room")},
            {"type": "objective", "id": "DELI", "x": -12.0, "y": -7.0, "z": 0.9, "room": "deli_counter"},
            {"type": "objective", "id": "SERVER", "x": 8.0, "y": 8.0, "z": sh + 1.1, "room": "server_room"},
        ]

    spec["markers"] = markers
    return spec


# ---------------------------------------------------------------------------
# REGISTRY
# ---------------------------------------------------------------------------
REGISTRY = {
    "bank": bank,
    "police_station": police_station,
    "corner_deli": corner_deli,
    # rowhome, warehouse, safehouse -> follow
}


def make(preset: str, **kwargs) -> dict:
    if preset not in REGISTRY:
        raise KeyError(f"unknown preset '{preset}'. "
                       f"available: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[preset](**kwargs)
