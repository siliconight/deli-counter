"""
deli_counter.py  --  Deli Counter level kit (core library)
=================================================================
A spec-driven generator for monolithic game levels in Blender 4.x,
exporting to Godot 4 via glTF (-convcolonly / -colonly collision convention).

WORKFLOW
--------
    prompt (you describe the building)
        -> LevelSpec (a declarative description, written per level)
        -> build(spec) in Blender -> VISUAL + COLLISION collections
        -> export .glb -> Godot auto-collision on import

You never edit this file per-level. You write a small spec file (see
spec_template.py) that imports from here, and run it in Blender.

DESIGN
------
A LevelSpec is fully declarative: footprint, stories, and a list of FEATURES.
Each feature is a placed element -- a room partition, a door, a window, a
stairwell, a vault, a hole in a slab, a prop volume, etc. The builder walks
the spec and emits geometry deterministically (seeded), so the same spec
always yields the same level. Pickiness about size lives entirely in the
spec: every dimension is explicit and in meters.

Coordinate system: origin at building center, ground floor slab top at z=0.
+X east, +Y north, +Z up. Story s spans z in [s*H, (s+1)*H].

Run in Blender: open your spec file in Scripting, Alt+P.
Headless:  blender --background --python your_spec.py
"""

import bpy
import bmesh
import math
import os
import random

# ============================================================================
# SPEC SCHEMA  --  imported from spec_types (pure Python, no bpy)
# ============================================================================

from spec_types import (
    Axis, Wall, Collision, Opening, ExtWall, Partition, Stairwell,
    SlabHole, Volume, Parapet, LevelSpec, Asset, Placement,
    Room, VerticalLink, Marker, Objective, LootSpawn, Zone, Material,
    Ladder, Ramp, VaultLedge,
)
from rarity import resolve_rarity
import interactives
import roofs


# ============================================================================
# BUILDER
# ============================================================================

