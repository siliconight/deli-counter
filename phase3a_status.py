import json, os
SPECS = ["museum_a01","museum_a02","museum_a03","courthouse_a01","courthouse_a02",
         "courthouse_a03","mansion_a01","mansion_a02","mansion_a03",
         "country_club_a01","country_club_a02","brewery_a01","brewery_a02",
         "brewery_a03","marina_a01","marina_a02","marina_a03"]
print("=== P3 WAVE A BUILDING GATES (17) ===")
navp = imp = 0
for s in SPECS:
    nf, gf = f"build/{s}.navgate.json", f"build/{s}.godot_import.json"
    nav = json.load(open(nf)) if os.path.exists(nf) else {}
    im = json.load(open(gf)) if os.path.exists(gf) else {}
    navp += bool(nav.get("ok")); imp += bool(im.get("ok"))
    if not (nav.get("ok") and im.get("ok")):
        stairs = [(x.get("id"), x.get("status")) for x in nav.get("stairs", [])]
        print(f"  FAIL {s:20s} nav={'PASS' if nav.get('ok') else 'FAIL'} import={'PASS' if im.get('ok') else 'FAIL'} polys={nav.get('navmesh_polys')} stairs={stairs} unreach={nav.get('markers',{}).get('unreachable')}")
print(f"  --> nav {navp}/17, import {imp}/17 (silence above = green)")
