import glob
import json

for fn in sorted(glob.glob("tests/mandala_toponymy_swarm/swarm_in_*.json")):
    with open(fn, "r", encoding="utf-8") as f:
        data = json.load(f)
    for s in data["settlements"]:
        k = s["key"]
        n = s["name"]
        if any(w in k.lower() or w in n.lower() for w in ["pyay", "prome", "ksetra", "hakha", "chin state"]):
            print(f"{fn}: key={k}, name={n}, country={s.get('country')}, coords={s.get('coords_lat_lng')}, latest={s.get('latest_year')}")
