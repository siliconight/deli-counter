import json, os
SPECS = ["rail_station_a01","rail_station_a02","rail_station_a03",
         "freight_terminal_a01","freight_terminal_a02","freight_terminal_a03",
         "self_storage_a01","self_storage_a02","self_storage_a03",
         "construction_site_a01","construction_site_a02","construction_site_a03",
         "funeral_home_a01","funeral_home_a02","funeral_home_a03",
         "strip_club_a01","strip_club_a02","strip_club_a03"]
print("=== P3 WAVE B BUILDING GATES (18) ===")
navp = imp = 0
for s in SPECS:
    nf, gf = f"build/{s}.navgate.json", f"build/{s}.godot_import.json"
    nav = json.load(open(nf)) if os.path.exists(nf) else {}
    im = json.load(open(gf)) if os.path.exists(gf) else {}
    navp += bool(nav.get("ok")); imp += bool(im.get("ok"))
    if not (nav.get("ok") and im.get("ok")):
        stairs = [(x.get("id"), x.get("status")) for x in nav.get("stairs", [])]
        print(f"  FAIL {s:24s} nav={'PASS' if nav.get('ok') else 'FAIL'} import={'PASS' if im.get('ok') else 'FAIL'} polys={nav.get('navmesh_polys')} stairs={stairs} unreach={nav.get('markers',{}).get('unreachable')}")
print(f"  --> nav {navp}/18, import {imp}/18 (silence above = green)")
