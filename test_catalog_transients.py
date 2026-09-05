"""CATALOG.md must not move when a pipeline writes a spec into this repo.

ROADMAP 73, and the reason this is a test rather than a tidy-up. The chain:

  * `specs/lf_*.json` are Level Factory's transient inputs. They are correctly
    gitignored (.gitignore:49) and none is tracked.
  * `specs/CATALOG.md` IS tracked, and `new_level.py` refreshes it after every
    spec write.
  * Level Factory folds a tool repo's dirty-TRACKED-file hash into the build
    fingerprint (`packages/adapters/sdk.py:_read_git_commit`); untracked files
    are deliberately excluded so that pipeline writes cannot bust the cache.

So indexing lf_ specs put the ONE tracked file the pipeline touches into the
fingerprint. Measured before the fix: a single `new_level.py --preset bank`
turned the revision from `099a9cd` into `099a9cd+dirty.cbd2f89b2b4fe547`, with
`specs/CATALOG.md` the only dirty tracked file. One deli_generate job changed
the revision its own siblings key on, every later job cache-missed, and jobs
the functional lock had already fingerprinted re-ran behind it -- which moved
the gameplay-anchor and interactive registries and made `verify_no_drift`
refuse the export. That blocked cold runs 1 through 3.

The property under test is not "the catalogue is tidy". It is that a pipeline
spec write leaves this repo's tracked tree BYTE-IDENTICAL.
"""
import json
import shutil
from pathlib import Path

import catalog

HERE = Path(__file__).resolve().parent
SPECS = HERE / "specs"


def _a_real_spec() -> Path:
    """Any authored spec; copied to make a transient with valid content."""
    for p in sorted(SPECS.glob("*.json")):
        if not p.name.startswith(catalog._TRANSIENT_PREFIX):
            return p
    raise AssertionError("no authored spec to copy")


def test_library_specs_excludes_pipeline_transients():
    names = [Path(p).name for p in catalog._library_specs()]
    assert names, "the library is empty -- the glob is wrong"
    assert not [n for n in names if n.startswith(catalog._TRANSIENT_PREFIX)]


def test_authored_specs_are_still_indexed():
    """The exclusion must be narrow. A prefix filter that swallowed the
    library would pass the test above and destroy the catalogue."""
    names = {Path(p).name for p in catalog._library_specs()}
    assert _a_real_spec().name in names


def test_a_pipeline_spec_write_does_not_move_the_catalogue():
    """The one that matters: write a transient, and CATALOG.md is unchanged."""
    before = catalog.render([catalog.summarize(p)
                             for p in catalog._library_specs()])
    transient = SPECS / f"{catalog._TRANSIENT_PREFIX}it73_guard_9001.json"
    shutil.copyfile(_a_real_spec(), transient)
    try:
        # The name inside the spec should not matter either; set it anyway so
        # the fixture looks like something Level Factory would have written.
        d = json.loads(transient.read_text(encoding="utf-8"))
        d["name"] = transient.stem
        transient.write_text(json.dumps(d, indent=1), encoding="utf-8")

        after = catalog.render([catalog.summarize(p)
                                for p in catalog._library_specs()])
        assert after == before, \
            "a pipeline spec write moved CATALOG.md -- roadmap 73 is back"
    finally:
        transient.unlink(missing_ok=True)
