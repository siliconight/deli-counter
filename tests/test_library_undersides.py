"""Every library stair is solid underneath unless it is named here (0.262.0).

The walker, walking cold run 9383, of deli_a03's up-stair: "this stair has unexpected space below it". Solid has been
the default since the walker asked for it (2026-09-13, `test_stair_underside.py`); that stair was the library's one
exception, opened by hand in 0.124.1 because its foot could only be reached from under its high end, and it outlived
its reason when 0.189.0 widened the door beside it. Nothing noticed, because nothing asked. Now an open underside in
the library is a decision written down below with its reason -- a sightline, say -- or it is a failure, and the nav
gate proves a solid flight's foot reachable the way it proves every flight (`nav_gate.py`).

THE TEST THAT MATTERS IS `test_every_library_stair_is_solid_unless_named`.
"""
import glob
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import spec_loader  # noqa: E402
import stairwell  # noqa: E402

#: (spec file, stair id) -> why its underside is open. Empty: no library stair is open underneath.
OPEN_UNDERSIDES = {}


def _library():
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        spec = spec_loader.load_spec(p)
        for st in getattr(spec, "stairs", []) or []:
            yield os.path.basename(p), spec, st


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("DC_STAIR_UNDERSIDES", raising=False)


def test_every_library_stair_is_solid_unless_named():
    opened = sorted((name, st.id) for name, spec, st in _library()
                    if stairwell.stair_underside(spec, st) == "open" and (name, st.id) not in OPEN_UNDERSIDES)
    assert not opened, "open underneath and not named in OPEN_UNDERSIDES: %s" % opened


def test_every_named_opening_is_still_open_and_says_why():
    """A name here that no longer builds open is a reason nobody is reading."""
    built = {(name, st.id): stairwell.stair_underside(spec, st) for name, spec, st in _library()}
    for key, why in OPEN_UNDERSIDES.items():
        assert built.get(key) == "open", key
        assert why.strip(), key