class _Builder:
    def __init__(self, spec: LevelSpec, base_dir: str = "."):
        self.s = spec
        self.base_dir = base_dir
        random.seed(spec.seed)
        self.col_suffix = {
            "convex": "-convcolonly",
            "trimesh": "-colonly",
            "none": "",
        }
        self.VISUAL = None
        self.COLLISION = None
        self._asset_index = {a.id: a for a in spec.assets}
        self._material_index = {m.id: m for m in spec.materials}
        # Shared-mesh cache for module reuse. Identical modular segments (keyed
        # by role+dims) and repeated placement assets (keyed by asset id) link a
        # SINGLE mesh datablock instead of duplicating geometry, so the glTF
        # export carries one mesh + N nodes -> Godot loads one Mesh resource
        # instanced N times (one mesh/texture in VRAM; edit the shared module and
        # every instance follows). Populated lazily by _box / _placements.
        self._module_cache = {}

    # -- helpers ------------------------------------------------------------
    def snap(self, v):
        g = self.s.grid
        return round(v / g) * g

    # -- modular wall config -----------------------------------------------
    # Modular emission is OPT-IN. Resolve it from the spec when present
    # (spec.modular / spec.module), else fall back to the DC_MODULAR /
    # DC_MODULE env vars so it can be tried without a spec_types change.
    # Default: OFF -> existing specs rebuild byte-identical.
    def _modular_on(self):
        v = getattr(self.s, "modular", None)
        if v is not None:
            return bool(v)
        return os.environ.get("DC_MODULAR", "").strip().lower() in (
            "1", "true", "yes", "on")

    def _module_size(self):
        """Module width in metres for tiling solid spans. <= 0 disables tiling
        (pure opening-decomposition, 'Phase A'); > 0 tiles each solid span into
        whole modules + an end remainder ('Phase B')."""
        m = getattr(self.s, "module", None)
        if m is None:
            m = os.environ.get("DC_MODULE", "")
        try:
            return float(m) if str(m).strip() != "" else 2.0
        except (TypeError, ValueError):
            return 2.0

    def _module_lib(self):
        """Absolute path to the module library (the zoo of
        <type>_<theme>_<style>.glb), or None when unset -> resolver OFF and the
        emitter generates greybox boxes exactly as before."""
        lib = getattr(self.s, "module_library", None)
        if lib is None:
            lib = os.environ.get("DC_MODULE_LIB", "").strip() or None
        if not lib:
            return None
        if not os.path.isabs(lib):
            lib = os.path.normpath(os.path.join(self.base_dir, lib))
        return lib

    def _theme(self):
        t = getattr(self.s, "theme", None) or os.environ.get("DC_THEME", "").strip()
        return t or "greybox"

    def _state(self):
        """Optional model 'state' (e.g. damaged, weathered). From DC_STATE or a
        spec `state` field; None when unset. Honors the kit-naming convention
        <type>_<descriptor>_<variant>[_w<cm>][_<state>]."""
        s = getattr(self.s, "state", None) or os.environ.get("DC_STATE", "").strip()
        return s or None

    def _resolve_module(self, typename, style=1, width=None, state=None):
        """Resolve a slot to a module file, honoring the kit-naming convention
        <type>_<descriptor>_<variant>[_w<cm>][_<state>].glb.

        Per kit (active theme, then greybox), tries the most specific name first:
            1. <type>_<kit>_<style>_w<cm>_<state>   (width + state)
            2. <type>_<kit>_<style>_w<cm>           (width)
            3. <type>_<kit>_<style>_<state>         (state)
            4. <type>_<kit>_<style>                 (generic)
        width = the slot's exact width in cm (modules are instanced at authored
        size, never scaled). state = an optional model state (DC_STATE / spec),
        cosmetic to resolution and recorded in the slot manifest's current_ref so
        game code can act on it. Returns (path, kit, stem) or None (-> caller
        generates the greybox box). Backward compatible: no width and no state ->
        resolution is exactly as before."""
        lib = self._module_lib()
        if lib is None:
            return None
        if state is None:
            state = self._state()
        wtok = f"w{int(round(width * 100))}" if width else None

        def _stems(kit):
            base = f"{typename}_{kit}_{style:02d}"
            out = []
            if wtok and state:
                out.append(f"{base}_{wtok}_{state}")
            if wtok:
                out.append(f"{base}_{wtok}")
            if state:
                out.append(f"{base}_{state}")
            out.append(base)
            return out

        seen = []
        for kit in (self._theme(), "greybox"):
            if kit in seen:
                continue
            seen.append(kit)
            for stem in _stems(kit):
                path = os.path.join(lib, stem + ".glb")
                if os.path.exists(path):
                    return path, kit, stem
        return None

    def _instance_module(self, path, name, loc, rot_y, role=None):
        """Import a module GLB ONCE (cache each part's mesh datablock + local
        transform + collision suffix), then instance it: objects link the cached
        meshes, placed at the slot transform (loc + rot_y about up). Visual and
        collision parts route to their collections by the node-name suffix, so
        the module brings its own authored collision (apertures stay open). N
        instances of one module share one mesh -> one mesh in VRAM."""
        import mathutils
        key = ("module", path)
        parts = self._module_cache.get(key)
        if parts is None:
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=path)
            new = [o for o in bpy.data.objects
                   if o not in before and o.type == 'MESH']
            parts = []
            for o in new:
                nm = o.name.lower()
                if "convcol" in nm:
                    suf = self.col_suffix["convex"]      # -convcolonly
                elif "colonly" in nm or nm.endswith("-col"):
                    suf = self.col_suffix["trimesh"]     # -colonly
                else:
                    suf = None                            # visual
                o.data.use_fake_user = True               # survive purges
                parts.append((o.data, suf, o.matrix_world.copy()))
            for o in new:                                 # drop objects, keep data
                for c in list(o.users_collection):
                    c.objects.unlink(o)
            self._module_cache[key] = parts
        slot_m = (mathutils.Matrix.Translation(loc)
                  @ mathutils.Matrix.Rotation(math.radians(rot_y), 4, 'Z'))
        for i, (mesh_data, suf, local_m) in enumerate(parts):
            if suf:
                obj = bpy.data.objects.new(f"{name}_{i}{suf}", mesh_data)
                self.COLLISION.objects.link(obj)
            else:
                obj = bpy.data.objects.new(f"{name}_{i}", mesh_data)
                self.VISUAL.objects.link(obj)
                if role:
                    self.surface_roles[obj.name] = role
            obj.matrix_world = slot_m @ local_m
        return True

    def _cover(self, role, kit):
        """Tally art-pass coverage: which roles resolved to a theme/greybox
        module vs fell back to generated geometry."""
        self._coverage[(role, kit)] = self._coverage.get((role, kit), 0) + 1

    def _clear(self):
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        for block in (bpy.data.meshes, bpy.data.materials):
            for b in list(block):
                if b.users == 0:
                    block.remove(b)

    def _col(self, name):
        c = bpy.data.collections.get(name)
        if c is None:
            c = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(c)
        return c

    def _box(self, name, center, size, collection, role=None, share_key=None):
        # share_key set -> identical modules link ONE cached mesh datablock
        # (baked to real size, object carries position only) so the export
        # instances one module N times. share_key None -> original behaviour:
        # a private unit-cube mesh sized by object scale.
        cache = self._module_cache
        if share_key is not None and share_key in cache:
            mesh = cache[share_key]
            obj = bpy.data.objects.new(name, mesh)
            collection.objects.link(obj)
            obj.location = center
        else:
            mesh = bpy.data.meshes.new(name)
            obj = bpy.data.objects.new(name, mesh)
            collection.objects.link(obj)
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0)
            bm.to_mesh(mesh)
            bm.free()
            sx = max(size[0], 1e-4)
            sy = max(size[1], 1e-4)
            sz = max(size[2], 1e-4)
            if share_key is not None:
                # Bake the size into the shared mesh (verts at real dimensions),
                # leave object scale at 1 so an art pass on the module isn't
                # stretched differently per instance. Cache for reuse.
                import mathutils
                mesh.transform(mathutils.Matrix.Diagonal((sx, sy, sz, 1.0)))
                obj.location = center
                cache[share_key] = mesh
            else:
                obj.scale = (sx, sy, sz)
                obj.location = center
        # Record the authoritative surface role for VISUAL meshes so downstream
        # tools (Patina styling, the vertex-nuance pass) consume a label instead
        # of re-inferring floor/wall/ceiling from geometry (which is error-prone
        # across Blender/glTF/world-axis conventions). Collision meshes don't
        # need a role. The role -> node-name map is emitted into gameplay.json
        # as "surface_roles".
        if role is not None and collection is self.VISUAL:
            self.surface_roles[obj.name] = role
        return obj

    def _empty(self, name, location, collection, rot_z=0.0, size=0.4):
        """A named Empty used as a gameplay marker node. Exports to glTF as a
        node with no mesh; Godot's import script maps the name to a game node."""
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = 'ARROWS'
        obj.empty_display_size = size
        obj.location = location
        obj.rotation_euler = (0.0, 0.0, math.radians(rot_z))
        collection.objects.link(obj)
        return obj

    def _col_box(self, name, center, size, mode=None, share_key=None):
        mode = mode or self.s.collision
        suf = self.col_suffix[mode]
        if suf == "":
            return None
        return self._box(name + suf, center, size, self.COLLISION,
                         share_key=share_key)

    def _capsule(self, name, base_center, height, radius, collection):
        """A simple human-proxy: a cylinder standing on its base. Used only for
        the scale-reference overlay. base_center is the floor point; the proxy
        rises `height` from there."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12,
                              radius1=1.0, radius2=1.0, depth=1.0)
        bm.to_mesh(mesh)
        bm.free()
        obj.scale = (max(radius, 1e-4), max(radius, 1e-4), max(height, 1e-4))
        obj.location = (base_center[0], base_center[1],
                        base_center[2] + height / 2)
        return obj

    def _scale_ref(self):
        """If spec.scale_ref, drop a 1.8 m human-proxy at each spawn marker into
        a separate SCALE_REF collection. Purely a Blender-side visual check —
        kept out of VISUAL/COLLISION so it never affects export."""
        if not self.s.scale_ref:
            return
        ref = self._col("SCALE_REF")
        ph, pr = 1.8, 0.4     # player height / capsule radius (m), per guidelines
        n = 0
        for m in self.s.markers:
            if "spawn" not in m.type.lower():
                continue
            suffix = ("_" + m.id) if m.id else ""
            self._capsule(f"SCALEREF_{m.type.upper()}{suffix}",
                          (m.x, m.y, m.z), ph, pr, ref)
            n += 1
        if n == 0:
            self._capsule("SCALEREF_ORIGIN", (0.0, 0.0, 0.0), ph, pr, ref)
        # SCALE_REF stays visible in the viewport for the check; export()
        # excludes it explicitly so it never lands in a .glb/.gltf/.obj.
        print(f"[deli_counter] scale_ref: {max(n,1)} human proxy(ies) "
              f"({ph:g} m tall) in SCALE_REF collection (not exported)")

    def _box_with_holes(self, name, center, size, holes, collection):
        """Solid box minus rectangular holes (visual). holes: list of dicts
        with u (offset along run), v (offset in Z from wall center), w, h."""
        wall = self._box(name, center, size, collection, role="wall")
        if not holes:
            return wall
        long_axis = 0 if size[0] >= size[1] else 1
        cutters = []
        for i, hole in enumerate(holes):
            u, v, w, h = hole["u"], hole["v"], hole["w"], hole["h"]
            if long_axis == 0:
                hc = (center[0] + u, center[1], center[2] + v)
                hs = (w, size[1] * 2, h)
            else:
                hc = (center[0], center[1] + u, center[2] + v)
                hs = (size[0] * 2, w, h)
            cutters.append(self._box(f"{name}_cut{i}", hc, hs, collection))
        for cut in cutters:
            m = wall.modifiers.new(name="cut", type='BOOLEAN')
            m.operation = 'DIFFERENCE'
            m.object = cut
            m.solver = 'EXACT'
        bpy.context.view_layer.objects.active = wall
        for m in list(wall.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
        for cut in cutters:
            bpy.data.objects.remove(cut, do_unlink=True)
        return wall

    # -- openings -> hole dicts + collision segments ------------------------
    def _machine_for(self, op, wall_name, story):
        """The interactive state machine for an opening (or None). Derived
        purely from the AUTHORED opening + its wall, so both the hole/slot pass
        and the gameplay pass compute the SAME stable id independently. See
        interactives.py + docs/INTERACTIVES.md."""
        return interactives.derive_interactive(
            self.s.name, wall_name, story, op.kind, op.pos,
            breakable=bool(getattr(op, "breakable", False)),
            override=getattr(op, "interactive", None))

    def _opening_to_hole(self, op: Opening, run_len, wall_name=None,
                         story=None):
        r = op.resolved()
        u = self.snap(op.pos * run_len)
        H = self.s.story_height
        v = -H / 2.0 + r["sill"] + r["height"] / 2.0 + self.s.floor_thick / 2.0
        return dict(u=u, v=v, w=r["width"], h=r["height"], kind=op.kind,
                    sill=r["sill"],
                    interactive=self._machine_for(op, wall_name, story))

    def _wall_collision(self, name, center, size, axis, holes):
        """Emit convex collision for a wall pierced by any number of openings.

        Each opening carves a vertical void the width of the opening; the wall
        stays solid everywhere else. Per kind:
          - door / garage  -> void left open (walkable)
          - breach         -> void filled with a tagged removable BREACHPANEL
                              (visual + collision) so the shell reads solid in
                              the greybox; game code deletes the panel to open it
          - window (sill>0) -> NOT a void: the wall stays solid behind the
                              (visually cut) window. Vaulting through is game code.
        Each opening also gets a lintel above and, when sill>0, a sill wall
        below. Handles multiple openings on one wall (e.g. two front doors, or a
        door + a breach) -- the previous version only resolved the first one,
        which left every other opening as a dead hole you couldn't pass.
        """
        full = size[0] if axis == 0 else size[1]
        thick_idx = 1 if axis == 0 else 0
        thick = size[thick_idx]
        cz = center[2]
        H = size[2]
        ft = self.s.floor_thick

        # Only doors/garages/breaches/vaults carve the wall. Windows stay solid.
        carve = sorted((h for h in holes
                        if h["kind"] in ("door", "garage", "breach", "vault")),
                       key=lambda h: h["u"])
        if not carve:
            self._col_box(name, center, size)
            return

        def box(suffix, cu, clen, vcz=None, vh=None, mode_col=True, visual=False):
            """One axis-aligned chunk. cu/clen run along the wall axis;
            vcz/vh override the vertical centre/height (default: full height)."""
            if clen <= 0.05:
                return
            zc = cz if vcz is None else vcz
            zh = size[2] if vh is None else vh
            if zh <= 0.05:
                return
            if axis == 0:
                c = (center[0] + cu, center[1], zc)
                sz = (clen, thick, zh)
            else:
                c = (center[0], center[1] + cu, zc)
                sz = (thick, clen, zh)
            if visual:
                self._box(f"{name}_{suffix}", c, sz, self.VISUAL)
            if mode_col:
                self._col_box(f"{name}_{suffix}", c, sz)

        # 1) full-height jambs in the gaps between (and flanking) openings
        cursor = -full / 2
        for i, h in enumerate(carve):
            left = h["u"] - h["w"] / 2
            box(f"jamb{i}", (cursor + left) / 2, left - cursor)
            cursor = max(cursor, h["u"] + h["w"] / 2)
        box("jambN", (cursor + full / 2) / 2, full / 2 - cursor)

        # 2) per-opening sill (below), lintel (above), and breach panel (fill)
        wall_bottom = cz - H / 2
        wall_top = cz + H / 2
        for i, h in enumerate(carve):
            u, w, hh, sill = h["u"], h["w"], h["h"], h["sill"]
            open_bottom = wall_bottom + ft / 2 + sill
            open_top = open_bottom + hh
            if sill > 0.05:
                sill_h = open_bottom - wall_bottom
                box(f"sill{i}", u, w, vcz=wall_bottom + sill_h / 2, vh=sill_h)
            lintel_h = wall_top - open_top
            if lintel_h > 0.05:
                box(f"lintel{i}", u, w, vcz=open_top + lintel_h / 2, vh=lintel_h)
            if h["kind"] == "breach":
                box(f"BREACHPANEL{i}", u, w, vcz=(open_bottom + open_top) / 2,
                    vh=hh, mode_col=True, visual=True)
            elif h["kind"] == "vault":
                # default state is LOCKED (closed) -> a solid armored panel fills
                # the portal, like a breach panel. Zoo's vault_door art swaps in.
                box(f"VAULTDOOR{i}", u, w, vcz=(open_bottom + open_top) / 2,
                    vh=hh, mode_col=True, visual=True)

    # -- modular wall emitter ----------------------------------------------
    # Opt-in (_modular_on). Replaces the boolean _box_with_holes + chunked
    # _wall_collision pair: decompose a wall run into solid wall segments and
    # per-opening pieces, each its OWN named visual+collision object (a swap
    # slot for the art pass). See docs/WALL_SEGMENTATION.md + ASSET_SWAP_CONTRACT.md.
    @staticmethod
    def _slot_typename(role, size_mod):
        # size folded into the type token (naming law): a wall remainder is its
        # own type so a themed kit can author a dedicated end piece.
        if role == "wall":
            return "wallEnd" if size_mod == "end" else "wall"
        return role  # doorway / window / breach

    def _slot_orient(self, wall_name, axis):
        """Facing + Y-rotation (deg) that brings a canonically-authored module
        (along X) onto this wall, plus the story index parsed from the name.
        ext_{story}_{N|S|E|W}; int_{story}_{i} (partition -> axis-derived)."""
        parts = wall_name.split("_")
        if parts and parts[0] == "ext" and len(parts) >= 3:
            story = int(parts[1]) if parts[1].lstrip("-").isdigit() else None
            facing = parts[2]
            rot = {"N": 0, "E": 90, "S": 180, "W": 270}.get(facing, 0)
        elif parts and parts[0] == "int" and len(parts) >= 2:
            story = int(parts[1]) if parts[1].lstrip("-").isdigit() else None
            facing = "X" if axis == 0 else "Y"
            rot = 0 if axis == 0 else 90
        else:
            story = None
            facing = "X" if axis == 0 else "Y"
            rot = 0 if axis == 0 else 90
        return facing, rot, story

    def _record_wall_slot(self, vname, c, sz, axis, role, size_mod, ref=None):
        wall_name = vname.rsplit("_seg", 1)[0]
        facing, rot_y, story = self._slot_orient(wall_name, axis)
        typ = self._slot_typename(role, size_mod)
        dims = [round(sz[0], 4), round(sz[1], 4), round(sz[2], 4)]
        # Greybox wall REMAINDERS (wallEnd) come in many sizes but share one
        # ref -- a single fixed mesh can't fill them. They are plain solid
        # filler (no opening, never themed), so the module is authored as a
        # UNIT box and the size rides as a per-slot scale: one module fits every
        # remainder. Full-width walls and openings stay exact-fit (scale 1) so
        # themed art is never stretched. (Verified in-engine: unit box * fit.dims
        # reproduces the baked shell 1:1.)
        scale = dims[:] if size_mod == "end" else [1.0, 1.0, 1.0]
        self.slots.append({
            "slot_id": vname, "role": role, "size_mod": size_mod, "style": 1,
            "current_ref": ref or f"{typ}_greybox_01", "kit_axis": "theme",
            "wall": wall_name, "story": story, "facing": facing,
            "transform": {"translation": [round(c[0], 4), round(c[1], 4),
                                          round(c[2], 4)],
                          "rot_y": rot_y, "scale": scale},
            "fit": {"dims": dims,
                    "pivot": "center", "openings": [], "collision": "convex"},
        })

    def _record_opening_slot(self, vb, center, size, axis, h, ref=None):
        """One slot for the WHOLE opening (the swap unit), carrying aperture
        dims so a themed doorway/window prefab can replace its frame 1:1."""
        facing, rot_y, story = self._slot_orient(vb, axis)
        kind = h["kind"]
        role = {"door": "doorway", "garage": "doorway", "window": "window",
                "breach": "breach", "vault": "vault_door",
                "teller": "teller_line", "safe_deposit": "safe_deposit_boxes"}.get(kind, "doorway")
        u, w, hh, sill = h["u"], h["w"], h["h"], h["sill"]
        if axis == 0:
            oc = (center[0] + u, center[1], center[2])
            wall_thick = size[1]
        else:
            oc = (center[0], center[1] + u, center[2])
            wall_thick = size[0]
        slot = {
            "slot_id": vb, "role": role, "size_mod": "full", "style": 1,
            "current_ref": ref or f"{role}_greybox_01", "kit_axis": "theme",
            "wall": vb.rsplit("_open", 1)[0], "story": story, "facing": facing,
            "transform": {"translation": [round(oc[0], 4), round(oc[1], 4),
                                          round(oc[2], 4)],
                          "rot_y": rot_y, "scale": [1.0, 1.0, 1.0]},
            "fit": {"dims": [round(w, 4), round(wall_thick, 4),
                             round(size[2], 4)],
                    "pivot": "center",
                    "openings": [{"kind": kind, "width": round(w, 4),
                                  "height": round(hh, 4), "sill": round(sill, 4)}],
                    "collision": "convex"},
        }
        # if this opening is an interactive fixture (door / breachable wall /
        # breakable window), carry the art-facing state-machine block so Zoo
        # builds a per-state art variant. Same id as the gameplay entry.
        machine = h.get("interactive")
        if machine:
            slot["interactive"] = interactives.slot_interactive(machine)
        self.slots.append(slot)

    def _seg_box(self, vname, cname, center, size, axis, cu, clen, vcz, vh,
                 role=None, visual=True, collide=True, material=None,
                 record_slot=True, size_mod="full"):
        """One axis-aligned wall chunk emitted as a matched visual+collision
        pair. cu = centre offset along the run axis; clen = length along the
        run; vcz/vh = vertical centre/height. Skips slivers."""
        if clen <= 0.05 or vh <= 0.05:
            return
        thick = size[1] if axis == 0 else size[0]
        if axis == 0:
            c = (center[0] + cu, center[1], vcz)
            sz = (clen, thick, vh)
        else:
            c = (center[0], center[1] + cu, vcz)
            sz = (thick, clen, vh)
        # Identical modules share one mesh: key by role + rounded dims (visual)
        # and rounded dims (collision). Repeated full-width wall modules collapse
        # to a single shared mesh; unique remainders / openings keep their own.
        dkey = (round(sz[0], 4), round(sz[1], 4), round(sz[2], 4))
        vkey = ("Vseg", role, dkey)
        ckey = ("Cseg", dkey)
        # RESOLVER FORK: if a module library is configured and a module exists for
        # this wall type (theme, then greybox), instance that authored module at
        # the slot transform instead of generating a box. Falls through to the
        # generated box when nothing resolves, so the art pass is progressive.
        if record_slot and role:
            typ = self._slot_typename(role, size_mod)
            resolved = self._resolve_module(typ, width=clen)
            if resolved:
                path, kit, stem = resolved
                wall_name = vname.rsplit("_seg", 1)[0]
                _, rot_y, _ = self._slot_orient(wall_name, axis)
                self._instance_module(path, vname, c, rot_y, role=role)
                self._record_wall_slot(vname, c, sz, axis, role, size_mod,
                                       ref=stem)
                self._cover(role, kit)
                return
        if visual:
            self._box(vname, c, sz, self.VISUAL, role=role, share_key=vkey)
        if collide:
            cob = self._col_box(cname, c, sz, share_key=ckey)
            if cob is not None:
                # record acoustic surface against the base name, matching the
                # convention _exterior already uses (suffix stripped on import).
                self._record_surface(cname, material)
        if record_slot and role:
            self._record_wall_slot(vname, c, sz, axis, role, size_mod)
            self._cover(role, "generated")

    def _wall_span(self, vbase, cbase, center, size, axis, a, b, k, material):
        """Emit a solid wall span between run-offsets a..b (from the wall
        centre) as one box, or — when a module size is set — a row of whole
        module tiles plus an end remainder. Returns the next segment index k."""
        L = b - a
        if L <= 0.05:
            return k
        H = size[2]
        cz = center[2]
        M = self._module_size()
        if M <= 0:                       # Phase A: one box per solid span
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, (a + b) / 2.0, L, cz, H, role="wall",
                          material=material, size_mod="span")
            return k + 1
        n = int((L + 1e-6) // M)         # whole modules
        x = a
        for _ in range(n):
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, x + M / 2.0, M, cz, H, role="wall",
                          material=material, size_mod="full")
            x += M
            k += 1
        rem = b - x
        if rem > 0.05:                   # end remainder (a 'wallEnd' partial)
            self._seg_box(f"{vbase}_seg{k}", f"{cbase}_seg{k}", center, size,
                          axis, x + rem / 2.0, rem, cz, H, role="wall",
                          material=material, size_mod="end")
            k += 1
        return k

    def _opening_piece(self, vbase, cbase, center, size, axis, h, j, material):
        """Emit the pieces belonging to ONE opening, grouped under
        {base}_open{j}: lintel above (all kinds), sill below (raised/window),
        and the aperture fill — door/garage = void (walkable), window = sealed
        pane, breach = removable panel. role -> surface_roles for the swap."""
        H = size[2]
        cz = center[2]
        ft = self.s.floor_thick
        u, w, hh, sill, kind = h["u"], h["w"], h["h"], h["sill"], h["kind"]
        wall_bottom = cz - H / 2.0
        wall_top = cz + H / 2.0
        open_bottom = wall_bottom + ft / 2.0 + sill
        open_top = open_bottom + hh
        vb, cb = f"{vbase}_open{j}", f"{cbase}_open{j}"
        role = {"door": "doorway", "garage": "doorway", "window": "window",
                "breach": "breach", "vault": "vault_door",
                "teller": "teller_line", "safe_deposit": "safe_deposit_boxes"}.get(kind, "doorway")
        # RESOLVER FORK: a themed opening module replaces the whole frame at once.
        resolved = self._resolve_module(role, width=w)
        if resolved:
            path, kit, stem = resolved
            _, rot_y, _ = self._slot_orient(vb, axis)
            if axis == 0:
                oc = (center[0] + u, center[1], center[2])
            else:
                oc = (center[0], center[1] + u, center[2])
            self._instance_module(path, vb, oc, rot_y, role=role)
            self._record_opening_slot(vb, center, size, axis, h, ref=stem)
            self._cover(role, kit)
            return
        # one swap slot for the whole opening (the frame pieces below are its
        # geometry, not separate slots).
        self._record_opening_slot(vb, center, size, axis, h)
        self._cover(role, "generated")

        lintel_h = wall_top - open_top
        if lintel_h > 0.05:
            self._seg_box(f"{vb}_lintel", f"{cb}_lintel", center, size, axis,
                          u, w, open_top + lintel_h / 2.0, lintel_h,
                          role=role, material=material, record_slot=False)
        if sill > 0.05:
            sill_h = open_bottom - wall_bottom
            self._seg_box(f"{vb}_sill", f"{cb}_sill", center, size, axis,
                          u, w, wall_bottom + sill_h / 2.0, sill_h,
                          role=role, material=material, record_slot=False)
        if kind == "window":
            # sealed pane: full-thickness solid so the shell stays as sealed as
            # the pre-modular wall (vaulting through is game code, unchanged).
            # A themed window prefab replaces this piece in the art pass.
            self._seg_box(f"{vb}_pane", f"{cb}_pane", center, size, axis,
                          u, w, (open_bottom + open_top) / 2.0, hh,
                          role="window", material=material, record_slot=False)
        elif kind == "breach":
            self._seg_box(f"{vb}_BREACHPANEL", f"{cb}_BREACHPANEL", center,
                          size, axis, u, w, (open_bottom + open_top) / 2.0, hh,
                          role="breach", material=material, record_slot=False)
        elif kind == "vault":
            # closed by default (locked) -> a solid armored panel fills the
            # portal, so the greybox reads shut and blocks. Zoo's vault_door
            # module swaps in; its open/breached states unseal it.
            self._seg_box(f"{vb}_VAULTDOOR", f"{cb}_VAULTDOOR", center,
                          size, axis, u, w, (open_bottom + open_top) / 2.0, hh,
                          role="vault_door", material=material,
                          record_slot=False)
        elif kind == "teller":
            # a solid barrier (counter + bulletproof glass) fills the span; the
            # shell stays sealed. Zoo's teller_line module swaps in.
            self._seg_box(f"{vb}_TELLERLINE", f"{cb}_TELLERLINE", center,
                          size, axis, u, w, (open_bottom + open_top) / 2.0, hh,
                          role="teller_line", material=material,
                          record_slot=False)
        elif kind == "safe_deposit":
            # a solid wall of deposit boxes fills the span. Zoo's
            # safe_deposit_boxes module swaps in.
            self._seg_box(f"{vb}_SAFEDEPOSIT", f"{cb}_SAFEDEPOSIT", center,
                          size, axis, u, w, (open_bottom + open_top) / 2.0, hh,
                          role="safe_deposit_boxes", material=material,
                          record_slot=False)
        # door / garage: aperture left void (walkable) -> nothing in the span

    def _emit_wall_run(self, vbase, cbase, center, size, axis, holes, material):
        """Walk the run left->right: solid spans become wall segment(s),
        each opening becomes its own piece. Every emitted object is a named
        visual+collision pair = an art-pass swap slot."""
        full = size[0] if axis == 0 else size[1]
        carve = sorted(holes, key=lambda hh: hh["u"])
        cursor = -full / 2.0
        k = 0
        for j, h in enumerate(carve):
            left = h["u"] - h["w"] / 2.0
            k = self._wall_span(vbase, cbase, center, size, axis,
                                cursor, left, k, material)
            self._opening_piece(vbase, cbase, center, size, axis, h, j, material)
            cursor = max(cursor, h["u"] + h["w"] / 2.0)
        self._wall_span(vbase, cbase, center, size, axis,
                        cursor, full / 2.0, k, material)

    # -- top-level build steps ---------------------------------------------
    def _vertex_nuance(self,
                       target_edge=0.6,   # ~grid; densify to roughly this edge
                       bevel_width=0.015,  # ~1.5cm hard-edge bevel
                       max_subdiv=4):      # safety clamp on subdivision cuts
        """OPTIONAL anti-flatness pass (--vertex-nuance). VISUAL ONLY — never
        touches COLLISION. For each visual mesh: apply its scale (so we work in
        real metres, dodging the non-uniform-scale UV/texel trap), densify to
        ~target_edge so vertex color has resolution, bevel hard edges so light
        catches, then bake procedural vertex colors derived purely from
        geometry (deterministic — preserves byte-identical output):
          - fake AO: darken by local concavity (approx via vertex normal vs
            face spread) and by proximity to the mesh's lower/inner extents
          - height grime: subtle darkening near the floor (low local z)
          - per-normal tint: floor / wall / ceiling get distinct base tints
        Readability, not beauty. Needs a vertex-color-reading material in Godot
        (StandardMaterial3D.vertex_color_use_as_albedo) to display.
        """
        import mathutils  # noqa: F401  (Blender-only; available at runtime)

        FLOOR_TINT = (0.62, 0.60, 0.58)
        WALL_TINT = (0.74, 0.74, 0.76)
        CEIL_TINT = (0.68, 0.68, 0.70)
        AO_STRENGTH = 0.45
        GRIME_HEIGHT = 0.6   # metres above local floor where grime fades out
        GRIME_STRENGTH = 0.25

        # iterate a snapshot — we don't add/remove objects, just edit meshes
        for obj in list(self.VISUAL.objects):
            if obj.type != 'MESH' or obj.data is None:
                continue
            mesh = obj.data

            # 1) bake scale into the mesh so all geometry math is in real metres
            sx, sy, sz = obj.scale
            if (sx, sy, sz) != (1.0, 1.0, 1.0):
                for v in mesh.vertices:
                    v.co.x *= sx
                    v.co.y *= sy
                    v.co.z *= sz
                obj.scale = (1.0, 1.0, 1.0)

            bm = bmesh.new()
            bm.from_mesh(mesh)

            # 2) densify: subdivide edges longer than target_edge, clamped
            for _ in range(max_subdiv):
                long_edges = [e for e in bm.edges
                              if e.calc_length() > target_edge * 1.5]
                if not long_edges:
                    break
                bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1,
                                          use_grid_fill=False)
                bm.normal_update()

            # 3) bevel hard edges (visual only). Small width; clamp prevents
            # self-intersection on thin boxes.
            hard = [e for e in bm.edges if e.is_contiguous and len(e.link_faces) == 2]
            if hard and bevel_width > 0:
                try:
                    bmesh.ops.bevel(bm, geom=hard, offset=bevel_width,
                                    affect='EDGES', segments=1, clamp_overlap=True)
                except TypeError:
                    # older bmesh.ops.bevel signature fallback
                    bmesh.ops.bevel(bm, geom=hard, offset=bevel_width,
                                    segments=1, clamp_overlap=True)
            bm.normal_update()

            # base tint: prefer the AUTHORITATIVE role recorded at build time
            # (slab->floor/ceiling, walls, etc.) over guessing from the normal.
            # Per-object role, with a per-face normal fallback for meshes that
            # carry no role (or mixed-orientation faces).
            obj_role = getattr(self, "surface_roles", {}).get(obj.name)
            role_tint = {
                "floor": FLOOR_TINT, "ceiling": CEIL_TINT, "wall": WALL_TINT,
                "stair": FLOOR_TINT, "ramp": FLOOR_TINT, "ladder": WALL_TINT,
                "prop": WALL_TINT,
            }

            # local z-extent for the height-grime gradient
            zs = [v.co.z for v in bm.verts]
            zmin = min(zs) if zs else 0.0

            # 4) vertex colors — bmesh color layer
            color_layer = (bm.loops.layers.color.get("Col")
                           or bm.loops.layers.color.new("Col"))
            for face in bm.faces:
                if obj_role in role_tint:
                    base = role_tint[obj_role]
                else:
                    # no authoritative role — fall back to normal-based guess
                    n = face.normal
                    if n.z > 0.7:
                        base = FLOOR_TINT
                    elif n.z < -0.7:
                        base = CEIL_TINT
                    else:
                        base = WALL_TINT
                for loop in face.loops:
                    v = loop.vert
                    # fake AO: concave/edge vertices (many linked faces, normal
                    # divergence) darker. Approx: more linked faces -> deeper.
                    valence = len(v.link_faces)
                    ao = 1.0 - min(AO_STRENGTH, max(0.0, (valence - 4) * 0.06))
                    # height grime near floor
                    h = v.co.z - zmin
                    grime = 1.0 - (GRIME_STRENGTH * max(0.0, 1.0 - h / GRIME_HEIGHT))
                    shade = ao * grime
                    loop[color_layer] = (base[0] * shade, base[1] * shade,
                                         base[2] * shade, 1.0)

            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

    def build(self):
        self._clear()
        self.VISUAL = self._col("VISUAL")
        self.COLLISION = self._col("COLLISION")
        self.MARKERS = self._col("MARKERS")
        self.surface_roles = {}   # node name -> authoritative surface role
        self.slots = []           # art-pass swap slots (one per swappable module)
        self._coverage = {}       # (role, kit|'generated') -> count, for intel
        self.gameplay = {"mode": self.s.mode, "markers": [], "rooms": [],
                         "vertical_links": [], "openings": [],
                         "objectives": [], "loot": [], "zones": [],
                         "materials": [], "surfaces": [], "interactives": [],
                         "stair_systems": [], "ladders": []}
        # OPTIONAL building rarity: resolve once, expose as the single source of
        # truth on the gameplay.json top level. None when unset (no rarity).
        # _record_openings stamps the same colour onto each breachable door so a
        # networked door can pop it on open. resolve_rarity raises on a bad tier
        # -> a typo fails the build instead of shipping an uncolourable building.
        self.rarity_info = resolve_rarity(self.s.rarity)
        self.gameplay["rarity"] = self.s.rarity
        self.gameplay["rarity_color"] = self.rarity_info
        if getattr(self.s, "facade", False):
            # FACADE shell: exterior + roof + theme only. No interior, no
            # gameplay -- a non-enterable filler you reuse and art-pass later.
            self._slabs()
            self._exterior()
            self._parapets()
            self._materials()
            self._scale_ref()
            print(f"[deli_counter] built FACADE '{self.s.name}': "
                  f"{len(self.VISUAL.objects)} visual, "
                  f"{len(self.COLLISION.objects)} collision (shell only)")
            return
        self._slabs()
        self._exterior()
        self._partitions()
        self._stairs()
        self._ladders()
        self._ramps()
        self._vault_ledges()
        self._platforms()
        self._vertical_links()
        self._slab_holes_cut()
        self._volumes()
        self._placements()
        self._parapets()
        self._rooms()
        self._stair_semantics()
        self._ladder_semantics()
        self._markers()
        self._heist()
        self._materials()
        self._scale_ref()
        if getattr(self.s, "vertex_nuance", False):
            self._vertex_nuance()
        print(f"[deli_counter] built '{self.s.name}' seed={self.s.seed}: "
              f"{len(self.VISUAL.objects)} visual, "
              f"{len(self.COLLISION.objects)} collision, "
              f"{len(self.MARKERS.objects)} markers")

    def _story_range(self):
        base = -1 if self.s.has_basement else 0
        return base, self.s.n_stories

    def _slabs(self):
        base, top = self._story_range()
        for s in range(base, top + 1):
            is_roof = (s == top)
            # roof uses roof_thick (defaults to floor_thick); interior floors
            # always use floor_thick.
            ft = (self.s.roof_thick or self.s.floor_thick) if is_roof \
                else self.s.floor_thick
            z = s * self.s.story_height
            # roof=="none" drops the top cap entirely (no visual, no collision).
            if is_roof and self.s.roof == "none":
                continue
            # a slab's top face is the floor of story s; the topmost slab caps
            # the building (roof) and reads as a ceiling/roof surface.
            role = "ceiling" if is_roof else "floor"
            # VISUAL: skip only the roof mesh when authoring open-top; the
            # collision below is unaffected, so grenades/projectiles still bounce.
            if not (is_roof and self.s.roof == "open"):
                self._box(f"slab_{s}", (0, 0, z - ft / 2),
                          (self.s.footprint_x, self.s.footprint_y, ft),
                          self.VISUAL, role=role)
            # Slabs use TRIMESH collision regardless of the spec default, which
            # is convex. Stairwells, ramps, and hatches boolean-cut holes in the
            # slab; a CONVEX hull fills any hole straight back in, capping the
            # opening with invisible collision (you see the gap but can't pass).
            # A flat slab as trimesh is cheap and is the only shape that keeps
            # the hole. The roof keeps collision even when its visual is hidden.
            self._col_box(f"slab_col_{s}", (0, 0, z - ft / 2),
                          (self.s.footprint_x, self.s.footprint_y, ft),
                          mode="trimesh")
            # ALWAYS emit the roof as an art-pass swap-slot (when modular) so
            # Zoo can dress it -- present even in "open" mode, since the slot is
            # the always-there hook that lets a roof be added after the fun test.
            if is_roof and self._modular_on():
                self._record_roof_slots(top, z - ft / 2, ft)

    def _record_roof_slots(self, story, cz, ft):
        """Emit the roof swap-slots (see roofs.roof_slots -- pure & tested) so
        Zoo can dress the roof. footprint = one slot; per_room = one per
        top-story room honoring Room.roofed."""
        self.slots.extend(roofs.roof_slots(self.s, story, cz, ft))

    def _exterior(self):
        base, top = self._story_range()
        hx, hy = self.s.footprint_x / 2, self.s.footprint_y / 2
        H, wt = self.s.story_height, self.s.wall_thick
        # index explicit ext walls by (wall, story)
        explicit = {(w.wall, w.story): w for w in self.s.ext_walls}
        for s in range(base, top):
            z = s * H
            cz = z + H / 2
            wall_geo = {
                "N": ((0, hy, cz), (self.s.footprint_x, wt, H), 0),
                "S": ((0, -hy, cz), (self.s.footprint_x, wt, H), 0),
                "E": ((hx, 0, cz), (wt, self.s.footprint_y, H), 1),
                "W": ((-hx, 0, cz), (wt, self.s.footprint_y, H), 1),
            }
            for wname, (c, size, axis) in wall_geo.items():
                spec_w = explicit.get((wname, s))
                if spec_w is None and not self.s.auto_exterior:
                    continue
                run = size[0] if axis == 0 else size[1]
                holes = []
                if spec_w:
                    holes = [self._opening_to_hole(op, run, f"ext_{s}_{wname}", s)
                             for op in spec_w.openings]
                    self._record_openings(spec_w.openings, c, axis, run,
                                          f"ext_{s}_{wname}", s)
                name = f"ext_{s}_{wname}"
                col_name = f"ext_col_{s}_{wname}"
                mat = spec_w.material if spec_w else None
                if self._modular_on():
                    self._emit_wall_run(name, col_name, c, size, axis, holes, mat)
                else:
                    self._box_with_holes(name, c, size, holes, self.VISUAL)
                    if holes:
                        self._wall_collision(col_name, c, size, axis, holes)
                    else:
                        self._col_box(col_name, c, size)
                    self._record_surface(col_name, mat)

    def _record_openings(self, openings, wall_center, axis, run, wall_name, story):
        """Capture tactical opening metadata (tag/breach_class/material/etc.)
        into gameplay.json, with the opening's world position. Also emits a
        DOOR_SOCKET / BREACH_PANEL marker empty when tactical tags are present
        so Godot can replace baked openings with reusable scenes, and one
        INTERACTIVES entry (the replicable state machine) per interactive
        opening -- see interactives.py + docs/INTERACTIVES.md."""
        H = self.s.story_height
        _facing, wall_rot, _st = self._slot_orient(wall_name, axis)
        # slot_ref must match the modular pass's slot id: _emit_wall_run walks
        # openings sorted by their run-position u, naming each {wall}_open{k}.
        # Reproduce that order here so a gameplay entry points at its slot.
        order = sorted(range(len(openings)),
                       key=lambda idx: self.snap(openings[idx].pos * run))
        slot_index = {orig: k for k, orig in enumerate(order)}
        for j, op in enumerate(openings):
            r = op.resolved()
            u = op.pos * run
            cz = wall_center[2] - H / 2 + r["sill"] + r["height"] / 2 \
                + self.s.floor_thick / 2
            if axis == 0:
                wx, wy = wall_center[0] + u, wall_center[1]
            else:
                wx, wy = wall_center[0], wall_center[1] + u
            has_meta = any([op.tag, op.breach_class, op.material,
                            op.vaultable, op.reinforceable])
            entry = {
                "wall": wall_name, "kind": op.kind, "story": story,
                "x": round(wx, 3), "y": round(wy, 3), "z": round(cz, 3),
                "width": r["width"], "height": r["height"], "sill": r["sill"],
                "tag": op.tag, "breach_class": op.breach_class,
                "material": op.material, "vaultable": bool(op.vaultable),
                "reinforceable": bool(op.reinforceable),
            }
            # building_id on every opening so any entry point resolves to its
            # building (uniform with Lot compounds, where openings carry the
            # building id). For a single DC build this is the level name.
            entry["building"] = self.s.name
            # If the building has a rarity, stamp the tier + its canonical colour
            # onto EVERY opening. The design counts a door / window / breach as a
            # valid entry attempt, so any of them must resolve to the building's
            # rarity -- the kit doesn't pre-judge which openings the game treats
            # as entries. (A window carrying a rarity does NOT make it glow on the
            # curb; the reveal only fires when the game registers an entry. The
            # game reads opening.rarity_color or the socket-anchor meta below.)
            if self.rarity_info:
                entry["rarity"] = self.rarity_info["tier"]
                entry["rarity_color"] = self.rarity_info
            self.gameplay["openings"].append(entry)
            # socket markers for door/breach so Godot can swap in scenes
            if op.kind == "door":
                nm = f"DOOR_SOCKET_{wall_name}_{j}".upper()
                sock = self._empty(nm, (wx, wy, cz), self.MARKERS)
                self._tag_rarity_anchor(sock)
            elif op.kind == "breach":
                nm = f"BREACH_PANEL_{wall_name}_{j}".upper()
                sock = self._empty(nm, (wx, wy, cz), self.MARKERS)
                self._tag_rarity_anchor(sock)
            elif op.kind == "vault":
                nm = f"VAULT_DOOR_{wall_name}_{j}".upper()
                sock = self._empty(nm, (wx, wy, cz), self.MARKERS)
                self._tag_rarity_anchor(sock)
            elif op.kind == "teller":
                nm = f"TELLER_LINE_{wall_name}_{j}".upper()
                sock = self._empty(nm, (wx, wy, cz), self.MARKERS)
                self._tag_rarity_anchor(sock)
            elif op.kind == "safe_deposit":
                nm = f"SAFE_DEPOSIT_{wall_name}_{j}".upper()
                sock = self._empty(nm, (wx, wy, cz), self.MARKERS)
                self._tag_rarity_anchor(sock)

            # INTERACTIVE fixture: the replicable state machine for a door /
            # breachable wall / breakable window. slot_ref points at the modular
            # slot (same {wall}_open{k} the geometry pass names); id matches the
            # slots.json interactive block. Netcode owns replication; this is
            # network-solution agnostic (state, not synchronization).
            machine = self._machine_for(op, wall_name, story)
            if machine:
                slot_ref = f"{wall_name}_open{slot_index[j]}"
                self.gameplay["interactives"].append(
                    interactives.gameplay_interactive(
                        machine, slot_ref,
                        {"translation": [round(wx, 3), round(wy, 3),
                                         round(cz, 3)], "rot_y": wall_rot},
                        building=self.s.name))

    def _tag_rarity_anchor(self, obj):
        """Tag a door/breach socket Empty with its building (and rarity, if any)
        as custom properties, which export to glTF node `extras` -> Godot node
        metadata. The building tag is always written (server-authoritative
        is_revealed keys on building_id); the rarity props only when the building
        has a rarity. Lets a networked door scene instanced AT this socket resolve
        its building and pop the colour locally, without joining back to the
        building root. gameplay.json stays authoritative; this is convenience."""
        obj["building"] = self.s.name
        if not self.rarity_info:
            return
        obj["rarity"] = self.rarity_info["tier"]
        obj["rarity_color_hex"] = self.rarity_info["hex"]
        obj["rarity_rgb"] = self.rarity_info["rgb"]

    def _partitions(self):
        H, wt = self.s.story_height, self.s.wall_thick
        for i, p in enumerate(self.s.partitions):
            z = p.story * H
            cz = z + H / 2
            length = abs(p.end - p.start)
            mid = (p.start + p.end) / 2
            if p.axis == "Y":
                c = (p.pos, mid, cz)
                size = (wt, length, H)
                axis = 1
            else:
                c = (mid, p.pos, cz)
                size = (length, wt, H)
                axis = 0
            holes = [self._opening_to_hole(op, length, f"int_{p.story}_{i}",
                                           p.story) for op in p.openings]
            self._record_openings(p.openings, c, axis, length,
                                  f"int_{p.story}_{i}", p.story)
            name = f"int_{p.story}_{i}"
            col_name = f"int_col_{p.story}_{i}"
            if self._modular_on():
                self._emit_wall_run(name, col_name, c, size, axis, holes, p.material)
            else:
                self._box_with_holes(name, c, size, holes, self.VISUAL)
                if holes:
                    self._wall_collision(col_name, c, size, axis, holes)
                else:
                    self._col_box(col_name, c, size)
                self._record_surface(col_name, p.material)

    # ---- stair local-frame helpers (facing rotation, 90-degree steps) ----
    # Stairs are authored in a LOCAL frame -- ascent along +Y, parallel-run
    # offsets along +/-X -- and rotated about the anchor (x, y) by `facing` at
    # emission. "N" is the identity (the pre-0.68 convention), so every
    # existing spec bakes byte-identical geometry.

    def _stair_pt(self, st, lx, ly):
        dx, dy = lx - st.x, ly - st.y
        f = st.facing
        if f == "S":
            dx, dy = -dx, -dy
        elif f == "E":
            dx, dy = dy, -dx
        elif f == "W":
            dx, dy = -dy, dx
        return st.x + dx, st.y + dy

    def _stair_sz(self, st, sx_, sy_, sz_):
        return (sy_, sx_, sz_) if st.facing in ("E", "W") else (sx_, sy_, sz_)

    def _stair_tilt(self, st, sign, angle):
        """Ramp euler for a flight ascending local +/-Y (sign) under facing."""
        f = st.facing
        if f == "N":
            return (sign * angle, 0.0, 0.0)
        if f == "S":
            return (-sign * angle, 0.0, 0.0)
        if f == "E":
            return (0.0, -sign * angle, 0.0)
        return (0.0, sign * angle, 0.0)

    def _stair_tilt_x(self, st, angle):
        """Ramp euler for a flight ascending local +X (the L's second leg)."""
        f = st.facing
        if f == "N":
            return (0.0, -angle, 0.0)
        if f == "S":
            return (0.0, angle, 0.0)
        if f == "E":
            return (-angle, 0.0, 0.0)
        return (angle, 0.0, 0.0)

    def _stair_hole(self, st, story, lx, ly, size_x, size_y):
        wx, wy = self._stair_pt(st, lx, ly)
        sx_, sy_, _ = self._stair_sz(st, size_x, size_y, 0)
        self.s.slab_holes.append(SlabHole(story=story, x=wx, y=wy,
                                          size_x=sx_, size_y=sy_))

    def _stairs(self):
        H = self.s.story_height
        for si, st in enumerate(self.s.stairs):
            if st.style == "spiral":
                self._stair_spiral(si, st, H)
                continue
            if st.style == "l_shaped":
                self._stair_l_shaped(si, st, H)
                continue
            # derive step count so rise stays near st.step_rise regardless of
            # floor height; explicit n_steps overrides. clamp to a sane range.
            n_steps = st.n_steps or max(6, min(40, round(H / st.step_rise)))
            step_d = st.run / n_steps
            step_h = H / n_steps
            # A switchback's reversed legs must sit in PARALLEL runs, offset
            # sideways by the stair width -- otherwise an up-leg and the next
            # (reversed) leg occupy the same footprint and their steps
            # interpenetrate into unwalkable smeared geometry. Straight stairs
            # keep a single run (no offset). A scissor (spec 6.4) is the same
            # two-channel shaft, but the channels are INDEPENDENT full-height
            # flights travelling in opposite directions every story.
            x_offset = 0.0 if st.style == "straight" else st.width / 2
            import math as _m
            length3d = _m.sqrt(st.run ** 2 + H ** 2)
            angle = _m.atan2(H, st.run)
            for s in range(st.from_story, st.to_story):
                z = s * H
                leg = s - st.from_story
                if st.style == "scissor":
                    flights = [(1, st.x - x_offset, "a"),
                               (-1, st.x + x_offset, "b")]
                else:
                    sign = 1 if (leg % 2 == 0 or st.style == "straight") else -1
                    # reversed legs shift to the parallel run beside the main one
                    flights = [(sign,
                                st.x + (x_offset if sign > 0 else -x_offset),
                                "")]
                for sign, sx, ch in flights:
                    for i in range(n_steps):
                        cz = z + step_h * (i + 0.5)
                        cy = st.y + sign * (step_d * (i + 0.5) - st.run / 2)
                        wx, wy = self._stair_pt(st, sx, cy)
                        self._box(f"stair{si}{ch}_{s}_{i}", (wx, wy, cz),
                                  self._stair_sz(st, st.width, step_d, step_h),
                                  self.VISUAL, role="stair")
                    # COLLISION is a single smooth ramp under the visual steps,
                    # NOT a box per step. Boxy per-step colliders catch a
                    # CharacterBody3D on every riser (you stick / have to
                    # jump); a flush incline at the flight's pitch lets any
                    # controller walk straight up with no step logic. Visual
                    # stays stepped. Sat half a step proud so its surface rides
                    # the step nosings.
                    wx, wy = self._stair_pt(st, sx, st.y)
                    ramp = self._box(
                        f"stair{si}{ch}ramp_{s}" + self.col_suffix["convex"],
                        (wx, wy, z + H / 2 + step_h / 2),
                        self._stair_sz(st, st.width, length3d, 0.25),
                        self.COLLISION)
                    ramp.rotation_euler = self._stair_tilt(st, sign, angle)
                # landing at the top of each leg (except the final one) bridges
                # this run to the parallel run the next leg starts from, so you
                # can turn the corner. Spans both runs in X, one step deep.
                if st.style == "switchback" and s < st.to_story - 1:
                    sign = 1 if (leg % 2 == 0) else -1
                    top_y = st.y + sign * (st.run / 2)
                    land_z = z + H - step_h / 2
                    land_w = st.width + 2 * x_offset      # covers both runs
                    wx, wy = self._stair_pt(st, st.x, top_y)
                    self._box(f"stair{si}_land_{s}", (wx, wy, land_z),
                              self._stair_sz(st, land_w, step_d * 1.4, step_h),
                              self.VISUAL, role="stair")
                    self._col_box(f"stair{si}col_land_{s}", (wx, wy, land_z),
                                  self._stair_sz(st, land_w, step_d * 1.4,
                                                 step_h))
                if st.style == "scissor":
                    # thin divider between the channels: scissor flights are
                    # SEPARATED routes sharing a shaft, not one wide stair.
                    wx, wy = self._stair_pt(st, st.x, st.y)
                    self._box(f"stair{si}_divider_{s}", (wx, wy, z + H / 2),
                              self._stair_sz(st, 0.1, st.run, H),
                              self.VISUAL, role="stair")
                    self._col_box(f"stair{si}col_divider_{s}",
                                  (wx, wy, z + H / 2),
                                  self._stair_sz(st, 0.1, st.run, H))
                if st.cut_slabs:
                    # The slab hole must clear the *top* of the flight plus the
                    # player's body so you can walk off onto the landing, not
                    # just the stair footprint. The top step sits at
                    # st.y + sign*(run/2); extend the hole ~0.8 m past it in
                    # the travel direction (player radius + margin), and pad
                    # the near side and width a bit too. Widened in X to cover
                    # both parallel runs + the landing. A scissor tops out at
                    # BOTH ends, so its hole is symmetric.
                    clear = 0.8
                    hole_w = st.width + 2 * x_offset + 0.8
                    if st.style == "scissor":
                        self._stair_hole(st, s + 1, st.x, st.y,
                                         hole_w, st.run + 2 * clear)
                    else:
                        near = st.run / 2 + 0.3    # behind the bottom step
                        far = st.run / 2 + clear   # past the top landing
                        hole_y = st.y + sign * (far - near) / 2
                        self._stair_hole(st, s + 1, st.x, hole_y,
                                         hole_w, far + near)

    def _stair_l_shaped(self, si, st, H):
        """L-shaped stair (spec 6.3): leg A ascends local +Y for half the
        rise, a corner landing turns 90 degrees, leg B ascends local +X to the
        floor above. Both legs reuse `run`, so the pitch is gentler than a
        switchback's -- the L is a lobby/corner stair, not a core stair. Each
        story repeats the same L; leg B discharges onto the floor plate."""
        import math as _m
        n = st.n_steps or max(6, min(40, round(H / st.step_rise)))
        half = max(1, n // 2)
        n2 = max(1, n - half)
        step_h = H / n
        dA, dB = st.run / half, st.run / n2
        w = st.width
        riseA = H * half / n
        yB = st.y + st.run / 2 + w / 2          # leg B's local row
        for s in range(st.from_story, st.to_story):
            z = s * H
            for i in range(half):               # leg A: local +Y
                cz = z + step_h * (i + 0.5)
                cy = st.y + dA * (i + 0.5) - st.run / 2
                wx, wy = self._stair_pt(st, st.x, cy)
                self._box(f"stair{si}a_{s}_{i}", (wx, wy, cz),
                          self._stair_sz(st, w, dA, step_h),
                          self.VISUAL, role="stair")
            lenA = _m.sqrt(st.run ** 2 + riseA ** 2)
            angA = _m.atan2(riseA, st.run)
            wx, wy = self._stair_pt(st, st.x, st.y)
            ramp = self._box(f"stair{si}aramp_{s}" + self.col_suffix["convex"],
                             (wx, wy, z + riseA / 2 + step_h / 2),
                             self._stair_sz(st, w, lenA, 0.25), self.COLLISION)
            ramp.rotation_euler = self._stair_tilt(st, 1, angA)
            # corner landing, flush with leg A's top
            land_z = z + riseA - step_h / 2
            wx, wy = self._stair_pt(st, st.x, yB)
            self._box(f"stair{si}_corner_{s}", (wx, wy, land_z),
                      self._stair_sz(st, w, w, step_h), self.VISUAL,
                      role="stair")
            self._col_box(f"stair{si}col_corner_{s}", (wx, wy, land_z),
                          self._stair_sz(st, w, w, step_h))
            for i in range(n2):                 # leg B: local +X
                cz = z + riseA + step_h * (i + 0.5)
                cx = st.x + w / 2 + dB * (i + 0.5)
                wx, wy = self._stair_pt(st, cx, yB)
                self._box(f"stair{si}b_{s}_{i}", (wx, wy, cz),
                          self._stair_sz(st, dB, w, step_h),
                          self.VISUAL, role="stair")
            riseB = H - riseA
            lenB = _m.sqrt(st.run ** 2 + riseB ** 2)
            angB = _m.atan2(riseB, st.run)
            wx, wy = self._stair_pt(st, st.x + w / 2 + st.run / 2, yB)
            ramp = self._box(f"stair{si}bramp_{s}" + self.col_suffix["convex"],
                             (wx, wy, z + riseA + riseB / 2 + step_h / 2),
                             self._stair_sz(st, lenB, w, 0.25), self.COLLISION)
            ramp.rotation_euler = self._stair_tilt_x(st, angB)
            if st.cut_slabs:
                # bounding hole over both legs + step-off past leg B's top
                lx0, lx1 = st.x - w / 2 - 0.3, st.x + w / 2 + st.run + 0.8
                ly0, ly1 = st.y - st.run / 2 - 0.3, st.y + st.run / 2 + w + 0.3
                self._stair_hole(st, s + 1, (lx0 + lx1) / 2, (ly0 + ly1) / 2,
                                 lx1 - lx0, ly1 - ly0)

    def _stair_spiral(self, si, st, H):
        """Spiral stair (spec 6.5): one revolution per story of wedge treads
        around a pole. `width` is the RADIUS. Decorative / private / service
        only -- the review hard-refuses an egress role on it. Collision is
        per-step boxes (a helix has no single flush ramp); a capsule catches
        on risers exactly as the ramp comment warns, which is acceptable for
        a stair the review already keeps off required routes."""
        import math as _m
        n = st.n_steps or max(10, min(24, round(H / st.step_rise)))
        step_h = H / n
        r = st.width
        tread = 2 * _m.pi * r / n * 1.15        # wedge chord + overlap
        stories = range(min(st.from_story, st.to_story),
                        max(st.from_story, st.to_story))
        for s in stories:
            z = s * H
            for i in range(n):
                a = 2 * _m.pi * (i + 0.5) / n
                cx = st.x + _m.cos(a) * r / 2
                cy = st.y + _m.sin(a) * r / 2
                cz = z + step_h * (i + 0.5)
                box = self._box(f"stair{si}_{s}_{i}", (cx, cy, cz),
                                (r, tread, step_h), self.VISUAL, role="stair")
                box.rotation_euler = (0.0, 0.0, a)
                col = self._col_box(f"stair{si}col_{s}_{i}", (cx, cy, cz),
                                    (r, tread, step_h))
                if col is not None:
                    col.rotation_euler = (0.0, 0.0, a)
            if st.cut_slabs:
                self.s.slab_holes.append(SlabHole(
                    story=s + 1, x=st.x, y=st.y,
                    size_x=2 * r + 0.5, size_y=2 * r + 0.5))
        n_st = max(st.from_story, st.to_story) - min(st.from_story, st.to_story)
        self._box(f"stair{si}_pole", (st.x, st.y,
                                      min(st.from_story, st.to_story) * H
                                      + n_st * H / 2),
                  (0.16, 0.16, n_st * H), self.VISUAL, role="stair")
        self._col_box(f"stair{si}col_pole", (st.x, st.y,
                                             min(st.from_story, st.to_story)
                                             * H + n_st * H / 2),
                      (0.16, 0.16, n_st * H))

    def _ladders(self):
        """Vertical climb: rungs + two side rails (VISUAL), climbing one floor
        per story in the range. Cuts the slab it passes through, and emits a
        climb-volume anchor (LADDER_ marker + meta) the post-import turns into an
        Area3D. The geometry is visual-only: a solid rung catches a capsule on
        the way up exactly like a boxy stair riser, so traversal is the climb
        volume's job, not the mesh's (the game/harness owns the climb mechanic)."""
        H = self.s.story_height
        for li, ld in enumerate(self.s.ladders):
            along_x = ld.facing in ("N", "S")   # rails spread along X if facing N/S
            n_rungs_per_floor = max(3, round(H / ld.rung_spacing))
            for s in range(ld.from_story, ld.to_story):
                z = s * H
                # side rails (two thin vertical posts) -- VISUAL only.
                half = ld.width / 2
                for sgn in (-1, 1):
                    if along_x:
                        rc = (ld.x + sgn * half, ld.y, z + H / 2)
                        rs = (0.06, ld.depth, H)
                    else:
                        rc = (ld.x, ld.y + sgn * half, z + H / 2)
                        rs = (ld.depth, 0.06, H)
                    self._box(f"ladder{li}_rail_{s}_{sgn}", rc, rs, self.VISUAL,
                              role="ladder")
                # rungs -- VISUAL only (no collision; the climb is volume-driven).
                for r in range(n_rungs_per_floor):
                    rz = z + ld.rung_spacing * (r + 0.5)
                    if rz >= z + H:
                        break
                    if along_x:
                        cc, cs = (ld.x, ld.y, rz), (ld.width, ld.depth, 0.05)
                    else:
                        cc, cs = (ld.x, ld.y, rz), (ld.depth, ld.width, 0.05)
                    self._box(f"ladder{li}_rung_{s}_{r}", cc, cs, self.VISUAL,
                              role="ladder")
                if ld.cut_slabs:
                    self.s.slab_holes.append(SlabHole(
                        story=s + 1, x=ld.x, y=ld.y,
                        size_x=ld.width + 0.6, size_y=ld.width + 0.6))
            # climb-volume anchor: the marker + the climb metadata the post-import
            # needs to build an Area3D the player climbs (height, footprint, facing).
            zc = ld.from_story * H
            self._empty(f"LADDER_{li}", (ld.x, ld.y, zc), self.MARKERS)
            self.gameplay["markers"].append({
                "name": f"LADDER_{li}", "type": "ladder", "id": f"ladder_{li}",
                "x": ld.x, "y": ld.y, "z": zc,
                "climb_height": (ld.to_story - ld.from_story) * H,
                "width": ld.width, "depth": ld.depth, "facing": ld.facing,
            })

    def _ramps(self):
        """Inclined walkable slab between two heights. Flagged steep ramps are
        still built; validate.py warns. Cuts the slab at the top story."""
        H = self.s.story_height
        for ri, rp in enumerate(self.s.ramps):
            dz = (rp.to_story - rp.from_story) * H
            z0 = rp.from_story * H
            # single inclined box: model as a thin slab rotated about its axis
            import math as _m
            length3d = _m.sqrt(rp.run ** 2 + dz ** 2)
            angle = _m.atan2(dz, rp.run)
            cx, cy = rp.x, rp.y
            cz = z0 + dz / 2
            obj = self._box(f"ramp{ri}", (cx, cy, cz),
                            (rp.width if rp.axis == "Y" else length3d,
                             length3d if rp.axis == "Y" else rp.width,
                             rp.thickness), self.VISUAL, role="ramp")
            # tilt about the horizontal axis perpendicular to ascent
            if rp.axis == "Y":
                obj.rotation_euler = (angle, 0.0, 0.0)
            else:
                obj.rotation_euler = (0.0, -angle, 0.0)
            colobj = self._box(f"ramp{ri}_col" + self.col_suffix["convex"],
                               (cx, cy, cz),
                               (rp.width if rp.axis == "Y" else length3d,
                                length3d if rp.axis == "Y" else rp.width,
                                rp.thickness), self.COLLISION)
            colobj.rotation_euler = obj.rotation_euler
            if rp.cut_slabs and rp.to_story > rp.from_story:
                self.s.slab_holes.append(SlabHole(
                    story=rp.to_story, x=rp.x,
                    y=rp.y + (rp.run / 2 if rp.axis == "Y" else 0),
                    size_x=rp.width + 0.4 if rp.axis == "Y" else rp.run,
                    size_y=rp.run if rp.axis == "Y" else rp.width + 0.4))

    def _vault_ledges(self):
        """Waist-height ledge you vault over within a floor. Solid box, tagged
        VAULTLEDGE so the game can mark sub-height collision as vaultable."""
        for vi, vl in enumerate(self.s.vault_ledges):
            z = vl.story * self.s.story_height + vl.height / 2
            if vl.axis == "X":
                size = (vl.length, vl.thick, vl.height)
            else:
                size = (vl.thick, vl.length, vl.height)
            name = f"VAULTLEDGE_{vi}"
            self._box(name, (vl.x, vl.y, z), size, self.VISUAL, role="floor")
            self._col_box(name, (vl.x, vl.y, z), size)
            self._record_surface(name + self.col_suffix["convex"], vl.material)

    def _platforms(self):
        """Elevated walkable deck (catwalk / equipment platform / rest
        platform) at an arbitrary absolute z, with guard rails on the named
        edges. The deck is walkable collision tagged PLATFORM_<id>; rails are
        waist-height cover boxes. Ladders reference the deck as a surface."""
        for p in self.s.platforms:
            zc = p.z - p.thick / 2       # deck box centered under the walk top
            name = f"PLATFORM_{p.id.upper()}"
            self._box(name, (p.x, p.y, zc),
                      (p.size_x, p.size_y, p.thick), self.VISUAL, role="floor")
            self._col_box(name, (p.x, p.y, zc),
                          (p.size_x, p.size_y, p.thick))
            self._record_surface(name + self.col_suffix["convex"], p.material)
            # guard rails on requested edges (Rule 7); waist-height thin boxes
            hx, hy = p.size_x / 2, p.size_y / 2
            gz = p.z + p.guard_height / 2
            rt = 0.05
            for edge in (p.guard_edges or []):
                if edge == "N":
                    c, s = (p.x, p.y + hy, gz), (p.size_x, rt, p.guard_height)
                elif edge == "S":
                    c, s = (p.x, p.y - hy, gz), (p.size_x, rt, p.guard_height)
                elif edge == "E":
                    c, s = (p.x + hx, p.y, gz), (rt, p.size_y, p.guard_height)
                elif edge == "W":
                    c, s = (p.x - hx, p.y, gz), (rt, p.size_y, p.guard_height)
                else:
                    continue
                rname = f"{name}_RAIL_{edge}"
                self._box(rname, c, s, self.VISUAL, role="floor")
                self._col_box(rname, c, s)
            # marker empty so the post-import can anchor the platform semantics
            self._empty(name, (p.x, p.y, p.z), self.MARKERS)

    def _slab_holes_cut(self):
        """Boolean-subtract holes from slabs (visual + collision)."""
        ft = self.s.floor_thick
        for hole in self.s.slab_holes:
            z = hole.story * self.s.story_height - ft / 2
            cutter_c = (hole.x, hole.y, z)
            cutter_s = (hole.size_x, hole.size_y, ft * 3)
            for coll, prefix in ((self.VISUAL, f"slab_{hole.story}"),
                                 (self.COLLISION, f"slab_col_{hole.story}")):
                target = None
                for o in coll.objects:
                    if o.name.startswith(prefix):
                        target = o
                        break
                if target is None:
                    continue
                cut = self._box(f"{prefix}_holecut", cutter_c, cutter_s, coll)
                m = target.modifiers.new(name="hole", type='BOOLEAN')
                m.operation = 'DIFFERENCE'
                m.object = cut
                m.solver = 'EXACT'
                bpy.context.view_layer.objects.active = target
                bpy.ops.object.modifier_apply(modifier=m.name)
                bpy.data.objects.remove(cut, do_unlink=True)

    def _volumes(self):
        for v in self.s.volumes:
            c = (v.x, v.y, v.z)
            size = (v.size_x, v.size_y, v.size_z)
            if v.visual:
                self._box(v.name, c, size, self.VISUAL, role="prop")
            if v.collision != "none":
                self._col_box(f"{v.name}_col", c, size, mode=v.collision)
                self._record_surface(f"{v.name}_col", v.material)

    # ----------------------------------------------------------------------
    # KITBASHING  --  import external models and place instances
    # ----------------------------------------------------------------------
    def _asset_path(self, asset, file=None):
        rel = file if file is not None else asset.file
        root = os.path.normpath(os.path.join(self.base_dir, self.s.assets_dir))
        return os.path.normpath(os.path.join(root, rel))

    def _import_asset_objects(self, asset):
        """Import an asset's geometry; return the newly added mesh objects.
        Importers append to the scene, so we diff object sets to find what
        arrived."""
        before = set(bpy.data.objects)
        path = self._asset_path(asset)
        if not os.path.exists(path):
            raise FileNotFoundError(f"asset '{asset.id}' missing file: {path}")

        if asset.fmt in ("glb", "gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif asset.fmt == "obj":
            bpy.ops.wm.obj_import(filepath=path)
        elif asset.fmt == "blend":
            with bpy.data.libraries.load(path, link=False) as (src, dst):
                if asset.blend_object and asset.blend_object in src.objects:
                    dst.objects = [asset.blend_object]
                else:
                    dst.objects = list(src.objects)
            for o in dst.objects:
                if o is not None:
                    bpy.context.scene.collection.objects.link(o)
        else:
            raise ValueError(f"unknown asset fmt: {asset.fmt}")

        return [o for o in bpy.data.objects if o not in before
                and o.type == 'MESH']

    def _join_objects(self, objs, name):
        if not objs:
            return None
        if len(objs) == 1:
            objs[0].name = name
            return objs[0]
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        joined = bpy.context.view_layer.objects.active
        joined.name = name
        return joined

    def _make_convex_hull(self, src_obj, name):
        """Convex-hull collision mesh from src_obj's world-space geometry."""
        me = bpy.data.meshes.new(name)
        hull_obj = bpy.data.objects.new(name, me)
        self.COLLISION.objects.link(hull_obj)
        bm = bmesh.new()
        bm.from_mesh(src_obj.data)
        bm.transform(src_obj.matrix_world)
        try:
            res = bmesh.ops.convex_hull(bm, input=bm.verts)
            bmesh.ops.delete(
                bm,
                geom=res.get("geom_unused", []) + res.get("geom_interior", []),
                context='VERTS',
            )
        except Exception:
            pass
        bm.to_mesh(me)
        bm.free()
        hull_obj.matrix_world.identity()
        return hull_obj

    def _make_box_bounds(self, src_obj, name):
        coords = [src_obj.matrix_world @ v.co for v in src_obj.data.vertices]
        if not coords:
            return None
        xs = [c.x for c in coords]; ys = [c.y for c in coords]; zs = [c.z for c in coords]
        cx, cy, cz = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2
        sx = max(max(xs)-min(xs), 1e-3)
        sy = max(max(ys)-min(ys), 1e-3)
        sz = max(max(zs)-min(zs), 1e-3)
        return self._box(name, (cx, cy, cz), (sx, sy, sz), self.COLLISION)

    def _apply_transform(self, obj, p):
        obj.location = (p.x, p.y, p.z)
        obj.rotation_euler = (math.radians(p.rot_x),
                              math.radians(p.rot_y),
                              math.radians(p.rot_z))
        if p.scale_xyz:
            obj.scale = tuple(p.scale_xyz)
        else:
            obj.scale = (p.scale, p.scale, p.scale)
        bpy.context.view_layer.update()

    def _import_collision_file(self, asset, base):
        before = set(bpy.data.objects)
        path = self._asset_path(asset, asset.collision_file)
        if not os.path.exists(path):
            raise FileNotFoundError(f"collision file missing: {path}")
        ext = os.path.splitext(path)[1].lower()
        if ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=path)
        else:
            raise ValueError(f"unsupported collision file: {ext}")
        return [o for o in bpy.data.objects if o not in before
                and o.type == 'MESH']

    def _placements(self):
        if not self.s.placements:
            return
        for i, p in enumerate(self.s.placements):
            asset = self._asset_index.get(p.asset)
            if asset is None:
                raise KeyError(f"placement #{i} references unknown asset "
                               f"id '{p.asset}'")
            base = p.name or f"{asset.id}_{i}"

            # Durable module reuse: import + join each asset ONCE, then link the
            # cached mesh datablock for every later placement (object carries only
            # its transform). The artist art-passes the source asset file; on the
            # next build DC re-imports it once and instances it N times -> the art
            # pass persists across regeneration and one mesh/texture lives in VRAM.
            akey = ("asset", asset.id)
            if akey in self._module_cache:
                visual = bpy.data.objects.new(base, self._module_cache[akey])
                self.VISUAL.objects.link(visual)
            else:
                imported = self._import_asset_objects(asset)
                visual = self._join_objects(imported, base)
                if visual is None:
                    continue
                for c in list(visual.users_collection):
                    c.objects.unlink(visual)
                self.VISUAL.objects.link(visual)
                self._module_cache[akey] = visual.data
            self._apply_transform(visual, p)

            pmode = p.collision or asset.collision
            # placements are already module references — record them as slots too
            # so the manifest is the WHOLE building (grey + kitbash), uniform.
            self.slots.append({
                "slot_id": base, "role": "prop", "size_mod": "full", "style": 1,
                "current_ref": asset.id, "kit_axis": "material",
                "wall": None, "story": None, "facing": None,
                "transform": {"translation": [round(p.x, 4), round(p.y, 4),
                                              round(p.z, 4)],
                              "rot_y": round(p.rot_z, 4),
                              "scale": list(p.scale_xyz) if p.scale_xyz
                                       else [p.scale, p.scale, p.scale]},
                "fit": {"dims": None, "pivot": "asset", "openings": [],
                        "collision": pmode},
            })

            mode = p.collision or asset.collision
            if mode == "none":
                continue
            elif mode == "convex":
                self._make_convex_hull(visual, base + self.col_suffix["convex"])
            elif mode == "box":
                bb = self._make_box_bounds(visual, base + "_bb")
                if bb:
                    bb.name = base + self.col_suffix["convex"]
            elif mode == "trimesh":
                col = visual.copy()
                col.data = visual.data.copy()
                col.name = base + self.col_suffix["trimesh"]
                self.COLLISION.objects.link(col)
            elif mode == "file":
                if not asset.collision_file:
                    raise ValueError(f"asset '{asset.id}' collision='file' "
                                     "but no collision_file given")
                cobjs = self._import_collision_file(asset, base)
                cj = self._join_objects(cobjs, base + self.col_suffix["convex"])
                if cj:
                    for c in list(cj.users_collection):
                        c.objects.unlink(cj)
                    self.COLLISION.objects.link(cj)
                    self._apply_transform(cj, p)

    # ----------------------------------------------------------------------
    # TACTICAL LAYER  --  vertical links, rooms, markers, gameplay.json
    # ----------------------------------------------------------------------
    def _vertical_links(self):
        """floor_hole / hatch links cut the slab (like slab_holes) and record
        gameplay intent. 'stair' links are descriptive only (geometry comes
        from the stairs section). All are written to gameplay.json."""
        for v in self.s.vertical_links:
            self.gameplay["vertical_links"].append({
                "kind": v.kind, "role": v.role,
                "from_story": v.from_story, "to_story": v.to_story,
                "story": v.story, "x": v.x, "y": v.y,
                "breachable": v.breachable,
            })
            if v.kind in ("floor_hole", "hatch") and v.cut_slab \
                    and v.story is not None and v.x is not None:
                sx = v.size_x or 1.5
                sy = v.size_y or 1.5
                self.s.slab_holes.append(SlabHole(
                    story=v.story, x=v.x, y=v.y, size_x=sx, size_y=sy))
            # a hatch is a breachable marker too
            if v.kind == "hatch" and v.x is not None:
                z = (v.story or 0) * self.s.story_height
                name = "HATCH_" + (f"{int(v.x)}_{int(v.y)}")
                self._empty(name, (v.x, v.y, z), self.MARKERS)
                self.gameplay["markers"].append({
                    "name": name, "type": "hatch",
                    "x": v.x, "y": v.y, "z": z,
                    "breachable": bool(v.breachable)})

    def _rooms(self):
        for r in self.s.rooms:
            minx, miny, maxx, maxy = r.bounds
            cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
            z = r.story * self.s.story_height
            name = "NAV_REGION_" + r.id.upper()
            self._empty(name, (cx, cy, z), self.MARKERS, size=0.6)
            self.gameplay["rooms"].append({
                "id": r.id, "story": r.story, "bounds": r.bounds,
                "role": r.role, "combat_range": r.combat_range,
                "fortifiable": bool(r.fortifiable),
                "objective": bool(r.objective or r.role == "objective_room"),
                "center": [cx, cy, z],
            })

    def _stair_semantics(self):
        """Derive the semantic stair systems (stairwell.py: role, stack, floors
        served, approach, discharge) into gameplay.json, plus a STAIRSYS_<ID>
        marker empty at each stair base so the post-import can anchor them.
        Geometry is untouched -- this is contract data over what _stairs baked."""
        import stairwell
        systems = stairwell.derive(self.s)
        self.gameplay["stair_systems"] = systems
        H = self.s.story_height
        for sysd, st in zip(systems, self.s.stairs):
            z = min(st.from_story, st.to_story) * H
            self._empty(f"STAIRSYS_{sysd['id'].upper()}",
                        (st.x, st.y, z), self.MARKERS)

    def _ladder_semantics(self):
        """Derive the semantic ladder systems (ladder.py: role, surfaces,
        anchors, transition, egress exclusion, route nodes) into gameplay.json,
        and drop mount/dismount empties the post-import anchors traversal to.
        Geometry (rails/rungs) is already baked by _ladders(); this is the
        contract over it."""
        import ladder as _lad
        systems = _lad.derive(self.s)
        self.gameplay["ladders"] = systems
        H = self.s.story_height
        for d, ld in zip(systems, self.s.ladders):
            z0 = min(ld.from_story, ld.to_story) * H
            z1 = max(ld.from_story, ld.to_story) * H
            self._empty(f"{d['id'].upper()}_MOUNT", (ld.x, ld.y, z0),
                        self.MARKERS)
            self._empty(f"{d['id'].upper()}_DISMOUNT", (ld.x, ld.y, z1),
                        self.MARKERS)

    def _markers(self):
        for m in self.s.markers:
            suffix = ("_" + m.id) if m.id else ""
            name = m.type.upper() + suffix
            self._empty(name, (m.x, m.y, m.z), self.MARKERS, rot_z=m.rot_z)
            entry = {"name": name, "type": m.type, "id": m.id,
                     "x": m.x, "y": m.y, "z": m.z, "rot_z": m.rot_z,
                     "room": m.room}
            if m.meta:
                entry["meta"] = m.meta
            self.gameplay["markers"].append(entry)

    # ----------------------------------------------------------------------
    # MATERIALS  --  acoustic palette + surface map for gool (no visual PBR)
    # ----------------------------------------------------------------------
    def _resolve_material(self, material_id):
        """Resolve a material id (or None) to an acoustic descriptor dict, or
        None if no material applies. Falls back to spec.default_material."""
        mid = material_id or self.s.default_material
        if not mid:
            return None
        m = self._material_index.get(mid)
        if m is None:
            return {"id": mid, "acoustic": None, "absorption": None,
                    "damping": None, "unresolved": True}
        return {"id": m.id, "acoustic": m.acoustic,
                "absorption": m.absorption, "damping": m.damping}

    def _record_surface(self, node_name, material_id):
        """Map a collision-node name to its acoustic material in gameplay.json.
        The game's audio raycaster reads the hit body's name, looks it up here,
        and hands the material to gool's IAudioGeometryQuery."""
        desc = self._resolve_material(material_id)
        if desc is None:
            return
        self.gameplay["surfaces"].append({"node": node_name, "material": desc})

    def _materials(self):
        """Emit the resolved palette into gameplay.json for reference."""
        for m in self.s.materials:
            self.gameplay["materials"].append({
                "id": m.id, "acoustic": m.acoustic,
                "absorption": m.absorption, "damping": m.damping})

    def _heist(self):
        """Emit heist-mode markers: objectives, loot, and zones. These are
        written regardless of mode (so a designer can mix), but the heist
        validation rules only fire when mode == 'heist'."""
        for o in self.s.objectives:
            name = f"OBJECTIVE_{o.id}".upper()
            self._empty(name, (o.x, o.y, o.z), self.MARKERS)
            self.gameplay["objectives"].append({
                "name": name, "id": o.id, "kind": o.kind,
                "x": o.x, "y": o.y, "z": o.z, "room": o.room,
                "required": bool(o.required), "duration": o.duration,
                "meta": o.meta})
        for l in self.s.loot:
            name = f"LOOT_{l.id}".upper()
            self._empty(name, (l.x, l.y, l.z), self.MARKERS)
            self.gameplay["loot"].append({
                "name": name, "id": l.id, "kind": l.kind,
                "x": l.x, "y": l.y, "z": l.z, "value": l.value,
                "bags": l.bags, "room": l.room, "meta": l.meta})
        for zn in self.s.zones:
            cx = (zn.bounds[0] + zn.bounds[2]) / 2 if zn.bounds else 0.0
            cy = (zn.bounds[1] + zn.bounds[3]) / 2 if zn.bounds else 0.0
            cz = zn.story * self.s.story_height
            name = f"{zn.kind.upper()}_ZONE_{zn.id}".upper()
            self._empty(name, (cx, cy, cz), self.MARKERS, size=0.8)
            self.gameplay["zones"].append({
                "name": name, "id": zn.id, "kind": zn.kind,
                "story": zn.story, "bounds": zn.bounds,
                "center": [cx, cy, cz], "meta": zn.meta})

    def _parapets(self):
        hx, hy = self.s.footprint_x / 2, self.s.footprint_y / 2
        for p in self.s.parapets:
            z = p.story * self.s.story_height
            cz = z + p.height / 2
            t = p.thick
            segs = [
                ("N", (0, hy - t / 2, cz), (self.s.footprint_x, t, p.height)),
                ("S", (0, -hy + t / 2, cz), (self.s.footprint_x, t, p.height)),
                ("E", (hx - t / 2, 0, cz), (t, self.s.footprint_y, p.height)),
                ("W", (-hx + t / 2, 0, cz), (t, self.s.footprint_y, p.height)),
            ]
            for n, c, size in segs:
                self._box(f"parapet_{n}", c, size, self.VISUAL, role="wall")
                self._col_box(f"parapet_{n}_col", c, size)


def build(spec: LevelSpec, base_dir: str = "."):
    """Public entry point. base_dir is the spec file's folder, used to
    resolve the vendored assets directory for kitbashing. Returns the builder
    so callers can read .gameplay (tactical companion data)."""
    b = _Builder(spec, base_dir=base_dir)
    b.build()
    return b


def write_slot_manifest(builder, path):
    """Write <name>.slots.json -- the art-pass input. One record per swappable
    module (wall segment / opening / placement): what kind it is, where it sits,
    and the fit a themed replacement must match (dims, pivot, openings,
    collision). Theme resolution + instancing consume this; the artist authors
    `<type>_<theme>_<style>.glb` files and the manifest pulls them in. Output-only
    -- no schema change. See docs/SLOT_MANIFEST.md."""
    import json
    data = {
        "slot_manifest_version": "1.2.0",
        "building_id": builder.s.name,
        "theme": getattr(builder.s, "theme", None) or "greybox",
        "module_library": getattr(builder.s, "module_library", None) or "art/zoo",
        "module_size": builder._module_size(),
        # transforms are raw spec/Blender space (Z-up), same as gameplay.json;
        # rot_y is degrees about up to orient a canonically-authored module.
        "space": "spec/Blender Z-up raw coords; rot_y = degrees about up",
        # art-pass coverage: per role/kit, how many slots resolved to a theme
        # module, a greybox module, or fell back to generated geometry.
        "coverage": {f"{r}/{k}": n
                     for (r, k), n in sorted(builder._coverage.items())},
        "slots": builder.slots,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    cov = ", ".join(f"{r}/{k}:{n}"
                    for (r, k), n in sorted(builder._coverage.items())) or "none"
    print(f"[deli_counter] slot manifest -> {path} "
          f"({len(builder.slots)} slots; coverage {cov})")
    return data


def write_light_manifest(builder, path):
    """Write <name>.lights.json -- the lighting contract. One anchor per light
    (a fluorescent ceiling row per room, an area light per window), derived from
    the rooms and openings the build computed. The renderer (Lux) instances a
    rig per anchor and tunes it from the active preset. Output-only -- no schema
    change. See docs/LIGHT_MANIFEST.md."""
    import json
    import lights as _lights
    data = _lights.build_light_manifest(
        builder.s.name,
        builder.gameplay.get("rooms", []),
        builder.gameplay.get("openings", []),
        builder.s.story_height,
        authored=getattr(builder.s, "lights", None),
        theme=getattr(builder.s, "theme", None),
    )
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[deli_counter] light manifest -> {path} "
          f"({len(data['anchors'])} anchors)")
    return data


def write_gameplay_json(builder, path):
    """Write the tactical companion file (<name>.gameplay.json) next to the
    GLB. Holds markers, rooms, vertical links, and tagged openings so Godot
    can read gameplay meaning without parsing node names."""
    import json
    data = {
        "level": builder.s.name,
        "mode": builder.s.mode,
        # Stable building id the server keys is_revealed + the rarity roll on.
        # For a single DC build this is the level name; every opening/anchor
        # carries the same value so any entry point resolves to this building.
        "building_id": builder.s.name,
        # building footprint (x, y in metres) — lets a site assembler (Lot)
        # test approach space in front of each entry against neighbours.
        "footprint": [builder.s.footprint_x, builder.s.footprint_y],
        # OPTIONAL building rarity: the single source of truth. `rarity` is the
        # tier string (or null); `rarity_color` is the resolved colour record
        # ({tier, rank, color_name, hex, rgb}) or null. The networked-door
        # reveal reads this; breachable openings below carry the same colour.
        "rarity": builder.gameplay.get("rarity"),
        "rarity_color": builder.gameplay.get("rarity_color"),
        "markers": builder.gameplay["markers"],
        "rooms": builder.gameplay["rooms"],
        "vertical_links": builder.gameplay["vertical_links"],
        "openings": builder.gameplay["openings"],
        "objectives": builder.gameplay["objectives"],
        "loot": builder.gameplay["loot"],
        "zones": builder.gameplay["zones"],
        "materials": builder.gameplay["materials"],
        "surfaces": builder.gameplay["surfaces"],
        # interactive fixtures (doors / breachable walls / breakable windows):
        # one replicable state machine per id. The game spawns a networked node
        # per entry and drives which art variant renders. See docs/INTERACTIVES.md.
        "interactives": builder.gameplay["interactives"],
        # semantic stair systems (docs/stairwell_placement_spec.md s13):
        # role, stack, floors served, per-floor approach, ground discharge.
        # Derived by stairwell.py; the review that gated it ran in validate.
        "stair_systems": builder.gameplay.get("stair_systems", []),
        # semantic ladder systems (docs/deli_counter_ladder_placement_spec.md s14):
        # role, connected surfaces, anchors, transition, egress exclusion,
        # route nodes. Derived by ladder.py; a ladder is never ordinary egress.
        "ladders": builder.gameplay.get("ladders", []),
        # elevated platforms (catwalks / equipment decks / rest platforms);
        # ladders reference these as surfaces by id (ladder spec Phase 4)
        "platforms": [
            {"id": p.id, "x": p.x, "y": p.y, "z": p.z,
             "size_x": p.size_x, "size_y": p.size_y,
             "role": p.role, "destination": p.destination,
             "guard_edges": list(p.guard_edges or [])}
            for p in builder.s.platforms],
        # authoritative node-name -> surface role map (floor/ceiling/wall/stair/
        # ramp/ladder/prop). Downstream tools (Patina styling, vertex nuance)
        # should consume this instead of inferring roles from geometry.
        "surface_roles": getattr(builder, "surface_roles", {}),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[deli_counter] gameplay -> {path}")
    return data


def export(path: str, fmt: str = None):
    """Export the scene. Format inferred from extension unless fmt given.

    Supported:
      .glb       glTF binary  (engine-ready, single file, Godot collision tags)
      .gltf      glTF text + .bin + textures (web/AR/VR, diff-friendlier)
      .obj       Wavefront OBJ (+ .mtl): static geometry, highly compatible,
                 splits into text files that diff well in source control.
                 NOTE: OBJ has no node-name collision convention -- it carries
                 the -convcolonly / -colonly names as object/group names, which
                 Godot's OBJ importer ignores. Use OBJ as the archival/static
                 format; use GLB for the Godot-collision pipeline.
    """
    ext = (fmt or path.rsplit(".", 1)[-1]).lower()
    # The SCALE_REF collection is a Blender-only visual aid — never export it.
    # Temporarily exclude it from the view layer (covers use_visible glTF) and
    # hide it (covers the OBJ exporter), then restore afterward.
    _scale_lc = None
    _prev_exclude = _prev_hide = None
    try:
        _scale_lc = bpy.context.view_layer.layer_collection.children.get("SCALE_REF")
    except Exception:
        _scale_lc = None
    if _scale_lc is not None:
        _prev_exclude = _scale_lc.exclude
        _scale_lc.exclude = True

    try:
        if ext == "glb":
            bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                                      use_visible=True)
        elif ext == "gltf":
            bpy.ops.export_scene.gltf(filepath=path, export_format='GLTF_SEPARATE',
                                      use_visible=True)
        elif ext == "obj":
            # Blender 4.x: bpy.ops.wm.obj_export
            bpy.ops.wm.obj_export(filepath=path, export_selected_objects=False,
                                  export_materials=True, export_triangulated_mesh=True)
        else:
            raise ValueError(f"Unsupported export format: {ext} "
                             "(use glb, gltf, or obj)")
    finally:
        if _scale_lc is not None and _prev_exclude is not None:
            _scale_lc.exclude = _prev_exclude
    print(f"[deli_counter] exported {path}")


# backwards-compat alias
def export_glb(path: str):
    export(path, "glb")

