#!/usr/bin/env python3
r"""Phase 4 Wave B status -- local ground truth for the 12 terminal configs.

Run from deli_counter\ after the engine batch:
    python phase4b_status.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

NAMES = ["airport_terminal_a01", "airport_terminal_a02", "airport_terminal_a03",
         "bank_tower_a01", "bank_tower_a02", "bank_tower_a03",
         "landmark_hall_a01", "landmark_hall_a02", "landmark_hall_a03",
         "train_yard_a01", "train_yard_a02", "train_yard_a03"]


def verdict(path, ok_key="ok"):
    p = os.path.join(BUILD, path)
    if not os.path.exists(p):
        return "missing"
    try:
        r = json.load(open(p))
    except Exception as e:
        return f"unreadable ({e})"
    ok = r.get(ok_key)
    if ok is None and "checks" in r:
        ok = all(c.get("ok") for c in r["checks"])
    return "PASS" if ok else "FAIL"


def detail(path):
    p = os.path.join(BUILD, path)
    if not os.path.exists(p):
        return ""
    try:
        r = json.load(open(p))
    except Exception:
        return ""
    outs = []
    for c in r.get("checks", []):
        if not c.get("ok"):
            outs.append(f"{c.get('id', c.get('name', '?'))}: {c.get('why', c.get('detail', ''))}")
    if not r.get("ok", True) and not outs:
        outs.append(str(r.get("why", r.get("error", "")))[:160])
    return "; ".join(outs)[:200]


nav_p = imp_p = 0
print(f"{'config':<18} {'nav_gate':<9} {'godot_import':<12}")
print("-" * 42)
for n in NAMES:
    nv = verdict(f"{n}.navgate.json")
    im = verdict(f"{n}.godot_import.json")
    nav_p += nv == "PASS"
    imp_p += im == "PASS"
    print(f"{n:<18} {nv:<9} {im:<12}")
    for tag, rep in (("nav", f"{n}.navgate.json"), ("imp", f"{n}.godot_import.json")):
        if verdict(rep) == "FAIL":
            d = detail(rep)
            if d:
                print(f"    [{tag}] {d}")
print("-" * 42)
print(f"nav {nav_p}/12   import {imp_p}/12")
print("ALL GREEN" if nav_p == imp_p == 12 else "stragglers above")
