"""`portable_building.combine_circulation` (0.209.0): one `circulation_check` from the
arms that ran -- the shell's, the dressing's, the roof props' -- in the shape 0.149.0's
readers split by name."""
import portable_building as pb


def test_one_arm_is_returned_as_itself():
    shell = {"ok": True, "source": "shell", "conflicts": []}
    assert pb.combine_circulation(
        [("shell", shell), ("dressing", None), ("roofprops", None)]) is shell
    dress = {"ok": False, "source": "dressing"}
    assert pb.combine_circulation(
        [("shell", None), ("dressing", dress), ("roofprops", None)]) is dress


def test_two_arms_keep_0_208_0_s_shape_and_three_add_the_roof():
    shell = {"ok": True, "source": "shell"}
    dress = {"ok": False, "source": "dressing"}
    roof = {"ok": True, "source": "roofprops"}
    assert pb.combine_circulation(
        [("shell", shell), ("dressing", dress), ("roofprops", None)]) == {
            "ok": False, "shell": shell, "dressing": dress}
    assert pb.combine_circulation(
        [("shell", shell), ("dressing", dress), ("roofprops", roof)]) == {
            "ok": False, "shell": shell, "dressing": dress, "roofprops": roof}
    assert pb.combine_circulation(
        [("shell", shell), ("dressing", None), ("roofprops", roof)]) == {
            "ok": True, "shell": shell, "roofprops": roof}


def test_no_arm_is_none():
    assert pb.combine_circulation(
        [("shell", None), ("dressing", None), ("roofprops", None)]) is None
