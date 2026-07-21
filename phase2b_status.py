import json, os
WAVE_A = ["credit_union_a01","credit_union_a02","credit_union_a03","supermarket_a01",
          "supermarket_a02","supermarket_a03","pharmacy_a01","pharmacy_a02",
          "large_warehouse_a01","large_warehouse_a02","large_warehouse_a03",
          "depot_a01","depot_a02","clinic_a01","clinic_a02"]
WAVE_B = ["gas_station_a01","gas_station_a02","gas_station_a03","auto_shop_a01",
          "auto_shop_a02","pawn_shop_a01","pawn_shop_a02","strip_retail_a01",
          "strip_retail_a02","apartment_walkup_a01","apartment_walkup_a02","apartment_walkup_a03"]
print("=== PHASE 2 BUILDING GATES (27 configs) ===")
navp = imp = 0
for s in WAVE_A + WAVE_B:
    nf, gf = f"build/{s}.navgate.json", f"build/{s}.godot_import.json"
    nav = json.load(open(nf)) if os.path.exists(nf) else {}
    im = json.load(open(gf)) if os.path.exists(gf) else {}
    navp += bool(nav.get("ok")); imp += bool(im.get("ok"))
    if not (nav.get("ok") and im.get("ok")):
        stairs = [(x.get("id"), x.get("status")) for x in nav.get("stairs", [])]
        print(f"  FAIL {s:24s} nav={'PASS' if nav.get('ok') else 'FAIL'} import={'PASS' if im.get('ok') else 'FAIL'} polys={nav.get('navmesh_polys')} stairs={stairs} unreach={nav.get('markers',{}).get('unreachable')}")
print(f"  --> nav {navp}/27, import {imp}/27 (failures listed above; silence = green)")
print("=== SITE GATES ===")
for proj, spec in [("strip_mall_proj","strip_mall"), ("walkup_siege_proj","walkup_siege"),
                   ("warehouse_district_proj","warehouse_district")]:
    wf = f"../_runs/{proj}/{spec}_navqa.walktest.json"
    mf = f"../_runs/{proj}/{spec}.mp_smoke.json"
    w = json.load(open(wf)) if os.path.exists(wf) else {}
    m = json.load(open(mf)) if os.path.exists(mf) else {}
    bad = [p['leg'] for p in w.get("path_proofs",[]) if not p['ok']]
    stuck = [x['name'] for x in w.get("walkers",[]) if not str(x['status']).startswith('ok')]
    print(f"  {spec:20s} walktest={'PASS' if w.get('ok') else 'FAIL'} sim={w.get('sim_seconds')}s bad_proofs={bad[:3]} stuck={stuck[:4]}  mp_smoke={'PASS' if m.get('ok') else 'FAIL'}")
