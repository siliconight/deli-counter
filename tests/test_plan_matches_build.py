"""The plan draws what is built, in the two places it did not (0.254.0, the factory's roadmap 293).

An exploded axonometric reads the plan's layout (`floorplan.storey_walls`), so it would have inherited both:
partitions drawn a fixed 0.15 m thick where `deli_counter.py`'s `_partitions` stands them at `wall_thick`, and the
storey height labelled "clg" where it is floor to floor. Both are asked of the rendered plan, as a reader sees it.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import floorplan as FP  # noqa: E402
import spec_loader  # noqa: E402


def _load(name):
    return spec_loader.load_spec(os.path.join(HERE, "specs", name + ".json"))


def _bands(svg):
    """(short side, long side) in px of every wall band the plan draws."""
    walls = svg[svg.index('<g id="walls">'):svg.index('<g id="openings">')]
    out = []
    for m in re.finditer(r'<rect x="[-\d.]+" y="[-\d.]+" width="([\d.]+)" height="([\d.]+)"', walls):
        w, h = float(m.group(1)), float(m.group(2))
        out.append((min(w, h), max(w, h)))
    return out


def test_a_partition_is_drawn_at_the_thickness_it_is_built_at():
    """deli_a03's ground floor stands partitions; every band longer than it is thick is drawn at `wall_thick`, none
    at the 0.15 m the plan used to draw a partition at."""
    spec = _load("deli_a03")
    assert any(p.story == 0 for p in spec.partitions)
    built = spec.wall_thick * FP.PX_PER_M
    bands = [b for b in _bands(FP.render_story(spec, 0)) if b[1] > b[0] + 0.05]
    assert bands
    assert not [b for b in bands if abs(b[0] - 0.15 * FP.PX_PER_M) < 0.05], "a band drawn 0.15 m thick"
    assert all(abs(b[0] - built) < 0.06 for b in bands if b[1] > built + 0.05), sorted(set(b[0] for b in bands))


def test_the_plan_calls_the_storey_height_floor_to_floor():
    spec = _load("office")
    svg = FP.render_story(spec, 0)
    assert "%.1f m floor to floor" % FP._story_height(spec) in svg and " clg " not in svg
