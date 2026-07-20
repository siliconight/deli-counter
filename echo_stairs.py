import json, glob, os
for g in sorted(glob.glob("build/*.gameplay.json")):
    try:
        d = json.load(open(g))
        ss = [s.get("id") for s in d.get("stair_systems", [])]
        print(f"  {os.path.basename(g):32s} stairs={ss}")
    except Exception as e:
        print(f"  {g}: ERR {e}")
