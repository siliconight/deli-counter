"""Tests for audit_specs.py (no bpy). Run: python3 test_audit_specs.py"""
import json
import os
import tempfile

import audit_specs


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _write(d):
    fd, path = tempfile.mkstemp(suffix=".json", dir="specs")
    with os.fdopen(fd, "w") as f:
        json.dump(d, f)
    return path


def _base(**kw):
    d = {"name": "t", "mode": "heist", "n_stories": 2,
         "footprint_x": 20, "footprint_y": 20,
         "rooms": [{"id": "ground", "story": 0, "bounds": [-10, -10, 10, 10],
                    "role": "service_access"}]}
    d.update(kw)
    return d


def test_clean_single_story_no_findings():
    p = _write(_base(n_stories=1, rooms=[]))
    try:
        hard, soft = audit_specs.audit_spec(p)
        assert hard == []
    finally:
        os.remove(p)


def test_trapped_upper_room_is_hard():
    # story-1 room, no circulation -> trapped
    d = _base(rooms=[
        {"id": "ground", "story": 0, "bounds": [-10, -10, 10, 10],
         "role": "service_access"},
        {"id": "upstairs", "story": 1, "bounds": [-10, -10, 10, 10],
         "role": "objective_room"}])
    p = _write(d)
    try:
        hard, _ = audit_spec_hard(p)
        assert any("upstairs" in h and "not" in h for h in hard)
    finally:
        os.remove(p)


def test_stair_reaches_upper_room_clean():
    d = _base(rooms=[
        {"id": "ground", "story": 0, "bounds": [-10, -10, 10, 10],
         "role": "service_access"},
        {"id": "upstairs", "story": 1, "bounds": [-10, -10, 10, 10],
         "role": "connector"}],
        stairs=[{"x": 0, "y": 0, "from_story": 0, "to_story": 1,
                 "role": "main_rotation"}])
    p = _write(d)
    try:
        hard, _ = audit_spec_hard(p)
        assert not any("upstairs" in h for h in hard)
    finally:
        os.remove(p)


def test_facade_shell_exempt():
    # facade-only, no interior -> upper floor need not be reachable
    d = _base(facade=True, rooms=[])
    p = _write(d)
    try:
        hard, _ = audit_specs.audit_spec(p)
        assert hard == []
    finally:
        os.remove(p)


def test_ladder_top_out_of_range_is_hard():
    d = _base(n_stories=1, rooms=[
        {"id": "g", "story": 0, "bounds": [-10, -10, 10, 10],
         "role": "service_access"}],
        ladders=[{"x": 0, "y": 0, "from_story": 0, "to_story": 3,
                  "role": "service_access", "upper_surface": "roof",
                  "transition": "roof_hatch_exit"}])
    p = _write(d)
    try:
        hard, _ = audit_spec_hard(p)
        assert any("exceeds n_stories" in h for h in hard)
    finally:
        os.remove(p)


def test_hatch_vlink_makes_story_reachable():
    # single-story vertical_link (hatch form) counts as reaching that story
    d = _base(rooms=[
        {"id": "ground", "story": 0, "bounds": [-10, -10, 10, 10],
         "role": "service_access"},
        {"id": "upstairs", "story": 1, "bounds": [-10, -10, 10, 10],
         "role": "connector"}],
        vertical_links=[{"kind": "hatch", "story": 1, "x": 0, "y": 0}])
    p = _write(d)
    try:
        hard, _ = audit_spec_hard(p)
        assert not any("upstairs" in h for h in hard)
    finally:
        os.remove(p)


def audit_spec_hard(p):
    """Helper: audit and return (hard, soft), tolerating loader specifics."""
    return audit_specs.audit_spec(p)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all audit_specs tests passed")
