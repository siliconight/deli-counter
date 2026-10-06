#!/usr/bin/env python3
r"""Phase 4 Wave A status -- local ground truth for the 13 venue configs.

Run from deli_counter\ after the engine batch:
    python phase4a_status.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")

NAMES = ["stadium_a01", "stadium_a02", "stadium_a03", "stadium_a04",
         "arena_a01", "arena_a02", "arena_a03",
         "casino_a01", "casino_a02", "casino_a03",
         "market_hall_a01", "market_hall_a02", "market_hall_a03"]


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
print(f"nav {nav_p}/13   import {imp_p}/13")
print("ALL GREEN" if nav_p == imp_p == 13 else "stragglers above")
