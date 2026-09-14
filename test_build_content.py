"""A shell is stale when its manifest describes other bytes (0.131.1).

Cold run 9053, 2026-09-14: `build/*.glb` is gitignored and the manifest and
slots beside it are tracked, so merging 0.131.0 moved the slots to a new build
and left 0.129.0's shells on disk. The composer placed a 1.8 m waiting-chair
module over a 2.4 m greybox node of the same name and the placement gate
refused the export. `build_freshness.content_stale` asks the manifest.

Run:  python -m pytest test_build_content.py
"""
import hashlib
import json

import build_freshness as bf


def _sha16(data):
    return hashlib.sha256(data).hexdigest()[:16]


def _shell(tmp_path, spec=b'{"a": 1}\n', glb=b"glTF-one", recorded_glb=None,
           recorded_spec=None, gameplay=True):
    (tmp_path / "specs").mkdir(exist_ok=True)
    (tmp_path / "build").mkdir(exist_ok=True)
    (tmp_path / "specs" / "shop.json").write_bytes(spec)
    (tmp_path / "build" / "shop.glb").write_bytes(glb)
    if gameplay:
        (tmp_path / "build" / "shop.gameplay.json").write_text("{}")
    man = {"spec": "shop.json",
           "spec_sha256_16": recorded_spec or _sha16(spec),
           "outputs": ["shop.glb"]}
    if recorded_glb is not None:
        man["outputs_sha256_16"] = {"shop.glb": recorded_glb}
    (tmp_path / "build" / "shop.manifest.json").write_text(json.dumps(man))
    return str(tmp_path)


def test_a_shell_matching_its_manifest_is_fresh(tmp_path):
    here = _shell(tmp_path, recorded_glb=_sha16(b"glTF-one"))
    assert bf.content_stale(here) == []


def test_the_merge_that_broke_9053_a_glb_from_another_build(tmp_path):
    """The tracked manifest records one build; the untracked GLB is another."""
    here = _shell(tmp_path, glb=b"glTF-old", recorded_glb=_sha16(b"glTF-new"))
    (hit,) = bf.content_stale(here)
    assert hit[0].endswith("shop.glb") and "not the build" in hit[1]


def test_a_spec_edited_after_the_build_is_stale(tmp_path):
    """A migration rewrote the spec and nothing rebuilt it. No geometry source
    moved, so the mtime rule has nothing to compare."""
    here = _shell(tmp_path, spec=b'{"a": 2}\n', recorded_spec=_sha16(b'{"a": 1}\n'))
    (hit,) = bf.content_stale(here)
    assert "spec shop.json changed" in hit[1]


def test_line_endings_alone_are_not_a_change(tmp_path):
    """git's autocrlf rewrites endings on checkout; gas_station_a02 measured so
    (743 CRLF on disk, its manifest hashed the LF bytes)."""
    lf = b'{\n  "a": 1\n}\n'
    here = _shell(tmp_path, spec=lf.replace(b"\n", b"\r\n"), recorded_spec=_sha16(lf))
    assert bf.content_stale(here) == []


def test_a_manifest_older_than_the_fingerprint_is_not_judged_on_it(tmp_path):
    here = _shell(tmp_path, glb=b"anything", recorded_glb=None)
    assert bf.content_stale(here) == []


def test_a_shell_no_gate_reads_is_ignored(tmp_path):
    here = _shell(tmp_path, glb=b"old", recorded_glb=_sha16(b"new"), gameplay=False)
    assert bf.content_stale(here) == []
