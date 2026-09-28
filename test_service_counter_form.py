"""0.146.0 -- the stores' register counters ask for Zoo 1.7.0's `service` form.

`migrate_service_counter.py` gives every checked-in `register_counter` the
form; the delis' `front_register_counter` is not one. The preset carries it
for specs made later. And the form survives into the slot Zoo reads -- a
field on a spec that never reaches `slots.json` would be the knob with no
effect this repo keeps finding.
"""
import glob
import json
import os
import shutil

import migrate_service_counter as M

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    return json.load(open(os.path.join(HERE, "specs", name), encoding="utf-8"))


def test_every_store_counter_in_the_library_has_the_form():
    assert M.main(["--check"]) == 0, "run: python migrate_service_counter.py"
    n = 0
    for p in glob.glob(os.path.join(HERE, "specs", "*.json")):
        if os.path.basename(p).startswith("lf_"):
            continue
        for v in json.load(open(p, encoding="utf-8")).get("volumes") or []:
            if v.get("name") == M.COUNTER:
                assert v.get("form") == M.FORM, p
                n += 1
    assert n == 9, n


def test_the_deli_counters_are_left_alone():
    for name in ("deli_a01.json", "cr_deli.json", "corner_deli_heist_01.json"):
        v = [x for x in _load(name)["volumes"] if x["name"] == "front_register_counter"]
        assert v and not v[0].get("form"), name


def test_the_migration_is_idempotent_and_keeps_an_existing_form(tmp_path):
    src = os.path.join(HERE, "specs", "gas_station_a02.json")
    d = json.load(open(src, encoding="utf-8"))
    for v in d["volumes"]:
        if v["name"] == M.COUNTER:
            v.pop("form", None)
    (tmp_path / "a.json").write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    d2 = json.loads(json.dumps(d))
    for v in d2["volumes"]:
        if v["name"] == M.COUNTER:
            v["form"] = "bar"
    (tmp_path / "b.json").write_text(json.dumps(d2, indent=1) + "\n", encoding="utf-8")
    shutil.copy(src, tmp_path / "lf_skip.json")
    assert M.main(["--check", "--dir", str(tmp_path)]) == 1
    assert M.main(["--dir", str(tmp_path)]) == 0
    first = (tmp_path / "a.json").read_bytes()
    assert M.main(["--dir", str(tmp_path)]) == 0
    assert (tmp_path / "a.json").read_bytes() == first
    got = {v["name"]: v.get("form") for v in json.loads(first)["volumes"]}
    assert got[M.COUNTER] == "service"
    kept = json.load(open(tmp_path / "b.json", encoding="utf-8"))
    assert [v["form"] for v in kept["volumes"] if v["name"] == M.COUNTER] == ["bar"]


def test_the_preset_carries_it_for_a_spec_made_later():
    import presets
    spec = presets.gas_station()
    v = [x for x in spec["volumes"] if x["name"] == M.COUNTER]
    assert v and v[0]["form"] == M.FORM


def test_the_form_reaches_the_slot_zoo_reads():
    """Built from the checked-in spec: the slot for the counter says
    `service`, which is what `kit.honour_dressing` reads."""
    slots = os.path.join(HERE, "build", "gas_station_a02.slots.json")
    doc = json.load(open(slots, encoding="utf-8"))
    rows = [s for s in doc["slots"] if s.get("slot_id", "").startswith(M.COUNTER)]
    assert rows, sorted({s.get("slot_id", "")[:24] for s in doc["slots"]})[:20]
    assert all(s.get("form") == M.FORM for s in rows), [(s["slot_id"], s.get("form")) for s in rows]
