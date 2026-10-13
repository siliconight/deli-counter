"""A rowhome's stoop is circulation, not a prop standing in it (0.211.1, factory roadmap 240).

0.211.0 drew its landing and treads with the surface role `prop`, and Deli Counter's own circulation gate
(`circulation.check_shell`) read each landing as a prop standing 0.15 m into its front doorway, on all
twelve rowhomes -- cold run 9271, `PRESENTATION_CIRCULATION` 0 -> 12. The 0.15 m is the gate's, not the
stoop's: `doorway_volume` starts a door's volume at its wall's bottom plus its sill, the builder opens the
door at the slab's top (floor_thick / 2) plus its sill, and a landing's top IS the threshold. A stoop is
the way to the door: its pieces are `stair`, as a flight's treads are -- the climbable affordance's colour
in a greybox -- and the gate reads none of them as a prop. The art pass still dresses each as a volume:
its slot's role is the slot's own.

Read off the built shells, so it fails until `build.py` has run on 0.211.1.
"""
import glob
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))

import circulation   # noqa: E402

NAMES = sorted(os.path.basename(p)[:-4]
               for p in glob.glob(os.path.join(HERE, "build", "gs_empty_rowhome_*.glb")))
PIECES = ("stoop_landing", "stoop_tread_1", "stoop_tread_2")


def _built(name):
    with open(os.path.join(HERE, "build", name + ".slots.json"), encoding="utf-8") as fh:
        slots = json.load(fh)
    with open(os.path.join(HERE, "build", name + ".gameplay.json"), encoding="utf-8") as fh:
        gp = json.load(fh)
    return os.path.join(HERE, "build", name + ".glb"), slots, gp


def test_the_twelve_are_built():
    assert len(NAMES) == 12, NAMES


@pytest.mark.parametrize("name", NAMES)
def test_every_rowhome_keeps_its_own_circulation_clear(name):
    glb, slots, gp = _built(name)
    out = circulation.check_shell(glb, slots, gp)
    assert out["ok"], (name, out["conflicts"], out.get("error"))
    # it looked: the front door and the back door are its volumes
    assert out["volumes"] >= 2, out


@pytest.mark.parametrize("name", NAMES)
def test_the_stoop_is_a_stair_to_the_gate_and_a_volume_to_the_art(name):
    _glb, slots, gp = _built(name)
    roles = gp["surface_roles"]
    for piece in PIECES:
        assert roles.get(piece) == "stair", (name, piece, roles.get(piece))
    st = {s["slot_id"]: s for s in slots["slots"] if s["slot_id"].startswith("stoop_")}
    assert sorted(st) == sorted(PIECES)
    assert all(s["role"] == "prop" and s["material"] == "concrete" for s in st.values())
