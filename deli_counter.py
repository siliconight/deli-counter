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
)


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

    # -- helpers ------------------------------------------------------------
    def snap(self, v):
        g = self.s.grid
        return round(v / g) * g

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

    def _box(self, name, center, size, collection):
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()
        obj.scale = (max(size[0], 1e-4), max(size[1], 1e-4), max(size[2], 1e-4))
        obj.location = center
        return obj

    def _col_box(self, name, center, size, mode=None):
        mode = mode or self.s.collision
        suf = self.col_suffix[mode]
        if suf == "":
            return None
        return self._box(name + suf, center, size, self.COLLISION)

    def _box_with_holes(self, name, center, size, holes, collection):
        """Solid box minus rectangular holes (visual). holes: list of dicts
        with u (offset along run), v (offset in Z from wall center), w, h."""
        wall = self._box(name, center, size, collection)
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
    def _opening_to_hole(self, op: Opening, run_len):
        r = op.resolved()
        u = self.snap(op.pos * run_len)
        H = self.s.story_height
        v = -H / 2.0 + r["sill"] + r["height"] / 2.0 + self.s.floor_thick / 2.0
        return dict(u=u, v=v, w=r["width"], h=r["height"], kind=op.kind,
                    sill=r["sill"])

    def _wall_collision(self, name, center, size, axis, holes):
        """Emit convex collision segments flanking door-height openings.
        Window-height openings (sill>0) keep the wall solid (impassable),
        which is correct. 'breach' openings get a tagged removable panel."""
        H = self.s.story_height
        passables = [h for h in holes if h["sill"] <= 0.05]
        if not passables:
            self._col_box(name, center, size)
            return
        # support a single passable opening per wall robustly
        h0 = passables[0]
        u, w, hh = h0["u"], h0["w"], h0["h"]
        full = size[0] if axis == 0 else size[1]
        thick_idx = 1 if axis == 0 else 0
        thick = size[thick_idx]
        cz = center[2]

        def seg(suffix, cu, clen):
            if clen <= 0.05:
                return
            if axis == 0:
                c = (center[0] + cu, center[1], cz)
                sz = (clen, thick, size[2])
            else:
                c = (center[0], center[1] + cu, cz)
                sz = (thick, clen, size[2])
            self._col_box(f"{name}_{suffix}", c, sz)

        left_w = (full / 2 + u) - w / 2
        seg("L", -full / 2 + left_w / 2, left_w)
        right_w = (full / 2 - u) - w / 2
        seg("R", full / 2 - right_w / 2, right_w)
        lintel_h = size[2] - hh - self.s.floor_thick
        if lintel_h > 0.05:
            lz = cz + size[2] / 2 - lintel_h / 2
            if axis == 0:
                self._col_box(f"{name}_T", (center[0] + u, center[1], lz),
                              (w, thick, lintel_h))
            else:
                self._col_box(f"{name}_T", (center[0], center[1] + u, lz),
                              (thick, w, lintel_h))
        # breach panel: a separate, tagged removable collision+visual chunk
        if h0["kind"] == "breach":
            if axis == 0:
                bc = (center[0] + u, center[1], cz - size[2] / 2 + self.s.floor_thick / 2 + hh / 2)
                bs = (w, thick, hh)
            else:
                bc = (center[0], center[1] + u, cz - size[2] / 2 + self.s.floor_thick / 2 + hh / 2)
                bs = (thick, w, hh)
            self._box(f"{name}_BREACHPANEL", bc, bs, self.VISUAL)
            self._col_box(f"{name}_BREACHPANEL", bc, bs)

    # -- top-level build steps ---------------------------------------------
    def build(self):
        self._clear()
        self.VISUAL = self._col("VISUAL")
        self.COLLISION = self._col("COLLISION")
        self._slabs()
        self._exterior()
        self._partitions()
        self._stairs()
        self._slab_holes_cut()
        self._volumes()
        self._placements()
        self._parapets()
        print(f"[deli_counter] built '{self.s.name}' seed={self.s.seed}: "
              f"{len(self.VISUAL.objects)} visual, "
              f"{len(self.COLLISION.objects)} collision")

    def _story_range(self):
        base = -1 if self.s.has_basement else 0
        return base, self.s.n_stories

    def _slabs(self):
        base, top = self._story_range()
        ft = self.s.floor_thick
        for s in range(base, top + 1):
            z = s * self.s.story_height
            self._box(f"slab_{s}", (0, 0, z - ft / 2),
                      (self.s.footprint_x, self.s.footprint_y, ft), self.VISUAL)
            self._col_box(f"slab_col_{s}", (0, 0, z - ft / 2),
                          (self.s.footprint_x, self.s.footprint_y, ft))

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
                    holes = [self._opening_to_hole(op, run) for op in spec_w.openings]
                self._box_with_holes(f"ext_{s}_{wname}", c, size, holes, self.VISUAL)
                if holes:
                    self._wall_collision(f"ext_col_{s}_{wname}", c, size, axis, holes)
                else:
                    self._col_box(f"ext_col_{s}_{wname}", c, size)

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
            holes = [self._opening_to_hole(op, length) for op in p.openings]
            self._box_with_holes(f"int_{p.story}_{i}", c, size, holes, self.VISUAL)
            if holes:
                self._wall_collision(f"int_col_{p.story}_{i}", c, size, axis, holes)
            else:
                self._col_box(f"int_col_{p.story}_{i}", c, size)

    def _stairs(self):
        H = self.s.story_height
        for si, st in enumerate(self.s.stairs):
            n_steps = 12
            step_d = st.run / n_steps
            for s in range(st.from_story, st.to_story):
                z = s * H
                step_h = H / n_steps
                sign = 1 if ((s - st.from_story) % 2 == 0 or st.style == "straight") else -1
                for i in range(n_steps):
                    cz = z + step_h * (i + 0.5)
                    cy = st.y + sign * (step_d * (i + 0.5) - st.run / 2)
                    self._box(f"stair{si}_{s}_{i}", (st.x, cy, cz),
                              (st.width, step_d, step_h), self.VISUAL)
                    self._col_box(f"stair{si}col_{s}_{i}", (st.x, cy, cz),
                                  (st.width, step_d, step_h))
                if st.cut_slabs:
                    self.s.slab_holes.append(SlabHole(
                        story=s + 1, x=st.x, y=st.y,
                        size_x=st.width + 0.4, size_y=st.run + 0.4))

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
                self._box(v.name, c, size, self.VISUAL)
            if v.collision != "none":
                self._col_box(f"{v.name}_col", c, size, mode=v.collision)

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

            imported = self._import_asset_objects(asset)
            visual = self._join_objects(imported, base)
            if visual is None:
                continue
            for c in list(visual.users_collection):
                c.objects.unlink(visual)
            self.VISUAL.objects.link(visual)
            self._apply_transform(visual, p)

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
                self._box(f"parapet_{n}", c, size, self.VISUAL)
                self._col_box(f"parapet_{n}_col", c, size)


def build(spec: LevelSpec, base_dir: str = "."):
    """Public entry point. base_dir is the spec file's folder, used to
    resolve the vendored assets directory for kitbashing."""
    _Builder(spec, base_dir=base_dir).build()


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
    print(f"[deli_counter] exported {path}")


# backwards-compat alias
def export_glb(path: str):
    export(path, "glb")

