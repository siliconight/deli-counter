"""zoo_export.py - generate a Godot "zoo" .tscn from a folder of module GLBs.

The in-game asset catalogue from the gym/zoo/museum workflow: one instance of
every module, knolled on a grid, each with a name label, plus scale references
(a 2 m cube and a 1.8 m player pillar) so you see real scale at a glance instead
of guessing from asset-browser thumbnails. Open it in Godot, fly through, read
the names off the labels, grab what you need.

bpy-free, like tscn_export - it scans a folder and writes a scene that instances
the GLBs (one PackedScene resource each, reused). This is a DOCUMENTATION
artifact for the team, not a mission shell; DC generates it, the editor consumes
it. Run standalone (`python zoo_export.py art/zoo`) or via `build.py --zoo`.
"""

import math
import os

from tscn_export import _f, _ref_path


def _label(node_name, text, pos):
    x, y, z = pos
    return [
        f'[node name="{node_name}" type="Label3D" parent="."]',
        f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, "
        f"{_f(x)}, {_f(y)}, {_f(z)})",
        f'text = "{text}"',
        "billboard = 1",          # face the camera so labels are always readable
        "pixel_size = 0.01",
        "font_size = 64",
        "outline_size = 12",
        "",
    ]


def _scale_refs(spacing):
    """A 2 m cube and a ~1.8 m player pillar, labelled, set just off the grid
    origin so every module reads against a known size."""
    bx, bz = -spacing, -spacing
    out = []
    out += [
        '[node name="ref_2m_cube" type="CSGBox3D" parent="."]',
        f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, "
        f"{_f(bx)}, 1, {_f(bz)})",
        "size = Vector3(2, 2, 2)",
        "",
    ]
    out += _label("ref_2m_label", "2 m cube", (bx, 2.4, bz))
    out += [
        '[node name="ref_player" type="CSGBox3D" parent="."]',
        f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, "
        f"{_f(bx - spacing)}, 0.9, {_f(bz)})",
        "size = Vector3(0.5, 1.8, 0.5)",
        "",
    ]
    out += _label("ref_player_label", "player 1.8 m", (bx - spacing, 2.1, bz))
    return out


def build_zoo(glb_names, res_root, out_path, spacing=3.0, cols=None):
    """Write a zoo .tscn instancing each module name on a grid. Returns path."""
    names = sorted(glb_names)          # sort clusters type_kit_style prefixes
    n = len(names)
    if not n:
        raise ValueError("no modules to lay out")
    if cols is None:
        cols = max(1, int(math.ceil(math.sqrt(n))))
    ids = {nm: f"{i + 1}_{nm}" for i, nm in enumerate(names)}

    out = [f"[gd_scene load_steps={n + 1} format=3]", ""]
    for nm in names:
        out.append(f'[ext_resource type="PackedScene" '
                   f'path="{_ref_path(res_root, nm)}" id="{ids[nm]}"]')
    out += ["", '[node name="Zoo" type="Node3D"]', ""]
    out += _scale_refs(spacing)
    for idx, nm in enumerate(names):
        x = (idx % cols) * spacing
        z = (idx // cols) * spacing
        out.append(f'[node name="{nm}" parent="." '
                   f'instance=ExtResource("{ids[nm]}")]')
        out.append(f"transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, "
                   f"{_f(x)}, 0, {_f(z)})")
        out.append("")
        out += _label(f"lbl_{idx}", nm, (x, 2.6, z))

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return out_path


def zoo_from_dir(lib_dir, res_root, out_path, spacing=3.0):
    names = [os.path.splitext(f)[0] for f in os.listdir(lib_dir)
             if f.lower().endswith(".glb")]
    if not names:
        raise FileNotFoundError(f"no .glb modules in {lib_dir}")
    return build_zoo(names, res_root, out_path, spacing=spacing)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Generate a Godot zoo .tscn from a folder of module GLBs")
    ap.add_argument("lib_dir", help="local folder of module .glb files")
    ap.add_argument("--res-root", default="res://art/zoo",
                    help="res:// path where those modules live in the project")
    ap.add_argument("--out", default="build/zoo.tscn")
    ap.add_argument("--spacing", type=float, default=3.0)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    print(f"[zoo] {zoo_from_dir(args.lib_dir, args.res_root, args.out, args.spacing)}")
