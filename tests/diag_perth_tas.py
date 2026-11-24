import glob, json, os

SDIR = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\_shared\settlement_sources"
MOD_AUS = r"f:\Active Projects\Project 1509 - SVEA\histmap\1.data_raw\population_regional\AUSTRAL\3.modern\1.modern_australia\modern_australia_settlements.json"

d = json.load(open(MOD_AUS, encoding="utf-8"))
print("=== modern_australia city_proper >= 100k ===")
for k, v in sorted(d.items(), key=lambda kv: -max(kv[1]["population"].values())):
  mx = max(v["population"].values())
  if v.get("population_scope") == "city_proper" and mx >= 100000:
    print(f"  {k:40s} | {v.get('admin1',''):20s} | {v['coords']} | peak={mx}")

print("\n=== Scanning source files for Perth (lat < -38) with pop > 20k ===")
for fp in sorted(glob.glob(os.path.join(SDIR, "*.json"))):
  raw = json.load(open(fp, encoding="utf-8"))
  if isinstance(raw, dict) and "settlements" in raw:
    items = raw["settlements"].items() if isinstance(raw["settlements"], dict) else enumerate(raw["settlements"])
  elif isinstance(raw, dict):
    items = raw.items()
  elif isinstance(raw, list):
    items = enumerate(raw)
  else:
    continue
  for k, v in items:
    if not isinstance(v, dict):
      continue
    nm = str(v.get("name") or k).lower()
    co = v.get("coords") or []
    pop = v.get("population") or {}
    if "perth" in nm and len(co) >= 2 and float(co[0]) < -38 and pop and max(int(x) for x in pop.values()) > 20000:
      print("  FOUND:", os.path.basename(fp), k, v.get("admin1"), co, len(pop), max(int(x) for x in pop.values()))
