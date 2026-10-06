import json, glob, os
print("=== BUILDING GATES ===")
specs = ["bank_branch_a02","bank_branch_a03","bank_branch_a04","deli_a01","deli_a02",
         "deli_a03","warehouse_a01","warehouse_a02","parking_garage_a01","parking_garage_a02"]
navp = imp = 0
for s in specs:
    nf = f"build/{s}.navgate.json"; gf = f"build/{s}.godot_import.json"
    nav = json.load(open(nf)) if os.path.exists(nf) else {}
    imp_j = json.load(open(gf)) if os.path.exists(gf) else {}
    nav_ok = nav.get("ok"); imp_ok = imp_j.get("ok")
    navp += bool(nav_ok); imp += bool(imp_ok)
    stairs = [(x.get("id"), x.get("status")) for x in nav.get("stairs", [])]
    print(f"  {s:22s} nav={'PASS' if nav_ok else 'FAIL'} import={'PASS' if imp_ok else 'FAIL'} polys={nav.get('navmesh_polys')} stairs={stairs}")
print(f"  --> nav {navp}/10, import {imp}/10")
print("=== SITE GATES ===")
for proj, spec in [("deli_block_proj","deli_block"), ("central_vault_proj","central_vault")]:
    wf = f"../_runs/{proj}/{spec}_navqa.walktest.json"
    mf = f"../_runs/{proj}/{spec}.mp_smoke.json"
    w = json.load(open(wf)) if os.path.exists(wf) else {}
    m = json.load(open(mf)) if os.path.exists(mf) else {}
    bad = [p['leg'] for p in w.get("path_proofs",[]) if not p['ok']]
    print(f"  {spec:16s} walktest={'PASS' if w.get('ok') else 'FAIL'} sim={w.get('sim_seconds')}s bad_proofs={bad[:4]}  mp_smoke={'PASS' if m.get('ok') else 'FAIL'}")
