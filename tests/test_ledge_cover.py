"""A vault ledge inside furniture draws no box of its own (0.227.0; see ledge_cover.py).

Found on the factory's cold run 9322, whose office z-fought `base:VAULTLEDGE_0` against `reception_desk`: the preset
stands its 5 m ledge in its 5 m desk on purpose -- the desk is the vault -- and the ledge drew a box 10 cm taller.

Run: python -m pytest -q tests/test_ledge_cover.py
"""
import inspect
from pathlib import Path
from types import SimpleNamespace

import ledge_cover
import spec_loader

HERE = Path(__file__).resolve().parent.parent


def _ledge_box(spec, vl):
    """The box `deli_counter._vault_ledges` builds for a ledge: centre and size, spec frame."""
    z = vl.story * spec.story_height + vl.height / 2
    size = (vl.length, vl.thick, vl.height) if vl.axis == "X" else (vl.thick, vl.length, vl.height)
    return (vl.x, vl.y, z), size


def _vol(name, c, s, visual=True):
    return SimpleNamespace(name=name, x=c[0], y=c[1], z=c[2], size_x=s[0], size_y=s[1], size_z=s[2], visual=visual)


def test_the_offices_reception_desk_is_its_ledges_look():
    spec = spec_loader.load_spec(str(HERE / "specs" / "office.json"))
    (vl,) = spec.vault_ledges
    frac, under = ledge_cover.cover(*_ledge_box(spec, vl), spec.volumes)
    assert under == "reception_desk" and abs(frac - 1.0 / 1.1) < 1e-6, (frac, under)
    assert frac >= ledge_cover.HIDDEN_BY


def test_a_ledge_in_open_floor_draws_itself():
    far = _vol("crate", (20.0, 20.0, 0.5), (1.0, 1.0, 1.0))
    assert ledge_cover.cover((0.0, 0.0, 0.55), (4.0, 0.2, 1.1), [far]) == (0.0, None)


def test_a_ledge_wholly_inside_a_counter_is_the_counters():
    counter = _vol("register_counter", (0.0, 0.0, 0.6), (5.0, 0.8, 1.2))
    frac, under = ledge_cover.cover((0.0, 0.0, 0.55), (4.0, 0.2, 1.1), [counter])
    assert under == "register_counter" and abs(frac - 1.0) < 1e-9


def test_an_invisible_volume_hides_nothing():
    ghost = _vol("register_counter", (0.0, 0.0, 0.6), (5.0, 0.8, 1.2), visual=False)
    assert ledge_cover.cover((0.0, 0.0, 0.55), (4.0, 0.2, 1.1), [ghost]) == (0.0, None)


def test_the_emitter_asks_before_it_draws():
    src = (HERE / "deli_counter.py").read_text(encoding="utf-8")
    body = src[src.index("    def _vault_ledges(self):"):src.index("    def _platforms(self):")]
    assert "ledge_cover.cover((vl.x, vl.y, z), size, self.s.volumes)" in body
    assert "if frac < ledge_cover.HIDDEN_BY:" in body
    # the collision and its tag stay either way
    assert body.index("self._col_box(name") > body.index("if frac < ledge_cover.HIDDEN_BY:")


def test_the_threshold_is_a_dial_and_says_so():
    assert ledge_cover.HIDDEN_BY == 0.5
    assert "meant to be changed" in inspect.getsource(ledge_cover)
