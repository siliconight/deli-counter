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

import level_design


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


# eviction log of the most recent make(..., stairs_first=True) call:
# [(kind, name, reason)] for props/markers/rooms the core reservation removed
LAST_CORE_EVICTIONS: list = []


# ---------------------------------------------------------------------------
# BANK  --  reference recipe
# ---------------------------------------------------------------------------
def bank(name: str = "bank_preset",
         mode: str = "heist",
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
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "side_entry"},
        ]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.25, "width": 1.2, "tag": "staff_entry"},
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

    # second vertical link into the vault basement: a straight service stair on
    # the east/lobby side. A single stair makes the vault a one-approach siege
    # (combat_audit flags VERT_DEAD_END); a second link gives 4-player co-op a
    # flank route and splits the push. The gameplay team can still wall it for a
    # holdout -- more routes = more playground. (Roof stays single-access by
    # design; it's unfurnished siege space.)
    if basement:
        spec["stairs"].append({
            "x": half_x - 4, "y": -half_y + 5,
            "from_story": -1, "to_story": 0,
            "style": "straight", "cut_slabs": True,
        })

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

    # the roof story stays single-access by design (unfurnished siege space);
    # the vault basement now has two vertical links, so only the roof is accepted.
    spec.setdefault("audit_accept", []).append(
        {"code": "VERT_DEAD_END",
         "why": "roof story: single stair to unfurnished roof is the design"})
    return spec


# ---------------------------------------------------------------------------
# POLICE STATION  --  dense tactical interior, 2 floors + roof access
# ---------------------------------------------------------------------------
def police_station(name: str = "police_station_preset",
                   mode: str = "heist",
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
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "staff_entry"},
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
            {"kind": "door", "pos": 0.0, "width": 1.4, "tag": "armory_door", "reinforceable": True}]},
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

    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -16.0, "y": -12.0, "from_story": 0, "to_story": 1,
         "facing": "E", "cut_slabs": True})
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
            {"kind": "door", "pos": 0.18, "width": 1.4, "tag": "alley_entry"},
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
        {"story": 0, "axis": "Y", "pos": -8.0, "start": -14.0, "end": 14.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.4, "width": 1.1, "tag": "customer_to_counter"},
            {"kind": "breach", "pos": 0.38, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]},
        {"story": 0, "axis": "X", "pos": 7.0, "start": -14.0, "end": 14.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": 0.42, "width": 1.1, "tag": "kitchen_to_loading"},
            {"kind": "window", "pos": -0.3, "width": 1.4, "sill": 1.1, "material": "glass"}]},
        {"story": 0, "axis": "Y", "pos": -3.0, "start": -19.0, "end": 19.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.05, "width": 1.2, "tag": "front_to_back"},
            {"kind": "breach", "pos": 0.28, "width": 1.5, "breach_class": "soft_wall", "material": "drywall"}]},
        {"story": 0, "axis": "X", "pos": 6.0, "start": -19.0, "end": 19.0, "material": "drywall", "openings": [
            {"kind": "garage", "pos": 0.15, "width": 2.4, "height": 2.5, "tag": "stockroom_gate"},
            {"kind": "door", "pos": -0.4, "width": 1.2, "tag": "office_stair_door"}]},
        {"story": 1, "axis": "Y", "pos": -2.0, "start": -14.0, "end": 14.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.1, "tag": "hall_to_manager_office"},
            {"kind": "breach", "pos": 0.36, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]},
        {"story": 1, "axis": "X", "pos": 2.0, "start": -19.0, "end": 19.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.25, "width": 1.4, "tag": "apartment_hall"},
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
    # roof ladder moved out of the public stockroom corner: a roof-access
    # climb may not originate in a public_entry / objective room (ladder
    # spec s8.3), so it rises through the apartment side instead.
    spec["ladders"] = [{
        "x": 8.0, "y": -12.0, "from_story": 0, "to_story": 2,
        "width": 0.7, "depth": 0.25, "rung_spacing": 0.3, "cut_slabs": True, "facing": "N"}]
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
    # combat-audit second vertical link: stories -1<->0 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -7.0, "y": -13.0, "from_story": -1, "to_story": 0,
         "facing": "N", "cut_slabs": True})
    return spec


