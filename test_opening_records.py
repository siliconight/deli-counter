"""An opening is recorded where its hole is cut (0.162.0).

`_opening_to_hole` cuts every opening at `snap(pos * run)`; `_record_openings`
recorded `pos * run`, so 957 of the library's 1,943 openings sat off their own
holes -- 596 by 0.10 m or more, up to 0.25 m -- and everything placed from the
record stood beside its doorway: the door socket, the interactive, a window's
light, the storefront's lit sign box. Measured against the built outputs:
each exterior opening in `<id>.gameplay.json` must stand on an opening slot
of the same wall in `<id>.slots.json`, and the derived sign on its door.
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")


def _load(path):
    return json.load(open(path, encoding="utf-8"))


def _built():
    for g in sorted(glob.glob(os.path.join(BUILD, "*.gameplay.json"))):
        name = os.path.basename(g)[:-len(".gameplay.json")]
        s = os.path.join(BUILD, name + ".slots.json")
        if os.path.isfile(s):
            yield name, _load(g), _load(s)["slots"]


def _along(wall, xy):
    # ext_<story>_<N|S|E|W>: a N/S wall runs along x, an E/W wall along y
    return xy[0] if wall.rsplit("_", 1)[-1] in ("N", "S") else xy[1]


def test_every_exterior_opening_stands_on_its_built_slot():
    checked = 0
    for name, gp, slots in _built():
        holes = {}
        for s in slots:
            sid = s["slot_id"]
            if "_open" in sid and sid.startswith("ext_") and not sid.endswith("_open"):
                wall = sid.split("_open")[0]
                holes.setdefault(wall, []).append(_along(wall, s["transform"]["translation"]))
        if not holes:
            continue                 # a non-modular shell carries no opening slots
        for op in gp.get("openings") or []:
            wall = op.get("wall", "")
            if not wall.startswith("ext_") or wall not in holes:
                continue
            u = _along(wall, (op["x"], op["y"]))
            assert min(abs(u - h) for h in holes[wall]) < 1e-3, (name, wall, op["kind"], u, holes[wall])
            checked += 1
    assert checked > 500, checked            # the check reached the library


def test_the_storefront_sign_is_centred_on_its_door():
    """Against the door AS BUILT -- its opening slot -- not against the
    opening record: the first cut of this test compared the sign with the
    record, which the old build had wrong in the same way, and it passed on
    the build it exists to refuse."""
    checked = 0
    for name, gp, slots in _built():
        lp = os.path.join(BUILD, name + ".lights.json")
        if not os.path.isfile(lp):
            continue
        signs = [a for a in _load(lp)["anchors"] if a["type"] == "sign" and a.get("source") == "derived"]
        for sg in signs:
            wall = sg["wall"]
            built = [_along(wall, s["transform"]["translation"]) for s in slots
                     if s["slot_id"].startswith(wall + "_open") and not s["slot_id"].endswith("_open")]
            if not built:
                continue             # a non-modular shell: no slot to measure against
            u = _along(wall, sg["pos"])
            assert min(abs(u - h) for h in built) < 1e-3, (name, u, built)
            checked += 1
    assert checked > 10, checked
