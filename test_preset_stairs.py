"""Pure tests for the preset vertical-circulation retrofit (no bpy):
every preset leaves make() with classified, oriented, stamped stairs and
role-carrying ladders, and reviews clean. Run: python3 test_preset_stairs.py"""
import presets
import stairwell as S
import ladder as L
from spec_loader import spec_from_dict


def _run(fn):
    fn()
    print(f"[ok] {fn.__name__}")


def _specs():
    for p in sorted(presets.REGISTRY):
        yield p, presets.make(p, name=f"t_{p}")


def test_every_preset_stair_is_classified_oriented_stamped():
    for p, spec in _specs():
        for sd in spec.get("stairs") or []:
            assert sd.get("role") in S.STAIR_ROLES, (p, sd)
            assert sd.get("facing") in ("N", "E", "S", "W"), (p, sd)
            assert sd.get("id"), (p, sd)
            assert (sd.get("meta") or {}).get("generated_by") == "presets", \
                (p, sd["id"])


def test_every_preset_reviews_clean():
    for p, spec in _specs():
        sp = spec_from_dict(spec)
        serrs, _, _ = S.check(sp)
        lerrs, _, _ = L.check(sp)
        assert serrs == [], (p, serrs[:2])
        assert lerrs == [], (p, lerrs[:2])


def test_every_preset_ladder_has_a_role():
    for p, spec in _specs():
        for ld in spec.get("ladders") or []:
            assert ld.get("role") in L.LADDER_ROLES, (p, ld)
            assert ld.get("id"), (p, ld)


def test_preset_stairs_have_clear_circulation():
    """The generated stamp is only applied to physically clean stairs, so a
    stamped stair must have zero clearance findings."""
    for p, spec in _specs():
        sp = spec_from_dict(spec)
        for i, st in enumerate(sp.stairs):
            if (getattr(st, "meta", None) or {}).get("generated_by"):
                fs = S.clearance_findings(sp, st, S.stair_ident(st, i))
                assert fs == [], (p, S.stair_ident(st, i), fs[:1])


def test_finishing_is_deterministic():
    a = presets.make("bank", name="t_det")
    b = presets.make("bank", name="t_det")
    assert a["stairs"] == b["stairs"] and a.get("ladders") == b.get("ladders")


def test_authored_role_and_facing_survive():
    spec = {"name": "t", "n_stories": 2, "footprint_x": 24,
            "footprint_y": 18, "story_height": 3.5,
            "stairs": [{"x": 0.0, "y": 0.0, "from_story": 0, "to_story": 1,
                        "width": 1.2, "run": 4.0, "style": "straight",
                        "facing": "E", "role": "service", "id": "mine"}]}
    presets._finish_stairs(spec)
    sd = spec["stairs"][0]
    assert sd["facing"] == "E" and sd["role"] == "service"   # authored kept
    assert sd["meta"]["generated_by"] == "presets"           # clean -> stamped


def test_unfixable_stair_is_not_stamped():
    """A stair that no facing can make physically clean keeps authored
    severity (no generated stamp) instead of breaking generation."""
    spec = {"name": "t", "n_stories": 2, "footprint_x": 8,
            "footprint_y": 8, "story_height": 3.5,
            "stairs": [{"x": 0.0, "y": 0.0, "from_story": 0, "to_story": 1,
                        "width": 1.2, "run": 6.0, "style": "straight"}]}
    presets._finish_stairs(spec)
    sd = spec["stairs"][0]
    assert sd.get("role") and sd.get("facing")               # still finished
    assert "generated_by" not in (sd.get("meta") or {})      # but not stamped


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            _run(fn)
    print("all preset stair tests passed")
