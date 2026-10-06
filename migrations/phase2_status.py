import json, os
SPECS = ["credit_union_a01","credit_union_a02","credit_union_a03",
         "supermarket_a01","supermarket_a02","supermarket_a03",
         "pharmacy_a01","pharmacy_a02",
         "large_warehouse_a01","large_warehouse_a02","large_warehouse_a03",
         "depot_a01","depot_a02","clinic_a01","clinic_a02"]
print("=== WAVE A BUILDING GATES ===")
navp = imp = 0
for s in SPECS:
    nf, gf = f"build/{s}.navgate.json", f"build/{s}.godot_import.json"
    nav = json.load(open(nf)) if os.path.exists(nf) else {}
    im = json.load(open(gf)) if os.path.exists(gf) else {}
    navp += bool(nav.get("ok")); imp += bool(im.get("ok"))
    stairs = [(x.get("id"), x.get("status")) for x in nav.get("stairs", [])]
    print(f"  {s:24s} nav={'PASS' if nav.get('ok') else 'FAIL'} import={'PASS' if im.get('ok') else 'FAIL'} polys={nav.get('navmesh_polys')} stairs={stairs}")
print(f"  --> nav {navp}/15, import {imp}/15")
