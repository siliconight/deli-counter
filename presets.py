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
# REGISTRY
# ---------------------------------------------------------------------------
REGISTRY = {
    "bank": bank,
    # corner_store, rowhome, warehouse, police_station, safehouse -> follow
}


def make(preset: str, **kwargs) -> dict:
    if preset not in REGISTRY:
        raise KeyError(f"unknown preset '{preset}'. "
                       f"available: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[preset](**kwargs)
