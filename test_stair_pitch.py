"""Every shipped stair is one a body can climb.

The walker, on cold run 9046's walk copy: "cant get up the steps". Measured
across the library: 61 of 148 straight and switchback flights were over the
45 degrees a CharacterBody3D stands on, and every nav gate passed them because
the bake allows 55. See `stair_pitch.py`.
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import stair_pitch  # noqa: E402


def test_walkable_run_lands_at_the_target_pitch_and_never_under_it():
    for H in (2.9, 3.2, 4.2, 4.6, 5.0, 5.5, 6.0, 6.5):
        run = stair_pitch.walkable_run(H)
        assert stair_pitch.pitch_deg(H, run) <= stair_pitch.TARGET_PITCH_DEG + 1e-9
        assert stair_pitch.pitch_deg(H, run - 0.1) > stair_pitch.TARGET_PITCH_DEG


def test_the_stadium_the_walker_could_not_climb():
    spec = {"story_height": 5.5, "stairs": [
        {"id": "st01_stair_n", "style": "straight", "run": 4.7}]}
    assert round(stair_pitch.pitch_deg(5.5, 4.7), 1) == 49.5
    assert stair_pitch.lengthen(spec) == ["st01_stair_n"]
    assert stair_pitch.pitch_deg(5.5, spec["stairs"][0]["run"]) <= 38.0
    assert stair_pitch.lengthen(spec) == []          # idempotent


def test_a_gentle_stair_and_a_spiral_are_left_alone():
    spec = {"story_height": 3.0, "stairs": [
        {"id": "a", "style": "straight", "run": 4.0},
        {"id": "b", "style": "spiral", "run": 1.0}]}
    assert stair_pitch.lengthen(spec) == []
    assert spec["stairs"][0]["run"] == 4.0 and spec["stairs"][1]["run"] == 1.0


def test_every_shipped_flight_is_walkable():
    steep = []
    for p in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        if os.path.basename(p).startswith("lf_"):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if d.get("facade"):
            continue
        H = float(d.get("story_height") or 0.0)
        for st in d.get("stairs") or []:
            if (st.get("style") or "straight") not in stair_pitch.PITCHED_STYLES:
                continue
            a = stair_pitch.pitch_deg(H, st.get("run") or stair_pitch.DEFAULT_RUN)
            if a > stair_pitch.MAX_WALKABLE_PITCH_DEG + 1e-9:
                steep.append((os.path.basename(p), st.get("id"), round(a, 1)))
    assert not steep, steep
