"""Per-storey footprint: the derivation everything shares (roadmap 116).

The library's baseline before this existed, measured by `tools/massing.py`:
127 shells, every one describing ONE footprint, and the 114 readable from
built geometry filling their own bounding box with min 1.000, mean 1.000 and
NO variance. `LevelSpec` carried one `footprint_x`, one `footprint_y` and one
`n_stories`, so it could not express another answer.

These run without Blender.

    python -m pytest test_setbacks.py -q
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import setbacks as SB
import spec_loader
from spec_types import LevelSpec, Setback


def _spec(n_stories=3, basement=False, **kw):
    return LevelSpec(footprint_x=20.0, footprint_y=14.0, n_stories=n_stories,
                     has_basement=basement, wall_thick=0.3, **kw)


# ---- nothing opts in, nothing changes -------------------------------------

def test_a_spec_with_no_setbacks_is_the_base_footprint_everywhere():
    s = _spec()
    for k in range(0, 4):
        assert SB.storey_extent(s, k) == (-10.0, -7.0, 10.0, 7.0)
    assert SB.is_stepped(s) is False


#: Specs that deliberately step. Every other shell must bake byte-identically
#: or this feature is not opt-in -- verified once by hash: `night_pawn.glb`
#: was bit-for-bit unchanged across the builder change, with only the
#: manifest's `built_utc` moving.
_STEPPED = {
    "setback_demo.json",        # a stepped industrial shed: the lower wing read
    "office_stepped.json",      # the top storey set back, wrapping a terrace
}


def test_only_the_demo_steps():
    """A NAMED list rather than an empty one. `stepped == []` was the honest
    assertion until the demo existed; keeping it would have meant deleting the
    check the moment the feature was used. This way a spec that starts
    stepping without anyone deciding it should still fails."""
    import glob
    paths = sorted(glob.glob(os.path.join(HERE, "specs", "*.json")))
    assert len(paths) > 100, len(paths)
    stepped = set()
    for p in paths:
        try:
            spec = spec_loader.load_spec(p)
        except Exception:
            continue
        if SB.is_stepped(spec):
            stepped.add(os.path.basename(p))
    assert stepped == _STEPPED, stepped ^ _STEPPED


# ---- one entry steps once -------------------------------------------------

def test_a_setback_applies_from_its_storey_upward():
    s = _spec(setbacks=[Setback(story=1, inset_n=3.0, inset_e=2.0)])
    assert SB.storey_extent(s, 0) == (-10.0, -7.0, 10.0, 7.0)
    assert SB.storey_extent(s, 1) == (-10.0, -7.0, 8.0, 4.0)
    assert SB.storey_extent(s, 2) == (-10.0, -7.0, 8.0, 4.0)   # carries up
    assert SB.is_stepped(s) is True


def test_a_side_left_at_zero_stays_flush():
    """A street frontage holds the building line while the rear steps back."""
    s = _spec(setbacks=[Setback(story=1, inset_n=4.0)])
    x0, y0, x1, y1 = SB.storey_extent(s, 1)
    assert (x0, x1) == (-10.0, 10.0)      # E and W untouched
    assert y0 == -7.0                      # S holds the line
    assert y1 == 3.0                       # N steps back


def test_an_asymmetric_setback_moves_the_storey_centre():
    """A wall placed at +/- half a size would be in the wrong place."""
    s = _spec(setbacks=[Setback(story=1, inset_n=4.0)])
    assert SB.storey_centre(s, 0) == (0.0, 0.0)
    assert SB.storey_centre(s, 1) == (0.0, -2.0)
    assert SB.storey_size(s, 1) == (20.0, 10.0)


# ---- two entries step twice, they do not compound -------------------------

def test_the_highest_applicable_setback_wins():
    """Additive would make the second entry's numbers depend on the first,
    which is how an author ends up computing deltas by hand."""
    s = _spec(n_stories=4, setbacks=[Setback(story=1, inset_n=2.0),
                                     Setback(story=3, inset_n=5.0)])
    assert SB.storey_extent(s, 1)[3] == 5.0    # 7 - 2
    assert SB.storey_extent(s, 2)[3] == 5.0    # carried
    assert SB.storey_extent(s, 3)[3] == 2.0    # 7 - 5, NOT 7 - 2 - 5


# ---- the slab is what makes a setback walkable ----------------------------

def test_a_slab_caps_the_storey_below_it():
    """This is what turns a setback into a terrace with a real collider
    rather than a ledge the upper wall stands on the edge of."""
    s = _spec(setbacks=[Setback(story=1, inset_n=4.0)])
    # the slab whose top face is storey 1's floor caps storey 0 -> full width
    assert SB.slab_extent(s, 1) == (-10.0, -7.0, 10.0, 7.0)
    # the roof over storey 1 takes storey 1's inset extent
    assert SB.slab_extent(s, 2) == (-10.0, -7.0, 10.0, 3.0)


def test_the_lowest_slab_takes_its_own_storey():
    s = _spec(basement=True, setbacks=[Setback(story=1, inset_n=4.0)])
    assert SB.slab_extent(s, -1) == (-10.0, -7.0, 10.0, 7.0)


# ---- refusals, because the builder would happily emit both ----------------

def test_an_inset_deeper_than_the_footprint_is_refused():
    s = _spec(setbacks=[Setback(story=1, inset_n=20.0)])
    codes = {c for c, _ in SB.findings(s)}
    assert "SETBACK_CONSUMES_STOREY" in codes


def test_a_storey_thinner_than_its_own_walls_is_refused():
    s = _spec(setbacks=[Setback(story=1, inset_n=6.8, inset_s=6.8)])
    codes = {c for c, _ in SB.findings(s)}
    assert "SETBACK_LEAVES_NO_ROOM" in codes


def test_a_setback_at_the_base_is_refused():
    """It would inset the whole building rather than step it -- which is a
    smaller footprint, not a setback, and `footprint_x` already says that."""
    s = _spec(setbacks=[Setback(story=0, inset_n=2.0)])
    assert "SETBACK_AT_BASE" in {c for c, _ in SB.findings(s)}


def test_a_setback_above_the_roof_is_refused():
    s = _spec(n_stories=2, setbacks=[Setback(story=5, inset_n=2.0)])
    assert "SETBACK_ABOVE_ROOF" in {c for c, _ in SB.findings(s)}


def test_a_buildable_setback_is_clean():
    s = _spec(setbacks=[Setback(story=1, inset_n=3.0, inset_e=2.0)])
    assert SB.findings(s) == []
