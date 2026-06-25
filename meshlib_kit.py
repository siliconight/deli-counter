"""
meshlib_kit.py  --  manifest + docs for the optional GridMap parts-kit
======================================================================
The parts-kit MeshLibrary itself is generated IN GODOT by
godot/addon/deli_counter/meshlib_kit.gd (built in-engine so the mesh data is
always valid). This module is the offline half: it defines the canonical kit
(module names, grid dimensions, collision) so the two stay in sync, emits a
manifest, and documents the kit. It's verifiable without Blender or Godot.

The kit is OPTIONAL and additive — the baked .glb remains Deli Counter's
primary, replication-free output. The MeshLibrary is a companion for anyone who
wants to hand-greybox a fresh layout on a GridMap by eye. Dimensions follow the
kit's scale guidelines (0.5 m main grid, 1.0 m structural, 3 m story, 0.2 m
walls, 2.2 m doorways).
"""

STORY_H = 3.0
WALL_T = 0.2
CELL = 1.0
DOOR_H = 2.2
DOOR_W = 1.2

# canonical kit: (name, plan footprint w x d in m, height in m, has_collision,
#                 description)
KIT = [
    ("floor_1x1",     CELL, CELL, WALL_T, True,  "1x1 m floor/ceiling slab"),
    ("wall_1m",       CELL, WALL_T, STORY_H, True, "solid wall segment, full story"),
    ("wall_half_1m",  CELL, WALL_T, 1.1, True,  "half wall / railing at cover height"),
    ("wall_door_1m",  CELL, WALL_T, STORY_H, True, f"wall with a {DOOR_W}x{DOOR_H} m doorway"),
    ("wall_window_1m", CELL, WALL_T, STORY_H, True, "wall with a mid-height window opening"),
    ("pillar",        0.4, 0.4, STORY_H, True,  "0.4 m square column, full story"),
    ("counter_unit",  CELL, 0.6, 1.0, True,    "counter / low shelf, deli-counter scale"),
    ("stair_flight",  CELL, CELL * 4, STORY_H, True, "straight flight rising one story over ~4 cells"),
    ("crate_1m",      CELL, CELL, CELL, True,   "1 m cover cube"),
]


def manifest():
    """Return the kit as a list of dicts."""
    return [
        {"name": n, "footprint_w": w, "footprint_d": d, "height": h,
         "collision": col, "desc": desc}
        for (n, w, d, h, col, desc) in KIT
    ]


def grid_recommendation():
    """Recommended GridMap cell size for this kit."""
    return {"structural": (1.0, STORY_H, 1.0), "fine": (0.5, STORY_H, 0.5)}


def format_manifest():
    lines = ["Deli Counter — GridMap parts-kit (optional companion to the .glb)",
             "",
             f"  {'module':<16} {'plan (w x d)':<14} {'height':<8} collision",
             f"  {'-'*16} {'-'*14} {'-'*8} {'-'*9}"]
    for it in manifest():
        plan = f"{it['footprint_w']}x{it['footprint_d']} m"
        lines.append(f"  {it['name']:<16} {plan:<14} "
                     f"{it['height']:<8} {'yes' if it['collision'] else 'no'}")
    rec = grid_recommendation()
    lines += ["",
              f"  recommended GridMap cell size: {rec['structural']} (structural) "
              f"or {rec['fine']} (fine)",
              "  generate the .meshlib by running "
              "addons/deli_counter/meshlib_kit.gd in Godot."]
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_manifest())
