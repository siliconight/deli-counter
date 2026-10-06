"""A demo spec says so, and its validation manifest carries it (0.187.0).

The breadth sweep drew `setback_demo` and `pvp_station_ref` into
card_block_001's lots (cold runs 9170, 9174; roadmap 185). Level Factory
reads Deli Counter's own word for what a shell is -- `facade` -- rather than
guessing from a name, so the word for a demo has to come from here too.

Run:  python -m pytest test_demo_flag.py -q
"""
import json
import os

import evidence
import spec_loader

HERE = os.path.dirname(os.path.abspath(__file__))
DEMOS = ("setback_demo", "pvp_station_ref", "survival_demo", "kitbash_demo",
         "rarity_demo")


def _spec(name):
    return os.path.join(HERE, "specs", name + ".json")


def test_the_five_demo_specs_say_so():
    for name in DEMOS:
        assert spec_loader.load_spec(_spec(name)).demo is True, name


def test_a_building_is_not_a_demo_unless_it_says_so():
    assert spec_loader.load_spec(_spec("deli_a01")).demo is False


def test_the_schema_declares_it():
    with open(os.path.join(HERE, "schema", "level.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["properties"]["demo"]["type"] == "boolean"


def test_the_validation_manifest_carries_it():
    """`evidence.collect` builds the report `write_reports` saves as
    `<id>.validation.json`, which is the file Level Factory reads."""
    report, _, _ = evidence.collect(_spec("setback_demo"))
    assert report["demo"] is True
    report, _, _ = evidence.collect(_spec("deli_a01"))
    assert report["demo"] is False
