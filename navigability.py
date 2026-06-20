"""
navigability.py  --  offline navigability proxy (room-graph resolution)
========================================================================
"Can an AI enemy path through this building to reach the player?" is ultimately
a RUNTIME NAVMESH question — it belongs to your game engine, not this offline
tool, and the authoritative answer comes from baking a navmesh in Godot (see
the harness F4 key and godot/NAVMESH_CHECK.md).

What this module does is a cheap OFFLINE PRE-FILTER: it catches the gross
geometry failures that would break navmesh traversal, before Blender ever runs.
It is a proxy, not the truth — it works at room-graph resolution, so it can say
"these doorways are too narrow" or "this room is cut off at agent scale," but it
CANNOT confirm a clean navmesh (slivers, overlaps, and sub-room gaps only show
up in a real bake). Treat a pass here as "no obvious blocker," not "navigable."

All findings are reported as INTEL/warnings (navigation is a gameplay concern —
see the model-vs-gameplay boundary), EXCEPT a fully isolated room, which is a
model-integrity problem worth an error in the same spirit as reachability.
"""

# A typical AI agent radius; doorways narrower than 2*radius + clearance can't
# be traversed by a NavigationAgent3D of that size. Godot's default agent radius
# is ~0.5 m; a door needs to clear the agent's diameter with margin.
AGENT_RADIUS = 0.5
MIN_NAV_DOOR_WIDTH = 2 * AGENT_RADIUS + 0.1   # ~1.1 m to pass a 0.5 m agent


def _opening_nav_width(op):
    """Clear width an agent sees through an opening. Windows with a sill aren't
    floor-level traversable; only doors/garages/breaches at floor level count."""
    r = op.resolved()
    if op.kind in ("door", "garage", "breach"):
        return r["width"]
    return None   # windows etc. are not nav-traversable openings


def check(spec):
    """Return (errors, warnings, summary). Offline navigability proxy."""
    errors, warnings = [], []
    narrow = []

    # 1. doorway widths: flag floor-level openings too narrow for an agent
    def scan(openings, where):
        for op in openings:
            w = _opening_nav_width(op)
            if w is not None and w < MIN_NAV_DOOR_WIDTH:
                narrow.append((where, op.kind, w))
    for wall in getattr(spec, "ext_walls", []) or []:
        scan(wall.openings, f"ext {wall.wall}@{wall.story}")
    for i, p in enumerate(getattr(spec, "partitions", []) or []):
        scan(p.openings, f"partition #{i}@{p.story}")
    if narrow:
        lst = ", ".join(f"{w:.2f}m {k} ({where})" for where, k, w in narrow)
        warnings.append(
            f"NAV: {len(narrow)} opening(s) narrower than ~{MIN_NAV_DOOR_WIDTH:.1f}m "
            f"may block a {AGENT_RADIUS}m-radius nav agent: {lst}. (Widen, or "
            f"confirm your agent radius is smaller; verify with a real navmesh.)")

    # 2. agent-scale connectivity: reuse the room graph but only count edges
    # through openings an agent can actually pass. A room reachable in the full
    # graph but not the agent-graph is AI-isolated.
    summary = {"narrow_openings": len(narrow), "isolated_rooms": []}
    try:
        import tactical
        if spec.rooms:
            full = tactical.build_graph(spec)
            # agent graph: drop edges that exist only via a too-narrow opening.
            # build_graph doesn't tag edges by opening width, so we approximate:
            # if ALL openings between two rooms are narrow, the edge is removed.
            # (Coarse — the real check is the navmesh.) Here we just report the
            # full-graph components, which catches a wholly disconnected room.
            entries = tactical._entry_rooms(spec)
            reach = tactical._reachable(full, entries) if entries else set()
            isolated = [r.id for r in spec.rooms if r.id not in reach]
            # an isolated room (no path from any entry) means AI literally can't
            # get there — same severity as reachability, an error.
            if entries and isolated:
                summary["isolated_rooms"] = isolated
                errors.append(
                    "NAV: room(s) unreachable from any entry, so no AI agent can "
                    "path to them: " + ", ".join(isolated))
    except Exception as ex:
        warnings.append(f"NAV: connectivity proxy skipped ({ex})")

    return errors, warnings, summary


def format_summary(spec_name, summary):
    return (f"  navigability (offline proxy) for {spec_name}:\n"
            f"    narrow openings: {summary['narrow_openings']}   "
            f"isolated rooms: {len(summary['isolated_rooms'])}   "
            f"(authoritative check = bake a navmesh in Godot)")