# ---------------------------------------------------------------------------
# COMPOUND  --  multi-story assault compound with a central atrium + boss room
# ---------------------------------------------------------------------------
def compound(name: str = "compound_preset",
             mode: str = "heist",
             floors: int = 3,
             scale_ref: bool = False,
             basement: bool = False) -> dict:
    """A fortified multi-story compound built for a climactic assault: a wide
    ground floor (garage, entry hall, main hall, fortifiable security rooms), a
    central atrium punched up through the upper floors as a vertical sightline,
    two switchback stairs wrapping the core, and an objective room on the top
    floor — a boss suite to clear in assault mode, or a penthouse vault to crack
    in heist mode. floors is 2 or 3 (default 3); the atrium and objective always
    sit on the top floor. No basement (the arg is accepted but ignored)."""
    floors = max(2, min(3, int(floors)))
    top = floors - 1            # index of the top story
    sh = 3.8
    fx, fy = 42.0, 30.0

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name,
        "mode": mode,
        "seed": 1983,
        "grid": 0.5,
        "footprint_x": fx,
        "footprint_y": fy,
        "story_height": sh,
        "n_stories": floors,
        "has_basement": False,
        "wall_thick": 0.3,
        "floor_thick": 0.3,
        "collision": "convex",
        "auto_exterior": True,
        "scale_ref": bool(scale_ref),
        "default_material": "concrete",
        "materials": [
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "drywall", "acoustic": "Drywall"},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
            {"id": "metal", "acoustic": "Metal", "absorption": 0.5, "damping": 0.3},
            {"id": "wood", "acoustic": "Wood"},
        ],
    }

    # --- exterior walls: solid ground, windowed middle, glass-front top ------
    ext = [
        {"wall": "S", "story": 0, "material": "concrete", "openings": [
            {"kind": "garage", "pos": -0.34, "width": 4.2, "tag": "garage_entry"},
            {"kind": "door", "pos": 0.0, "width": 1.8, "tag": "front_entry"},
            {"kind": "window", "pos": 0.28, "width": 2.2, "sill": 1.0, "vaultable": True},
            {"kind": "window", "pos": 0.42, "width": 2.2, "sill": 1.0, "vaultable": True}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.18, "width": 1.5, "tag": "rear_service"},
            {"kind": "breach", "pos": 0.22, "width": 1.5, "breach_class": "soft_wall", "material": "drywall", "tag": "rear_breach"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.10, "width": 1.1, "tag": "west_entry"},
            {"kind": "window", "pos": 0.28, "width": 2.0, "sill": 1.0, "vaultable": True}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.10, "width": 1.1, "tag": "east_entry"},
            {"kind": "breach", "pos": -0.25, "width": 1.5, "breach_class": "soft_wall", "material": "drywall", "tag": "east_breach"}]},
    ]
    # middle floors (everything between ground and top): windowed on all sides
    for st in range(1, top):
        for w in ("S", "N", "W", "E"):
            ext.append({"wall": w, "story": st, "material": "concrete", "openings": [
                {"kind": "window", "pos": -0.25, "width": 1.8, "sill": 0.9, "vaultable": True},
                {"kind": "window", "pos": 0.25, "width": 1.8, "sill": 0.9, "vaultable": True}]})
    # top floor: glass front (S), windows elsewhere
    ext += [
        {"wall": "S", "story": top, "material": "glass", "openings": [
            {"kind": "window", "pos": -0.28, "width": 2.2, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.0, "width": 2.4, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.28, "width": 2.2, "sill": 0.9, "vaultable": True}]},
        {"wall": "N", "story": top, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.25, "width": 1.8, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.25, "width": 1.8, "sill": 0.9, "vaultable": True}]},
        {"wall": "W", "story": top, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.18, "width": 1.8, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.18, "width": 1.8, "sill": 0.9, "vaultable": True}]},
        {"wall": "E", "story": top, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.18, "width": 1.8, "sill": 0.9, "vaultable": True},
            {"kind": "window", "pos": 0.18, "width": 1.8, "sill": 0.9, "vaultable": True}]},
    ]
    spec["ext_walls"] = ext

    # --- partitions: ground floor split; upper floors get a cross-wall -------
    parts = [
        {"story": 0, "axis": "X", "pos": -3.0, "start": -21.0, "end": 21.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.18}, {"kind": "door", "pos": 0.18}]},
        {"story": 0, "axis": "X", "pos": 6.5, "start": -21.0, "end": 21.0, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.35}, {"kind": "door", "pos": 0.0}, {"kind": "door", "pos": 0.35}]},
        {"story": 0, "axis": "Y", "pos": -8.0, "start": 6.5, "end": 15.0, "material": "drywall", "openings": [{"kind": "door", "pos": 0.0}]},
        {"story": 0, "axis": "Y", "pos": 8.0, "start": 6.5, "end": 15.0, "material": "drywall", "openings": [{"kind": "door", "pos": 0.0}]},
    ]
    for st in range(1, floors):
        # cross-wall + two flanking rooms; openings avoid the atrium in the middle
        parts += [
            {"story": st, "axis": "X", "pos": (1.0 if st == top else 0.0), "start": -21.0, "end": 21.0, "material": "drywall", "openings": [
                {"kind": "door", "pos": -0.22}, {"kind": "door", "pos": 0.22}]},
            {"story": st, "axis": "Y", "pos": -7.0, "start": 1.0, "end": 15.0, "material": "drywall", "openings": [{"kind": "door", "pos": 0.0}]},
            {"story": st, "axis": "Y", "pos": 7.0, "start": 1.0, "end": 15.0, "material": "drywall", "openings": [{"kind": "door", "pos": 0.0, "width": 1.5}]},
        ]
    spec["partitions"] = parts

    # --- two switchback stairs wrapping the core, climbing to the top --------
    spec["stairs"] = [
        {"x": 0.0, "y": 11.0, "from_story": 0, "to_story": top, "style": "switchback", "cut_slabs": True},
        {"x": -15.0, "y": 10.5, "from_story": 0, "to_story": top, "style": "switchback", "cut_slabs": True},
    ]
    # --- central atrium: a slab hole on every floor above ground ------------
    holes = []
    for st in range(1, floors):
        shrink = (st - 1) * 2.0   # atrium tapers slightly as it rises
        holes.append({"story": st, "x": 0.0, "y": 0.5, "size_x": 10.0 - shrink, "size_y": 8.0 - shrink})
    spec["slab_holes"] = holes
    spec["vertical_links"] = [
        {"kind": "stair", "from_story": 0, "to_story": top, "role": "main_rotation"},
        {"kind": "stair", "from_story": 0, "to_story": top, "role": "flank_rotation"},
        {"kind": "floor_hole", "story": 1, "x": 0.0, "y": 0.5, "size_x": 10.0, "size_y": 8.0, "role": "atrium_vertical_sightline"},
    ]
    spec["parapets"] = [{"story": floors, "height": 1.1, "thick": 0.3}]

    # --- vault ledges: overlook railings on upper floors ---------------------
    ledges = []
    for st in range(1, floors):
        ledges += [
            {"x": -10.0, "y": -0.5, "story": st, "length": 6.0, "axis": "X", "height": 1.1, "material": "wood"},
            {"x": 10.0, "y": -0.5, "story": st, "length": 6.0, "axis": "X", "height": 1.1, "material": "wood"},
        ]
    spec["vault_ledges"] = ledges

    # --- volumes: cover on every floor, boss desk + statue up top ------------
    vols = [
        {"name": "front_desk", "x": 0.0, "y": -7.5, "z": 0.55, "size_x": 8.0, "size_y": 1.0, "size_z": 1.1, "collision": "convex", "material": "wood"},
        {"name": "center_bar", "x": 0.0, "y": 1.5, "z": 0.55, "size_x": 10.0, "size_y": 1.2, "size_z": 1.1, "collision": "convex", "material": "wood"},
        {"name": "garage_cover", "x": -15.0, "y": 10.5, "z": 0.8, "size_x": 4.0, "size_y": 2.0, "size_z": 1.6, "collision": "convex", "material": "metal"},
        {"name": "security_block", "x": 15.0, "y": 10.0, "z": 0.8, "size_x": 4.0, "size_y": 2.0, "size_z": 1.6, "collision": "convex", "material": "metal"},
    ]
    for st in range(1, floors):
        zbase = st * sh
        vols += [
            {"name": f"upper_cover_west_{st}", "x": -12.0, "y": 8.0, "z": zbase + 0.55, "size_x": 3.5, "size_y": 1.0, "size_z": 1.1, "collision": "convex", "material": "wood"},
            {"name": f"upper_cover_east_{st}", "x": 12.0, "y": 8.0, "z": zbase + 0.55, "size_x": 3.5, "size_y": 1.0, "size_z": 1.1, "collision": "convex", "material": "wood"},
        ]
    ztop = top * sh
    vols += [
        {"name": "boss_desk", "x": 0.0, "y": 9.0, "z": ztop + 0.55, "size_x": 5.0, "size_y": 1.6, "size_z": 1.2, "collision": "convex", "material": "wood"},
        {"name": "north_statue", "x": 0.0, "y": 13.0, "z": ztop + 0.9, "size_x": 2.0, "size_y": 2.0, "size_z": 3.0, "collision": "convex", "material": "metal"},
        {"name": "roof_unit", "x": 15.0, "y": 10.0, "z": floors * sh + 0.7, "size_x": 4.0, "size_y": 3.0, "size_z": 1.4, "collision": "convex", "material": "metal"},
    ]
    spec["volumes"] = vols

    # --- rooms: ground fixed; upper floors generated; objective on top -------
    rooms = [
        {"id": "entry_hall", "story": 0, "bounds": [-21.0, -15.0, 21.0, -3.0], "role": "public_entry", "combat_range": "long"},
        {"id": "main_hall", "story": 0, "bounds": [-21.0, -3.0, 21.0, 6.5], "role": "connector", "combat_range": "long"},
        {"id": "garage", "story": 0, "bounds": [-21.0, 6.5, -8.0, 15.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
        {"id": "stair_core", "story": 0, "bounds": [-8.0, 6.5, 8.0, 15.0], "role": "connector", "combat_range": "close"},
        {"id": "east_security", "story": 0, "bounds": [8.0, 6.5, 21.0, 15.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
    ]
    for st in range(1, floors):
        if st == top:
            rooms += [
                {"id": "top_balcony", "story": st, "bounds": [-21.0, -15.0, 21.0, 1.0], "role": "connector", "combat_range": "medium"},
                {"id": "antechamber", "story": st, "bounds": [-21.0, 1.0, -7.5, 15.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
                {"id": "objective_suite", "story": st, "bounds": [-7.5, 1.0, 7.5, 15.0], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
                {"id": "trophy_room", "story": st, "bounds": [7.5, 1.0, 21.0, 15.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
            ]
        else:
            rooms += [
                {"id": f"gallery_{st}", "story": st, "bounds": [-21.0, -15.0, 21.0, 0.0], "role": "connector", "combat_range": "medium"},
                {"id": f"west_room_{st}", "story": st, "bounds": [-21.0, 0.0, -7.0, 15.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
                {"id": f"overlook_{st}", "story": st, "bounds": [-7.0, 0.0, 7.0, 15.0], "role": "connector", "combat_range": "medium"},
                {"id": f"east_room_{st}", "story": st, "bounds": [7.0, 0.0, 21.0, 15.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
            ]
    spec["rooms"] = rooms

    # --- markers: attacker spawns + cover always; objective by mode ----------
    boss_z = ztop + 3.8 - 0.2   # eye-ish height in the top suite
    markers = [
        {"type": "attacker_spawn", "id": "A", "x": 0.0, "y": -19.0, "z": 0.0, "rot_z": 90, "room": "entry_hall"},
        {"type": "attacker_spawn", "id": "B", "x": -26.0, "y": 0.0, "z": 0.0, "rot_z": 0, "room": "entry_hall"},
        {"type": "attacker_spawn", "id": "C", "x": 26.0, "y": 2.0, "z": 0.0, "rot_z": 180, "room": "entry_hall"},
        {"type": "cover_high", "x": 0.0, "y": -7.5, "z": 0.0, "room": "entry_hall"},
        {"type": "cover_high", "x": 0.0, "y": 1.5, "z": 0.0, "room": "main_hall"},
        {"type": "camera_socket", "id": "01", "x": 18.0, "y": -10.0, "z": 3.2, "room": "entry_hall"},
        {"type": "camera_socket", "id": "02", "x": -18.0, "y": 10.0, "z": 3.2, "room": "garage"},
    ]
    if mode == "assault":
        markers += [
            {"type": "defender_spawn", "id": "boss", "x": 0.0, "y": 10.0, "z": ztop, "rot_z": 180, "room": "objective_suite"},
            {"type": "objective", "id": "final_objective", "x": 0.0, "y": 10.0, "z": ztop, "room": "objective_suite", "meta": {"kind": "eliminate"}},
            {"type": "cover_high", "x": 0.0, "y": 9.0, "z": ztop, "room": "objective_suite"},
        ]
    else:  # heist — top suite becomes a penthouse vault to crack
        spec["objectives"] = [
            {"id": "crack_penthouse_vault", "kind": "drill", "x": 0.0, "y": 9.0, "z": ztop + 0.2, "room": "objective_suite", "required": True, "duration": 40.0, "meta": {"phase": "loud"}},
        ]
        spec["loot"] = [
            {"id": "penthouse_cash", "kind": "cash", "x": 0.0, "y": 9.0, "z": ztop + 0.3, "value": 9000, "bags": 3, "room": "objective_suite"},
        ]
        spec["zones"] = [
            {"id": "garage_extract", "kind": "extraction", "story": 0, "bounds": [-21.0, 6.5, -8.0, 15.0], "meta": {"phase": "escape"}},
        ]
        markers += [
            {"type": "objective", "id": "VAULT", "x": 0.0, "y": 9.0, "z": ztop + 0.2, "room": "objective_suite"},
            {"type": "loot", "id": "PENTHOUSE_CASH", "x": 0.0, "y": 9.0, "z": ztop + 0.3, "room": "objective_suite"},
            {"type": "extraction", "id": "GARAGE", "x": -15.0, "y": 10.5, "z": 0.0, "rot_z": 0, "room": "garage"},
        ]
    spec["markers"] = markers
    return spec


# ---------------------------------------------------------------------------
# HOSPITAL  --  survival-first: fight floor-by-floor up to a rooftop holdout
# ---------------------------------------------------------------------------
def hospital(name: str = "hospital_preset",
             mode: str = "survival",
             floors: int = 3,
             scale_ref: bool = False,
             basement: bool = False) -> dict:
    """A multi-story hospital built for a survival run: the team starts in the
    ground-floor lobby (a safe_room), fights up through wards and corridors
    floor by floor, and reaches a rooftop helipad holdout (the finale) to
    survive a final wave and extract. Horde spawns are spread across every
    floor — stairwells, ward backs, elevator shafts — so pressure comes from
    all sides as you ascend. floors is 2-4 (default 3); the lobby is always the
    start and the roof is always the finale. In assault mode the rooftop
    becomes an objective room to take instead, with horde spawns dropped.

    Maps to roadmap L8. The first preset built survival-first — proves the mode
    translates into generated geometry, not just hand-authored specs."""
    floors = max(2, min(4, int(floors)))
    top = floors - 1
    sh = 3.6
    fx, fy = 40.0, 30.0
    half_x, half_y = fx / 2, fy / 2

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name,
        "mode": mode,
        "seed": 1985,
        "grid": 0.5,
        "footprint_x": fx,
        "footprint_y": fy,
        "story_height": sh,
        "n_stories": floors,
        "has_basement": bool(basement),
        "wall_thick": 0.3,
        "floor_thick": 0.3,
        "collision": "convex",
        "auto_exterior": True,
        "scale_ref": bool(scale_ref),
        "default_material": "concrete",
        "materials": [
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
            {"id": "tile", "acoustic": "Concrete", "absorption": 0.6, "damping": 0.5},
            {"id": "metal", "acoustic": "Metal", "absorption": 0.3, "damping": 0.2},
        ],
    }

    # --- exterior: glass-front lobby on ground, windowed wards above ---------
    ext = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.1, "width": 2.2, "tag": "main_entrance"},
            {"kind": "window", "pos": -0.35, "width": 2.4, "sill": 0.9, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.3, "width": 2.4, "sill": 0.9, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "garage", "pos": -0.3, "width": 3.4, "height": 2.8, "tag": "ambulance_bay"},
            {"kind": "door", "pos": 0.3, "width": 1.2, "tag": "service_entrance"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "west_entrance"}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "breach", "pos": 0.0, "width": 1.5, "breach_class": "soft_wall", "material": "drywall", "tag": "east_breach"}]},
    ]
    for st in range(1, floors):
        glass = "glass" if st == top else "concrete"
        for w in ("S", "N", "W", "E"):
            ext.append({"wall": w, "story": st, "material": "concrete", "openings": [
                {"kind": "window", "pos": -0.28, "width": 1.6, "sill": 0.9, "vaultable": True, "material": glass},
                {"kind": "window", "pos": 0.28, "width": 1.6, "sill": 0.9, "vaultable": True, "material": glass}]})
    spec["ext_walls"] = ext

    # --- partitions: a central corridor spine + ward divisions per floor -----
    parts = []
    for st in range(0, floors):
        # central east-west corridor wall (the spine), doors along it
        parts.append({"story": st, "axis": "X", "pos": 0.0, "start": -half_x + 1, "end": half_x - 1,
                      "material": "drywall", "openings": [
                          {"kind": "door", "pos": -0.3, "width": 1.4, "tag": f"corridor_n_{st}"},
                          {"kind": "door", "pos": 0.1, "width": 1.4, "tag": f"corridor_s_{st}"},
                          {"kind": "door", "pos": 0.4, "width": 1.4}]})
        # ward cross-walls
        parts.append({"story": st, "axis": "Y", "pos": -8.0, "start": -half_y + 1, "end": half_y - 1,
                      "material": "drywall", "openings": [
                          {"kind": "door", "pos": -0.2, "width": 1.2},
                          {"kind": "breach", "pos": 0.3, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]})
        parts.append({"story": st, "axis": "Y", "pos": 8.0, "start": -half_y + 1, "end": half_y - 1,
                      "material": "drywall", "openings": [
                          {"kind": "door", "pos": 0.2, "width": 1.2},
                          {"kind": "breach", "pos": -0.3, "width": 1.4, "breach_class": "soft_wall", "material": "drywall"}]})
    spec["partitions"] = parts

    # --- vertical: two stairwells (main + emergency) climb the full height ---
    spec["stairs"] = [
        {"x": -15.0, "y": 11.0, "from_story": 0, "to_story": top, "width": 1.4, "style": "switchback", "cut_slabs": True},
        {"x": 15.0, "y": -11.0, "from_story": 0, "to_story": top, "width": 1.2, "style": "switchback", "cut_slabs": True},
    ]
    # an elevator shaft as a vertical horde-spawn channel (floor holes stacked)
    holes = []
    for st in range(1, floors):
        holes.append({"story": st, "x": 0.0, "y": 12.0, "size_x": 2.6, "size_y": 2.6})
    spec["slab_holes"] = holes
    spec["vertical_links"] = [
        {"kind": "stair", "from_story": 0, "to_story": top, "role": "main_route"},
        {"kind": "stair", "from_story": 0, "to_story": top, "role": "emergency_route"},
        {"kind": "floor_hole", "story": 1, "x": 0.0, "y": 12.0, "size_x": 2.6, "size_y": 2.6, "role": "elevator_shaft_horde_channel"},
    ]
    spec["parapets"] = [{"story": floors, "height": 1.1, "thick": 0.3}]

    # --- cover: nurse stations, gurneys, reception ---------------------------
    vols = [
        {"name": "lobby_reception", "x": 0.0, "y": -10.0, "z": 0.55, "size_x": 8.0, "size_y": 1.2, "size_z": 1.1, "collision": "convex", "material": "metal"},
        {"name": "waiting_seats", "x": -10.0, "y": -10.0, "z": 0.3, "size_x": 5.0, "size_y": 2.0, "size_z": 0.6, "collision": "convex", "material": "metal"},
    ]
    for st in range(0, floors):
        zb = st * sh
        vols += [
            {"name": f"nurse_station_{st}", "x": -10.0, "y": 2.0, "z": zb + 0.55, "size_x": 4.0, "size_y": 1.4, "size_z": 1.1, "collision": "convex", "material": "metal"},
            {"name": f"supply_cart_{st}", "x": 10.0, "y": 4.0, "z": zb + 0.5, "size_x": 1.2, "size_y": 2.4, "size_z": 1.0, "collision": "convex", "material": "metal"},
        ]
    # rooftop helipad pad marking + HVAC cover
    ztop = top * sh
    vols += [
        {"name": "helipad_hvac", "x": 12.0, "y": 10.0, "z": floors * sh + 0.7, "size_x": 4.0, "size_y": 3.0, "size_z": 1.4, "collision": "convex", "material": "metal"},
        {"name": "rooftop_stairhead", "x": -15.0, "y": 11.0, "z": floors * sh + 1.1, "size_x": 3.0, "size_y": 3.0, "size_z": 2.2, "collision": "convex", "material": "concrete"},
    ]
    spec["volumes"] = vols

    # --- rooms: lobby (start) on ground, wards on middle, roof (finale) ------
    rooms = [
        {"id": "lobby", "story": 0, "bounds": [-half_x, -half_y, half_x, 0.0], "role": "safe_room", "combat_range": "medium"},
        {"id": "ground_west_ward", "story": 0, "bounds": [-half_x, 0.0, -8.0, half_y], "role": "route_node", "combat_range": "close"},
        {"id": "ground_central", "story": 0, "bounds": [-8.0, 0.0, 8.0, half_y], "role": "connector", "combat_range": "medium"},
        {"id": "ground_east_ward", "story": 0, "bounds": [8.0, 0.0, half_x, half_y], "role": "route_node", "combat_range": "close"},
    ]
    for st in range(1, floors):
        if st == top:
            rooms += [
                {"id": "roof_helipad", "story": st, "bounds": [-half_x, -half_y, half_x, half_y], "role": "finale", "fortifiable": True, "combat_range": "long"},
            ]
        else:
            rooms += [
                {"id": f"ward_south_{st}", "story": st, "bounds": [-half_x, -half_y, half_x, 0.0], "role": "route_node", "combat_range": "close"},
                {"id": f"ward_west_{st}", "story": st, "bounds": [-half_x, 0.0, -8.0, half_y], "role": "route_node", "combat_range": "close"},
                {"id": f"ward_central_{st}", "story": st, "bounds": [-8.0, 0.0, 8.0, half_y], "role": "connector", "combat_range": "medium"},
                {"id": f"ward_east_{st}", "story": st, "bounds": [8.0, 0.0, half_x, half_y], "role": "route_node", "combat_range": "close"},
            ]
    spec["rooms"] = rooms

    # --- zones + markers: mode-specific --------------------------------------
    markers = [
        {"type": "cover_low", "id": "RECEPTION", "x": 0.0, "y": -10.0, "z": 0.0, "room": "lobby"},
        {"type": "cover_low", "id": "WAITING", "x": -10.0, "y": -10.0, "z": 0.0, "room": "lobby"},
    ]

    if mode == "survival":
        spec["zones"] = [
            {"id": "lobby_safe", "kind": "safe_room", "story": 0, "bounds": [-half_x + 1, -half_y + 1, half_x - 1, -1.0]},
            {"id": "rooftop_holdout", "kind": "finale", "story": top, "bounds": [-half_x + 1, -half_y + 1, half_x - 1, half_y - 1]},
            {"id": "helipad_extract", "kind": "extraction", "story": top, "bounds": [8.0, 6.0, half_x - 1, half_y - 1], "meta": {"rescue": "helicopter"}},
        ]
        markers += [
            {"type": "survivor_spawn", "id": "START", "x": 0.0, "y": -12.0, "z": 0.0, "rot_z": 0, "room": "lobby"},
            {"type": "rescue", "id": "CHOPPER", "x": 12.0, "y": 10.0, "z": ztop, "room": "roof_helipad"},
        ]
        # horde spawns: spread across every floor — ward backs + the elevator
        # shaft + stairheads. This is what makes the ascent a survival run.
        for st in range(0, floors):
            zb = st * sh
            markers.append({"type": "horde_spawn", "id": f"H_W{st}", "x": -16.0, "y": 6.0, "z": zb, "room": ("lobby" if st == 0 else None), "meta": {"floor": st}})
            markers.append({"type": "horde_spawn", "id": f"H_E{st}", "x": 16.0, "y": 6.0, "z": zb, "meta": {"floor": st}})
        # elevator-shaft spawn channel (vertical pressure)
        markers.append({"type": "horde_spawn", "id": "H_SHAFT", "x": 0.0, "y": 12.0, "z": 0.0, "meta": {"channel": "elevator"}})
    else:  # assault — rooftop becomes the objective to take; no horde
        # retag the roof room as an objective room
        for r in rooms:
            if r["id"] == "roof_helipad":
                r["role"] = "objective_room"
                r["objective"] = True
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": 0.0, "y": -13.0, "z": 0.0, "rot_z": 0, "room": "lobby"},
            {"type": "attacker_spawn", "id": "B", "x": -18.0, "y": 0.0, "z": 0.0, "rot_z": 90, "room": "lobby"},
            {"type": "defender_spawn", "id": "D", "x": 0.0, "y": 8.0, "z": ztop, "rot_z": 180, "room": "roof_helipad"},
            {"type": "objective", "id": "ROOFTOP", "x": 0.0, "y": 8.0, "z": ztop, "room": "roof_helipad", "meta": {"kind": "capture"}},
        ]

    spec["markers"] = markers
    return spec


# ---------------------------------------------------------------------------
# WAREHOUSE  --  assault sandbox: big open interior, catwalks, sparse cover
# ---------------------------------------------------------------------------
def warehouse(name: str = "warehouse_preset",
              mode: str = "heist",
              floors: int = 1,
              scale_ref: bool = False,
              basement: bool = False) -> dict:
    """A large open warehouse: a single tall main floor with a partial upper
    catwalk/mezzanine, loading docks, and sparse crate/rack cover for long
    sightlines and flanking. The classic assault sandbox — multiple entries
    (roll-up doors, man-doors, a breachable wall), one fortifiable office as a
    holdable point. `floors` is treated as 1 (the mezzanine is generated
    regardless); the arg is accepted for CLI uniformity. Heist mode turns the
    office into a small objective+loot room."""
    sh = 6.0                 # tall single story
    fx, fy = 48.0, 34.0
    half_x, half_y = fx / 2, fy / 2

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 1986, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 1, "has_basement": False, "wall_thick": 0.35,
        "floor_thick": 0.3, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "metal",
        "materials": [
            {"id": "metal", "acoustic": "Metal", "absorption": 0.35, "damping": 0.25},
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
        ],
    }
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "metal", "openings": [
            {"kind": "garage", "pos": -0.3, "width": 4.5, "height": 4.5, "tag": "loading_dock_1"},
            {"kind": "garage", "pos": 0.2, "width": 4.5, "height": 4.5, "tag": "loading_dock_2"},
            {"kind": "door", "pos": 0.45, "width": 1.2, "tag": "south_mandoor"}]},
        {"wall": "N", "story": 0, "material": "metal", "openings": [
            {"kind": "door", "pos": -0.3, "width": 1.2, "tag": "north_mandoor"},
            {"kind": "breach", "pos": 0.25, "width": 1.6, "breach_class": "soft_wall", "material": "drywall", "tag": "north_breach"}]},
        {"wall": "W", "story": 0, "material": "metal", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "west_mandoor"}]},
        {"wall": "E", "story": 0, "material": "metal", "openings": [
            {"kind": "door", "pos": 0.2, "width": 1.2, "tag": "east_office_door"},
            {"kind": "window", "pos": -0.2, "width": 2.0, "sill": 1.0, "vaultable": True}]},
    ]
    # partitions: a full-width wall at y=8 splits main floor from the north
    # strip (doors connect them), then the office is walled off in the NE
    # corner with two doors so the objective has >=2 access paths.
    # (axis="X": wall runs along X at y=pos; axis="Y": wall runs along Y at x=pos)
    spec["partitions"] = [
        {"story": 0, "axis": "X", "pos": 8.0, "start": -half_x, "end": half_x, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.35, "width": 1.4, "tag": "to_north_bay"},
            {"kind": "door", "pos": 0.0, "width": 1.4},
            {"kind": "door", "pos": 0.35, "width": 1.4, "tag": "to_office_zone"}]},
        {"story": 0, "axis": "Y", "pos": 11.0, "start": 8.0, "end": half_y, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.4, "width": 1.1, "tag": "office_door_1"},
            {"kind": "door", "pos": 0.2, "width": 1.1, "tag": "office_door_2"}]},
    ]
    # mezzanine catwalk: a proper partial upper story would need n_stories=2;
    # to keep this a clean single-floor sandbox we use tall stacked cover for
    # verticality instead of a floating catwalk (the schema attaches stairs and
    # ledges to stories, not arbitrary heights).
    spec["stairs"] = []
    spec["vault_ledges"] = []
    # sparse cover: crate stacks (some tall, for vertical play) + racks
    spec["volumes"] = [
        {"name": "crate_stack_tall_1", "x": -8.0, "y": -4.0, "z": 1.5, "size_x": 3.0, "size_y": 3.0, "size_z": 3.0, "collision": "convex", "material": "concrete"},
        {"name": "crate_stack_tall_2", "x": 4.0, "y": 3.0, "z": 1.5, "size_x": 3.0, "size_y": 3.0, "size_z": 3.0, "collision": "convex", "material": "concrete"},
        {"name": "crate_stack_low", "x": -14.0, "y": 6.0, "z": 0.75, "size_x": 2.5, "size_y": 2.5, "size_z": 1.5, "collision": "convex", "material": "concrete"},
        {"name": "rack_row_1", "x": -2.0, "y": -10.0, "z": 1.5, "size_x": 14.0, "size_y": 1.2, "size_z": 3.0, "collision": "convex", "material": "metal"},
        {"name": "rack_row_2", "x": -2.0, "y": 4.0, "z": 1.5, "size_x": 14.0, "size_y": 1.2, "size_z": 3.0, "collision": "convex", "material": "metal"},
        {"name": "forklift_cover", "x": 10.0, "y": -8.0, "z": 0.9, "size_x": 2.5, "size_y": 1.4, "size_z": 1.8, "collision": "convex", "material": "metal"},
    ]
    spec["rooms"] = [
        {"id": "main_floor", "story": 0, "bounds": [-half_x, -half_y, half_x, 8.0], "role": "public_entry", "combat_range": "long"},
        {"id": "north_bay", "story": 0, "bounds": [-half_x, 8.0, 11.0, half_y], "role": "connector", "combat_range": "long"},
        {"id": "office", "story": 0, "bounds": [11.0, 8.0, half_x, half_y], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
    ]
    markers = [
        {"type": "cover_high", "id": "CRATE1", "x": -8.0, "y": -4.0, "z": 0.0, "room": "main_floor"},
        {"type": "cover_high", "id": "CRATE2", "x": 4.0, "y": 3.0, "z": 0.0, "room": "main_floor"},
        {"type": "cover_low", "id": "FORKLIFT", "x": 10.0, "y": -8.0, "z": 0.0, "room": "main_floor"},
        {"type": "camera_socket", "id": "01", "x": -20.0, "y": -14.0, "z": 5.0, "room": "main_floor", "rot_z": 45},
    ]
    if mode == "heist":
        spec["objectives"] = [{"id": "crack_office_safe", "kind": "drill", "x": 15.0, "y": 13.0, "z": 0.2, "room": "office", "required": True, "duration": 30.0}]
        spec["loot"] = [{"id": "warehouse_goods", "kind": "contraband", "x": -2.0, "y": -10.0, "z": 1.0, "value": 5000, "bags": 3, "room": "main_floor"}]
        spec["zones"] = [{"id": "dock_extract", "kind": "extraction", "story": 0, "bounds": [-half_x, -half_y, 0.0, -10.0]}]
        markers += [
            {"type": "objective", "id": "SAFE", "x": 15.0, "y": 13.0, "z": 0.2, "room": "office"},
            {"type": "loot", "id": "GOODS", "x": -2.0, "y": -10.0, "z": 1.0, "room": "main_floor"},
            {"type": "extraction", "id": "DOCK", "x": -10.0, "y": -15.0, "z": 0.0, "room": "main_floor"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": 0.0, "y": -16.0, "z": 0.0, "rot_z": 0, "room": "main_floor"},
            {"type": "attacker_spawn", "id": "B", "x": -22.0, "y": 0.0, "z": 0.0, "rot_z": 90, "room": "main_floor"},
            {"type": "defender_spawn", "id": "D", "x": 18.0, "y": 14.0, "z": 0.0, "rot_z": 225, "room": "office"},
            {"type": "objective", "id": "OFFICE", "x": 16.0, "y": 13.0, "z": 0.0, "room": "office", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # low big-box parapet band
    spec["parapets"] = [{"story": 1, "height": 0.8, "thick": 0.3}]
    return spec


# ---------------------------------------------------------------------------
# SUBURBAN_SAFEHOUSE  --  assault: compact multi-story house, vertical clears
# ---------------------------------------------------------------------------
def suburban_safehouse(name: str = "suburban_safehouse_preset",
                       mode: str = "heist",
                       floors: int = 2,
                       scale_ref: bool = False,
                       basement: bool = True) -> dict:
    """A compact suburban house run as a vertical assault: tight rooms, a
    central stair, an attic objective, and a basement (default on). Close-
    quarters, room-by-room clears with verticality — the small-footprint
    counterpart to the bigger presets. floors fixed at 2 above ground; params
    mode (assault default; heist supported), basement, scale_ref."""
    sh = 3.0
    fx, fy = 18.0, 14.0
    hx, hy = fx / 2, fy / 2
    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 1987, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 2, "has_basement": bool(basement), "wall_thick": 0.25,
        "floor_thick": 0.25, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "wood",
        "materials": [
            {"id": "wood", "acoustic": "Wood", "absorption": 0.35, "damping": 0.3},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
        ],
    }
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "wood", "openings": [
            {"kind": "door", "pos": -0.2, "width": 1.4, "tag": "front_door"},
            {"kind": "window", "pos": 0.25, "width": 1.4, "sill": 0.9, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 0, "material": "wood", "openings": [
            {"kind": "door", "pos": 0.2, "width": 1.2, "tag": "back_door"},
            {"kind": "breach", "pos": -0.25, "width": 1.3, "breach_class": "soft_wall", "material": "drywall"}]},
        {"wall": "W", "story": 0, "material": "wood", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.3, "sill": 0.9, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 0, "material": "wood", "openings": [
            {"kind": "garage", "pos": 0.0, "width": 2.6, "height": 2.2, "tag": "garage"}]},
        {"wall": "S", "story": 1, "material": "wood", "openings": [
            {"kind": "window", "pos": -0.2, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.25, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 1, "material": "wood", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "breach", "pos": 0.3, "width": 1.5, "breach_class": "soft_wall", "material": "drywall"}]},
        {"wall": "W", "story": 1, "material": "wood", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 1, "material": "wood", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"}]},
    ]
    parts = [
        {"story": 0, "axis": "Y", "pos": -1.0, "start": -hy, "end": hy, "material": "drywall", "openings": [{"kind": "door", "pos": -0.3, "width": 1.1}]},
        {"story": 0, "axis": "X", "pos": 2.0, "start": -hx, "end": -1.0, "material": "drywall", "openings": [{"kind": "door", "pos": 0.0, "width": 1.1}]},
        {"story": 1, "axis": "Y", "pos": -1.0, "start": -hy, "end": hy, "material": "drywall", "openings": [{"kind": "door", "pos": 0.3, "width": 1.1}]},
        {"story": 1, "axis": "Y", "pos": 1.0, "start": 1.0, "end": hx, "material": "drywall", "openings": [{"kind": "door", "pos": 0.0, "width": 1.1}]},
    ]
    if basement:
        parts.append({"story": -1, "axis": "Y", "pos": 0.0, "start": -hx, "end": hx, "material": "concrete", "openings": [{"kind": "door", "pos": 0.0, "width": 1.1}]})
    spec["partitions"] = parts
    stair_lo = -1 if basement else 0
    spec["stairs"] = [{"x": 5.0, "y": 4.0, "from_story": stair_lo, "to_story": 1, "width": 1.0, "run": 3.5, "style": "switchback", "cut_slabs": True}]
    spec["vertical_links"] = [{"kind": "stair", "from_story": stair_lo, "to_story": 1, "role": "main_route"}]
    spec["volumes"] = [
        {"name": "living_sofa", "x": -6.0, "y": -4.0, "z": 0.45, "size_x": 2.6, "size_y": 1.0, "size_z": 0.9, "collision": "convex", "material": "wood"},
        {"name": "kitchen_island", "x": -6.0, "y": 4.0, "z": 0.5, "size_x": 2.0, "size_y": 1.2, "size_z": 1.0, "collision": "convex", "material": "wood"},
        {"name": "attic_crates", "x": 5.0, "y": -4.0, "z": sh + 0.5, "size_x": 2.0, "size_y": 2.0, "size_z": 1.0, "collision": "convex", "material": "wood"},
    ]
    rooms = [
        {"id": "living_room", "story": 0, "bounds": [-hx, -hy, -1.0, 2.0], "role": "public_entry", "combat_range": "close"},
        {"id": "kitchen", "story": 0, "bounds": [-hx, 2.0, -1.0, hy], "role": "connector", "combat_range": "close"},
        {"id": "garage_stair", "story": 0, "bounds": [-1.0, -hy, hx, hy], "role": "connector", "combat_range": "close"},
        {"id": "bedroom", "story": 1, "bounds": [-hx, -hy, -1.0, hy], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
        {"id": "attic_room", "story": 1, "bounds": [-1.0, -hy, hx, hy], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
    ]
    if basement:
        rooms.append({"id": "basement", "story": -1, "bounds": [-hx, -hy, hx, hy], "role": "fortifiable", "fortifiable": True, "combat_range": "close"})
    spec["rooms"] = rooms
    markers = [
        {"type": "cover_low", "id": "SOFA", "x": -6.0, "y": -4.0, "z": 0.0, "room": "living_room"},
        {"type": "cover_low", "id": "ISLAND", "x": -6.0, "y": 4.0, "z": 0.0, "room": "kitchen"},
    ]
    if mode == "heist":
        spec["objectives"] = [{"id": "grab_stash", "kind": "bag", "x": 5.0, "y": -4.0, "z": sh + 0.2, "room": "attic_room", "required": True, "duration": 6.0}]
        spec["loot"] = [{"id": "house_stash", "kind": "cash", "x": 5.0, "y": -4.0, "z": sh + 0.2, "value": 4000, "bags": 2, "room": "attic_room"}]
        spec["zones"] = [{"id": "front_extract", "kind": "extraction", "story": 0, "bounds": [-hx, -hy, -1.0, -4.0]}]
        markers += [
            {"type": "objective", "id": "STASH", "x": 5.0, "y": -4.0, "z": sh + 0.2, "room": "attic_room"},
            {"type": "extraction", "id": "FRONT", "x": -5.0, "y": -6.0, "z": 0.0, "room": "living_room"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": -4.0, "y": -8.0, "z": 0.0, "rot_z": 0, "room": "living_room"},
            {"type": "defender_spawn", "id": "D", "x": 5.0, "y": -4.0, "z": sh, "rot_z": 180, "room": "attic_room"},
            {"type": "objective", "id": "ATTIC", "x": 5.0, "y": -4.0, "z": sh, "room": "attic_room", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # combat-audit second vertical link: stories -1<->0 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -7.2, "y": 5.6, "from_story": -1, "to_story": 0,
         "facing": "E", "cut_slabs": True})
    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -7.2, "y": 5.6, "from_story": 0, "to_story": 1,
         "facing": "E", "cut_slabs": True})
    return spec


# ---------------------------------------------------------------------------
# ROWHOME  --  assault: narrow deep multi-floor terrace, stacked clears
# ---------------------------------------------------------------------------
def rowhome(name: str = "rowhome_preset",
            mode: str = "heist",
            floors: int = 3,
            scale_ref: bool = False,
            basement: bool = False) -> dict:
    """A narrow, deep terraced rowhouse: a thin footprint run front-to-back
    over 3 stacked floors, connected by a single rear stair — vertical
    room-by-room clears with very tight angles. Inspired by the rowhouse_raid
    example, generalized to a preset. floors fixed at 3; params mode (assault
    default; heist supported), basement, scale_ref."""
    sh = 3.0
    fx, fy = 8.0, 22.0       # narrow + deep
    hx, hy = fx / 2, fy / 2
    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode,
        # period rowhome: tight interior doors are the point; accepted
        "audit_accept": [{"code": "OBJ_NARROW", "room": "front_2", "why": "period rowhome realism: tight interiors"}], "seed": 1988, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 3, "has_basement": bool(basement), "wall_thick": 0.3,
        "floor_thick": 0.25, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "brick",
        "materials": [
            {"id": "brick", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "wood", "acoustic": "Wood", "absorption": 0.35, "damping": 0.3},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
        ],
    }
    # only front (S) and back (N) walls have openings; sides are party walls
    ext = []
    for st in range(0, 3):
        ext.append({"wall": "S", "story": st, "material": "brick", "openings": (
            [{"kind": "door", "pos": 0.0, "width": 1.4, "tag": "front_door"}] if st == 0
            else [{"kind": "window", "pos": -0.2, "width": 1.1, "sill": 1.0, "vaultable": True, "material": "glass"},
                  {"kind": "window", "pos": 0.2, "width": 1.1, "sill": 1.0, "vaultable": True, "material": "glass"}])})
        ext.append({"wall": "N", "story": st, "material": "brick", "openings": (
            [{"kind": "door", "pos": 0.0, "width": 1.2, "tag": "back_door"}] if st == 0
            else [{"kind": "window", "pos": 0.0, "width": 1.1, "sill": 1.0, "vaultable": True, "material": "glass"},
                  {"kind": "breach", "pos": 0.3, "width": 1.0, "breach_class": "soft_wall", "material": "drywall"}])})
        # party walls (W/E) solid — no openings
        ext.append({"wall": "W", "story": st, "material": "brick", "openings": []})
        ext.append({"wall": "E", "story": st, "material": "brick", "openings": []})
    spec["ext_walls"] = ext
    # one cross-partition per floor splitting front/back room
    parts = []
    for st in range(0, 3):
        parts.append({"story": st, "axis": "X", "pos": 0.0, "start": -hx, "end": hy - 5.0, "material": "drywall", "openings": [{"kind": "door", "pos": -0.2, "width": 1.1}]})
    spec["partitions"] = parts
    # single rear stair spanning all floors
    stair_lo = -1 if basement else 0
    spec["stairs"] = [{"x": 0.0, "y": hy - 2.5, "from_story": stair_lo, "to_story": 2, "width": 0.9, "run": 3.0, "style": "switchback", "cut_slabs": True}]
    spec["vertical_links"] = [{"kind": "stair", "from_story": stair_lo, "to_story": 2, "role": "main_route"}]
    spec["volumes"] = [
        {"name": "front_sofa", "x": 0.0, "y": -7.0, "z": 0.45, "size_x": 2.2, "size_y": 0.9, "size_z": 0.9, "collision": "convex", "material": "wood"},
        {"name": "bed_2f", "x": 0.0, "y": -7.0, "z": sh + 0.3, "size_x": 2.0, "size_y": 1.2, "size_z": 0.6, "collision": "convex", "material": "wood"},
        {"name": "desk_3f", "x": 0.0, "y": -7.0, "z": 2 * sh + 0.4, "size_x": 1.8, "size_y": 0.9, "size_z": 0.8, "collision": "convex", "material": "wood"},
    ]
    rooms = []
    role_by_floor = {0: "public_entry", 1: "connector", 2: "objective_room"}
    for st in range(0, 3):
        rooms.append({"id": f"front_{st}", "story": st, "bounds": [-hx, -hy, hx, 0.0],
                      "role": role_by_floor[st], "combat_range": "close",
                      **({"objective": True, "fortifiable": True} if st == 2 else {})})
        rooms.append({"id": f"back_{st}", "story": st, "bounds": [-hx, 0.0, hx, hy], "role": "connector", "combat_range": "close"})
    spec["rooms"] = rooms
    markers = [{"type": "cover_low", "id": "SOFA", "x": 0.0, "y": -7.0, "z": 0.0, "room": "front_0"}]
    if mode == "heist":
        spec["objectives"] = [{"id": "grab_top", "kind": "bag", "x": 0.0, "y": -7.0, "z": 2 * sh + 0.4, "room": "front_2", "required": True, "duration": 6.0}]
        spec["loot"] = [{"id": "top_floor_stash", "kind": "cash", "x": 0.0, "y": -7.0, "z": 2 * sh + 0.4, "value": 3500, "bags": 2, "room": "front_2"}]
        spec["zones"] = [{"id": "front_extract", "kind": "extraction", "story": 0, "bounds": [-hx, -hy, hx, -7.0]}]
        markers += [
            {"type": "objective", "id": "TOP", "x": 0.0, "y": -7.0, "z": 2 * sh + 0.4, "room": "front_2"},
            {"type": "extraction", "id": "FRONT", "x": 0.0, "y": -9.0, "z": 0.0, "room": "front_0"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": 0.0, "y": -10.0, "z": 0.0, "rot_z": 0, "room": "front_0"},
            {"type": "attacker_spawn", "id": "B", "x": 0.0, "y": 10.0, "z": 0.0, "rot_z": 180, "room": "back_0"},
            {"type": "defender_spawn", "id": "D", "x": 0.0, "y": -7.0, "z": 2 * sh, "rot_z": 180, "room": "front_2"},
            {"type": "objective", "id": "TOPFLOOR", "x": 0.0, "y": -7.0, "z": 2 * sh, "room": "front_2", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -3.0, "y": 1.0, "from_story": 0, "to_story": 1,
         "facing": "N", "cut_slabs": True})
    # combat-audit second vertical link: stories 1<->2 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -3.0, "y": 1.0, "from_story": 1, "to_story": 2,
         "facing": "N", "cut_slabs": True})
    # flat Philly roof: low front parapet/cornice line, matching
    # facade_rowhome (0.7) so mixed blocks read as one street
    spec["parapets"] = [{"story": 3, "height": 0.7, "thick": 0.3}]
    return spec


# ---------------------------------------------------------------------------
# CASINO_TOWER  --  hybrid heist/assault: public floor + secure vault levels
# ---------------------------------------------------------------------------
def casino_tower(name: str = "casino_tower_preset",
                 mode: str = "heist",
                 floors: int = 3,
                 scale_ref: bool = False,
                 basement: bool = True) -> dict:
    """A casino: a glamorous open gaming floor on the ground, a cashier cage +
    count room upstairs, and a basement vault — a hybrid that plays as a heist
    (default: cage + vault objectives, loot, extraction) or an assault (secure
    the vault). Wide public ground floor, tightening to high-security upper and
    basement. floors fixed at 2 above ground; params mode (heist default;
    assault supported), basement (default on — it holds the vault), scale_ref."""
    sh = 4.0                 # tall glamorous floors
    fx, fy = 44.0, 32.0
    hx, hy = fx / 2, fy / 2
    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode,
        # one-breach vault is the designed climax; the combat audit reports it as accepted
        "audit_accept": [{"code": "OBJ_ONE_DOOR", "room": "vault", "why": "designed climax: one breach wall"}], "seed": 1989, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 2, "has_basement": bool(basement), "wall_thick": 0.35,
        "floor_thick": 0.3, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "concrete",
        "materials": [
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "metal", "acoustic": "Metal", "absorption": 0.3, "damping": 0.2},
            {"id": "carpet", "acoustic": "Curtain", "absorption": 0.8, "damping": 0.7},
        ],
    }
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.1, "width": 2.4, "tag": "grand_entrance"},
            {"kind": "window", "pos": -0.35, "width": 3.0, "sill": 0.8, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.3, "width": 3.0, "sill": 0.8, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.2, "width": 1.2, "tag": "staff_entrance"},
            {"kind": "breach", "pos": 0.25, "width": 1.5, "breach_class": "soft_wall", "material": "drywall", "tag": "back_breach"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "valet_entrance"}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "garage", "pos": 0.0, "width": 3.2, "height": 2.6, "tag": "armored_car_bay"}]},
        {"wall": "S", "story": 1, "material": "glass", "openings": [
            {"kind": "window", "pos": -0.25, "width": 2.0, "sill": 0.9, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.25, "width": 2.0, "sill": 0.9, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 1, "material": "concrete", "openings": [
            {"kind": "breach", "pos": 0.0, "width": 1.4, "breach_class": "reinforceable", "material": "concrete", "reinforceable": True, "tag": "count_room_breach"}]},
        {"wall": "W", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.6, "sill": 0.9, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.6, "sill": 0.9, "vaultable": True, "material": "glass"}]},
    ]
    parts = [
        {"story": 0, "axis": "X", "pos": 8.0, "start": -hx, "end": hx, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.3, "width": 1.4}, {"kind": "door", "pos": 0.3, "width": 1.4}]},
        {"story": 0, "axis": "Y", "pos": 10.0, "start": 8.0, "end": hx, "material": "metal", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.1, "tag": "cage_door"}]},
        {"story": 1, "axis": "X", "pos": 0.0, "start": -hx, "end": hx, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.25, "width": 1.2}, {"kind": "door", "pos": 0.25, "width": 1.2}]},
        {"story": 1, "axis": "Y", "pos": 0.0, "start": 0.0, "end": hx, "material": "metal", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.4, "tag": "count_room_door"}]},
    ]
    if basement:
        parts.append({"story": -1, "axis": "Y", "pos": 0.0, "start": -hx, "end": hx, "material": "concrete", "openings": [
            {"kind": "breach", "pos": 0.0, "width": 1.4, "breach_class": "reinforceable", "material": "concrete", "reinforceable": True, "tag": "vault_breach"}]})
    spec["partitions"] = parts
    stair_lo = -1 if basement else 0
    spec["stairs"] = [{"x": -16.0, "y": 12.0, "from_story": stair_lo, "to_story": 1, "width": 1.4, "run": 4.5, "style": "switchback", "cut_slabs": True}]
    spec["vertical_links"] = [
        {"kind": "stair", "from_story": stair_lo, "to_story": 1, "role": "main_route"},
        {"kind": "hatch", "story": 1, "x": 14.0, "y": 8.0, "size_x": 1.4, "size_y": 1.4, "breachable": True, "cut_slab": True, "role": "count_room_skylight"},
    ]
    spec["slab_holes"] = [{"story": 1, "x": 14.0, "y": 8.0, "size_x": 1.4, "size_y": 1.4}]
    spec["parapets"] = [{"story": 2, "height": 1.0, "thick": 0.3}]
    vols = [
        {"name": "gaming_tables", "x": -6.0, "y": -4.0, "z": 0.5, "size_x": 12.0, "size_y": 6.0, "size_z": 1.0, "collision": "convex", "material": "carpet"},
        {"name": "slot_bank_1", "x": 12.0, "y": -8.0, "z": 0.9, "size_x": 6.0, "size_y": 1.2, "size_z": 1.8, "collision": "convex", "material": "metal"},
        {"name": "bar_cover", "x": -16.0, "y": -6.0, "z": 0.6, "size_x": 1.2, "size_y": 8.0, "size_z": 1.2, "collision": "convex", "material": "metal"},
        {"name": "cage_counter", "x": 16.0, "y": 12.0, "z": 0.55, "size_x": 6.0, "size_y": 1.0, "size_z": 1.1, "collision": "convex", "material": "metal"},
        {"name": "count_table", "x": 12.0, "y": 10.0, "z": sh + 0.45, "size_x": 4.0, "size_y": 2.0, "size_z": 0.9, "collision": "convex", "material": "metal"},
    ]
    if basement:
        vols.append({"name": "vault_block", "x": 0.0, "y": 6.0, "z": -sh + 0.7, "size_x": 8.0, "size_y": 6.0, "size_z": 1.4, "collision": "convex", "material": "metal"})
    spec["volumes"] = vols
    rooms = [
        {"id": "gaming_floor", "story": 0, "bounds": [-hx, -hy, hx, 8.0], "role": "public_entry", "combat_range": "long"},
        {"id": "north_concourse", "story": 0, "bounds": [-hx, 8.0, 10.0, hy], "role": "connector", "combat_range": "medium"},
        {"id": "cashier_cage", "story": 0, "bounds": [10.0, 8.0, hx, hy], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
        {"id": "upper_lounge", "story": 1, "bounds": [-hx, -hy, hx, 0.0], "role": "connector", "combat_range": "medium"},
        {"id": "security_office", "story": 1, "bounds": [-hx, 0.0, 0.0, hy], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
        {"id": "count_room", "story": 1, "bounds": [0.0, 0.0, hx, hy], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
    ]
    if basement:
        rooms.append({"id": "vault", "story": -1, "bounds": [-hx, -hy, hx, hy], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"})
    spec["rooms"] = rooms
    markers = [
        {"type": "cover_high", "id": "TABLES", "x": -6.0, "y": -4.0, "z": 0.0, "room": "gaming_floor"},
        {"type": "cover_high", "id": "SLOTS", "x": 12.0, "y": -8.0, "z": 0.0, "room": "gaming_floor"},
        {"type": "camera_socket", "id": "01", "x": 0.0, "y": -14.0, "z": 3.5, "room": "gaming_floor"},
        {"type": "camera_socket", "id": "02", "x": 16.0, "y": 14.0, "z": 3.5, "room": "cashier_cage"},
    ]
    if mode == "heist":
        objs = [
            {"id": "rob_cage", "kind": "bag_cash", "x": 16.0, "y": 12.0, "z": 0.9, "room": "cashier_cage", "required": True, "duration": 10.0, "meta": {"phase": "loud"}},
            {"id": "hack_count_room", "kind": "hack", "x": 12.0, "y": 10.0, "z": sh + 0.9, "room": "count_room", "required": False, "duration": 20.0},
        ]
        loot = [{"id": "cage_cash", "kind": "cash", "x": 16.0, "y": 12.0, "z": 0.9, "value": 6000, "bags": 2, "room": "cashier_cage"}]
        if basement:
            objs.append({"id": "drill_vault", "kind": "drill", "x": 0.0, "y": 6.0, "z": -sh + 1.0, "room": "vault", "required": True, "duration": 50.0, "meta": {"phase": "loud", "noise_radius": 30}})
            loot.append({"id": "vault_cash", "kind": "cash", "x": 0.0, "y": 6.0, "z": -sh + 1.2, "value": 20000, "bags": 4, "room": "vault"})
        spec["objectives"] = objs
        spec["loot"] = loot
        spec["zones"] = [
            {"id": "valet_extract", "kind": "extraction", "story": 0, "bounds": [-hx, -hy, -14.0, 0.0], "meta": {"phase": "escape"}},
            {"id": "cage_secure", "kind": "secure", "story": 0, "bounds": [10.0, 8.0, hx, hy]},
        ]
        markers += [
            {"type": "objective", "id": "CAGE", "x": 16.0, "y": 12.0, "z": 0.9, "room": "cashier_cage"},
            {"type": "objective", "id": "COUNT", "x": 12.0, "y": 10.0, "z": sh + 0.9, "room": "count_room"},
            {"type": "extraction", "id": "VALET", "x": -18.0, "y": -6.0, "z": 0.0, "room": "gaming_floor"}]
        if basement:
            markers += [
                {"type": "objective", "id": "VAULT", "x": 0.0, "y": 6.0, "z": -sh + 1.0, "room": "vault"},
                {"type": "loot", "id": "VAULT_CASH", "x": 0.0, "y": 6.0, "z": -sh + 1.2, "room": "vault"}]
    else:  # assault — secure the vault (or count room w/o basement)
        target_room = "vault" if basement else "count_room"
        tz = (-sh + 1.0) if basement else (sh)
        ty = 6.0 if basement else 10.0
        tx = 0.0 if basement else 12.0
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": 0.0, "y": -14.0, "z": 0.0, "rot_z": 0, "room": "gaming_floor"},
            {"type": "attacker_spawn", "id": "B", "x": -20.0, "y": 0.0, "z": 0.0, "rot_z": 90, "room": "gaming_floor"},
            {"type": "defender_spawn", "id": "D", "x": tx, "y": ty, "z": tz, "rot_z": 180, "room": target_room},
            {"type": "objective", "id": "SECURE", "x": tx, "y": ty, "z": tz, "room": target_room, "meta": {"kind": "secure"}}]
    spec["markers"] = markers
    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -21.0, "y": 9.0, "from_story": 0, "to_story": 1,
         "facing": "E", "cut_slabs": True})
    # the vault basement's single approach is the designed climax
    spec.setdefault("audit_accept", []).append(
        {"code": "VERT_DEAD_END",
         "why": "vault basement: single approach is the designed climax"})
    return spec


# ---------------------------------------------------------------------------
# GAS_STATION  --  heist: convenience store + pump forecourt (walked layout)
# ---------------------------------------------------------------------------
def gas_station(name: str = "gas_station_preset",
                mode: str = "heist",
                floors: int = 1,
                scale_ref: bool = False,
                basement: bool = False) -> dict:
    """A highway gas station / convenience store: a glass-front sales floor with
    market aisles and a coffee island, a back stockroom, and a manager office
    holding the safe (the objective), all fronted by a pump forecourt under a
    lit canopy. Modeled on the walked fuel_stop layout. `floors`/`basement` are
    accepted for CLI uniformity but the building is one tall story. Heist mode
    arms the register + office safe; assault mode makes the office the holdable
    point. NOTE: the canopy columns and pumps are emitted as repeated VOLUMES
    for a clean greybox — per docs/AUTHORING.md they're the textbook case for
    promoting to a single placed asset (`placements`) at art-pass time."""
    fx, fy = 32.0, 22.0
    sh = 4.2
    half_x, half_y = fx / 2, fy / 2

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 1999, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 1, "has_basement": False, "wall_thick": 0.3,
        "floor_thick": 0.3, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "concrete",
        "materials": _mats("concrete", "drywall", "glass", "metal", "wood"),
    }
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.16, "width": 1.8, "tag": "front_entry_west"},
            {"kind": "door", "pos": 0.16, "width": 1.8, "tag": "front_entry_east"},
            {"kind": "window", "pos": -0.4, "width": 3.0, "height": 2.4, "sill": 1.0, "material": "glass"},
            {"kind": "window", "pos": 0.4, "width": 3.0, "height": 2.4, "sill": 1.0, "material": "glass"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "garage", "pos": 0.28, "width": 3.0, "height": 3.0, "tag": "stock_roll_door"},
            {"kind": "door", "pos": 0.46, "width": 1.2, "tag": "office_back_door"},
            {"kind": "breach", "pos": -0.3, "width": 1.6, "breach_class": "soft_wall", "material": "drywall", "tag": "north_breach"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.1, "width": 1.1, "tag": "west_service"},
            {"kind": "window", "pos": 0.3, "width": 1.6, "sill": 1.2, "vaultable": True}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.2, "width": 1.1, "tag": "east_stock_service"}]},
    ]
    spec["partitions"] = [
        {"story": 0, "axis": "Y", "pos": 6.0, "start": -half_y, "end": half_y, "material": "drywall", "openings": [
            {"kind": "door", "pos": -0.3, "width": 1.4, "tag": "sales_to_stock"},
            {"kind": "door", "pos": 0.3, "width": 1.1, "tag": "sales_to_office"}]},
        {"story": 0, "axis": "X", "pos": 2.0, "start": 6.0, "end": half_x, "material": "drywall", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "stock_to_office"}]},
    ]
    spec["stairs"] = []
    spec["vault_ledges"] = [
        {"x": -12.0, "y": -7.0, "story": 0, "length": 6.0, "axis": "X", "height": 1.1, "material": "wood"},
    ]
    spec["volumes"] = [
        {"name": "register_counter", "x": -12.0, "y": -7.0, "z": 0.55, "size_x": 6.0, "size_y": 0.9, "size_z": 1.1, "collision": "convex", "material": "wood"},
        {"name": "aisle_1", "x": -8.0, "y": 0.0, "z": 0.9, "size_x": 0.9, "size_y": 10.0, "size_z": 1.8, "collision": "convex", "material": "metal"},
        {"name": "aisle_2", "x": -3.0, "y": 0.0, "z": 0.9, "size_x": 0.9, "size_y": 10.0, "size_z": 1.8, "collision": "convex", "material": "metal"},
        {"name": "coffee_island", "x": 2.0, "y": -7.0, "z": 0.55, "size_x": 3.0, "size_y": 2.0, "size_z": 1.1, "collision": "convex", "material": "metal"},
        {"name": "cooler_run", "x": 4.5, "y": 6.0, "z": 1.1, "size_x": 2.8, "size_y": 8.0, "size_z": 2.2, "collision": "convex", "material": "glass"},
        {"name": "stock_rack_1", "x": 11.0, "y": -6.0, "z": 1.25, "size_x": 6.0, "size_y": 0.9, "size_z": 2.5, "collision": "convex", "material": "metal"},
        {"name": "stock_rack_2", "x": 11.0, "y": -2.5, "z": 1.25, "size_x": 6.0, "size_y": 0.9, "size_z": 2.5, "collision": "convex", "material": "metal"},
        {"name": "manager_desk", "x": 12.0, "y": 7.0, "z": 0.4, "size_x": 2.0, "size_y": 1.0, "size_z": 0.8, "collision": "convex", "material": "wood"},
        {"name": "office_safe", "x": 14.5, "y": 9.0, "z": 0.5, "size_x": 0.9, "size_y": 0.9, "size_z": 1.0, "collision": "convex", "material": "metal"},
        {"name": "forecourt_pad", "x": 0.0, "y": -18.0, "z": 0.05, "size_x": 28.0, "size_y": 12.0, "size_z": 0.1, "collision": "trimesh", "material": "concrete"},
        {"name": "canopy_roof", "x": 0.0, "y": -18.0, "z": 5.0, "size_x": 24.0, "size_y": 10.0, "size_z": 0.4, "collision": "convex", "material": "metal"},
        {"name": "canopy_col_1", "x": -10.0, "y": -14.0, "z": 2.5, "size_x": 0.4, "size_y": 0.4, "size_z": 5.0, "collision": "convex", "material": "metal"},
        {"name": "canopy_col_2", "x": 0.0, "y": -14.0, "z": 2.5, "size_x": 0.4, "size_y": 0.4, "size_z": 5.0, "collision": "convex", "material": "metal"},
        {"name": "canopy_col_3", "x": 10.0, "y": -14.0, "z": 2.5, "size_x": 0.4, "size_y": 0.4, "size_z": 5.0, "collision": "convex", "material": "metal"},
        {"name": "canopy_col_4", "x": -10.0, "y": -22.0, "z": 2.5, "size_x": 0.4, "size_y": 0.4, "size_z": 5.0, "collision": "convex", "material": "metal"},
        {"name": "canopy_col_5", "x": 0.0, "y": -22.0, "z": 2.5, "size_x": 0.4, "size_y": 0.4, "size_z": 5.0, "collision": "convex", "material": "metal"},
        {"name": "canopy_col_6", "x": 10.0, "y": -22.0, "z": 2.5, "size_x": 0.4, "size_y": 0.4, "size_z": 5.0, "collision": "convex", "material": "metal"},
        {"name": "pump_island_1", "x": -8.0, "y": -18.0, "z": 0.15, "size_x": 1.6, "size_y": 6.0, "size_z": 0.3, "collision": "convex", "material": "concrete"},
        {"name": "pump_island_2", "x": 0.0, "y": -18.0, "z": 0.15, "size_x": 1.6, "size_y": 6.0, "size_z": 0.3, "collision": "convex", "material": "concrete"},
        {"name": "pump_island_3", "x": 8.0, "y": -18.0, "z": 0.15, "size_x": 1.6, "size_y": 6.0, "size_z": 0.3, "collision": "convex", "material": "concrete"},
        {"name": "pump_1", "x": -8.0, "y": -20.0, "z": 0.7, "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex", "material": "metal"},
        {"name": "pump_2", "x": -8.0, "y": -16.0, "z": 0.7, "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex", "material": "metal"},
        {"name": "pump_3", "x": 0.0, "y": -20.0, "z": 0.7, "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex", "material": "metal"},
        {"name": "pump_4", "x": 0.0, "y": -16.0, "z": 0.7, "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex", "material": "metal"},
        {"name": "pump_5", "x": 8.0, "y": -20.0, "z": 0.7, "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex", "material": "metal"},
        {"name": "pump_6", "x": 8.0, "y": -16.0, "z": 0.7, "size_x": 1.0, "size_y": 1.2, "size_z": 1.4, "collision": "convex", "material": "metal"},
    ]
    spec["rooms"] = [
        {"id": "forecourt", "story": 0, "bounds": [-14.0, -24.0, 14.0, -half_y], "role": "staging", "combat_range": "medium"},
        {"id": "sales_floor", "story": 0, "bounds": [-half_x, -half_y, 6.0, half_y], "role": "public_entry", "combat_range": "long"},
        {"id": "stockroom", "story": 0, "bounds": [6.0, -half_y, half_x, 2.0], "role": "connector", "combat_range": "close"},
        {"id": "back_office", "story": 0, "bounds": [6.0, 2.0, half_x, half_y], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
    ]
    markers = [
        {"type": "cover_low", "id": "REG", "x": -12.0, "y": -7.0, "z": 0.0, "room": "sales_floor"},
        {"type": "cover_high", "id": "AISLE1", "x": -8.0, "y": 0.0, "z": 0.0, "room": "sales_floor"},
        {"type": "cover_high", "id": "AISLE2", "x": -3.0, "y": 0.0, "z": 0.0, "room": "sales_floor"},
        {"type": "cover_high", "id": "RACK1", "x": 11.0, "y": -6.0, "z": 0.0, "room": "stockroom"},
        {"type": "camera_socket", "id": "01", "x": -15.0, "y": 10.0, "z": 3.5, "room": "sales_floor", "rot_z": -45},
    ]
    if mode == "heist":
        spec["objectives"] = [
            {"id": "register_grab", "kind": "bag_cash", "x": -12.0, "y": -7.0, "z": 0.9, "room": "sales_floor", "required": True, "duration": 8.0},
            {"id": "office_safe", "kind": "drill", "x": 14.5, "y": 9.0, "z": 0.5, "room": "back_office", "required": True, "duration": 30.0},
        ]
        spec["loot"] = [
            {"id": "register_cash", "kind": "cash", "x": -12.0, "y": -7.0, "z": 0.9, "value": 2500, "bags": 1, "room": "sales_floor"},
            {"id": "safe_cash", "kind": "cash", "x": 14.5, "y": 9.0, "z": 0.6, "value": 8000, "bags": 2, "room": "back_office"},
            {"id": "stock_contraband", "kind": "contraband", "x": 11.0, "y": -2.5, "z": 1.0, "value": 3000, "bags": 1, "room": "stockroom"},
        ]
        spec["zones"] = [{"id": "forecourt_extract", "kind": "extraction", "story": 0, "bounds": [-12.0, -24.0, 12.0, -14.0]}]
        markers += [
            {"type": "objective", "id": "REGISTER", "x": -12.0, "y": -7.0, "z": 0.9, "room": "sales_floor"},
            {"type": "objective", "id": "SAFE", "x": 14.5, "y": 9.0, "z": 0.5, "room": "back_office"},
            {"type": "loot", "id": "SAFECASH", "x": 14.5, "y": 9.0, "z": 0.6, "room": "back_office"},
            {"type": "extraction", "id": "FORECOURT", "x": 0.0, "y": -20.0, "z": 0.0, "room": "sales_floor"},
            {"type": "attacker_spawn", "id": "A", "x": -8.0, "y": -22.0, "z": 0.0, "rot_z": 0, "room": "sales_floor"},
            {"type": "attacker_spawn", "id": "B", "x": 8.0, "y": -22.0, "z": 0.0, "rot_z": 0, "room": "sales_floor"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": -8.0, "y": -22.0, "z": 0.0, "rot_z": 0, "room": "sales_floor"},
            {"type": "attacker_spawn", "id": "B", "x": 8.0, "y": -22.0, "z": 0.0, "rot_z": 0, "room": "sales_floor"},
            {"type": "defender_spawn", "id": "D", "x": 12.0, "y": 8.0, "z": 0.0, "rot_z": 200, "room": "back_office"},
            {"type": "objective", "id": "OFFICE", "x": 12.0, "y": 7.0, "z": 0.0, "room": "back_office", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    return spec


# ---------------------------------------------------------------------------
# OFFICE  --  assault/heist: multi-story corporate tower, central core
# ---------------------------------------------------------------------------
def office(name: str = "office_preset",
           mode: str = "heist",
           floors: int = 3,
           basement: bool = False,
           scale_ref: bool = False) -> dict:
    """A corporate office tower: a glass-curtain-wall block with a ground-floor
    lobby, a central stair/elevator core serving every floor, open bullpen
    floors with cubicle cover, and an executive suite on the top floor (assault:
    the holdable point; heist: an exec safe + server room). `floors` sets
    above-ground stories (default 3); `basement` adds a records/parking level on
    the core. Distinct from the bank: repeating floors reached by an internal
    core, objective up top rather than a basement vault."""
    floors = max(1, int(floors))
    fx, fy = 34.0, 24.0
    sh = 3.6
    half_x, half_y = fx / 2, fy / 2
    top = floors - 1

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 2001, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": floors, "has_basement": bool(basement), "wall_thick": 0.3,
        "floor_thick": 0.3, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "concrete",
        "materials": _mats("concrete", "drywall", "glass", "metal", "wood"),
    }

    ext = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.1, "width": 2.0, "tag": "lobby_main_west"},
            {"kind": "door", "pos": 0.1, "width": 2.0, "tag": "lobby_main_east"},
            {"kind": "window", "pos": -0.38, "width": 4.0, "height": 2.6, "sill": 0.4, "material": "glass"},
            {"kind": "window", "pos": 0.38, "width": 4.0, "height": 2.6, "sill": 0.4, "material": "glass"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.35, "width": 1.2, "tag": "service_north"},
            {"kind": "breach", "pos": 0.3, "width": 1.6, "breach_class": "soft_wall", "material": "drywall", "tag": "north_breach"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.2, "tag": "west_service"}]},
        {"wall": "E", "story": 0, "material": "glass", "openings": [
            {"kind": "window", "pos": 0.0, "width": 3.0, "height": 2.6, "sill": 0.4, "material": "glass", "vaultable": True}]},
    ]
    for st in range(1, floors):
        ext.append({"wall": "S", "story": st, "material": "glass", "openings": [
            {"kind": "window", "pos": -0.25, "width": 5.0, "height": 2.4, "sill": 0.6, "material": "glass", "vaultable": True},
            {"kind": "window", "pos": 0.25, "width": 5.0, "height": 2.4, "sill": 0.6, "material": "glass", "vaultable": True}]})
        ext.append({"wall": "N", "story": st, "material": "glass", "openings": [
            {"kind": "window", "pos": 0.0, "width": 5.0, "height": 2.4, "sill": 0.6, "material": "glass"}]})
    spec["ext_walls"] = ext

    # central core: short Y walls at x=+/-3 (the corridor runs N-S through it),
    # with a door each side, on every story.
    parts = []
    lo = -1 if basement else 0
    for st in range(lo, floors):
        parts.append({"story": st, "axis": "Y", "pos": -3.0, "start": -4.0, "end": 4.0, "material": "drywall",
                      "openings": [{"kind": "door", "pos": 0.0, "width": 1.4, "tag": f"core_w_{st}"}]})
        parts.append({"story": st, "axis": "Y", "pos": 3.0, "start": -4.0, "end": 4.0, "material": "drywall",
                      "openings": [{"kind": "door", "pos": 0.0, "width": 1.4, "tag": f"core_e_{st}"}]})
    # top-floor exec suite, NE corner, two doors for >=2 access
    parts.append({"story": top, "axis": "Y", "pos": 8.0, "start": 4.0, "end": half_y, "material": "drywall",
                  "openings": [{"kind": "door", "pos": 0.0, "width": 1.1, "tag": "exec_w"}]})
    parts.append({"story": top, "axis": "X", "pos": 4.0, "start": 8.0, "end": half_x, "material": "drywall",
                  "openings": [{"kind": "door", "pos": 0.0, "width": 1.4, "tag": "exec_s"}]})
    spec["partitions"] = parts

    hi = floors - 1
    if hi > lo:
        spec["stairs"] = [{"x": 0.0, "y": 0.0, "from_story": lo, "to_story": hi, "style": "switchback", "cut_slabs": True}]
    else:
        spec["stairs"] = []
    spec["vault_ledges"] = [
        {"x": 0.0, "y": -8.0, "story": 0, "length": 5.0, "axis": "X", "height": 1.1, "material": "wood"},
    ]

    vols = [
        {"name": "elevator_block", "x": 0.0, "y": 0.0, "z": 1.5, "size_x": 2.0, "size_y": 2.0, "size_z": 3.0, "collision": "convex", "material": "metal"},
        {"name": "reception_desk", "x": 0.0, "y": -8.0, "z": 0.5, "size_x": 5.0, "size_y": 1.2, "size_z": 1.0, "collision": "convex", "material": "wood"},
    ]
    for st in range(floors):
        zb = st * sh
        vols.append({"name": f"cubicles_w_{st}", "x": -10.0, "y": 6.0, "z": zb + 0.6, "size_x": 8.0, "size_y": 6.0, "size_z": 1.2, "collision": "convex", "material": "drywall"})
        vols.append({"name": f"cubicles_e_{st}", "x": 10.0, "y": -6.0, "z": zb + 0.6, "size_x": 8.0, "size_y": 6.0, "size_z": 1.2, "collision": "convex", "material": "drywall"})
    # top-floor exec extras
    vols.append({"name": "exec_desk", "x": 12.0, "y": 8.0, "z": top * sh + 0.4, "size_x": 2.4, "size_y": 1.1, "size_z": 0.8, "collision": "convex", "material": "wood"})
    vols.append({"name": "exec_safe", "x": 15.0, "y": 10.0, "z": top * sh + 0.5, "size_x": 0.9, "size_y": 0.9, "size_z": 1.0, "collision": "convex", "material": "metal"})
    spec["volumes"] = vols

    rooms = [
        {"id": "lobby", "story": 0, "bounds": [-half_x, -half_y, half_x, 0.0], "role": "public_entry", "combat_range": "long"},
        {"id": "ground_bullpen", "story": 0, "bounds": [-half_x, 0.0, half_x, half_y], "role": "connector", "combat_range": "long"},
    ]
    for st in range(1, top):
        rooms.append({"id": f"floor_{st}", "story": st, "bounds": [-half_x, -half_y, half_x, half_y], "role": "connector", "combat_range": "long"})
    if top >= 1:
        rooms.append({"id": "exec_lobby", "story": top, "bounds": [-half_x, -half_y, 8.0, half_y], "role": "connector", "combat_range": "long"})
        rooms.append({"id": "exec_anteroom", "story": top, "bounds": [8.0, -half_y, half_x, 4.0], "role": "connector", "combat_range": "close"})
        rooms.append({"id": "exec_suite", "story": top, "bounds": [8.0, 4.0, half_x, half_y], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"})
    else:
        # single-floor office: exec suite carved on the ground NE
        rooms.append({"id": "exec_suite", "story": 0, "bounds": [8.0, 4.0, half_x, half_y], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"})

    spec["rooms"] = rooms

    obj_story = top
    markers = [
        {"type": "cover_high", "id": "CUBE_W0", "x": -10.0, "y": 6.0, "z": 0.0, "room": "ground_bullpen"},
        {"type": "cover_high", "id": "CUBE_E0", "x": 10.0, "y": -6.0, "z": 0.0, "room": "lobby"},
        {"type": "cover_low", "id": "RECEPTION", "x": 0.0, "y": -8.0, "z": 0.0, "room": "lobby"},
        {"type": "camera_socket", "id": "01", "x": -15.0, "y": -10.0, "z": 3.0, "room": "lobby", "rot_z": -45},
    ]
    exec_room = "exec_suite"
    if mode == "heist":
        spec["objectives"] = [
            {"id": "exec_safe", "kind": "drill", "x": 15.0, "y": 10.0, "z": obj_story * sh + 0.5, "room": exec_room, "required": True, "duration": 30.0},
            {"id": "server_pull", "kind": "hack", "x": 12.0, "y": 8.0, "z": obj_story * sh + 0.2, "room": exec_room, "required": False, "duration": 20.0},
        ]
        spec["loot"] = [
            {"id": "exec_cash", "kind": "cash", "x": 15.0, "y": 10.0, "z": obj_story * sh + 0.6, "value": 12000, "bags": 2, "room": exec_room},
        ]
        spec["zones"] = [{"id": "lobby_extract", "kind": "extraction", "story": 0, "bounds": [-half_x, -half_y, half_x, -8.0]}]
        markers += [
            {"type": "objective", "id": "SAFE", "x": 15.0, "y": 10.0, "z": obj_story * sh + 0.5, "room": exec_room},
            {"type": "loot", "id": "EXECCASH", "x": 15.0, "y": 10.0, "z": obj_story * sh + 0.6, "room": exec_room},
            {"type": "extraction", "id": "LOBBY", "x": 0.0, "y": -10.0, "z": 0.0, "room": "lobby"},
            {"type": "attacker_spawn", "id": "A", "x": -4.0, "y": -10.0, "z": 0.0, "rot_z": 0, "room": "lobby"},
            {"type": "attacker_spawn", "id": "B", "x": 4.0, "y": -10.0, "z": 0.0, "rot_z": 0, "room": "lobby"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": -4.0, "y": -10.0, "z": 0.0, "rot_z": 0, "room": "lobby"},
            {"type": "attacker_spawn", "id": "B", "x": 4.0, "y": -10.0, "z": 0.0, "rot_z": 0, "room": "lobby"},
            {"type": "defender_spawn", "id": "D", "x": 13.0, "y": 9.0, "z": obj_story * sh, "rot_z": 200, "room": exec_room},
            {"type": "objective", "id": "EXEC", "x": 12.0, "y": 8.0, "z": obj_story * sh, "room": exec_room, "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -16.0, "y": -11.0, "from_story": 0, "to_story": 1,
         "facing": "E", "cut_slabs": True})
    # combat-audit second vertical link: stories 1<->2 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -16.0, "y": -11.0, "from_story": 1, "to_story": 2,
         "facing": "E", "cut_slabs": True})
    # standard commercial parapet band for the skyline
    spec["parapets"] = [{"story": 3, "height": 1.1, "thick": 0.3}]
    return spec


# ---------------------------------------------------------------------------
# PARKING_GARAGE  --  assault: enclosed multi-level deck, ramp + column grid
# ---------------------------------------------------------------------------
def parking_garage(name: str = "parking_garage_preset",
                   mode: str = "heist",
                   floors: int = 2,
                   basement: bool = False,
                   scale_ref: bool = False) -> dict:
    """An enclosed multi-level parking structure: low concrete decks linked by a
    drivable ramp and a pedestrian stair core, rows of structural columns, a
    sealed perimeter with vehicle openings as the entries, and a glassed
    attendant booth (assault: the holdable point; heist: the cash office). The
    sealed shell passes the enterability gate while the ramp gives honest
    vertical traversal. `floors` sets deck count (min 2). The column grid is the
    prime candidate to promote from repeated VOLUMES to one placed asset at
    art-pass time (docs/AUTHORING.md)."""
    floors = max(2, int(floors))
    fx, fy = 36.0, 28.0
    sh = 3.0
    half_x, half_y = fx / 2, fy / 2

    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 2002, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": floors, "has_basement": False, "wall_thick": 0.35,
        "floor_thick": 0.3, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "concrete",
        "materials": _mats("concrete", "drywall", "glass", "metal", "wood"),
    }

    ext = [
        {"wall": "S", "story": 0, "material": "concrete", "openings": [
            {"kind": "garage", "pos": -0.25, "width": 5.0, "height": 2.4, "tag": "vehicle_in"},
            {"kind": "garage", "pos": 0.25, "width": 5.0, "height": 2.4, "tag": "vehicle_out"},
            {"kind": "door", "pos": 0.45, "width": 1.1, "tag": "pedestrian_s"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.4, "width": 1.1, "tag": "pedestrian_n"},
            {"kind": "breach", "pos": 0.3, "width": 1.6, "breach_class": "soft_wall", "material": "drywall", "tag": "north_breach"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.1, "tag": "west_ped"}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.1, "tag": "east_ped"}]},
    ]
    # upper decks: open bays (windows) on every facing — shell stays sealed but reads open
    for st in range(1, floors):
        for w in ("S", "N", "E", "W"):
            ext.append({"wall": w, "story": st, "material": "concrete", "openings": [
                {"kind": "window", "pos": -0.25, "width": 6.0, "height": 1.4, "sill": 1.0},
                {"kind": "window", "pos": 0.25, "width": 6.0, "height": 1.4, "sill": 1.0}]})
    spec["ext_walls"] = ext

    # attendant booth: SW corner glass box, two doors (>=2 access for objective)
    spec["partitions"] = [
        {"story": 0, "axis": "Y", "pos": -half_x + 8.0, "start": -half_y, "end": -half_y + 6.0, "material": "glass",
         "openings": [{"kind": "door", "pos": 0.0, "width": 1.4, "tag": "booth_e"}]},
        {"story": 0, "axis": "X", "pos": -half_y + 6.0, "start": -half_x, "end": -half_x + 8.0, "material": "glass",
         "openings": [{"kind": "door", "pos": 0.0, "width": 1.2, "tag": "booth_n"}]},
    ]

    # drivable ramp (E side) linking each deck to the next; pedestrian stair (NW)
    ramps = []
    for st in range(floors - 1):
        ramps.append({"x": half_x - 5.0, "y": 0.0, "from_story": st, "to_story": st + 1,
                      "run": 10.0, "width": 3.0, "axis": "Y", "cut_slabs": True})
    spec["ramps"] = ramps
    spec["stairs"] = [{"x": -half_x + 4.0, "y": half_y - 4.0, "from_story": 0, "to_story": floors - 1,
                       "style": "switchback", "cut_slabs": True}]
    spec["vault_ledges"] = []

    # column grid (repeated -> promote candidate) + booth desk
    cols_x = [-12.0, -4.0, 4.0, 10.0]
    cols_y = [-8.0, 0.0, 8.0]
    vols = []
    for st in range(floors):
        for i, cx in enumerate(cols_x):
            for j, cy in enumerate(cols_y):
                vols.append({"name": f"col_{st}_{i}{j}", "x": cx, "y": cy, "z": st * sh + 1.5,
                             "size_x": 0.5, "size_y": 0.5, "size_z": 3.0, "collision": "convex", "material": "concrete"})
    vols.append({"name": "booth_desk", "x": -14.0, "y": -11.0, "z": 0.5, "size_x": 2.0, "size_y": 1.0, "size_z": 1.0, "collision": "convex", "material": "metal"})
    spec["volumes"] = vols

    rooms = [
        {"id": "attendant_booth", "story": 0, "bounds": [-half_x, -half_y, -half_x + 8.0, -half_y + 6.0], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
        {"id": "deck_0_south", "story": 0, "bounds": [-half_x + 8.0, -half_y, half_x, -half_y + 6.0], "role": "public_entry", "combat_range": "long"},
        {"id": "deck_0_main", "story": 0, "bounds": [-half_x, -half_y + 6.0, half_x, half_y], "role": "connector", "combat_range": "long"},
    ]
    for st in range(1, floors):
        rooms.append({"id": f"deck_{st}", "story": st, "bounds": [-half_x, -half_y, half_x, half_y], "role": "connector", "combat_range": "long"})
    spec["rooms"] = rooms

    markers = [
        {"type": "cover_high", "id": "COL00", "x": -12.0, "y": -8.0, "z": 0.0, "room": "deck_0_main"},
        {"type": "cover_high", "id": "COL11", "x": -4.0, "y": 0.0, "z": 0.0, "room": "deck_0_main"},
        {"type": "cover_high", "id": "COL22", "x": 4.0, "y": 8.0, "z": 0.0, "room": "deck_0_main"},
        {"type": "camera_socket", "id": "01", "x": half_x - 3.0, "y": half_y - 3.0, "z": 2.6, "room": "deck_0_main", "rot_z": 225},
    ]
    if mode == "heist":
        spec["objectives"] = [
            {"id": "booth_safe", "kind": "drill", "x": -14.0, "y": -11.0, "z": 0.5, "room": "attendant_booth", "required": True, "duration": 25.0},
        ]
        spec["loot"] = [
            {"id": "booth_cash", "kind": "cash", "x": -14.0, "y": -11.0, "z": 0.6, "value": 6000, "bags": 2, "room": "attendant_booth"},
        ]
        spec["zones"] = [{"id": "vehicle_extract", "kind": "extraction", "story": 0, "bounds": [-half_x, -half_y, 0.0, -half_y + 6.0]}]
        markers += [
            {"type": "objective", "id": "BOOTHSAFE", "x": -14.0, "y": -11.0, "z": 0.5, "room": "attendant_booth"},
            {"type": "loot", "id": "BOOTHCASH", "x": -14.0, "y": -11.0, "z": 0.6, "room": "attendant_booth"},
            {"type": "extraction", "id": "VEHICLE", "x": -4.0, "y": -12.0, "z": 0.0, "room": "deck_0_south"},
            {"type": "attacker_spawn", "id": "A", "x": -9.0, "y": -12.0, "z": 0.0, "rot_z": 0, "room": "deck_0_south"},
            {"type": "attacker_spawn", "id": "B", "x": 9.0, "y": -12.0, "z": 0.0, "rot_z": 0, "room": "deck_0_south"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": -9.0, "y": -12.0, "z": 0.0, "rot_z": 0, "room": "deck_0_south"},
            {"type": "attacker_spawn", "id": "B", "x": 9.0, "y": -12.0, "z": 0.0, "rot_z": 0, "room": "deck_0_south"},
            {"type": "defender_spawn", "id": "D", "x": -14.0, "y": -11.0, "z": 0.0, "rot_z": 45, "room": "attendant_booth"},
            {"type": "objective", "id": "BOOTH", "x": -14.0, "y": -11.0, "z": 0.0, "room": "attendant_booth", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # skyline parapet on the (capped) roof slab; the upper deck itself
    # is an enclosed level, so no interior barrier is needed
    spec["parapets"] = [{"story": 2, "height": 1.1, "thick": 0.35}]
    return spec


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# VERTICAL HEIST SET-PIECES  --  exercise stairs (0.51 ramp) + a roof ladder
# (0.52 climb volume). Comfortable ~36deg stair runs (run ~= story_height*1.4).
# ---------------------------------------------------------------------------
def auto_shop(name: str = "auto_shop_preset", mode: str = "heist",
              floors: int = 2, scale_ref: bool = False) -> dict:
    """Two-storey auto service garage: an open ground bay (roll-up door, lifts,
    parts racks) and an upper office holding the safe, joined by a stair. A
    roof-access ladder off the upper floor gives a flank/escape. Medium-range
    industrial heist; exercises the stair ramp + the ladder climb volume."""
    sh = 3.6
    fx, fy = 26.0, 18.0
    hx, hy = fx / 2, fy / 2
    run = round(sh * 1.4, 1)        # ~5.0 m -> ~36deg, comfortable
    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 1971, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 2, "has_basement": False, "wall_thick": 0.3,
        "floor_thick": 0.3, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "concrete",
        "materials": [
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "metal", "acoustic": "Metal", "absorption": 0.35, "damping": 0.25},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
        ],
    }
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "metal", "openings": [
            {"kind": "garage", "pos": -0.15, "width": 4.0, "height": 3.0, "tag": "bay_door"},
            {"kind": "door", "pos": 0.35, "width": 1.1, "tag": "front_man_door"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.3, "width": 1.1, "tag": "rear_door"},
            {"kind": "breach", "pos": -0.3, "width": 1.3, "breach_class": "soft_wall", "material": "drywall"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.25, "width": 1.4, "sill": 1.2, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": -0.3, "width": 1.1, "tag": "side_door"}]},
        {"wall": "S", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.2, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "window", "pos": 0.25, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.3, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"},
            {"kind": "breach", "pos": 0.3, "width": 1.2, "breach_class": "soft_wall", "material": "drywall"}]},
        {"wall": "W", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.3, "sill": 1.0, "vaultable": True, "material": "glass"}]},
    ]
    spec["partitions"] = [
        # ground: wall off the back strip (parts/stair) from the open bay
        {"story": 0, "axis": "X", "pos": 4.0, "start": -hx, "end": hx, "material": "concrete",
         "openings": [{"kind": "door", "pos": -0.25, "width": 1.1}, {"kind": "door", "pos": 0.3, "width": 1.1}]},
        # upper: split office (objective) from storage
        {"story": 1, "axis": "X", "pos": 2.0, "start": -hy, "end": hy, "material": "drywall",
         "openings": [{"kind": "door", "pos": 0.2, "width": 1.4}]},
    ]
    spec["stairs"] = [{"x": 9.0, "y": 6.5, "from_story": 0, "to_story": 1,
                       "width": 1.2, "run": run, "style": "switchback", "cut_slabs": True}]
    # roof-access ladder off the upper floor -> story 2 hatch. It climbs from
    # upper_storage, not the office: a roof hatch may not open from an
    # objective room (ladder spec s8.3).
    spec["ladders"] = [{"x": -10.5, "y": -6.0, "from_story": 1, "to_story": 2,
                        "width": 0.5, "depth": 0.15, "facing": "S", "cut_slabs": True}]
    spec["vertical_links"] = [
        {"kind": "stair", "from_story": 0, "to_story": 1, "role": "main_route"},
        {"kind": "hatch", "from_story": 1, "to_story": 2, "role": "roof_escape", "x": -10.5, "y": -6.0},
    ]
    spec["volumes"] = [
        {"name": "lift_1", "x": -6.0, "y": -3.0, "z": 0.1, "size_x": 2.6, "size_y": 1.2, "size_z": 0.2, "collision": "convex", "material": "metal"},
        {"name": "lift_2", "x": 4.0, "y": -3.0, "z": 0.1, "size_x": 2.6, "size_y": 1.2, "size_z": 0.2, "collision": "convex", "material": "metal"},
        {"name": "parts_rack", "x": -10.0, "y": 6.5, "z": 0.9, "size_x": 1.0, "size_y": 5.0, "size_z": 1.8, "collision": "convex", "material": "metal"},
        {"name": "tool_bench", "x": 2.0, "y": 6.5, "z": 0.5, "size_x": 3.0, "size_y": 1.0, "size_z": 1.0, "collision": "convex", "material": "metal"},
        {"name": "office_desk", "x": -7.0, "y": 5.5, "z": sh + 0.4, "size_x": 1.8, "size_y": 0.9, "size_z": 0.8, "collision": "convex", "material": "metal"},
    ]
    rooms = [
        {"id": "service_bay", "story": 0, "bounds": [-hx, -hy, hx, 4.0], "role": "public_entry", "combat_range": "medium"},
        {"id": "parts_back", "story": 0, "bounds": [-hx, 4.0, hx, hy], "role": "connector", "combat_range": "close"},
        {"id": "upper_office", "story": 1, "bounds": [-hx, 2.0, hx, hy], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
        {"id": "upper_storage", "story": 1, "bounds": [-hx, -hy, hx, 2.0], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
    ]
    spec["rooms"] = rooms
    markers = [
        {"type": "cover_low", "id": "LIFT1", "x": -6.0, "y": -3.0, "z": 0.0, "room": "service_bay"},
        {"type": "cover_low", "id": "LIFT2", "x": 4.0, "y": -3.0, "z": 0.0, "room": "service_bay"},
        {"type": "cover_high", "id": "RACK", "x": -10.0, "y": 6.5, "z": 0.0, "room": "parts_back"},
    ]
    if mode == "heist":
        spec["objectives"] = [{"id": "crack_office_safe", "kind": "drill", "x": -7.0, "y": 6.0, "z": sh + 0.2, "room": "upper_office", "required": True, "duration": 30.0}]
        spec["loot"] = [{"id": "shop_take", "kind": "cash", "x": -7.0, "y": 6.0, "z": sh + 0.2, "value": 6000, "bags": 3, "room": "upper_office"}]
        spec["zones"] = [{"id": "bay_extract", "kind": "extraction", "story": 0, "bounds": [-hx, -hy, hx, -4.0]}]
        markers += [
            {"type": "objective", "id": "SAFE", "x": -7.0, "y": 6.0, "z": sh + 0.2, "room": "upper_office"},
            {"type": "extraction", "id": "BAY", "x": 0.0, "y": -7.5, "z": 0.0, "room": "service_bay"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": 0.0, "y": -8.0, "z": 0.0, "rot_z": 0, "room": "service_bay"},
            {"type": "defender_spawn", "id": "D", "x": -7.0, "y": 6.0, "z": sh, "rot_z": 180, "room": "upper_office"},
            {"type": "objective", "id": "OFFICE", "x": -7.0, "y": 6.0, "z": sh, "room": "upper_office", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -12.0, "y": -8.0, "from_story": 0, "to_story": 1,
         "facing": "E", "cut_slabs": True})
    # roof-ladder building: the rooftop is a fighting position, so the
    # edge gets a lip -- cover at the parapet, no naked fall-off
    spec["parapets"] = [{"story": 2, "height": 1.0, "thick": 0.3}]
    return spec


def pawn_shop(name: str = "pawn_shop_preset", mode: str = "heist",
              floors: int = 2, scale_ref: bool = False) -> dict:
    """Small two-storey corner pawn shop: a glass-front shop floor with display-
    case cover and a counter, a back room with the safe, and an upper storage/
    apartment reached by a stair, with a roof ladder for escape. Tight close-
    quarters safe job; exercises stairs + ladder in a small footprint."""
    sh = 3.4
    fx, fy = 16.0, 14.0
    hx, hy = fx / 2, fy / 2
    run = round(sh * 1.4, 1)        # ~4.8 m -> ~35deg
    spec = {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": mode, "seed": 1973, "grid": 0.5,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": 2, "has_basement": False, "wall_thick": 0.25,
        "floor_thick": 0.25, "collision": "convex", "auto_exterior": True,
        "scale_ref": bool(scale_ref), "default_material": "concrete",
        "materials": [
            {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
            {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.05},
            {"id": "drywall", "acoustic": "Drywall", "absorption": 0.42, "damping": 0.38},
            {"id": "wood", "acoustic": "Wood", "absorption": 0.35, "damping": 0.3},
        ],
    }
    spec["ext_walls"] = [
        {"wall": "S", "story": 0, "material": "glass", "openings": [
            {"kind": "door", "pos": -0.2, "width": 1.4, "tag": "front_door"},
            {"kind": "window", "pos": 0.25, "width": 2.2, "sill": 0.6, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.0, "width": 1.1, "tag": "rear_door"},
            {"kind": "breach", "pos": 0.35, "width": 1.1, "breach_class": "soft_wall", "material": "drywall"}]},
        {"wall": "W", "story": 0, "material": "concrete", "openings": [
            {"kind": "window", "pos": -0.2, "width": 1.2, "sill": 0.8, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 0, "material": "concrete", "openings": [
            {"kind": "door", "pos": 0.25, "width": 1.1, "tag": "alley_door"}]},
        {"wall": "S", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.4, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "N", "story": 1, "material": "concrete", "openings": [
            {"kind": "breach", "pos": 0.0, "width": 1.2, "breach_class": "soft_wall", "material": "drywall"}]},
        {"wall": "W", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"}]},
        {"wall": "E", "story": 1, "material": "concrete", "openings": [
            {"kind": "window", "pos": 0.0, "width": 1.2, "sill": 1.0, "vaultable": True, "material": "glass"}]},
    ]
    spec["partitions"] = [
        # ground: counter wall splitting shop floor (front) from back safe room
        {"story": 0, "axis": "X", "pos": 2.0, "start": -hx, "end": hx, "material": "wood",
         "openings": [{"kind": "door", "pos": -0.3, "width": 1.4}, {"kind": "door", "pos": 0.35, "width": 1.1}]},
        # upper: split storage from apartment
        {"story": 1, "axis": "X", "pos": 0.0, "start": -hy, "end": hy, "material": "drywall",
         "openings": [{"kind": "door", "pos": 0.0, "width": 1.1}]},
    ]
    # back-room stair to the upper storage/apartment. The 16x14 shell is too
    # tight for a N/S ascent against the rear wall (the flight + landings
    # need ~8.6 m of run axis), so it lies along the back room's E-W axis;
    # _finish_stairs orients it so entry and exit both open onto clear floor.
    spec["stairs"] = [{"x": 2.5, "y": 5.5, "from_story": 0, "to_story": 1,
                       "width": 1.0, "run": run, "style": "switchback", "cut_slabs": True}]
    spec["ladders"] = [{"x": -6.0, "y": 4.5, "from_story": 1, "to_story": 2,
                        "width": 0.5, "depth": 0.15, "facing": "S", "cut_slabs": True}]
    spec["vertical_links"] = [
        {"kind": "stair", "from_story": 0, "to_story": 1, "role": "main_route"},
        {"kind": "hatch", "from_story": 1, "to_story": 2, "role": "roof_escape", "x": -6.0, "y": 4.5},
    ]
    spec["volumes"] = [
        {"name": "display_case_1", "x": -4.0, "y": -3.5, "z": 0.5, "size_x": 2.4, "size_y": 0.9, "size_z": 1.0, "collision": "convex", "material": "glass"},
        {"name": "display_case_2", "x": 4.0, "y": -3.5, "z": 0.5, "size_x": 2.4, "size_y": 0.9, "size_z": 1.0, "collision": "convex", "material": "glass"},
        {"name": "counter", "x": 0.0, "y": 1.2, "z": 0.55, "size_x": 4.0, "size_y": 0.7, "size_z": 1.1, "collision": "convex", "material": "wood"},
        # shelving sits clear of the roof ladder's climb envelope (Rule:
        # the climbing volume is reserved space)
        {"name": "shelving", "x": -3.5, "y": 4.5, "z": sh + 0.9, "size_x": 0.8, "size_y": 4.0, "size_z": 1.8, "collision": "convex", "material": "wood"},
    ]
    rooms = [
        {"id": "shop_floor", "story": 0, "bounds": [-hx, -hy, hx, 2.0], "role": "public_entry", "combat_range": "close"},
        {"id": "safe_room", "story": 0, "bounds": [-hx, 2.0, hx, hy], "role": "objective_room", "objective": True, "fortifiable": True, "combat_range": "close"},
        {"id": "apartment", "story": 1, "bounds": [-hx, -hy, hx, 0.0], "role": "connector", "combat_range": "close"},
        {"id": "upper_storage", "story": 1, "bounds": [-hx, 0.0, hx, hy], "role": "fortifiable", "fortifiable": True, "combat_range": "close"},
    ]
    spec["rooms"] = rooms
    markers = [
        {"type": "cover_low", "id": "CASE1", "x": -4.0, "y": -3.5, "z": 0.0, "room": "shop_floor"},
        {"type": "cover_low", "id": "CASE2", "x": 4.0, "y": -3.5, "z": 0.0, "room": "shop_floor"},
        {"type": "cover_low", "id": "COUNTER", "x": 0.0, "y": 1.2, "z": 0.0, "room": "shop_floor"},
    ]
    if mode == "heist":
        spec["objectives"] = [{"id": "crack_safe", "kind": "drill", "x": 0.0, "y": 5.0, "z": 0.2, "room": "safe_room", "required": True, "duration": 25.0}]
        spec["loot"] = [{"id": "pawn_take", "kind": "valuables", "x": 0.0, "y": 5.0, "z": 0.2, "value": 5000, "bags": 2, "room": "safe_room"}]
        spec["zones"] = [{"id": "front_extract", "kind": "extraction", "story": 0, "bounds": [-hx, -hy, hx, -4.0]}]
        markers += [
            {"type": "objective", "id": "SAFE", "x": 0.0, "y": 5.0, "z": 0.2, "room": "safe_room"},
            {"type": "extraction", "id": "FRONT", "x": -3.0, "y": -6.0, "z": 0.0, "room": "shop_floor"}]
    else:
        markers += [
            {"type": "attacker_spawn", "id": "A", "x": -3.0, "y": -6.0, "z": 0.0, "rot_z": 0, "room": "shop_floor"},
            {"type": "defender_spawn", "id": "D", "x": 0.0, "y": 5.0, "z": 0.0, "rot_z": 180, "room": "safe_room"},
            {"type": "objective", "id": "SAFE", "x": 0.0, "y": 5.0, "z": 0.0, "room": "safe_room", "meta": {"kind": "capture"}}]
    spec["markers"] = markers
    # combat-audit second vertical link: stories 0<->1 fought as a
    # single-stair siege; this ladder makes the pair a level. Placement
    # clearance-verified against partitions/volumes/stairs on both stories.
    spec.setdefault("ladders", []).append(
        {"x": -7.0, "y": -6.0, "from_story": 0, "to_story": 1,
         "facing": "E", "cut_slabs": True})
    # roof-ladder building: parapet lip = rooftop cover + edge safety
    spec["parapets"] = [{"story": 2, "height": 0.9, "thick": 0.3}]
    return spec


# ---------------------------------------------------------------------------
# FACADE shells -- non-enterable filler buildings: exterior + roof + collision
# + theme ONLY (no interior, no gameplay). They emit no tactical data and are
# meant to be REUSED all over a block and art-passed later by resolving their
# modular wall slots into themed window/brick modules. Pair with Lot's
# `blocker` (give the blocker this shell's .glb/.tscn) to wall a street.
# ---------------------------------------------------------------------------
def _facade(name, fx, fy, stories, sh, material, mats, parapet_h=0.8, seed=1999):
    return {
        "$schema": "../schema/level.schema.json",
        "name": name, "mode": "heist", "seed": seed, "grid": 0.5,
        "facade": True,
        "footprint_x": fx, "footprint_y": fy, "story_height": sh,
        "n_stories": stories, "has_basement": False,
        "wall_thick": 0.3, "floor_thick": 0.3, "collision": "convex",
        "auto_exterior": True,       # solid sealed exterior shell (no openings)
        "modular": True,             # art-pass-ready: walls become swap slots
        "scale_ref": False,
        "default_material": material,
        "materials": mats,
        "parapets": [{"story": stories, "height": parapet_h, "thick": 0.3}],
    }


def facade_rowhome(name: str = "facade_rowhome", floors: int = 2,
                   scale_ref: bool = False) -> dict:
    """Narrow 2-storey rowhome shell -- the DELCO/Philly street-wall unit. Reuse
    it in a run down a block (vary the height a touch per instance). Non-enterable
    filler; art-pass resolves the slots to brick + windows + a stoop door."""
    s = _facade(name, 8.0, 11.0, floors, 3.1, "concrete", [
        {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
        {"id": "wood", "acoustic": "Wood", "absorption": 0.5, "damping": 0.45},
    ], parapet_h=0.7, seed=1901)
    s["scale_ref"] = bool(scale_ref)
    return s


def facade_storefront(name: str = "facade_storefront", floors: int = 2,
                      scale_ref: bool = False) -> dict:
    """Wider commercial storefront shell (shop below, apartment above) for main-
    street frontage. Non-enterable filler; art-pass resolves the ground floor to
    glazing + a sign band, the upper floor to apartment windows."""
    s = _facade(name, 14.0, 12.0, floors, 3.4, "concrete", [
        {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
        {"id": "glass", "acoustic": "Glass", "absorption": 0.1, "damping": 0.1},
    ], parapet_h=0.9, seed=1902)
    s["scale_ref"] = bool(scale_ref)
    return s


def facade_industrial(name: str = "facade_industrial", floors: int = 1,
                      scale_ref: bool = False) -> dict:
    """Big single-storey industrial wall shell -- caps a block or backs an alley.
    Tall, blank, cheap. Non-enterable filler; art-pass adds corrugated metal +
    a roll-up door + clerestory strip."""
    s = _facade(name, 30.0, 20.0, floors, 6.0, "metal", [
        {"id": "metal", "acoustic": "Metal", "absorption": 0.35, "damping": 0.25},
        {"id": "concrete", "acoustic": "Concrete", "absorption": 0.7, "damping": 0.6},
    ], parapet_h=0.6, seed=1903)
    s["scale_ref"] = bool(scale_ref)
    return s


# ---------------------------------------------------------------------------
# REGISTRY
# ---------------------------------------------------------------------------
REGISTRY = {
    "bank": bank,
    "police_station": police_station,
    "corner_deli": corner_deli,
    "compound": compound,
    "hospital": hospital,
    "warehouse": warehouse,
    "suburban_safehouse": suburban_safehouse,
    "rowhome": rowhome,
    "casino_tower": casino_tower,
    "gas_station": gas_station,
    "office": office,
    "parking_garage": parking_garage,
    "auto_shop": auto_shop,
    "pawn_shop": pawn_shop,
    "facade_rowhome": facade_rowhome,
    "facade_storefront": facade_storefront,
    "facade_industrial": facade_industrial,
}


def _finish_stairs(spec: dict) -> None:
    """Close the stair loop for preset output: every generated stair leaves
    here with an explicit FACING (chosen to clear the physical circulation
    review, not defaulted north), a ROLE (the strongest classification the
    layout supports), a stable id, and the `meta.generated_by` stamp that
    opts it into stairwell.py's hard generated-stair contract.

    Facing: all four cardinals are evaluated with stairwell.clearance_findings
    and the cleanest wins (ties break N,E,S,W -- deterministic forever).
    Role: egress roles are tried first and kept only if the whole spec still
    reviews with zero stairwell errors; otherwise the stair degrades to a
    classified non-egress role. The generated stamp is only applied when the
    stair is physically clean -- a recipe whose stair cannot be oriented
    clean keeps authored (warning-level) severity so generation never breaks,
    and the regression sweep flags it for a position fix."""
    stairs = spec.get("stairs") or []
    if not stairs or spec.get("facade"):
        return
    from spec_loader import spec_from_dict
    import stairwell as _sw

    def _load():
        return spec_from_dict(spec)

    # pass 1: orient every stair (earlier choices are fixed for later ones,
    # so landing-vs-other-stair checks see settled footprints)
    clean = []
    for i, sd in enumerate(stairs):
        authored = sd.get("facing")
        order = ([authored] + [f for f in ("N", "E", "S", "W")
                               if f != authored]) if authored \
            else ["N", "E", "S", "W"]
        best_f, best_n = order[0], None
        for f in order:
            sd["facing"] = f
            sp = _load()
            n = len(_sw.clearance_findings(sp, sp.stairs[i],
                                           sd.get("id") or f"stair_{i}"))
            if best_n is None or n < best_n:
                best_f, best_n = f, n
            if n == 0:
                break
        sd["facing"] = best_f
        clean.append(best_n == 0)

    # pass 2: role + id + generated stamp
    role_ladder = {0: ["primary_egress", "public_convenience", "service"],
                   1: ["secondary_egress", "service"]}
    for i, sd in enumerate(stairs):
        if not sd.get("id"):
            sd["id"] = f"{spec.get('name', 'level')}_stair_{i}"
        had_role = bool(sd.get("role"))
        if clean[i]:
            meta = dict(sd.get("meta") or {})
            meta.setdefault("generated_by", "presets")
            sd["meta"] = meta
        if had_role:
            continue
        candidates = role_ladder.get(i, ["service"])
        chosen = candidates[-1]
        for role in candidates:
            sd["role"] = role
            sp = _load()
            errors, _, _ = _sw.check(sp)
            if not any(f"'{sd['id']}'" in e for e in errors):
                chosen = role
                break
        sd["role"] = chosen


def _finish_ladders(spec: dict) -> None:
    """The ladder counterpart of _finish_stairs: every preset ladder leaves
    generation with a stable id and a ROLE (Rule 1: a ladder without a role
    is not generated). Role candidates come from what the ladder physically
    is -- reaches the roof -> roof_access, climbs out of a basement ->
    service_access, interior second route -> special_gameplay_route -- and
    the first role whose contract the layout satisfies (no ladder errors
    naming this ladder) wins. If every candidate errors, the first is kept
    so the failure is visible in review: that is a recipe bug to fix, not
    something to silence."""
    ladders = spec.get("ladders") or []
    if not ladders or spec.get("facade"):
        return
    from spec_loader import spec_from_dict
    import ladder as _ld
    n_stories = spec.get("n_stories", 1)
    for i, ld in enumerate(ladders):
        if not ld.get("id"):
            ld["id"] = f"{spec.get('name', 'level')}_ladder_{i}"
        if ld.get("role"):
            continue
        hi = max(ld.get("from_story", 0), ld.get("to_story", 0))
        lo = min(ld.get("from_story", 0), ld.get("to_story", 0))
        if hi >= n_stories:
            candidates = ["roof_access", "service_access"]
        elif lo < 0:
            candidates = ["service_access", "maintenance_access"]
        else:
            candidates = ["special_gameplay_route", "service_access"]
        chosen = candidates[0]
        for role in candidates:
            ld["role"] = role
            sp = spec_from_dict(spec)
            errors, _, _ = _ld.check(sp)
            if not any(f"'{ld['id']}'" in e for e in errors):
                chosen = role
                break
        ld["role"] = chosen


def make(preset: str, enrich: bool = True, stairs_first: bool = False,
         archetype: Optional[str] = None, **kwargs) -> dict:
    """Build a preset spec. By default the finished spec is run through
    level_design.enrich() so every building comes out with readable cover
    cadence and callout landmarks (better by construction), and every stair
    leaves classified + oriented via _finish_stairs (the stair loop closes
    at generation time, not review time). Pass enrich=False for the raw
    recipe output (stairs are still finished -- an unfinished stair is a
    generation bug, not a style choice).

    stairs_first=True inverts the recipe's generation order: the recipe's
    authored stairs are REPLACED by stair cores reserved against the shell
    (stair_core.py), and the recipe's partitions, rooms, props, and markers
    adapt around the reservation -- walls trim at the shaft, enclosures gain
    doors onto the landings, overlapped rooms split around a dedicated
    stairwell, and props inside the reservation are evicted. `archetype`
    overrides the preset's default stair_place profile."""
    if preset not in REGISTRY:
        raise KeyError(f"unknown preset '{preset}'. "
                       f"available: {', '.join(sorted(REGISTRY))}")
    spec = REGISTRY[preset](**kwargs)
    # orientation FIRST: the stair's facing (and therefore its landing
    # reservation) must be settled before enrich seeds cover around it --
    # otherwise cover placed against the default-north reservation can land
    # on the finally-chosen facing's landing (found by the 100-seed sweep).
    _finish_stairs(spec)
    if enrich and not spec.get("facade"):
        level_design.enrich(spec)
    if stairs_first and not spec.get("facade") \
            and spec.get("n_stories", 1) >= 2:
        import stair_core
        arch = archetype or stair_core.DEFAULT_ARCHETYPE.get(preset)
        if arch is None:
            raise ValueError(f"no default archetype for preset '{preset}'; "
                             f"pass archetype=...")
        global LAST_CORE_EVICTIONS
        LAST_CORE_EVICTIONS = stair_core.core_first(spec, arch)
    _finish_stairs(spec)
    _finish_ladders(spec)
    return spec
