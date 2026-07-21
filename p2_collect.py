import shutil, os, json
DST = r"C:\Projects\gabagool_studios\gabagool_factory\_runs\p2_diag"
shutil.rmtree(DST, ignore_errors=True); os.makedirs(DST)
picks = [
 ("build/supermarket_a03.navgate.json", "sm03.navgate.json"),
 ("build/gas_station_a01.godot_import.json", "gs01.import.json"),
 ("build/gas_station_a02.godot_import.json", "gs02.import.json"),
 ("build/gas_station_a01.navgate.json", "gs01.navgate.json"),
 ("build/pawn_shop_a01.navgate.json", "pw01.navgate.json"),
 ("build/apartment_walkup_a01.navgate.json", "aw01.navgate.json"),
 (r"..\_runs\walkup_siege_proj\walkup_siege.mp_smoke.json", "ws.smoke.json"),
 (r"..\_runs\warehouse_district_proj\warehouse_district_navqa.walktest.json", "wd.walktest.json"),
]
for src, dst in picks:
    try:
        shutil.copy(src, os.path.join(DST, dst)); print("copied", dst)
    except Exception as e:
        print("MISS", dst, e)
# also snapshot the mp_smoke per-process logs for walkup_siege
for lg in ("host", "client0", "client1", "client2"):
    src = rf"..\_runs\walkup_siege_proj\_mp_logs\{lg}.log"
    try:
        shutil.copy(src, os.path.join(DST, f"ws_{lg}.log")); print("copied", f"ws_{lg}.log")
    except Exception as e:
        print("MISS", lg, e)
print("done ->", DST)
