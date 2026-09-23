"""A GLB is bundled with what it names, and a package says so when it is not.

THE DEFECT. Zoo 1.2.0 stopped embedding a module's images in its binary chunk
and started writing them beside it under a relative glTF `images[].uri`.
`portable_building.build_package` bundles a module by resolving one
`res://art/zoo/<name>.glb` out of the scene and copying that one path, so
every composed building since carried its geometry and none of its pixels.

Measured 2026-09-22 on cold run 9068's shipped `LF_club_block_007`: 1,264
external references across 265 GLBs, all missing; 1,136 of them came through
this repo's composer. The walker's report was "around 90% graybox".

`_closure_check` returned `portable: true` on every one of them, because it
walks `.tscn/.tres/.gd/.godot` for `res://` strings and a glTF `uri` is
neither.

Run:  python -m pytest test_glb_deps.py
"""
import json
import os
import struct

import pytest

import glb_deps


def _glb(path, images=(), *, tag="stub"):
    doc = {"asset": {"version": "2.0", "generator": tag}, "scene": 0,
           "scenes": [{"nodes": [0]}], "nodes": [{"name": tag}]}
    if images:
        doc["images"] = [{"name": os.path.basename(u), "uri": u}
                         for u in images]
    payload = json.dumps(doc).encode("utf-8")
    payload += b" " * (-len(payload) % 4)
    chunk = struct.pack("<II", len(payload), 0x4E4F534A) + payload
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    with open(str(path), "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, 12 + len(chunk)) + chunk)
    return str(path)


def _png(path):
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    with open(str(path), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
    return str(path)


# --- what a GLB names -------------------------------------------------------

def test_an_external_uri_is_a_dependency(tmp_path):
    _glb(tmp_path / "wall.glb", ["_tex/brick_a1b2c3d4.png"])
    assert glb_deps.dependencies(tmp_path / "wall.glb") == [
        "_tex/brick_a1b2c3d4.png"]


def test_an_embedded_image_is_not(tmp_path):
    """The pre-1.2.0 module, which the old copy was right about."""
    _glb(tmp_path / "wall.glb", ["data:image/png;base64,iVBORw0KGgo="])
    assert glb_deps.dependencies(tmp_path / "wall.glb") == []


def test_a_file_that_is_not_a_glb_raises_rather_than_answering_nothing(tmp_path):
    """"Names nothing" and "could not be read" are different answers, and a
    caller copying files must not be handed the first when the truth is the
    second."""
    (tmp_path / "broken.glb").write_bytes(b"not a glb")
    with pytest.raises(glb_deps.GlbUnreadable):
        glb_deps.dependencies(tmp_path / "broken.glb")


def test_the_json_chunk_need_not_be_first(tmp_path):
    """A BIN chunk ahead of the JSON chunk is legal glTF; assuming otherwise
    would report a healthy module as unreadable."""
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": []}],
           "nodes": [], "images": [{"name": "t", "uri": "_tex/x.png"}]}
    payload = json.dumps(doc).encode("utf-8")
    payload += b" " * (-len(payload) % 4)
    binc = b"\0" * 16
    body = (struct.pack("<II", len(binc), 0x004E4942) + binc
            + struct.pack("<II", len(payload), 0x4E4F534A) + payload)
    (tmp_path / "odd.glb").write_bytes(
        struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body)
    assert glb_deps.dependencies(tmp_path / "odd.glb") == ["_tex/x.png"]


# --- the copy ---------------------------------------------------------------

def test_the_copy_carries_the_texture(tmp_path):
    src, dst = tmp_path / "kit", tmp_path / "pkg" / "art" / "zoo"
    _glb(src / "wall.glb", ["_tex/brick_a1b2c3d4.png"])
    _png(src / "_tex" / "brick_a1b2c3d4.png")
    copied = glb_deps.copy_with_deps(src / "wall.glb", dst / "wall.glb")
    assert copied == ["_tex/brick_a1b2c3d4.png"]
    assert os.path.isfile(str(dst / "_tex" / "brick_a1b2c3d4.png"))
    assert glb_deps.unresolved(str(tmp_path / "pkg")) == []


def test_two_modules_sharing_a_texture_write_one_file(tmp_path):
    """The saving the format change exists for. Godot does not deduplicate
    identical embedded images -- Zoo measured 20 identical embeds at
    27,962,000 B against 1,398,100 B for one shared external -- so a bundler
    that copied per module would give that back."""
    src, dst = tmp_path / "kit", tmp_path / "pkg"
    _glb(src / "a.glb", ["_tex/brick_a1b2c3d4.png"])
    _glb(src / "b.glb", ["_tex/brick_a1b2c3d4.png"])
    _png(src / "_tex" / "brick_a1b2c3d4.png")
    glb_deps.copy_with_deps(src / "a.glb", dst / "a.glb")
    glb_deps.copy_with_deps(src / "b.glb", dst / "b.glb")
    assert sorted(os.listdir(str(dst / "_tex"))) == ["brick_a1b2c3d4.png"]


def test_the_copy_refuses_rather_than_moving_half_of_what_it_was_asked_to(tmp_path):
    src, dst = tmp_path / "kit", tmp_path / "pkg"
    _glb(src / "wall.glb", ["_tex/brick_a1b2c3d4.png"])
    with pytest.raises(OSError):
        glb_deps.copy_with_deps(src / "wall.glb", dst / "wall.glb")


@pytest.mark.parametrize("uri", ["../outside/x.png", "/var/x.png",
                                 "https://example.invalid/x.png"])
def test_a_reference_a_recipient_cannot_follow_is_refused(tmp_path, uri):
    src, dst = tmp_path / "kit", tmp_path / "pkg"
    _glb(src / "wall.glb", [uri])
    with pytest.raises(OSError):
        glb_deps.copy_with_deps(src / "wall.glb", dst / "wall.glb")


# --- the closure self-check -------------------------------------------------

def test_the_package_check_now_sees_a_reference_inside_a_glb(tmp_path):
    """The gap that let four packages call themselves portable."""
    import portable_building
    _glb(tmp_path / "wall.glb", ["_tex/brick_a1b2c3d4.png"])
    report = portable_building._closure_check(str(tmp_path))
    assert report["glb_unresolved_count"] == 1
    assert report["portable"] is False
    # THE CONTROL. Without it this proves only that the check can say no.
    _png(tmp_path / "_tex" / "brick_a1b2c3d4.png")
    report = portable_building._closure_check(str(tmp_path))
    assert report["glb_unresolved_count"] == 0
    assert report["portable"] is True


def test_the_bundler_calls_the_dependency_copy():
    """A source assertion, because the alternative is a full compose inside a
    unit test. The two `shutil.copy2` calls it replaces were the defect."""
    import inspect

    import portable_building
    body = inspect.getsource(portable_building.build_package)
    assert body.count("glb_deps.copy_with_deps(") == 2  # the call sites, not the prose
    assert "shutil.copy2(src, os.path.join(art, ref))" not in body
    assert "shutil.copy2(src, os.path.join(ldir, fname))" not in body
